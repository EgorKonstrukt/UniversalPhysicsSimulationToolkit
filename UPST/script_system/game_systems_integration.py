import pygame
import pymunk
import math
import time
import random
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from UPST.config import Config


class GizmosAPI:
    def __init__(self, gizmos_manager):
        self.gizmos = gizmos_manager
        
    def draw_line(self, start: Tuple[float, float], end: Tuple[float, float], 
                  color: str = 'white', width: int = 2, persistent: bool = False, 
                  duration: float = 0.0) -> str:
        return self.gizmos.draw_line(start, end, color, width, persistent, duration)
        
    def draw_circle(self, center: Tuple[float, float], radius: float, 
                   color: str = 'white', filled: bool = False, width: int = 2,
                   persistent: bool = False, duration: float = 0.0) -> str:
        return self.gizmos.draw_circle(center, radius, color, filled, width, persistent, duration)
        
    def draw_rectangle(self, rect: Tuple[float, float, float, float], 
                      color: str = 'white', filled: bool = False, width: int = 2,
                      persistent: bool = False, duration: float = 0.0) -> str:
        x, y, w, h = rect
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        return self.draw_polygon(points, color, filled, width, persistent, duration)
        
    def draw_polygon(self, points: List[Tuple[float, float]], 
                    color: str = 'white', filled: bool = False, width: int = 2,
                    persistent: bool = False, duration: float = 0.0) -> str:
        return self.gizmos.draw_polygon(points, color, filled, width, persistent, duration)
        
    def draw_text(self, text: str, position: Tuple[float, float], 
                 color: str = 'white', size: int = 16,
                 persistent: bool = False, duration: float = 0.0) -> str:
        return self.gizmos.draw_text(text, position, color, size, persistent, duration)
        
    def draw_arrow(self, start: Tuple[float, float], end: Tuple[float, float],
                  color: str = 'white', width: int = 2, head_size: float = 10,
                  persistent: bool = False, duration: float = 0.0) -> str:
        return self.gizmos.draw_arrow(start, end, color, width, head_size, persistent, duration)
        
    def draw_grid(self, center: Tuple[float, float], size: Tuple[int, int],
                 spacing: float = 50, color: str = 'gray', width: int = 1,
                 persistent: bool = False, duration: float = 0.0) -> List[str]:
        lines = []
        cx, cy = center
        cols, rows = size
        
        for i in range(cols + 1):
            x = cx - (cols * spacing / 2) + i * spacing
            start = (x, cy - (rows * spacing / 2))
            end = (x, cy + (rows * spacing / 2))
            lines.append(self.draw_line(start, end, color, width, persistent, duration))
            
        for i in range(rows + 1):
            y = cy - (rows * spacing / 2) + i * spacing
            start = (cx - (cols * spacing / 2), y)
            end = (cx + (cols * spacing / 2), y)
            lines.append(self.draw_line(start, end, color, width, persistent, duration))
            
        return lines
        
    def draw_coordinate_system(self, origin: Tuple[float, float] = (0, 0),
                             length: float = 100, persistent: bool = False,
                             duration: float = 0.0) -> List[str]:
        ox, oy = origin
        elements = []
        
        elements.append(self.draw_arrow((ox, oy), (ox + length, oy), 'red', 3, 15, persistent, duration))
        elements.append(self.draw_text('X', (ox + length + 20, oy), 'red', 16, persistent, duration))
        
        elements.append(self.draw_arrow((ox, oy), (ox, oy + length), 'green', 3, 15, persistent, duration))
        elements.append(self.draw_text('Y', (ox, oy + length + 20), 'green', 16, persistent, duration))
        
        return elements
        
    def draw_vector_field(self, bounds: Tuple[float, float, float, float],
                         vector_func: callable, spacing: float = 50,
                         scale: float = 1.0, color: str = 'cyan',
                         persistent: bool = False, duration: float = 0.0) -> List[str]:
        x_min, y_min, x_max, y_max = bounds
        vectors = []
        
        x = x_min
        while x <= x_max:
            y = y_min
            while y <= y_max:
                try:
                    vx, vy = vector_func(x, y)
                    end_x = x + vx * scale
                    end_y = y + vy * scale
                    vectors.append(self.draw_arrow((x, y), (end_x, end_y), color, 1, 5, persistent, duration))
                except:
                    pass
                y += spacing
            x += spacing
            
        return vectors
        
    def clear_all(self):
        self.gizmos.clear_all()
        
    def clear_by_id(self, gizmo_id: str):
        self.gizmos.remove_gizmo(gizmo_id)


