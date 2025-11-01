import pygame
import pygame_gui
from pygame_gui.elements import UISelectionList, UIPanel, UIWindow, UITextBox, UIButton
from UPST.script_system.script_system import GlobalScriptManager
from UPST.gui.script_input_window import ScriptInputWindow
from UPST.config import config
from UPST.gui.properties_window import PropertiesWindow
from UPST.gui.texture_window import TextureWindow

class ScriptMenu:
    def __init__(self, manager, ui_manager, context_menu):
        self.manager = manager
        self.ui_manager = ui_manager
        self.context_menu = context_menu
        self.global_script_manager = GlobalScriptManager()
        self.script_input_window = None
        self.create_script_menu()

    def create_script_menu(self):
        self.script_window = UIPanel(
            relative_rect=pygame.Rect(0, 0, 300, 300),
            manager=self.manager,
            visible=False,
            margins={'left': 5, 'right': 5, 'top': 5, 'bottom': 5},
            object_id=pygame_gui.core.ObjectID(object_id='#script_menu_panel', class_id='@script_menu')
        )

        available_scripts = [
                                'Execute Python Code',
                                'Load Script from File',
                                'Manage Scripts',
                                'Run Selected Script'
                            ] + list(self.global_script_manager.script_executor.scripts.keys())

        self.script_list = UISelectionList(
            relative_rect=pygame.Rect(0, 0, 290, 280),
            item_list=available_scripts,
            container=self.script_window,
            manager=self.manager,
            allow_double_clicks=False,
            object_id=pygame_gui.core.ObjectID(object_id='#script_selection_list', class_id='@script_menu')
        )

    def show_menu(self, position, clicked_object=None):
        self.global_script_manager.set_context_provider(lambda: {
            'ui_manager': self.ui_manager,
            'context_menu': self.context_menu,
            'clicked_object': clicked_object,
            'config': config,
            'PropertiesWindow': PropertiesWindow,
            'TextureWindow': TextureWindow,
            'physics_manager': getattr(self.ui_manager, 'physics_manager', None),
            'space': getattr(getattr(self.ui_manager, 'physics_manager', None), 'space', None)
        })
        x, y = position
        max_x, max_y = pygame.display.get_surface().get_size()
        rect = self.script_window.rect
        x = min(x, max_x - rect.width)
        y = min(y, max_y - rect.height)
        self.script_window.set_position((x, y))
        self.script_window.show()

        available_scripts = [
                                'Execute Python Code',
                                'Load Script from File',
                                'Manage Scripts',
                                'Run Selected Script'
                            ] + list(self.global_script_manager.script_executor.scripts.keys())

        self.script_list.set_item_list(available_scripts)

    def hide(self):
        self.script_window.hide()
        if self.script_input_window:
            self.script_input_window.hide()

    def process_event(self, event):
        if self.script_input_window:
            self.script_input_window.process_event(event)

        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.script_list:
                self.handle_script_selection(event.text)
                self.script_window.hide()

    def handle_script_selection(self, selection):
        if selection == 'Execute Python Code':
            self._open_code_execution_window()
        elif selection == 'Load Script from File':
            self._open_file_execution_window()
        elif selection == 'Manage Scripts':
            self._open_script_manager_window()
        elif selection == 'Run Selected Script':
            if self.context_menu.clicked_object:
                self.global_script_manager.execute_script('default_script')
        elif selection in self.global_script_manager.script_executor.scripts:
            self.global_script_manager.execute_script(selection)

    def _open_code_execution_window(self):
        if not self.script_input_window:
            self.script_input_window = ScriptInputWindow(
                self.manager,
                lambda: self.global_script_manager.context_provider()
            )
        self.script_input_window.show()

    def _open_file_execution_window(self):
        if not self.script_input_window:
            self.script_input_window = ScriptInputWindow(
                self.manager,
                lambda: self.global_script_manager.context_provider()
            )
        self.script_input_window.show()
        self.script_input_window._open_file_dialog()

    def _open_script_manager_window(self):
        pass
