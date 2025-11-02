import threading, time, traceback, sys
from typing import Optional, Any, Callable
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos
import pygame, pymunk, math, random

class ScriptInstance:
    def __init__(self, code: str, owner: Any, name: str = "Unnamed Script", threaded: bool = False):
        self.code = code
        self.owner = owner
        self.name = name
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.thread_lock = threading.Lock()
        self._user_threads: list[threading.Thread] = []
        self._bg_fps = 60.0
        self.globals = {
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
            "set_bg_fps": self.set_bg_fps
        }
        self.locals = {}
        try: exec(self.code, self.globals, self.locals)
        except Exception as e: Debug.log_exception(f"Script '{self.name}' compilation error: {traceback.format_exc()}", "Scripting")
        self._start_fn = self.locals.get("start")
        self._update_main = self.locals.get("update")
        self._update_bg = self.locals.get("update_threaded")
        self._stop_fn = self.locals.get("stop")
        self.threaded = threaded or bool(self._update_bg)
        Debug.log_info(f"Script '{self.name}' initialized on {type(owner).__name__}.", "Scripting")
        self._ensure_safe_state()

    def _ensure_safe_state(self):
        if not hasattr(self, '_projected'): self._projected = []
        if not hasattr(self, 'phase'): self.phase = 0.0
        if not hasattr(self, 'position'): self.position = (0.0, 0.0)

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
        if self.running:
            return
        self.running = True
        try:
            if self._start_fn:
                self._start_fn()
        except Exception as e:
            Debug.log_exception(f"Script '{self.name}' start() error: {traceback.format_exc()}", "Scripting")
        if self.threaded and (self._update_bg or self._update_main):
            self.thread = threading.Thread(target=self._bg_loop, daemon=True)
            self.thread.start()
    def update(self, dt: float):
        if not self.running or not self._update_main: return
        try: self._update_main(dt)
        except Exception as e: Debug.log_exception(f"Script '{self.name}' update() error: {traceback.format_exc()}", "Scripting")

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
        except Exception as e: Debug.log_exception(f"Script '{self.name}' stop() error: {traceback.format_exc()}", "Scripting")

    def _bg_loop(self):
        last_time = time.perf_counter()
        while self.running:
            current_time = time.perf_counter()
            elapsed = current_time - last_time
            last_time = current_time
            dt = self.get_bg_dt()
            frame_time = 0.0
            fn = self._update_bg or self._update_main
            if fn:
                while elapsed > 0 and frame_time < 0.2 and self.running:
                    step = min(elapsed, dt)
                    try: fn(step)
                    except Exception as e: Debug.log_exception(f"Script '{self.name}' bg update error: {traceback.format_exc()}", "Scripting")
                    elapsed -= step
                    frame_time += step
            sleep_time = dt - (time.perf_counter() - last_time)
            if sleep_time > 0: time.sleep(sleep_time)