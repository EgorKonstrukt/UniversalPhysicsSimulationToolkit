import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui


class GearTool(BaseTool):
    name="Gear"
    icon_path="sprites/gui/tools/gear.png"
    def __init__(self,pm):
        super().__init__(pm)
        self.center=None
        self.settings_window=None
        self.teeth_entry=None
        self.module_entry=None
        self.thick_entry=None
        self.snap_cb=None

    def create_settings_window(self):
        win=pygame_gui.elements.UIWindow(rect=pygame.Rect(180,10,360,160),manager=self.ui_manager.manager,window_display_title="Gear Settings")
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,80,20),text="Teeth:",manager=self.ui_manager.manager,container=win)
        self.teeth_entry=pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(90,10,60,20),initial_text="20",manager=self.ui_manager.manager,container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(160,10,80,20),text="Module:",manager=self.ui_manager.manager,container=win)
        self.module_entry=pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(240,10,60,20),initial_text="4",manager=self.ui_manager.manager,container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,40,80,20),text="Thick:",manager=self.ui_manager.manager,container=win)
        self.thick_entry=pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(90,40,60,20),initial_text="1.0",manager=self.ui_manager.manager,container=win)
        self.snap_cb=pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10,70,200,20),text="Auto snap to another gear",manager=self.ui_manager.manager,container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,100,300,40),text="Click to place center. Drag to set angle.",manager=self.ui_manager.manager,container=win)
        self.settings_window=win

    def _involute_point(self,r,phi):
        x=r*(math.cos(phi)+phi*math.sin(phi))
        y=r*(math.sin(phi)-phi*math.cos(phi))
        return x,y

    def _generate_gear_outline(self,z,m):
        rb=m*z*0.5*math.cos(math.radians(20))
        ra=m*z*0.5+1*m
        rf=m*z*0.5-1.25*m
        pts=[]
        for tooth in range(z):
            base_ang=tooth*(2*math.pi/z)
            for side in (-1,1):
                for i in range(8):
                    t=i*0.07
                    px,py=self._involute_point(rb,t)
                    ang=base_ang+side*math.atan2(py,px)
                    R=math.hypot(px,py)
                    if R>ra: break
                    pts.append((math.cos(ang)*R,math.sin(ang)*R))
            pts.append((math.cos(base_ang)*ra,math.sin(base_ang)*ra))
            pts.append((math.cos(base_ang+2*math.pi/z)*ra,math.sin(base_ang+2*math.pi/z)*ra))
        return pts

    def _closest_gear(self,pos):
        best=None; dmin=999999
        for s in self.pm.space.shapes:
            if isinstance(s,pymunk.Poly) and hasattr(s,"_is_gear"):
                dx=s.body.position.x-pos[0]
                dy=s.body.position.y-pos[1]
                d=dx*dx+dy*dy
                if d<dmin:
                    dmin=d; best=s
        return best

    def _add_gear(self,pos,angle,z,m,thick):
        pts=self._generate_gear_outline(z,m)
        cx=sum(p[0] for p in pts)/len(pts)
        cy=sum(p[1] for p in pts)/len(pts)
        pts=[(p[0]-cx,p[1]-cy) for p in pts]
        mass=len(pts)*0.4
        body=pymunk.Body(mass,pymunk.moment_for_poly(mass,pts))
        body.position=pos
        body.angle=angle
        sh=pymunk.Poly(body,pts)
        sh.friction=0.9
        sh.elasticity=0.0
        sh._is_gear=True
        self.pm.space.add(body,sh)
        return sh

    def handle_event(self,event,world_pos):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            self.center=world_pos
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1 and self.center:
            try: z=int(self.teeth_entry.get_text())
            except: z=20
            try: m=float(self.module_entry.get_text())
            except: m=4
            try: thick=float(self.thick_entry.get_text())
            except: thick=1.0
            ang=math.atan2(world_pos[1]-self.center[1],world_pos[0]-self.center[0])
            pos=self.center
            if self.snap_cb.get_state():
                g=self._closest_gear(self.center)
                if g:
                    rz=g.radius if hasattr(g,"radius") else 0
                    r0=m*z*0.5
                    ang2=math.atan2(self.center[1]-g.body.position.y,self.center[0]-g.body.position.x)
                    pos=(g.body.position.x+math.cos(ang2)*(rz+r0),g.body.position.y+math.sin(ang2)*(rz+r0))
            self._add_gear(pos,ang,z,m,thick)
            self.center=None
