import threading
import time
from typing import Optional, Any, Dict
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.modules.profiler import profile
from UPST.sound.sound_synthesizer import synthesizer
from UPST.config import config
import pygame
import pymunk
import math
import random

class ScriptInstance:
    def __init__(self, code: str, owner: Any, name: str = "Unnamed Script", threaded: bool = False):
        self.code = code
        self.owner = owner
        self.name = name
        self.threaded = threaded
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.globals = {"owner": owner, "Gizmos": Gizmos, "Debug": Debug, "pymunk": pymunk, "math": math, "random": random, "pygame": pygame, "log": lambda msg: Debug.log_info(str(msg), "UserScript"), "script": self}
        self.locals = {}
        exec(self.code, self.globals, self.locals)
        self._start_fn = self.locals.get("start")
        self._update_fn = self.locals.get("update")
        self._stop_fn = self.locals.get("stop")
        Debug.log_info(f"Script '{self.name}' initialized on {type(owner).__name__}.", "Scripting")

    def start(self):
        if self.running: return
        self.running = True
        if self.threaded:
            self.thread = threading.Thread(target=self._threaded_loop, daemon=True)
            self.thread.start()
        else:
            if self._start_fn:
                try: self._start_fn()
                except Exception as e: Debug.log_exception(f"Error in script '{self.name}' start(): {e}", "Scripting")

    def update(self, dt: float = 0.0):
        if not self.running or self.threaded: return
        if self._update_fn:
            try: self._update_fn(dt)
            except Exception as e: Debug.log_exception(f"Error in script '{self.name}' update(): {e}", "Scripting")

    def stop(self):
        if not self.running: return
        self.running = False
        if self.thread and self.thread.is_alive(): self.thread.join(timeout=1.0)
        if not self.threaded and self._stop_fn:
            try: self._stop_fn()
            except Exception as e: Debug.log_exception(f"Error in script '{self.name}' stop(): {e}", "Scripting")

    def _threaded_loop(self):
        if self._start_fn:
            try: self._start_fn()
            except Exception as e: Debug.log_exception(f"Error in threaded script '{self.name}' start(): {e}", "Scripting")
        while self.running:
            if self._update_fn:
                try: self._update_fn(1.0/100.0)
                except Exception as e: Debug.log_exception(f"Error in threaded script '{self.name}' update(): {e}", "Scripting")
            time.sleep(1.0/100.0)
        if self._stop_fn:
            try: self._stop_fn()
            except Exception as e: Debug.log_exception(f"Error in threaded script '{self.name}' stop(): {e}", "Scripting")
