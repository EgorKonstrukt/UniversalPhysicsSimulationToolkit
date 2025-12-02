import pymunk
import pygame
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
import pygame_gui

class InputHandler:
    def __init__(self, game_app, gizmos_manager, debug_manager, undo_redo_manager, ui_manager, tool_system):
        self.app = game_app
        self.gizmos_manager = gizmos_manager
        self.debug_manager = debug_manager
        self.undo_redo_manager = undo_redo_manager
        self.ui_manager = ui_manager
        self.tool_system = tool_system
        self.key_f_pressed = False
        self.key_f_hold_start_time = 0
        self.key_z_pressed = False
        self.key_z_hold_start_time = 0
        self.camera_dragging = False
        self.camera_drag_start_pos = (0, 0)
        self.object_dragging = None
        self.first_joint_body = None
        self.first_joint_pos = None

    def is_mouse_on_ui(self):
        return self.app.ui_manager.manager.get_focus_set()

    def process_events(self, profiler, events):
        world_mouse_pos = self.app.camera.screen_to_world(pygame.mouse.get_pos())
        for event in events:
            self.app.ui_manager.process_event(event, self.app)
            self.gizmos_manager.handle_event(event)
            self.debug_manager.handle_input(event)
            self.undo_redo_manager.handle_input(event)

            self.handle_keyboard_events(event, world_mouse_pos)
            self.handle_mouse_events(event, world_mouse_pos)
            profiler.process_event(event)
            if event.type == pygame.QUIT:
                self.app.running = False
            self.handle_held_keys(world_mouse_pos)
            if self.tool_system.current_tool:
                self.tool_system.handle_input(world_mouse_pos)

    def handle_keyboard_events(self, event, world_mouse_pos):
        if self.is_mouse_on_ui():
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.app.toggle_grid()
            mods = pygame.key.get_mods()

            if event.key == pygame.K_r and (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_SHIFT):
                if hasattr(self.app, 'script_manager'):
                    self.app.script_manager.reload_all_scripts()
            elif event.key == pygame.K_ESCAPE:
                if self.first_joint_body:
                    self.first_joint_body = None
                elif self.tool_system.current_tool:
                    self.tool_system.current_tool.deactivate()
                    self.tool_system.current_tool = None
            elif event.key == pygame.K_f:
                self.key_f_pressed = True
                self.key_f_hold_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_n:
                synthesizer.play_frequency(800, duration=0.2, waveform='sine')
                field_name = self.app.ui_manager.selected_force_field_button_text
                self.app.force_field_manager.toggle_field(field_name)
            elif event.key == pygame.K_p:
                pygame.image.save(self.app.screen, "../../screenshot.png")
                self.app.ui_manager.console_window.add_output_line_to_log("Screenshot saved!")
            elif event.key == pygame.K_DELETE:
                info = self.app.physics_manager.space.point_query_nearest(
                    world_mouse_pos, 0, pymunk.ShapeFilter()
                )
                if info and info.shape:
                    self.app.physics_manager.remove_shape_body(info.shape)

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_f:
                if (pygame.time.get_ticks() - self.key_f_hold_start_time) < config.input.hold_time_ms:
                    if self.tool_system.current_tool and hasattr(self.tool_system.current_tool, 'spawn_at'):
                        self.tool_system.current_tool.spawn_at(world_mouse_pos)
                self.key_f_pressed = False
        keys = pygame.key.get_pressed()
        self.app.camera.shift_speed = 5 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1

    def handle_mouse_events(self, event, world_mouse_pos):
        if not self.is_mouse_on_ui():
            self.app.camera.handle_mouse_event(event)
        if self.tool_system.current_tool:
            self.tool_system.current_tool.handle_event(event, world_mouse_pos)
        if self.is_mouse_on_ui():
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                pass
                # info = self.app.physics_manager.space.point_query_nearest(world_mouse_pos, 0, pymunk.ShapeFilter())
                # if info and info.shape and info.shape.body != self.app.physics_manager.static_body:
                #     self.object_dragging = info.shape.body
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
                self.camera_dragging = False
                self.object_dragging = None

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
            if self.tool_system.current_tool and hasattr(self.tool_system.current_tool, 'spawn_at'):
                self.tool_system.current_tool.spawn_at(world_mouse_pos)