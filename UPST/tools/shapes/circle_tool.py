import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui

class CircleTool(BaseTool):
    name = "Circle"
    icon_path = "sprites/gui/spawn/circle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, config.app.screen_height-200, 300, 200), manager=self.ui_manager.manager,
                                           window_display_title="Circle Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.radius_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                                relative_rect=pygame.Rect(30, 10, 100, 20),
                                                                container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 20, 20), text="R:", container=win,
                                    manager=self.ui_manager.manager)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.7",
                                                                  relative_rect=pygame.Rect(80, 55, 100, 20),
                                                                  container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 55, 80, 20), text="Friction:", container=win,
                                    manager=self.ui_manager.manager)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.5",
                                                                    relative_rect=pygame.Rect(90, 75, 105, 20),
                                                                    container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 75, 85, 20), text="Elasticity:", container=win,
                                    manager=self.ui_manager.manager)
        self.color_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 105, 100, 25), text="Pick Color",
                                                      manager=self.ui_manager.manager, container=win)
        self.rand_cb = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 130, 20, 20), text="",
                                                    manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(28, 130, 100, 20), text="Random", container=win,
                                    manager=self.ui_manager.manager)
        self.rand_img = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(5, 130, 20, 20),
                                                    image_surface=pygame.image.load("sprites/gui/checkbox_true.png"),
                                                    container=win, manager=self.ui_manager.manager)
        self.settings_window = win

    def spawn_at(self, pos):
        r = float(self.radius_entry.get_text())
        mass = r * math.pi / 10
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
        body.name = "Body"
        body.color = self._get_color('circle')
        body.position = pos
        body.custom_force = pygame.math.Vector2(0, 0)
        body.temperature = 3000
        body.heat_capacity = 1000
        body.thermal_conductivity = 1.0
        shape = pymunk.Circle(body, r)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('circle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()

    def spawn_dragged(self, start, end):
        start_vec = pymunk.Vec2d(*start)
        end_vec = pymunk.Vec2d(*end)
        r = (start_vec - end_vec).length
        if r <= 0: return
        mass = r * math.pi / 10
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
        body.name = "Body"
        body.color = self._get_color('circle')
        body.position = start
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Circle(body, r)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('circle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()
        self.preview = None

    def _calc_preview(self, end_pos):
        start_vec = pymunk.Vec2d(*self.drag_start)
        end_vec = pymunk.Vec2d(*end_pos)
        r = (start_vec - end_vec).length
        area = math.pi * r ** 2
        perimeter = 2 * math.pi * r
        return {"type": "circle", "position": self.drag_start, "radius": r, "area": area, "perimeter": perimeter, "color": (200, 200, 255, 200)}

    def _draw_custom_preview(self, screen, camera):
        center = self.preview['position']
        r = self.preview['radius'] * camera.scaling
        sp = camera.world_to_screen(center)
        pygame.draw.circle(screen, self.preview['color'], sp, int(r), 1)
        guide_end = (center[0] + r, center[1])
        guide_screen = camera.world_to_screen(guide_end)
        pygame.draw.line(screen, (255, 200, 200, 200), sp, guide_screen, 1)
        self._draw_moving_hatch(screen, camera, center, r)

    def _draw_moving_hatch(self, screen, camera, center, radius):
        cx, cy = center
        period = 10.0
        offset = self._last_hatch_offset
        line_color = (*self.preview['color'][:3], 128)
        max_lines = 60
        r = radius / camera.scaling
        x_min, x_max = cx - r, cx + r
        y_min, y_max = cy - r, cy + r

        c_low = (y_min - x_max) - offset
        c_high = (y_max - x_min) - offset
        c_start = int(c_low / period) * period
        c_end = int(c_high / period + 1) * period
        total_lines = int((c_end - c_start) / period)
        if total_lines <= max_lines:
            c_values = [c_start + i * period for i in range(total_lines)]
        else:
            step = total_lines / max_lines
            c_values = [c_start + int(i * step) * period for i in range(max_lines)]

        for c_unshifted in c_values:
            const = c_unshifted + offset
            points = []
            # Пересечение диагонали y = x + const с окружностью
            # Решаем (x - cx)^2 + (x + const - cy)^2 = r^2
            a = 2
            b = 2 * (const - cy - cx)
            c = (cx ** 2 + (const - cy) ** 2 - r ** 2)
            disc = b * b - 4 * a * c
            if disc < 0: continue
            sqrt_disc = math.sqrt(disc)
            x1 = (-b + sqrt_disc) / (2 * a)
            x2 = (-b - sqrt_disc) / (2 * a)
            y1 = x1 + const
            y2 = x2 + const
            p1_in = (x_min <= x1 <= x_max) and (y_min <= y1 <= y_max)
            p2_in = (x_min <= x2 <= x_max) and (y_min <= y2 <= y_max)
            if p1_in: points.append((x1, y1))
            if p2_in: points.append((x2, y2))
            if len(points) == 2:
                s1 = camera.world_to_screen(points[0])
                s2 = camera.world_to_screen(points[1])
                pygame.draw.line(screen, line_color, s1, s2, 2)

    def _get_metric_lines(self):
        r = self.preview['radius']
        a = self.preview['area']
        p = self.preview['perimeter']
        return [f"R: {r:.1f}", f"A: {a:.1f}", f"P: {p:.1f}"]

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme, pal = get_theme_and_palette(config, None, getattr(self.ui_manager, "shape_palette", None))
            pdef = theme.get_palette_def(pal)
            return sample_color_from_def(pdef)
        sc = getattr(self.ui_manager, "shape_colors", {})
        return tuple(sc.get(shape_type, (200, 200, 200, 255)))