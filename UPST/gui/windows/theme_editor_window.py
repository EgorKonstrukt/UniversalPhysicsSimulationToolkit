import json
import os
import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UITextEntryLine, UIButton, UIDropDownMenu, UILabel, UIPanel
from pygame_gui.windows import UIColourPickerDialog
import re


def parse_gradient(value: str):
    """Преобразует строку вида 'rgba(...),rgba(...),270' → (color1, color2, angle)"""
    if not isinstance(value, str) or value.count(',') < 2:
        return None
    parts = [p.strip() for p in value.split(',')]
    if len(parts) < 3:
        return None
    try:
        color1_str = ','.join(parts[:4])  # может быть 'rgba(56,56,56,201)'
        color2_str = ','.join(parts[4:8]) if len(parts) >= 8 else parts[4] if len(parts) > 4 else parts[1]
        angle_str = parts[-1]

        def parse_color(cs):
            if cs.startswith('rgba('):
                nums = re.findall(r'\d+', cs)
                if len(nums) >= 4:
                    return pygame.Color(int(nums[0]), int(nums[1]), int(nums[2]))
            elif cs.startswith('#'):
                return pygame.Color(cs)
            return pygame.Color(128, 128, 128)

        c1 = parse_color(color1_str)
        c2 = parse_color(color2_str)
        angle = int(angle_str)
        return c1, c2, angle
    except Exception:
        return None


def format_gradient(c1: pygame.Color, c2: pygame.Color, angle: int) -> str:
    return f"rgba({c1.r},{c1.g},{c1.b},{c1.a}),rgba({c2.r},{c2.g},{c2.b},{c2.a}),{angle}"

