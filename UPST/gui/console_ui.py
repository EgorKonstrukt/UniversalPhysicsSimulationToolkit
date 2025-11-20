import pygame
import pygame_gui
from UPST.config import config

class ConsoleUI:
    def __init__(self, manager, screen_width, screen_height):
        self.manager = manager
        self.console_window = pygame_gui.windows.UIConsoleWindow(pygame.Rect(screen_width-800, screen_height-300, 500, 310), manager=self.manager)

    def resize(self, screen_width, screen_height):
        self.console_window.set_position((screen_width-800, screen_height-300))