import pygame
import pygame_gui
import os
from pygame_gui.elements import UITextEntryLine, UIButton, UILabel, UIWindow, UIImage
from tkinter import Tk
from tkinter.filedialog import askopenfilename


class TextureWindow:
    def __init__(self, manager, body, on_close_callback=None):
        self.manager = manager
        self.body = body
        self.on_close_callback = on_close_callback
        self.window = None
        self.texture_path_input = None
        self.preview_image = None
        self.apply_button = None
        self.cancel_button = None
        self.browse_button = None
        self.create_window()

    def create_window(self):
        rect = pygame.Rect(0, 0, 340, 320)
        rect.center = pygame.display.get_surface().get_rect().center
        self.window = UIWindow(
            rect=rect,
            manager=self.manager,
            window_display_title="Texture Path",
            object_id='#texture_window'
        )
        UILabel(
            relative_rect=pygame.Rect(10, 10, 320, 20),
            text='Texture path:',
            container=self.window,
            manager=self.manager
        )
        self.texture_path_input = UITextEntryLine(
            relative_rect=pygame.Rect(10, 35, 240, 30),
            manager=self.manager,
            container=self.window
        )
        self.browse_button = UIButton(
            relative_rect=pygame.Rect(260, 35, 70, 30),
            text='Browse',
            container=self.window,
            manager=self.manager
        )
        preview_rect = pygame.Rect(10, 75, 128, 128)
        self.preview_image = UIImage(
            relative_rect=preview_rect,
            image_surface=pygame.Surface((128, 128)),
            manager=self.manager,
            container=self.window
        )
        self.apply_button = UIButton(
            relative_rect=pygame.Rect(10, 220, 100, 30),
            text='Apply',
            container=self.window,
            manager=self.manager
        )
        self.cancel_button = UIButton(
            relative_rect=pygame.Rect(230, 220, 100, 30),
            text='Cancel',
            container=self.window,
            manager=self.manager
        )
        self.update_preview()

    def process_event(self, event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.browse_button:
                    self.open_file_dialog()
                elif event.ui_element == self.apply_button:
                    self.apply_texture()
                    self.close()
                elif event.ui_element == self.cancel_button:
                    self.close()

    def open_file_dialog(self):
        Tk().withdraw()
        initial_dir = os.path.dirname(self.texture_path_input.get_text().strip()) or os.path.expanduser("~")
        file_path = askopenfilename(
            title="Select texture file",
            initialdir=initial_dir,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tga *.dds"), ("All files", "*.*")]
        )
        if file_path:
            norm_path = os.path.normpath(file_path)
            self.texture_path_input.set_text(norm_path)
            self.update_preview()

    def update_preview(self):
        path = self.texture_path_input.get_text().strip()
        if not path or not os.path.isfile(path):
            self._set_preview_surface(pygame.Surface((128, 128)))
            return
        try:
            img = pygame.image.load(path).convert_alpha()
            w, h = img.get_size()
            scale = min(128 / w, 128 / h, 1.0)
            new_size = (int(w * scale), int(h * scale))
            scaled = pygame.transform.smoothscale(img, new_size)
            surface = pygame.Surface((128, 128), pygame.SRCALPHA)
            surface.fill((30, 30, 30, 255))
            x = (128 - new_size[0]) // 2
            y = (128 - new_size[1]) // 2
            surface.blit(scaled, (x, y))
            self._set_preview_surface(surface)
        except pygame.error:
            self._set_preview_surface(pygame.Surface((128, 128)))

    def _set_preview_surface(self, surface):
        self.preview_image.set_image(surface)

    def apply_texture(self):
        path = self.texture_path_input.get_text().strip()
        if path and os.path.isfile(path):
            self.body.texture_path = path

    def close(self):
        if self.window:
            self.window.kill()
            self.window = None
        if self.on_close_callback:
            self.on_close_callback()

    def update(self, time_delta):
        pass