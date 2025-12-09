import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui


class MoveTool(BaseTool):
    name = "Move"
    icon_path = "sprites/gui/tools/move.png"
    def __init__(self, pm):
        super().__init__(pm)
        self.tgt = None
        self.drag = False
        self.offset = pymunk.Vec2d(0, 0)
        self.cb_center = None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, config.app.screen_height-130, 300, 130),
            manager=self.ui_manager.manager,
            window_display_title="Move Settings"
        )
        self.cb_center = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 10, 200, 20),
            text="Брать за центр массы",
            manager=self.ui_manager.manager,
            container=win
        )
        self.settings_window = win

    def handle_event(self, event, wpos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            info = self.pm.space.point_query_nearest(wpos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
            if body:
                self.tgt = body
                if self.cb_center.get_state():
                    self.offset = pymunk.Vec2d(0, 0)
                else:
                    self.offset = wpos - self.tgt.position
                self.drag = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag:
                self._stop_move()
        elif event.type == pygame.MOUSEMOTION and self.drag and self.tgt:
            self._move_to(wpos)

    def _move_to(self, wpos):
        self.tgt.position = wpos - self.offset

    def _stop_move(self):
        self.drag = False
        self.tgt = None
        self.undo_redo.take_snapshot()

    def deactivate(self):
        if self.drag:
            self._stop_move()