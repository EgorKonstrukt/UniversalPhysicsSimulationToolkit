import socket
import threading
import json
import time
from typing import Dict, Any, Optional, Callable


class GameEditorBridge:
    def __init__(self, script_engine, debug_manager, port=12345):
        self.script_engine = script_engine
        self.debug_manager = debug_manager
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.running = False
        self.server_thread = None
        
        self.message_handlers = {
            'execute_script': self.handle_execute_script,
            'stop_script': self.handle_stop_script,
            'get_script_status': self.handle_get_script_status,
            'list_scripts': self.handle_list_scripts
        }
        
    def start_server(self):
        if self.running:
            return True
            
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(1)
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            self.debug_manager.log(f"Game-Editor bridge server started on port {self.port}", "Bridge")
            return True
            
        except Exception as e:
            self.debug_manager.log_error(f"Failed to start bridge server: {e}", "Bridge")
            return False
            
    def stop_server(self):
        self.running = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
            
        self.debug_manager.log("Game-Editor bridge server stopped", "Bridge")
        
    def _server_loop(self):
        while self.running:
            try:
                self.debug_manager.log("Waiting for external editor connection...", "Bridge")
                client_socket, client_address = self.server_socket.accept()
                
                self.client_socket = client_socket
                self.client_address = client_address
                
                self.debug_manager.log(f"External editor connected from {client_address}", "Bridge")
                self.send_message({'type': 'connection_established', 'status': 'connected'})
                
                self._handle_client()
                
            except Exception as e:
                if self.running:
                    self.debug_manager.log_error(f"Server loop error: {e}", "Bridge")
                    time.sleep(1)
                    
    def _handle_client(self):
        buffer = ""
        
        while self.running and self.client_socket:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            self._process_message(message)
                        except json.JSONDecodeError as e:
                            self.debug_manager.log_error(f"Failed to decode message: {e}", "Bridge")
                            
            except Exception as e:
                self.debug_manager.log_error(f"Client handling error: {e}", "Bridge")
                break
                
        self.debug_manager.log("External editor disconnected", "Bridge")
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
    def _process_message(self, message: Dict[str, Any]):
        msg_type = message.get('type', '')
        
        if msg_type in self.message_handlers:
            try:
                self.message_handlers[msg_type](message)
            except Exception as e:
                self.debug_manager.log_error(f"Error handling message type '{msg_type}': {e}", "Bridge")
                self.send_error_response(message, str(e))
        else:
            self.debug_manager.log_error(f"Unknown message type: {msg_type}", "Bridge")
            self.send_error_response(message, f"Unknown message type: {msg_type}")
            
    def handle_execute_script(self, message: Dict[str, Any]):
        script_id = message.get('script_id', '')
        code = message.get('code', '')
        async_execution = message.get('async', False)
        
        if not script_id or not code:
            self.send_error_response(message, "Missing script_id or code")
            return
            
        self.debug_manager.log(f"Executing script from external editor: {script_id}", "Bridge")
        
        result = self.script_engine.execute_script(script_id, code, async_execution)
        
        response = {
            'type': 'script_result',
            'script_id': script_id,
            'result': result
        }
        
        self.send_message(response)
        
    def handle_stop_script(self, message: Dict[str, Any]):
        script_id = message.get('script_id', '')
        
        if not script_id:
            self.send_error_response(message, "Missing script_id")
            return
            
        self.debug_manager.log(f"Stopping script from external editor: {script_id}", "Bridge")
        
        success = self.script_engine.stop_script(script_id)
        
        response = {
            'type': 'script_stopped',
            'script_id': script_id,
            'success': success
        }
        
        self.send_message(response)
        
    def handle_get_script_status(self, message: Dict[str, Any]):
        script_id = message.get('script_id', '')
        
        if not script_id:
            self.send_error_response(message, "Missing script_id")
            return
            
        status = self.script_engine.get_script_status(script_id)
        
        response = {
            'type': 'script_status',
            'script_id': script_id,
            'status': status
        }
        
        self.send_message(response)
        
    def handle_list_scripts(self, message: Dict[str, Any]):
        scripts = []
        
        for script_id, process_info in self.script_engine.running_scripts.items():
            status = self.script_engine.get_script_status(script_id)
            scripts.append({
                'id': script_id,
                'status': status.get('status', 'unknown'),
                'start_time': status.get('start_time', 0)
            })
            
        response = {
            'type': 'script_list',
            'scripts': scripts
        }
        
        self.send_message(response)
        
    def send_message(self, message: Dict[str, Any]) -> bool:
        if not self.client_socket:
            return False
            
        try:
            json_data = json.dumps(message) + "\n"
            self.client_socket.send(json_data.encode('utf-8'))
            return True
        except Exception as e:
            self.debug_manager.log_error(f"Failed to send message to external editor: {e}", "Bridge")
            return False
            
    def send_error_response(self, original_message: Dict[str, Any], error: str):
        response = {
            'type': 'error',
            'original_type': original_message.get('type', ''),
            'error': error
        }
        self.send_message(response)
        
    def send_script_output(self, script_id: str, output: str):
        message = {
            'type': 'script_output',
            'script_id': script_id,
            'output': output
        }
        self.send_message(message)
        
    def send_script_error(self, script_id: str, error: str):
        message = {
            'type': 'script_error',
            'script_id': script_id,
            'error': error
        }
        self.send_message(message)
        
    def send_debug_log(self, level: str, category: str, message: str, timestamp: str):
        log_message = {
            'type': 'debug_log',
            'level': level,
            'category': category,
            'message': message,
            'timestamp': timestamp
        }
        self.send_message(log_message)
        
    def is_connected(self) -> bool:
        return self.client_socket is not None
        
    def get_connection_info(self) -> Optional[Dict[str, Any]]:
        if self.client_socket and self.client_address:
            return {
                'address': self.client_address[0],
                'port': self.client_address[1],
                'connected_time': time.time()
            }
        return None

