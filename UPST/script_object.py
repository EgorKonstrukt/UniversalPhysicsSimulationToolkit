import pygame
import pymunk
import uuid
import time
from typing import Dict, Any, Optional, List
import json
import os


class ScriptObject:
    def __init__(self, position=(0, 0), name="", code="", auto_run=False, 
                 script_engine=None, physics_body=None):
        self.id = str(uuid.uuid4())
        self.name = name or f"Script_{self.id[:8]}"
        self.code = code
        self.position = position
        self.auto_run = auto_run
        self.script_engine = script_engine
        
        self.created_time = time.time()
        self.last_modified = time.time()
        self.last_executed = None
        self.execution_count = 0
        
        self.is_running = False
        self.last_result = None
        
        self.physics_body = physics_body
        self.visual_radius = 30
        self.color = (100, 150, 255, 200)
        self.selected = False
        
        if physics_body is None:
            self._create_physics_body()
            
    def _create_physics_body(self):
        mass = 10
        moment = pymunk.moment_for_circle(mass, 0, self.visual_radius)
        self.physics_body = pymunk.Body(mass, moment)
        self.physics_body.position = self.position
        
        shape = pymunk.Circle(self.physics_body, self.visual_radius)
        shape.friction = 0.7
        shape.elasticity = 0.3
        shape.color = self.color
        
        self.physics_body.script_object = self
        shape.script_object = self
        
        if self.script_engine and hasattr(self.script_engine, 'physics_manager'):
            self.script_engine.physics_manager.add_body_shape(self.physics_body, shape)
            
    def update_code(self, new_code: str):
        self.code = new_code
        self.last_modified = time.time()
        
    def execute(self, async_execution=False) -> Dict[str, Any]:
        if not self.script_engine:
            return {'success': False, 'error': 'No script engine available'}
            
        if not self.code.strip():
            return {'success': False, 'error': 'No code to execute'}
            
        self.last_executed = time.time()
        self.execution_count += 1
        
        enhanced_code = f"""
# Script Object Context
script_object_id = "{self.id}"
script_object_name = "{self.name}"
script_object_position = {self.position}

# Original code
{self.code}
"""
        
        result = self.script_engine.execute_script(self.id, enhanced_code, async_execution)
        self.last_result = result
        
        if async_execution:
            self.is_running = True
        else:
            self.is_running = False
            
        return result
        
    def stop_execution(self):
        if self.script_engine and self.is_running:
            success = self.script_engine.stop_script(self.id)
            if success:
                self.is_running = False
            return success
        return False
        
    def get_status(self) -> Dict[str, Any]:
        status = {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'is_running': self.is_running,
            'execution_count': self.execution_count,
            'last_executed': self.last_executed,
            'last_modified': self.last_modified,
            'auto_run': self.auto_run,
            'code_length': len(self.code),
            'has_physics_body': self.physics_body is not None
        }
        
        if self.script_engine:
            engine_status = self.script_engine.get_script_status(self.id)
            status.update(engine_status)
            
        return status
        
    def draw_debug_info(self, screen, camera, font):
        if not self.physics_body:
            return
            
        screen_pos = camera.world_to_screen(self.physics_body.position)
        
        color = (255, 100, 100) if self.is_running else (100, 150, 255)
        if self.selected:
            color = (255, 255, 100)
            
        pygame.draw.circle(screen, color, screen_pos, int(self.visual_radius * camera.scaling), 2)
        
        if font:
            text_surface = font.render(self.name, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(screen_pos[0], screen_pos[1] - 40))
            screen.blit(text_surface, text_rect)
            
        status_color = (0, 255, 0) if self.last_result and self.last_result.get('success') else (255, 0, 0)
        pygame.draw.circle(screen, status_color, 
                         (screen_pos[0] + 20, screen_pos[1] - 20), 5)
                         
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'position': list(self.position),
            'auto_run': self.auto_run,
            'created_time': self.created_time,
            'last_modified': self.last_modified,
            'execution_count': self.execution_count,
            'visual_radius': self.visual_radius,
            'color': self.color
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], script_engine=None):
        obj = cls(
            position=tuple(data.get('position', (0, 0))),
            name=data.get('name', ''),
            code=data.get('code', ''),
            auto_run=data.get('auto_run', False),
            script_engine=script_engine
        )
        
        obj.id = data.get('id', obj.id)
        obj.created_time = data.get('created_time', obj.created_time)
        obj.last_modified = data.get('last_modified', obj.last_modified)
        obj.execution_count = data.get('execution_count', 0)
        obj.visual_radius = data.get('visual_radius', 30)
        obj.color = tuple(data.get('color', (100, 150, 255, 200)))
        
        return obj
        
    def save_to_file(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
    @classmethod
    def load_from_file(cls, filepath: str, script_engine=None):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data, script_engine)
        
    def __str__(self):
        return f"ScriptObject(id={self.id[:8]}, name={self.name}, running={self.is_running})"
        
    def __repr__(self):
        return self.__str__()


