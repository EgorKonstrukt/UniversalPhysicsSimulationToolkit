from UPST.config import config
import math
import pymunk
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos, get_gizmos
from UPST.modules.hierarchy import HierarchyNode
from UPST.modules.profiler import profile
from UPST.scripting.script_manager import ScriptManager
from UPST.modules.undo_redo_manager import get_undo_redo
from UPST.modules.statistics import stats

class PhysicsManager:
    def __init__(self, game_app, undo_redo_manager, script_manager):
        try:
            Debug.log_info("PhysicsManager initialization started.", "Physics")
            self.app = game_app
            self.script_manager = script_manager
            self.undo_redo_manager = undo_redo_manager
            self.space = pymunk.Space(threaded=config.multithreading.pymunk_threaded)
            # self.space.use_spatial_hash(dim=1, count=10)
            self.space.threads = config.multithreading.pymunk_threads
            self.space.iterations = int(config.physics.iterations)
            self.space.sleep_time_threshold = float(config.physics.sleep_time_threshold)
            self.space.damping = 1.0
            self.space.collision_slop = 0.01
            self.space.collision_bias = pow(1.0 - 0.1, 60.0)
            self.space.on_collision()
            self.static_body = self.space.static_body
            self.simulation_frequency = int(config.physics.simulation_frequency)
            self.simulation_speed_multiplier = 1.0
            self.running_physics = True
            self.running_scripts = True
            self.static_lines = []
            self._fixed_dt = 1.0 / max(1, self.simulation_frequency)
            self._accumulator = 0.0
            self._ccd_bodies = set()
            self._angular_damping = 0.0
            self.air_friction = True
            self.air_friction_linear = 0.0100
            self.air_friction_quadratic = 0.00100
            self.air_friction_multiplier = 1.0
            self.air_density = 1.225
            self.theme = config.world.themes.get(config.world.current_theme, config.world.themes["Default"])
            self.simulation_time = 0.0
            self.selected_bodies = set()

            if not self.theme:
                Debug.log_warning(f"Theme '{self.app.world_theme}' not found, defaulting to Classic.", "Physics")
                self.theme = config.world.themes["Default"]
            Debug.log_info(f"Physics space initialized with {self.space.threads} threads and {self.space.iterations} iterations.", "Physics")

        except Exception as e:
            Debug.log_error(f"Failed to initialize PhysicsManager: {e}", "Physics")

    def select_bodies_in_rect(self, rect_world):
        self.selected_bodies.clear()
        for shape in self.space.shapes:
            if not hasattr(shape, 'body') or not shape.body: continue
            pos = shape.body.position
            if rect_world.collidepoint(pos.x, pos.y):
                self.selected_bodies.add(shape.body)

    def clear_selection(self):
        self.selected_bodies.clear()
    def weld_bodies(self, b_master, b_slave):
        if b_master is b_slave:
            return
        if b_slave.body_type != pymunk.Body.DYNAMIC:
            return
        mm, ms = b_master.mass, b_slave.mass
        if mm + ms <= 0:
            return

        self.undo_redo_manager.take_snapshot()

        wm, ws = b_master.position, b_slave.position
        new_com_world = (wm * mm + ws * ms) / (mm + ms)
        self.space.remove(b_master, *b_master.shapes)
        self.space.remove(b_slave, *b_slave.shapes)
        self.script_manager.remove_scripts_by_owner(b_slave)

        new_body = pymunk.Body(0, 0, body_type=pymunk.Body.DYNAMIC)
        new_body.position = new_com_world
        shapes = []

        for src_body in (b_master, b_slave):
            src_color = getattr(src_body, 'color', (200, 200, 200, 255))
            if len(src_color) == 3:
                src_color = (*src_color, 255)
            for s in list(src_body.shapes):
                if isinstance(s, pymunk.Circle):
                    wp = src_body.local_to_world(s.offset)
                    off = wp - new_com_world
                    ns = pymunk.Circle(new_body, s.radius, off)
                elif isinstance(s, pymunk.Segment):
                    wa = src_body.local_to_world(s.a)
                    wb = src_body.local_to_world(s.b)
                    na = wa - new_com_world
                    nb = wb - new_com_world
                    ns = pymunk.Segment(new_body, na, nb, s.radius)
                elif isinstance(s, pymunk.Poly):
                    verts = [src_body.local_to_world(v) - new_com_world for v in s.get_vertices()]
                    ns = pymunk.Poly(new_body, verts)
                else:
                    continue
                ns.friction = s.friction
                ns.elasticity = s.elasticity
                ns.collision_type = s.collision_type
                ns.filter = s.filter
                ns.color = getattr(s, 'color', src_color)
                if hasattr(s, 'mass') and s.mass > 0:
                    ns.mass = s.mass
                elif src_body.mass > 0:
                    total_area = sum(shape.area for shape in src_body.shapes if hasattr(shape, 'area'))
                    if total_area > 0:
                        ns.mass = src_body.mass * (ns.area / total_area)
                    else:
                        ns.mass = src_body.mass / len(src_body.shapes)
                else:
                    ns.mass = 1.0
                shapes.append(ns)

        self.space.add(new_body, *shapes)
    @profile("update_scripts")
    def update_scripts(self, dt: float):
        try:
            if self.running_scripts and self.running_physics:
                self.script_manager.update_all(dt)
        except Exception as e:
            Debug.log_error(f"Error in update_scripts: {e}", "Physics")

    def reset_with_theme(self):
        self.delete_all()
        self.theme = config.world.themes.get(config.world.current_theme, config.world.themes["Default"])
        self.create_base_world()

    def create_base_world(self):
        try:
            Debug.log_info("Creating base world geometry and debug texts.", "Physics")
            self.set_gravity_mode(mode="world", g=(0,-981))
            vertices = [(-10000, config.app.screen_height - 200), (-10000, config.app.screen_height),
                        (10000, config.app.screen_height), (10000, config.app.screen_height - 200)]
            floor = pymunk.Poly(self.static_body, vertices)
            floor.friction = 1.0
            floor.elasticity = 0.5
            floor.color = self.theme.platform_color
            self.space.add(floor)
            self.static_lines.append(floor)
            Gizmos.draw_text(position=(950, 350),
                             text="Welcome to the " + config.app.version + "!",
                             font_name="Consolas",
                             font_size=40,
                             font_world_space=True,
                             color=(255, 0, 255),
                             duration=60.01,
                             world_space=True)
            Gizmos.draw_text(position=(1000, 600),
                             text=config.app.guide_text,
                             font_name="Consolas",
                             font_size=30,
                             font_world_space=True,
                             color=(255, 255, 255),
                             duration=60.01,
                             world_space=True)
            Debug.log_info("Welcome and guide texts drawn using Gizmos.", "Physics")
            Debug.log_info("Base world created after undo_redo manager setup.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in create_base_world: {e}", "Physics")

    @profile("physics_step")
    def step(self, dt: float):
        try:
            if not self.running_physics:
                return
            for body in self.space.bodies:
                if hasattr(body, 'hierarchy_node'):
                    node = body.hierarchy_node
                    if node.parent:
                        node._update_world_transform()
            # for body in self.space.bodies:
            #     if hasattr(body, 'color') and body.color is not None:
            #         for shape in body.shapes:
            #             shape.color = body.color
            effective_dt = self._fixed_dt * self.simulation_speed_multiplier
            self._accumulator += max(0.0, float(dt) * self.simulation_speed_multiplier)
            prev_pos = {b: b.position for b in self.space.bodies if b.body_type == pymunk.Body.DYNAMIC}
            while self._accumulator >= effective_dt:
                if self.air_friction:
                    self._apply_air_friction()

                self.space.step(effective_dt)
                if self._angular_damping > 0.0:
                    k = max(0.0, min(1.0, 1.0 - self._angular_damping))
                    for b in self.space.bodies:
                        if b.body_type == pymunk.Body.DYNAMIC:
                            b.angular_velocity *= k
                for b in list(self._ccd_bodies):
                    if b not in prev_pos or b.body_type != pymunk.Body.DYNAMIC:
                        continue
                    start = prev_pos[b]
                    end = pymunk.Vec2d(b.position)
                    delta = end - start
                    if delta.length < 1e-5:
                        continue
                    hit = self.space.segment_query_first(start, end, self.space.collision_slop, pymunk.ShapeFilter())
                    if hit and hit.shape and hit.alpha < 1.0:
                        n = hit.normal
                        b.position = hit.point - n * (self.space.collision_slop * 1.01)
                        e = 0.5
                        try:
                            e = 0.5 * (hit.shape.elasticity + sum(s.elasticity for s in b.shapes) / max(1, len(b.shapes)))
                        except Exception:
                            pass
                        v = pymunk.Vec2d(b.velocity)
                        vn = v.dot(n) * n
                        vt = v - vn
                        b.velocity = vt - vn * max(0.0, min(1.0, e))
                prev_pos = {b: b.position for b in self.space.bodies if b.body_type == pymunk.Body.DYNAMIC}
                self._accumulator -= effective_dt
        except Exception as e:
            Debug.log_error(f"Error in physics step: {e}", "Physics")
        self.simulation_time += effective_dt

    def _is_in_space(self, obj):
        if isinstance(obj, pymunk.Body):
            return obj in self.space.bodies
        elif isinstance(obj, pymunk.Shape):
            return obj in self.space.shapes
        elif isinstance(obj, pymunk.Constraint):
            return obj in self.space.constraints
        return False

    def remove_body(self, body):
        try:
            if not isinstance(body, pymunk.Body):
                Debug.log_warning("remove_body called with non-Body object", "Physics")
                return
            if not self._is_in_space(body):
                Debug.log_info(f"Body {body.__hash__()} already removed or not in space; skipping.", "Physics")
                return
            Debug.log_info(f"Removing body {body.__hash__()} and its shapes.", "Physics")
            self.script_manager.remove_scripts_by_owner(body)
            shapes_to_remove = [s for s in list(body.shapes) if self._is_in_space(s)]
            if shapes_to_remove:
                self.space.remove(*shapes_to_remove)
                for s in shapes_to_remove:
                    Debug.log_info(f"Shape {s.__hash__()} removed from body {body.__hash__()}.", "Physics")
            self.space.remove(body)
            Debug.log_info(f"Body {body.__hash__()} successfully removed from physics space.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in remove_body: {e}", "Physics")

    def remove_shape_body(self, shape):
        try:
            if not isinstance(shape, pymunk.Shape):
                Debug.log_warning("remove_shape_body called with non-Shape object", "Physics")
                return
            if not self._is_in_space(shape):
                Debug.log_info(f"Shape {shape.__hash__()} already removed or not in space; skipping.", "Physics")
                return
            Debug.log_info(f"Removing shape {shape.__hash__()} and possibly its body.", "Physics")
            body = shape.body
            self.space.remove(shape)
            Debug.log_info(f"Shape {shape.__hash__()} removed from space.", "Physics")
            self.undo_redo_manager.take_snapshot()
            if body and body != self.static_body and self._is_in_space(body) and not any(self._is_in_space(s) for s in body.shapes):
                self.script_manager.remove_scripts_by_owner(body)
                self.space.remove(body)
                Debug.log_info(f"Body {body.__hash__()} removed (no shapes left).", "Physics")
            else:
                Debug.log_info(f"Body {body.__hash__()} retained (still has active shapes).", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in remove_shape_body: {e}", "Physics")
    def delete_all(self):
        try:
            Debug.log_info("Starting full physics space cleanup.", "Physics")
            dynamic_bodies = [b for b in self.space.bodies if b is not self.static_body and self._is_in_space(b)]
            for body in dynamic_bodies:
                shapes_to_remove = [s for s in list(body.shapes) if self._is_in_space(s)]
                if shapes_to_remove:
                    self.space.remove(*shapes_to_remove)
                    for s in shapes_to_remove:
                        Debug.log_info(f"Removed shape {s.__hash__()} from body {body.__hash__()}.", "Physics")
                self.script_manager.remove_scripts_by_owner(body)
                self.space.remove(body)
                Debug.log_info(f"Removed dynamic body {body.__hash__()}.", "Physics")

            orphaned_shapes = [s for s in self.space.shapes if self._is_in_space(s)]
            if orphaned_shapes:
                self.space.remove(*orphaned_shapes)
                for s in orphaned_shapes:
                    Debug.log_info(f"Removed orphaned/static shape {s.__hash__()} (type: {type(s).__name__}).", "Physics")
            self.static_lines.clear()

            constraints = [c for c in self.space.constraints if self._is_in_space(c)]
            if constraints:
                self.space.remove(*constraints)
                for c in constraints:
                    Debug.log_info(f"Removed constraint {c.__hash__()}.", "Physics")

            gizmos_mgr = get_gizmos()
            if gizmos_mgr:
                gizmos_mgr.clear()
                gizmos_mgr.clear_persistent()
                gizmos_mgr.clear_unique()

            Debug.log_info("Physics space fully cleared.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error during delete_all: {e}", "Physics")

    def _shape_proj_area_and_cd(self, s, b, vel_unit):
        try:
            if hasattr(s, "cross_sectional_area") and getattr(s, "cross_sectional_area") is not None:
                A = float(s.cross_sectional_area)
            else:
                if isinstance(s, pymunk.Circle):
                    r = float(s.radius)
                    span = 2.0 * r
                    A = span
                elif isinstance(s, pymunk.Segment):
                    a = pymunk.Vec2d(*s.a)
                    c = pymunk.Vec2d(*s.b)
                    world_a = b.position + a.rotated(b.angle)
                    world_c = b.position + c.rotated(b.angle)
                    span = (world_c - world_a).dot(vel_unit.perpendicular()) if vel_unit.length > 0 else (
                                world_c - world_a).length
                    span = abs(span)
                    thickness = getattr(s, "radius", 0.5)
                    A = max(0.001, span * (thickness * 2.0))
                elif isinstance(s, pymunk.Poly):
                    verts = [pymunk.Vec2d(*v) for v in s.get_vertices()]
                    if not verts:
                        A = 0.0
                    else:
                        pts = [b.position + v.rotated(b.angle) for v in verts]
                        projs = [p.dot(vel_unit.perpendicular()) for p in pts]
                        A = max(projs) - min(projs)
                        A = abs(A)
                        if A < 1e-4:
                            sm = 0.0
                            for i in range(len(verts)):
                                x1, y1 = verts[i].x, verts[i].y
                                x2, y2 = verts[(i + 1) % len(verts)].x, verts[(i + 1) % len(verts)].y
                                sm += x1 * y2 - x2 * y1
                            poly_area = abs(sm) * 0.5
                            A = max(0.001, poly_area ** 0.5)
                else:
                    A = 0.001
            if hasattr(s, "drag_coeff") and getattr(s, "drag_coeff") is not None:
                Cd = float(s.drag_coeff)
            else:
                if isinstance(s, pymunk.Circle):
                    Cd = 0.47
                elif isinstance(s, pymunk.Segment):
                    Cd = 1.2
                elif isinstance(s, pymunk.Poly):
                    Cd = 1.0
                else:
                    Cd = 1.0
            return max(0.0, float(A)), max(0.0, float(Cd))
        except Exception:
            return 0.0, 1.0

    def update(self, rotation):
        try:
            self.step(1.0 / max(1, self.simulation_frequency))
        except Exception as e:
            Debug.log_error(f"Error in update: {e}", "Physics")

    def pause_physics(self):
        """Ставит физику и скрипты на паузу"""
        self.running_physics = False
        self.script_manager.pause_all_scripts()
        Debug.log_info("Physics and scripts paused", "Physics")

    def resume_physics(self):
        """Снимает с паузы физику и скрипты"""
        self.running_physics = True
        self.script_manager.resume_all_scripts()
        Debug.log_info("Physics and scripts resumed", "Physics")

    def toggle_pause(self):
        try:
            if self.running_physics:
                self.pause_physics()
            else:
                self.resume_physics()
            # self.undo_redo_manager.take_snapshot()
            stats.increment('paused_times', delta=1)
            stats.save()
            Debug.log_info(f"Physics simulation {'paused' if not self.running_physics else 'unpaused'}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in toggle_pause: {e}", "Physics")

    def add_body_shape(self, body, shape):
        try:
            self.space.add(body, shape)
            if not hasattr(body, 'hierarchy_node'):
                body.hierarchy_node = HierarchyNode(name=f"Body_{id(body)}", body=body)
            stats.increment('objects_created', delta=1)
            stats.save()
            Debug.log_info(f"Added body and shape to physics space. Body ID: {body.__hash__()}, Shape ID: {shape.__hash__()}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in add_body_shape: {e}", "Physics")

    def add_static_line(self, segment):
        try:
            self.static_lines.append(segment)
            self.space.add(segment)
            stats.increment('static_created', delta=1)
            stats.save()
            Debug.log_info(f"Added static line to physics space. Segment ID: {segment.__hash__()}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in add_static_line: {e}", "Physics")

    def add_constraint(self, constraint):
        try:
            self.space.add(constraint)
            stats.increment('constraints_created', delta=1)
            stats.save()
            Debug.log_info(f"Added constraint to physics space. Constraint ID: {constraint.__hash__()}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in add_constraint: {e}", "Physics")

    def get_body_at_position(self, position):
        try:
            Debug.log_info(f"Querying body at position: {position}.", "Physics")
            query = self.space.point_query_nearest(position, 0, pymunk.ShapeFilter())
            if query and query.shape and query.shape.body:
                Debug.log_info(f"Found body {query.shape.body.__hash__()} at position.", "Physics")
                return query.shape.body
            Debug.log_info("No body found at position.", "Physics")
            return None
        except Exception as e:
            Debug.log_error(f"Error in get_body_at_position: {e}", "Physics")
            return None

    def get_last_body(self):
        try:
            Debug.log_info("Getting last body added to physics space.", "Physics")
            bodies = list(self.space.bodies)
            if bodies:
                Debug.log_info(f"Last body found: {bodies[-1].__hash__()}.", "Physics")
                return bodies[-1]
            Debug.log_info("No bodies in physics space.", "Physics")
            return None
        except Exception as e:
            Debug.log_error(f"Error in get_last_body: {e}", "Physics")
            return None



    def set_simulation_paused(self, paused: bool):
        try:
            self.running_physics = bool(paused)
            g = get_gizmos()
            if g: g.simulation_paused = bool(paused)
            print(g.simulation_paused)
            Debug.log_info(f"Physics simulation {'paused' if self.running_physics else 'resumed'} via set_simulation_paused.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_simulation_paused: {e}", "Physics")

    def set_simulation_frequency(self, hz: int):
        try:
            hz = int(max(1, hz))
            self.simulation_frequency = hz
            self._fixed_dt = 1.0 / hz
            Debug.log_info(f"Simulation frequency set to {hz} Hz", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_simulation_frequency: {e}", "Physics")

    def set_simulation_speed_multiplier(self, multiplier: float):
        try:
            self.simulation_speed_multiplier = max(0.1, float(multiplier))
            Debug.log_info(f"Simulation speed multiplier set to {self.simulation_speed_multiplier}x", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_simulation_speed_multiplier: {e}", "Physics")

    def set_iterations(self, iters: int):
        try:
            iters = int(max(1, iters))
            self.space.iterations = iters
            Debug.log_info(f"Solver iterations set to {iters}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_iterations: {e}", "Physics")

    def set_air_friction_linear(self, linear: float):
        try:
            self.air_friction_linear = max(0.0, float(linear))
            Debug.log_info(f"Air friction params set: linear={self.air_friction_linear}",
                           "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_air_friction_linear: {e}", "Physics")

    def set_air_friction_quadratic(self, quadratic: float):
        try:
            self.air_friction_quadratic = max(0.0, float(quadratic))
            Debug.log_info(f"Air friction params set: quadratic={self.air_friction_quadratic}",
                           "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_air_friction_quadratic: {e}", "Physics")

    def set_air_friction_multiplier(self, multiplier: float):
        try:
            self.air_friction_multiplier = max(0.0, float(multiplier))
            Debug.log_info(f"Air friction params set: multiplier={self.air_friction_multiplier}",
                           "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_air_friction_multiplier: {e}", "Physics")

    def set_air_density(self, density: float):
        try:
            self.air_density = max(0.0, float(density))
            Debug.log_info(f"Air friction params set: density={self.air_density}",
                           "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_air_density: {e}", "Physics")


    def set_damping(self, linear: float = 1.0, angular: float = 0.0):
        try:
            self.space.damping = max(0.0, min(1.0, float(linear)))
            self._angular_damping = max(0.0, min(1.0, float(angular)))
            Debug.log_info(f"Damping set: linear={self.space.damping}, angular={self._angular_damping}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_damping: {e}", "Physics")

    def set_air_friction_params(self, linear: float, quadratic: float, multiplier: float):
        try:
            self.air_friction_linear = max(0.0, float(linear))
            self.air_friction_quadratic = max(0.0, float(quadratic))
            self.air_friction_multiplier = max(0.0, float(multiplier))
            Debug.log_info(f"Air friction params set: linear={self.air_friction_linear}, quadratic={self.air_friction_quadratic}, multiplier={self.air_friction_multiplier}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_air_friction_params: {e}", "Physics")

    def set_sleep_time_threshold(self, seconds: float):
        try:
            self.space.sleep_time_threshold = max(0.0, float(seconds))
            Debug.log_info(f"Sleep time threshold set to {self.space.sleep_time_threshold}s", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_sleep_time_threshold: {e}", "Physics")

    def set_collision_slop(self, slop: float):
        try:
            self.space.collision_slop = max(0.0, float(slop))
            Debug.log_info(f"Collision slop set to {self.space.collision_slop}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_collision_slop: {e}", "Physics")

    def set_collision_bias(self, bias: float):
        try:
            self.space.collision_bias = max(0.0, min(1.0, float(bias)))
            Debug.log_info(f"Collision bias set to {self.space.collision_bias}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_collision_bias: {e}", "Physics")

    def set_gravity_mode(self, mode: str = "world", camera_rotation: float = None, g: tuple = None):
        try:
            base_g = pymunk.Vec2d(*((0, -981) if g is None else g))
            if mode == "camera" and camera_rotation is not None:
                rot = pymunk.Transform.rotation(camera_rotation)
                gv = rot @ base_g
                self.space.gravity = gv
            else:
                self.space.gravity = base_g
        except Exception as e:
            Debug.log_error(f"Error in set_gravity_mode: {e}", "Physics")

    def raycast(self, a: tuple, b: tuple, radius: float = 0.0, mask: pymunk.ShapeFilter = None):
        try:
            if mask is None:
                mask = pymunk.ShapeFilter()
            return self.space.segment_query_first(pymunk.Vec2d(*a), pymunk.Vec2d(*b), radius, mask)
        except Exception as e:
            Debug.log_error(f"Error in raycast: {e}", "Physics")
            return None

    def overlap_aabb(self, bb: tuple, mask: pymunk.ShapeFilter = None):
        try:
            bb_obj = pymunk.BB(*bb)
            out = []
            def _collector(shape): out.append(shape)
            self.space.bb_query(bb_obj, _collector, mask or pymunk.ShapeFilter())
            return out
        except Exception as e:
            Debug.log_error(f"Error in overlap_aabb: {e}", "Physics")
            return []

    def shapecast(self, shape: pymunk.Shape, transform: pymunk.Transform = None):
        try:
            temp_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            if isinstance(shape, pymunk.Circle):
                temp = pymunk.Circle(temp_body, shape.radius, shape.offset)
            elif isinstance(shape, pymunk.Segment):
                temp = pymunk.Segment(temp_body, shape.a, shape.b, shape.radius)
            elif isinstance(shape, pymunk.Poly):
                temp = pymunk.Poly(temp_body, shape.get_vertices(), transform=None)
            else:
                return []
            if transform is not None:
                temp_body.position = (transform.tx, transform.ty)
                angle = math.atan2(transform.b, transform.a)
                temp_body.angle = angle
            return self.space.shape_query(temp)
        except Exception as e:
            Debug.log_error(f"Error in shapecast: {e}", "Physics")
            return []

    def enable_ccd(self, shape_or_body, enabled: bool = True):
        try:
            body = shape_or_body if isinstance(shape_or_body, pymunk.Body) else getattr(shape_or_body, 'body', None)
            if not isinstance(body, pymunk.Body):
                return
            if enabled:
                self._ccd_bodies.add(body)
            else:
                self._ccd_bodies.discard(body)
        except Exception as e:
            Debug.log_error(f"Error in enable_ccd: {e}", "Physics")

    def _apply_air_friction(self):
        for b in self.space.bodies:
            if b.body_type != pymunk.Body.DYNAMIC: continue
            total_torque_from_drag = 0.0
            for s in b.shapes:
                try:
                    if getattr(s, "sensor", False): continue
                    if hasattr(s, "offset"):
                        off = pymunk.Vec2d(*s.offset)
                    elif isinstance(s, pymunk.Segment):
                        a = pymunk.Vec2d(*s.a); c = pymunk.Vec2d(*s.b); off = (a + c) * 0.5
                    elif isinstance(s, pymunk.Poly):
                        try:
                            verts = [pymunk.Vec2d(*v) for v in s.get_vertices()]
                            off = sum(verts, pymunk.Vec2d(0, 0)) / len(verts) if verts else pymunk.Vec2d(0, 0)
                        except Exception:
                            off = pymunk.Vec2d(0, 0)
                    else:
                        off = pymunk.Vec2d(0, 0)
                    wp = b.position + off.rotated(b.angle)
                    r = wp - b.position
                    ang_vel_vec = pymunk.Vec2d(-b.angular_velocity * r.y, b.angular_velocity * r.x)
                    vp = b.velocity + ang_vel_vec
                    vm = vp.length
                    if vm <= 1e-9: continue
                    vel_unit = vp / vm
                    A, Cd = self._shape_proj_area_and_cd(s, b, vel_unit)
                    lin = -self.air_friction_multiplier * self.air_friction_linear * A * vp
                    quad = -self.air_friction_multiplier * (0.5 * self.air_density * Cd * A * vm) * vel_unit * self.air_friction_quadratic
                    f = lin + quad
                    b.apply_force_at_world_point(f, wp)
                except Exception as e:
                    Debug.log_error(f"Error applying air friction on body {b.__hash__()}: {e}", "Physics")
            # --- Apply rotational aerodynamic drag ---
            if abs(b.angular_velocity) > 1e-9:
                area_rot = 0.0
                for s in b.shapes:
                    if isinstance(s, pymunk.Circle):
                        area_rot += s.radius
                    elif isinstance(s, pymunk.Segment):
                        a = pymunk.Vec2d(*s.a); c = pymunk.Vec2d(*s.b)
                        length = (c - a).length
                        area_rot += length * (getattr(s, "radius", 0.5) * 2.0)
                    elif isinstance(s, pymunk.Poly):
                        verts = [pymunk.Vec2d(*v) for v in s.get_vertices()]
                        if verts:
                            sm = 0.0
                            for i in range(len(verts)):
                                x1, y1 = verts[i].x, verts[i].y
                                x2, y2 = verts[(i + 1) % len(verts)].x, verts[(i + 1) % len(verts)].y
                                sm += x1 * y2 - x2 * y1
                            area_rot += abs(sm) * 0.5
                area_rot = max(0.001, area_rot)
                av = b.angular_velocity
                av_abs = abs(av)
                torque_lin = -self.air_friction_multiplier * self.air_friction_linear * area_rot * av
                torque_quad = -self.air_friction_multiplier * self.air_friction_quadratic * 0.5 * self.air_density * area_rot * av_abs * av
                total_torque = torque_lin + torque_quad
                b.torque += total_torque