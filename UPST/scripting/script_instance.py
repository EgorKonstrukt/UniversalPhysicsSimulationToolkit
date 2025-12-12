import os
import time
import math
import random
import threading
import traceback
from typing import Optional, Any, Callable, TypeVar, Dict, List, Tuple, Union, Set

import pygame
import pymunk

from UPST.config import config
from UPST.modules.camera import Camera
from UPST.modules.profiler import profile
from UPST.sound.sound_synthesizer import synthesizer
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos, get_gizmos
from UPST.gui.windows.plotter_window import PlotterWindow

try:
    import numpy as np
except Exception:
    np = None

try:
    from numba import njit
    _numba_available = True
except Exception:
    _numba_available = False
    def njit(cache=True):
        def _decorator(fn):
            return fn
        return _decorator

T = TypeVar('T', bound=Callable)

class ScriptInstance:


    def __init__(self, code: str, owner: Any, name: str = "Unnamed Script", threaded_default: bool = False, app=None):
        self.code = code
        self.app = app
        self.owner = owner
        self.name = name
        self.running = False
        self.paused = False
        self.thread: Optional[threading.Thread] = None
        self._user_threads: List[threading.Thread] = []
        self.thread_lock = threading.RLock()
        self._bg_fps = config.scripting.background_fps
        self._stop_event = threading.Event()
        self._last_bg_time: Optional[float] = None
        self.state: Dict[str, Any] = {}
        self.filepath: Optional[str] = None
        self._start_fn: Optional[Callable] = None
        self._update_main: Optional[Callable] = None
        self._update_bg: Optional[Callable] = None
        self._stop_fn: Optional[Callable] = None
        self._save_state_fn: Optional[Callable] = None
        self._load_state_fn: Optional[Callable] = None
        self.threaded = threaded_default
        self._init_namespace_and_compile()

    def _user_thread_decorator(self, fn: T) -> T:
        def wrapper(*a, **kw):
            if not self.running:
                Debug.log_warning(f"Function '{fn.__name__}' called outside running ScriptInstance '{self.name}'", "Scripting")
                return None
            if not _numba_available and not (hasattr(fn, '_uses_io') or getattr(fn, '__name__', '').startswith('io_')):
                Debug.log_warning(f"CPU-bound @threaded function '{fn.__name__}' in script '{self.name}' may suffer from GIL. Install numba or use I/O-bound operations only.", "Scripting")
            Debug.log_info(f"Spawning user thread for {fn.__name__} in script '{self.name}'", "Scripting")
            return self.spawn_thread(fn, *a, **kw)
        wrapper._is_user_threaded = True
        wrapper._original = fn
        return wrapper

    def _main_manager(self):
        return self.app.ui_manager if self.app and hasattr(self.app, 'ui_manager') else config.ui_manager

    def _make_plotter(self):
        mm = self._main_manager()
        return lambda *a, **kw: PlotterWindow(mm, *a, **kw)

    def _is_pickle_safe(self, v) -> bool:
        if isinstance(v, (int, float, str, bool, type(None))): return True
        if isinstance(v, (list, tuple)): return all(self._is_pickle_safe(x) for x in v)
        if isinstance(v, dict): return all(isinstance(k, (str, int, float, bool)) and self._is_pickle_safe(val) for k, val in v.items())
        return False

    def _unwrap_if_threaded(self, obj: Optional[Callable]) -> Optional[Callable]:
        if not callable(obj): return obj
        if getattr(obj, "_is_user_threaded", False):
            orig = getattr(obj, "_original", None)
            if callable(orig):
                Debug.log_warning(f"User function '{getattr(orig, '__name__', 'unknown')}' in script '{self.name}' was decorated with @threaded; unwrapping for synchronous execution.", "Scripting")
                return orig
        return obj

    def _build_base_namespace(self, for_recompile: bool = False) -> Dict[str, Any]:
        mm = self._main_manager() if for_recompile else None
        plotter_factory = (lambda *a, **kw: PlotterWindow(mm, *a, **kw)) if for_recompile else self._make_plotter()
        threaded_decorator = self._user_thread_decorator if not for_recompile else (
            lambda fn: (lambda *a, **k: self.spawn_thread(fn, *a, **k)).__setattr__('_is_user_threaded', True) or
                       setattr(lambda *a, **k: self.spawn_thread(fn, *a, **k), '_original', fn) or
                       (lambda *a, **k: self.spawn_thread(fn, *a, **k))
        )
        if for_recompile:
            def threaded(fn):
                wrapper = lambda *a, **k: self.spawn_thread(fn, *a, **k)
                wrapper._is_user_threaded = True
                wrapper._original = fn
                return wrapper
            threaded_decorator = threaded
        return {
            "owner": self.owner, "app": self.app, "config": config, "Camera": Camera,
            "Gizmos": Gizmos, "Debug": Debug, "synthesizer": synthesizer, "pymunk": pymunk,
            "time": time, "math": math, "random": random, "threading": threading,
            "pygame": pygame, "self": self, "traceback": traceback, "profile": profile,
            "thread_lock": self.thread_lock, "spawn_thread": self.spawn_thread,
            "log": lambda m: Debug.log_info(str(m), "UserScript"), "set_bg_fps": self.set_bg_fps,
            "threaded": threaded_decorator, "np": np, "njit": njit,
            "Optional": Optional, "Any": Any, "Callable": Callable, "TypeVar": TypeVar,
            "Dict": Dict, "List": List, "Tuple": Tuple, "Union": Union, "Set": Set,
            "PlotterWindow": plotter_factory, "load_script": self._load_script_wrapper
        }

    def _init_namespace_and_compile(self):
        ns = self._build_base_namespace()
        try:
            exec(self.code, ns, ns)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' compilation error: {traceback.format_exc()}", "Scripting")
            ns = {}
        for k, v in ns.items():
            if k.startswith('__') or k in config.scripting.BUILTIN_NAMES or callable(v) or isinstance(v, type):
                continue
            if self._is_pickle_safe(v):
                self.state[k] = v
            else:
                Debug.log_warning(f"Non-picklable variable '{k}' skipped in script state (type: {type(v).__name__}).", "Scripting")
        self._extract_functions(ns)
        self.threaded = self.threaded or bool(self._update_bg)
        if self.threaded and not _numba_available:
            Debug.log_warning(f"Script '{self.name}' uses background updates without numba — may be GIL-bound.", "Scripting")
        Debug.log_info(f"Script '{self.name}' initialized on {type(self.owner).__name__ if self.owner is not None else 'None'}. threaded={self.threaded}", "Scripting")

    def _load_script_wrapper(self, name: str) -> str:
        d = "UserScripts"
        os.makedirs(d, exist_ok=True)
        if not name.endswith(".py"): name += ".py"
        p = os.path.join(d, name)
        if not os.path.isfile(p):
            Debug.log_error(f"Script file not found: {p}", "Scripting")
            return ""
        with open(p, 'r', encoding='utf-8') as f:
            code = f.read()
        self.filepath = os.path.abspath(p)
        return code

    def reload_from_file(self) -> bool:
        if not self.filepath or not os.path.isfile(self.filepath): return False
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                new_code = f.read()
            ok = self._recompile(new_code)
            if ok: Debug.log_info(f"Reloaded script '{self.name}' from {self.filepath}", "Scripting")
            return ok
        except Exception:
            Debug.log_exception(f"Failed to reload script '{self.name}' from {self.filepath}", "Scripting")
            return False

    def set_bg_fps(self, fps: float):
        with self.thread_lock:
            try:
                v = float(fps)
            except Exception:
                return
            self._bg_fps = max(1.0, min(240.0, v))

    def get_bg_dt(self) -> float:
        with self.thread_lock:
            return 1.0 / max(1.0, self._bg_fps)

    def spawn_thread(self, target: Callable, *args, **kwargs) -> Optional[threading.Thread]:
        if not self.running:
            Debug.log_warning(f"Attempted to spawn thread on stopped script '{self.name}'", "Scripting")
            return None
        with self.thread_lock:
            self._user_threads = [t for t in self._user_threads if t.is_alive()]
            if len(self._user_threads) >= config.scripting.MAX_USER_THREADS:
                Debug.log_error(f"Script '{self.name}' exceeded thread limit ({config.scripting.MAX_USER_THREADS}). Ignoring spawn.", "Scripting")
                return None
            t = threading.Thread(target=self._thread_wrapper, args=(target, args, kwargs), daemon=True)
            self._user_threads.append(t)
        t.start()
        return t

    def _thread_wrapper(self, target: Callable, args, kwargs):
        while self.running and not self._stop_event.is_set() and self.is_paused():
            time.sleep(0.01)
        try:
            target(*args, **kwargs)
        except Exception:
            Debug.log_exception(f"User thread in script '{self.name}' crashed: {traceback.format_exc()}", "Scripting")
        finally:
            with self.thread_lock:
                cur = threading.current_thread()
                self._user_threads = [t for t in self._user_threads if t is not cur and t.is_alive()]

    def start(self):
        if self.running: return
        self.running = True
        self._stop_event.clear()
        self._last_bg_time = time.perf_counter()
        gm = get_gizmos()
        if gm: gm.scripts_paused = False
        try:
            if self._start_fn: self._start_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' start() error: {traceback.format_exc()}", "Scripting")
        if self.threaded and self._update_bg:
            self.thread = threading.Thread(target=self._bg_loop, daemon=True)
            self.thread.start()

    @profile("update", "scripting")
    def update(self, dt: float):
        if not self.running or not self._update_main or self.is_paused():
            return
        start = time.perf_counter()
        try:
            self._update_main(dt)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' update() error", "Scripting")
        self._last_exec_time = time.perf_counter() - start

    def _join_user_threads(self, timeout_per_thread: float = 0.1):
        with self.thread_lock:
            threads = [t for t in self._user_threads if t.is_alive()]
        for t in threads:
            try:
                t.join(timeout_per_thread)
            except Exception:
                pass
        with self.thread_lock:
            self._user_threads = [t for t in self._user_threads if t.is_alive()]

    def stop(self):
        if not self.running: return
        if getattr(self, 'preserve_gizmos', True):
            gm = get_gizmos()
            if gm: gm.scripts_paused = True
        self.running = False
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(0.5)
        self._join_user_threads(0.1)
        try:
            if self._stop_fn: self._stop_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' stop() error: {traceback.format_exc()}", "Scripting")

    def get_serializable_state(self) -> dict:
        if self._save_state_fn:
            try:
                usr = self._save_state_fn()
                if isinstance(usr, dict): return usr
                Debug.log_warning(f"save_state() in '{self.name}' must return dict; got {type(usr)}. Ignored.", "Scripting")
            except Exception as e:
                Debug.log_exception(f"Error in save_state() of '{self.name}': {e}", "Scripting")
        return {}

    def restore_state(self, state: dict):
        if self._load_state_fn:
            try:
                self._load_state_fn(state)
            except Exception as e:
                Debug.log_exception(f"Error in load_state() of '{self.name}': {e}", "Scripting")

    def pause(self):
        with self.thread_lock:
            self.paused = True

    def resume(self):
        with self.thread_lock:
            self.paused = False

    def is_paused(self) -> bool:
        with self.thread_lock:
            return self.paused

    def _bg_loop(self):
        self._last_bg_time = time.perf_counter()
        while self.running and not self._stop_event.is_set():
            if self.is_paused():
                time.sleep(0.01)
                continue
            now = time.perf_counter()
            dt_t = self.get_bg_dt()
            if self._update_bg:
                start = time.perf_counter()
                try:
                    self._update_bg(dt_t)
                except Exception:
                    Debug.log_exception(f"Script '{self.name}' background update error", "Scripting")
                self._last_exec_time = time.perf_counter() - start
            elapsed = time.perf_counter() - now
            st = max(0.0, dt_t - elapsed)
            if st > 0: time.sleep(st)

    def _recompile(self, new_code: str) -> bool:
        self.code = new_code
        ns = self._build_base_namespace(for_recompile=True)
        try:
            exec(self.code, ns, ns)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' recompilation error: {traceback.format_exc()}", "Scripting")
            return False
        self._extract_functions(ns)
        return True
    def recompile(self) -> bool:
        """Recompile script from its current `self.code`, preserving runtime state."""
        if not self.running:
            return self._recompile(self.code)
        saved_state = self.state.copy()
        was_running = self.running
        self.stop()
        ok = self._recompile(self.code)
        if ok:
            self.state.update(saved_state)
            if was_running:
                self.start()
        return ok

    def _extract_functions(self, ns: Dict[str, Any]):
        self._start_fn = self._unwrap_if_threaded(ns.get("start"))
        self._update_main = self._unwrap_if_threaded(ns.get("update"))
        self._update_bg = ns.get("update_threaded")
        self._stop_fn = self._unwrap_if_threaded(ns.get("stop"))
        self._save_state_fn = ns.get("save_state")
        self._load_state_fn = ns.get("load_state")