from UPST.config import config
import math
import pymunk
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos, get_gizmos
from UPST.scripting.script_manager import ScriptManager

class PhysicsManager:
    def __init__(self, game_app, undo_redo_manager):
        try:
            Debug.log_info("PhysicsManager initialization started.", "Physics")
            self.app = game_app
            self.undo_redo_manager = undo_redo_manager
            self.space = pymunk.Space(threaded=config.multithreading.pymunk_threaded)
            self.space.threads = config.multithreading.pymunk_threads
            self.space.iterations = int(config.physics.iterations)
            self.space.sleep_time_threshold = float(config.physics.sleep_time_threshold)
            self.space.damping = 1.0
            self.space.collision_slop = 0.01
            self.space.collision_bias = pow(1.0 - 0.1, 60.0)
            self.static_body = self.space.static_body
            self.simulation_frequency = int(config.physics.simulation_frequency)
            self.running_physics = True
            self.running_scripts = True
            self.static_lines = []
            self._fixed_dt = 1.0 / max(1, self.simulation_frequency)
            self._accumulator = 0.0
            self._ccd_bodies = set()
            self._angular_damping = 0.0
            self.theme = config.world.themes.get(self.app.world_theme)
            self.script_manager = ScriptManager(app=self.app)
            if not self.theme:
                Debug.log_warning(f"Theme '{self.app.world_theme}' not found, defaulting to Classic.", "Physics")
                self.theme = config.world.themes["Classic"]
            Debug.log_info(f"Physics space initialized with {self.space.threads} threads and {self.space.iterations} iterations.", "Physics")
            if config.app.create_base_world:
                self.create_base_world()
                Debug.log_info("Base world created.", "Physics")
        except Exception as e:
            Debug.log_error(f"Failed to initialize PhysicsManager: {e}", "Physics")

    def update_scripts(self, dt: float):
        try:
            if self.running_scripts and self.running_physics:
                self.script_manager.update_all(dt)
        except Exception as e:
            Debug.log_error(f"Error in update_scripts: {e}", "Physics")

    def create_base_world(self):
        try:
            Debug.log_info("Creating base world geometry and debug texts.", "Physics")
            vertices = [(-10000, config.app.screen_height - 200), (-10000, config.app.screen_height),
                        (10000, config.app.screen_height), (10000, config.app.screen_height - 200)]
            floor = pymunk.Poly(self.static_body, vertices)
            floor.friction = 1.0
            floor.elasticity = 0.5
            floor.color = self.theme.platform_color
            self.space.add(floor)
            self.static_lines.append(floor)
            Gizmos.draw_text(position=(950, 350), text="Welcome to the " + config.app.version + "!", font_name="Consolas", font_size=40, font_world_space=True, color=(255, 0, 255), duration=0.01, world_space=True)
            Gizmos.draw_text(position=(1000, 600), text=config.app.guide_text, font_name="Consolas", font_size=30, font_world_space=True, color=(255, 255, 255), duration=0.01, world_space=True)
            Debug.log_info("Welcome and guide texts drawn using Gizmos.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in create_base_world: {e}", "Physics")

    def step(self, dt: float):
        try:
            if not self.running_physics:
                return
            self._accumulator += max(0.0, float(dt))
            prev_pos = {b: b.position for b in self.space.bodies if b.body_type == pymunk.Body.DYNAMIC}
            while self._accumulator >= self._fixed_dt:
                self.space.step(self._fixed_dt)
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
                self._accumulator -= self._fixed_dt
        except Exception as e:
            Debug.log_error(f"Error in physics step: {e}", "Physics")

    def update(self, rotation):
        try:
            self.set_gravity_mode("camera", rotation)
            self.step(1.0 / max(1, self.simulation_frequency))
        except Exception as e:
            Debug.log_error(f"Error in update: {e}", "Physics")

    def toggle_pause(self):
        try:
            self.running_physics = not self.running_physics
            Debug.log_info(f"Physics simulation {'paused' if not self.running_physics else 'unpaused'}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in toggle_pause: {e}", "Physics")

    def add_body_shape(self, body, shape):
        try:
            self.space.add(body, shape)
            self.undo_redo_manager.take_snapshot()
            Debug.log_info(f"Added body and shape to physics space. Body ID: {body.__hash__()}, Shape ID: {shape.__hash__()}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in add_body_shape: {e}", "Physics")

    def add_static_line(self, segment):
        try:
            self.static_lines.append(segment)
            self.space.add(segment)
            self.undo_redo_manager.take_snapshot()
            Debug.log_info(f"Added static line to physics space. Segment ID: {segment.__hash__()}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in add_static_line: {e}", "Physics")

    def add_constraint(self, constraint):
        try:
            self.space.add(constraint)
            self.undo_redo_manager.take_snapshot()
            Debug.log_info(f"Added constraint to physics space. Constraint ID: {constraint.__hash__()}.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in add_constraint: {e}", "Physics")

    def remove_shape_body(self, shape):
        try:
            Debug.log_info(f"Attempting to remove shape and its body if empty. Shape ID: {shape.__hash__()}.", "Physics")
            body = shape.body
            self.space.remove(shape)
            self.undo_redo_manager.take_snapshot()
            Debug.log_info(f"Shape {shape.__hash__()} removed from space.", "Physics")
            if body and not body.shapes:
                self.script_manager.remove_scripts_by_owner(body)
                self.space.remove(body)
                Debug.log_info(f"Body {body.__hash__()} removed as it has no more shapes.", "Physics")
            else:
                Debug.log_info(f"Body {body.__hash__()} not removed as it still has shapes.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in remove_shape_body: {e}", "Physics")

    def delete_all(self):
        try:
            Debug.log_info("Deleting all bodies, shapes, and constraints from physics space.", "Physics")
            for body in list(self.space.bodies):
                if body is self.static_body:
                    continue
                if body:
                    self.script_manager.remove_scripts_by_owner(body)
                self.space.remove(body, *body.shapes)
                Debug.log_info(f"Body {body.__hash__()} and its shapes removed.", "Physics")
            for line in list(self.static_lines):
                self.space.remove(line)
                Debug.log_info(f"Static line {line.__hash__()} removed.", "Physics")
            self.static_lines.clear()
            for constraint in list(self.space.constraints):
                self.space.remove(constraint)
                Debug.log_info(f"Constraint {constraint.__hash__()} removed.", "Physics")
            gizmos_mgr = get_gizmos()
            if gizmos_mgr:
                gizmos_mgr.clear()
                gizmos_mgr.clear_persistent()
                gizmos_mgr.clear_unique()
        except Exception as e:
            Debug.log_error(f"Error in delete_all: {e}", "Physics")

    def get_body_at_position(self, position):
        try:
            Debug.log_info(f"Querying body at position: {position}.", "Physics")
            self.undo_redo_manager.take_snapshot()
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

    def remove_body(self, body):
        try:
            Debug.log_info(f"Attempting to remove body {body.__hash__()} and its shapes.", "Physics")
            if body in self.space.bodies:
                self.script_manager.remove_scripts_by_owner(body)
                for shape in list(body.shapes):
                    if shape in self.space.shapes:
                        self.space.remove(shape)
                        Debug.log_info(f"Shape {shape.__hash__()} removed from body {body.__hash__()}.", "Physics")
                self.space.remove(body)
                Debug.log_info(f"Body {body.__hash__()} removed from physics space.", "Physics")
            else:
                Debug.log_warning(f"Attempted to remove body {body.__hash__()} but it was not found in space.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in remove_body: {e}", "Physics")

    def set_simulation_paused(self, paused: bool):
        try:
            self.running_physics = bool(paused)
            g = get_gizmos()
            if g: g.simulation_paused = bool(paused)
            print(g.simulation_paused)
            Debug.log_info(f"Physics simulation {'paused' if self.running_physics else 'resumed'} via set_simulation_paused.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_simulation_paused: {e}", "Physics")

    def toggle_pause(self):
        try:
            self.running_physics = not self.running_physics
            g = get_gizmos()
            if g: g.simulation_paused = True
            Debug.log_info(f"Physics simulation {'paused' if self.running_physics else 'resumed'} via toggle_pause.", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in toggle_pause: {e}", "Physics")
    def set_simulation_frequency(self, hz: int):
        try:
            hz = int(max(1, hz))
            self.simulation_frequency = hz
            self._fixed_dt = 1.0 / hz
            Debug.log_info(f"Simulation frequency set to {hz} Hz", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_simulation_frequency: {e}", "Physics")

    def set_iterations(self, iters: int):
        try:
            iters = int(max(1, iters))
            self.space.iterations = iters
            Debug.log_info(f"Solver iterations set to {iters}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_iterations: {e}", "Physics")

    def set_damping(self, linear: float = 1.0, angular: float = 0.0):
        try:
            self.space.damping = max(0.0, min(1.0, float(linear)))
            self._angular_damping = max(0.0, min(1.0, float(angular)))
            Debug.log_info(f"Damping set: linear={self.space.damping}, angular={self._angular_damping}", "Physics")
        except Exception as e:
            Debug.log_error(f"Error in set_damping: {e}", "Physics")

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
            base_g = pymunk.Vec2d(*((0, 900) if g is None else g))
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