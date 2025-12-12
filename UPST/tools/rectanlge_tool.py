import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.tool_manager import BaseTool
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

    def spawn_at(self, pos):
        w = float(self.w_entry.get_text())
        h = float(self.h_entry.get_text())
        mass = (w * h) / 200
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w * 2, h * 2)))
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
        body.position = center
        body.custom_force = pygame.math.Vector2(0, 0)
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('rectangle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()

    def _calc_preview(self, end_pos):
        dx = end_pos[0] - self.drag_start[0]
        dy = end_pos[1] - self.drag_start[1]
        w, h = abs(dx), abs(dy)
        center = (self.drag_start[0] + dx / 2, self.drag_start[1] + dy / 2)
        area = w * h
        perimeter = 2 * (w + h)
        return {"type": "rect", "position": center, "width": w, "height": h, "area": area, "perimeter": perimeter, "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        r = pygame.Rect(0, 0, self.preview['width'], self.preview['height'])
        r.center = sp
        pygame.draw.rect(screen, self.preview['color'], r, 1)

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