class ThemeEditorWindow(UIWindow):
    def __init__(self, rect, manager, theme_path='theme.json', ui_manager_ref=None):
        super().__init__(rect, manager, window_display_title='Theme Editor', object_id='#theme_editor_window')
        self.theme_path = theme_path
        self.ui_manager_ref = ui_manager_ref
        self.original_theme = self._load_theme()
        self.current_theme = json.loads(json.dumps(self.original_theme))  # deep copy
        self.active_picker = None
        self.picker_target = None  # (section, group, key)
        self.controls = {}
        self._build_ui()

    def _load_theme(self):
        with open(self.theme_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_ui(self):
        container = self
        w, h = container.get_container().get_size()
        scrollable_panel = UIPanel(
            relative_rect=pygame.Rect(0, 0, w - 30, h - 60),
            manager=self.ui_manager,
            container=container,
            margins={'left': 5, 'right': 5, 'top': 5, 'bottom': 5}
        )
        y_offset = 0
        col_width = (w - 40) // 3
        row_height = 30
        padding = 5

        def place_control(ctrl, x, y):
            ctrl.relative_rect.x = x
            ctrl.relative_rect.y = y
            ctrl.relative_rect.width = col_width - padding
            ctrl.rebuild()

        sections = list(self.current_theme.keys())
        for i, section in enumerate(sections):
            safe_section_id = section.replace('.', '_').replace(' ', '_')
            col = i % 3
            row = i // 3
            x = col * col_width
            y = row * (row_height + padding)
            label = UILabel(
                relative_rect=pygame.Rect(x, y, col_width, row_height),
                text=f"[{section}]",
                manager=self.ui_manager,
                container=scrollable_panel,
                object_id='#section_label'
            )
            btn = UIButton(
                relative_rect=pygame.Rect(x, y + row_height, col_width, row_height),
                text='Edit',
                manager=self.ui_manager,
                container=scrollable_panel,
                object_id=f'#edit_{safe_section_id}'
            )
            btn.original_section_name = section
            self.controls[section] = (label, btn)
            y_offset = max(y_offset, y + row_height * 2 + padding)

        actions_y = y_offset + 20
        self.apply_btn = UIButton(
            relative_rect=pygame.Rect(w//2 - 100, actions_y, 100, 30),
            text='Apply',
            manager=self.ui_manager,
            container=container
        )
        self.save_btn = UIButton(
            relative_rect=pygame.Rect(w//2 + 5, actions_y, 100, 30),
            text='Save',
            manager=self.ui_manager,
            container=container
        )
        scrollable_panel.set_dimensions((w - 30, min(h - 60, y_offset + 60)))


    def _open_section_editor(self, section_name):
        section_data = self.current_theme[section_name]
        sub_window_rect = pygame.Rect(150, 100, 650, 600)
        sub_window = UIWindow(sub_window_rect, self.ui_manager, window_display_title=f'Edit: {section_name}')
        panel = UIPanel(
            relative_rect=pygame.Rect(5, 5, 640, 560),
            manager=self.ui_manager,
            container=sub_window
        )
        y = 10
        row_h = 34
        for group_key, group_vals in section_data.items():
            if not isinstance(group_vals, dict):
                continue
            UILabel(
                relative_rect=pygame.Rect(10, y, 120, row_h),
                text=f"{group_key}:", manager=self.ui_manager, container=panel
            )
            y += row_h
            for param_key, param_val in group_vals.items():
                if group_key == 'colours':
                    grad = parse_gradient(param_val)
                    if grad:
                        c1, c2, angle = grad
                        btn1 = UIButton(
                            relative_rect=pygame.Rect(130, y, 100, row_h),
                            text='Color 1',
                            manager=self.ui_manager,
                            container=panel,
                            object_id='#theme_grad_color'
                        )
                        btn1.theme_section = section_name
                        btn1.theme_group = group_key
                        btn1.theme_param = param_key
                        btn1.gradient_index = 0
                        btn1.original_value = param_val

                        btn2 = UIButton(
                            relative_rect=pygame.Rect(240, y, 100, row_h),
                            text='Color 2',
                            manager=self.ui_manager,
                            container=panel,
                            object_id='#theme_grad_color'
                        )
                        btn2.theme_section = section_name
                        btn2.theme_group = group_key
                        btn2.theme_param = param_key
                        btn2.gradient_index = 1
                        btn2.original_value = param_val

                        UILabel(
                            relative_rect=pygame.Rect(350, y, 200, row_h),
                            text=f"Angle: {angle}°",
                            manager=self.ui_manager,
                            container=panel
                        )
                    else:
                        btn = UIButton(
                            relative_rect=pygame.Rect(130, y, 120, row_h),
                            text='Pick Color',
                            manager=self.ui_manager,
                            container=panel,
                            object_id='#theme_color_picker'
                        )
                        btn.theme_section = section_name
                        btn.theme_group = group_key
                        btn.theme_param = param_key
                        btn.is_gradient = False
                        btn.original_value = param_val
                        UILabel(
                            relative_rect=pygame.Rect(260, y, 350, row_h),
                            text=str(param_val)[:40],
                            manager=self.ui_manager,
                            container=panel
                        )
                else:
                    entry = UITextEntryLine(
                        relative_rect=pygame.Rect(130, y, 480, row_h),
                        initial_text=str(param_val),
                        manager=self.ui_manager,
                        container=panel
                    )
                    entry.theme_section = section_name
                    entry.theme_group = group_key
                    entry.theme_param = param_key
                y += row_h + 5
                if y > 500:
                    break
        close_btn = UIButton(
            relative_rect=pygame.Rect(550, 565, 80, 25),
            text='Close',
            manager=self.ui_manager,
            container=sub_window
        )
        close_btn.sub_window = sub_window

    def _attach_color_handler(self, btn):
        def handler():
            current_val = self.current_theme[btn.section][btn.group][btn.param]
            if current_val.startswith('rgba') or current_val.startswith('#'):
                try:
                    if current_val.startswith('rgba'):
                        comps = current_val.split(',')[0].replace('rgba(', '').replace(')', '').split()
                        r, g, b = [int(c.strip()) for c in comps[:3]]
                    else:
                        color = pygame.Color(current_val)
                        r, g, b = color.r, color.g, color.b
                    init_col = pygame.Color(r, g, b)
                except Exception:
                    init_col = pygame.Color(128, 128, 128)
            else:
                init_col = pygame.Color(128, 128, 128)
            self.active_picker = UIColourPickerDialog(
                rect=pygame.Rect(0, 0, 420, 420),
                manager=self.ui_manager,
                initial_colour=init_col,
                window_title=f"Pick color for {btn.param}"
            )
            self.picker_target = (btn.section, btn.group, btn.param)
        btn.set_callback(handler)

    def _attach_text_handler(self, entry):
        def handler():
            self.current_theme[entry.section][entry.group][entry.param] = entry.get_text()
        entry.set_on_text_changed_callback(lambda: None)  # не обновляем сразу
        entry.set_on_unfocus_callback(handler)
    def _handle_color_button_press(self, btn):
        if hasattr(btn, 'is_gradient') and not btn.is_gradient:
            self._pick_single_color(btn)
        elif hasattr(btn, 'gradient_index'):
            self._pick_gradient_color(btn)
        else:
            self._pick_single_color(btn)

    def _pick_single_color(self, btn):
        current_val = getattr(btn, 'original_value', "#808080")
        section = btn.theme_section
        group = btn.theme_group
        param = btn.theme_param

        try:
            if current_val.startswith('#'):
                init_col = pygame.Color(current_val)
            else:
                init_col = pygame.Color(128, 128, 128)
        except Exception:
            init_col = pygame.Color(128, 128, 128)

        self.active_picker = UIColourPickerDialog(
            rect=pygame.Rect(0, 0, 420, 420),
            manager=self.ui_manager,
            initial_colour=init_col,
            window_title=f"Pick color for {param}"
        )
        self.picker_target = (section, group, param, None)

    def _pick_gradient_color(self, btn):
        section = btn.theme_section
        group = btn.theme_group
        param = btn.theme_param
        grad = parse_gradient(btn.original_value)
        if not grad:
            return
        c1, c2, angle = grad
        init_col = c1 if btn.gradient_index == 0 else c2

        self.active_picker = UIColourPickerDialog(
            rect=pygame.Rect(0, 0, 420, 420),
            manager=self.ui_manager,
            initial_colour=init_col,
            window_title=f"Pick gradient color {btn.gradient_index + 1} for {param}"
        )
        self.picker_target = (section, group, param, btn.gradient_index)
    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.apply_btn:
                self._apply_theme()
            elif event.ui_element == self.save_btn:
                self._save_theme()
            elif event.ui_element in [btn for _, btn in self.controls.values()]:
                for section_name, (_, btn) in self.controls.items():
                    if event.ui_element == btn:
                        self._open_section_editor(section_name)
                        break
            elif hasattr(event.ui_element, 'theme_section'):
                self._handle_color_button_press(event.ui_element)
            elif hasattr(event.ui_element, 'sub_window'):
                event.ui_element.sub_window.kill()
            elif event.type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
                if self.active_picker and event.ui_element == self.active_picker:
                    r, g, b = event.colour.r, event.colour.g, event.colour.b
                    if len(self.picker_target) == 4:
                        sec, grp, key, grad_idx = self.picker_target
                        old_val = self.current_theme[sec][grp][key]
                        if grad_idx is None:
                            self.current_theme[sec][grp][key] = f"#{r:02X}{g:02X}{b:02X}"
                        else:
                            grad = parse_gradient(old_val)
                            if grad:
                                c1, c2, angle = grad
                                new_color = pygame.Color(r, g, b, 201)
                                if grad_idx == 0:
                                    c1 = new_color
                                else:
                                    c2 = new_color
                                self.current_theme[sec][grp][key] = format_gradient(c1, c2, angle)
                    self.active_picker = None
                    self.picker_target = None
        super().process_event(event)

    def _apply_theme(self):
        temp_path = 'temp_theme.json'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_theme, f, indent=2)
        try:
            self.ui_manager_ref.ui_manager.get_theme().load_theme(temp_path)
            os.remove(temp_path)
        except Exception as e:
            print(f"Failed to apply theme: {e}")

    def _save_theme(self):
        with open(self.theme_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_theme, f, indent=2)