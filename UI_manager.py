import pygame
import pygame_gui
import os
import sys

import pymunk
from pygame_gui import ui_manager

from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.gui.contex_menu import ContextMenu
from UPST.gui.bars.bottom_bar import BottomBar
from UPST.gui.bars.top_left_bar import TopLeftBar
from UPST.gui.bars.top_right_bar import TopRightBar
from UPST.gui.force_field_ui import ForceFieldUI
from UPST.gui.console_ui import ConsoleUI
from UPST.modules.profiler import profile
from UPST.utils import get_resource_path


REPO_LIST_LOADED_EVENT = pygame.event.custom_type()

class UIManager:
    def __init__(self, screen_width, screen_height, physics_manager, camera, input_handler, screen, font, tool_system=None, network_manager=None, app=None):
        self.app = app
        theme_path = get_resource_path('theme.json')
        self.manager = pygame_gui.UIManager((screen_width, screen_height), theme_path)
        self.tool_system = tool_system
        self.screen = screen
        self.font = font
        self.input_handler = input_handler
        self.physics_manager = physics_manager
        self.camera = camera
        self.network_manager = network_manager
        self.network_menu = None
        self.physics_debug_manager = None
        self.active_color_picker = None
        self.color_picker_for_shape = None
        self.script_editor = None
        self.context_menu = ContextMenu(self.manager, self, self.app)
        # self.force_field_ui = ForceFieldUI(self.manager, screen_width, screen_height, self)
        self.console_ui = ConsoleUI(self.manager, screen_width, screen_height)
        self.bottom_bar = BottomBar(screen_width, screen_height, self.manager, physics_manager=self.physics_manager)
        self.top_left_bar = TopLeftBar(screen_width, screen_height, self.manager, app=self.app, physics_manager=self.physics_manager)
        self.top_right_bar = TopRightBar(screen_width, screen_height, self.manager, app=self.app, physics_manager=self.physics_manager)
        self.tool_buttons = []
        self.shape_colors = {'rectangle': pygame.Color(128,128,128), 'circle': pygame.Color(128,128,128), 'triangle': pygame.Color(128,128,128), 'polyhedron': pygame.Color(128,128,128)}
        self.rectangle_color_random = True
        self.circle_color_random = True
        self.triangle_color_random = True
        self.poly_color_random = True
        self._init_fonts()
        self.script_windows = []
        self.plotter_windows = []

    def _init_fonts(self):
        font_path = get_resource_path("fonts/Consolas.ttf")
        self.manager.add_font_paths(font_name="consolas", regular_path=font_path)
        self.manager.preload_fonts([{'name': 'consolas', 'size': 14, 'style': 'regular'},
                                    {'name': 'consolas', 'size': 18, 'style': 'regular'},
                                    {'name': 'consolas', 'size': 20, 'style': 'bold'}])

    def register_script_window(self, w):
        if w not in self.script_windows: self.script_windows.append(w)
    def unregister_script_window(self, w):
        try: self.script_windows.remove(w)
        except ValueError: pass

    def register_plotter_window(self, w):
        if w not in self.plotter_windows: self.plotter_windows.append(w)
    def unregister_plotter_window(self, w):
        try: self.plotter_windows.remove(w)
        except ValueError: pass

    def show_inline_script_editor(self, script=None, owner=None):
        if hasattr(self, '_script_editor') and self.script_editor:
            self.script_editor.window.kill()
        from UPST.gui.windows.script_editor_window import ScriptEditorWindow
        self.script_editor = ScriptEditorWindow(rect=pygame.Rect(150,100,550,750), manager=self.manager, physics_manager=self.physics_manager, physics_debug_manager=self.physics_debug_manager, owner=owner, script=script, app=self.app)

    def init_network_menu(self):
        if self.network_manager is not None and self.network_menu is None:
            from UPST.network.network_menu import NetworkMenu
            self.network_menu = NetworkMenu(ui_manager=self.manager, network_manager=self.network_manager, title="Network")

    def set_physics_debug_manager(self, physics_debug_manager):
        self.physics_debug_manager = physics_debug_manager

    def toggle_color_mode(self, shape_type):
        current = getattr(self, f"{shape_type}_color_random", True)
        setattr(self, f"{shape_type}_color_random", not current)
        img_path = get_resource_path("sprites/gui/checkbox_true.png" if not current else "sprites/gui/checkbox_false.png")
        img_element = getattr(self, f"{shape_type}_color_random_image")
        img_element.set_image(pygame.image.load(img_path))

    def open_color_picker(self, shape_type):
        if self.active_color_picker:
            self.active_color_picker.kill()
        initial = self.shape_colors.get(shape_type, pygame.Color(128,128,128))
        self.active_color_picker = pygame_gui.windows.UIColourPickerDialog(rect=pygame.Rect(0,0,420,420), manager=self.manager, initial_colour=initial, window_title=f"Pick Color for {shape_type.title()}")
        self.color_picker_for_shape = shape_type

    def process_event(self, event, game_app):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if not self.manager.get_hovering_any_element():
                if not self.manager.hovering_any_ui_element:
                    world_pos = self.camera.screen_to_world(event.pos)
                    shapes = self.physics_manager.space.point_query(world_pos, 0, pymunk.ShapeFilter())
                    clicked_obj = shapes[0].shape.body if shapes else None
                    self.open_context_menu(event.pos, clicked_obj)
        if event.type == REPO_LIST_LOADED_EVENT:
            if hasattr(self.app, 'repo_window') and self.app.repo_window.alive():
                self.app.repo_window.handle_repo_list_loaded(event.dict["items"])

        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                self._handle_button_press(event, game_app)
            elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                self._handle_slider_move(event, game_app)
            elif event.user_type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
                self._handle_color_pick(event)
            elif event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
                self.context_menu.process_event(event)
        if event.type == pygame_gui.UI_CONSOLE_COMMAND_ENTERED and event.ui_element == self.console_ui.console_window:
            game_app.console_handler.process_command(event.command)
        elif event.type == pygame.WINDOWRESIZED:
            config.app.screen_width = event.x
            config.app.screen_height = event.y
            self._on_resize()
        self.manager.process_events(event)
        if self.network_menu:
            self.network_menu.process_event(event)
        self.context_menu.process_event(event)
        if self.script_editor:
            self.script_editor.process_event(event)
        self.bottom_bar.process_event(event)
        self.top_left_bar.process_event(event)
        self.top_right_bar.process_event(event)

        for w in list(self.script_windows):
            try:
                w.handle_event(event)
            except Exception:
                Debug.log_exception("Error while dispatching UI event to script window.", "GUI")
        for w in list(self.plotter_windows):
            try: w.handle_event(event)
            except Exception: Debug.log_exception("Error dispatching plotter event.", "GUI")
    def _handle_button_press(self, event, game_app):
        # if event.ui_element in self.force_field_ui.force_field_buttons:
        #     self.force_field_ui.handle_button_press(event.ui_element, game_app)
        if hasattr(event.ui_element, 'tool_name'):
            self.tool_system.activate_tool(event.ui_element.tool_name)

    def _handle_color_pick(self, event):
        if self.active_color_picker and event.ui_element == self.active_color_picker and self.tool_system.current_tool:
            if hasattr(self.tool_system.current_tool, 'set_color'):
                self.tool_system.current_tool.set_color(pygame.Color(event.colour))
            self.active_color_picker = None
            self.color_picker_for_shape = None

    def _handle_slider_move(self, event, game_app):
        pass
        # self.force_field_ui.handle_slider_move(event, game_app)

    def _on_resize(self):
        screen_w, screen_h = config.app.screen_width, config.app.screen_height
        self.manager.set_window_resolution((screen_w, screen_h))
        # self.force_field_ui.resize(screen_w, screen_h)
        self.console_ui.resize(screen_w, screen_h)
        self.bottom_bar.resize(screen_w, screen_h)

    @profile("ui_manager_update")
    def update(self, time_delta, clock):
        self.manager.update(time_delta)
        self.context_menu.update(time_delta, clock)
        for w in list(self.plotter_windows):
            try: w.update(time_delta, self.physics_manager.simulation_time)
            except Exception: Debug.log_exception("Error updating plotter window.", "GUI")

    def draw(self, screen):
        self.context_menu.draw_menu_line(screen, self.camera)
        self.manager.draw_ui(screen)
        if self.tool_system:
            self.tool_system.draw_preview(screen, self.camera)

    def open_context_menu(self, position, clicked_object):
        self.context_menu.show_menu(position, clicked_object)

    def open_properties_window(self, obj):
        print(f"Opening properties for object: {obj}")
        self.properties_window = pygame_gui.elements.UIWindow(pygame.Rect(100,100,300,400), manager=self.manager, window_display_title=f"Properties: {obj.body.mass:.2f}kg")
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,280,20), text=f"Mass: {obj.body.mass:.2f}kg", container=self.properties_window, manager=self.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,30,280,20), text=f"Velocity: {obj.body.velocity.length:.2f}m/s", container=self.properties_window, manager=self.manager)

    def hide_all_object_windows(self):
        if self.tool_system:
            for tool in self.tool_system.tools.values():
                if tool.settings_window:
                    tool.settings_window.hide()

    def resize(self, new_width, new_height):
        config.app.screen_width = new_width
        config.app.screen_height = new_height