import pygame
import pymunk
import math
import time
import random
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from UPST.config import config


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
            
        for j in range(rows + 1):
            y = cy - (rows * spacing / 2) + j * spacing
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
                         spacing: float = 50, func=None, color: str = 'cyan',
                         width: int = 2, persistent: bool = False, 
                         duration: float = 0.0) -> List[str]:
        if func is None:
            def func(x, y): 
                return (math.sin(x * 0.01) * 50, math.cos(y * 0.01) * 50)
        
        x_min, y_min, x_max, y_max = bounds
        gizmo_ids = []
        
        x = x_min
        while x <= x_max:
            y = y_min
            while y <= y_max:
                vx, vy = func(x, y)
                gizmo_ids.append(self.draw_arrow((x, y), (x + vx, y + vy), color, width, 8, persistent, duration))
                y += spacing
            x += spacing
            
        return gizmo_ids
        
    def draw_function(self, func, x_range: Tuple[float, float], 
                     samples: int = 100, color: str = 'yellow',
                     width: int = 2, persistent: bool = False, 
                     duration: float = 0.0) -> str:
        x_min, x_max = x_range
        dx = (x_max - x_min) / max(1, samples - 1)
        points = []
        for i in range(samples):
            x = x_min + i * dx
            y = func(x)
            points.append((x, y))
        return self.draw_polygon(points, color, False, width, persistent, duration)
        
    def draw_sine_wave(self, origin: Tuple[float, float], length: float, 
                      amplitude: float, frequency: float, 
                      phase: float = 0.0, samples: int = 100,
                      color: str = 'magenta', width: int = 2,
                      persistent: bool = False, duration: float = 0.0) -> str:
        ox, oy = origin
        dx = length / max(1, samples - 1)
        points = []
        for i in range(samples):
            x = ox + i * dx
            y = oy + math.sin(phase + frequency * (i / samples) * 2 * math.pi) * amplitude
            points.append((x, y))
        return self.draw_polygon(points, color, False, width, persistent, duration)
        
    def draw_radial_grid(self, center: Tuple[float, float], radius: float, 
                        rings: int = 5, spokes: int = 12, 
                        color: str = 'lightgray', width: int = 1,
                        persistent: bool = False, duration: float = 0.0) -> List[str]:
        cx, cy = center
        gizmo_ids = []
        
        for i in range(1, rings + 1):
            r = radius * i / rings
            gizmo_ids.append(self.draw_circle(center, r, color, False, width, persistent, duration))
            
        for j in range(spokes):
            angle = 2 * math.pi * j / spokes
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            gizmo_ids.append(self.draw_line(center, (x, y), color, width, persistent, duration))
            
        return gizmo_ids
        
    def draw_crosshair(self, center: Tuple[float, float], size: float = 20, 
                      color: str = 'white', width: int = 2,
                      persistent: bool = False, duration: float = 0.0) -> List[str]:
        cx, cy = center
        lines = []
        lines.append(self.draw_line((cx - size, cy), (cx + size, cy), color, width, persistent, duration))
        lines.append(self.draw_line((cx, cy - size), (cx, cy + size), color, width, persistent, duration))
        return lines
        
    def draw_trajectory(self, points: List[Tuple[float, float]], 
                       color: str = 'yellow', width: int = 2,
                       persistent: bool = False, duration: float = 0.0) -> str:
        return self.draw_polygon(points, color, False, width, persistent, duration)
        
    def draw_vectors(self, origin: Tuple[float, float], vectors: List[Tuple[float, float]], 
                    scale: float = 1.0, color: str = 'cyan', width: int = 2,
                    persistent: bool = False, duration: float = 0.0) -> List[str]:
        ox, oy = origin
        ids = []
        for vx, vy in vectors:
            ids.append(self.draw_arrow((ox, oy), (ox + vx * scale, oy + vy * scale), color, width, 8, persistent, duration))
        return ids
        
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
            mass = max(1.0, radius * radius * 0.01)
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
        
    def spawn_rectangle(self, position: Tuple[float, float], size: Tuple[float, float] = (50, 30),
                        mass: float = None, friction: float = 0.7, elasticity: float = 0.5,
                        color: Tuple[int, int, int, int] = None, angle: float = 0.0,
                        velocity: Tuple[float, float] = (0, 0)) -> pymunk.Body:
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
                area += x1 * y2 - x2 * y1
            area = abs(area) / 2.0
            mass = max(1.0, area / 200)
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
                   segments: int = 10, segment_mass: float = 0.5,
                   joint_stiffness: float = 1000) -> List[pymunk.Body]:
        dx = (end_pos[0] - start_pos[0]) / segments
        dy = (end_pos[1] - start_pos[1]) / segments
        segment_length = math.sqrt(dx*dx + dy*dy)
        bodies = []
        constraints = []
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
        
    def play_note(self, note: str, duration: float = 0.5, volume: float = 0.5):
        self.synthesizer.play_note(note, duration=duration, volume=volume)
        
    def play_chord(self, notes: List[str], duration: float = 0.8, volume: float = 0.5):
        self.synthesizer.play_chord(notes, duration=duration, volume=volume)
        
    def play_sequence(self, notes: List[str], durations: List[float] = None, 
                     volume: float = 0.5, interval: float = 0.1):
        self.synthesizer.play_sequence(notes, durations=durations, volume=volume, interval=interval)
        
    def play_scale(self, root: str = 'C', mode: str = 'major', octave: int = 4, 
                  ascending: bool = True, duration: float = 0.3):
        scale = {
            'major': [2, 2, 1, 2, 2, 2, 1],
            'minor': [2, 1, 2, 2, 1, 2, 2],
            'pentatonic': [2, 2, 3, 2, 3],
            'blues': [3, 2, 1, 1, 3, 2]
        }.get(mode, [2, 2, 1, 2, 2, 2, 1])
        notes = []
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        root_idx = note_names.index(root.upper())
        idx = root_idx
        for step in scale:
            notes.append(f"{note_names[idx]}{octave}")
            idx = (idx + step) % 12
        if ascending:
            self.play_sequence(notes, [duration] * len(notes), volume=0.5, interval=0.05)
        else:
            self.play_sequence(list(reversed(notes)), [duration] * len(notes), volume=0.5, interval=0.05)
        
    def create_melody(self, scale: str = 'C major', length: int = 8, 
                      rhythm: str = 'quarter', octave: int = 4) -> List[str]:
        scale_notes = {
            'C major': ['C', 'D', 'E', 'F', 'G', 'A', 'B'],
            'A minor': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
            'G major': ['G', 'A', 'B', 'C', 'D', 'E', 'F#'],
            'E minor': ['E', 'F#', 'G', 'A', 'B', 'C', 'D']
        }.get(scale, ['C', 'D', 'E', 'F', 'G', 'A', 'B'])
        rhythm_map = {
            'whole': 1.0, 'half': 0.5, 'quarter': 0.25,
            'eighth': 0.125, 'sixteenth': 0.0625
        }
        duration = rhythm_map.get(rhythm, 0.25)
        melody = []
        for _ in range(length):
            note = random.choice(scale_notes)
            melody.append(f"{note}{octave}")
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
            distance = math.sqrt((bx - cx) ** 2 + (by - cy) ** 2)
            if distance <= radius:
                bodies.append(body)
        return bodies

    def apply_force_to_all(self, force: Tuple[float, float]):
        for body in self.space.bodies:
            body.apply_force_at_world_point(force, body.position)

    def apply_impulse_to_all(self, impulse: Tuple[float, float]):
        for body in self.space.bodies:
            body.apply_impulse_at_world_point(impulse, body.position)

    def create_explosion(self, center: Tuple[float, float], force: float, radius: float):
        cx, cy = center
        for body in self.space.bodies:
            bx, by = body.position
            distance = math.sqrt((bx - cx) ** 2 + (by - cy) ** 2)
            if 0 < distance <= radius:
                dir_x = (bx - cx) / distance
                dir_y = (by - cy) / distance
                force_magnitude = force * (1 - distance / radius)
                impulse = (dir_x * force_magnitude, dir_y * force_magnitude)
                body.apply_impulse_at_world_point(impulse, body.position)

    def create_gravity_well(self, center: Tuple[float, float], strength: float, radius: float):
        cx, cy = center
        for body in self.space.bodies:
            bx, by = body.position
            distance = math.sqrt((bx - cx) ** 2 + (by - cy) ** 2)
            if 0 < distance <= radius:
                dir_x = (cx - bx) / distance
                dir_y = (cy - by) / distance
                force_magnitude = strength / max(1.0, distance * distance)
                force_vec = (dir_x * force_magnitude, dir_y * force_magnitude)
                body.force = (body.force[0] + force_vec[0], body.force[1] + force_vec[1])

    def set_gravity(self, gravity: Tuple[float, float]):
        self.space.gravity = gravity

    def get_gravity(self) -> Tuple[float, float]:
        return tuple(self.space.gravity)

    def pause_simulation(self):
        self.physics_manager.running_physics = False

    def resume_simulation(self):
        self.physics_manager.running_physics = True

    def step_simulation(self, dt: float = None):
        if dt is None:
            dt = 1.0 / 60.0
        self.physics_manager.step(dt)

    def delete_all_bodies(self):
        self.physics_manager.delete_all()

    def create_joint(self, body_a: pymunk.Body, body_b: pymunk.Body, joint_type: str, **kwargs):
        joint_type = joint_type.lower()
        joint = None
        if joint_type == 'pin' or joint_type == 'rigid':
            anchor_a = kwargs.get('anchor_a', (0, 0))
            anchor_b = kwargs.get('anchor_b', (0, 0))
            joint = pymunk.PinJoint(body_a, body_b, anchor_a, anchor_b)
        elif joint_type == 'pivot':
            anchor = kwargs.get('anchor', (0, 0))
            joint = pymunk.PivotJoint(body_a, body_b, anchor)
        elif joint_type == 'spring':
            anchor_a = kwargs.get('anchor_a', (0, 0))
            anchor_b = kwargs.get('anchor_b', (0, 0))
            rest_length = kwargs.get('rest_length', 100.0)
            stiffness = kwargs.get('stiffness', 1000.0)
            damping = kwargs.get('damping', 10.0)
            joint = pymunk.DampedSpring(body_a, body_b, anchor_a, anchor_b, rest_length, stiffness, damping)
        elif joint_type == 'motor':
            rate = kwargs.get('rate', 2.0)
            joint = pymunk.SimpleMotor(body_a, body_b, rate)
        elif joint_type == 'gear':
            phase = kwargs.get('phase', 0.0)
            ratio = kwargs.get('ratio', 1.0)
            joint = pymunk.GearJoint(body_a, body_b, phase, ratio)
        elif joint_type == 'slide':
            anchor_a = kwargs.get('anchor_a', (0, 0))
            anchor_b = kwargs.get('anchor_b', (0, 0))
            min_d = kwargs.get('min', 10.0)
            max_d = kwargs.get('max', 30.0)
            joint = pymunk.SlideJoint(body_a, body_b, anchor_a, anchor_b, min_d, max_d)
        elif joint_type == 'rotarylimit' or joint_type == 'rotary_limit':
            min_angle = kwargs.get('min', -0.5)
            max_angle = kwargs.get('max', 0.5)
            joint = pymunk.RotaryLimitJoint(body_a, body_b, min_angle, max_angle)
        else:
            raise ValueError(f"Unknown joint type: {joint_type}")
        self.space.add(joint)
        return joint

    def raycast(self, a: Tuple[float, float], b: Tuple[float, float], radius: float = 0.0, mask: pymunk.ShapeFilter = None):
        return self.physics_manager.raycast(a, b, radius, mask)

    def overlap_aabb(self, bb: Tuple[float, float, float, float], mask: pymunk.ShapeFilter = None):
        return self.physics_manager.overlap_aabb(bb, mask)

    def shapecast(self, shape: pymunk.Shape, transform: pymunk.Transform = None):
        return self.physics_manager.shapecast(shape, transform)

    def create_motor(self, a: pymunk.Body, b: pymunk.Body, rate: float = 2.0):
        c = pymunk.SimpleMotor(a, b, rate)
        self.space.add(c)
        return c

    def create_gear(self, a: pymunk.Body, b: pymunk.Body, phase: float = 0.0, ratio: float = 1.0):
        c = pymunk.GearJoint(a, b, phase, ratio)
        self.space.add(c)
        return c

    def create_slide(self, a: pymunk.Body, b: pymunk.Body, anchor_a, anchor_b, min_d: float, max_d: float):
        c = pymunk.SlideJoint(a, b, anchor_a, anchor_b, min_d, max_d)
        self.space.add(c)
        return c

    def create_rotary_limit(self, a: pymunk.Body, b: pymunk.Body, min_angle: float, max_angle: float):
        c = pymunk.RotaryLimitJoint(a, b, min_angle, max_angle)
        self.space.add(c)
        return c

    def enable_ccd(self, shape_or_body, enabled: bool = True):
        self.physics_manager.enable_ccd(shape_or_body, enabled)


