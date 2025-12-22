import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui


class PinJointTool(BaseTool):
    name = "PinJoint"
    icon_path = "sprites/gui/tools/rigid.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.first_body = None
        self.first_pos = None
        self.distance = 0.0

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 300, 130),
            manager=self.ui_manager.manager,
            window_display_title="Pin Joint Settings"
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Distance:", manager=self.ui_manager.manager, container=win)
        self.distance_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="auto", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
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
                    anchor1 = self.first_body.world_to_local(self.first_pos)
                    anchor2 = body.world_to_local(world_pos)
                    try:
                        dist_text = self.distance_entry.get_text().strip()
                        dist = 0.0 if dist_text == "auto" else float(dist_text)
                        rigid = pymunk.PinJoint(self.first_body, body, anchor1, anchor2)
                        rigid.distance = dist
                        self.pm.space.add(rigid)
                        self.undo_redo.take_snapshot()
                    except ValueError:
                        pass
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None