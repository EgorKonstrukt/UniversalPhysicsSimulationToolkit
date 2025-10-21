import sys
import io
import threading
import asyncio
import traceback
import types
import importlib.util
from typing import Dict, Any, Optional, Callable, List
import queue
import time
import pickle
import os
from contextlib import redirect_stdout, redirect_stderr


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
        
    def play_note(self, note, duration=1.0, **kwargs):
        return self.synthesizer.play_note(note, duration, **kwargs)
        
    def play_frequency(self, freq, duration=1.0, **kwargs):
        return self.synthesizer.play_frequency(freq, duration, **kwargs)
        
    def draw_line(self, start, end, color='white', width=2, **kwargs):
        return self.gizmos.draw_line(start, end, color, width, **kwargs)
        
    def draw_circle(self, center, radius, color='white', filled=False, **kwargs):
        return self.gizmos.draw_circle(center, radius, color, filled, **kwargs)
        
    def draw_text(self, text, position, color='white', **kwargs):
        return self.gizmos.draw_text(text, position, color, **kwargs)
        
    def log(self, message, category="Script"):
        self.debug.log(message, category)
        
    def get_mouse_pos(self):
        return self.input_handler.get_mouse_world_pos()
        
    def get_bodies(self):
        return list(self.physics_manager.space.bodies)
        
    def delete_all_bodies(self):
        self.physics_manager.delete_all()


class ScriptOutput:
    def __init__(self):
        self.output = []
        self.errors = []
        
    def write(self, text):
        if text.strip():
            self.output.append(text)
            
    def flush(self):
        pass
        
    def get_output(self):
        return ''.join(self.output)
        
    def clear(self):
        self.output.clear()
        self.errors.clear()


class ScriptEngine:
    def __init__(self, physics_manager, ui_manager, camera, spawner, sound_manager, 
                 synthesizer, gizmos, debug, save_load_manager, input_handler, console):
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
        self.running_scripts = {}
        self.script_threads = {}
        self.script_outputs = {}
        self.global_namespace = self._create_global_namespace()
        
        self.async_loop = None
        self.async_thread = None
        self._start_async_loop()
        
    def _create_global_namespace(self):
        namespace = {
            '__builtins__': __builtins__,
            'math': __import__('math'),
            'random': __import__('random'),
            'time': __import__('time'),
            'numpy': None,
            'pygame': None,
            'pymunk': None,
            'context': self.context,
            'spawn_circle': self.context.spawn_circle,
            'spawn_rectangle': self.context.spawn_rectangle,
            'spawn_triangle': self.context.spawn_triangle,
            'play_note': self.context.play_note,
            'play_frequency': self.context.play_frequency,
            'draw_line': self.context.draw_line,
            'draw_circle': self.context.draw_circle,
            'draw_text': self.context.draw_text,
            'log': self.context.log,
            'get_mouse_pos': self.context.get_mouse_pos,
            'get_bodies': self.context.get_bodies,
            'delete_all_bodies': self.context.delete_all_bodies,
        }
        
        try:
            import numpy as np
            namespace['numpy'] = np
            namespace['np'] = np
        except ImportError:
            pass
            
        try:
            import pygame
            namespace['pygame'] = pygame
        except ImportError:
            pass
            
        try:
            import pymunk
            namespace['pymunk'] = pymunk
        except ImportError:
            pass
            
        return namespace
        
    def _start_async_loop(self):
        def run_loop():
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()
            
        self.async_thread = threading.Thread(target=run_loop, daemon=True)
        self.async_thread.start()
        
    def execute_script(self, script_id: str, code: str, async_execution: bool = False) -> Dict[str, Any]:
        if async_execution:
            return self._execute_async(script_id, code)
        else:
            return self._execute_sync(script_id, code)
            
    def _execute_sync(self, script_id: str, code: str) -> Dict[str, Any]:
        output = ScriptOutput()
        result = {
            'success': False,
            'output': '',
            'error': '',
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            local_namespace = self.global_namespace.copy()
            
            with redirect_stdout(output), redirect_stderr(output):
                compiled_code = compile(code, f"<script_{script_id}>", 'exec')
                exec(compiled_code, local_namespace)
                
            result['success'] = True
            result['output'] = output.get_output()
            
        except Exception as e:
            result['error'] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            
        result['execution_time'] = time.time() - start_time
        self.script_outputs[script_id] = result
        
        return result
        
    def _execute_async(self, script_id: str, code: str) -> Dict[str, Any]:
        if script_id in self.running_scripts:
            self.stop_script(script_id)
            
        def run_script():
            try:
                result = self._execute_sync(script_id, code)
                self.running_scripts[script_id] = {
                    'status': 'completed',
                    'result': result
                }
            except Exception as e:
                self.running_scripts[script_id] = {
                    'status': 'error',
                    'error': str(e)
                }
                
        thread = threading.Thread(target=run_script, daemon=True)
        thread.start()
        
        self.script_threads[script_id] = thread
        self.running_scripts[script_id] = {
            'status': 'running',
            'thread': thread
        }
        
        return {'success': True, 'message': f'Script {script_id} started asynchronously'}
        
    def stop_script(self, script_id: str) -> bool:
        if script_id in self.running_scripts:
            script_info = self.running_scripts[script_id]
            if script_info['status'] == 'running' and 'thread' in script_info:
                # Note: Python doesn't have a clean way to stop threads
                # This is a limitation we'll document
                del self.running_scripts[script_id]
                if script_id in self.script_threads:
                    del self.script_threads[script_id]
                return True
        return False
        
    def get_script_status(self, script_id: str) -> Dict[str, Any]:
        if script_id in self.running_scripts:
            return self.running_scripts[script_id]
        elif script_id in self.script_outputs:
            return {
                'status': 'completed',
                'result': self.script_outputs[script_id]
            }
        else:
            return {'status': 'not_found'}
            
    def list_running_scripts(self) -> List[str]:
        return [sid for sid, info in self.running_scripts.items() 
                if info['status'] == 'running']
                
    def clear_outputs(self):
        self.script_outputs.clear()
        
    def update(self, dt):
        completed_scripts = []
        for script_id, info in self.running_scripts.items():
            if info['status'] == 'running' and 'thread' in info:
                if not info['thread'].is_alive():
                    completed_scripts.append(script_id)
                    
        for script_id in completed_scripts:
            if script_id in self.script_threads:
                del self.script_threads[script_id]
                
    def shutdown(self):
        if self.async_loop:
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)
        
        for script_id in list(self.running_scripts.keys()):
            self.stop_script(script_id)

