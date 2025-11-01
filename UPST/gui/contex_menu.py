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
from UPST.gui.script_menu import ScriptMenu
from UPST.script_system.script_system import GlobalScriptManager

class ContextMenu:
    def __init__(self, manager, ui_manager):
        self.manager = manager
        self.ui_manager = ui_manager
        self.context_menu = None
        self.context_menu_list = None
        self.clicked_object = None
        self.properties_window = None
        self.script_menu = ScriptMenu(manager, ui_manager, self)
        self.global_script_manager = GlobalScriptManager()
        self.global_script_manager.set_context_provider(lambda: {
            'ui_manager': self.ui_manager,
            'context_menu': self,
            'clicked_object': self.clicked_object,
            'config': config,
            'PropertiesWindow': PropertiesWindow,
            'TextureWindow': TextureWindow,
            'physics_manager': getattr(self.ui_manager, 'physics_manager', None),
            'space': getattr(getattr(self.ui_manager, 'physics_manager', None), 'space', None)
        })
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
            'Set Texture',
            'Reset Position',
            'Reset Rotation',
            'Make Static',
            'Make Dynamic',
            'Select for Debug',
            'Run Python Script'
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
        self.script_menu.hide()

    def process_event(self, event):
        if self.properties_window:
            self.properties_window.process_event(event)

        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.context_menu_list:
                self.handle_selection(event.text)
                self.context_menu.hide()

        self.script_menu.process_event(event)

    def handle_selection(self, selection):
        if not self.clicked_object and selection != 'Run Python Script':
            return

        handlers = {
            'Properties': self.open_properties_window,
            'Delete Object': self.delete_object,
            'Duplicate': self.duplicate_object,
            'Freeze/Unfreeze': self.toggle_freeze_object,
            'Set Texture': self.open_texture_window,
            'Reset Position': self.reset_position,
            'Reset Rotation': self.reset_rotation,
            'Make Static': self.make_static,
            'Make Dynamic': self.make_dynamic,
            'Select for Debug': self.select_for_debug,
            'Run Python Script': self.run_python_script
        }

        handler = handlers.get(selection)
        if handler:
            handler()

    def run_python_script(self):
        self.script_menu.show_menu(
            pygame.mouse.get_pos(),
            self.clicked_object
        )

    def open_properties_window(self):
        if self.properties_window:
            self.properties_window.kill()
        self.properties_window = PropertiesWindow(
            manager=self.manager,
            body=self.clicked_object,
            on_close_callback=lambda: setattr(self, 'properties_window', None)
        )

    def update(self, time_delta, clock):
        if self.properties_window:
            self.properties_window.update(time_delta)
        self.global_script_manager.update()

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