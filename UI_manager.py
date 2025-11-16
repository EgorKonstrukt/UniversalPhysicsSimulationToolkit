import pygame
import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UIHorizontalSlider, UILabel, UIButton, UITextEntryLine, UIImage, \
    UIPanel
from pygame_gui.windows import UIConsoleWindow, UIColourPickerDialog
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
from UPST.modules.profiler import profile
import math
from UPST.gui.contex_menu import ContextMenu
from UPST.network.network_menu import NetworkMenu
import pymunk
import tkinter as tk
from tkinter import filedialog
from UPST.gui.script_editor_window import ScriptEditorWindow
class UIManager:
    def __init__(self, screen_width, screen_height, physics_manager, camera,
                 input_handler, screen, font, tool_manager=None, network_manager=None, app=None):
        self.app = app
        self.refresh_scripts_btn = None
        self.edit_script_btn = None
        self.stop_script_btn = None
        self.new_script_btn = None
        self.script_target_dropdown = None
        self.manager = pygame_gui.UIManager((screen_width, screen_height),
                                            'theme.json',
                                            )
        self.tool_manager = tool_manager
        self.screen = screen
        self.font = font
        self.input_handler = input_handler
        self.physics_manager = physics_manager
        self.camera = camera
        self.network_menu = None
        self.selected_force_field_button_text = "attraction1"
        self.rectangle_color_random = True
        self.circle_color_random = True
        self.triangle_color_random = True
        self.poly_color_random = True
        self.shape_colors = {
            'rectangle': pygame.Color(128, 128, 128),
            'circle': pygame.Color(128, 128, 128),
            'triangle': pygame.Color(128, 128, 128),
            'polyhedron': pygame.Color(128, 128, 128)
        }
        self.tool_buttons = []
        self.tool_icons = {}
        self.physics_debug_manager = None
        self.plotter = None
        self.create_all_elements()
        self.hide_all_object_windows()
        self.manager.add_font_paths(font_name="consolas", regular_path="fonts/Consolas.ttf")
        self.manager.preload_fonts([
            {'name': 'consolas', 'size': 14, 'style': 'regular'},
            {'name': 'consolas', 'size': 18, 'style': 'regular'},
            {'name': 'consolas', 'size': 20, 'style': 'bold'}
        ])
        self.active_color_picker = None
        self.color_picker_for_shape = None
        self.script_editor = None
    def show_inline_script_editor(self, script=None, owner=None):
        if hasattr(self, '_script_editor') and self.script_editor:
            self.script_editor.window.kill()
        self.script_editor = ScriptEditorWindow(
            rect=pygame.Rect(150, 100, 550, 750),
            manager=self.manager,
            physics_manager=self.physics_manager,
            physics_debug_manager=self.physics_debug_manager,
            owner=owner,
            script=script,
            app=self.app
        )
        # return self.script_editor
    def _create_color_controls(self, parent_window, obj_prefix):
        panel = UIPanel(relative_rect=pygame.Rect(5, 100, 200, 60), manager=self.manager, container=parent_window)
        pick_btn = UIButton(relative_rect=pygame.Rect(5, 5, 100, 25), text="Pick Color", manager=self.manager,
                            container=panel)
        rand_cb = UIButton(relative_rect=pygame.Rect(5, 32, 20, 20), text="", manager=self.manager, container=panel,
                           tool_tip_text="Random color")
        rand_label = UILabel(relative_rect=pygame.Rect(28, 32, 100, 20), text="Random", container=panel,
                             manager=self.manager)
        checkbox_img = UIImage(relative_rect=pygame.Rect(5, 32, 20, 20),
                               image_surface=pygame.image.load("sprites/gui/checkbox_true.png"), container=panel,
                               manager=self.manager)
        setattr(self, f"{obj_prefix}_color_button", pick_btn)
        setattr(self, f"{obj_prefix}_color_random_checkbox", rand_cb)
        setattr(self, f"{obj_prefix}_color_random_image", checkbox_img)
    def init_network_menu(self):
        if self.network_manager is not None and self.network_menu is None:
            self.network_menu = NetworkMenu(ui_manager=self.manager,
                                            network_manager=self.network_manager,
                                            title="Network")
    def set_physics_debug_manager(self, physics_debug_manager):
        self.physics_debug_manager = physics_debug_manager
    def set_plotter(self, plotter):
        self.plotter = plotter
    def create_all_elements(self):
        self.create_force_field_buttons()
        self.create_console()
        self.create_settings_window()
        self.create_force_field_settings()
        self.create_object_settings_windows()
        self.create_utility_buttons()
        self.create_pause_icon()
        self.context_menu = ContextMenu(self.manager, self)
        self.create_physics_debug_settings_window()
        self.create_plotter_window()
        self.create_script_window()
    def update_script_list(self):
        if not self.script_window or not hasattr(self.physics_manager, 'script_manager'):
            return
        scripts = self.physics_manager.script_manager.get_all_scripts()
        items = []
        self._script_item_map = {}
        for i, s in enumerate(scripts):
            owner_desc = "World" if s.owner is None else f"Body@{id(s.owner)}"
            status = "R" if s.running else "S"
            threaded_mark = "T" if s.threaded else "M"
            display = f"[{threaded_mark}{status}] {s.name} — {owner_desc}"
            items.append(display)
            self._script_item_map[display] = s
        self.script_list.set_item_list(items)
    def stop_selected_script(self):
        selected = self.script_list.get_single_selection()
        if selected and selected in self._script_item_map:
            script = self._script_item_map[selected]
            self.physics_manager.script_manager.remove_script(script)
            self.update_script_list()
    def create_script_window(self):
        self.script_window = pygame_gui.elements.UIWindow(
            pygame.Rect(50, 50, 400, 500),
            manager=self.manager,
            window_display_title="Script Manager",
            visible=False
        )
        self.script_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(10, 50, 370, 350),
            item_list=[],
            manager=self.manager,
            container=self.script_window
        )
        self.refresh_scripts_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 410, 120, 30),
            text="Refresh",
            manager=self.manager,
            container=self.script_window
        )
        self.stop_script_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(140, 410, 120, 30),
            text="Stop Selected",
            manager=self.manager,
            container=self.script_window
        )
        self.open_script_editor_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(270, 410, 110, 30),
            text="New Script",
            manager=self.manager,
            container=self.script_window
        )
    def create_force_field_buttons(self):
        self.force_field_buttons = []
        self.force_field_icons = []
        paths = ["attraction.png", "repulsion.png", "ring.png", "spiral.png", "laydigital.png"]
        texts = ["attraction", "repulsion", "ring", "spiral", "freeze"]
        for i, (path, text) in enumerate(zip(paths, texts)):
            pos = (config.app.screen_width - 135, config.app.screen_height - 500 + 51 * i)
            button = UIButton(relative_rect=pygame.Rect(pos, (110, 50)), text=text, manager=self.manager)
            icon = UIImage(relative_rect=pygame.Rect(pos[0] - 50, pos[1] + 1, 47, 47),
                           image_surface=pygame.image.load(f"sprites/gui/force_field/{path}"), manager=self.manager)
            self.force_field_buttons.append(button)
            self.force_field_icons.append(icon)
    def create_console(self):
        self.console_window = UIConsoleWindow(
            pygame.Rect(config.app.screen_width - 800, config.app.screen_height - 300, 500, 310),
            manager=self.manager)
    def create_settings_window(self):
        self.settings_window = pygame_gui.elements.UIWindow(
            pygame.Rect(200, config.app.screen_height - 300, 400, 200), manager=self.manager,
            window_display_title="Settings")
        self.debug_draw_collision_points_checkbox = UIButton(
            relative_rect=pygame.Rect(5, 10, 20, 20),
            text="",
            container=self.settings_window,
            tool_tip_text="Draw collision points",
            manager=self.manager
        )
        UILabel(relative_rect=pygame.Rect(5, 10, 200, 20),
                text="Draw Collision Points", container=self.settings_window, manager=self.manager)
        self.debug_draw_constraints_checkbox = UIButton(
            relative_rect=pygame.Rect(5, 30, 20, 20),
            text="",
            container=self.settings_window,
            tool_tip_text="Draw constraints",
            manager=self.manager
        )
        UILabel(relative_rect=pygame.Rect(5, 30, 200, 20),
                text="Draw Constraints", container=self.settings_window, manager=self.manager)
        self.debug_draw_body_outlines_checkbox = UIButton(
            relative_rect=pygame.Rect(5, 60, 20, 20),
            text="",
            container=self.settings_window,
            tool_tip_text="Draw body outlines",
            manager=self.manager
        )
        UILabel(relative_rect=pygame.Rect(5, 60, 200, 20),
                text="Draw Body Outlines", container=self.settings_window, manager=self.manager)
        self.debug_draw_center_of_mass_checkbox = UIButton(
            relative_rect=pygame.Rect(5, 90, 20, 20),
            text="",
            container=self.settings_window,
            tool_tip_text="Draw center of mass",
            manager=self.manager
        )
        UILabel(relative_rect=pygame.Rect(5, 90, 200, 20),
                text="Draw Center of Mass", container=self.settings_window, manager=self.manager)
    def create_physics_debug_settings_window(self):
        self.physics_debug_window = pygame_gui.elements.UIWindow(
            pygame.Rect(config.app.screen_width - 450, 10, 400, 600), manager=self.manager,
            window_display_title="Physics Debug Settings")
        self.physics_debug_window.hide()
        y_offset = 10
        self.debug_setting_checkboxes = {}
        # for attr_name in dir(PhysicsDebugSettings):
        #     if not attr_name.startswith('__') and isinstance(getattr(PhysicsDebugSettings, attr_name), bool):
        #         display_name = attr_name.replace('show_', '').replace('_', ' ').title()
        #         checkbox = UIButton(
        #             relative_rect=pygame.Rect(5, y_offset, 20, 20),
        #             text="",
        #             container=self.physics_debug_window,
        #             tool_tip_text=f"Toggle {display_name}",
        #             manager=self.manager
        #         )
        #         label = UILabel(relative_rect=pygame.Rect(30, y_offset, 250, 20),
        #                         text=display_name, container=self.physics_debug_window, manager=self.manager)
        #         self.debug_setting_checkboxes[attr_name] = checkbox
        #         y_offset += 25
        self.toggle_all_debug_button = UIButton(
            relative_rect=pygame.Rect(5, y_offset, 150, 30),
            text="Toggle All Debug",
            container=self.physics_debug_window,
            manager=self.manager
        )
        y_offset += 35
        self.clear_debug_history_button = UIButton(
            relative_rect=pygame.Rect(5, y_offset, 150, 30),
            text="Clear Debug History",
            container=self.physics_debug_window,
            manager=self.manager
        )
    def create_plotter_window(self):
        self.plotter_window = pygame_gui.elements.UIWindow(
            pygame.Rect(50, 50, 600, 400), manager=self.manager,
            window_display_title="Physics Plotter")
        self.plotter_window.hide()
        self.plotter_surface_element = UIImage(
            relative_rect=pygame.Rect(10, 10, 580, 300),
            image_surface=pygame.Surface((580, 300), pygame.SRCALPHA),
            container=self.plotter_window,
            manager=self.manager
        )
        self.plotter_dropdown = UIDropDownMenu(
            options_list=['Select Parameter'],
            starting_option='Select Parameter',
            relative_rect=pygame.Rect(10, 320, 150, 30),
            container=self.plotter_window,
            manager=self.manager
        )
        self.plotter_add_button = UIButton(
            relative_rect=pygame.Rect(170, 320, 80, 30),
            text='Add Plot',
            container=self.plotter_window,
            manager=self.manager
        )
        self.plotter_clear_button = UIButton(
            relative_rect=pygame.Rect(260, 320, 80, 30),
            text='Clear Plots',
            container=self.plotter_window,
            manager=self.manager
        )
    def create_force_field_settings(self):
        self.strength_slider = UIHorizontalSlider(relative_rect=pygame.Rect(400, 10, 200, 20), start_value=500,
                                                  value_range=(0, 5000), manager=self.manager)
        self.radius_slider = UIHorizontalSlider(relative_rect=pygame.Rect(400, 40, 200, 20), start_value=500,
                                                value_range=(0, 10000), manager=self.manager)
        self.text_label_strength = UILabel(relative_rect=pygame.Rect(380, 10, 250, 50),
                                           text=f"Force Field Strength: {500}", manager=self.manager)
        self.text_label_radius = UILabel(relative_rect=pygame.Rect(400, 40, 200, 50), text=f"Force Field Radius: {500}",
                                         manager=self.manager)
        self.hide_force_field_settings()
    def create_utility_buttons(self):
        self.save_button = UIButton(relative_rect=pygame.Rect(config.app.screen_width - 135, 10, 125, 40), text="Save World",
                                    manager=self.manager)
        self.load_button = UIButton(relative_rect=pygame.Rect(config.app.screen_width - 135, 60, 125, 40), text="Load World",
                                    manager=self.manager)
        self.delete_all_button = UIButton(relative_rect=pygame.Rect(200, config.app.screen_height - 50, 125, 40),
                                          text="Delete All", manager=self.manager)
        self.toggle_debug_window_button = UIButton(relative_rect=pygame.Rect(config.app.screen_width - 135, 110, 125, 40), text="Debug Settings", manager=self.manager)
        self.toggle_plotter_window_button = UIButton(relative_rect=pygame.Rect(config.app.screen_width - 135, 160, 125, 40), text="Plotter", manager=self.manager)
        self.toggle_script_window_button = UIButton(
            relative_rect=pygame.Rect(config.app.screen_width - 135, 210, 125, 40),
            text="Scripts",
            manager=self.manager
        )
    def create_pause_icon(self):
        self.pause_icon = UIImage(relative_rect=pygame.Rect(config.app.screen_width - 450, 10, 50, 50),
                                  image_surface=pygame.image.load("sprites/gui/pause.png").convert_alpha(),
                                  manager=self.manager)
        self.pause_icon.hide()
    def _create_object_window(self, title, img_path):
        window = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.manager,
                                              window_display_title=title)
        UIImage(relative_rect=pygame.Rect(215, 5, 50, 50), image_surface=pygame.image.load(img_path), container=window,
                manager=self.manager)
        return window
    def _create_common_object_inputs(self, window):
        inputs = {}
        inputs['friction_label'] = UILabel(relative_rect=pygame.Rect(5, 55, 80, 20), text="Friction:", container=window,
                                           manager=self.manager)
        inputs['friction_entry'] = UITextEntryLine(initial_text="0.7", relative_rect=pygame.Rect(80, 55, 100, 20),
                                                   container=window, manager=self.manager)
        inputs['elasticity_label'] = UILabel(relative_rect=pygame.Rect(5, 75, 85, 20), text="Elasticity:",
                                             container=window, manager=self.manager)
        inputs['elasticity_entry'] = UITextEntryLine(initial_text="0.5", relative_rect=pygame.Rect(90, 75, 105, 20),
                                                     container=window, manager=self.manager)
        return inputs
    def _create_color_panel(self, parent_window, obj_prefix):
        color_panel = UIPanel(relative_rect=pygame.Rect(5, 100, parent_window.get_relative_rect().width - 45, 130),
                              manager=self.manager, container=parent_window)
        red_slider = UIHorizontalSlider(relative_rect=pygame.Rect(90, 10, 150, 20), start_value=128,
                                        value_range=(0, 255), manager=self.manager, container=color_panel)
        green_slider = UIHorizontalSlider(relative_rect=pygame.Rect(90, 30, 150, 20), start_value=128,
                                          value_range=(0, 255), manager=self.manager, container=color_panel)
        blue_slider = UIHorizontalSlider(relative_rect=pygame.Rect(90, 50, 150, 20), start_value=128,
                                         value_range=(0, 255), manager=self.manager, container=color_panel)
        UILabel(relative_rect=pygame.Rect(5, 10, 85, 20), text="Red:", container=color_panel, manager=self.manager)
        UILabel(relative_rect=pygame.Rect(5, 30, 85, 20), text="Green:", container=color_panel, manager=self.manager)
        UILabel(relative_rect=pygame.Rect(5, 50, 85, 20), text="Blue:", container=color_panel, manager=self.manager)
        checkbox_panel = UIPanel(relative_rect=pygame.Rect(5, 75, 130, 45), manager=self.manager, container=color_panel)
        random_button = UIButton(relative_rect=pygame.Rect(-1, -1, 85, 40), text="Random", manager=self.manager,
                                 container=checkbox_panel)
        checkbox_image = UIImage(relative_rect=pygame.Rect(85, 2, 35, 35),
                                 image_surface=pygame.image.load("sprites/gui/checkbox_true.png"),
                                 container=checkbox_panel, manager=self.manager)
        setattr(self, f"{obj_prefix}_color_sliders", (red_slider, green_slider, blue_slider))
        setattr(self, f"{obj_prefix}_color_mode_button", random_button)
        setattr(self, f"{obj_prefix}_color_mode_checkbox_image", checkbox_image)
    def create_object_settings_windows(self):
        self.window_rectangle = self._create_object_window("Rectangle Settings", "sprites/gui/spawn/rectangle.png")
        self.rect_inputs = self._create_common_object_inputs(self.window_rectangle)
        self.rect_inputs['size_x_label'] = UILabel(relative_rect=pygame.Rect(10, 10, 20, 20), text="X:",
                                                   container=self.window_rectangle, manager=self.manager)
        self.rect_inputs['size_x_entry'] = UITextEntryLine(initial_text="30",
                                                           relative_rect=pygame.Rect(30, 10, 100, 20),
                                                           container=self.window_rectangle, manager=self.manager)
        self.rect_inputs['size_y_label'] = UILabel(relative_rect=pygame.Rect(10, 30, 20, 20), text="Y:",
                                                   container=self.window_rectangle, manager=self.manager)
        self.rect_inputs['size_y_entry'] = UITextEntryLine(initial_text="30",
                                                           relative_rect=pygame.Rect(30, 30, 100, 20),
                                                           container=self.window_rectangle, manager=self.manager)
        self._create_color_controls(self.window_rectangle, "rectangle")
        self.window_circle = self._create_object_window("Circle Settings", "sprites/gui/spawn/circle.png")
        self.circle_inputs = self._create_common_object_inputs(self.window_circle)
        self.circle_inputs['radius_label'] = UILabel(relative_rect=pygame.Rect(10, 10, 20, 20), text="R:",
                                                     container=self.window_circle, manager=self.manager)
        self.circle_inputs['radius_entry'] = UITextEntryLine(initial_text="30",
                                                             relative_rect=pygame.Rect(30, 10, 100, 20),
                                                             container=self.window_circle, manager=self.manager)
        self._create_color_controls(self.window_circle, "circle")
        self.window_triangle = self._create_object_window("Triangle Settings", "sprites/gui/spawn/triangle.png")
        self.triangle_inputs = self._create_common_object_inputs(self.window_triangle)
        self.triangle_inputs['size_label'] = UILabel(relative_rect=pygame.Rect(10, 10, 50, 20), text="Size:",
                                                     container=self.window_triangle, manager=self.manager)
        self.triangle_inputs['size_entry'] = UITextEntryLine(initial_text="30",
                                                             relative_rect=pygame.Rect(60, 10, 100, 20),
                                                             container=self.window_triangle, manager=self.manager)
        self._create_color_controls(self.window_triangle, "triangle")
        self.window_polyhedron = self._create_object_window("Polyhedron Settings", "sprites/gui/spawn/polyhedron.png")
        self.poly_inputs = self._create_common_object_inputs(self.window_polyhedron)
        self.poly_inputs['size_label'] = UILabel(relative_rect=pygame.Rect(10, 10, 50, 20), text="Size:",
                                                 container=self.window_polyhedron, manager=self.manager)
        self.poly_inputs['size_entry'] = UITextEntryLine(initial_text="30", relative_rect=pygame.Rect(60, 10, 100, 20),
                                                         container=self.window_polyhedron, manager=self.manager)
        self.poly_inputs['faces_label'] = UILabel(relative_rect=pygame.Rect(10, 30, 50, 20), text="Faces:",
                                                  container=self.window_polyhedron, manager=self.manager)
        self.poly_inputs['faces_entry'] = UITextEntryLine(initial_text="6", relative_rect=pygame.Rect(60, 30, 100, 20),
                                                          container=self.window_polyhedron, manager=self.manager)
        self._create_color_controls(self.window_polyhedron, "polyhedron")
    def toggle_color_mode(self, shape_type):
        attr = f"{shape_type}_color_random"
        current = getattr(self, attr)
        new = not current
        setattr(self, attr, new)
        img_path = "sprites/gui/checkbox_true.png" if new else "sprites/gui/checkbox_false.png"
        img_element = getattr(self, f"{shape_type}_color_random_image")
        img_element.set_image(pygame.image.load(img_path))
    def open_color_picker(self, shape_type):
        if self.active_color_picker:
            self.active_color_picker.kill()
        initial = self.shape_colors.get(shape_type, pygame.Color(128, 128, 128))
        self.active_color_picker = UIColourPickerDialog(
            rect=pygame.Rect(0, 0, 420, 420),
            manager=self.manager,
            initial_colour=initial,
            window_title=f"Pick Color for {shape_type.title()}"
        )
        self.color_picker_for_shape = shape_type
    def process_event(self, event, game_app):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                self.handle_button_press(event, game_app)
            elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                self.handle_slider_move(event, game_app)
            elif event.user_type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
                if self.active_color_picker and event.ui_element == self.active_color_picker:
                    if self.color_picker_for_shape:
                        self.shape_colors[self.color_picker_for_shape] = pygame.Color(event.colour)
                    self.active_color_picker = None
                    self.color_picker_for_shape = None
            elif event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
                self.context_menu.process_event(event)
                if event.ui_element == self.plotter_dropdown:
                    self.selected_plot_parameter = event.text
        if event.type == pygame_gui.UI_CONSOLE_COMMAND_ENTERED and event.ui_element == self.console_window:
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
    def _on_resize(self):
        screen_w, screen_h = config.app.screen_width, config.app.screen_height
        self.manager.set_window_resolution((screen_w, screen_h))
        for i, (button, icon) in enumerate(zip(self.force_field_buttons, self.force_field_icons)):
            pos = (screen_w - 135, screen_h - 500 + 51 * i)
            button.set_position(pos)
            icon.set_position((pos[0] - 50, pos[1] + 1))
        self.console_window.set_position((screen_w - 800, screen_h - 300))
        self.settings_window.set_position((200, screen_h - 300))
        self.physics_debug_window.set_position((screen_w - 450, 10))
        self.plotter_window.set_position((50, 50))
        self.save_button.set_position((screen_w - 135, 10))
        self.load_button.set_position((screen_w - 135, 60))
        self.toggle_debug_window_button.set_position((screen_w - 135, 110))
        self.toggle_plotter_window_button.set_position((screen_w - 135, 160))
        self.delete_all_button.set_position((200, screen_h - 50))
        self.toggle_script_window_button.set_position((screen_w - 135, 210))
        self.pause_icon.set_position((screen_w - 450, 10))
        # self._update_window_scaling(self.script_window, 0.4, 0.5)
        # self._update_window_scaling(self.settings_window, 0.4, 0.2)
        # self._update_window_scaling(self.physics_debug_window, 0.4, 0.6)
        # self._update_window_scaling(self.plotter_window, 0.6, 0.4)
        # self._update_window_scaling(self.window_rectangle, 0.4, 0.3)
        # self._update_window_scaling(self.window_circle, 0.4, 0.3)
        # self._update_window_scaling(self.window_triangle, 0.4, 0.3)
        # self._update_window_scaling(self.window_polyhedron, 0.4, 0.3)
        # self._update_window_scaling(self.console_window, 0.5, 0.31)
    def _update_window_scaling(self, window, width_ratio, height_ratio):
        if not window:
            return
        new_w = int(config.app.screen_width * width_ratio)
        new_h = int(config.app.screen_height * height_ratio)
        current_pos = window.get_position()
        window.set_dimensions((new_w, new_h))
        window.set_position(current_pos)
    def handle_button_press(self, event, game_app):
        if event.ui_element in self.tool_buttons:
            synthesizer.play_frequency(1030, duration=0.03, waveform='sine')
            self.handle_tool_button_select(event.ui_element, game_app)
        elif event.ui_element == self.new_script_btn:
            target = self.script_target_dropdown.selected_option
            owner = None
            if target == "Selected Object" and self.physics_debug_manager and self.physics_debug_manager.selected_body:
                owner = self.physics_debug_manager.selected_body
            self.show_inline_script_editor(owner=owner)
        elif event.ui_element == self.edit_script_btn:
            selected = self.script_list.get_single_selection()
            if selected and selected in self._script_item_map:
                script = self._script_item_map[selected]
                self.show_inline_script_editor(script=script)
        elif event.ui_element == self.stop_script_btn:
            self.stop_selected_script()
        elif event.ui_element == self.refresh_scripts_btn:
            self.update_script_list()
        elif event.ui_element in self.force_field_buttons:
            self.selected_force_field_button_text = event.ui_element.text
            self.show_force_field_settings()
        elif event.ui_element == self.save_button:
            synthesizer.play_frequency(100, duration=0.2, waveform='sine')
            game_app.save_load_manager.save_world()
        elif event.ui_element == self.load_button:
            synthesizer.play_frequency(100, duration=0.2, waveform='sine')
            game_app.save_load_manager.load_world()
        elif event.ui_element == self.delete_all_button:
            synthesizer.play_frequency(1530, duration=0.05, waveform='sine')
            self.physics_manager.delete_all()
        elif event.ui_element == getattr(self, 'rectangle_color_button', None):
            if not self.rectangle_color_random:
                self.open_color_picker('rectangle')
        elif event.ui_element == getattr(self, 'rectangle_color_random_checkbox', None):
            self.toggle_color_mode('rectangle')
        elif event.ui_element == getattr(self, 'circle_color_button', None):
            if not self.circle_color_random:
                self.open_color_picker('circle')
        elif event.ui_element == getattr(self, 'triangle_color_button', None):
            if not self.triangle_color_random:
                self.open_color_picker('triangle')
        elif event.ui_element == getattr(self, 'polyhedron_color_button', None):
            if not self.poly_color_random:
                self.open_color_picker('polyhedron')
        elif event.ui_element == getattr(self, 'rectangle_color_random_checkbox', None):
            self.toggle_color_mode('rectangle')
        elif event.ui_element == getattr(self, 'circle_color_random_checkbox', None):
            self.toggle_color_mode('circle')
        elif event.ui_element == getattr(self, 'triangle_color_random_checkbox', None):
            self.toggle_color_mode('triangle')
        elif event.ui_element == getattr(self, 'polyhedron_color_random_checkbox', None):
            self.toggle_color_mode('polyhedron')
        elif event.ui_element == self.toggle_debug_window_button:
            self.physics_debug_window.show() if not self.physics_debug_window.visible else self.physics_debug_window.hide()
        elif event.ui_element == self.toggle_plotter_window_button:
            self.plotter_window.show() if not self.plotter_window.visible else self.plotter_window.hide()
        elif event.ui_element == self.toggle_all_debug_button:
            if self.physics_debug_manager:
                self.physics_debug_manager.toggle_all_debug()
                self.update_debug_checkboxes()
        elif event.ui_element == self.clear_debug_history_button:
            if self.physics_debug_manager:
                self.physics_debug_manager.clear_trails()
        elif event.ui_element == self.plotter_add_button:
            if self.plotter and self.physics_debug_manager.selected_body and hasattr(self, 'selected_plot_parameter'):
                print(f"Adding plot for {self.selected_plot_parameter} of {self.physics_debug_manager.selected_body}")
                self.physics_debug_manager.add_plot_parameter(self.physics_debug_manager.selected_body,
                                                              self.selected_plot_parameter)
        elif event.ui_element == self.plotter_clear_button:
            if self.plotter:
                self.plotter.clear_data()
        elif event.ui_element == self.toggle_script_window_button:
            self.script_window.show() if not self.script_window.visible else self.script_window.hide()
        elif event.ui_element == self.refresh_scripts_button:
            self.update_script_list()
        elif event.ui_element == self.stop_script_button:
            self.stop_selected_script()
        elif event.ui_element == self.open_script_editor_button:
            self.show_inline_script_editor()
        else:
            for setting_name, checkbox in self.debug_setting_checkboxes.items():
                if event.ui_element == checkbox:
                    if self.physics_debug_manager:
                        toggle_method = getattr(self.physics_debug_manager, f"toggle_{setting_name}", None)
                        if toggle_method:
                            toggle_method()
                            self.update_debug_checkboxes()
                    break
    def update_debug_checkboxes(self):
        if self.physics_debug_manager:
            settings = config.physics_debug
            for attr_name, checkbox in self.debug_setting_checkboxes.items():
                current_state = getattr(settings, attr_name, False)
                image_path = "sprites/gui/checkbox_true.png" if current_state else "sprites/gui/checkbox_false.png"
                checkbox.set_image(pygame.image.load(image_path))
    def update_plotter_dropdown(self):
        if self.physics_debug_manager and self.physics_debug_manager.selected_body:
            # Define available parameters to plot
            plot_parameters = [
                'Velocity Length',
                'Angular Velocity',
                'Kinetic Energy',
                'Potential Energy',
                'Total Energy',
                'Mass',
                'Moment of Inertia',
                'Linear Momentum',
                'Angular Momentum',
                'Force X',
                'Force Y',
                'Torque'
            ]
            self.plotter_dropdown.add_options(plot_parameters)
            self.plotter_dropdown.set_text('Select Parameter')
        else:
            self.plotter_dropdown.add_options(['No object selected'])
            self.plotter_dropdown.set_text('No object selected')
    def toggle_color_mode(self, shape_type):
        attr = f"{shape_type}_color_random"
        current = getattr(self, attr)
        new = not current
        setattr(self, attr, new)
        img_path = "sprites/gui/checkbox_true.png" if new else "sprites/gui/checkbox_false.png"
        img_element = getattr(self, f"{shape_type}_color_random_image")
        img_element.set_image(pygame.image.load(img_path))
    def handle_slider_move(self, event, game_app):
        if event.ui_element == self.strength_slider:
            game_app.force_field_manager.strength = int(event.value)
            self.text_label_strength.set_text(f"Force Field Strength: {game_app.force_field_manager.strength}")
        elif event.ui_element == self.radius_slider:
            game_app.force_field_manager.radius = int(event.value)
            self.text_label_radius.set_text(f"Force Field Radius: {game_app.force_field_manager.radius}")
    def handle_tool_button_select(self, button, game_app):
        self.hide_all_object_windows()
        game_app.input_handler.current_tool = button.text
        game_app.input_handler.first_joint_body = None
        tool_map = {
            "Circle": self.window_circle,
            "Rectangle": self.window_rectangle,
            "Triangle": self.window_triangle,
            "Polyhedron": self.window_polyhedron,
        }
        if button.text in tool_map:
            window_to_show = tool_map[button.text]
            if window_to_show:
                window_to_show.show()
    @profile("ui_update")
    def update(self, time_delta, clock):
        self.manager.update(time_delta)
        self.context_menu.update(time_delta, clock)
        if self.plotter:
            self.plotter_surface_element.set_image(self.plotter.get_surface())
        if self.script_window and self.script_window.alive():
            self.update_script_list()
            self.script_editor
    @profile("ui_draw")
    def draw(self, screen):
        def auto_scale_unit(value):
            """Преобразует значение в наиболее подходящую единицу измерения"""
            if value >= 100:
                return f"{value / 100:.2f} m"
            elif value >= 1:
                return f"{value:.2f} cm"
            else:
                return f"{value * 10:.2f} mm"
        self.manager.draw_ui(screen)
        if self.input_handler.preview_shape:
            shape_info = self.input_handler.preview_shape
            font = self.font
            text_color = (255, 255, 255)
            bg_color = (0, 0, 0, 128)
            padding = 4
            line_height = 16
            texts = []
            pos = self.camera.world_to_screen(shape_info["position"])
            if shape_info["type"] == "circle":
                radius = shape_info["radius"] * self.camera.target_scaling
                pygame.draw.circle(self.screen, shape_info["color"], pos, int(radius), 2)
                unit_r = auto_scale_unit(shape_info["radius"])
                area = math.pi * shape_info["radius"] ** 2
                perimeter = 2 * math.pi * shape_info["radius"]
                texts = [
                    f"R: {unit_r}",
                    f"Area: {auto_scale_unit(area)}",
                    f"Circumference: {auto_scale_unit(perimeter)}"
                ]
            elif shape_info["type"] == "rect":
                center = pos
                width = shape_info["width"] * self.camera.target_scaling
                height = shape_info["height"] * self.camera.target_scaling
                rect = pygame.Rect(0, 0, int(width), int(height))
                rect.center = center
                pygame.draw.rect(self.screen, shape_info["color"], rect, 2)
                area = shape_info["width"] * shape_info["height"]
                perimeter = 2 * (shape_info["width"] + shape_info["height"])
                texts = [
                    f"W: {auto_scale_unit(shape_info['width'])}",
                    f"H: {auto_scale_unit(shape_info['height'])}",
                    f"Area: {auto_scale_unit(area)}",
                    f"Perimeter: {auto_scale_unit(perimeter)}"
                ]
            elif shape_info["type"] == "triangle":
                center = pos
                width = shape_info["width"] * self.camera.target_scaling
                height = shape_info["height"] * self.camera.target_scaling
                half_width = width / 2
                top = (center[0], center[1] - height / 2)
                left = (center[0] - half_width, center[1] + height / 2)
                right = (center[0] + half_width, center[1] + height / 2)
                points = [top, left, right]
                pygame.draw.polygon(self.screen, shape_info["color"], points, 2)
                base = shape_info["width"]
                hgt = shape_info["height"]
                area = (base * hgt) / 2
                side = math.hypot(base / 2, hgt)
                perimeter = base + 2 * side
                texts = [
                    f"Base: {auto_scale_unit(base)}",
                    f"Height: {auto_scale_unit(hgt)}",
                    f"Area: {auto_scale_unit(area)}",
                    f"Perimeter: {auto_scale_unit(perimeter)}"
                ]
            if texts:
                text_surfaces = [font.render(text, True, text_color) for text in texts]
                total_height = len(texts) * line_height
                text_width = max(s.get_width() for s in text_surfaces)
                text_pos = (pos[0] + 20, pos[1] - total_height)
                bg_rect = pygame.Rect(text_pos[0], text_pos[1], text_width + padding * 2, total_height + padding * 2)
                text_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                text_surface.fill(bg_color)
                self.screen.blit(text_surface, bg_rect.topleft)
                for i, surface in enumerate(text_surfaces):
                    x = bg_rect.x + padding
                    y = bg_rect.y + padding + i * line_height
                    self.screen.blit(surface, (x, y))
    def open_context_menu(self, position, clicked_object):
        self.context_menu.show_menu(position, clicked_object)
    def open_properties_window(self, obj):
        print(f"Opening properties for object: {obj}")
        self.properties_window = pygame_gui.elements.UIWindow(
            pygame.Rect(100, 100, 300, 400), manager=self.manager,
            window_display_title=f"Properties: {obj.body.mass:.2f}kg")
        UILabel(relative_rect=pygame.Rect(10, 10, 280, 20), text=f"Mass: {obj.body.mass:.2f}kg", container=self.properties_window, manager=self.manager)
        UILabel(relative_rect=pygame.Rect(10, 30, 280, 20), text=f"Velocity: {obj.body.velocity.length:.2f}m/s", container=self.properties_window, manager=self.manager)
    def hide_all_object_windows(self):
        self.window_rectangle.hide()
        self.window_circle.hide()
        self.window_triangle.hide()
        self.window_polyhedron.hide()
    def show_force_field_settings(self):
        self.strength_slider.show()
        self.radius_slider.show()
        self.text_label_radius.show()
        self.text_label_strength.show()
    def hide_force_field_settings(self):
        self.strength_slider.hide()
        self.radius_slider.hide()
        self.text_label_radius.hide()
        self.text_label_strength.hide()
    def toggle_pause_icon(self, show):
        if show:
            self.pause_icon.show()
        else:
            self.pause_icon.hide()
    def resize(self, new_width, new_height):
        config.app.screen_width = new_width
        config.app.screen_height = new_height