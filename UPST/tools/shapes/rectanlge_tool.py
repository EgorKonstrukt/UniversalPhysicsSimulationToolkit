import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui

class RectangleTool(BaseTool):
    name = "Rectangle"
    icon_path = "sprites/gui/spawn/rectangle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, config.app.screen_height-200, 300, 200), manager=self.ui_manager.manager,
                                           window_display_title="Rectangle Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.w_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                           relative_rect=pygame.Rect(30, 10, 100, 20), container=win,
                                                           manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 20, 20), text="W:", container=win,
                                    manager=self.ui_manager.manager)
        self.h_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                           relative_rect=pygame.Rect(30, 30, 100, 20), container=win,
                                                           manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 30, 20, 20), text="H:", container=win,
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
    def handle_event(self, event, world_pos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drag_start = world_pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_start:
                self.spawn_dragged(self.drag_start, world_pos)
            self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start:
            self.preview = self._calc_preview(world_pos)
    def spawn_at(self, pos):
        w = float(self.w_entry.get_text())
        h = float(self.h_entry.get_text())
        mass = (w * h) / 200
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w * 2, h * 2)))
        body.name = "Body"
        body.color = self._get_color('rectangle')
        body.position = pos
        body.temperature = 20
        body.heat_capacity = 1000
        body.thermal_conductivity = 1.0
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly.create_box(body, (w * 2, h * 2))
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('rectangle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()

    def spawn_dragged(self, start, end):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        w = abs(dx)
        h = abs(dy)
        if w <= 0 or h <= 0: return
        center = (start[0] + dx / 2, start[1] + dy / 2)
        mass = (w * h) / 200
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w, h)))
        body.name = "Body"
        body.color = self._get_color('rectangle')
        body.position = center
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('rectangle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()
        self.preview = None

    def _calc_preview(self, end_pos):
        dx = end_pos[0] - self.drag_start[0]
        dy = end_pos[1] - self.drag_start[1]
        w, h = abs(dx), abs(dy)
        center = (self.drag_start[0] + dx / 2, self.drag_start[1] + dy / 2)
        area = w * h
        perimeter = 2 * (w + h)
        return {"type": "rect", "position": center, "width": w, "height": h, "area": area, "perimeter": perimeter, "color": (200, 200, 255, 200)}

    def _draw_custom_preview(self, screen, camera):
        w = self.preview['width']
        h = self.preview['height']
        cx, cy = self.preview['position']
        p0 = (cx - w/2, cy - h/2)
        p1 = (cx + w/2, cy - h/2)
        p2 = (cx + w/2, cy + h/2)
        p3 = (cx - w/2, cy + h/2)
        world_pts = [p0, p1, p2, p3]
        screen_pts = [camera.world_to_screen(p) for p in world_pts]

        pygame.draw.polygon(screen, self.preview['color'], screen_pts, 1)

        self._draw_moving_hatch(screen, camera, world_pts)

    def _draw_moving_hatch(self, screen, camera, world_rect):
        cx = (world_rect[0][0] + world_rect[2][0]) / 2
        cy = (world_rect[0][1] + world_rect[2][1]) / 2
        w = abs(world_rect[1][0] - world_rect[0][0])
        h = abs(world_rect[2][1] - world_rect[1][1])
        half_w, half_h = w / 2, h / 2

        x_min = cx - half_w
        x_max = cx + half_w
        y_min = cy - half_h
        y_max = cy + half_h

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
        w = self.preview['width']
        h = self.preview['height']
        a = self.preview['area']
        p = self.preview['perimeter']
        return [f"W: {w:.1f}", f"H: {h:.1f}", f"A: {a:.1f}", f"P: {p:.1f}"]

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme, pal = get_theme_and_palette(config, None, getattr(self.ui_manager, "shape_palette", None))
            pdef = theme.get_palette_def(pal)
            return sample_color_from_def(pdef)
        sc = getattr(self.ui_manager, "shape_colors", {})
        return tuple(sc.get(shape_type, (200, 200, 200, 255)))