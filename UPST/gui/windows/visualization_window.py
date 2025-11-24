import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIPanel, UICheckBox, UITextEntryLine, UIHorizontalSlider, UILabel, UIButton
from pygame_gui.windows import UIColourPickerDialog
from dataclasses import fields
from typing import Tuple, Any
from UPST.config import config

class VisualizationWindow:
    def __init__(self, rect: pygame.Rect, manager: pygame_gui.UIManager, app=None):
        self.manager = manager
        self.app = app
        self.window = UIWindow(rect=rect, manager=manager, window_display_title="Physics Visualization")
        self.checkboxes = {}
        self.entries = {}
        self.sliders = {}
        self.color_buttons = {}
        self.color_previews = {}
        self.pending_color_field = None
        self._build_ui()
    def _build_ui(self):
        groups = self._group_fields()
        col_count = 3
        col_width = (self.window.rect.width - 30) // col_count
        panel_height = self.window.rect.height - 60
        padding = 10
        for col_idx, (group_name, group_fields) in enumerate(groups.items()):
            col_x = padding + (col_idx % col_count) * col_width
            col_y = 40 + (col_idx // col_count) * (panel_height + padding)
            panel_rect = pygame.Rect(col_x, col_y, col_width - padding, panel_height)
            panel = UIPanel(relative_rect=panel_rect, manager=self.manager, container=self.window)
            UILabel(pygame.Rect(5, 3, panel_rect.width - 10, 22), group_name.replace('_', ' ').title(), self.manager, panel)
            y_offset = 28
            line_height = 26
            label_width = int(col_width * 0.5)
            preview_width = 20
            btn_width = int(col_width * 0.35 - preview_width - 5)
            for f in group_fields:
                name, val = f.name, getattr(config.physics_debug, f.name)
                label_rect = pygame.Rect(5, y_offset, label_width, line_height)
                preview_rect = pygame.Rect(label_width + 5, y_offset + 3, preview_width, preview_width)
                btn_rect = pygame.Rect(label_width + preview_width + 10, y_offset, btn_width, line_height)
                if isinstance(val, bool):
                    cb = UICheckBox(pygame.Rect(btn_rect.left - 20,
                                                y_offset + 3, 25, 25),
                                    '', self.manager, panel)
                    cb.set_state(bool(val))
                    self.checkboxes[name] = cb
                    UILabel(label_rect, name.replace('_', ' ').title(),
                            self.manager,
                            panel)
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    entry = UITextEntryLine(btn_rect, self.manager, panel)
                    entry.set_text(str(val))
                    self.entries[name] = entry
                    UILabel(label_rect, name.replace('_', ' ').title(), self.manager, panel)
                    if name in ('vector_scale', 'text_scale', 'energy_bar_height'):
                        slider_rect = pygame.Rect(btn_rect.left, y_offset + line_height + 2, btn_width, 20)
                        rng = (0.0, 3.0) if 'scale' in name else (0.0, 100.0)
                        slider = UIHorizontalSlider(slider_rect, val, rng, self.manager, panel)
                        self.sliders[name] = slider
                        y_offset += 24
                elif self._is_color_value(val):
                    preview_surface = pygame.Surface((preview_width, preview_width))
                    preview_surface.fill(val)
                    preview_image = pygame_gui.elements.UIImage(preview_rect, preview_surface, self.manager, container=panel)
                    self.color_previews[name] = preview_image
                    btn = UIButton(btn_rect, "Pick", self.manager, container=panel)
                    self.color_buttons[btn] = name
                    UILabel(label_rect, name.replace('_', ' ').title(), self.manager, panel)
                y_offset += line_height
    def _is_color_value(self, val: Any) -> bool:
        if isinstance(val, (tuple, list)):
            if len(val) == 3:
                return all(isinstance(c, int) and 0 <= c <= 255 for c in val)
        return False
    def _group_fields(self):
        groups = {}
        for f in fields(config.physics_debug):
            cat = self._categorize(f.name)
            groups.setdefault(cat, []).append(f)
        return groups
    def _categorize(self, name: str) -> str:
        if 'color' in name: return 'colors'
        if 'show_' in name: return 'visibility'
        if any(k in name for k in ('scale', 'length', 'height', 'samples', 'digits', 'window', 'smoothing')): return 'scales_and_limits'
        if 'position' in name: return 'positions'
        return 'misc'
    def apply(self):
        for n, cb in self.checkboxes.items():
            setattr(config.physics_debug, n, cb.get_state())
        for n, e in self.entries.items():
            t = e.get_text()
            try:
                orig = getattr(config.physics_debug, n)
                if self._is_color_value(orig):
                    v = tuple(int(c.strip()) for c in t.split(','))
                    if len(v) == 3 and all(0 <= c <= 255 for c in v):
                        setattr(config.physics_debug, n, v)
                        self._update_color_preview(n, v)
                else:
                    setattr(config.physics_debug, n, type(orig)(t))
            except Exception:
                pass
        for n, s in self.sliders.items():
            val = s.get_current_value()
            setattr(config.physics_debug, n, val)
            if n in self.entries:
                self.entries[n].set_text(str(val))
        config.save()
    def _update_color_preview(self, name: str, color: Tuple[int, int, int]):
        if name in self.color_previews:
            preview = self.color_previews[name]
            preview.image = pygame.Surface((preview.rect.width, preview.rect.height))
            preview.image.fill(color)
            preview.rebuild()
    def process_event(self, event):
        if event.type in (pygame_gui.UI_CHECK_BOX_CHECKED, pygame_gui.UI_CHECK_BOX_UNCHECKED):
            if event.ui_element in self.checkboxes.values():
                self.apply()
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element in self.entries.values():
                self.apply()
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element in self.sliders.values():
                self.apply()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.color_buttons:
                self._open_color_picker(event.ui_element)
        elif event.type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
            if self.pending_color_field:
                new_color = (event.colour.r, event.colour.g, event.colour.b)
                setattr(config.physics_debug, self.pending_color_field, new_color)
                self._update_color_preview(self.pending_color_field, new_color)
                config.save()
                self.pending_color_field = None
    def _open_color_picker(self, btn):
        self.pending_color_field = self.color_buttons[btn]
        current_val = getattr(config.physics_debug, self.pending_color_field)
        UIColourPickerDialog(
            pygame.Rect(100, 100, 300, 400),
            self.manager,
            window_title=f"Select {self.pending_color_field.replace('_', ' ').title()}",
            initial_colour=pygame.Color(*current_val)
        )