class CameraAPI:
    def __init__(self, camera):
        self.camera = camera
        
    def get_position(self) -> Tuple[float, float]:
        return self.camera.translation
        
    def set_position(self, position: Tuple[float, float]):
        self.camera.translation = position
        
    def move(self, offset: Tuple[float, float]):
        tx, ty = self.camera.translation
        dx, dy = offset
        self.camera.translation = (tx + dx, ty + dy)
        
    def get_zoom(self) -> float:
        return self.camera.scaling
        
    def set_zoom(self, zoom: float):
        self.camera.scaling = zoom
        if hasattr(self.camera, "target_scaling"):
            self.camera.target_scaling = zoom
        
    def zoom_to_fit(self, rect: Tuple[float, float, float, float], margin: float = 50.0):
        x, y, w, h = rect
        sx = (w + margin * 2) / max(1.0, self.camera.viewport_size[0])
        sy = (h + margin * 2) / max(1.0, self.camera.viewport_size[1])
        scale = 1.0 / max(sx, sy)
        self.set_zoom(scale)
        self.set_position((x + w / 2, y + h / 2))
        
    def screen_to_world(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        return self.camera.screen_to_world(screen_pos)
        
    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[int, int]:
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
            'draw_function': self.gizmos_api.draw_function,
            'draw_sine_wave': self.gizmos_api.draw_sine_wave,
            'draw_radial_grid': self.gizmos_api.draw_radial_grid,
            'draw_crosshair': self.gizmos_api.draw_crosshair,
            'draw_trajectory': self.gizmos_api.draw_trajectory,
            'draw_vectors': self.gizmos_api.draw_vectors,
            'clear_gizmos': self.gizmos_api.clear_all,
            'clear_gizmo_by_id': self.gizmos_api.clear_by_id,
        })
        enhanced_context.update({
            'spawn_circle': self.spawner_api.spawn_circle,
            'spawn_rectangle': self.spawner_api.spawn_rectangle,
            'spawn_polygon': self.spawner_api.spawn_polygon,
            'spawn_chain': self.spawner_api.spawn_chain,
            'create_compound_object': self.spawner_api.create_compound_object,
        })
        enhanced_context.update({
            'play_note': self.synthesizer_api.play_note,
            'play_chord': self.synthesizer_api.play_chord,
            'play_sequence': self.synthesizer_api.play_sequence,
            'play_scale': self.synthesizer_api.play_scale,
            'create_melody': self.synthesizer_api.create_melody,
            'set_audio_effects': self.synthesizer_api.set_effects,
        })
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
            'raycast': self.physics_api.raycast,
            'overlap_aabb': self.physics_api.overlap_aabb,
            'shapecast': self.physics_api.shapecast,
            'create_motor': self.physics_api.create_motor,
            'create_gear': self.physics_api.create_gear,
            'create_slide': self.physics_api.create_slide,
            'create_rotary_limit': self.physics_api.create_rotary_limit,
            'enable_ccd': self.physics_api.enable_ccd,
        })
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
        enhanced_context.update({
            'get_mouse_world_pos': lambda: self.camera.screen_to_world(pygame.mouse.get_pos()),
            'play_sound': self.sound_manager.play,
            'pause': self.physics_manager.toggle_pause,
            'save_world': self.save_load_manager.save_world,
            'load_world': self.save_load_manager.load_world,
            'toggle_grid': lambda: self.ui_manager.toggle_grid(),
            'toggle_debug': lambda: self.ui_manager.toggle_debug(),
            'show_message': lambda msg: self.console.add_output_line_to_log(str(msg)),
        })
        enhanced_context.update({
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
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
