import pygame
import pygame_gui
import os
import pymunk
import json
import math
import time
import threading
from pygame_gui.elements import UITextEntryLine, UIButton, UILabel, UIWindow, UIImage, UIPanel, UIHorizontalSlider, \
    UIDropDownMenu, UISelectionList
from pygame_gui.windows import UIColourPickerDialog, UIFileDialog
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib

from UPST.modules.texture_processor import TextureState, TextureProcessor

from UPST.modules.undo_redo_manager import get_undo_redo

class FilterMode(Enum):
    NEAREST = 0
    BILINEAR = 1
    TRILINEAR = 2

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
        self.rotation_slider = None
        self.scale_slider = None
        self.rotation_label = None
        self.scale_label = None
        self.mirror_x_btn = None
        self.mirror_y_btn = None
        self.crop_rect = pygame.Rect(0, 0, 128, 128)
        self.dragging = False
        self.drag_offset = (0, 0)
        self.bg_color = pygame.Color(30, 30, 30)
        self.loaded_surface = None
        self.rotation_angle = 0
        self.scale_factor = 1.0
        self.mirror_x = False
        self.mirror_y = False
        self.filter_mode = FilterMode.BILINEAR
        self.tiling_mode = 'clamp'
        self.blend_mode = 'normal'
        self.preview_quality = 1.0
        self.config_path = os.path.join(os.path.dirname(__file__), 'texture_config.json')
        self.undo_stack: List[TextureState] = []
        self.max_undo_steps = 10
        self.active_layer = 0
        self.layers = [{'name': 'Base', 'visible': True, 'opacity': 255}]
        self.crop_mode = False
        self.last_save_time = 0
        self.auto_save_interval = 5.0
        self.processor = TextureProcessor()
        self.batch_mode = False
        self.batch_paths: List[str] = []
        self.batch_index = 0
        self.preview_thread: Optional[threading.Thread] = None
        self.preview_lock = threading.Lock()
        self.preview_surface: Optional[pygame.Surface] = None
        self.preview_dirty = True
        self.load_config()
        self.create_window()
        self.load_body_texture_state()
        self.undo_redo = get_undo_redo()

    def load_body_texture_state(self):
        """Initialize editor state from the body's current texture properties."""
        if hasattr(self.body, 'texture_path') and self.body.texture_path:
            self.texture_path_input.set_text(self.body.texture_path)
        if hasattr(self.body, 'texture_rotation'):
            self.rotation_angle = self.body.texture_rotation
            self.rotation_slider.set_current_value(self.rotation_angle)
            self.rotation_label.set_text(f'Rotation: {self.rotation_angle}°')
        if hasattr(self.body, 'texture_scale'):
            self.scale_factor = self.body.texture_scale
            self.scale_slider.set_current_value(self.scale_factor)
            self.scale_label.set_text(f'Scale: {self.scale_factor:.2f}x')
        if hasattr(self.body, 'texture_mirror_x'):
            self.mirror_x = self.body.texture_mirror_x
        if hasattr(self.body, 'texture_mirror_y'):
            self.mirror_y = self.body.texture_mirror_y
        # Note: filter_mode, tiling_mode, blend_mode are editor-only for now
        self.update_preview()

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                cfg = json.load(f)
                self.bg_color = pygame.Color(cfg.get('bg_color', [30, 30, 30]))
                self.rotation_angle = cfg.get('rotation', 0)
                self.scale_factor = cfg.get('scale', 1.0)
                self.filter_mode = FilterMode(cfg.get('filter_mode', FilterMode.BILINEAR.value))
                self.tiling_mode = cfg.get('tiling_mode', 'clamp')
                self.blend_mode = cfg.get('blend_mode', 'normal')
                self.preview_quality = cfg.get('preview_quality', 1.0)
        except FileNotFoundError:
            pass

    def save_config(self):
        cfg = {
            'bg_color': list(self.bg_color),
            'rotation': self.rotation_angle,
            'scale': self.scale_factor,
            'filter_mode': self.filter_mode.value,
            'tiling_mode': self.tiling_mode,
            'blend_mode': self.blend_mode,
            'preview_quality': self.preview_quality
        }
        with open(self.config_path, 'w') as f:
            json.dump(cfg, f)

    def create_window(self):
        surf = pygame.display.get_surface()
        center = surf.get_rect().center
        rect = pygame.Rect(0, 0, 800, 700)
        rect.center = center
        self.window = UIWindow(
            rect=rect, manager=self.manager, window_display_title="Advanced Texture Editor",
            object_id='#texture_window'
        )
        UILabel(relative_rect=pygame.Rect(10, 10, 480, 20), text='Texture path:', container=self.window, manager=self.manager)
        self.texture_path_input = UITextEntryLine(relative_rect=pygame.Rect(10, 35, 470, 30), manager=self.manager, container=self.window)
        self.browse_button = UIButton(relative_rect=pygame.Rect(500, 35, 90, 30), text='Browse', container=self.window, manager=self.manager)
        batch_btn = UIButton(relative_rect=pygame.Rect(600, 35, 90, 30), text='Batch', container=self.window, manager=self.manager)
        self.color_button = UIButton(relative_rect=pygame.Rect(10, 70, 120, 30), text='Set BG Color', container=self.window, manager=self.manager)
        self.rotation_label = UILabel(relative_rect=pygame.Rect(10, 105, 100, 20), text=f'Rotation: {self.rotation_angle}°', container=self.window, manager=self.manager)
        self.rotation_slider = UIHorizontalSlider(relative_rect=pygame.Rect(10, 130, 200, 20), start_value=self.rotation_angle, value_range=(-180, 180), manager=self.manager, container=self.window)
        self.scale_label = UILabel(relative_rect=pygame.Rect(10, 155, 100, 20), text=f'Scale: {self.scale_factor:.2f}x', container=self.window, manager=self.manager)
        self.scale_slider = UIHorizontalSlider(relative_rect=pygame.Rect(10, 180, 200, 20), start_value=self.scale_factor, value_range=(0.1, 3.0), manager=self.manager, container=self.window)
        self.mirror_x_btn = UIButton(relative_rect=pygame.Rect(220, 130, 60, 20), text='Mirror X', container=self.window, manager=self.manager)
        self.mirror_y_btn = UIButton(relative_rect=pygame.Rect(220, 155, 60, 20), text='Mirror Y', container=self.window, manager=self.manager)
        crop_btn = UIButton(relative_rect=pygame.Rect(220, 180, 60, 20), text='Crop', container=self.window, manager=self.manager)
        self.preview_container = UIPanel(relative_rect=pygame.Rect(10, 210, 256, 256), manager=self.manager, container=self.window, object_id='#preview_panel')
        self.preview_image = UIImage(relative_rect=pygame.Rect(0, 0, 256, 256), image_surface=pygame.Surface((256, 256)), manager=self.manager, container=self.preview_container)
        filter_dropdown = UIDropDownMenu(options_list=[e.name for e in FilterMode], starting_option=self.filter_mode.name, relative_rect=pygame.Rect(10, 480, 150, 20), manager=self.manager, container=self.window)
        tiling_dropdown = UIDropDownMenu(options_list=['clamp', 'repeat', 'mirror'], starting_option=self.tiling_mode, relative_rect=pygame.Rect(170, 480, 100, 20), manager=self.manager, container=self.window)
        blend_dropdown = UIDropDownMenu(options_list=['normal', 'multiply', 'add', 'subtract'], starting_option=self.blend_mode, relative_rect=pygame.Rect(280, 480, 100, 20), manager=self.manager, container=self.window)
        undo_btn = UIButton(relative_rect=pygame.Rect(10, 510, 80, 30), text='Undo', container=self.window, manager=self.manager)
        reset_btn = UIButton(relative_rect=pygame.Rect(100, 510, 80, 30), text='Reset', container=self.window, manager=self.manager)
        auto_save_btn = UIButton(relative_rect=pygame.Rect(190, 510, 80, 30), text='Auto-Save', container=self.window, manager=self.manager)
        self.apply_button = UIButton(relative_rect=pygame.Rect(10, 550, 100, 30), text='Apply', container=self.window, manager=self.manager)
        self.cancel_button = UIButton(relative_rect=pygame.Rect(390, 550, 100, 30), text='Cancel', container=self.window, manager=self.manager)
        next_btn = UIButton(relative_rect=pygame.Rect(500, 550, 90, 30), text='Next', container=self.window, manager=self.manager)
        prev_btn = UIButton(relative_rect=pygame.Rect(600, 550, 90, 30), text='Prev', container=self.window, manager=self.manager)
        self.update_preview()

    def process_event(self, event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.browse_button:
                    self.open_file_dialog()
                elif event.ui_element.text == 'Batch':
                    self.open_batch_dialog()
                elif event.ui_element == self.color_button:
                    UIColourPickerDialog(pygame.Rect(0, 0, 390, 300), self.manager, window_title="Pick Background", initial_colour=self.bg_color)
                elif event.ui_element == self.apply_button:
                    self.apply_texture()
                    if not self.batch_mode:
                        self.close()
                    else:
                        self.next_batch_item()
                elif event.ui_element == self.cancel_button:
                    self.close()
                elif event.ui_element == self.mirror_x_btn:
                    self.mirror_x = not self.mirror_x
                    self.push_state_to_undo()
                    self.update_preview()
                elif event.ui_element == self.mirror_y_btn:
                    self.mirror_y = not self.mirror_y
                    self.push_state_to_undo()
                    self.update_preview()
                elif event.ui_element.text == 'Crop':
                    self.crop_mode = not self.crop_mode
                elif event.ui_element.text == 'Undo':
                    self.undo()
                elif event.ui_element.text == 'Reset':
                    self.reset_transforms()
                elif event.ui_element.text == 'Auto-Save':
                    self.auto_save_interval = 5.0 if self.auto_save_interval == 0 else 0
                elif event.ui_element.text == 'Next':
                    self.next_batch_item()
                elif event.ui_element.text == 'Prev':
                    self.prev_batch_item()
            elif event.user_type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
                self.bg_color = event.colour
                self.update_preview()
            elif event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                self.texture_path_input.set_text(event.text)
                self.update_preview()
            elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.rotation_slider:
                    self.rotation_angle = int(event.value)
                    self.rotation_label.set_text(f'Rotation: {self.rotation_angle}°')
                    self.push_state_to_undo()
                elif event.ui_element == self.scale_slider:
                    self.scale_factor = round(event.value, 2)
                    self.scale_label.set_text(f'Scale: {self.scale_factor}x')
                    self.push_state_to_undo()
                self.update_preview()
            elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                if event.text == 'NEAREST':
                    self.filter_mode = FilterMode.NEAREST
                elif event.text == 'BILINEAR':
                    self.filter_mode = FilterMode.BILINEAR
                elif event.text == 'TRILINEAR':
                    self.filter_mode = FilterMode.TRILINEAR
                elif event.text in ['clamp', 'repeat', 'mirror']:
                    self.tiling_mode = event.text
                elif event.text in ['normal', 'multiply', 'add', 'subtract']:
                    self.blend_mode = event.text
                self.push_state_to_undo()
                self.update_preview()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = pygame.mouse.get_pos()
            if self.preview_container.get_abs_rect().collidepoint(*mp):
                pr = self.preview_container.get_abs_rect()
                rel_x = mp[0] - pr.left
                rel_y = mp[1] - pr.top
                if self.crop_rect.collidepoint(rel_x, rel_y) and self.crop_mode:
                    self.dragging = True
                    self.drag_offset = (mp[0] - (self.preview_container.rect.left + self.crop_rect.x), mp[1] - (self.preview_container.rect.top + self.crop_rect.y))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx, my = pygame.mouse.get_pos()
            nx = mx - self.drag_offset[0] - self.preview_container.rect.left
            ny = my - self.drag_offset[1] - self.preview_container.rect.top
            self.crop_rect.x = max(0, min(nx, 256 - self.crop_rect.width))
            self.crop_rect.y = max(0, min(ny, 256 - self.crop_rect.height))
            self.update_preview()

    def push_state_to_undo(self):
        state = TextureState(
            rotation=self.rotation_angle,
            scale=self.scale_factor,
            mirror_x=self.mirror_x,
            mirror_y=self.mirror_y,
            filter_mode=self.filter_mode,
            tiling_mode=self.tiling_mode,
            blend_mode=self.blend_mode,
            crop_rect=(self.crop_rect.x, self.crop_rect.y, self.crop_rect.width, self.crop_rect.height),
            bg_color=(self.bg_color.r, self.bg_color.g, self.bg_color.b)
        )
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

    def open_file_dialog(self):
        Tk().withdraw()
        initial_dir = os.path.dirname(self.texture_path_input.get_text().strip()) or os.path.expanduser("~")
        file_path = askopenfilename(
            title="Select texture file",
            initialdir=initial_dir,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tga *.dds *.webp"), ("All files", "*.*")]
        )
        if file_path:
            norm_path = os.path.normpath(file_path)
            self.texture_path_input.set_text(norm_path)
            self.update_preview()

    def open_batch_dialog(self):
        Tk().withdraw()
        initial_dir = os.path.dirname(self.texture_path_input.get_text().strip()) or os.path.expanduser("~")
        file_paths = askopenfilename(
            title="Select texture files",
            initialdir=initial_dir,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tga *.dds *.webp"), ("All files", "*.*")],
            multiple=True
        )
        if file_paths:
            self.batch_paths = [os.path.normpath(p) for p in file_paths]
            self.batch_index = 0
            self.batch_mode = True
            if self.batch_paths:
                self.texture_path_input.set_text(self.batch_paths[0])
                self.update_preview()

    def next_batch_item(self):
        if self.batch_mode and self.batch_paths:
            self.batch_index = (self.batch_index + 1) % len(self.batch_paths)
            self.texture_path_input.set_text(self.batch_paths[self.batch_index])
            self.update_preview()

    def prev_batch_item(self):
        if self.batch_mode and self.batch_paths:
            self.batch_index = (self.batch_index - 1) % len(self.batch_paths)
            self.texture_path_input.set_text(self.batch_paths[self.batch_index])
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
        elif isinstance(shape, pymunk.Segment):
            a = (center[0] + int(shape.a.x * surface_size[0] / max(surface_size)), center[1] + int(shape.a.y * surface_size[1] / max(surface_size)))
            b = (center[0] + int(shape.b.x * surface_size[0] / max(surface_size)), center[1] + int(shape.b.y * surface_size[1] / max(surface_size)))
            pygame.draw.line(surf, (255, 255, 255, 128), a, b, 1)
        return surf

    def _async_update_preview(self):
        path = self.texture_path_input.get_text().strip()
        shape = self._get_first_shape()
        base = pygame.Surface((256, 256))
        base.fill(self.bg_color)
        if not path or not os.path.isfile(path):
            overlay = self._render_shape_overlay((256, 256), shape)
            base.blit(overlay, (0, 0))
            with self.preview_lock:
                self.preview_surface = base
                self.preview_dirty = False
            return
        try:
            state = TextureState(
                rotation=self.rotation_angle,
                scale=self.scale_factor,
                mirror_x=self.mirror_x,
                mirror_y=self.mirror_y,
                filter_mode=self.filter_mode,
                tiling_mode=self.tiling_mode,
                blend_mode=self.blend_mode,
                crop_rect=(self.crop_rect.x, self.crop_rect.y, self.crop_rect.width, self.crop_rect.height),
                bg_color=(self.bg_color.r, self.bg_color.g, self.bg_color.b)
            )
            processed = self.processor.process_texture(path, state, (256, 256))
            crop_pos = ((256 - processed.get_width()) // 2, (256 - processed.get_height()) // 2)
            base.blit(processed, crop_pos)
            pygame.draw.rect(base, (255, 0, 0), self.crop_rect, 1)
            overlay = self._render_shape_overlay((256, 256), shape)
            base.blit(overlay, (0, 0))
            with self.preview_lock:
                self.preview_surface = base
                self.preview_dirty = False
        except (pygame.error, ValueError, OSError):
            fallback = pygame.Surface((256, 256))
            fallback.fill((50, 50, 50))
            overlay = self._render_shape_overlay((256, 256), shape)
            fallback.blit(overlay, (0, 0))
            with self.preview_lock:
                self.preview_surface = fallback
                self.preview_dirty = False

    def update_preview(self):
        if self.preview_thread and self.preview_thread.is_alive():
            return
        self.preview_dirty = True
        path = self.texture_path_input.get_text().strip()
        if path and os.path.isfile(path):
            try:
                self.loaded_surface = pygame.image.load(path).convert_alpha()
            except (pygame.error, OSError):
                self.loaded_surface = None
        else:
            self.loaded_surface = None
        self.preview_thread = threading.Thread(target=self._async_update_preview)
        self.preview_thread.daemon = True
        self.preview_thread.start()

    def _set_preview_surface(self, surface):
        self.preview_image.set_image(surface)

    def apply_texture(self):
        path = self.texture_path_input.get_text().strip()
        if not path or not os.path.isfile(path) or not self.loaded_surface:
            return
        try:
            shape = self._get_first_shape()
            if isinstance(shape, pymunk.Circle):
                target_size = (int(2 * shape.radius), int(2 * shape.radius))
            elif isinstance(shape, (pymunk.Poly, pymunk.Segment)):
                bb = shape.bb
                target_size = (int(bb.right - bb.left), int(bb.top - bb.bottom))
            else:
                target_size = (256, 256)
        except (ValueError, AttributeError):
            target_size = (256, 256)
        state = TextureState(
            rotation=self.rotation_angle,
            scale=self.scale_factor,
            mirror_x=self.mirror_x,
            mirror_y=self.mirror_y,
            filter_mode=self.filter_mode,
            tiling_mode=self.tiling_mode,
            blend_mode=self.blend_mode,
            crop_rect=(0, 0, self.loaded_surface.get_width(), self.loaded_surface.get_height()), # Ignore crop for apply
            bg_color=(self.bg_color.r, self.bg_color.g, self.bg_color.b)
        )

        try:
            processed_surface = self.processor.process_texture(path, state, target_size)
            if processed_surface.get_bitsize() != 32:
                processed_surface = processed_surface.convert_alpha()
            actual_size = processed_surface.get_size()
            raw_bytes = pygame.image.tobytes(processed_surface, "RGBA")
            self.body.texture_bytes = raw_bytes
            self.body.texture_size = actual_size
            self.body.texture_bytes = raw_bytes
            self.body.texture_size = actual_size
            self.body.texture_path = path
            self.body.texture_rotation = self.rotation_angle
            self.body.texture_scale = self.scale_factor
            self.body.texture_mirror_x = self.mirror_x
            self.body.texture_mirror_y = self.mirror_y
            self.body.stretch_texture = (self.tiling_mode != 'clamp')
            self.save_config()
            self.last_save_time = time.time()
            self.undo_redo.take_snapshot()
        except Exception as e:
            print(f"Texture apply error: {e}")



    def undo(self):
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.rotation_angle = state.rotation
            self.scale_factor = state.scale
            self.mirror_x = state.mirror_x
            self.mirror_y = state.mirror_y
            self.filter_mode = state.filter_mode
            self.tiling_mode = state.tiling_mode
            self.blend_mode = state.blend_mode
            self.crop_rect = pygame.Rect(*state.crop_rect)
            self.bg_color = pygame.Color(*state.bg_color)
            self.rotation_slider.set_current_value(self.rotation_angle)
            self.scale_slider.set_current_value(self.scale_factor)
            self.rotation_label.set_text(f'Rotation: {self.rotation_angle}°')
            self.scale_label.set_text(f'Scale: {self.scale_factor}x')
            self.update_preview()

    def reset_transforms(self):
        self.rotation_angle = 0
        self.scale_factor = 1.0
        self.mirror_x = False
        self.mirror_y = False
        self.crop_rect = pygame.Rect(0, 0, 128, 128)
        self.rotation_slider.set_current_value(0)
        self.scale_slider.set_current_value(1.0)
        self.rotation_label.set_text(f'Rotation: 0°')
        self.scale_label.set_text(f'Scale: 1.0x')
        self.update_preview()

    def close(self):
        if self.window:
            self.window.kill()
            self.window = None
        if self.on_close_callback:
            self.on_close_callback()

    def update(self, time_delta):
        if self.auto_save_interval > 0 and time.time() - self.last_save_time > self.auto_save_interval:
            self.apply_texture()
        if not self.preview_dirty:
            with self.preview_lock:
                if self.preview_surface:
                    self._set_preview_surface(self.preview_surface)
                    self.preview_surface = None
            self.preview_dirty = True