class SpawnerAPI:
    def __init__(self, object_spawner, physics_manager):
        self.spawner = object_spawner
        self.physics_manager = physics_manager
        
    def spawn_circle(self, position: Tuple[float, float], radius: float = 30,
                    mass: float = None, friction: float = 0.7, elasticity: float = 0.5,
                    color: Tuple[int, int, int, int] = None, velocity: Tuple[float, float] = (0, 0)) -> pymunk.Body:
        
        if mass is None:
            mass = radius * math.pi / 10
            
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = position
        body.velocity = velocity
        
        shape = pymunk.Circle(body, radius)
        shape.friction = friction
        shape.elasticity = elasticity
        
        if color:
            shape.color = color
        else:
            shape.color = self.spawner.get_random_color_from_theme()
            
        self.physics_manager.add_body_shape(body, shape)
        return body
        
    def spawn_rectangle(self, position: Tuple[float, float], size: Tuple[float, float] = (30, 30),
                       mass: float = None, friction: float = 0.7, elasticity: float = 0.5,
                       color: Tuple[int, int, int, int] = None, velocity: Tuple[float, float] = (0, 0),
                       angle: float = 0) -> pymunk.Body:
        
        width, height = size
        if mass is None:
            mass = (width * height) / 200
            
        moment = pymunk.moment_for_box(mass, size)
        body = pymunk.Body(mass, moment)
        body.position = position
        body.velocity = velocity
        body.angle = angle
        
        points = [(-width/2, -height/2), (-width/2, height/2), (width/2, height/2), (width/2, -height/2)]
        shape = pymunk.Poly(body, points)
        shape.friction = friction
        shape.elasticity = elasticity
        
        if color:
            shape.color = color
        else:
            shape.color = self.spawner.get_random_color_from_theme()
            
        self.physics_manager.add_body_shape(body, shape)
        return body
        
    def spawn_polygon(self, position: Tuple[float, float], vertices: List[Tuple[float, float]],
                     mass: float = None, friction: float = 0.7, elasticity: float = 0.5,
                     color: Tuple[int, int, int, int] = None, velocity: Tuple[float, float] = (0, 0)) -> pymunk.Body:
        
        if mass is None:
            area = 0
            for i in range(len(vertices)):
                x1, y1 = vertices[i]
                x2, y2 = vertices[(i + 1) % len(vertices)]
                area += (x1 * y2 - x2 * y1)
            mass = abs(area) / 200
            
        moment = pymunk.moment_for_poly(mass, vertices)
        body = pymunk.Body(mass, moment)
        body.position = position
        body.velocity = velocity
        
        shape = pymunk.Poly(body, vertices)
        shape.friction = friction
        shape.elasticity = elasticity
        
        if color:
            shape.color = color
        else:
            shape.color = self.spawner.get_random_color_from_theme()
            
        self.physics_manager.add_body_shape(body, shape)
        return body
        
    def spawn_chain(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                   segments: int = 10, segment_length: float = None, 
                   segment_mass: float = 1.0, joint_stiffness: float = 1000) -> List[pymunk.Body]:
        
        if segment_length is None:
            total_length = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
            segment_length = total_length / segments
            
        bodies = []
        constraints = []
        
        dx = (end_pos[0] - start_pos[0]) / segments
        dy = (end_pos[1] - start_pos[1]) / segments
        
        for i in range(segments):
            pos = (start_pos[0] + dx * i, start_pos[1] + dy * i)
            body = self.spawn_rectangle(pos, (segment_length * 0.8, 5), segment_mass)
            bodies.append(body)
            
            if i > 0:
                constraint = pymunk.PinJoint(bodies[i-1], body, (segment_length/2, 0), (-segment_length/2, 0))
                constraint.stiffness = joint_stiffness
                self.physics_manager.space.add(constraint)
                constraints.append(constraint)
                
        return bodies
        
    def create_compound_object(self, position: Tuple[float, float], 
                             parts: List[Dict[str, Any]]) -> List[pymunk.Body]:
        bodies = []
        
        for part in parts:
            part_type = part.get('type', 'circle')
            offset = part.get('offset', (0, 0))
            part_pos = (position[0] + offset[0], position[1] + offset[1])
            
            if part_type == 'circle':
                body = self.spawn_circle(part_pos, **{k: v for k, v in part.items() if k not in ['type', 'offset']})
            elif part_type == 'rectangle':
                body = self.spawn_rectangle(part_pos, **{k: v for k, v in part.items() if k not in ['type', 'offset']})
            elif part_type == 'polygon':
                body = self.spawn_polygon(part_pos, **{k: v for k, v in part.items() if k not in ['type', 'offset']})
            else:
                continue
                
            bodies.append(body)
            
        return bodies


