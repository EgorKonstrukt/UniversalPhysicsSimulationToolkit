import pygame
import pygame_gui
from UPST.config import config

class SettingsUI:
    def __init__(self, manager, screen_height):
        self.manager = manager
        self.settings_window = pygame_gui.elements.UIWindow(pygame.Rect(200, screen_height-300, 400, 200), manager=self.manager, window_display_title="Settings")
        self._create_debug_checkboxes()

    def _create_debug_checkboxes(self):
        labels = [("Draw collision points",10),("Draw constraints",30),("Draw body outlines",60),("Draw center of mass",90)]
        for text, y in labels:
            btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5,y,20,20), text="", container=self.settings_window, tool_tip_text=text, manager=self.manager)
            pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5,y,200,20), text=text.replace("Draw ",""), container=self.settings_window, manager=self.manager)

    def resize(self, screen_height):
        self.settings_window.set_position((200, screen_height-300))