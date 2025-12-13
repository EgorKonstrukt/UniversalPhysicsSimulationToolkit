import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class TriangleTool(BaseTool):
    name = "Triangle"
    icon_path = "sprites/gui/spawn/triangle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, config.app.screen_height-200, 300, 200), manager=self.ui_manager.manager,
                                           window_display_title="Triangle Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.size_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                              relative_rect=pygame.Rect(60, 10, 100, 20), container=win,
                                                              manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 50, 20), text="Size:", container=win,
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
        size = float(self.size_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / 3), size * math.sin(i * 2 * math.pi / 3)) for i in range(3)]
        mass = (size ** 2) / 200
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = pos
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('triangle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()

    def spawn_dragged(self, start, end):
        delta = pymunk.Vec2d(end[0] - start[0], end[1] - start[1])
        size = delta.length / 2
        if size <= 0: return
        points = [(size * math.cos(i * 2 * math.pi / 3), size * math.sin(i * 2 * math.pi / 3)) for i in range(3)]
        mass = (size ** 2) / 200
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = start
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('triangle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()
        self.preview = None

    def _calc_preview(self, end_pos):
        delta = pymunk.Vec2d(end_pos[0] - self.drag_start[0], end_pos[1] - self.drag_start[1])
        size = delta.length / 2
        points = [(size * math.cos(i * 2 * math.pi / 3), size * math.sin(i * 2 * math.pi / 3)) for i in range(3)]
        area = abs(sum(points[i][0]*points[(i+1)%3][1] - points[(i+1)%3][0]*points[i][1] for i in range(3))) / 2
        perimeter = sum(math.dist(points[i], points[(i+1)%3]) for i in range(3))
        return {"type": "poly", "position": self.drag_start, "points": points, "area": area, "perimeter": perimeter, "color": (200, 200, 255, 200)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        pts = [(sp[0] + p[0], sp[1] + p[1]) for p in self.preview['points']]
        pygame.draw.polygon(screen, self.preview['color'], pts, 1)
        world_pts = [(self.preview['position'][0] + p[0], self.preview['position'][1] + p[1]) for p in self.preview['points']]
        self._draw_moving_hatch(screen, camera, world_pts)

    def _draw_moving_hatch(self, screen, camera, world_pts):
        xs = [p[0] for p in world_pts]
        ys = [p[1] for p in world_pts]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        period = 10.0
        offset = self._last_hatch_offset
        line_color = (*self.preview['color'][:3], 128)
        max_lines = 60
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
            y = x_min + const
            if y_min <= y <= y_max: points.append((x_min, y))
            y = x_max + const
            if y_min <= y <= y_max: points.append((x_max, y))
            x = y_min - const
            if x_min <= x <= x_max: points.append((x, y_min))
            x = y_max - const
            if x_min <= x <= x_max: points.append((x, y_max))
            if len(points) >= 2:
                p1 = camera.world_to_screen(points[0])
                p2 = camera.world_to_screen(points[1])
                pygame.draw.line(screen, line_color, p1, p2, 2)

    def _get_metric_lines(self):
        a = self.preview['area']
        p = self.preview['perimeter']
        return [f"A: {a:.1f}", f"P: {p:.1f}"]

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme, pal = get_theme_and_palette(config, None, getattr(self.ui_manager, "shape_palette", None))
            pdef = theme.get_palette_def(pal)
            return sample_color_from_def(pdef)
        sc = getattr(self.ui_manager, "shape_colors", {})
        return tuple(sc.get(shape_type, (200, 200, 200, 255)))