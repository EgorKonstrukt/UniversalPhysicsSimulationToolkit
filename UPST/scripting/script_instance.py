import threading
import time
import traceback
from typing import Optional, Any, Callable, TypeVar, Dict, List, Tuple, Union, Set

import pygame
import pymunk
import math
import random

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
        self.thread: Optional[threading.Thread] = None
        self._user_threads: list[threading.Thread] = []
        self.thread_lock = threading.RLock()
        self._bg_fps = 60.0
        self._stop_event = threading.Event()
        self._last_bg_time = None
        self.state = {}

        def threaded(fn: T) -> T:
            def wrapper(*args, **kwargs):
                if not self.running:
                    Debug.log_warning(f"Function '{fn.__name__}' called outside running ScriptInstance '{self.name}'", "Scripting")
                    return None
                if not _numba_available and not (hasattr(fn, '_uses_io') or getattr(fn, '__name__', '').startswith('io_')):
                    Debug.log_warning(f"CPU-bound @threaded function '{fn.__name__}' in script '{self.name}' may suffer from GIL. Install numba or use I/O-bound operations only.", "Scripting")
                Debug.log_info(f"Spawning user thread for {fn.__name__} in script '{self.name}'", "Scripting")
                return self.spawn_thread(fn, *args, **kwargs)
            wrapper._is_user_threaded = True
            wrapper._original = fn
            return wrapper

        namespace: Dict[str, Any] = {
            "owner": owner,
            "app": app,
            "config": config,
            "Camera": Camera,
            "Gizmos": Gizmos,
            "Debug": Debug,
            "synthesizer": synthesizer,
            "pymunk": pymunk,
            "time": time,
            "math": math,
            "random": random,
            "threading": threading,
            "pygame": pygame,
            "self": self,
            "traceback": traceback,
            "profile": profile,
            "thread_lock": self.thread_lock,
            "spawn_thread": self.spawn_thread,
            "log": lambda msg: Debug.log_info(str(msg), "UserScript"),
            "set_bg_fps": self.set_bg_fps,
            "threaded": threaded,
            "np": np,
            "njit": njit,
            "Optional": Optional,
            "Any": Any,
            "Callable": Callable,
            "TypeVar": TypeVar,
            "Dict": Dict,
            "List": List,
            "Tuple": Tuple,
            "Union": Union,
            "Set": Set,
            "PlotterWindow": PlotterWindow,
        }

        try:
            exec(self.code, namespace, namespace)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' compilation error: {traceback.format_exc()}", "Scripting")
            namespace = {}

        def _is_pickle_safe(value):
            if isinstance(value, (int, float, str, bool, type(None))):
                return True
            if isinstance(value, (list, tuple)):
                return all(_is_pickle_safe(v) for v in value)
            if isinstance(value, dict):
                return all(isinstance(k, (str, int, float, bool)) and _is_pickle_safe(v) for k, v in value.items())
            return False

        for k, v in namespace.items():
            if k.startswith('__') or k in (
                    "owner", "Gizmos", "Debug","synthesizer" , "pymunk", "time", "math", "random", "threading",
                    "pygame", "self", "traceback", "profile", "thread_lock", "spawn_thread",
                    "log", "set_bg_fps", "threaded", "np", "njit"
            ) or callable(v) or isinstance(v, type):
                continue
            if _is_pickle_safe(v):
                self.state[k] = v
            else:
                Debug.log_warning(f"Non-picklable variable '{k}' skipped in script state (type: {type(v).__name__}).",
                                  "Scripting")

        def _unwrap_if_threaded(obj: Optional[Callable]) -> Optional[Callable]:
            if not callable(obj):
                return obj
            if getattr(obj, "_is_user_threaded", False):
                orig = getattr(obj, "_original", None)
                if callable(orig):
                    Debug.log_warning(f"User function '{getattr(orig, '__name__', 'unknown')}' in script '{self.name}' was decorated with @threaded; unwrapping for synchronous execution.", "Scripting")
                    return orig
            return obj

        self._start_fn = _unwrap_if_threaded(namespace.get("start"))
        self._update_main = _unwrap_if_threaded(namespace.get("update"))
        self._update_bg = namespace.get("update_threaded")
        self._stop_fn = _unwrap_if_threaded(namespace.get("stop"))
        self.threaded = threaded_default or bool(self._update_bg)
        self._save_state_fn = namespace.get("save_state")
        self._load_state_fn = namespace.get("load_state")

        if self.threaded and not _numba_available:
            Debug.log_warning(f"Script '{self.name}' uses background updates without numba — may be GIL-bound.", "Scripting")
        Debug.log_info(f"Script '{self.name}' initialized on {type(owner).__name__}. threaded={self.threaded}", "Scripting")

    def set_bg_fps(self, fps: float):
        with self.thread_lock:
            try:
                fps_val = float(fps)
            except Exception:
                return
            self._bg_fps = max(1.0, min(240.0, fps_val))

    def get_bg_dt(self) -> float:
        with self.thread_lock:
            return 1.0 / max(1.0, self._bg_fps)

    def spawn_thread(self, target: Callable, *args, **kwargs) -> Optional[threading.Thread]:
        if not self.running:
            Debug.log_warning(f"Attempted to spawn thread on stopped script '{self.name}'", "Scripting")
            return None
        with self.thread_lock:
            if len(self._user_threads) > 16:
                Debug.log_error(f"Script '{self.name}' exceeded thread limit (16). Ignoring spawn.", "Scripting")
                return None
        t = threading.Thread(target=self._thread_wrapper, args=(target, args, kwargs), daemon=True)
        with self.thread_lock:
            self._user_threads.append(t)
        t.start()
        return t

    def _thread_wrapper(self, target: Callable, args, kwargs):
        try:
            target(*args, **kwargs)
        except Exception:
            Debug.log_exception(f"User thread in script '{self.name}' crashed: {traceback.format_exc()}", "Scripting")
        finally:
            with self.thread_lock:
                current = threading.current_thread()
                if current in self._user_threads:
                    self._user_threads.remove(current)

    def start(self):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self._last_bg_time = time.perf_counter()
        gizmos_mgr = get_gizmos()
        if gizmos_mgr:
            gizmos_mgr.scripts_paused = False
        try:
            if self._start_fn:
                self._start_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' start() error: {traceback.format_exc()}", "Scripting")
        if self.threaded and self._update_bg:
            self.thread = threading.Thread(target=self._bg_loop, daemon=True)
            self.thread.start()

    @profile("update", "scripting")
    def update(self, dt: float):
        if not self.running or not self._update_main:
            return
        try:
            self._update_main(dt)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' update() error: {traceback.format_exc()}", "Scripting")

    def stop(self):
        if not self.running:
            return
        if getattr(self, 'preserve_gizmos', True):
            gizmos_mgr = get_gizmos()
            if gizmos_mgr:
                gizmos_mgr.scripts_paused = True
            # if gizmos_mgr:
            #     persistent_temp = [g for g in gizmos_mgr.gizmos if g.duration == -1]
            #     gizmos_mgr.persistent_gizmos.extend(persistent_temp)
            #     gizmos_mgr.gizmos[:] = [g for g in gizmos_mgr.gizmos if g.duration != -1]
        self.running = False
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(0.5)
        with self.thread_lock:
            threads = [t for t in self._user_threads if t.is_alive()]
        for t in threads:
            t.join(0.1)
        with self.thread_lock:
            self._user_threads = [t for t in self._user_threads if t.is_alive()]
        try:
            if self._stop_fn:
                self._stop_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' stop() error: {traceback.format_exc()}", "Scripting")

    def get_serializable_state(self) -> dict:
        if self._save_state_fn:
            try:
                user_state = self._save_state_fn()
                if isinstance(user_state, dict):
                    return user_state
                else:
                    Debug.log_warning(f"save_state() in '{self.name}' must return dict; got {type(user_state)}. Ignored.", "Scripting")
            except Exception as e:
                Debug.log_exception(f"Error in save_state() of '{self.name}': {e}", "Scripting")
        return {}

    def restore_state(self, state: dict):
        if self._load_state_fn:
            try:
                self._load_state_fn(state)
            except Exception as e:
                Debug.log_exception(f"Error in load_state() of '{self.name}': {e}", "Scripting")

    def _bg_loop(self):
        self._last_bg_time = time.perf_counter()
        while self.running and not self._stop_event.is_set():
            now = time.perf_counter()
            dt_target = self.get_bg_dt()
            if self._update_bg:
                try:
                    self._update_bg(dt_target)
                except Exception:
                    Debug.log_exception(f"Script '{self.name}' background update error: {traceback.format_exc()}", "Scripting")
            elapsed = time.perf_counter() - now
            sleep_time = max(0.0, dt_target - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _recompile(self, new_code: str):
        self.code = new_code
        namespace = self._build_namespace()
        try:
            exec(self.code, namespace, namespace)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' recompilation error: {traceback.format_exc()}", "Scripting")
            return
        self._update_functions_from_namespace(namespace)

    def _build_namespace(self):
        def threaded(fn):
            def wrapper(*args, **kwargs):
                return self.spawn_thread(fn, *args, **kwargs)

            wrapper._is_user_threaded = True
            wrapper._original = fn
            return wrapper

        return {
            "owner": self.owner,
            "Gizmos": Gizmos,
            "Debug": Debug,
            "synthesizer": synthesizer,
            "pymunk": pymunk,
            "time": time,
            "math": math,
            "random": random,
            "threading": threading,
            "pygame": pygame,
            "self": self,
            "traceback": traceback,
            "profile": profile,
            "thread_lock": self.thread_lock,
            "spawn_thread": self.spawn_thread,
            "log": lambda msg: Debug.log_info(str(msg), "UserScript"),
            "set_bg_fps": self.set_bg_fps,
            "threaded": threaded,
            "np": np,
            "njit": njit,
            "Optional": Optional,
            "Any": Any,
            "Callable": Callable,
            "TypeVar": TypeVar,
            "Dict": Dict,
            "List": List,
            "Tuple": Tuple,
            "Union": Union,
            "Set": Set,
            "PlotterWindow": PlotterWindow(manager=self.app.ui_manager),
        }

    def _update_functions_from_namespace(self, namespace):
        def _unwrap_if_threaded(obj):
            if getattr(obj, "_is_user_threaded", False):
                orig = getattr(obj, "_original", None)
                if callable(orig):
                    return orig
            return obj

        self._start_fn = _unwrap_if_threaded(namespace.get("start"))
        self._update_main = _unwrap_if_threaded(namespace.get("update"))
        self._update_bg = namespace.get("update_threaded")
        self._stop_fn = _unwrap_if_threaded(namespace.get("stop"))
        self._save_state_fn = namespace.get("save_state")
        self._load_state_fn = namespace.get("load_state")