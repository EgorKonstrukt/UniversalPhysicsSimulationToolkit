import subprocess
import sys
import os
import tempfile
import threading
import time
import socket
import json
from typing import Optional, Dict, Any, Callable
import tkinter as tk
from tkinter import messagebox
import queue


class IDLEBridge:
    def __init__(self, script_engine, on_code_execute: Optional[Callable] = None):
        self.script_engine = script_engine
        self.on_code_execute = on_code_execute
        
        self.idle_process = None
        self.temp_files = []
        self.communication_server = None
        self.server_thread = None
        self.server_port = None
        
        self.code_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        self._setup_communication_server()
        
    def _setup_communication_server(self):
        def server_worker():
            self.communication_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.communication_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.communication_server.bind(('localhost', 0))
            self.server_port = self.communication_server.getsockname()[1]
            self.communication_server.listen(1)
            
            while True:
                try:
                    client, addr = self.communication_server.accept()
                    self._handle_client(client)
                except Exception as e:
                    if self.communication_server:
                        print(f"Server error: {e}")
                    break
                    
        self.server_thread = threading.Thread(target=server_worker, daemon=True)
        self.server_thread.start()
        
        time.sleep(0.1)
        
    def _handle_client(self, client):
        try:
            data = client.recv(4096).decode('utf-8')
            if data:
                message = json.loads(data)
                
                if message['type'] == 'execute_code':
                    code = message['code']
                    script_id = message.get('script_id', 'idle_temp')
                    
                    result = self.script_engine.execute_script(script_id, code, False)
                    
                    response = {
                        'type': 'execution_result',
                        'result': result
                    }
                    
                    client.send(json.dumps(response).encode('utf-8'))
                    
                    if self.on_code_execute:
                        self.on_code_execute(code, result)
                        
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            client.close()
            
    def create_idle_startup_script(self) -> str:
        startup_code = f'''
import socket
import json
import sys

# UPST Game Integration
class UPSTGameBridge:
    def __init__(self):
        self.server_port = {self.server_port}
        
    def execute_in_game(self, code, script_id="idle_temp"):
        """Execute code in the UPST game engine"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', self.server_port))
            
            message = {{
                'type': 'execute_code',
                'code': code,
                'script_id': script_id
            }}
            
            sock.send(json.dumps(message).encode('utf-8'))
            response = sock.recv(4096).decode('utf-8')
            result = json.loads(response)
            
            sock.close()
            
            if result['result']['success']:
                if result['result']['output']:
                    print("Game Output:")
                    print(result['result']['output'])
                print(f"Execution time: {{result['result']['execution_time']:.4f}}s")
            else:
                print("Game Error:")
                print(result['result']['error'])
                
            return result['result']
            
        except Exception as e:
            print(f"Bridge error: {{e}}")
            return {{'success': False, 'error': str(e)}}
            
    def spawn_circle(self, position=(0, 0), radius=30):
        """Spawn a circle in the game"""
        code = f"spawn_circle({position}, radius={radius})"
        return self.execute_in_game(code)
        
    def spawn_rectangle(self, position=(0, 0), size=(30, 30)):
        """Spawn a rectangle in the game"""
        code = f"spawn_rectangle({position}, size={size})"
        return self.execute_in_game(code)
        
    def play_note(self, note, duration=1.0):
        """Play a musical note in the game"""
        code = f"play_note('{note}', {duration})"
        return self.execute_in_game(code)
        
    def draw_line(self, start, end, color='white'):
        """Draw a line in the game"""
        code = f"draw_line({start}, {end}, '{color}')"
        return self.execute_in_game(code)
        
    def get_mouse_pos(self):
        """Get mouse position in game world"""
        code = "mouse_pos = get_mouse_pos(); print(f'Mouse: {{mouse_pos}}')"
        return self.execute_in_game(code)
        
    def clear_all(self):
        """Clear all objects in the game"""
        code = "delete_all_bodies()"
        return self.execute_in_game(code)

# Create global bridge instance
game = UPSTGameBridge()

# Helper functions for quick access
def run_in_game(code):
    """Quick function to run code in game"""
    return game.execute_in_game(code)

def spawn_circle(pos=(0, 0), r=30):
    return game.spawn_circle(pos, r)
    
def spawn_rect(pos=(0, 0), size=(30, 30)):
    return game.spawn_rectangle(pos, size)
    
def play(note, dur=1.0):
    return game.play_note(note, dur)
    
def line(start, end, color='white'):
    return game.draw_line(start, end, color)
    
def mouse():
    return game.get_mouse_pos()
    
def clear():
    return game.clear_all()

print("UPST Game Integration Loaded!")
print("Available commands:")
print("  game.execute_in_game(code) - Execute Python code in game")
print("  spawn_circle(pos, radius) - Spawn circle")
print("  spawn_rect(pos, size) - Spawn rectangle") 
print("  play(note, duration) - Play musical note")
print("  line(start, end, color) - Draw line")
print("  mouse() - Get mouse position")
print("  clear() - Clear all objects")
print("  run_in_game(code) - Quick execute")
print()
'''
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        temp_file.write(startup_code)
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
        
    def launch_idle(self, startup_script: Optional[str] = None):
        if self.idle_process and self.idle_process.poll() is None:
            messagebox.showwarning("IDLE", "IDLE is already running")
            return False
            
        try:
            if startup_script is None:
                startup_script = self.create_idle_startup_script()
                
            # Try different IDLE launch methods
            idle_commands = [
                [sys.executable, '-m', 'idlelib.idle', '-r', startup_script],
                [sys.executable, '-m', 'idlelib', '-r', startup_script],
                ['idle', '-r', startup_script],
                ['idle3', '-r', startup_script],
                ['python', '-m', 'idlelib.idle', '-r', startup_script],
                ['python3', '-m', 'idlelib.idle', '-r', startup_script]
            ]
            
            for cmd in idle_commands:
                try:
                    self.idle_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                    )
                    
                    # Check if process started successfully
                    time.sleep(1)
                    if self.idle_process.poll() is None:
                        print(f"IDLE launched successfully with command: {' '.join(cmd)}")
                        return True
                    else:
                        self.idle_process = None
                        
                except (FileNotFoundError, subprocess.SubprocessError):
                    continue
                    
            messagebox.showerror("IDLE Launch Error", 
                               "Could not launch IDLE. Please ensure Python IDLE is installed.")
            return False
            
        except Exception as e:
            messagebox.showerror("IDLE Launch Error", f"Error launching IDLE: {e}")
            return False
            
    def close_idle(self):
        if self.idle_process:
            try:
                self.idle_process.terminate()
                self.idle_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.idle_process.kill()
            finally:
                self.idle_process = None
                
    def is_idle_running(self) -> bool:
        return self.idle_process is not None and self.idle_process.poll() is None
        
    def send_code_to_idle(self, code: str):
        # This would require more complex integration with IDLE's internals
        # For now, we'll use the bridge communication
        pass
        
    def cleanup(self):
        self.close_idle()
        
        if self.communication_server:
            try:
                self.communication_server.close()
            except:
                pass
                
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
                
        self.temp_files.clear()


