import pygame
import pygame_gui
from UPST.tools.base_tool import BaseTool
import math

class FractalTool(BaseTool):
    name = "fractal"
    category = "Visualization"
    icon_path = None
    tooltip = "Render animated Mandelbrot/Julia fractals with time parameter 't'"

    def __init__(self, app):
        super().__init__(app)
        self.graph_manager = app.console_handler.graph_manager
        self.fractal_type = "mandelbrot"
        self.max_iter = 100
        self.escape_radius = 2.0
        self.fractal_c = complex(-0.7, 0.27)
        self.palette = "#000000,#0000ff,#00ffff,#00ff00,#ffff00,#ff0000"
        self.color = (0, 200, 255)
        self.width = 2
        self.style = "solid"
        self.x_range = (-0.16, 1.0405)
        self.y_range = (-0.722, 0.246)
        self.t_value = 0.0
        self._last_applied_t = None
        self.anim_enabled = False
        self.anim_t_min = 0.0
        self.anim_t_max = 1.0
        self.anim_duration = 5.0
        self.anim_easing = "linear"
        self.anim_start_time = 0.0

    def create_settings_window(self):
        if self.settings_window and self.settings_window.alive():
            self.settings_window.show()
            return
        screen_w, screen_h = self.ui_manager.manager.window_resolution
        win_size = (450, 530)
        pos = self.tool_system._find_non_overlapping_position(win_size, pygame.Rect(0, 0, screen_w, screen_h))
        rect = pygame.Rect(*pos, *win_size)
        self.settings_window = pygame_gui.elements.UIWindow(
            rect=rect,
            manager=self.ui_manager.manager,
            window_display_title=f"{self.name} Settings",
            resizable=True
        )
        container = self.settings_window.get_container()
        y = 10
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 80, 25), "Type:", self.ui_manager.manager, container=container)
        self.type_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['mandelbrot', 'julia'], self.fractal_type, pygame.Rect(95, y, 120, 25),
            self.ui_manager.manager, container=container
        )
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 25, 25), "t =", self.ui_manager.manager, container=container)
        self.t_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(40, y, 80, 25), self.ui_manager.manager, container=container)
        self.t_entry.set_text(str(self.t_value))
        self.t_entry.disable() if self.anim_enabled else self.t_entry.enable()
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 100, 25), "Animate t:", self.ui_manager.manager, container=container)
        self.anim_checkbox = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(110, y, 25, 25),
            text="",
            manager=self.ui_manager.manager,
            container=container
        )
        self.anim_checkbox.set_state(True) if self.anim_enabled else self.anim_checkbox.set_state(False)
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 70, 25), "t range:", self.ui_manager.manager, container=container)
        self.t_min_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(85, y, 60, 25), self.ui_manager.manager, container=container)
        self.t_min_entry.set_text(str(self.anim_t_min))
        self.t_max_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(155, y, 60, 25), self.ui_manager.manager, container=container)
        self.t_max_entry.set_text(str(self.anim_t_max))
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 70, 25), "Duration:", self.ui_manager.manager, container=container)
        self.duration_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(85, y, 60, 25), self.ui_manager.manager, container=container)
        self.duration_entry.set_text(str(self.anim_duration))
        pygame_gui.elements.UILabel(pygame.Rect(155, y, 30, 25), "s", self.ui_manager.manager, container=container)
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 70, 25), "Easing:", self.ui_manager.manager, container=container)
        self.easing_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['linear', 'ease-out'], self.anim_easing, pygame.Rect(85, y, 100, 25),
            self.ui_manager.manager, container=container
        )
        y += 40
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 80, 25), "Max iter:", self.ui_manager.manager, container=container)
        self.iter_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(95, y, 60, 25), self.ui_manager.manager, container=container)
        self.iter_entry.set_text(str(self.max_iter))
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 100, 25), "Escape radius:", self.ui_manager.manager, container=container)
        self.er_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(115, y, 60, 25), self.ui_manager.manager, container=container)
        self.er_entry.set_text(str(self.escape_radius))
        y += 35
        self.c_label = pygame_gui.elements.UILabel(pygame.Rect(10, y, 30, 25), "c =", self.ui_manager.manager, container=container)
        self.c_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(45, y, 120, 25), self.ui_manager.manager, container=container)
        self.c_entry.set_text(f"{self.fractal_c.real}+{self.fractal_c.imag}i")
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 60, 25), "Palette:", self.ui_manager.manager, container=container)
        self.palette_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(75, y, 270, 25), self.ui_manager.manager, container=container)
        self.palette_entry.set_text(self.palette)
        y += 40
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 80, 25), "Color:", self.ui_manager.manager, container=container)
        self.color_btn = pygame_gui.elements.UIButton(pygame.Rect(90, y, 60, 25), "", self.ui_manager.manager, container=container)
        self._update_color_btn()
        pygame_gui.elements.UILabel(pygame.Rect(160, y, 60, 25), "Width:", self.ui_manager.manager, container=container)
        self.width_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(220, y, 40, 25), self.ui_manager.manager, container=container)
        self.width_entry.set_text(str(self.width))
        pygame_gui.elements.UILabel(pygame.Rect(270, y, 50, 25), "Style:", self.ui_manager.manager, container=container)
        self.style_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['solid', 'dashed', 'dotted'], self.style, pygame.Rect(320, y, 60, 25),
            self.ui_manager.manager, container=container
        )
        y += 45
        self.apply_btn = pygame_gui.elements.UIButton(pygame.Rect(10, y, 100, 30), "Apply", self.ui_manager.manager, container=container)
        self.clear_btn = pygame_gui.elements.UIButton(pygame.Rect(120, y, 100, 30), "Clear", self.ui_manager.manager, container=container)
        self._update_c_visibility()


    def _update_c_visibility(self):
        is_julia = self.fractal_type == "julia"
        self.c_label.visible = is_julia
        self.c_entry.visible = is_julia

    def _update_color_btn(self):
        surf = pygame.Surface((56, 21))
        surf.fill(self.color)
        self.color_btn.drawable_shape.states['normal'].surface = surf
        self.color_btn.drawable_shape.redraw_all_states()

    def handle_event(self, event, world_pos):
        super().handle_event(event, world_pos)
        if not self.settings_window or not self.settings_window.alive(): return
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.color_btn:
                r, g, b = self.color
                r = (r + 50) % 256
                g = (g + 100) % 256
                b = (b + 150) % 256
                self.color = (r, g, b)
                self._update_color_btn()
            elif event.ui_element == self.apply_btn:
                self._apply_fractal_settings(force=True)
            elif event.ui_element == self.clear_btn:
                self.graph_manager.handle_graph_command('clear')
        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.type_dropdown:
                self.fractal_type = event.text
                self._update_c_visibility()
                self._apply_fractal_settings(force=True)
            elif event.ui_element == self.easing_dropdown:
                self.anim_easing = event.text
        elif event.type in (pygame_gui.UI_CHECK_BOX_CHECKED, pygame_gui.UI_CHECK_BOX_UNCHECKED):
            if event.ui_element == self.anim_checkbox:
                self.anim_enabled = self.anim_checkbox.get_state()
                if self.anim_enabled:
                    self.anim_start_time = pygame.time.get_ticks() / 1000.0
                    self.t_entry.disable()
                else:
                    self.t_entry.enable()
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.width_entry:
                try: self.width = max(1, min(5, int(event.text)))
                except: pass
            elif event.ui_element == self.t_entry and not self.anim_enabled:
                try: self.t_value = float(self.t_entry.get_text())
                except: pass
                self._apply_fractal_settings(force=True)
            elif event.ui_element == self.t_min_entry:
                try: self.anim_t_min = float(self.t_min_entry.get_text())
                except: pass
            elif event.ui_element == self.t_max_entry:
                try: self.anim_t_max = float(self.t_max_entry.get_text())
                except: pass
            elif event.ui_element == self.duration_entry:
                try: self.anim_duration = max(0.1, float(self.duration_entry.get_text()))
                except: pass
        elif event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED:
            if event.ui_element == self.t_entry and not self.anim_enabled:
                try:
                    new_t = float(self.t_entry.get_text() or "0")
                    if abs(new_t - self.t_value) > 1e-6:
                        self.t_value = new_t
                        self._apply_fractal_settings()
                except: pass

    def _evaluate_param(self, expr, t_val):
        if 't' not in expr.lower():
            return expr
        try:
            safe_dict = {"t": t_val, "__builtins__": {}}
            result = eval(expr.replace('i','j'), safe_dict)
            if isinstance(result, complex):
                return f"{result.real}+{result.imag}j"
            return str(float(result))
        except:
            return expr

    def _ease_out(self, t):
        return 1 - (1 - t) ** 2

    def update(self, dt):
        if self.anim_enabled and self.anim_duration > 0:
            elapsed = (pygame.time.get_ticks() / 1000.0 - self.anim_start_time) % self.anim_duration
            phase = elapsed / self.anim_duration
            if self.anim_easing == "ease-out":
                phase = self._ease_out(phase)
            self.t_value = self.anim_t_min + (self.anim_t_max - self.anim_t_min) * phase
            self.t_entry.set_text(f"{self.t_value:.4f}")
            self._apply_fractal_settings(force=True)
        elif not self.anim_enabled and self._last_applied_t != self.t_value:
            self._apply_fractal_settings(force=True)


    def _apply_fractal_settings(self, force=False):
        try:
            current_t = self.t_value
            if not force and current_t == self._last_applied_t:
                return
            self._last_applied_t = current_t
            self.max_iter = max(10, min(1000, int(self.iter_entry.get_text())))
            self.escape_radius = max(1.0, float(self.er_entry.get_text()))
            if self.fractal_type == "julia":
                c_expr = self.c_entry.get_text()
                c_str = self._evaluate_param(c_expr, current_t).replace('i', 'j')
                self.fractal_c = complex(c_str)
            self.palette = self.palette_entry.get_text()
        except:
            pass
        cmd_parts = [f"fractal {self.fractal_type}"]
        cmd_parts.extend([
            f"x={self.x_range[0]}..{self.x_range[1]}",
            f"y={self.y_range[0]}..{self.y_range[1]}",
            f"max_iter:{self.max_iter}",
            f"escape_radius:{self.escape_radius}",
            f"color:{self.color[0]},{self.color[1]},{self.color[2]}",
            f"width:{self.width}",
            f"style:{self.style}"
        ])
        if self.fractal_type == "julia":
            c_real = self.fractal_c.real
            c_imag = self.fractal_c.imag
            c_formatted = f"{c_real}{c_imag:+}i".replace('+-', '-')
            cmd_parts.append(f"c={c_formatted}")
        if self.palette.strip():
            cmd_parts.append(f"palette:{self.palette}")
        full_cmd = "; ".join(cmd_parts)
        self.graph_manager.handle_graph_command(full_cmd)

    def activate(self):
        super().activate()
        if not self.settings_window or not self.settings_window.alive():
            self.create_settings_window()

    def deactivate(self):
        super().deactivate()
        if self.settings_window and self.settings_window.alive():
            self.settings_window.hide()