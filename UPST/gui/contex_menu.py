import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UIHorizontalSlider, UILabel, UIButton, UITextEntryLine, UIImage, \
    UIPanel, UITextBox, UISelectionList
from pygame_gui.windows import UIConsoleWindow
import pygame
import pymunk
import math
from UPST.config import config
from UPST.gui.properties_window import PropertiesWindow


class ContextMenu:
    def __init__(self, manager, ui_manager):
        self.manager = manager
        self.ui_manager = ui_manager
        self.context_menu = None
        self.context_menu_list = None
        self.clicked_object = None
        self.properties_window = None
        self.create_menu()

    def create_menu(self):
        self.context_menu = UIPanel(
            relative_rect=pygame.Rect(0, 0, 260, 420),
            manager=self.manager,
            visible=False,
            margins={'left': 5, 'right': 5, 'top': 5, 'bottom': 5},
            object_id=pygame_gui.core.ObjectID(object_id='#context_menu_panel', class_id='@context_menu')
        )
        menu_items = [
            'Delete Object',
            'Properties',
            'Duplicate',
            'Freeze/Unfreeze',
            'Set Velocity',
            'Set Angular Velocity',
            'Set Mass',
            'Set Friction',
            'Set Elasticity',
            'Add Force',
            'Add Torque',
            'Reset Position',
            'Reset Rotation',
            'Make Static',
            'Make Dynamic',
            'Select for Debug'
        ]
        self.context_menu_list = UISelectionList(
            relative_rect=pygame.Rect(0, 0, 250, 400),
            item_list=menu_items,
            container=self.context_menu,
            manager=self.manager,
            allow_double_clicks=False,
            object_id=pygame_gui.core.ObjectID(object_id='#context_menu_list', class_id='@context_menu')
        )

    def show_menu(self, position, clicked_object):
        self.clicked_object = clicked_object
        x, y = position
        max_x, max_y = pygame.display.get_surface().get_size()
        rect = self.context_menu.rect
        x = min(x, max_x - rect.width)
        y = min(y, max_y - rect.height)
        self.context_menu.set_position((x, y))
        self.context_menu.show()

    def hide(self):
        self.context_menu.hide()

    def process_event(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.context_menu_list:
                self.handle_selection(event.text)
                self.context_menu.hide()
        if self.properties_window:
            self.properties_window.process_event(event)

    def handle_selection(self, selection):
        if not self.clicked_object: return
        handlers = {
            'Properties': self.open_properties_window,
            'Delete Object': self.delete_object,
            'Duplicate': self.duplicate_object,
            'Freeze/Unfreeze': self.toggle_freeze_object,
            'Set Velocity': self.set_velocity_dialog,
            'Set Angular Velocity': self.set_angular_velocity_dialog,
            'Set Mass': self.set_mass_dialog,
            'Set Friction': self.set_friction_dialog,
            'Set Elasticity': self.set_elasticity_dialog,
            'Add Force': self.add_force_dialog,
            'Add Torque': self.add_torque_dialog,
            'Reset Position': self.reset_position,
            'Reset Rotation': self.reset_rotation,
            'Make Static': self.make_static,
            'Make Dynamic': self.make_dynamic,
            'Select for Debug': self.select_for_debug
        }
        handler = handlers.get(selection)
        if handler: handler()

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
        if not self.clicked_object or not self.clicked_object.shapes: return
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
        else: return
        ns.friction, ns.elasticity = s.friction, s.elasticity
        nb.position, nb.velocity, nb.angular_velocity = np, b.velocity, b.angular_velocity
        self.ui_manager.physics_manager.space.add(nb, ns)

    def toggle_freeze_object(self):
        if not self.clicked_object: return
        b = self.clicked_object
        if b.velocity.length < 0.1 and abs(b.angular_velocity) < 0.1:
            b.velocity, b.angular_velocity = (100, 0), 1.0
        else:
            b.velocity, b.angular_velocity = (0, 0), 0

    def set_velocity_dialog(self):
        if self.clicked_object: self.clicked_object.velocity = (100, 0)

    def set_angular_velocity_dialog(self):
        if self.clicked_object: self.clicked_object.angular_velocity = 2.0

    def set_mass_dialog(self):
        if self.clicked_object: self.clicked_object.mass = 10.0

    def set_friction_dialog(self):
        if self.clicked_object and self.clicked_object.shapes:
            for s in self.clicked_object.shapes: s.friction = 0.8

    def set_elasticity_dialog(self):
        if self.clicked_object and self.clicked_object.shapes:
            for s in self.clicked_object.shapes: s.elasticity = 0.9

    def add_force_dialog(self):
        if self.clicked_object:
            self.clicked_object.apply_force_at_world_point((1000, 0), self.clicked_object.position)

    def add_torque_dialog(self):
        if self.clicked_object: self.clicked_object.torque += 1000

    def reset_position(self):
        if self.clicked_object:
            self.clicked_object.position, self.clicked_object.velocity = (0, 0), (0, 0)

    def reset_rotation(self):
        if self.clicked_object:
            self.clicked_object.angle, self.clicked_object.angular_velocity = 0, 0

    def make_static(self):
        if self.clicked_object: self.clicked_object.body_type = pymunk.Body.STATIC

    def make_dynamic(self):
        if self.clicked_object: self.clicked_object.body_type = pymunk.Body.DYNAMIC

    def select_for_debug(self):
        if self.clicked_object and self.ui_manager.physics_debug_manager:
            self.ui_manager.physics_debug_manager.selected_body = self.clicked_object