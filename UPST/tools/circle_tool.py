import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class CircleTool(BaseTool):
    name = "Circle"
    icon_path = "sprites/gui/spawn/circle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.ui_manager.manager,
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
        body.position = pos
        shape = pymunk.Circle(body, r)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('circle')
        self.pm.add_body_shape(body, shape)

    def spawn_dragged(self, start, end):
        start_vec = pymunk.Vec2d(*start)
        end_vec = pymunk.Vec2d(*end)
        r = (start_vec - end_vec).length
        if r <= 0: return
        mass = r * math.pi / 10
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
        body.position = start
        shape = pymunk.Circle(body, r)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('circle')
        self.pm.add_body_shape(body, shape)
        self.undo_redo.take_snapshot()

    def _calc_preview(self, end_pos):
        start_vec = pymunk.Vec2d(*self.drag_start)
        end_vec = pymunk.Vec2d(*end_pos)
        r = (start_vec - end_vec).length
        area = math.pi * r**2
        perimeter = 2 * math.pi * r
        return {"type": "circle", "position": self.drag_start, "radius": r, "area": area, "perimeter": perimeter, "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        pygame.draw.circle(screen, self.preview['color'], sp, int(self.preview['radius']), 1)

    def _get_metric_lines(self):
        r = self.preview['radius']
        a = self.preview['area']
        p = self.preview['perimeter']
        return [f"R: {r:.1f}", f"A: {a:.1f}", f"P: {p:.1f}"]

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme = config.world.themes.get(config.world.current_theme, config.world.themes["Classic"])
            r_range, g_range, b_range = theme.shape_color_range
            return (random.randint(r_range[0], r_range[1]), random.randint(g_range[0], g_range[1]),
                    random.randint(b_range[0], b_range[1]), 255)
        return getattr(self.ui_manager, f"shape_colors")[shape_type]