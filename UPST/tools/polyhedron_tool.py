import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class PolyhedronTool(BaseTool):
    name = "Polyhedron"
    icon_path = "sprites/gui/spawn/polyhedron.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.ui_manager.manager,
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
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in
                  range(faces)]
        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        mass = abs(area) / 2 / 100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = pos
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('polyhedron')
        self.pm.add_body_shape(body, shape)

    def spawn_dragged(self, start, end):
        delta = pymunk.Vec2d(end[0] - start[0], end[1] - start[1])
        size = delta.length / 2
        if size <= 0:
            return
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in
                  range(faces)]
        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        mass = abs(area) / 2 / 100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = start
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('polyhedron')
        self.pm.add_body_shape(body, shape)

    def _calc_preview(self, end_pos):
        delta = pymunk.Vec2d(end_pos[0] - self.drag_start[0], end_pos[1] - self.drag_start[1])
        size = delta.length / 2
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in
                  range(faces)]
        return {"type": "poly", "position": self.drag_start, "points": points, "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        pts = [(sp[0] + p[0], sp[1] + p[1]) for p in self.preview['points']]
        pygame.draw.polygon(screen, self.preview['color'], pts, 1)

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme = config.world.themes.get(config.world.current_theme, config.world.themes["Classic"])
            r_range, g_range, b_range = theme.shape_color_range
            return (random.randint(r_range[0], r_range[1]), random.randint(g_range[0], g_range[1]),
                    random.randint(b_range[0], b_range[1]), 255)
        return getattr(self.ui_manager, f"shape_colors")[shape_type]