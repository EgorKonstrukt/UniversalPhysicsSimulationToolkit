import pygame
import pygame_gui
import os
import pymunk
from pygame_gui.elements import UITextEntryLine, UIButton, UILabel, UIWindow, UIImage, UIPanel
from pygame_gui.windows import UIColourPickerDialog, UIFileDialog
from tkinter import Tk
from tkinter.filedialog import askopenfilename

class TextureWindow:
    def __init__(self, manager, body, on_close_callback=None):
        self.manager = manager
        self.body = body
        self.on_close_callback = on_close_callback
        self.window = None
        self.texture_path_input = None
        self.preview_container = None
        self.preview_image = None
        self.apply_button = None
        self.cancel_button = None
        self.browse_button = None
        self.color_button = None
        self.crop_rect = pygame.Rect(0, 0, 128, 128)
        self.dragging = False
        self.drag_offset = (0, 0)
        self.bg_color = pygame.Color(30, 30, 30)
        self.loaded_surface = None
        self.create_window()

    def create_window(self):
        rect = pygame.Rect(0, 0, 400, 420)
        rect.center = pygame.display.get_surface().get_rect().center
        self.window = UIWindow(
            rect=rect,
            manager=self.manager,
            window_display_title="Texture & Crop Editor",
            object_id='#texture_window'
        )
        UILabel(relative_rect=pygame.Rect(10, 10, 380, 20), text='Texture path:', container=self.window, manager=self.manager)
        self.texture_path_input = UITextEntryLine(relative_rect=pygame.Rect(10, 35, 270, 30), manager=self.manager, container=self.window)
        self.browse_button = UIButton(relative_rect=pygame.Rect(290, 35, 90, 30), text='Browse', container=self.window, manager=self.manager)
        self.color_button = UIButton(relative_rect=pygame.Rect(10, 70, 120, 30), text='Set BG Color', container=self.window, manager=self.manager)
        self.preview_container = UIPanel(relative_rect=pygame.Rect(10, 110, 128, 128), manager=self.manager, container=self.window, object_id='#preview_panel')
        self.preview_image = UIImage(relative_rect=pygame.Rect(0, 0, 128, 128), image_surface=pygame.Surface((128, 128)), manager=self.manager, container=self.preview_container)
        self.apply_button = UIButton(relative_rect=pygame.Rect(10, 280, 100, 30), text='Apply', container=self.window, manager=self.manager)
        self.cancel_button = UIButton(relative_rect=pygame.Rect(290, 280, 100, 30), text='Cancel', container=self.window, manager=self.manager)
        self.update_preview()

    def process_event(self, event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.browse_button:
                    self.open_file_dialog()
                elif event.ui_element == self.color_button:
                    UIColourPickerDialog(pygame.Rect(0, 0, 390, 300), self.manager, window_title="Pick Background", initial_colour=self.bg_color)
                elif event.ui_element == self.apply_button:
                    self.apply_texture()
                    self.close()
                elif event.ui_element == self.cancel_button:
                    self.close()
            elif event.user_type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
                self.bg_color = event.colour
                self.update_preview()
            elif event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                self.texture_path_input.set_text(event.text)
                self.update_preview()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            if self.preview_container.get_relative_rect().collidepoint(mouse_pos[0] - self.preview_container.rect.left, mouse_pos[1] - self.preview_container.rect.top):
                self.dragging = True
                self.drag_offset = (mouse_pos[0] - self.crop_rect.x - self.preview_container.rect.left, mouse_pos[1] - self.crop_rect.y - self.preview_container.rect.top)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            new_x = mouse_x - self.drag_offset[0] - self.preview_container.rect.left
            new_y = mouse_y - self.drag_offset[1] - self.preview_container.rect.top
            self.crop_rect.x = max(0, min(new_x, 128 - self.crop_rect.width))
            self.crop_rect.y = max(0, min(new_y, 128 - self.crop_rect.height))
            self.update_preview()

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

    def _get_first_shape(self):
        if hasattr(self.body, 'shape'):
            return self.body.shape
        if hasattr(self.body, 'shapes'):
            shapes = self.body.shapes
            if isinstance(shapes, dict):
                return next(iter(shapes.values()))
            elif hasattr(shapes, '__iter__'):
                return next(iter(shapes))
        raise ValueError("Body has no valid shape or shapes attribute")

    def _render_shape_overlay(self, surface_size, shape):
        surf = pygame.Surface(surface_size, pygame.SRCALPHA)
        center = (surface_size[0] // 2, surface_size[1] // 2)
        if isinstance(shape, pymunk.Circle):
            r = int(shape.radius * surface_size[0] / max(surface_size))
            pygame.draw.circle(surf, (255, 255, 255, 128), center, r, 1)
        elif isinstance(shape, pymunk.Poly):
            points = []
            for v in shape.get_vertices():
                x = center[0] + int(v.x * surface_size[0] / max(surface_size))
                y = center[1] + int(v.y * surface_size[1] / max(surface_size))
                points.append((x, y))
            if len(points) > 2:
                pygame.draw.polygon(surf, (255, 255, 255, 128), points, 1)
        return surf

    def update_preview(self):
        path = self.texture_path_input.get_text().strip()
        shape = self._get_first_shape()
        base = pygame.Surface((128, 128))
        base.fill(self.bg_color)
        if not path or not os.path.isfile(path):
            overlay = self._render_shape_overlay((128, 128), shape)
            base.blit(overlay, (0, 0))
            self._set_preview_surface(base)
            return
        try:
            img = pygame.image.load(path).convert_alpha()
            self.loaded_surface = img
            scaled = pygame.transform.smoothscale(img, (128, 128))
            base.blit(scaled, (0, 0))
            pygame.draw.rect(base, (255, 0, 0), self.crop_rect, 1)
            overlay = self._render_shape_overlay((128, 128), shape)
            base.blit(overlay, (0, 0))
            self._set_preview_surface(base)
        except (pygame.error, ValueError, OSError):
            fallback = pygame.Surface((128, 128))
            fallback.fill((50, 50, 50))
            overlay = self._render_shape_overlay((128, 128), shape)
            fallback.blit(overlay, (0, 0))
            self._set_preview_surface(fallback)

    def _set_preview_surface(self, surface):
        self.preview_image.set_image(surface)

    def apply_texture(self):
        path = self.texture_path_input.get_text().strip()
        if path and os.path.isfile(path) and self.loaded_surface:
            x_ratio = self.loaded_surface.get_width() / 128
            y_ratio = self.loaded_surface.get_height() / 128
            actual_crop = pygame.Rect(
                int(self.crop_rect.x * x_ratio),
                int(self.crop_rect.y * y_ratio),
                max(1, int(self.crop_rect.width * x_ratio)),
                max(1, int(self.crop_rect.height * y_ratio))
            )
            cropped = self.loaded_surface.subsurface(actual_crop.clamp(self.loaded_surface.get_rect()))
            output_path = path.rsplit('.', 1)[0] + '_cropped.png'
            pygame.image.save(cropped, output_path)
            self.body.texture_path = output_path

    def close(self):
        if self.window:
            self.window.kill()
            self.window = None
        if self.on_close_callback:
            self.on_close_callback()

    def update(self, time_delta):
        pass