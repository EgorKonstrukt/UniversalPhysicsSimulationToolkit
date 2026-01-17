import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui


class PivotJointTool(BaseTool):
    name = "PivotJoint"
    icon_path = "sprites/gui/tools/pivot.png"

    def __init__(self, pm, app):
        super().__init__(pm, app)
        self.first_body = None
        self.first_pos = None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 300, 130),
            manager=self.ui_manager.manager,
            window_display_title="Pivot Joint Settings"
        )
        self.collide_checkbox = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 10, 20, 20),
            text="Enable Collision",
            manager=self.ui_manager.manager,
            container=win
        )
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            info = self.pm.space.point_query_nearest(world_pos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
            if not body:
                self.first_body = None
                return
            if self.first_body is None:
                self.first_body = body
                self.first_pos = world_pos
            else:
                if self.first_body != body:
                    pivot = pymunk.PivotJoint(self.first_body, body, self.first_pos)
                    pivot.collide_bodies = self.collide_checkbox.get_state()
                    self.pm.space.add(pivot)
                    self.undo_redo.take_snapshot()
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None