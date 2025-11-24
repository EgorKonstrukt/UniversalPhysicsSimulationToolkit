import pygame
import pygame_gui
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
from UPST.gui.contex_menu import ContextMenu
from UPST.gui.bottom_bar import BottomBar
from UPST.gui.top_left_bar import TopLeftBar
from UPST.gui.top_right_bar import TopRightBar
from UPST.gui.force_field_ui import ForceFieldUI
from UPST.gui.console_ui import ConsoleUI
from UPST.gui.settings_ui import SettingsUI
from UPST.gui.plotter_ui import PlotterUI
import math

class UIManager:
    def __init__(self, screen_width, screen_height, physics_manager, camera, input_handler, screen, font, tool_system=None, network_manager=None, app=None):
        self.app = app
        self.manager = pygame_gui.UIManager((screen_width, screen_height), 'theme.json')
        self.tool_system = tool_system
        self.screen = screen
        self.font = font
        self.input_handler = input_handler
        self.physics_manager = physics_manager
        self.camera = camera
        self.network_manager = network_manager
        self.network_menu = None
        self.physics_debug_manager = None
        self.plotter = None
        self.active_color_picker = None
        self.color_picker_for_shape = None
        self.script_editor = None
        self.context_menu = ContextMenu(self.manager, self)
        self.force_field_ui = ForceFieldUI(self.manager, screen_width, screen_height, self)
        self.console_ui = ConsoleUI(self.manager, screen_width, screen_height)
        self.settings_ui = SettingsUI(self.manager, screen_height)
        self.plotter_ui = PlotterUI(self.manager)
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

    def _init_fonts(self):
        self.manager.add_font_paths(font_name="consolas", regular_path="fonts/Consolas.ttf")
        self.manager.preload_fonts([{'name':'consolas','size':14,'style':'regular'},{'name':'consolas','size':18,'style':'regular'},{'name':'consolas','size':20,'style':'bold'}])

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

    def set_plotter(self, plotter):
        self.plotter = plotter
        self.plotter_ui.set_plotter(plotter)

    def toggle_color_mode(self, shape_type):
        current = getattr(self, f"{shape_type}_color_random", True)
        setattr(self, f"{shape_type}_color_random", not current)
        img_path = "sprites/gui/checkbox_true.png" if not current else "sprites/gui/checkbox_false.png"
        img_element = getattr(self, f"{shape_type}_color_random_image")
        img_element.set_image(pygame.image.load(img_path))

    def open_color_picker(self, shape_type):
        if self.active_color_picker:
            self.active_color_picker.kill()
        initial = self.shape_colors.get(shape_type, pygame.Color(128,128,128))
        self.active_color_picker = pygame_gui.windows.UIColourPickerDialog(rect=pygame.Rect(0,0,420,420), manager=self.manager, initial_colour=initial, window_title=f"Pick Color for {shape_type.title()}")
        self.color_picker_for_shape = shape_type

    def process_event(self, event, game_app):
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

    def _handle_button_press(self, event, game_app):
        if event.ui_element in self.force_field_ui.force_field_buttons:
            self.force_field_ui.handle_button_press(event.ui_element, game_app)
        elif hasattr(event.ui_element, 'tool_name'):
            self.tool_system.activate_tool(event.ui_element.tool_name)

        elif event.ui_element == self.plotter_ui.add_btn:
            self._handle_plot_add()
        elif event.ui_element == self.plotter_ui.clear_btn:
            if self.plotter:
                self.plotter.clear_data()

    def _handle_plot_add(self):
        if self.plotter and self.physics_debug_manager.selected_body and hasattr(self, 'selected_plot_parameter'):
            self.physics_debug_manager.add_plot_parameter(self.physics_debug_manager.selected_body, self.selected_plot_parameter)

    def _handle_color_pick(self, event):
        if self.active_color_picker and event.ui_element == self.active_color_picker and self.tool_system.current_tool:
            if hasattr(self.tool_system.current_tool, 'set_color'):
                self.tool_system.current_tool.set_color(pygame.Color(event.colour))
            self.active_color_picker = None
            self.color_picker_for_shape = None

    def _handle_slider_move(self, event, game_app):
        self.force_field_ui.handle_slider_move(event, game_app)

    def _on_resize(self):
        screen_w, screen_h = config.app.screen_width, config.app.screen_height
        self.manager.set_window_resolution((screen_w, screen_h))
        self.force_field_ui.resize(screen_w, screen_h)
        self.console_ui.resize(screen_w, screen_h)
        self.settings_ui.resize(screen_h)
        self.plotter_ui.resize()
        self.bottom_bar.resize(screen_w, screen_h)

    def update(self, time_delta, clock):
        self.manager.update(time_delta)
        self.context_menu.update(time_delta, clock)
        if self.plotter:
            self.plotter_ui.update_surface(self.plotter.get_surface())

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