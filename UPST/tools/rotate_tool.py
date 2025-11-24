import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class RotateTool(BaseTool):
    name = "Rotate"
    icon_path = "sprites/gui/tools/rotate.png"
    def __init__(self, pm):
        super().__init__(pm)
        self.tgt = None
        self.drag = False
        self.start_angle = 0
        self.initial_vec = None
        self.cb_center = None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, 10, 260, 130),
            manager=self.ui_manager.manager,
            window_display_title="Rotate Settings"
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
                self.start_angle = self.tgt.angle
                offset = pymunk.Vec2d(0, 0) if self.cb_center.get_state() else wpos - self.tgt.position
                self.initial_vec = wpos - (self.tgt.position + offset)
                self.drag = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag:
                self._stop_rotate()
        elif event.type == pygame.MOUSEMOTION and self.drag and self.tgt:
            self._rotate_to(wpos)

    def _rotate_to(self, wpos):
        if not self.initial_vec or self.initial_vec.length == 0:
            return
        offset = pymunk.Vec2d(0, 0) if self.cb_center.get_state() else wpos - self.tgt.position
        current_vec = wpos - (self.tgt.position + offset)
        if current_vec.length == 0:
            return
        da = current_vec.angle - self.initial_vec.angle
        self.tgt.angle = self.start_angle + da

    def _stop_rotate(self):
        self.drag = False
        self.tgt = None
        self.initial_vec = None
        self.undo_redo.take_snapshot()

    def deactivate(self):
        if self.drag:
            self._stop_rotate()