class SynthesizerAPI:
    def __init__(self, synthesizer):
        self.synthesizer = synthesizer
        
    def play_note(self, note: str, duration: float = 1.0, volume: float = None,
                 waveform: str = 'sine', effects: bool = True) -> Any:
        return self.synthesizer.play_note(note, duration, volume=volume, 
                                        waveform=waveform, apply_effects=effects)
        
    def play_frequency(self, frequency: float, duration: float = 1.0, 
                      volume: float = None, waveform: str = 'sine', 
                      effects: bool = True) -> Any:
        return self.synthesizer.play_frequency(frequency, duration, volume=volume,
                                             waveform=waveform, apply_effects=effects)
        
    def play_chord(self, notes: List[str], duration: float = 1.0, 
                  volume: float = None, waveform: str = 'sine') -> List[Any]:
        return self.synthesizer.play_chord(notes, duration, waveform, volume)
        
    def play_sequence(self, notes: List[str], durations: List[float],
                     waveform: str = 'sine', volumes: List[float] = None):
        self.synthesizer.play_sequence(notes, durations, waveform, volumes=volumes)
        
    def play_scale(self, root: str = 'C4', scale_type: str = 'major',
                  note_duration: float = 0.5, waveform: str = 'sine'):
        scale_freqs = self.synthesizer.create_scale(root, scale_type)
        
        for freq in scale_freqs:
            self.synthesizer.play_frequency(freq, note_duration, waveform=waveform)
            time.sleep(note_duration)
            
    def create_melody(self, pattern: str, base_note: str = 'C4', 
                     note_duration: float = 0.5) -> List[str]:
        scale_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        octave = int(base_note[-1])
        
        melody = []
        for char in pattern:
            if char.isdigit():
                degree = int(char) - 1
                if 0 <= degree < len(scale_notes):
                    note = f"{scale_notes[degree]}{octave}"
                    melody.append(note)
                    
        return melody
        
    def set_effects(self, **effects):
        for effect, value in effects.items():
            if hasattr(self.synthesizer.effects, effect):
                self.synthesizer.effects[effect] = value


