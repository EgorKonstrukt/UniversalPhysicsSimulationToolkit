import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.base_tool import BaseTool
import pygame_gui


class MoveTool(BaseTool):
    name = "Move"
    category = "Manipulation"
    icon_path = "sprites/gui/tools/move.png"

    def __init__(self,app):
        super().__init__(app)
        self.tgt = None
        self.drag = False
        self.offset = pymunk.Vec2d(0, 0)
        self.cb_center = None
        self.saved_body_type = None
        self.saved_mass = None
        self.saved_moment = None

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
        self.cb_center = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 10, 200, 20),
            text="Брать за центр массы",
            manager=self.ui_manager.manager,
            container=win
        )
        self.settings_window = win

    def handle_event(self, event, wpos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            info = self.app.physics_manager.space.point_query_nearest(wpos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.app.physics_manager.static_body else None
            if body and body in self.app.physics_manager.selected_bodies:
                pass
            else:
                self.app.physics_manager.clear_selection()
                if body and body.body_type == pymunk.Body.DYNAMIC:
                    self.tgt = body
                    self.offset = wpos - self.tgt.position if not self.cb_center.get_state() else pymunk.Vec2d(0, 0)
                    self.saved_body_type = self.tgt.body_type
                    self.saved_mass = self.tgt.mass
                    self.saved_moment = self.tgt.moment
                    self.tgt.body_type = pymunk.Body.KINEMATIC
                    self.drag = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag:
                self._stop_move()
        elif event.type == pygame.MOUSEMOTION and self.drag and self.tgt:
            self._move_to(wpos)

    def _move_to(self, wpos):
        self.tgt.position = wpos - self.offset

    def _stop_move(self):
        if self.tgt and self.saved_states:
            for i, b in enumerate(self.tgt):
                b.body_type, b.mass, b.moment = self.saved_states[i]
            self.drag = False
            self.tgt = None
            self.saved_states = None
            self.offsets = None
            if hasattr(self, 'undo_redo'):
                self.undo_redo.take_snapshot()

    def deactivate(self):
        if self.drag:
            self._stop_move()