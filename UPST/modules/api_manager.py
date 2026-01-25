from typing import Any, Optional, Tuple, List, Union
import pymunk
from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.physics import physics_manager
from UPST.physics.physics_manager import PhysicsManager
from UPST.scripting import script_manager


class APIManager:
    def __init__(self, space, script_manager):
        self.space = space
        self.script_manager = script_manager
        self.static_body = space.static_body
        self.theme = config.world.themes.get(config.world.current_theme, {})
        self.static_lines = []

    def create_box(self, pos=(0, 0), size=(1, 1), angle=0, mass=1.0, friction=0.7,
                   elasticity=0.5, color=None, parent=None, name="Box"):
        w, h = size
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w, h)), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        body.angle = angle
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or (200, 200, 200, 255)
        self._add_body_shape(body, shape)
        return body

    def create_circle(self, pos=(0, 0), radius=1.0, mass=1.0, friction=0.7,
                      elasticity=0.5, color=None, parent=None, name="Circle"):
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, radius), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        shape = pymunk.Circle(body, radius)
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or (200, 200, 200, 255)
        self._add_body_shape(body, shape)
        return body

    def create_segment(self, a=(0, 0), b=(1, 0), thickness=0.1, mass=1.0,
                       friction=0.7, elasticity=0.5, color=None, parent=None, name="Segment"):
        body = pymunk.Body(mass, pymunk.moment_for_segment(mass, a, b, thickness),
                           body_type=pymunk.Body.DYNAMIC)
        shape = pymunk.Segment(body, a, b, thickness)
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or (200, 200, 200, 255)
        self._add_body_shape(body, shape)
        return body

    def create_static_box(self, pos=(0, 0), size=(1, 1), angle=0, friction=0.7,
                          elasticity=0.5, color=None, parent=None, name="StaticBox"):
        w, h = size
        verts = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
        shape = pymunk.Poly(self.static_body, verts, transform=pymunk.Transform.translation(*pos))
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or getattr(self.theme, "platform_color", (200, 200, 200, 255))
        self.space.add(shape)
        self.static_lines.append(shape)
        return shape

    def create_static_circle(self, pos=(0, 0), radius=1.0, friction=0.7,
                             elasticity=0.5, color=None, parent=None, name="StaticCircle"):
        shape = pymunk.Circle(self.static_body, radius, offset=pos)
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or getattr(self.theme, "platform_color", (200, 200, 200, 255))
        self.space.add(shape)
        self.static_lines.append(shape)
        return shape

    def create_static_segment(self, a=(0, 0), b=(1, 0), thickness=0.1, friction=0.7,
                              elasticity=0.5, color=None, parent=None, name="StaticSegment"):
        shape = pymunk.Segment(self.static_body, a, b, thickness)
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or getattr(self.theme, "platform_color", (200, 200, 200, 255))
        self.space.add(shape)
        self.static_lines.append(shape)
        return shape

    def delete(self, obj):
        if isinstance(obj, pymunk.Body):
            self._remove_body(obj)
        elif isinstance(obj, pymunk.Shape):
            self._remove_shape_body(obj)
        else:
            Debug.log_error("Cannot delete non-physics object", "Scripting")

    def get_all(self) -> List[Union[pymunk.Body, pymunk.Shape]]:
        return list(self.space.bodies) + list(self.space.shapes)

    def find_by_name(self, name: str) -> Optional[pymunk.Body]:
        for b in self.space.bodies:
            if getattr(b, 'name', None) == name:
                return b
        return None

    def find_by_tag(self, tag: str) -> List[pymunk.Body]:
        return [b for b in self.space.bodies if hasattr(b, 'tags') and tag in b.tags]

    def add_tag(self, obj, tag: str):
        if not hasattr(obj, 'tags'): obj.tags = set()
        obj.tags.add(tag)

    def remove_tag(self, obj, tag: str):
        if hasattr(obj, 'tags'): obj.tags.discard(tag)

    def set_transform(self, obj, pos=None, angle=None, scale=None):
        if isinstance(obj, pymunk.Body):
            if pos is not None: obj.position = pos
            if angle is not None: obj.angle = angle
        else:
            Debug.log_warning("Transform set on non-body", "Scripting")

    def get_position(self, obj) -> Tuple[float, float]:
        return getattr(obj, 'position', (0, 0))

    def get_angle(self, obj) -> float:
        return getattr(obj, 'angle', 0.0)

    def apply_force(self, obj, force, point=None):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            if point is None: point = obj.position
            obj.apply_force_at_world_point(force, point)

    def apply_impulse(self, obj, impulse, point=None):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            if point is None: point = obj.position
            obj.apply_impulse_at_world_point(impulse, point)

    def set_velocity(self, obj, velocity):
        if isinstance(obj, pymunk.Body): obj.velocity = velocity

    def get_velocity(self, obj) -> Tuple[float, float]:
        return getattr(obj, 'velocity', (0, 0))

    def set_angular_velocity(self, obj, omega):
        if isinstance(obj, pymunk.Body): obj.angular_velocity = omega

    def get_angular_velocity(self, obj) -> float:
        return getattr(obj, 'angular_velocity', 0.0)

    def set_mass(self, obj, mass):
        if isinstance(obj, pymunk.Body): obj.mass = mass

    def set_friction(self, obj, friction):
        if isinstance(obj, pymunk.Shape): obj.friction = friction

    def set_elasticity(self, obj, elasticity):
        if isinstance(obj, pymunk.Shape): obj.elasticity = elasticity

    def set_color(self, obj, color):
        if not isinstance(color, (tuple, list)) or len(color) not in (3, 4):
            Debug.log_error("Color must be (R,G,B) or (R,G,B,A)", "Scripting")
            return
        c = color if len(color) == 4 else (*color, 255)
        if isinstance(obj, pymunk.Shape):
            obj.color = c
        elif isinstance(obj, pymunk.Body):
            for s in obj.shapes: s.color = c

    def get_color(self, obj) -> Tuple[int, int, int, int]:
        if isinstance(obj, pymunk.Shape):
            return getattr(obj, 'color', (200, 200, 200, 255))
        elif isinstance(obj, pymunk.Body) and obj.shapes:
            return getattr(obj.shapes[0], 'color', (200, 200, 200, 255))
        return (200, 200, 200, 255)

    def attach_script(self, obj, code: str, name: str = "AttachedScript"):
        if isinstance(obj, (pymunk.Body, pymunk.Shape)):
            self.script_manager.add_script_to(obj, code, name, start_immediately=True)

    def get_script(self, obj, name: str):
        return self.script_manager.get_script_by_name(owner=obj, name=name)

    def remove_script(self, obj, name: str):
        self.script_manager.remove_script_by_name(owner=obj, name=name)

    def pause_simulation(self):
        pm = self._find_physics_manager()
        if pm: pm.pause_physics()

    def resume_simulation(self):
        pm = self._find_physics_manager()
        if pm: pm.resume_physics()

    def set_simulation_speed(self, speed: float):
        pm = self._find_physics_manager()
        if pm: pm.set_simulation_speed_multiplier(speed)

    def get_simulation_time(self) -> float:
        pm = self._find_physics_manager()
        return pm.simulation_time if pm else 0.0

    def _add_body_shape(self, body, shape):
        self.space.add(body, shape)
        if not hasattr(body, 'hierarchy_node'):
            from UPST.modules.hierarchy import HierarchyNode
            body.hierarchy_node = HierarchyNode(name=f"Body_{id(body)}", body=body)

    def _remove_body(self, body):
        if not isinstance(body, pymunk.Body):
            Debug.log_warning("remove_body called with non-Body object", "Physics")
            return
        if body not in self.space.bodies:
            Debug.log_info(f"Body {body.__hash__()} already removed or not in space; skipping.", "Physics")
            return
        self.script_manager.remove_scripts_by_owner(body)
        shapes_to_remove = [s for s in list(body.shapes) if s in self.space.shapes]
        if shapes_to_remove:
            self.space.remove(*shapes_to_remove)
        self.space.remove(body)

    def _remove_shape_body(self, shape):
        if not isinstance(shape, pymunk.Shape) or shape not in self.space.shapes:
            return
        body = shape.body
        self.space.remove(shape)
        if body != self.static_body and body in self.space.bodies and not any(s in self.space.shapes for s in body.shapes):
            self.script_manager.remove_scripts_by_owner(body)
            self.space.remove(body)

    def _find_physics_manager(self):
        for obj in self.space.bodies:
            if hasattr(obj, '_physics_manager_ref'):
                return obj._physics_manager_ref
        return None