class PhysicsAPI:
    def __init__(self, physics_manager):
        self.physics_manager = physics_manager
        self.space = physics_manager.space
        
    def get_all_bodies(self) -> List[pymunk.Body]:
        return list(self.space.bodies)
        
    def get_bodies_in_area(self, center: Tuple[float, float], radius: float) -> List[pymunk.Body]:
        bodies = []
        cx, cy = center
        
        for body in self.space.bodies:
            bx, by = body.position
            distance = math.sqrt((bx - cx)**2 + (by - cy)**2)
            if distance <= radius:
                bodies.append(body)
                
        return bodies
        
    def apply_force_to_all(self, force: Tuple[float, float]):
        for body in self.space.bodies:
            body.force = force
            
    def apply_impulse_to_all(self, impulse: Tuple[float, float]):
        for body in self.space.bodies:
            body.apply_impulse_at_world_point(impulse, body.position)
            
    def create_explosion(self, center: Tuple[float, float], force: float, radius: float):
        cx, cy = center
        for body in self.space.bodies:
            bx, by = body.position
            distance = math.sqrt((bx - cx)**2 + (by - cy)**2)
            if distance <= radius and distance > 0:
                force_x = (bx - cx) / distance
                force_y = (by - cy) / distance
                force_magnitude = force * (1 - distance / radius)
                impulse = (force_x * force_magnitude, force_y * force_magnitude)
                body.apply_impulse_at_world_point(impulse, body.position)
                
    def create_gravity_well(self, center: Tuple[float, float], strength: float, radius: float):
        cx, cy = center
        for body in self.space.bodies:
            bx, by = body.position
            distance = math.sqrt((bx - cx)**2 + (by - cy)**2)
            if distance <= radius and distance > 0:
                force_x = (cx - bx) / distance
                force_y = (cy - by) / distance
                force_magnitude = strength / (distance * distance)
                force_vec = (force_x * force_magnitude, force_y * force_magnitude)
                body.force = (body.force[0] + force_vec[0], body.force[1] + force_vec[1])
                
    def set_gravity(self, gravity: Tuple[float, float]):
        self.space.gravity = gravity
        
    def get_gravity(self) -> Tuple[float, float]:
        return self.space.gravity
        
    def pause_simulation(self):
        self.physics_manager.paused = True
        
    def resume_simulation(self):
        self.physics_manager.paused = False
        
    def step_simulation(self, dt: float = None):
        if dt is None:
            dt = 1.0 / 60.0
        self.space.step(dt)
        
    def delete_all_bodies(self):
        self.physics_manager.delete_all()
        
    def create_joint(self, body_a: pymunk.Body, body_b: pymunk.Body, 
                    joint_type: str = 'pin', **kwargs) -> pymunk.Constraint:
        
        if joint_type == 'pin':
            anchor_a = kwargs.get('anchor_a', (0, 0))
            anchor_b = kwargs.get('anchor_b', (0, 0))
            joint = pymunk.PinJoint(body_a, body_b, anchor_a, anchor_b)
        elif joint_type == 'pivot':
            anchor = kwargs.get('anchor', (0, 0))
            joint = pymunk.PivotJoint(body_a, body_b, anchor)
        elif joint_type == 'spring':
            anchor_a = kwargs.get('anchor_a', (0, 0))
            anchor_b = kwargs.get('anchor_b', (0, 0))
            rest_length = kwargs.get('rest_length', 100)
            stiffness = kwargs.get('stiffness', 1000)
            damping = kwargs.get('damping', 10)
            joint = pymunk.DampedSpring(body_a, body_b, anchor_a, anchor_b, 
                                      rest_length, stiffness, damping)
        else:
            raise ValueError(f"Unknown joint type: {joint_type}")
        self.space.add(joint)
        return joint


class CameraAPI:
    def __init__(self, camera):
        self.camera = camera
        
    def get_position(self) -> Tuple[float, float]:
        return self.camera.translation
        
    def set_position(self, position: Tuple[float, float]):
        self.camera.translation = position
        
    def move(self, offset: Tuple[float, float]):
        self.camera.translation = (
            self.camera.translation[0] + offset[0],
            self.camera.translation[1] + offset[1]
        )
        
    def get_zoom(self) -> float:
        return self.camera.scaling
        
    def set_zoom(self, zoom: float):
        self.camera.scaling = zoom
        self.camera.target_scaling = zoom
        
    def zoom_to_fit(self, bounds: Tuple[float, float, float, float]):
        x_min, y_min, x_max, y_max = bounds
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        
        width = x_max - x_min
        height = y_max - y_min
        
        screen_width = Config.SCREEN_WIDTH
        screen_height = Config.SCREEN_HEIGHT
        
        zoom_x = screen_width / width if width > 0 else 1
        zoom_y = screen_height / height if height > 0 else 1
        zoom = min(zoom_x, zoom_y) * 0.8
        
        self.set_position((center_x, center_y))
        self.set_zoom(zoom)
        
    def screen_to_world(self, screen_pos: Tuple[float, float]) -> Tuple[float, float]:
        return self.camera.screen_to_world(screen_pos)
        
    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[float, float]:
        return self.camera.world_to_screen(world_pos)


