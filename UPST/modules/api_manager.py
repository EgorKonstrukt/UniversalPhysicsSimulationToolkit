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

    def _create_dynamic_shape(self, body: pymunk.Body, shape: pymunk.Shape, friction: float, elasticity: float,
                              color: Optional[Tuple[int, int, int, int]]) -> pymunk.Body:
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or (200, 200, 200, 255)
        self._add_body_shape(body, shape)
        return body

    def _create_static_shape(self, shape: pymunk.Shape, friction: float, elasticity: float, color: Optional[Tuple[int, int, int, int]]) -> pymunk.Shape:
        shape.friction = friction
        shape.elasticity = elasticity
        if color is None:
            c = getattr(self.theme, "platform_color", (200, 200, 200, 255))
            if not isinstance(c, (tuple, list)) or len(c) not in (3, 4):
                c = (200, 200, 200, 255)
            shape.color = tuple(c) if len(c) == 4 else (*c, 255)
        else:
            shape.color = color
        self.space.add(shape)
        self.static_lines.append(shape)
        return shape

    def create_box(self, pos=(0, 0), size=(1, 1), angle=0, mass=1.0, friction=0.7, elasticity=0.5, color=None,
                   name="Box") -> pymunk.Body:
        w, h = size
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w, h)), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        body.angle = angle
        shape = pymunk.Poly.create_box(body, (w, h))
        return self._create_dynamic_shape(body, shape, friction, elasticity, color)

    def create_circle(self, pos=(0, 0), radius=1.0, mass=1.0, friction=0.7, elasticity=0.5, color=None,
                      name="Circle") -> pymunk.Body:
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, radius), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        shape = pymunk.Circle(body, radius)
        return self._create_dynamic_shape(body, shape, friction, elasticity, color)

    def create_segment(self, a=(0, 0), b=(1, 0), thickness=0.1, mass=1.0, friction=0.7, elasticity=0.5, color=None,
                       name="Segment") -> pymunk.Body:
        body = pymunk.Body(mass, pymunk.moment_for_segment(mass, a, b, thickness), body_type=pymunk.Body.DYNAMIC)
        shape = pymunk.Segment(body, a, b, thickness)
        return self._create_dynamic_shape(body, shape, friction, elasticity, color)

    def create_static_box(self, pos=(0, 0), size=(1, 1), angle=0, friction=0.7, elasticity=0.5, color=None,
                          name="StaticBox") -> pymunk.Shape:
        w, h = size
        verts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
        shape = pymunk.Poly(self.static_body, verts, transform=pymunk.Transform.translation(*pos))
        return self._create_static_shape(shape, friction, elasticity, color)

    def create_static_circle(self, pos=(0, 0), radius=1.0, friction=0.7, elasticity=0.5, color=None,
                             name="StaticCircle") -> pymunk.Shape:
        shape = pymunk.Circle(self.static_body, radius, offset=pos)
        return self._create_static_shape(shape, friction, elasticity, color)

    def create_static_segment(self, a=(0, 0), b=(1, 0), thickness=0.1, friction=0.7, elasticity=0.5, color=None,
                              name="StaticSegment") -> pymunk.Shape:
        shape = pymunk.Segment(self.static_body, a, b, thickness)
        return self._create_static_shape(shape, friction, elasticity, color)

    def delete(self, obj: Union[pymunk.Body, pymunk.Shape]):
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

    def add_tag(self, obj: Union[pymunk.Body, pymunk.Shape], tag: str):
        if not hasattr(obj, 'tags'): obj.tags = set()
        obj.tags.add(tag)

    def remove_tag(self, obj: Union[pymunk.Body, pymunk.Shape], tag: str):
        if hasattr(obj, 'tags'): obj.tags.discard(tag)

    def set_transform(self, obj: pymunk.Body, pos: Optional[Tuple[float, float]] = None, angle: Optional[float] = None):
        if isinstance(obj, pymunk.Body):
            if pos is not None: obj.position = pos
            if angle is not None: obj.angle = angle
        else:
            Debug.log_warning("Transform set on non-body", "Scripting")

    def get_position(self, obj: Union[pymunk.Body, pymunk.Shape]) -> Tuple[float, float]:
        return getattr(obj, 'position', (0, 0))

    def get_angle(self, obj: Union[pymunk.Body, pymunk.Shape]) -> float:
        return getattr(obj, 'angle', 0.0)

    def apply_force(self, obj: pymunk.Body, force: Tuple[float, float], point: Optional[Tuple[float, float]] = None):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            obj.apply_force_at_world_point(force, point or obj.position)

    def apply_impulse(self, obj: pymunk.Body, impulse: Tuple[float, float],
                      point: Optional[Tuple[float, float]] = None):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            obj.apply_impulse_at_world_point(impulse, point or obj.position)

    def set_velocity(self, obj: pymunk.Body, velocity: Tuple[float, float]):
        if isinstance(obj, pymunk.Body): obj.velocity = velocity

    def get_velocity(self, obj: Union[pymunk.Body, pymunk.Shape]) -> Tuple[float, float]:
        return getattr(obj, 'velocity', (0, 0))

    def set_angular_velocity(self, obj: pymunk.Body, omega: float):
        if isinstance(obj, pymunk.Body): obj.angular_velocity = omega

    def get_angular_velocity(self, obj: Union[pymunk.Body, pymunk.Shape]) -> float:
        return getattr(obj, 'angular_velocity', 0.0)

    def set_mass(self, obj: pymunk.Body, mass: float):
        if isinstance(obj, pymunk.Body): obj.mass = mass

    def set_friction(self, obj: pymunk.Shape, friction: float):
        if isinstance(obj, pymunk.Shape): obj.friction = friction

    def set_elasticity(self, obj: pymunk.Shape, elasticity: float):
        if isinstance(obj, pymunk.Shape): obj.elasticity = elasticity

    def set_color(self, obj: Union[pymunk.Body, pymunk.Shape],
                  color: Union[Tuple[int, int, int], Tuple[int, int, int, int]]):
        if not isinstance(color, (tuple, list)) or len(color) not in (3, 4):
            Debug.log_error("Color must be (R,G,B) or (R,G,B,A)", "Scripting")
            return
        c = color if len(color) == 4 else (*color, 255)
        if isinstance(obj, pymunk.Shape):
            obj.color = c
        elif isinstance(obj, pymunk.Body):
            for s in obj.shapes: s.color = c

    def get_color(self, obj: Union[pymunk.Body, pymunk.Shape]) -> Tuple[int, int, int, int]:
        if isinstance(obj, pymunk.Shape):
            return getattr(obj, 'color', (200, 200, 200, 255))
        elif isinstance(obj, pymunk.Body) and obj.shapes:
            return getattr(obj.shapes[0], 'color', (200, 200, 200, 255))
        return (200, 200, 200, 255)

    def attach_script(self, obj: Union[pymunk.Body, pymunk.Shape], code: str, name: str = "AttachedScript"):
        if isinstance(obj, (pymunk.Body, pymunk.Shape)):
            self.script_manager.add_script_to(obj, code, name, start_immediately=True)

    def get_script(self, obj: Union[pymunk.Body, pymunk.Shape], name: str):
        return self.script_manager.get_script_by_name(owner=obj, name=name)

    def remove_script(self, obj: Union[pymunk.Body, pymunk.Shape], name: str):
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

    def _add_body_shape(self, body: pymunk.Body, shape: pymunk.Shape):
        self.space.add(body, shape)
        if not hasattr(body, 'hierarchy_node'):
            from UPST.modules.hierarchy import HierarchyNode
            body.hierarchy_node = HierarchyNode(name=f"Body_{id(body)}", body=body)

    def _remove_body(self, body: pymunk.Body):
        if not isinstance(body, pymunk.Body) or body not in self.space.bodies:
            return
        self.script_manager.remove_scripts_by_owner(body)
        shapes = [s for s in body.shapes if s in self.space.shapes]
        if shapes:
            self.space.remove(*shapes)
        self.space.remove(body)

    def _remove_shape_body(self, shape: pymunk.Shape):
        if not isinstance(shape, pymunk.Shape) or shape not in self.space.shapes:
            return
        self.space.remove(shape)
        body = shape.body
        if body != self.static_body and body in self.space.bodies and not any(
                s in self.space.shapes for s in body.shapes):
            self.script_manager.remove_scripts_by_owner(body)
            self.space.remove(body)

    def _find_physics_manager(self) -> Optional[PhysicsManager]:
        for obj in self.space.bodies:
            if hasattr(obj, '_physics_manager_ref'):
                return obj._physics_manager_ref
        return None