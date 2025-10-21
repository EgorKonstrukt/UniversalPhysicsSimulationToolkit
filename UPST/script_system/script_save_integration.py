import json
import os
import pickle
import time
from typing import Dict, Any, List, Optional
import traceback


class ScriptSaveData:
    def __init__(self):
        self.version = "1.0"
        self.timestamp = time.time()
        self.script_objects = []
        self.script_engine_state = {}
        self.idle_integration_state = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'timestamp': self.timestamp,
            'script_objects': self.script_objects,
            'script_engine_state': self.script_engine_state,
            'idle_integration_state': self.idle_integration_state   
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        save_data = cls()
        save_data.version = data.get('version', '1.0')
        save_data.timestamp = data.get('timestamp', time.time())
        save_data.script_objects = data.get('script_objects', [])
        save_data.script_engine_state = data.get('script_engine_state', {})
        save_data.idle_integration_state = data.get('idle_integration_state', {})
        return save_data


class ScriptSaveManager:
    def __init__(self, script_object_manager, script_engine, idle_integration):
        self.script_object_manager = script_object_manager
        self.script_engine = script_engine
        self.idle_integration = idle_integration
        
        self.save_directory = "saves/scripts"
        self.backup_directory = "saves/scripts/backups"
        self.auto_save_enabled = True
        self.auto_save_interval = 300  # 5 minutes
        self.last_auto_save = time.time()
        
        self._ensure_directories()
        
    def _ensure_directories(self):
        os.makedirs(self.save_directory, exist_ok=True)
        os.makedirs(self.backup_directory, exist_ok=True)
        
    def save_scripts_data(self, world_name: str = None) -> Dict[str, Any]:
        try:
            save_data = ScriptSaveData()
            
            # Save script objects
            for script_obj in self.script_object_manager.get_all_script_objects():
                obj_data = script_obj.to_dict()
                
                # Add physics body data if exists
                if script_obj.physics_body:
                    obj_data['physics_body'] = {
                        'position': list(script_obj.physics_body.position),
                        'velocity': list(script_obj.physics_body.velocity),
                        'angle': script_obj.physics_body.angle,
                        'angular_velocity': script_obj.physics_body.angular_velocity,
                        'mass': script_obj.physics_body.mass,
                        'moment': script_obj.physics_body.moment
                    }
                    
                save_data.script_objects.append(obj_data)
                
            # Save script engine state
            save_data.script_engine_state = {
                'running_scripts': list(self.script_engine.running_scripts.keys()),
                'script_outputs': {k: v for k, v in self.script_engine.script_outputs.items()},
                'global_namespace_keys': list(self.script_engine.global_namespace.keys())
            }
            
            # Save IDLE integration state
            if self.idle_integration:
                save_data.idle_integration_state = {
                    'integration_enabled': self.idle_integration.integration_enabled,
                    'execution_history_count': len(self.idle_integration.executed_codes),
                    'is_idle_running': self.idle_integration.is_idle_running()
                }
                
            return {
                'success': True,
                'data': save_data.to_dict(),
                'script_count': len(save_data.script_objects),
                'timestamp': save_data.timestamp
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
    def load_scripts_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            save_data = ScriptSaveData.from_dict(data)
            
            # Clear existing scripts
            for script_id in list(self.script_object_manager.script_objects.keys()):
                self.script_object_manager.remove_script_object(script_id)
                
            # Load script objects
            loaded_count = 0
            for obj_data in save_data.script_objects:
                try:
                    # Create script object without physics body first
                    script_obj = self.script_object_manager.create_script_object(
                        position=tuple(obj_data.get('position', (0, 0))),
                        name=obj_data.get('name', ''),
                        code=obj_data.get('code', ''),
                        auto_run=False  # Don't auto-run during loading
                    )
                    
                    # Restore additional properties
                    script_obj.id = obj_data.get('id', script_obj.id)
                    script_obj.created_time = obj_data.get('created_time', script_obj.created_time)
                    script_obj.last_modified = obj_data.get('last_modified', script_obj.last_modified)
                    script_obj.execution_count = obj_data.get('execution_count', 0)
                    script_obj.visual_radius = obj_data.get('visual_radius', 30)
                    script_obj.color = tuple(obj_data.get('color', (100, 150, 255, 200)))
                    script_obj.auto_run = obj_data.get('auto_run', False)
                    
                    # Restore physics body state if exists
                    if 'physics_body' in obj_data and script_obj.physics_body:
                        body_data = obj_data['physics_body']
                        script_obj.physics_body.position = tuple(body_data.get('position', (0, 0)))
                        script_obj.physics_body.velocity = tuple(body_data.get('velocity', (0, 0)))
                        script_obj.physics_body.angle = body_data.get('angle', 0)
                        script_obj.physics_body.angular_velocity = body_data.get('angular_velocity', 0)
                        
                    loaded_count += 1
                    
                except Exception as e:
                    print(f"Error loading script object: {e}")
                    continue
                    
            # Restore script engine state
            if 'script_engine_state' in data:
                engine_state = save_data.script_engine_state
                # Clear previous outputs
                self.script_engine.clear_outputs()
                
            return {
                'success': True,
                'loaded_count': loaded_count,
                'total_count': len(save_data.script_objects),
                'timestamp': save_data.timestamp
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
    def save_to_file(self, filepath: str) -> Dict[str, Any]:
        try:
            result = self.save_scripts_data()
            if not result['success']:
                return result
                
            # Create backup if file exists
            if os.path.exists(filepath):
                backup_path = self._create_backup(filepath)
                
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result['data'], f, indent=2, ensure_ascii=False)
                
            return {
                'success': True,
                'filepath': filepath,
                'script_count': result['script_count'],
                'file_size': os.path.getsize(filepath)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
    def load_from_file(self, filepath: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(filepath):
                return {
                    'success': False,
                    'error': f'File not found: {filepath}'
                }
                
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            result = self.load_scripts_data(data)
            
            if result['success']:
                result['filepath'] = filepath
                result['file_size'] = os.path.getsize(filepath)
                
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
    def _create_backup(self, filepath: str) -> str:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        backup_filename = f"{name}_backup_{timestamp}{ext}"
        backup_path = os.path.join(self.backup_directory, backup_filename)
        
        try:
            import shutil
            shutil.copy2(filepath, backup_path)
            return backup_path
        except Exception as e:
            print(f"Failed to create backup: {e}")
            return None
            
    def auto_save(self, world_name: str = None) -> bool:
        if not self.auto_save_enabled:
            return False
            
        current_time = time.time()
        if current_time - self.last_auto_save < self.auto_save_interval:
            return False
            
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"autosave_scripts_{timestamp}.json"
            filepath = os.path.join(self.save_directory, filename)
            
            result = self.save_to_file(filepath)
            
            if result['success']:
                self.last_auto_save = current_time
                self._cleanup_old_autosaves()
                return True
                
        except Exception as e:
            print(f"Auto-save failed: {e}")
            
        return False
        
    def _cleanup_old_autosaves(self, keep_count: int = 10):
        try:
            autosave_files = []
            for filename in os.listdir(self.save_directory):
                if filename.startswith('autosave_scripts_') and filename.endswith('.json'):
                    filepath = os.path.join(self.save_directory, filename)
                    autosave_files.append((filepath, os.path.getmtime(filepath)))
                    
            # Sort by modification time (newest first)
            autosave_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old files
            for filepath, _ in autosave_files[keep_count:]:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Failed to remove old autosave {filepath}: {e}")
                    
        except Exception as e:
            print(f"Failed to cleanup autosaves: {e}")
            
    def get_save_files(self) -> List[Dict[str, Any]]:
        files = []
        
        try:
            for filename in os.listdir(self.save_directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.save_directory, filename)
                    stat = os.stat(filepath)
                    
                    files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'is_autosave': filename.startswith('autosave_')
                    })
                    
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            print(f"Failed to list save files: {e}")
            
        return files
        
    def export_scripts_as_python_files(self, directory: str) -> Dict[str, Any]:
        try:
            os.makedirs(directory, exist_ok=True)
            
            exported_count = 0
            for script_obj in self.script_object_manager.get_all_script_objects():
                if script_obj.code.strip():
                    filename = f"{script_obj.name}_{script_obj.id[:8]}.py"
                    # Replace invalid filename characters
                    filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                    filepath = os.path.join(directory, filename)
                    
                    header = f'''# Script: {script_obj.name}
# ID: {script_obj.id}
# Created: {time.ctime(script_obj.created_time)}
# Modified: {time.ctime(script_obj.last_modified)}
# Auto-run: {script_obj.auto_run}
# Position: {script_obj.position}

'''
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(header + script_obj.code)
                        
                    exported_count += 1
                    
            return {
                'success': True,
                'exported_count': exported_count,
                'directory': directory
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
    def update(self, dt):
        # Handle auto-save
        if self.auto_save_enabled:
            self.auto_save()


class ScriptSaveIntegration:
    def __init__(self, original_save_load_manager, script_save_manager):
        self.original_save_load_manager = original_save_load_manager
        self.script_save_manager = script_save_manager
        
        # Patch the original save/load methods
        self._patch_save_load_methods()
        
    def _patch_save_load_methods(self):
        # Store original methods
        self.original_save_world = self.original_save_load_manager.save_world
        self.original_load_world = self.original_save_load_manager.load_world
        
        # Replace with enhanced methods
        self.original_save_load_manager.save_world = self._enhanced_save_world
        self.original_save_load_manager.load_world = self._enhanced_load_world
        
    def _enhanced_save_world(self):
        # Call original save method
        self.original_save_world()
        
        # Save scripts data
        try:
            # Get the last saved file path (this is a simplification)
            # In a real implementation, you'd need to modify the original save method
            # to return the filepath or store it somewhere accessible
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            script_filepath = os.path.join(self.script_save_manager.save_directory, 
                                         f"world_scripts_{timestamp}.json")
            
            result = self.script_save_manager.save_to_file(script_filepath)
            
            if result['success']:
                if hasattr(self.original_save_load_manager, 'ui_manager'):
                    self.original_save_load_manager.ui_manager.console_window.add_output_line_to_log(
                        f"Scripts saved: {result['script_count']} objects"
                    )
            else:
                if hasattr(self.original_save_load_manager, 'ui_manager'):
                    self.original_save_load_manager.ui_manager.console_window.add_output_line_to_log(
                        f"Script save error: {result['error']}"
                    )
                    
        except Exception as e:
            print(f"Enhanced save error: {e}")
            
    def _enhanced_load_world(self):
        # Call original load method
        self.original_load_world()
        
        # Try to load corresponding scripts
        try:
            # Look for the most recent script save file
            save_files = self.script_save_manager.get_save_files()
            
            if save_files:
                # Load the most recent non-autosave file, or most recent autosave if no manual saves
                manual_saves = [f for f in save_files if not f['is_autosave']]
                file_to_load = manual_saves[0] if manual_saves else save_files[0]
                
                result = self.script_save_manager.load_from_file(file_to_load['filepath'])
                
                if result['success']:
                    if hasattr(self.original_save_load_manager, 'ui_manager'):
                        self.original_save_load_manager.ui_manager.console_window.add_output_line_to_log(
                            f"Scripts loaded: {result['loaded_count']}/{result['total_count']} objects"
                        )
                        
                    # Execute auto-run scripts after a short delay
                    import threading
                    def delayed_auto_run():
                        time.sleep(1)  # Give physics time to settle
                        self.script_save_manager.script_object_manager.execute_all_auto_run()
                        
                    threading.Thread(target=delayed_auto_run, daemon=True).start()
                    
                else:
                    if hasattr(self.original_save_load_manager, 'ui_manager'):
                        self.original_save_load_manager.ui_manager.console_window.add_output_line_to_log(
                            f"Script load error: {result['error']}"
                        )
                        
        except Exception as e:
            print(f"Enhanced load error: {e}")
            
    def restore_original_methods(self):
        # Restore original methods if needed
        self.original_save_load_manager.save_world = self.original_save_world
        self.original_save_load_manager.load_world = self.original_load_world

