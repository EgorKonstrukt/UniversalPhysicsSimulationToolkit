import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui

class SpringTool(BaseTool):
    name = "Spring"
    category = "Constraints"
    icon_path = "sprites/gui/tools/spring.png"

    def __init__(self, app):
        super().__init__(app)
        self.first_body = None
        self.first_pos = None
        self.stiffness = 200.0
        self.damping = 10.0
        self.rest_length = 0.0

    def create_settings_window(self):
        screen_w, screen_h = self.ui_manager.manager.window_resolution
        win_size = (300, 400)
        pos = self.tool_system._find_non_overlapping_position(win_size, pygame.Rect(0, 0, screen_w, screen_h))
        rect = pygame.Rect(*pos, *win_size)
        win = pygame_gui.elements.UIWindow(
            rect=rect,
            manager=self.ui_manager.manager,
            window_display_title=f"{self.name} Settings",
            resizable=True
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Stiffness:", manager=self.ui_manager.manager, container=win)
        self.stiffness_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="200", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 40, 120, 20), text="Damping:", manager=self.ui_manager.manager, container=win)
        self.damping_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 40, 60, 20), initial_text="10", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 70, 120, 20), text="Rest Length:", manager=self.ui_manager.manager, container=win)
        self.rest_len_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 70, 60, 20), initial_text="auto", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            info = self.app.physics_manager.space.point_query_nearest(world_pos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
            if not body:
                self.first_body = None
                return
            if self.first_body is None:
                self.first_body = body
                self.first_pos = world_pos
            else:
                if self.first_body != body:
                    anchor1 = self.first_body.world_to_local(self.first_pos)
                    anchor2 = body.world_to_local(world_pos)
                    try:
                        rest_len_text = self.rest_len_entry.get_text().strip()
                        rest_len = self.first_body.position.get_distance(body.position) if rest_len_text == "auto" else float(rest_len_text)
                        stiffness = float(self.stiffness_entry.get_text() or "200")
                        damping = float(self.damping_entry.get_text() or "10")
                        spring = pymunk.DampedSpring(self.first_body, body, anchor1, anchor2, rest_len, stiffness, damping)
                        spring.color = self._get_color("spring")
                        spring.rest_length = rest_len
                        spring.size = 10 * self.app.camera.inv_scaling
                        self.app.physics_manager.space.add(spring)
                        self.undo_redo.take_snapshot()
                    except ValueError:
                        pass
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme, pal = get_theme_and_palette(config, None, getattr(self.ui_manager, "shape_palette", None))
            pdef = theme.get_palette_def(pal)
            return sample_color_from_def(pdef)
        sc = getattr(self.ui_manager, "shape_colors", {})
        return tuple(sc.get(shape_type, (200, 200, 200, 255)))