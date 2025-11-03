import threading
import time
import traceback
import sys
from typing import Optional, Any, Callable, TypeVar, Dict
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos
import pygame
import pymunk
import math
import random

try:
    import numpy as np
except Exception:
    np = None

try:
    from numba import njit
except Exception:
    def njit(cache=True):
        def _decorator(fn):
            return fn
        return _decorator

T = TypeVar('T', bound=Callable)

class ScriptInstance:
    def __init__(self, code: str, owner: Any, name: str = "Unnamed Script", threaded_default: bool = False):
        self.code = code
        self.owner = owner
        self.name = name
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._user_threads: list[threading.Thread] = []
        self.thread_lock = threading.RLock()
        self._bg_fps = 60.0
        self._stop_event = threading.Event()
        self._last_bg_time = None

        def threaded(fn: T) -> T:
            def wrapper(*args, **kwargs):
                if not self.running:
                    Debug.log_warning(f"Function '{fn.__name__}' called outside running ScriptInstance '{self.name}'", "Scripting")
                    return None
                Debug.log_info(f"Spawning user thread for {fn.__name__} in script '{self.name}'", "Scripting")
                return self.spawn_thread(fn, *args, **kwargs)
            wrapper._is_user_threaded = True
            wrapper._original = fn
            return wrapper  # type: ignore

        namespace: Dict[str, Any] = {
            "owner": owner,
            "Gizmos": Gizmos,
            "Debug": Debug,
            "pymunk": pymunk,
            "time": time,
            "math": math,
            "random": random,
            "threading": threading,
            "pygame": pygame,
            "self": self,
            "traceback": traceback,
            "thread_lock": self.thread_lock,
            "spawn_thread": self.spawn_thread,
            "log": lambda msg: Debug.log_info(str(msg), "UserScript"),
            "set_bg_fps": self.set_bg_fps,
            "threaded": threaded,
            "np": np,
            "njit": njit
        }

        try:
            exec(self.code, namespace, namespace)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' compilation error: {traceback.format_exc()}", "Scripting")
            namespace = {}

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
        Debug.log_info(f"Script '{self.name}' initialized on {type(owner).__name__}. threaded={self.threaded}", "Scripting")

    def set_bg_fps(self, fps: float):
        with self.thread_lock:
            try:
                fps_val = float(fps)
            except Exception:
                return
            self._bg_fps = max(1.0, min(sys.float_info.max, fps_val))

    def get_bg_dt(self) -> float:
        with self.thread_lock:
            fps = max(1.0, self._bg_fps)
            return 1.0 / fps

    def spawn_thread(self, target: Callable, *args, **kwargs) -> Optional[threading.Thread]:
        if not self.running:
            Debug.log_warning(f"Attempted to spawn thread on stopped script '{self.name}'", "Scripting")
            return None
        t = threading.Thread(target=self._thread_wrapper, args=(target, args, kwargs), daemon=True)
        with self.thread_lock:
            self._user_threads.append(t)
        t.start()
        Debug.log_info(f"Spawned thread {t.name} for script '{self.name}'", "Scripting")
        return t

    def _thread_wrapper(self, target: Callable, args, kwargs):
        try:
            target(*args, **kwargs)
        except Exception:
            Debug.log_exception(f"User thread in script '{self.name}' crashed: {traceback.format_exc()}", "Scripting")
        finally:
            with self.thread_lock:
                try:
                    current = threading.current_thread()
                    if current in self._user_threads:
                        self._user_threads.remove(current)
                except Exception:
                    pass

    def start(self):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self._last_bg_time = time.perf_counter()
        try:
            if self._start_fn:
                self._start_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' start() error: {traceback.format_exc()}", "Scripting")
        if self.threaded and self._update_bg:
            self.thread = threading.Thread(target=self._bg_loop, daemon=True)
            self.thread.start()
            Debug.log_info(f"Background thread started for script '{self.name}'", "Scripting")

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
        self.running = False
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(0.5)
        with self.thread_lock:
            threads = list(self._user_threads)
        for t in threads:
            try:
                if t.is_alive():
                    t.join(0.1)
            except Exception:
                pass
        with self.thread_lock:
            self._user_threads = [t for t in self._user_threads if t.is_alive()]
        try:
            if self._stop_fn:
                self._stop_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' stop() error: {traceback.format_exc()}", "Scripting")
        Debug.log_info(f"Script '{self.name}' stopped", "Scripting")

    def _bg_loop(self):
        self._last_bg_time = time.perf_counter()
        while self.running and not self._stop_event.is_set():
            now = time.perf_counter()
            elapsed = now - self._last_bg_time
            self._last_bg_time = now
            dt_target = self.get_bg_dt()
            if not self._update_bg:
                time.sleep(dt_target)
                continue
            remaining = elapsed
            frame_accum = 0.0
            max_frame = 0.2
            try:
                while remaining > 0 and frame_accum < max_frame and self.running:
                    step = min(remaining, dt_target)
                    try:
                        self._update_bg(step)
                    except Exception:
                        Debug.log_exception(f"Script '{self.name}' background update error: {traceback.format_exc()}", "Scripting")
                    remaining -= step
                    frame_accum += step
            except Exception:
                Debug.log_exception(f"Script '{self.name}' bg loop exception: {traceback.format_exc()}", "Scripting")
            after = time.perf_counter()
            took = after - now
            sleep_time = max(0.0, dt_target - took)
            if sleep_time > 0:
                time.sleep(sleep_time)
