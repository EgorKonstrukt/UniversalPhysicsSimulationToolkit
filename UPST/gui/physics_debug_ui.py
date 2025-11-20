import pygame
import pygame_gui
from UPST.config import config

class PhysicsDebugUI:
    def __init__(self, manager, screen_width):
        self.manager = manager
        self.physics_debug_window = pygame_gui.elements.UIWindow(pygame.Rect(screen_width-450,10,400,600), manager=self.manager, window_display_title="Physics Debug Settings")
        self.physics_debug_window.hide()
        self.toggle_all_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5,10,150,30), text="Toggle All Debug", container=self.physics_debug_window, manager=self.manager)
        self.clear_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5,45,150,30), text="Clear Debug History", container=self.physics_debug_window, manager=self.manager)
        self.debug_checkboxes = {}
        self.physics_debug_manager = None

    def set_debug_manager(self, debug_manager):
        self.physics_debug_manager = debug_manager

    def update_checkboxes(self):
        if not self.physics_debug_manager:
            return
        settings = config.physics_debug
        for attr_name, checkbox in self.debug_checkboxes.items():
            state = getattr(settings, attr_name, False)
            img_path = "sprites/gui/checkbox_true.png" if state else "sprites/gui/checkbox_false.png"
            checkbox.set_image(pygame.image.load(img_path))

    def resize(self, screen_width):
        self.physics_debug_window.set_position((screen_width-450,10))