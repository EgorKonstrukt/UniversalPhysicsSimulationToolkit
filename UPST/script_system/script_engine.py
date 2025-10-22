import sys
import io
import threading
import asyncio
import traceback
import types
import importlib.util
from typing import Dict, Any, Optional, Callable, List, Tuple
import queue
import time
import pickle
import os
from contextlib import redirect_stdout, redirect_stderr
import math
import random
import pygame
import pymunk


class ScriptContext:
    def __init__(self, script_engine):
        self.script_engine = script_engine
        self.physics_manager = script_engine.physics_manager
        self.ui_manager = script_engine.ui_manager
        self.camera = script_engine.camera
        self.spawner = script_engine.spawner
        self.sound_manager = script_engine.sound_manager
        self.synthesizer = script_engine.synthesizer
        self.gizmos = script_engine.gizmos
        self.debug = script_engine.debug
        self.save_load_manager = script_engine.save_load_manager
        self.input_handler = script_engine.input_handler
        self.console = script_engine.console

    def spawn_circle(self, position, radius=30, **kwargs):
        return self.spawner.spawn_circle(position, radius, **kwargs)

    def spawn_rectangle(self, position, size=(30, 30), **kwargs):
        return self.spawner.spawn_rectangle(position, size, **kwargs)

    def spawn_triangle(self, position, size=30, **kwargs):
        return self.spawner.spawn_triangle(position, size, **kwargs)

    def spawn_polygon(self, position, vertices=None, **kwargs):
        if hasattr(self.spawner, "spawn_polygon"):
            if vertices is None:
                raise ValueError("vertices required for spawn_polygon")
            return self.spawner.spawn_polygon(position, vertices, **kwargs)
        if hasattr(self.spawner, "spawn_polyhedron"):
            return self.spawner.spawn_polyhedron(position, **kwargs)
        raise AttributeError("No polygon spawn method available")

    def spawn_chain(self, start_pos, end_pos, segments=10, segment_mass=0.5, joint_stiffness=1000):
        if hasattr(self.spawner, "spawn_chain"):
            return self.spawner.spawn_chain(start_pos, end_pos, segments, segment_mass, joint_stiffness)
        raise AttributeError("Spawner has no spawn_chain")

    def play_note(self, note, duration=1.0, **kwargs):
        return self.synthesizer.play_note(note, duration, **kwargs)

    def play_frequency(self, freq, duration=1.0, **kwargs):
        return self.synthesizer.play_frequency(freq, duration, **kwargs)

    def draw_line(self, start, end, color='white', width=2, **kwargs):
        return self.gizmos.draw_line(start, end, color, width, **kwargs)

    def draw_circle(self, center, radius, color='white', filled=False, **kwargs):
        return self.gizmos.draw_circle(center, radius, color, filled, **kwargs)

    def draw_polygon(self, points, color='white', filled=False, width=2, **kwargs):
        if hasattr(self.gizmos, "draw_polygon"):
            return self.gizmos.draw_polygon(points, color, filled, width, **kwargs)
        raise AttributeError("Gizmos has no draw_polygon")

    def draw_text(self, text, position, color='white', **kwargs):
        return self.gizmos.draw_text(text, position, color, **kwargs)

    def clear_gizmos(self):
        if hasattr(self.gizmos, "clear_all"):
            self.gizmos.clear_all()

    def show_message(self, msg):
        if hasattr(self.console, "add_output_line_to_log"):
            self.console.add_output_line_to_log(str(msg))

    def log(self, message, category="Script"):
        if hasattr(self.debug, "log"):
            self.debug.log(message, category)

    def get_mouse_pos(self):
        return self.camera.screen_to_world(pygame.mouse.get_pos())

    def get_bodies(self):
        return list(self.physics_manager.space.bodies)

    def delete_all_bodies(self):
        self.physics_manager.delete_all()

    def set_gravity(self, gravity):
        self.physics_manager.space.gravity = gravity

    def get_gravity(self):
        return tuple(self.physics_manager.space.gravity)

    def pause(self):
        self.physics_manager.toggle_pause()

    def resume(self):
        if not self.physics_manager.running_physics:
            self.physics_manager.toggle_pause()

    def step(self, dt=None):
        if dt is None:
            dt = 1.0 / max(1, getattr(self.physics_manager, "simulation_frequency", 60))
        self.physics_manager.step(dt)

    def set_simulation_frequency(self, hz: int):
        self.physics_manager.set_simulation_frequency(hz)

    def set_iterations(self, iters: int):
        self.physics_manager.set_iterations(iters)

    def set_damping(self, linear: float = 1.0, angular: float = 0.0):
        self.physics_manager.set_damping(linear, angular)

    def raycast(self, a, b, radius: float = 0.0, mask: pymunk.ShapeFilter = None):
        return self.physics_manager.raycast(a, b, radius, mask)

    def overlap_aabb(self, bb, mask: pymunk.ShapeFilter = None):
        return self.physics_manager.overlap_aabb(bb, mask)

    def shapecast(self, shape: pymunk.Shape, transform: pymunk.Transform = None):
        return self.physics_manager.shapecast(shape, transform)

    def enable_ccd(self, target, enabled: bool = True):
        self.physics_manager.enable_ccd(target, enabled)

    def create_joint(self, joint_type: str, body_a: pymunk.Body, body_b: pymunk.Body, **kwargs):
        t = joint_type.lower()
        if t in ("pin", "rigid"):
            a = kwargs.get("anchor_a", (0, 0))
            b = kwargs.get("anchor_b", (0, 0))
            j = pymunk.PinJoint(body_a, body_b, a, b)
        elif t == "pivot":
            p = kwargs.get("anchor", (0, 0))
            j = pymunk.PivotJoint(body_a, body_b, p)
        elif t == "spring":
            a = kwargs.get("anchor_a", (0, 0))
            b = kwargs.get("anchor_b", (0, 0))
            r = kwargs.get("rest_length", 100.0)
            k = kwargs.get("stiffness", 1000.0)
            d = kwargs.get("damping", 10.0)
            j = pymunk.DampedSpring(body_a, body_b, a, b, r, k, d)
        elif t == "motor":
            rate = kwargs.get("rate", 2.0)
            j = pymunk.SimpleMotor(body_a, body_b, rate)
        elif t == "gear":
            phase = kwargs.get("phase", 0.0)
            ratio = kwargs.get("ratio", 1.0)
            j = pymunk.GearJoint(body_a, body_b, phase, ratio)
        elif t == "slide":
            a = kwargs.get("anchor_a", (0, 0))
            b = kwargs.get("anchor_b", (0, 0))
            mn = kwargs.get("min", 10.0)
            mx = kwargs.get("max", 30.0)
            j = pymunk.SlideJoint(body_a, body_b, a, b, mn, mx)
        elif t in ("rotarylimit", "rotary_limit"):
            mn = kwargs.get("min", -0.5)
            mx = kwargs.get("max", 0.5)
            j = pymunk.RotaryLimitJoint(body_a, body_b, mn, mx)
        else:
            raise ValueError(f"Unknown joint type: {joint_type}")
        self.physics_manager.add_constraint(j)
        return j

    def create_motor(self, a, b, rate=2.0):
        j = pymunk.SimpleMotor(a, b, rate)
        self.physics_manager.add_constraint(j)
        return j

    def create_gear(self, a, b, phase=0.0, ratio=1.0):
        j = pymunk.GearJoint(a, b, phase, ratio)
        self.physics_manager.add_constraint(j)
        return j

    def create_slide(self, a, b, anchor_a, anchor_b, min_d, max_d):
        j = pymunk.SlideJoint(a, b, anchor_a, anchor_b, min_d, max_d)
        self.physics_manager.add_constraint(j)
        return j

    def create_rotary_limit(self, a, b, min_angle, max_angle):
        j = pymunk.RotaryLimitJoint(a, b, min_angle, max_angle)
        self.physics_manager.add_constraint(j)
        return j


