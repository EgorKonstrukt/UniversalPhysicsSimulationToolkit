import pygame
import pygame_gui
from UPST.modules.undo_redo_manager import get_undo_redo
from pygame_gui.elements import UIButton, UIImage, UIWindow, UICheckBox
from .config_option import ConfigOption
from .menu_builder import build_menu_structure
from .handlers import ContextMenuHandlers
from UPST.config import config

class ContextMenu(ContextMenuHandlers):
    def __init__(self, manager, ui_manager, app):
        self.app = app
        self.manager = manager
        self.ui_manager = ui_manager
        self.undo_redo = None  # Will be set via get_undo_redo() in handlers
        self.context_menu = None
        self.context_menu_buttons = []
        self.clicked_object = None
        self.properties_window = None
        self.script_window = None
        self.submenu_window = None
        self.submenu_buttons = []
        self.menu_structure = []
        self.hover_start_time = {}
        self.hovered_button = None
        self.menu_line_start_pos = None
        self.last_object_pos = None
        self.plugin_manager = app.plugin_manager
        self._placeholder_icon = None

    def _get_placeholder_icon(self, size):
        if self._placeholder_icon is None or self._placeholder_icon.get_size() != (size, size):
            self._placeholder_icon = pygame.Surface((size, size), pygame.SRCALPHA)
            self._placeholder_icon.fill((128, 0, 128, 200))
            pygame.draw.rect(self._placeholder_icon, (192, 128, 192, 255), (0, 0, size, size), 2)
        return self._placeholder_icon

    def create_menu(self):
        if self.context_menu: self.context_menu.kill()
        for btn, _ in self.context_menu_buttons: btn.kill()
        self.context_menu_buttons.clear()
        menu_items = [opt.name for opt in self.menu_structure]
        total_height = len(menu_items) * (config.context_menu.button_height + config.context_menu.button_spacing) - config.context_menu.button_spacing
        window_height = total_height + 28
        if self.clicked_object:
            base_name = getattr(self.clicked_object, 'name', self.clicked_object.__class__.__name__)
            tags = getattr(self.clicked_object, 'tags', None)
            title = f"{base_name} [{', '.join(sorted(str(t) for t in tags))}]" if isinstance(tags, (set, list)) and tags else base_name
        else:
            title = "World"
        self.context_menu = UIWindow(rect=pygame.Rect(0, 0, 260, window_height), manager=self.manager, window_display_title=title, object_id=pygame_gui.core.ObjectID(object_id='#context_menu_window', class_id='@context_menu'), resizable=False)
        self.context_menu.set_blocking(False)
        self.context_menu.border_colour = pygame.Color(255, 255, 255)
        for i, item in enumerate(menu_items):
            opt = self.menu_structure[i]
            btn_y = 4 + i * (config.context_menu.button_height + config.context_menu.button_spacing)
            text = f"{item} >" if opt.children else item
            btn = UIButton(relative_rect=pygame.Rect(4, btn_y, 248, config.context_menu.button_height), text=text, manager=self.manager, container=self.context_menu, object_id=pygame_gui.core.ObjectID(object_id=f'#context_btn_{i}', class_id='@context_button'))
            if opt.icon:
                try:
                    if isinstance(opt.icon, str):
                        img_surf = pygame.image.load(opt.icon).convert_alpha()
                    else:
                        img_surf = opt.icon
                except (FileNotFoundError, pygame.error):
                    icon_size = config.context_menu.button_height - 9
                    img_surf = self._get_placeholder_icon(icon_size)
                UIImage(relative_rect=pygame.Rect(11, btn_y + 4, config.context_menu.button_height - 9, config.context_menu.button_height - 9), image_surface=img_surf, manager=self.manager, container=self.context_menu)
            self.context_menu_buttons.append((btn, opt))

    def show_menu(self, position, clicked_object):
        selected_bodies = list(self.app.physics_manager.selected_bodies)
        if len(selected_bodies) > 1:
            self.clicked_object = selected_bodies
        else:
            self.clicked_object = clicked_object

        world_pos = self.app.camera.screen_to_world(position) if self.app.camera else position

        self.menu_structure = build_menu_structure(self.clicked_object, self.app, self.plugin_manager,
                                                   world_pos=world_pos)
        self.create_menu()
        x, y = position
        max_x, max_y = pygame.display.get_surface().get_size()
        rect = self.context_menu.get_abs_rect()
        x = min(x, max_x - rect.width)
        y = min(y, max_y - rect.height)
        self.context_menu.set_position((x, y))
        self.context_menu.show()
        self.menu_line_start_pos = getattr(self.clicked_object, 'position', None) if not isinstance(self.clicked_object,
                                                                                                    list) else None
        self.last_object_pos = self.menu_line_start_pos

    def hide(self):
        if self.context_menu: self.context_menu.hide()
        if self.submenu_window: self.submenu_window.kill(); self.submenu_window = None
        self.submenu_buttons.clear()
        self.hover_start_time.clear()
        self.hovered_button = None
        self.menu_line_start_pos = None
        self.last_object_pos = None

    def is_point_inside_menu(self, pos):
        return self.context_menu and self.context_menu.visible and self.context_menu.get_abs_rect().collidepoint(pos)

    def is_point_inside_submenu(self, pos):
        return self.submenu_window and self.submenu_window.visible and self.submenu_window.get_abs_rect().collidepoint(pos)

    def _show_submenu(self, submenu_options, position):
        self.hide_submenu()
        max_x, max_y = pygame.display.get_surface().get_size()
        submenu_height = len(submenu_options) * (config.context_menu.button_height + config.context_menu.button_spacing) - config.context_menu.button_spacing + 28
        submenu_width = 250
        x, y = position
        x = min(x, max_x - submenu_width); y = min(y, max_y - submenu_height)
        self.submenu_window = UIWindow(rect=pygame.Rect(x, y, submenu_width, submenu_height), manager=self.manager, window_display_title=str(self.clicked_object.__class__.__name__), object_id=pygame_gui.core.ObjectID(object_id='#submenu_window', class_id='@submenu'), resizable=False)
        self.submenu_window.set_blocking(False)
        self.submenu_buttons = []
        for i, opt in enumerate(submenu_options):
            btn_y = 4 + i * (config.context_menu.button_height + config.context_menu.button_spacing)
            text = f"{opt.name} >" if opt.children else opt.name
            if getattr(opt, 'is_checkbox', False):
                cb = UICheckBox(relative_rect=pygame.Rect(4, btn_y, config.context_menu.button_height, config.context_menu.button_height), text=opt.name, manager=self.manager, container=self.submenu_window, object_id=pygame_gui.core.ObjectID(object_id=f'#cb_{i}', class_id='@submenu_checkbox'))
                if getattr(opt, 'get_state', None): cb.set_state(opt.get_state(self))
                self.submenu_buttons.append((cb, opt))
            else:
                btn = UIButton(relative_rect=pygame.Rect(4, btn_y, submenu_width - 16, config.context_menu.button_height), text=text, manager=self.manager, container=self.submenu_window, object_id=pygame_gui.core.ObjectID(object_id=f'#submenu_btn_{i}', class_id='@context_button'))
                self.submenu_buttons.append((btn, opt))

    def hide_submenu(self):
        if self.submenu_window: self.submenu_window.kill(); self.submenu_window = None
        self.submenu_buttons.clear()

    def process_event(self, event):
        if self.properties_window: self.properties_window.process_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            inside_main = self.is_point_inside_menu(mouse_pos)
            inside_sub = self.is_point_inside_submenu(mouse_pos)
            inside_rename = hasattr(self, '_rename_win') and self._rename_win.alive() and self._rename_win.get_abs_rect().collidepoint(mouse_pos)
            if not (inside_main or inside_sub or inside_rename):
                self.hide()
                return True
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                for btn, option in self.context_menu_buttons:
                    if event.ui_element == btn:
                        if option.children:
                            menu_rect = btn.get_abs_rect()
                            self._show_submenu(option.children, (menu_rect.right, menu_rect.top))
                        else:
                            self.hide_submenu()
                            self._execute_option(option)
                            self.hide()
                        return True
                if self.submenu_window:
                    for btn, option in self.submenu_buttons:
                        if event.ui_element == btn:
                            if option.children:
                                menu_rect = btn.get_abs_rect()
                                self._show_submenu(option.children, (menu_rect.right, menu_rect.top))
                            else:
                                self._execute_option(option)
                                self.hide()
                            return True
                if hasattr(self, '_rename_win') and self._rename_win.alive():
                    if event.ui_element == self._rename_ok:
                        new_name = self._rename_entry.get_text().strip()
                        if new_name:
                            self.clicked_object.name = new_name
                            get_undo_redo().take_snapshot()
                        self._rename_win.kill()
                        return True
                    elif event.ui_element == self._rename_cancel:
                        self._rename_win.kill()
                        return True
            elif event.user_type in (pygame_gui.UI_CHECK_BOX_CHECKED, pygame_gui.UI_CHECK_BOX_UNCHECKED):
                for cb, opt in self.submenu_buttons:
                    if event.ui_element == cb and getattr(opt, 'is_checkbox', False):
                        if opt.set_state: opt.set_state(self, cb.checked)
                        break
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            self.hovered_button = None
            if self.context_menu and self.context_menu.visible:
                for btn, option in self.context_menu_buttons:
                    if btn.get_abs_rect().collidepoint(mouse_pos):
                        self.hovered_button = (btn, option)
                        break
            if self.submenu_window:
                for btn, option in self.submenu_buttons:
                    if btn.get_abs_rect().collidepoint(mouse_pos):
                        self.hovered_button = (btn, option)
                        break
        return False

    def update(self, time_delta, clock):
        if self.properties_window: self.properties_window.update(time_delta)
        if self.hovered_button:
            btn, option = self.hovered_button
            btn_id = id(btn)
            if btn_id not in self.hover_start_time:
                self.hover_start_time[btn_id] = pygame.time.get_ticks()
            else:
                elapsed = (pygame.time.get_ticks() - self.hover_start_time[btn_id]) / 1000.0
                is_main_menu_button = any(b == btn for b, _ in self.context_menu_buttons)
                if is_main_mode_button := is_main_menu_button:
                    if option.children:
                        if elapsed >= config.context_menu.hover_delay:
                            menu_rect = btn.get_abs_rect()
                            self._show_submenu(option.children, (menu_rect.right, menu_rect.top))
                            self.hover_start_time.clear()
                    else:
                        if self.submenu_window:
                            self.hide_submenu()
        else:
            self.hover_start_time.clear()
        if self.clicked_object and self.menu_line_start_pos and hasattr(self.clicked_object, 'position'):
            current_pos = self.clicked_object.position
            if self.last_object_pos != current_pos:
                self.menu_line_start_pos = current_pos
                self.last_object_pos = current_pos

    def draw_menu_line(self, screen, camera):
        if not self.menu_line_start_pos or not self.context_menu or not self.context_menu.visible: return
        start_screen = camera.world_to_screen(self.menu_line_start_pos)
        end_screen = self.context_menu.get_abs_rect().center
        pygame.draw.line(screen, (255, 255, 255), start_screen, end_screen, 2)

    def _execute_option(self, option):
        if option.handler: option.handler(self)