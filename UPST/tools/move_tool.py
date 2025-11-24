import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui


class MoveTool(BaseTool):
    name="Move"
    icon_path="sprites/gui/tools/move.png"
    def __init__(self,pm):
        super().__init__(pm)
        self.tgt=None
        self.drag=False
        self.cb_center=None
        self.cb_no_rot=None
        self.saved_moi=None

    def create_settings_window(self):
        win=pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200,10,260,130),
            manager=self.ui_manager.manager,
            window_display_title="Move Settings"
        )
        self.cb_center=pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10,10,200,20),
            text="Брать за центр массы",
            manager=self.ui_manager.manager,
            container=win
        )
        self.cb_no_rot=pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10,35,200,20),
            text="Отключить вращение",
            manager=self.ui_manager.manager,
            container=win
        )
        self.settings_window=win

    def handle_event(self,event,wpos):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            info=self.pm.space.point_query_nearest(wpos,0,pymunk.ShapeFilter())
            body=info.shape.body if info and info.shape and info.shape.body!=self.pm.static_body else None
            if body:
                self.tgt=body
                if self.cb_no_rot.get_state():
                    self.saved_moi=self.tgt.moment
                    self.tgt.moment=float("inf")
                    self.tgt.angular_velocity=0
                self.drag=True
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            if self.drag:self._stop_move()
        elif event.type==pygame.MOUSEMOTION and self.drag and self.tgt:
            self._move_to(wpos)

    def _move_to(self,wpos):
        if self.cb_center.get_state():
            self.tgt.position=wpos
        else:
            v=(wpos-self.tgt.position)*8
            self.tgt.velocity=v

    def _stop_move(self):
        if self.cb_no_rot.get_state() and self.saved_moi and self.tgt:
            self.tgt.moment=self.saved_moi
        self.saved_moi=None
        self.drag=False
        self.tgt=None
        self.undo_redo.take_snapshot()

    def deactivate(self):
        if self.drag:self._stop_move()