class GameSystemsIntegration:
    def __init__(self, physics_manager, ui_manager, camera, spawner, 
                 sound_manager, synthesizer, gizmos, debug, 
                 save_load_manager, input_handler, console):
        
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
        
        self.gizmos_api = GizmosAPI(gizmos)
        self.spawner_api = SpawnerAPI(spawner, physics_manager)
        self.synthesizer_api = SynthesizerAPI(synthesizer)
        self.physics_api = PhysicsAPI(physics_manager)
        self.camera_api = CameraAPI(camera)
        
    def create_enhanced_context(self, base_context):
        enhanced_context = base_context.__dict__.copy()
        
        # Gizmos functions
        enhanced_context.update({
            'draw_line': self.gizmos_api.draw_line,
            'draw_circle': self.gizmos_api.draw_circle,
            'draw_rectangle': self.gizmos_api.draw_rectangle,
            'draw_polygon': self.gizmos_api.draw_polygon,
            'draw_text': self.gizmos_api.draw_text,
            'draw_arrow': self.gizmos_api.draw_arrow,
            'draw_grid': self.gizmos_api.draw_grid,
            'draw_coordinate_system': self.gizmos_api.draw_coordinate_system,
            'draw_vector_field': self.gizmos_api.draw_vector_field,
            'clear_gizmos': self.gizmos_api.clear_all,
        })
        
        # Spawner functions
        enhanced_context.update({
            'spawn_circle': self.spawner_api.spawn_circle,
            'spawn_rectangle': self.spawner_api.spawn_rectangle,
            'spawn_polygon': self.spawner_api.spawn_polygon,
            'spawn_chain': self.spawner_api.spawn_chain,
            'create_compound_object': self.spawner_api.create_compound_object,
        })
        
        # Synthesizer functions
        enhanced_context.update({
            'play_note': self.synthesizer_api.play_note,
            'play_frequency': self.synthesizer_api.play_frequency,
            'play_chord': self.synthesizer_api.play_chord,
            'play_sequence': self.synthesizer_api.play_sequence,
            'play_scale': self.synthesizer_api.play_scale,
            'create_melody': self.synthesizer_api.create_melody,
            'set_audio_effects': self.synthesizer_api.set_effects,
        })
        
        # Physics functions
        enhanced_context.update({
            'get_all_bodies': self.physics_api.get_all_bodies,
            'get_bodies_in_area': self.physics_api.get_bodies_in_area,
            'apply_force_to_all': self.physics_api.apply_force_to_all,
            'apply_impulse_to_all': self.physics_api.apply_impulse_to_all,
            'create_explosion': self.physics_api.create_explosion,
            'create_gravity_well': self.physics_api.create_gravity_well,
            'set_gravity': self.physics_api.set_gravity,
            'get_gravity': self.physics_api.get_gravity,
            'pause_simulation': self.physics_api.pause_simulation,
            'resume_simulation': self.physics_api.resume_simulation,
            'step_simulation': self.physics_api.step_simulation,
            'delete_all_bodies': self.physics_api.delete_all_bodies,
            'create_joint': self.physics_api.create_joint,
        })
        
        # Camera functions
        enhanced_context.update({
            'get_camera_position': self.camera_api.get_position,
            'set_camera_position': self.camera_api.set_position,
            'move_camera': self.camera_api.move,
            'get_camera_zoom': self.camera_api.get_zoom,
            'set_camera_zoom': self.camera_api.set_zoom,
            'zoom_to_fit': self.camera_api.zoom_to_fit,
            'screen_to_world': self.camera_api.screen_to_world,
            'world_to_screen': self.camera_api.world_to_screen,
        })
        
        # Utility functions
        enhanced_context.update({
            'get_mouse_world_pos': lambda: self.camera_api.screen_to_world(pygame.mouse.get_pos()),
            'get_mouse_screen_pos': lambda: pygame.mouse.get_pos(),
            'get_time': time.time,
            'sleep': time.sleep,
            'log_info': lambda msg: self.debug.log(msg, "Script"),
            'log_warning': lambda msg: self.debug.log_warning(msg, "Script"),
            'log_error': lambda msg: self.debug.log_error(msg, "Script"),
        })
        
        # Math utilities
        enhanced_context.update({
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'pi': math.pi,
            'sqrt': math.sqrt,
            'atan2': math.atan2,
            'degrees': math.degrees,
            'radians': math.radians,
            'random_float': random.random,
            'random_int': random.randint,
            'random_choice': random.choice,
        })
        
        try:
            import numpy as np
            enhanced_context['np'] = np
            enhanced_context['numpy'] = np
        except ImportError:
            pass
            
        return enhanced_context

