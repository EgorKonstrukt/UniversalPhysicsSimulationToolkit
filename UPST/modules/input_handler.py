import pymunk
import pygame
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer

class InputHandler:
    def __init__(self, game_app, gizmos_manager, debug_manager, undo_redo_manager):
        self.app = game_app
        self.gizmos_manager = gizmos_manager
        self.debug_manager = debug_manager
        self.undo_redo_manager = undo_redo_manager
        self.key_f_pressed = False
        self.key_f_hold_start_time = 0
        self.key_z_pressed = False
        self.key_z_hold_start_time = 0
        self.camera_dragging = False
        self.camera_drag_start_pos = (0, 0)
        self.object_dragging = None
        self.creating_static_line = False
        self.static_line_start = (0, 0)
        self.current_tool = "Circle"
        self.spawn_tools = ["Circle", "Rectangle", "Triangle", "Polyhedron", "Spam", "Human"]
        self.joint_tools = ["Spring", "Pivot", "Rigid", "Motor", "Gear", "Slide", "RotaryLimit"]
        self.first_joint_body = None
        self.first_joint_pos = None
        self.dragging = False
        self.drag_start_pos = None
        self.preview_shape = None

    def is_mouse_on_ui(self):
        return self.app.ui_manager.manager.get_focus_set()

    def process_events(self, profiler, events):
        world_mouse_pos = self.app.camera.screen_to_world(pygame.mouse.get_pos())
        for event in events:
            self.app.ui_manager.process_event(event, self.app)
            self.gizmos_manager.handle_event(event)
            self.debug_manager.handle_input(event)
            self.undo_redo_manager.handle_input(event)
            if event.type == pygame.QUIT:
                self.app.running = False
            self.handle_keyboard_events(event)
            self.handle_mouse_events(event, world_mouse_pos)
            profiler.process_event(event)
        self.handle_held_keys(world_mouse_pos)

    def handle_keyboard_events(self, event):
        if self.is_mouse_on_ui():
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g and pygame.key.get_pressed()[pygame.K_LCTRL]:
                self.app.toggle_grid()
            if event.key == pygame.K_ESCAPE:
                if self.first_joint_body:
                    self.first_joint_body = None
                else:
                    self.app.ui_manager.settings_window.toggle_visibility()
            elif event.key == pygame.K_f:
                self.key_f_pressed = True
                self.key_f_hold_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_z:
                ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL
            elif event.key == pygame.K_SPACE:
                synthesizer.play_frequency(830, duration=0.04, waveform='sine')
                self.app.physics_manager.toggle_pause()
                self.app.ui_manager.toggle_pause_icon(not self.app.physics_manager.running_physics)
            elif event.key == pygame.K_b:
                synthesizer.play_frequency(150, duration=0.1, waveform='sine')
                self.creating_static_line = True
                self.static_line_start = self.app.camera.screen_to_world(pygame.mouse.get_pos())
            elif event.key == pygame.K_n:
                synthesizer.play_frequency(800, duration=0.2, waveform='sine')
                field_name = self.app.ui_manager.selected_force_field_button_text
                self.app.force_field_manager.toggle_field(field_name)
            elif event.key == pygame.K_p:
                pygame.image.save(self.app.screen, "../../screenshot.png")
                self.app.ui_manager.console_window.add_output_line_to_log("Screenshot saved!")
                self.app.sound_manager.play('screenshot')
            elif event.key == pygame.K_DELETE:
                info = self.app.physics_manager.space.point_query_nearest(
                    self.app.camera.screen_to_world(pygame.mouse.get_pos()), 0, pymunk.ShapeFilter()
                )
                if info and info.shape:
                    self.app.physics_manager.remove_shape_body(info.shape)
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_f:
                if (pygame.time.get_ticks() - self.key_f_hold_start_time) < config.input.hold_time_ms:
                    if self.current_tool in self.spawn_tools and not self.is_mouse_on_ui():
                        self.app.spawner.spawn(self.current_tool, self.app.camera.screen_to_world(pygame.mouse.get_pos()))
                self.key_f_pressed = False
            elif event.key == pygame.K_z:
                self.key_z_pressed = False
            elif event.key == pygame.K_b:
                synthesizer.play_frequency(120, duration=0.1, waveform='sine')
                self.creating_static_line = False
                line_end = self.app.camera.screen_to_world(pygame.mouse.get_pos())
                segment = pymunk.Segment(self.app.physics_manager.static_body, self.static_line_start, line_end, 5)
                segment.friction = 1.0
                segment.elasticity = 0.5
                self.app.physics_manager.add_static_line(segment)
        keys = pygame.key.get_pressed()
        self.app.camera.shift_speed = 5 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1

    def handle_mouse_events(self, event, world_mouse_pos):
        if self.is_mouse_on_ui():
            return
        self.app.camera.handle_mouse_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.current_tool in self.spawn_tools:
                    self.drag_start_pos = world_mouse_pos
                    self.dragging = True
                    self.preview_shape = None
                elif self.current_tool in self.joint_tools:
                    self.handle_joint_creation(world_mouse_pos)
                info = self.app.physics_manager.space.point_query_nearest(world_mouse_pos, 0, pymunk.ShapeFilter())
                if info and info.shape and info.shape.body != self.app.physics_manager.static_body:
                    self.object_dragging = info.shape.body
            elif event.button == 3:
                info = self.app.physics_manager.space.point_query_nearest(world_mouse_pos, 0, pymunk.ShapeFilter())
                clicked_object = info.shape.body if info and info.shape and info.shape.body != self.app.physics_manager.static_body else None
                self.app.ui_manager.open_context_menu(event.pos, clicked_object)
            elif event.button == 4:
                self.app.camera.target_scaling *= 1.1
            elif event.button == 5:
                self.app.camera.target_scaling *= 0.9
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                self.camera_dragging = False
                self.object_dragging = None
                if self.current_tool in self.spawn_tools:
                    self.app.spawner.spawn_dragged(self.current_tool, self.drag_start_pos, world_mouse_pos)
                self.drag_start_pos = None
                self.preview_shape = None
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging and self.current_tool in self.spawn_tools:
                self.preview_shape = self.calculate_preview_shape(world_mouse_pos)

    def handle_joint_creation(self, world_mouse_pos):
        info = self.app.physics_manager.space.point_query_nearest(world_mouse_pos, 0, pymunk.ShapeFilter())
        clicked_body = info.shape.body if info and info.shape and info.shape.body != self.app.physics_manager.static_body else None
        if not clicked_body:
            self.first_joint_body = None
            self.app.sound_manager.play('error')
            return
        if self.first_joint_body is None:
            self.first_joint_body = clicked_body
            self.first_joint_pos = world_mouse_pos
            self.app.sound_manager.play('click_3')
        else:
            if self.first_joint_body != clicked_body:
                body1 = self.first_joint_body
                body2 = clicked_body
                anchor1 = body1.world_to_local(self.first_joint_pos)
                anchor2 = body2.world_to_local(world_mouse_pos)
                constraint = None
                if self.current_tool == "Spring":
                    rest_length = body1.position.get_distance(body2.position)
                    constraint = pymunk.DampedSpring(body1, body2, anchor1, anchor2, rest_length, 200, 10)
                elif self.current_tool == "Pivot":
                    pivot_point = self.first_joint_pos
                    constraint = pymunk.PivotJoint(body1, body2, pivot_point)
                elif self.current_tool == "Rigid":
                    constraint = pymunk.PinJoint(body1, body2, anchor1, anchor2)
                elif self.current_tool == "Motor":
                    constraint = pymunk.SimpleMotor(body1, body2, 2.0)
                elif self.current_tool == "Gear":
                    constraint = pymunk.GearJoint(body1, body2, 0.0, 1.0)
                elif self.current_tool == "Slide":
                    min_d = 10.0
                    max_d = max(30.0, (pymunk.Vec2d(*self.first_joint_pos) - pymunk.Vec2d(*world_mouse_pos)).length)
                    constraint = pymunk.SlideJoint(body1, body2, anchor1, anchor2, min_d, max_d)
                elif self.current_tool == "RotaryLimit":
                    constraint = pymunk.RotaryLimitJoint(body1, body2, -0.5, 0.5)
                if constraint:
                    self.app.physics_manager.add_constraint(constraint)
                    self.app.sound_manager.play('click_4')
                self.first_joint_body = None
            else:
                self.first_joint_body = None
                self.app.sound_manager.play('error')

    def calculate_preview_shape(self, end_pos):
        start = self.drag_start_pos
        if start is None or end_pos is None:
            return None
        try:
            if self.current_tool == "Circle":
                start_vec = pymunk.Vec2d(start[0], start[1])
                end_vec = pymunk.Vec2d(end_pos[0], end_pos[1])
                radius = (start_vec - end_vec).length
                return {"type": "circle", "position": start, "radius": radius, "color": (200, 200, 255, 100)}
            elif self.current_tool == "Rectangle":
                dx = end_pos[0] - start[0]
                dy = end_pos[1] - start[1]
                center = (start[0] + dx / 2, start[1] + dy / 2)
                return {"type": "rect", "position": center, "width": abs(dx), "height": abs(dy), "color": (200, 200, 255, 100)}
            elif self.current_tool == "Triangle":
                dx = end_pos[0] - start[0]
                dy = end_pos[1] - start[1]
                center = (start[0] + dx / 2, start[1] + dy / 2)
                return {"type": "triangle", "position": center, "width": abs(dx), "height": abs(dy), "color": (200, 200, 255, 100)}
            elif self.current_tool == "Polyhedron":
                dx = end_pos[0] - start[0]
                dy = end_pos[1] - start[1]
                center = (start[0] + dx / 2, start[1] + dy / 2)
                return {"type": "polyhedron", "position": center, "width": abs(dx), "height": abs(dy), "radius": 50, "sides": 5, "color": (200, 200, 255, 100)}
        except Exception as e:
            print("Error calculating preview shape:", e)
            return None

    def handle_held_keys(self, world_mouse_pos):
        if self.is_mouse_on_ui():
            return
        if self.object_dragging:
            if self.app.physics_manager.running_physics:
                self.object_dragging.velocity = ((world_mouse_pos[0] - self.object_dragging.position[0]) * 10,
                                                 (world_mouse_pos[1] - self.object_dragging.position[1]) * 10)
            else:
                self.object_dragging.position = world_mouse_pos
                self.object_dragging.velocity = (0, 0)
        if self.key_f_pressed and (pygame.time.get_ticks() - self.key_f_hold_start_time) > config.input.hold_time_ms:
            if self.current_tool in self.spawn_tools:
                self.app.spawner.spawn(self.current_tool, world_mouse_pos)
