import threading, time, traceback, sys
from typing import Optional, Any, Callable, TypeVar
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos
import pygame, pymunk, math, random

T = TypeVar('T', bound=Callable)

def threaded(fn: T) -> T:
    def wrapper(*args, **kwargs):
        script_obj = kwargs.get("_script_context")
        if script_obj and isinstance(script_obj, ScriptInstance):
            return script_obj.spawn_thread(fn, *args, **kwargs)
        else:
            Debug.log_warning(f"Function '{fn.__name__}' decorated with @threaded called outside ScriptInstance context", "Scripting")
            return None
    return wrapper  # type: ignore

class ScriptInstance:
    def __init__(self, code: str, owner: Any, name: str = "Unnamed Script", threaded_default: bool = False):
        self.code = code
        self.owner = owner
        self.name = name
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.thread_lock = threading.Lock()
        self._user_threads: list[threading.Thread] = []
        self._bg_fps = 60.0

        def threaded(fn):
            def wrapper(*args, **kwargs):
                if not self.running:
                    Debug.log_warning(f"Script not running", "Scripting")
                    return None
                Debug.log_info(f"Spawning thread for {fn.__name__}", "Scripting")
                t = self.spawn_thread(fn, *args, **kwargs)
                Debug.log_info(f"Thread started: {t}", "Scripting")
                return t
            return wrapper

        namespace = {
            "owner": owner,
            "Gizmos": Gizmos,
            "Debug": Debug,
            "pymunk": pymunk,
            "time": time,
            "math": math,
            "random": random,
            "threading": threading,
            "pygame": pygame,
            "script": self,
            "thread_lock": self.thread_lock,
            "spawn_thread": self.spawn_thread,
            "log": lambda msg: Debug.log_info(str(msg), "UserScript"),
            "set_bg_fps": self.set_bg_fps,
            "threaded": threaded
        }

        try:
            exec(self.code, namespace, namespace)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' compilation error: {traceback.format_exc()}", "Scripting")
            namespace = {}

        self._start_fn = namespace.get("start")
        self._update_main = namespace.get("update")
        self._update_bg = namespace.get("update_threaded")
        self._stop_fn = namespace.get("stop")
        self.threaded = threaded_default or bool(self._update_bg)
        Debug.log_info(f"Script '{self.name}' initialized on {type(owner).__name__}.", "Scripting")

    def set_bg_fps(self, fps: float):
        with self.thread_lock:
            self._bg_fps = max(1.0, min(sys.float_info.max, fps))

    def get_bg_dt(self) -> float:
        with self.thread_lock:
            return 1.0 / max(1.0, self._bg_fps)

    def spawn_thread(self, target: Callable, *args, **kwargs) -> threading.Thread:
        if not self.running:
            Debug.log_warning(f"Attempted to spawn thread on stopped script '{self.name}'", "Scripting")
            return None
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        with self.thread_lock:
            self._user_threads.append(t)
        t.start()
        return t

    def start(self):
        if self.running: return
        self.running = True
        try:
            if self._start_fn: self._start_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' start() error: {traceback.format_exc()}", "Scripting")
        if self.threaded and self._update_bg:
            self.thread = threading.Thread(target=self._bg_loop, daemon=True)
            self.thread.start()

    def update(self, dt: float):
        if not self.running or not self._update_main: return
        try: self._update_main(dt)
        except Exception:
            Debug.log_exception(f"Script '{self.name}' update() error: {traceback.format_exc()}", "Scripting")

    def stop(self):
        if not self.running: return
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(0.5)
        with self.thread_lock:
            for t in self._user_threads:
                if t.is_alive(): t.join(0.1)
            self._user_threads.clear()
        try:
            if self._stop_fn: self._stop_fn()
        except Exception:
            Debug.log_exception(f"Script '{self.name}' stop() error: {traceback.format_exc()}", "Scripting")

    def _bg_loop(self):
        last_time = time.perf_counter()
        while self.running:
            current_time = time.perf_counter()
            elapsed = current_time - last_time
            last_time = current_time
            dt = self.get_bg_dt()
            frame_time = 0.0
            fn = self._update_bg
            if fn:
                while elapsed > 0 and frame_time < 0.2 and self.running:
                    step = min(elapsed, dt)
                    try: fn(step)
                    except Exception:
                        Debug.log_exception(f"Script '{self.name}' bg update error: {traceback.format_exc()}", "Scripting")
                    elapsed -= step
                    frame_time += step
            sleep_time = dt - (time.perf_counter() - last_time)
            if sleep_time > 0: time.sleep(sleep_time)