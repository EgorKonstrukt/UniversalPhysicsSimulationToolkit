from UPST.config import config
import pymunk

from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos


class PhysicsManager:
    """
    Manages the Pymunk physics space and its properties.
    """

    def __init__(self, game_app, undo_redo_manager):
        Debug.log_info("PhysicsManager initialization started.", "Physics")
        self.app = game_app
        self.undo_redo_manager = undo_redo_manager
        self.space = pymunk.Space(threaded=config.physics.pymunk_threaded)
        self.space.threads = config.physics.pymunk_threads
        self.space.iterations = config.physics.iterations
        self.space.sleep_time_threshold = config.physics.sleep_time_threshold
        self.static_body = self.space.static_body
        self.simulation_frequency = config.physics.simulation_frequency
        self.running_physics = True
        self.static_lines = []

        self.theme = config.world.themes.get(self.app.world_theme)
        if not self.theme:
            Debug.log_warning(f"Theme '{self.app.world_theme}' not found, defaulting to Classic.", "Physics")
            self.theme = config.world.themes["Classic"]
        Debug.log_info(f"Physics space initialized with {self.space.threads} threads and {self.space.iterations} iterations.", "Physics")

        if config.app.create_base_world:
            self.create_base_world()
            Debug.log_info("Base world created.", "Physics")

    def create_base_world(self):
        Debug.log_info("Creating base world geometry and debug texts.", "Physics")
        vertices = [(-10000, config.app.screen_height - 200), (-10000, config.app.screen_height),
                    (10000, config.app.screen_height), (10000, config.app.screen_height - 200)]
        floor = pymunk.Poly(self.static_body, vertices)
        floor.friction = 1.0
        floor.elasticity = 0.5
        floor.color = self.theme.platform_color
        self.space.add(floor)
        Debug.log_info("Floor segment added to physics space.", "Physics")

        Gizmos.draw_text(
            position=(950, 350),
            text="Welcome to the " + config.app.version + "!",
            font_name="Consolas",
            font_size=40,
            font_world_space=True,
            color=(255, 0, 255),
            duration=0.01,
            world_space=True
        )
        Gizmos.draw_text(
            position=(1000, 600),
            text=config.app.guide_text,
            font_name="Consolas",
            font_size=30,
            font_world_space=True,
            color=(255, 255, 255),
            duration=0.01,
            world_space=True
        )
        Gizmos.draw_text(
            position=(1000, 600),
            text=config.app.guide_text,
            font_name="Consolas",
            font_size=30,
            font_world_space=True,
            color=(255, 255, 255),
            duration=0.01,
            world_space=True
        )
        Debug.log_info("Welcome and guide texts drawn using Gizmos.", "Physics")

    def update(self, rotation):
        if self.running_physics:
            dt = 2.0 / self.simulation_frequency
            self.space.step(dt)
            self.space.gravity = rotation * 1000, 1000
    def toggle_pause(self):
        self.running_physics = not self.running_physics
        Debug.log_info(f"Physics simulation {'paused' if not self.running_physics else 'unpaused'}.", "Physics")

    def add_body_shape(self, body, shape):
        self.undo_redo_manager.take_snapshot()
        self.space.add(body, shape)
        Debug.log_info(f"Added body and shape to physics space. Body ID: {body.__hash__()}, Shape ID: {shape.__hash__()}.", "Physics")

    def add_static_line(self, segment):
        self.undo_redo_manager.take_snapshot()
        self.static_lines.append(segment)
        self.space.add(segment)
        Debug.log_info(f"Added static line to physics space. Segment ID: {segment.__hash__()}.", "Physics")

    def add_constraint(self, constraint):
        self.undo_redo_manager.take_snapshot()
        self.space.add(constraint)
        Debug.log_info(f"Added constraint to physics space. Constraint ID: {constraint.__hash__()}.", "Physics")

    def remove_shape_body(self, shape):
        Debug.log_info(f"Attempting to remove shape and its body if empty. Shape ID: {shape.__hash__()}.", "Physics")
        self.undo_redo_manager.take_snapshot()
        body = shape.body
        self.space.remove(shape)
        Debug.log_info(f"Shape {shape.__hash__()} removed from space.", "Physics")
        if body and not body.shapes:
            self.space.remove(body)
            Debug.log_info(f"Body {body.__hash__()} removed as it has no more shapes.", "Physics")
        else:
            Debug.log_info(f"Body {body.__hash__()} not removed as it still has shapes.", "Physics")

    def delete_all(self):
        Debug.log_info("Deleting all bodies, shapes, and constraints from physics space.", "Physics")
        for body in list(self.space.bodies):
            if body is self.static_body:
                continue
            self.space.remove(body, *body.shapes)
            Debug.log_info(f"Body {body.__hash__()} and its shapes removed.", "Physics")

        for line in self.static_lines:
            self.space.remove(line)
            Debug.log_info(f"Static line {line.__hash__()} removed.", "Physics")
        self.static_lines.clear()

        for constraint in list(self.space.constraints):
            self.space.remove(constraint)
            Debug.log_info(f"Constraint {constraint.__hash__()} removed.", "Physics")

    def get_body_at_position(self, position):
        Debug.log_info(f"Querying body at position: {position}.", "Physics")
        query = self.space.point_query_nearest(position, 0, pymunk.ShapeFilter())
        if query and query.shape.body:
            Debug.log_info(f"Found body {query.shape.body.__hash__()} at position.", "Physics")
            return query.shape.body
        Debug.log_info("No body found at position.", "Physics")
        return None

    def get_last_body(self):
        Debug.log_info("Getting last body added to physics space.", "Physics")
        bodies = list(self.space.bodies)
        if bodies:
            Debug.log_info(f"Last body found: {bodies[-1].__hash__()}.", "Physics")
            return bodies[-1]
        Debug.log_info("No bodies in physics space.", "Physics")
        return None

    def remove_body(self, body):
        Debug.log_info(f"Attempting to remove body {body.__hash__()} and its shapes.", "Physics")
        if body in self.space.bodies:
            for shape in body.shapes:
                self.space.remove(shape)
                Debug.log_info(f"Shape {shape.__hash__()} removed from body {body.__hash__()}.", "Physics")
            self.space.remove(body)
            Debug.log_info(f"Body {body.__hash__()} removed from physics space.", "Physics")
        else:
            Debug.log_warning(f"Attempted to remove body {body.__hash__()} but it was not found in space.", "Physics")
