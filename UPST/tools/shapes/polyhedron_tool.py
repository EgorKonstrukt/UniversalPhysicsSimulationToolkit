import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui

class PolyhedronTool(BaseTool):
    name = "Polyhedron"
    icon_path = "sprites/gui/spawn/polyhedron.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, config.app.screen_height-200, 300, 200), manager=self.ui_manager.manager,
                                           window_display_title="Polyhedron Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.size_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                              relative_rect=pygame.Rect(60, 10, 100, 20), container=win,
                                                              manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 50, 20), text="Size:", container=win,
                                    manager=self.ui_manager.manager)
        self.faces_entry = pygame_gui.elements.UITextEntryLine(initial_text="6",
                                                               relative_rect=pygame.Rect(60, 30, 100, 20),
                                                               container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 30, 50, 20), text="Faces:", container=win,
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
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in range(faces)]
        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        mass = abs(area) / 2 / 100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.name = "Body"
        body.color = self._get_color('polyhedron')
        body.position = pos
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('polyhedron')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()

    def spawn_dragged(self, start, end):
        delta = pymunk.Vec2d(end[0] - start[0], end[1] - start[1])
        size = delta.length / 2
        if size <= 0: return
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in range(faces)]
        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        mass = abs(area) / 2 / 100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.name = "Body"
        body.color = self._get_color('polyhedron')
        body.position = start
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('polyhedron')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()
        self.preview = None

    def _calc_preview(self, end_pos):
        delta = pymunk.Vec2d(end_pos[0] - self.drag_start[0], end_pos[1] - self.drag_start[1])
        size = delta.length / 2
        faces = int(self.faces_entry.get_text())
        pts = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in range(faces)]
        area = abs(sum(pts[i][0]*pts[(i+1)%faces][1] - pts[(i+1)%faces][0]*pts[i][1] for i in range(faces))) / 2
        perimeter = sum(math.dist(pts[i], pts[(i+1)%faces]) for i in range(faces))
        return {"type": "poly", "position": self.drag_start, "points": pts, "area": area, "perimeter": perimeter, "color": (200, 200, 255, 200)}

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
        max_lines = 100
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
            # Левая грань
            y = x_min + const
            if y_min <= y <= y_max:
                points.append((x_min, y))
            # Правая грань
            y = x_max + const
            if y_min <= y <= y_max:
                points.append((x_max, y))
            # Верхняя грань
            x = y_min - const
            if x_min <= x <= x_max:
                points.append((x, y_min))
            # Нижняя грань
            x = y_max - const
            if x_min <= x <= x_max:
                points.append((x, y_max))
            if len(points) >= 2:
                p1 = camera.world_to_screen(points[0])
                p2 = camera.world_to_screen(points[1])
                pygame.draw.line(screen, line_color, p1, p2, 2)

    def _get_metric_lines(self):
        a = self.preview['area']
        p = self.preview['perimeter']
        f = len(self.preview['points'])
        return [f"F: {f}", f"A: {a:.1f}", f"P: {p:.1f}"]

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme, pal = get_theme_and_palette(config, None, getattr(self.ui_manager, "shape_palette", None))
            pdef = theme.get_palette_def(pal)
            return sample_color_from_def(pdef)
        sc = getattr(self.ui_manager, "shape_colors", {})
        return tuple(sc.get(shape_type, (200, 200, 200, 255)))