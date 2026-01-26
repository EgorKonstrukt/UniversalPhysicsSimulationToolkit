from typing import Any, Optional, Tuple, List, Union, Dict, Callable
import pymunk
from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.physics import physics_manager
from UPST.physics.physics_manager import PhysicsManager
from UPST.scripting import script_manager
import math
import random


class APIManager:
    def __init__(self, space, script_manager):
        self.space = space
        self.script_manager = script_manager
        self.static_body = space.static_body
        self.theme = config.world.themes.get(config.world.current_theme, {})
        self.static_lines = []
        self._collision_handlers = {}
        self._joints = {}
        self._sensors = set()

    # ==================== BASIC SHAPE CREATION ====================

    def _create_dynamic_shape(self, body: pymunk.Body, shape: pymunk.Shape, friction: float, elasticity: float,
                              color: Optional[Tuple[int, int, int, int]]) -> pymunk.Body:
        shape.friction = friction
        shape.elasticity = elasticity
        shape.color = color or (200, 200, 200, 255)
        self._add_body_shape(body, shape)
        return body

    def _create_static_shape(self, shape: pymunk.Shape, friction: float, elasticity: float,
                             color: Optional[Tuple[int, int, int, int]]) -> pymunk.Shape:
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

    def create_box(self, pos=(0, 0), size=(1, 1), angle=0, mass=1.0, friction=0.7, elasticity=0.5,
                   color=None, name="Box", layer=1, group=0, sensor=False) -> pymunk.Body:
        w, h = size
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w, h)), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        body.angle = angle
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.filter = pymunk.ShapeFilter(group=group, categories=layer, mask=layer)
        shape.sensor = sensor
        if sensor:
            self._sensors.add(shape)
        return self._create_dynamic_shape(body, shape, friction, elasticity, color)

    def create_circle(self, pos=(0, 0), radius=1.0, mass=1.0, friction=0.7, elasticity=0.5, color=None,
                      name="Circle", layer=1, group=0, sensor=False) -> pymunk.Body:
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, radius), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        shape = pymunk.Circle(body, radius)
        shape.filter = pymunk.ShapeFilter(group=group, categories=layer, mask=layer)
        shape.sensor = sensor
        if sensor:
            self._sensors.add(shape)
        return self._create_dynamic_shape(body, shape, friction, elasticity, color)

    def create_polygon(self, pos=(0, 0), vertices=None, mass=1.0, friction=0.7, elasticity=0.5, color=None,
                       name="Polygon", layer=1, group=0, sensor=False) -> pymunk.Body:
        if vertices is None:
            vertices = [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]

        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, vertices), body_type=pymunk.Body.DYNAMIC)
        body.position = pos
        shape = pymunk.Poly(body, vertices)
        shape.filter = pymunk.ShapeFilter(group=group, categories=layer, mask=layer)
        shape.sensor = sensor
        if sensor:
            self._sensors.add(shape)
        return self._create_dynamic_shape(body, shape, friction, elasticity, color)

    # ==================== STATIC SHAPES ====================

    def create_static_box(self, pos=(0, 0), size=(1, 1), angle=0, friction=0.7, elasticity=0.5, color=None,
                          name="StaticBox", layer=1, group=0) -> pymunk.Shape:
        w, h = size
        verts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
        shape = pymunk.Poly(self.static_body, verts, transform=pymunk.Transform.translation(*pos))
        shape.filter = pymunk.ShapeFilter(group=group, categories=layer, mask=layer)
        return self._create_static_shape(shape, friction, elasticity, color)

    def create_static_circle(self, pos=(0, 0), radius=1.0, friction=0.7, elasticity=0.5, color=None,
                             name="StaticCircle", layer=1, group=0) -> pymunk.Shape:
        shape = pymunk.Circle(self.static_body, radius, offset=pos)
        shape.filter = pymunk.ShapeFilter(group=group, categories=layer, mask=layer)
        return self._create_static_shape(shape, friction, elasticity, color)

    def create_static_segment(self, a=(0, 0), b=(1, 0), thickness=0.1, friction=0.7, elasticity=0.5, color=None,
                              name="StaticSegment", layer=1, group=0) -> pymunk.Shape:
        shape = pymunk.Segment(self.static_body, a, b, thickness)
        shape.filter = pymunk.ShapeFilter(group=group, categories=layer, mask=layer)
        return self._create_static_shape(shape, friction, elasticity, color)

    # ==================== KINEMATIC BODIES ====================

    def create_kinematic_box(self, pos=(0, 0), size=(1, 1), angle=0, color=None, name="KinematicBox") -> pymunk.Body:
        w, h = size
        body = pymunk.Body(1, pymunk.moment_for_box(1, (w, h)), body_type=pymunk.Body.KINEMATIC)
        body.position = pos
        body.angle = angle
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.color = color or (150, 150, 255, 255)
        self._add_body_shape(body, shape)
        return body

    # ==================== JOINTS AND CONSTRAINTS ====================

    def create_pin_joint(self, body_a: pymunk.Body, body_b: pymunk.Body,
                         anchor_a: Tuple[float, float], anchor_b: Tuple[float, float]) -> pymunk.Constraint:
        joint = pymunk.PinJoint(body_a, body_b, anchor_a, anchor_b)
        self.space.add(joint)
        return joint

    def create_slide_joint(self, body_a: pymunk.Body, body_b: pymunk.Body,
                           anchor_a: Tuple[float, float], anchor_b: Tuple[float, float],
                           min: float, max: float) -> pymunk.Constraint:
        joint = pymunk.SlideJoint(body_a, body_b, anchor_a, anchor_b, min, max)
        self.space.add(joint)
        return joint

    def create_pivot_joint(self, body_a: pymunk.Body, body_b: pymunk.Body,
                           anchor: Tuple[float, float]) -> pymunk.Constraint:
        joint = pymunk.PivotJoint(body_a, body_b, anchor)
        self.space.add(joint)
        return joint

    def create_spring(self, body_a: pymunk.Body, body_b: pymunk.Body,
                      anchor_a: Tuple[float, float], anchor_b: Tuple[float, float],
                      rest_length: float, stiffness: float, damping: float) -> pymunk.Constraint:
        joint = pymunk.DampedSpring(body_a, body_b, anchor_a, anchor_b, rest_length, stiffness, damping)
        self.space.add(joint)
        return joint

    def create_motor(self, body_a: pymunk.Body, body_b: pymunk.Body, rate: float) -> pymunk.Constraint:
        joint = pymunk.SimpleMotor(body_a, body_b, rate)
        self.space.add(joint)
        return joint

    def remove_joint(self, joint: pymunk.Constraint):
        if joint in self.space.constraints:
            self.space.remove(joint)

    # ==================== COLLISION HANDLING ====================

    def add_collision_handler(self, collision_type_a: int, collision_type_b: int,
                              begin_func: Callable = None, pre_solve_func: Callable = None,
                              post_solve_func: Callable = None, separate_func: Callable = None):
        """Add collision handler for specific collision types"""
        handler = self.space.add_collision_handler(collision_type_a, collision_type_b)

        if begin_func:
            handler.begin = begin_func
        if pre_solve_func:
            handler.pre_solve = pre_solve_func
        if post_solve_func:
            handler.post_solve = post_solve_func
        if separate_func:
            handler.separate = separate_func

        key = (collision_type_a, collision_type_b)
        self._collision_handlers[key] = handler
        return handler

    def set_collision_type(self, obj: Union[pymunk.Body, pymunk.Shape], collision_type: int):
        """Set collision type for body or shape"""
        if isinstance(obj, pymunk.Shape):
            obj.collision_type = collision_type
        elif isinstance(obj, pymunk.Body):
            for shape in obj.shapes:
                shape.collision_type = collision_type

    # ==================== QUERY METHODS ====================

    def raycast(self, start: Tuple[float, float], end: Tuple[float, float],
                radius: float = 0.0, shape_filter=None) -> Optional[pymunk.SegmentQueryInfo]:
        """Cast a ray and return first hit"""
        return self.space.segment_query_first(start, end, radius, shape_filter)

    def raycast_all(self, start: Tuple[float, float], end: Tuple[float, float],
                    radius: float = 0.0, shape_filter=None) -> List[pymunk.SegmentQueryInfo]:
        """Cast a ray and return all hits"""
        hits = []

        def query_func(shape, point, normal, alpha):
            hits.append(pymunk.SegmentQueryInfo(shape, point, normal, alpha))
            return 1

        self.space.segment_query(start, end, radius, shape_filter, query_func)
        return hits

    def point_query(self, point: Tuple[float, float], max_distance: float = 0.0,
                    shape_filter=None) -> Optional[pymunk.PointQueryInfo]:
        """Query nearest shape at point"""
        return self.space.point_query_nearest(point, max_distance, shape_filter)

    def point_query_all(self, point: Tuple[float, float], max_distance: float = 0.0,
                        shape_filter=None) -> List[pymunk.PointQueryInfo]:
        """Query all shapes at point"""
        hits = []

        def query_func(shape, point, distance, gradient):
            hits.append(pymunk.PointQueryInfo(shape, point, distance, gradient))

        self.space.point_query(point, max_distance, shape_filter, query_func)
        return hits

    def aabb_query(self, bb: Tuple[float, float, float, float],
                   shape_filter=None) -> List[pymunk.Shape]:
        """Query shapes in bounding box"""
        shapes = []
        bb_obj = pymunk.BB(bb[0], bb[1], bb[2], bb[3])

        def query_func(shape):
            shapes.append(shape)

        self.space.bb_query(bb_obj, query_func, shape_filter)
        return shapes

    # ==================== FORCES AND IMPULSES ====================

    def apply_force(self, obj: pymunk.Body, force: Tuple[float, float],
                    point: Optional[Tuple[float, float]] = None):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            obj.apply_force_at_world_point(force, point or obj.position)

    def apply_impulse(self, obj: pymunk.Body, impulse: Tuple[float, float],
                      point: Optional[Tuple[float, float]] = None):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            obj.apply_impulse_at_world_point(impulse, point or obj.position)

    def apply_local_force(self, obj: pymunk.Body, force: Tuple[float, float],
                          point: Optional[Tuple[float, float]] = None):
        """Apply force in local coordinates"""
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            world_force = obj.rotation_vector.rotated(force)
            obj.apply_force_at_world_point(world_force, point or obj.position)

    def apply_torque(self, obj: pymunk.Body, torque: float):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            obj.torque += torque

    def apply_angular_impulse(self, obj: pymunk.Body, impulse: float):
        if isinstance(obj, pymunk.Body) and obj.body_type == pymunk.Body.DYNAMIC:
            obj.angular_velocity += impulse / obj.moment

    # ==================== BODY MANIPULATION ====================

    def set_transform(self, obj: pymunk.Body, pos: Optional[Tuple[float, float]] = None,
                      angle: Optional[float] = None):
        if isinstance(obj, pymunk.Body):
            if pos is not None:
                obj.position = pos
            if angle is not None:
                obj.angle = angle
        else:
            Debug.log_warning("Transform set on non-body", "Scripting")

    def set_velocity(self, obj: pymunk.Body, velocity: Tuple[float, float]):
        if isinstance(obj, pymunk.Body):
            obj.velocity = velocity

    def set_angular_velocity(self, obj: pymunk.Body, omega: float):
        if isinstance(obj, pymunk.Body):
            obj.angular_velocity = omega

    def set_mass(self, obj: pymunk.Body, mass: float):
        if isinstance(obj, pymunk.Body):
            obj.mass = mass
            # Recalculate moment of inertia
            if obj.shapes:
                total_moment = 0
                for shape in obj.shapes:
                    if isinstance(shape, pymunk.Circle):
                        total_moment += pymunk.moment_for_circle(mass, 0, shape.radius)
                    elif isinstance(shape, pymunk.Poly):
                        total_moment += pymunk.moment_for_poly(mass, shape.get_vertices())
                if total_moment > 0:
                    obj.moment = total_moment

    def set_friction(self, obj: pymunk.Shape, friction: float):
        if isinstance(obj, pymunk.Shape):
            obj.friction = friction

    def set_elasticity(self, obj: pymunk.Shape, elasticity: float):
        if isinstance(obj, pymunk.Shape):
            obj.elasticity = elasticity

    # ==================== PHYSICS PROPERTIES ====================

    def get_kinetic_energy(self, obj: pymunk.Body) -> float:
        """Calculate kinetic energy of body"""
        if isinstance(obj, pymunk.Body):
            linear_ke = 0.5 * obj.mass * obj.velocity.length ** 2
            angular_ke = 0.5 * obj.moment * obj.angular_velocity ** 2
            return linear_ke + angular_ke
        return 0.0

    def get_momentum(self, obj: pymunk.Body) -> Tuple[float, float]:
        """Calculate linear momentum of body"""
        if isinstance(obj, pymunk.Body):
            return (obj.mass * obj.velocity.x, obj.mass * obj.velocity.y)
        return (0, 0)

    def get_angular_momentum(self, obj: pymunk.Body) -> float:
        """Calculate angular momentum of body"""
        if isinstance(obj, pymunk.Body):
            return obj.moment * obj.angular_velocity
        return 0.0

    def get_center_of_mass(self, obj: pymunk.Body) -> Tuple[float, float]:
        """Get center of mass of body (world coordinates)"""
        if isinstance(obj, pymunk.Body):
            return obj.position
        return (0, 0)

    # ==================== SPACE MANAGEMENT ====================

    def delete(self, obj: Union[pymunk.Body, pymunk.Shape, pymunk.Constraint]):
        if isinstance(obj, pymunk.Body):
            self._remove_body(obj)
        elif isinstance(obj, pymunk.Shape):
            self._remove_shape_body(obj)
        elif isinstance(obj, pymunk.Constraint):
            self.remove_joint(obj)
        else:
            Debug.log_error("Cannot delete non-physics object", "Scripting")

    def clear_all(self):
        """Clear all dynamic objects from space"""
        for body in list(self.space.bodies):
            if body != self.static_body:
                self._remove_body(body)

        for shape in list(self.space.shapes):
            if shape.body == self.static_body:
                self.space.remove(shape)

        self.static_lines.clear()

    def get_all(self) -> List[Union[pymunk.Body, pymunk.Shape]]:
        return list(self.space.bodies) + list(self.space.shapes)

    def get_bodies(self) -> List[pymunk.Body]:
        return list(self.space.bodies)

    def get_shapes(self) -> List[pymunk.Shape]:
        return list(self.space.shapes)

    def get_joints(self) -> List[pymunk.Constraint]:
        return list(self.space.constraints)

    # ==================== SEARCH AND FILTER ====================

    def find_by_name(self, name: str) -> Optional[pymunk.Body]:
        for b in self.space.bodies:
            if getattr(b, 'name', None) == name:
                return b
        return None

    def find_by_tag(self, tag: str) -> List[pymunk.Body]:
        return [b for b in self.space.bodies if hasattr(b, 'tags') and tag in b.tags]

    def find_by_type(self, shape_type: type) -> List[pymunk.Shape]:
        """Find all shapes of specific type"""
        return [s for s in self.space.shapes if isinstance(s, shape_type)]

    def find_in_radius(self, center: Tuple[float, float], radius: float) -> List[pymunk.Body]:
        """Find bodies within radius"""
        bodies = []
        for body in self.space.bodies:
            if body != self.static_body:
                distance = math.sqrt((body.position.x - center[0]) ** 2 +
                                     (body.position.y - center[1]) ** 2)
                if distance <= radius:
                    bodies.append(body)
        return bodies

    # ==================== TAGS AND METADATA ====================

    def add_tag(self, obj: Union[pymunk.Body, pymunk.Shape], tag: str):
        if not hasattr(obj, 'tags'):
            obj.tags = set()
        obj.tags.add(tag)

    def remove_tag(self, obj: Union[pymunk.Body, pymunk.Shape], tag: str):
        if hasattr(obj, 'tags'):
            obj.tags.discard(tag)

    def has_tag(self, obj: Union[pymunk.Body, pymunk.Shape], tag: str) -> bool:
        return hasattr(obj, 'tags') and tag in obj.tags

    def set_metadata(self, obj: Union[pymunk.Body, pymunk.Shape], key: str, value: Any):
        if not hasattr(obj, 'metadata'):
            obj.metadata = {}
        obj.metadata[key] = value

    def get_metadata(self, obj: Union[pymunk.Body, pymunk.Shape], key: str, default=None) -> Any:
        return getattr(obj, 'metadata', {}).get(key, default)

    # ==================== VISUAL PROPERTIES ====================

    def set_color(self, obj: Union[pymunk.Body, pymunk.Shape],
                  color: Union[Tuple[int, int, int], Tuple[int, int, int, int]]):
        if not isinstance(color, (tuple, list)) or len(color) not in (3, 4):
            Debug.log_error("Color must be (R,G,B) or (R,G,B,A)", "Scripting")
            return
        c = color if len(color) == 4 else (*color, 255)
        if isinstance(obj, pymunk.Shape):
            obj.color = c
        elif isinstance(obj, pymunk.Body):
            for s in obj.shapes:
                s.color = c

    def get_color(self, obj: Union[pymunk.Body, pymunk.Shape]) -> Tuple[int, int, int, int]:
        if isinstance(obj, pymunk.Shape):
            return getattr(obj, 'color', (200, 200, 200, 255))
        elif isinstance(obj, pymunk.Body) and obj.shapes:
            return getattr(obj.shapes[0], 'color', (200, 200, 200, 255))
        return (200, 200, 200, 255)

    def set_visibility(self, obj: Union[pymunk.Body, pymunk.Shape], visible: bool):
        """Set visibility for rendering"""
        if isinstance(obj, pymunk.Shape):
            obj.visible = visible
        elif isinstance(obj, pymunk.Body):
            for shape in obj.shapes:
                shape.visible = visible

    # ==================== SCRIPT MANAGEMENT ====================

    def attach_script(self, obj: Union[pymunk.Body, pymunk.Shape], code: str, name: str = "AttachedScript"):
        if isinstance(obj, (pymunk.Body, pymunk.Shape)):
            self.script_manager.add_script_to(obj, code, name, start_immediately=True)

    def get_script(self, obj: Union[pymunk.Body, pymunk.Shape], name: str):
        return self.script_manager.get_script_by_name(owner=obj, name=name)

    def remove_script(self, obj: Union[pymunk.Body, pymunk.Shape], name: str):
        self.script_manager.remove_script_by_name(owner=obj, name=name)

    def get_all_scripts(self, obj: Union[pymunk.Body, pymunk.Shape]) -> List:
        """Get all scripts attached to object"""
        return self.script_manager.get_scripts_by_owner(obj)

    # ==================== SIMULATION CONTROL ====================

    def pause_simulation(self):
        pm = self._find_physics_manager()
        if pm:
            pm.pause_physics()

    def resume_simulation(self):
        pm = self._find_physics_manager()
        if pm:
            pm.resume_physics()

    def set_simulation_speed(self, speed: float):
        pm = self._find_physics_manager()
        if pm:
            pm.set_simulation_speed_multiplier(speed)

    def get_simulation_time(self) -> float:
        pm = self._find_physics_manager()
        return pm.simulation_time if pm else 0.0

    def set_gravity(self, x: float, y: float):
        """Set gravity vector"""
        self.space.gravity = (x, y)

    def get_gravity(self) -> Tuple[float, float]:
        """Get current gravity vector"""
        return self.space.gravity

    def set_damping(self, damping: float):
        """Set space damping"""
        self.space.damping = damping

    # ==================== UTILITY FUNCTIONS ====================

    def distance_between(self, obj1: Union[pymunk.Body, Tuple[float, float]],
                         obj2: Union[pymunk.Body, Tuple[float, float]]) -> float:
        """Calculate distance between two bodies or points"""
        if isinstance(obj1, pymunk.Body):
            pos1 = obj1.position
        else:
            pos1 = obj1

        if isinstance(obj2, pymunk.Body):
            pos2 = obj2.position
        else:
            pos2 = obj2

        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        return math.sqrt(dx * dx + dy * dy)

    def angle_between(self, obj1: pymunk.Body, obj2: pymunk.Body) -> float:
        """Calculate angle from obj1 to obj2"""
        dx = obj2.position.x - obj1.position.x
        dy = obj2.position.y - obj1.position.y
        return math.atan2(dy, dx)

    def vector_towards(self, from_obj: pymunk.Body, to_obj: pymunk.Body,
                       normalize: bool = True) -> Tuple[float, float]:
        """Get vector from one object to another"""
        dx = to_obj.position.x - from_obj.position.x
        dy = to_obj.position.y - from_obj.position.y

        if normalize and (dx != 0 or dy != 0):
            length = math.sqrt(dx * dx + dy * dy)
            dx /= length
            dy /= length

        return (dx, dy)

    def get_random_position(self, bounds: Tuple[float, float, float, float] = None) -> Tuple[float, float]:
        """Get random position within bounds or screen"""
        if bounds is None:
            bounds = (0, 0, config.app.screen_width, config.app.screen_height)

        x = random.uniform(bounds[0], bounds[2])
        y = random.uniform(bounds[1], bounds[3])
        return (x, y)

    # ==================== INTERNAL METHODS ====================

    def _add_body_shape(self, body: pymunk.Body, shape: pymunk.Shape):
        self.space.add(body, shape)
        if not hasattr(body, 'hierarchy_node'):
            from UPST.modules.hierarchy import HierarchyNode
            body.hierarchy_node = HierarchyNode(name=f"Body_{id(body)}", body=body)

    def _remove_body(self, body: pymunk.Body):
        if not isinstance(body, pymunk.Body) or body not in self.space.bodies:
            return
        for joint in list(self.space.constraints):
            if joint.a == body or joint.b == body:
                self.space.remove(joint)
        self.script_manager.remove_scripts_by_owner(body)
        shapes = [s for s in body.shapes if s in self.space.shapes]
        if shapes:
            self.space.remove(*shapes)
        self.space.remove(body)

    def _remove_shape_body(self, shape: pymunk.Shape):
        if not isinstance(shape, pymunk.Shape) or shape not in self.space.shapes:
            return
        self.space.remove(shape)
        if shape in self._sensors:
            self._sensors.remove(shape)
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

    # ==================== DEBUG AND INFO ====================

    def print_space_info(self):
        """Print information about space contents"""
        print(f"Bodies: {len(self.space.bodies)}")
        print(f"Shapes: {len(self.space.shapes)}")
        print(f"Constraints: {len(self.space.constraints)}")
        print(f"Gravity: {self.space.gravity}")
        print(f"Damping: {self.space.damping}")

    def get_space_stats(self) -> Dict[str, int]:
        """Get statistics about space"""
        return {
            'bodies': len(self.space.bodies),
            'shapes': len(self.space.shapes),
            'constraints': len(self.space.constraints),
            'static_shapes': len(self.static_lines),
            'sensors': len(self._sensors)
        }