import threading
import time
from typing import Optional, Any, Dict, Callable
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
        self._user_thread_pool: list[threading.Thread] = []
        self.globals = {
            "owner": owner,
            "Gizmos": Gizmos,
            "Debug": Debug,
            "pymunk": pymunk,
            "math": math,
            "random": random,
            "threading": threading,
            "pygame": pygame,
            "script": self,
            "thread_lock": self.thread_lock, "spawn_thread": self.spawn_thread,
            "log": lambda msg: Debug.log_info(str(msg), "UserScript")
        }
        self.locals = {}
        exec(self.code, self.globals, self.locals)
        self._start_fn = self.locals.get("start")
        self._update_main = self.locals.get("update")
        self._update_bg = self.locals.get("update_threaded")
        self._stop_fn = self.locals.get("stop")
        self.threaded = threaded or bool(self._update_bg)
        Debug.log_info(f"Script '{self.name}' initialized on {type(owner).__name__}.", "Scripting")

    def spawn_thread(self, target: Callable, *args, **kwargs) -> threading.Thread:
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        self._user_thread_pool.append(t)
        t.start()
        return t

    def start(self):
        if self.running: return
        self.running = True
        if self.threaded and (self._update_bg or self._update_main):
            self.thread = threading.Thread(target=self._bg_loop, daemon=True)
            self.thread.start()
        if self._start_fn:
            try: self._start_fn()
            except Exception as e: Debug.log_exception(f"Script '{self.name}' start() error: {e}", "Scripting")

    def update(self, dt: float):
        if not self.running: return
        if self._update_main:
            try: self._update_main(dt)
            except Exception as e: Debug.log_exception(f"Script '{self.name}' update() error: {e}", "Scripting")

    def stop(self):
        if not self.running: return
        self.running = False
        for t in self._user_thread_pool:
            if t.is_alive(): t.join(0.5)
        if self.thread and self.thread.is_alive(): self.thread.join(0.5)
        if self._stop_fn:
            try: self._stop_fn()
            except Exception as e: Debug.log_exception(f"Script '{self.name}' stop() error: {e}", "Scripting")

    def _bg_loop(self):
        fps = getattr(self, 'bg_fps', 100)
        dt = 1.0 / max(1, fps)
        while self.running:
            fn = self._update_bg or self._update_main
            if fn:
                try: fn(dt)
                except Exception as e: Debug.log_exception(f"Script '{self.name}' bg update error: {e}", "Scripting")
            time.sleep(dt)