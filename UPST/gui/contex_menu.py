import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UIHorizontalSlider, UILabel, UIButton, UITextEntryLine, UIImage, \
    UIPanel, UITextBox, UISelectionList
from pygame_gui.windows import UIConsoleWindow
import pygame
import pymunk
import math
from UPST.config import config
from UPST.gui.properties_window import PropertiesWindow
from UPST.gui.texture_window import TextureWindow
import tkinter as tk
from tkinter import simpledialog, messagebox
from UPST.gui.script_management_window import ScriptManagementWindow


class ConfigOption:
    def __init__(self, name, value=None, options=None, handler=None, children=None):
        self.name = name
        self.value = value
        self.options = options
        self.handler = handler
        self.children = children or []


class ContextMenu:
    def __init__(self, manager, ui_manager):
        self.manager = manager
        self.ui_manager = ui_manager
        self.context_menu = None
        self.context_menu_buttons = []
        self.clicked_object = None
        self.properties_window = None
        self.script_window = None
        self.button_height = 30
        self.button_spacing = -4
        self.submenu_window = None
        self.submenu_buttons = []
        self.menu_structure = self._build_menu_structure()
        self.hover_start_time = {}
        self.hover_delay = 0.5
        self.hovered_button = None

    def _build_menu_structure(self):
        return [
            ConfigOption("Delete Object", handler=self.delete_object),
            ConfigOption("Properties", handler=self.open_properties_window),
            ConfigOption("Duplicate", handler=self.duplicate_object),
            ConfigOption("Freeze/Unfreeze", handler=self.toggle_freeze_object),
            ConfigOption("Set Texture", handler=self.open_texture_window),
            ConfigOption("Reset", children=[
                ConfigOption("Reset Position", handler=self.reset_position),
                ConfigOption("Reset Rotation", handler=self.reset_rotation)
            ]),
            ConfigOption("Body Type", children=[
                ConfigOption("Make Static", handler=self.make_static),
                ConfigOption("Make Dynamic", handler=self.make_dynamic)
            ]),
            ConfigOption("Select for Debug", handler=self.select_for_debug),
            ConfigOption("Scripts", children=[
                ConfigOption("Run Python Script",
                             handler=lambda: self.ui_manager.show_inline_script_editor(owner=self.clicked_object)),
                ConfigOption("Edit Script", handler=self.edit_script),
                ConfigOption("Script Management", handler=self.open_script_management)
            ])
        ]

    def create_menu(self):
        if hasattr(self, 'context_menu') and self.context_menu:
            self.context_menu.kill()
        for btn, _ in self.context_menu_buttons:
            btn.kill()
        self.context_menu_buttons.clear()

        menu_items = [opt.name for opt in self.menu_structure]
        total_height = len(menu_items) * (self.button_height + self.button_spacing) - self.button_spacing
        panel_height = total_height + 8

        self.context_menu = UIPanel(
            relative_rect=pygame.Rect(0, 0, 260, panel_height),
            manager=self.manager,
            visible=False,
            margins={'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
            object_id=pygame_gui.core.ObjectID(object_id='#context_menu_panel', class_id='@context_menu')
        )

        for i, item in enumerate(menu_items):
            btn_y = 4 + i * (self.button_height + self.button_spacing)
            has_children = bool(self.menu_structure[i].children)
            text = f"{item} >" if has_children else item
            btn = UIButton(
                relative_rect=pygame.Rect(4, btn_y, 252, self.button_height),
                text=text,
                manager=self.manager,
                container=self.context_menu,
                object_id=pygame_gui.core.ObjectID(object_id=f'#context_btn_{i}', class_id='@context_button'),
                anchors={'left': 'left', 'right': 'left', 'top': 'top', 'bottom': 'top'}
            )
            self.context_menu_buttons.append((btn, self.menu_structure[i]))

    def open_script_management(self):
        if self.script_window and self.script_window.alive(): self.script_window.kill()
        rect = pygame.Rect(100, 100, 400, 300)
        self.script_window = ScriptManagementWindow(rect, self.manager, self.ui_manager.physics_manager.script_manager)

    def show_menu(self, position, clicked_object):
        self.clicked_object = clicked_object
        self.create_menu()
        x, y = position
        max_x, max_y = pygame.display.get_surface().get_size()
        rect = self.context_menu.rect
        x = min(x, max_x - rect.width)
        y = min(y, max_y - rect.height)
        self.context_menu.set_position((x, y))
        self.context_menu.show()

    def hide(self):
        if self.context_menu:
            self.context_menu.hide()
        if self.submenu_window:
            self.submenu_window.kill()
            self.submenu_window = None
        self.submenu_buttons.clear()
        self.hover_start_time.clear()
        self.hovered_button = None

    def is_point_inside_menu(self, pos):
        if not self.context_menu or not self.context_menu.visible:
            return False
        return self.context_menu.get_abs_rect().collidepoint(pos)

    def is_point_inside_submenu(self, pos):
        if not self.submenu_window or not self.submenu_window.visible:
            return False
        return self.submenu_window.get_abs_rect().collidepoint(pos)

    def _show_submenu(self, submenu_options, position):
        self.hide_submenu()
        max_x, max_y = pygame.display.get_surface().get_size()
        submenu_height = len(submenu_options) * (self.button_height + self.button_spacing) - self.button_spacing + 8
        submenu_width = 200

        x, y = position
        x = min(x, max_x - submenu_width)
        y = min(y, max_y - submenu_height)

        self.submenu_window = UIPanel(
            relative_rect=pygame.Rect(x, y, submenu_width, submenu_height),
            manager=self.manager,
            visible=True,
            margins={'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
            object_id=pygame_gui.core.ObjectID(object_id='#submenu_panel', class_id='@submenu')
        )

        self.submenu_buttons = []
        for i, opt in enumerate(submenu_options):
            btn_y = 4 + i * (self.button_height + self.button_spacing)
            has_children = bool(opt.children)
            text = f"{opt.name} >" if has_children else opt.name
            btn = UIButton(
                relative_rect=pygame.Rect(4, btn_y, submenu_width - 8, self.button_height),
                text=text,
                manager=self.manager,
                container=self.submenu_window,
                object_id=pygame_gui.core.ObjectID(object_id=f'#submenu_btn_{i}', class_id='@submenu_button'),
                anchors={'left': 'left', 'right': 'left', 'top': 'top', 'bottom': 'top'}
            )
            self.submenu_buttons.append((btn, opt))

    def hide_submenu(self):
        if self.submenu_window:
            self.submenu_window.kill()
            self.submenu_window = None
        self.submenu_buttons.clear()

    def process_event(self, event):
        if self.properties_window:
            self.properties_window.process_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.context_menu and self.context_menu.visible:
                if not self.is_point_inside_menu(mouse_pos) and not self.is_point_inside_submenu(mouse_pos):
                    self.hide()
                    return True

        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            # Check main menu buttons
            for btn, option in self.context_menu_buttons:
                if event.ui_element == btn:
                    if option.children:
                        menu_rect = btn.get_abs_rect()
                        submenu_pos = (menu_rect.right, menu_rect.top)
                        self._show_submenu(option.children, submenu_pos)
                    else:
                        self._execute_option(option)
                        self.hide()
                    break

            # Check submenu buttons
            if self.submenu_window:
                for btn, option in self.submenu_buttons:
                    if event.ui_element == btn:
                        if option.children:
                            menu_rect = btn.get_abs_rect()
                            submenu_pos = (menu_rect.right, menu_rect.top)
                            self._show_submenu(option.children, submenu_pos)
                        else:
                            self._execute_option(option)
                            self.hide()
                        break

        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            self.hovered_button = None

            # Check if hovering over main menu
            if self.context_menu and self.context_menu.visible:
                for btn, option in self.context_menu_buttons:
                    if btn.get_abs_rect().collidepoint(mouse_pos):
                        self.hovered_button = (btn, option)
                        break

            # Check if hovering over submenu
            if self.submenu_window:
                for btn, option in self.submenu_buttons:
                    if btn.get_abs_rect().collidepoint(mouse_pos):
                        self.hovered_button = (btn, option)
                        break

        return False

    def update(self, time_delta, clock):
        if self.properties_window:
            self.properties_window.update(time_delta)

        if self.hovered_button:
            btn, option = self.hovered_button
            btn_id = id(btn)

            if btn_id not in self.hover_start_time:
                self.hover_start_time[btn_id] = pygame.time.get_ticks()
            else:
                elapsed = (pygame.time.get_ticks() - self.hover_start_time[btn_id]) / 1000.0
                if elapsed >= self.hover_delay and option.children:
                    menu_rect = btn.get_abs_rect()
                    submenu_pos = (menu_rect.right, menu_rect.top)
                    self._show_submenu(option.children, submenu_pos)
                    self.hover_start_time.clear()
        else:
            self.hover_start_time.clear()

    def _execute_option(self, option):
        if not self.clicked_object and option.name not in ("Run Python Script", "Script Management"):
            return
        if option.handler:
            option.handler()

    def edit_script(self):
        if not self.clicked_object or not hasattr(self.clicked_object, '_scripts'):
            return
        scripts = self.clicked_object._scripts
        if not scripts:
            return
        script = scripts[0]
        self.ui_manager.show_inline_script_editor(script=script, owner=self.clicked_object)

    def open_properties_window(self):
        if self.properties_window:
            self.properties_window.kill()
        self.properties_window = PropertiesWindow(
            manager=self.manager,
            body=self.clicked_object,
            on_close_callback=lambda: setattr(self, 'properties_window', None)
        )

    def delete_object(self):
        if self.clicked_object:
            self.ui_manager.physics_manager.remove_body(self.clicked_object)

    def duplicate_object(self):
        if not self.clicked_object or not self.clicked_object.shapes:
            return
        b = self.clicked_object
        s = next(iter(b.shapes))
        off = pymunk.Vec2d(50, 50)
        np = b.position + off

        if isinstance(s, pymunk.Circle):
            nb = pymunk.Body(b.mass, b.moment)
            ns = pymunk.Circle(nb, s.radius, s.offset)
        elif isinstance(s, pymunk.Poly):
            nb = pymunk.Body(b.mass, b.moment)
            ns = pymunk.Poly(nb, s.get_vertices())
        else:
            return

        ns.friction, ns.elasticity = s.friction, s.elasticity
        nb.position, nb.velocity, nb.angular_velocity = np, b.velocity, b.angular_velocity
        self.ui_manager.physics_manager.space.add(nb, ns)

    def toggle_freeze_object(self):
        if not self.clicked_object:
            return
        b = self.clicked_object
        if b.velocity.length < 0.1 and abs(b.angular_velocity) < 0.1:
            b.velocity, b.angular_velocity = (100, 0), 1.0
        else:
            b.velocity, b.angular_velocity = (0, 0), 0

    def open_texture_window(self):
        if self.properties_window:
            self.properties_window.close()
        self.properties_window = TextureWindow(
            manager=self.manager,
            body=self.clicked_object,
            on_close_callback=lambda: setattr(self, 'properties_window', None)
        )

    def reset_position(self):
        if self.clicked_object:
            self.clicked_object.position, self.clicked_object.velocity = (0, 0), (0, 0)

    def reset_rotation(self):
        if self.clicked_object:
            self.clicked_object.angle, self.clicked_object.angular_velocity = 0, 0

    def make_static(self):
        if self.clicked_object:
            self.clicked_object.body_type = pymunk.Body.STATIC

    def make_dynamic(self):
        if self.clicked_object:
            self.clicked_object.body_type = pymunk.Body.DYNAMIC

    def select_for_debug(self):
        if self.clicked_object and self.ui_manager.physics_debug_manager:
            self.ui_manager.physics_debug_manager.selected_body = self.clicked_object