import pygame
import pygame_gui
from pygame_gui.elements import UITextEntryLine, UIButton, UILabel, UIPanel


class TextureWindow:
    def __init__(self, manager, body, on_close_callback=None):
        self.manager = manager
        self.body = body
        self.on_close_callback = on_close_callback
        self.window = None
        self.texture_path_input = None
        self.apply_button = None
        self.cancel_button = None
        self.create_window()

    def create_window(self):
        rect = pygame.Rect(0, 0, 320, 120)
        rect.center = pygame.display.get_surface().get_rect().center
        self.window = UIPanel(
            relative_rect=rect,
            manager=self.manager,
            object_id='#texture_window'
        )
        UILabel(
            relative_rect=pygame.Rect(10, 10, 300, 20),
            text='Texture path:',
            container=self.window,
            manager=self.manager
        )
        self.texture_path_input = UITextEntryLine(
            relative_rect=pygame.Rect(10, 35, 300, 30),
            manager=self.manager,
            container=self.window
        )
        self.apply_button = UIButton(
            relative_rect=pygame.Rect(10, 75, 100, 30),
            text='Apply',
            container=self.window,
            manager=self.manager
        )
        self.cancel_button = UIButton(
            relative_rect=pygame.Rect(210, 75, 100, 30),
            text='Cancel',
            container=self.window,
            manager=self.manager
        )

    def process_event(self, event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.apply_button:
                    self.apply_texture()
                    self.close()
                elif event.ui_element == self.cancel_button:
                    self.close()

    def apply_texture(self):
        path = self.texture_path_input.get_text().strip()
        if path:
            self.body.texture_path = path

    def close(self):
        if self.window:
            self.window.kill()
            self.window = None
        if self.on_close_callback:
            self.on_close_callback()

    def update(self, time_delta):
        pass
