import random
import pygame
import math
import pymunk
from UPST.config import config
from UPST.tools.base_tool import BaseTool
import pygame_gui


class MoveTool(BaseTool):
    name = "Move"
    category = "Manipulation"
    icon_path = "sprites/gui/tools/move.png"

    def __init__(self, app):
        super().__init__(app)
        self.tgt_bodies = []
        self.offsets = []
        self.saved_states = []
        self.drag = False
        self.cb_center = None

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
            clicked_body = info.shape.body if info and info.shape and info.shape.body != self.app.physics_manager.static_body else None
            if clicked_body and clicked_body in self.app.physics_manager.selected_bodies:
                self._start_drag(wpos)
            else:
                self.app.physics_manager.clear_selection()
                if clicked_body and clicked_body.body_type == pymunk.Body.DYNAMIC:
                    self.app.physics_manager.select_body(clicked_body)
                    self._start_drag(wpos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag:
                self._stop_move()
        elif event.type == pygame.MOUSEMOTION and self.drag:
            self._move_to(wpos)

    def _start_drag(self, wpos):
        self.tgt_bodies = list(self.app.physics_manager.selected_bodies)
        self.saved_states = []
        self.offsets = []
        use_center = self.cb_center.get_state() if self.cb_center else False
        for body in self.tgt_bodies:
            if body.body_type == pymunk.Body.DYNAMIC:
                self.saved_states.append((body.body_type, body.mass, body.moment))
                offset = pymunk.Vec2d(0, 0) if use_center else wpos - body.position
                self.offsets.append(offset)
                body.body_type = pymunk.Body.KINEMATIC
            else:
                self.saved_states.append(None)
                self.offsets.append(pymunk.Vec2d(0, 0))
        self.drag = True

    def _move_to(self, wpos):
        for i, body in enumerate(self.tgt_bodies):
            if self.saved_states[i] is not None:
                body.position = wpos - self.offsets[i]

    def _stop_move(self):
        for i, body in enumerate(self.tgt_bodies):
            if self.saved_states[i] is not None:
                orig_type, mass, moment = self.saved_states[i]
                body.body_type = orig_type
                body.mass = mass
                body.moment = moment
        self.drag = False
        self.tgt_bodies.clear()
        self.saved_states.clear()
        self.offsets.clear()
        if hasattr(self.app, 'undo_redo'):
            self.app.undo_redo.take_snapshot()

    def deactivate(self):
        if self.drag:
            self._stop_move()