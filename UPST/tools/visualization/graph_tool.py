import pygame
import pygame_gui
from UPST.tools.base_tool import BaseTool
from UPST.config import config

class GraphTool(BaseTool):
    name = "graph"
    category = "Visualization"
    icon_path = None
    tooltip = "Create mathematical graphs and fractals"

    def __init__(self, app):
        super().__init__(app)
        self.graph_manager = app.console_handler.graph_manager
        self.expression = "y=sin(x)"
        self.plot_type = "cartesian"
        self.color = (0, 200, 255)
        self.width = 2
        self.style = "solid"
        self.x_range = (-10.0, 10.0)
        self.y_range = (-5.0, 5.0)
        self.max_iter = 100
        self.escape_radius = 2.0
        self.fractal_c = complex(-0.7, 0.27)
        self.palette = "#000000,#0000ff,#00ffff,#00ff00,#ffff00,#ff0000"

    def create_settings_window(self):
        if self.settings_window and self.settings_window.alive():
            self.settings_window.show()
            return
        rect = pygame.Rect(100, 100, 400, 500)
        self.settings_window = pygame_gui.elements.UIWindow(
            rect, self.ui_manager.manager, window_display_title="Graph Settings",
            resizable=True, visible=True
        )
        container = self.settings_window.get_container()
        y = 10
        self.type_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['cartesian', 'parametric', 'polar', 'implicit', 'fractal', 'scatter', 'field'],
            self.plot_type, pygame.Rect(10, y, 180, 30), self.ui_manager.manager, container=container
        )
        self.expr_entry = pygame_gui.elements.UITextEntryLine(
            pygame.Rect(10, y + 40, 360, 30), self.ui_manager.manager, container=container
        )
        self.expr_entry.set_text(self.expression)
        y += 80
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 80, 25), "Color:", self.ui_manager.manager, container=container)
        self.color_btn = pygame_gui.elements.UIButton(
            pygame.Rect(90, y, 60, 25), "", self.ui_manager.manager, container=container
        )
        self._update_color_btn()
        pygame_gui.elements.UILabel(pygame.Rect(160, y, 60, 25), "Width:", self.ui_manager.manager, container=container)
        self.width_entry = pygame_gui.elements.UITextEntryLine(
            pygame.Rect(220, y, 40, 25), self.ui_manager.manager, container=container
        )
        self.width_entry.set_text(str(self.width))
        pygame_gui.elements.UILabel(pygame.Rect(270, y, 50, 25), "Style:", self.ui_manager.manager, container=container)
        self.style_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['solid', 'dashed', 'dotted'], self.style, pygame.Rect(320, y, 60, 25), self.ui_manager.manager, container=container
        )
        y += 40
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 50, 25), "X range:", self.ui_manager.manager, container=container)
        self.xmin_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(70, y, 80, 25), self.ui_manager.manager, container=container)
        self.xmin_entry.set_text(str(self.x_range[0]))
        pygame_gui.elements.UILabel(pygame.Rect(160, y, 20, 25), "..", self.ui_manager.manager, container=container)
        self.xmax_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(185, y, 80, 25), self.ui_manager.manager, container=container)
        self.xmax_entry.set_text(str(self.x_range[1]))
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 50, 25), "Y range:", self.ui_manager.manager, container=container)
        self.ymin_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(70, y, 80, 25), self.ui_manager.manager, container=container)
        self.ymin_entry.set_text(str(self.y_range[0]))
        pygame_gui.elements.UILabel(pygame.Rect(160, y, 20, 25), "..", self.ui_manager.manager, container=container)
        self.ymax_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(185, y, 80, 25), self.ui_manager.manager, container=container)
        self.ymax_entry.set_text(str(self.y_range[1]))
        y += 45
        self.fractal_params = pygame_gui.elements.UIPanel(
            pygame.Rect(10, y, 360, 120), manager=self.ui_manager.manager, container=container, visible=False
        )
        pygame_gui.elements.UILabel(pygame.Rect(10, 5, 80, 25), "Max iter:", self.ui_manager.manager, container=self.fractal_params)
        self.iter_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(95, 5, 60, 25), self.ui_manager.manager, container=self.fractal_params)
        self.iter_entry.set_text(str(self.max_iter))
        pygame_gui.elements.UILabel(pygame.Rect(10, 35, 100, 25), "Escape radius:", self.ui_manager.manager, container=self.fractal_params)
        self.er_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(115, 35, 60, 25), self.ui_manager.manager, container=self.fractal_params)
        self.er_entry.set_text(str(self.escape_radius))
        pygame_gui.elements.UILabel(pygame.Rect(10, 65, 30, 25), "c =", self.ui_manager.manager, container=self.fractal_params)
        self.c_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(45, 65, 120, 25), self.ui_manager.manager, container=self.fractal_params)
        self.c_entry.set_text(f"{self.fractal_c.real}+{self.fractal_c.imag}i")
        pygame_gui.elements.UILabel(pygame.Rect(10, 95, 60, 25), "Palette:", self.ui_manager.manager, container=self.fractal_params)
        self.palette_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(75, 95, 270, 25), self.ui_manager.manager, container=self.fractal_params)
        self.palette_entry.set_text(self.palette)
        y += 130
        self.apply_btn = pygame_gui.elements.UIButton(
            pygame.Rect(10, y, 100, 30), "Apply", self.ui_manager.manager, container=container
        )
        self.clear_btn = pygame_gui.elements.UIButton(
            pygame.Rect(120, y, 100, 30), "Clear", self.ui_manager.manager, container=container
        )
        self._update_ui_visibility()

    def _update_color_btn(self):
        surf = pygame.Surface((56, 21))
        surf.fill(self.color)
        self.color_btn.drawable_shape.states['normal'].surface = surf
        self.color_btn.drawable_shape.redraw_all_states()

    def _update_ui_visibility(self):
        is_fractal = self.plot_type == 'fractal'
        self.fractal_params.visible = is_fractal
        has_y_range = self.plot_type in ('cartesian', 'implicit', 'field', 'fractal')
        self.ymin_entry.visible = has_y_range
        self.ymax_entry.visible = has_y_range
        self.xmin_entry.visible = self.plot_type != 'fractal'
        self.xmax_entry.visible = self.plot_type != 'fractal'

    def handle_event(self, event, world_pos):
        super().handle_event(event, world_pos)
        if not self.settings_window or not self.settings_window.alive():
            return
        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.type_dropdown:
                self.plot_type = event.text
                self._update_ui_visibility()
            elif event.ui_element == self.style_dropdown:
                self.style = event.text
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.color_btn:
                r, g, b = self.color
                r = (r + 50) % 256
                g = (g + 100) % 256
                b = (b + 150) % 256
                self.color = (r, g, b)
                self._update_color_btn()
            elif event.ui_element == self.apply_btn:
                self._apply_graph_settings()
            elif event.ui_element == self.clear_btn:
                self.graph_manager.handle_graph_command('clear')
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.width_entry:
                try: self.width = max(1, min(5, int(event.text)))
                except: pass

    def _apply_graph_settings(self):
        try:
            xmin = float(self.xmin_entry.get_text())
            xmax = float(self.xmax_entry.get_text())
            ymin = float(self.ymin_entry.get_text())
            ymax = float(self.ymax_entry.get_text())
            self.x_range = (xmin, xmax)
            self.y_range = (ymin, ymax)
        except:
            pass
        self.expression = self.expr_entry.get_text().strip() or "y=sin(x)"
        cmd_parts = [self.expression]
        cmd_parts.append(f"color:{self.color[0]},{self.color[1]},{self.color[2]}")
        cmd_parts.append(f"width:{self.width}")
        cmd_parts.append(f"style:{self.style}")
        if self.plot_type == 'fractal':
            try:
                self.max_iter = max(10, min(1000, int(self.iter_entry.get_text())))
                self.escape_radius = max(1.0, float(self.er_entry.get_text()))
                c_str = self.c_entry.get_text().replace('i', 'j')
                self.fractal_c = complex(c_str)
                self.palette = self.palette_entry.get_text()
            except:
                pass
            cmd_parts.append(f"max_iter:{self.max_iter}")
            cmd_parts.append(f"escape_radius:{self.escape_radius}")
            cmd_parts.append(f"c={self.fractal_c.real}+{self.fractal_c.imag}j")
            if self.palette.strip():
                cmd_parts.append(f"palette:{self.palette}")
        else:
            if self.plot_type in ('cartesian', 'implicit', 'field'):
                cmd_parts.append(f"x={self.x_range[0]}..{self.x_range[1]}")
                cmd_parts.append(f"y={self.y_range[0]}..{self.y_range[1]}")
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