class IDLEIntegrationManager:
    def __init__(self, script_engine, ui_manager):
        self.script_engine = script_engine
        self.ui_manager = ui_manager
        
        self.idle_bridge = None
        self.integration_enabled = True
        
        self.executed_codes = []
        self.max_history = 100
        
    def initialize(self):
        if not self.integration_enabled:
            return False
            
        try:
            self.idle_bridge = IDLEBridge(
                self.script_engine,
                on_code_execute=self._on_code_executed
            )
            return True
        except Exception as e:
            print(f"Failed to initialize IDLE integration: {e}")
            return False
            
    def _on_code_executed(self, code: str, result: Dict[str, Any]):
        # Log executed code
        self.executed_codes.append({
            'code': code,
            'result': result,
            'timestamp': time.time()
        })
        
        # Keep history limited
        if len(self.executed_codes) > self.max_history:
            self.executed_codes.pop(0)
            
        # Update UI console
        if self.ui_manager and hasattr(self.ui_manager, 'console_window'):
            if result['success']:
                self.ui_manager.console_window.add_output_line_to_log(
                    f"IDLE executed: {code[:50]}{'...' if len(code) > 50 else ''}"
                )
                if result['output']:
                    self.ui_manager.console_window.add_output_line_to_log(
                        f"Output: {result['output']}"
                    )
            else:
                self.ui_manager.console_window.add_output_line_to_log(
                    f"IDLE error: {result['error']}"
                )
                
    def launch_idle(self) -> bool:
        if not self.idle_bridge:
            if not self.initialize():
                return False
                
        return self.idle_bridge.launch_idle()
        
    def close_idle(self):
        if self.idle_bridge:
            self.idle_bridge.close_idle()
            
    def is_idle_running(self) -> bool:
        return self.idle_bridge and self.idle_bridge.is_idle_running()
        
    def get_execution_history(self) -> list:
        return self.executed_codes.copy()
        
    def clear_history(self):
        self.executed_codes.clear()
        
    def create_script_from_history(self, indices: list) -> str:
        code_lines = []
        for i in indices:
            if 0 <= i < len(self.executed_codes):
                code_lines.append(self.executed_codes[i]['code'])
        return '\n\n'.join(code_lines)
        
    def export_session_script(self, filepath: str):
        all_code = self.create_script_from_history(range(len(self.executed_codes)))
        
        header = f'''# UPST Game Script Session Export
# Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
# Total commands: {len(self.executed_codes)}

'''
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + all_code)
            
    def shutdown(self):
        if self.idle_bridge:
            self.idle_bridge.cleanup()
            self.idle_bridge = None