class ScriptObjectManager:
    def __init__(self, script_engine):
        self.script_engine = script_engine
        self.script_objects = {}
        self.selected_object = None
        
    def create_script_object(self, position=(0, 0), name="", code="", auto_run=False) -> ScriptObject:
        script_obj = ScriptObject(
            position=position,
            name=name,
            code=code,
            auto_run=auto_run,
            script_engine=self.script_engine
        )
        
        self.script_objects[script_obj.id] = script_obj
        
        if auto_run and code.strip():
            script_obj.execute(async_execution=True)
            
        return script_obj
        
    def remove_script_object(self, script_id: str) -> bool:
        if script_id in self.script_objects:
            script_obj = self.script_objects[script_id]
            
            script_obj.stop_execution()
            
            if script_obj.physics_body and hasattr(self.script_engine, 'physics_manager'):
                try:
                    self.script_engine.physics_manager.space.remove(script_obj.physics_body)
                    for shape in script_obj.physics_body.shapes:
                        self.script_engine.physics_manager.space.remove(shape)
                except:
                    pass
                    
            del self.script_objects[script_id]
            
            if self.selected_object and self.selected_object.id == script_id:
                self.selected_object = None
                
            return True
        return False
        
    def get_script_object(self, script_id: str) -> Optional[ScriptObject]:
        return self.script_objects.get(script_id)
        
    def get_all_script_objects(self) -> List[ScriptObject]:
        return list(self.script_objects.values())
        
    def select_object_at_position(self, world_pos, tolerance=50) -> Optional[ScriptObject]:
        for script_obj in self.script_objects.values():
            if script_obj.physics_body:
                distance = (pymunk.Vec2d(*world_pos) - script_obj.physics_body.position).length
                if distance <= tolerance:
                    self.selected_object = script_obj
                    script_obj.selected = True
                    return script_obj
        return None
        
    def deselect_all(self):
        for script_obj in self.script_objects.values():
            script_obj.selected = False
        self.selected_object = None
        
    def update(self, dt):
        for script_obj in self.script_objects.values():
            if script_obj.physics_body:
                script_obj.position = script_obj.physics_body.position
                
        self.script_engine.update(dt)
        
    def draw_all(self, screen, camera, font):
        for script_obj in self.script_objects.values():
            script_obj.draw_debug_info(screen, camera, font)
            
    def save_all_to_directory(self, directory: str):
        os.makedirs(directory, exist_ok=True)
        
        for script_obj in self.script_objects.values():
            filename = f"{script_obj.name}_{script_obj.id[:8]}.json"
            filepath = os.path.join(directory, filename)
            script_obj.save_to_file(filepath)
            
    def load_all_from_directory(self, directory: str):
        if not os.path.exists(directory):
            return
            
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                try:
                    script_obj = ScriptObject.load_from_file(filepath, self.script_engine)
                    self.script_objects[script_obj.id] = script_obj
                    
                    if script_obj.auto_run and script_obj.code.strip():
                        script_obj.execute(async_execution=True)
                except Exception as e:
                    print(f"Error loading script object from {filepath}: {e}")
                    
    def execute_all_auto_run(self):
        for script_obj in self.script_objects.values():
            if script_obj.auto_run and script_obj.code.strip() and not script_obj.is_running:
                script_obj.execute(async_execution=True)

