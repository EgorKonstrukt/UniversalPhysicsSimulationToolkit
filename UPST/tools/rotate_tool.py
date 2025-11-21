import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class RotateTool(BaseTool):
    name="Rotate"
    icon_path="sprites/gui/tools/rotate.png"
    def __init__(self,pm):
        super().__init__(pm)
        self.tgt=None
        self.drag=False
        self.cb_center=None
        self.cb_lock=None
        self.start_angle=0
        self.start_vec=None

    def create_settings_window(self):
        win=pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200,10,260,130),
            manager=self.ui_manager.manager,
            window_display_title="Rotate Settings"
        )
        self.cb_center=pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10,10,200,20),
            text="Брать за центр массы",
            manager=self.ui_manager.manager,
            container=win
        )
        self.cb_lock=pygame_gui.elements.UICheckBox(
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
                self.start_angle=self.tgt.angle
                self.start_vec=(wpos-self.tgt.position)
                self.drag=True
                if self.cb_lock.get_state():
                    self.tgt.angular_velocity=0
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            if self.drag:self._stop_rotate()
        elif event.type==pygame.MOUSEMOTION and self.drag and self.tgt:
            self._rotate_to(wpos)

    def _rotate_to(self,wpos):
        v_now=(wpos-self.tgt.position)
        if v_now.length<1 or self.start_vec.length<1:return
        a0=math.atan2(self.start_vec.y,self.start_vec.x)
        a1=math.atan2(v_now.y,v_now.x)
        da=a1-a0
        self.tgt.angle=self.start_angle+da
        self.tgt.angular_velocity=da*12

    def _stop_rotate(self):
        if self.cb_lock.get_state():self.tgt.angular_velocity=0
        self.drag=False
        self.tgt=None

    def deactivate(self):
        if self.drag:self._stop_rotate()