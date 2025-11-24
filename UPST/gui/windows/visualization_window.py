import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIPanel, UICheckBox, UITextEntryLine, UIHorizontalSlider, UILabel
from dataclasses import fields
from typing import Tuple
from UPST.config import config

class VisualizationWindow:
    def __init__(self, rect: pygame.Rect, manager: pygame_gui.UIManager, app=None):
        self.manager = manager
        self.app = app
        self.window = UIWindow(rect=rect, manager=manager, window_display_title="Physics Visualization")
        self.checkboxes = {}
        self.entries = {}
        self.sliders = {}
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
            label_width = int(col_width * 0.6)
            ctrl_width = int(col_width * 0.35)

            for f in group_fields:
                name, val = f.name, getattr(config.physics_debug, f.name)
                label_rect = pygame.Rect(5, y_offset, label_width, line_height)
                ctrl_rect = pygame.Rect(label_width + 5, y_offset, ctrl_width, line_height)

                if isinstance(val, bool):
                    cb = UICheckBox(pygame.Rect(ctrl_rect.left - 20, y_offset + 3, 20, 20), '', self.manager, panel)
                    cb.set_state(True) if val else cb.set_state(False)
                    self.checkboxes[name] = cb
                    UILabel(label_rect, name.replace('_', ' ').title(), self.manager, panel)
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    entry = UITextEntryLine(ctrl_rect, self.manager, panel)
                    entry.set_text(str(val))
                    self.entries[name] = entry
                    UILabel(label_rect, name.replace('_', ' ').title(), self.manager, panel)
                    if name in ('vector_scale', 'text_scale', 'energy_bar_height'):
                        slider_rect = pygame.Rect(ctrl_rect.left, y_offset + line_height + 2, ctrl_width, 20)
                        rng = (0.0, 1.0) if 'scale' in name else (0.0, 100.0)
                        slider = UIHorizontalSlider(slider_rect, val, rng, self.manager, panel)
                        self.sliders[name] = slider
                        y_offset += 24
                elif isinstance(val, Tuple) and len(val) == 3 and all(isinstance(c, int) for c in val):
                    entry = UITextEntryLine(ctrl_rect, self.manager, panel)
                    entry.set_text(','.join(map(str, val)))
                    self.entries[name] = entry
                    UILabel(label_rect, name.replace('_', ' ').title(), self.manager, panel)
                y_offset += line_height

    def _group_fields(self):
        groups = {}
        for f in fields(config.physics_debug):
            cat = self._categorize(f.name)
            groups.setdefault(cat, []).append(f)
        return groups

    def _categorize(self, name: str) -> str:
        if 'color' in name: return 'colors'
        if 'show_' in name: return 'visibility'
        if any(k in name for k in ('scale', 'length', 'height', 'samples', 'digits', 'window')): return 'scales_and_limits'
        if 'position' in name: return 'positions'
        return 'misc'

    def apply(self):
        print('Applying...')
        for n, cb in self.checkboxes.items():
            setattr(config.physics_debug, n, cb.get_state())
        for n, e in self.entries.items():
            t = e.get_text()
            if 'color' in n:
                try:
                    v = tuple(int(c.strip()) for c in t.split(','))
                    if len(v) == 3:
                        setattr(config.physics_debug, n, v)
                except Exception:
                    pass
            else:
                try:
                    orig = getattr(config.physics_debug, n)
                    setattr(config.physics_debug, n, type(orig)(t))
                except Exception:
                    pass
        for n, s in self.sliders.items():
            setattr(config.physics_debug, n, s.get_current_value())
        config.save()

    def process_event(self, event):
        if event.type == pygame_gui.UI_CHECK_BOX_CHECKED:
            if event.ui_element in self.checkboxes.values():
                self.apply()
        elif event.type == pygame_gui.UI_CHECK_BOX_UNCHECKED:
            if event.ui_element in self.checkboxes.values():
                self.apply()
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            self.apply()
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            self.apply()