class ScriptOutput:
    def __init__(self):
        self.output = []
        self.errors = []

    def write(self, text):
        if text:
            self.output.append(text)

    def flush(self):
        pass

    def get_output(self):
        return ''.join(self.output)

    def clear(self):
        self.output.clear()
        self.errors.clear()


class ScriptEngine:
    def __init__(self, physics_manager, ui_manager, camera, spawner, sound_manager, synthesizer, gizmos, debug, save_load_manager, input_handler, console):
        self.physics_manager = physics_manager
        self.ui_manager = ui_manager
        self.camera = camera
        self.spawner = spawner
        self.sound_manager = sound_manager
        self.synthesizer = synthesizer
        self.gizmos = gizmos
        self.debug = debug
        self.save_load_manager = save_load_manager
        self.input_handler = input_handler
        self.console = console
        self.context = ScriptContext(self)
        self.running_scripts: Dict[str, Dict[str, Any]] = {}
        self.script_threads: Dict[str, threading.Thread] = {}
        self.script_outputs: Dict[str, Dict[str, Any]] = {}
        self.global_namespace = self._create_global_namespace()
        self.async_loop: Optional[asyncio.AbstractEventLoop] = None
        self.async_thread: Optional[threading.Thread] = None
        self._start_async_loop()

    def _create_global_namespace(self):
        ns = {
            '__builtins__': __builtins__,
            'math': math,
            'random': random,
            'time': time,
            'pygame': pygame,
            'pymunk': pymunk,
            'context': self.context,
            'spawn_circle': self.context.spawn_circle,
            'spawn_rectangle': self.context.spawn_rectangle,
            'spawn_triangle': self.context.spawn_triangle,
            'spawn_polygon': self.context.spawn_polygon,
            'spawn_chain': self.context.spawn_chain,
            'play_note': self.context.play_note,
            'play_frequency': self.context.play_frequency,
            'draw_line': self.context.draw_line,
            'draw_circle': self.context.draw_circle,
            'draw_polygon': self.context.draw_polygon,
            'draw_text': self.context.draw_text,
            'clear_gizmos': self.context.clear_gizmos,
            'show_message': self.context.show_message,
            'log': self.context.log,
            'get_mouse_pos': self.context.get_mouse_pos,
            'get_bodies': self.context.get_bodies,
            'delete_all_bodies': self.context.delete_all_bodies,
            'set_gravity': self.context.set_gravity,
            'get_gravity': self.context.get_gravity,
            'pause': self.context.pause,
            'resume': self.context.resume,
            'step': self.context.step,
            'set_simulation_frequency': self.context.set_simulation_frequency,
            'set_iterations': self.context.set_iterations,
            'set_damping': self.context.set_damping,
            'raycast': self.context.raycast,
            'overlap_aabb': self.context.overlap_aabb,
            'shapecast': self.context.shapecast,
            'enable_ccd': self.context.enable_ccd,
            'create_joint': self.context.create_joint,
            'create_motor': self.context.create_motor,
            'create_gear': self.context.create_gear,
            'create_slide': self.context.create_slide,
            'create_rotary_limit': self.context.create_rotary_limit,
        }
        try:
            import numpy as np
            ns['numpy'] = np
            ns['np'] = np
        except Exception:
            pass
        return ns

    def _start_async_loop(self):
        def run_loop():
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()
        t = threading.Thread(target=run_loop, daemon=True)
        t.start()
        self.async_thread = t

    def execute_script(self, script_id: str, code: str, async_execution: bool = False) -> Dict[str, Any]:
        if async_execution:
            return self._execute_async(script_id, code)
        return self._execute_sync(script_id, code)

    def _execute_sync(self, script_id: str, code: str) -> Dict[str, Any]:
        output = ScriptOutput()
        result = {'success': False, 'output': '', 'error': '', 'execution_time': 0.0}
        start = time.time()
        try:
            local_ns = self.global_namespace.copy()
            with redirect_stdout(output), redirect_stderr(output):
                compiled = compile(code, f"<script_{script_id}>", "exec")
                exec(compiled, local_ns)
            result['success'] = True
            result['output'] = output.get_output()
        except Exception as e:
            result['error'] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        result['execution_time'] = time.time() - start
        self.script_outputs[script_id] = result
        return result

    def _execute_async(self, script_id: str, code: str) -> Dict[str, Any]:
        if script_id in self.running_scripts:
            self.stop_script(script_id)
        def run_script():
            try:
                res = self._execute_sync(script_id, code)
                self.running_scripts[script_id] = {'status': 'completed', 'result': res}
            except Exception as e:
                self.running_scripts[script_id] = {'status': 'error', 'error': str(e)}
        t = threading.Thread(target=run_script, daemon=True)
        t.start()
        self.script_threads[script_id] = t
        self.running_scripts[script_id] = {'status': 'running', 'thread': t}
        return {'success': True, 'message': f"Script {script_id} started asynchronously"}

    def stop_script(self, script_id: str) -> bool:
        if script_id in self.running_scripts:
            info = self.running_scripts[script_id]
            if info.get('status') == 'running' and 'thread' in info:
                del self.running_scripts[script_id]
                if script_id in self.script_threads:
                    del self.script_threads[script_id]
                return True
        return False

    def get_script_status(self, script_id: str) -> Dict[str, Any]:
        if script_id in self.running_scripts:
            return self.running_scripts[script_id]
        if script_id in self.script_outputs:
            return {'status': 'completed', 'result': self.script_outputs[script_id]}
        return {'status': 'not_found'}

    def list_running_scripts(self) -> List[str]:
        return [sid for sid, info in self.running_scripts.items() if info.get('status') == 'running']

    def clear_outputs(self):
        self.script_outputs.clear()

    def update(self, dt):
        completed = []
        for sid, info in list(self.running_scripts.items()):
            t = info.get('thread')
            if info.get('status') == 'running' and isinstance(t, threading.Thread) and not t.is_alive():
                completed.append(sid)
        for sid in completed:
            if sid in self.script_threads:
                del self.script_threads[sid]
            self.running_scripts[sid] = {'status': 'completed', 'result': self.script_outputs.get(sid, {'success': True, 'output': '', 'error': '', 'execution_time': 0.0})}

    def shutdown(self):
        if self.async_loop:
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)
        for sid in list(self.running_scripts.keys()):
            self.stop_script(sid)
