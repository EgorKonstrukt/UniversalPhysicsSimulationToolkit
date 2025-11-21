import pymunk, pygame, math, random, traceback
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIImage, UICheckBox

from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
import pygame_gui

from UPST.tools.laser_processor import LaserProcessor
from UPST.tools.base_tool import BaseTool

from UPST.tools.circle_tool import CircleTool
from UPST.tools.rectanlge_tool import RectangleTool
from UPST.tools.triangle_tool import TriangleTool
from UPST.tools.polyhedron_tool import PolyhedronTool
from UPST.tools.spam_tool import SpamTool
from UPST.tools.human_tool import HumanTool

class ToolSystem:
    def __init__(self, physics_manager, sound_manager):
        self.pm = physics_manager
        self.sm = sound_manager
        self.ui_manager = None
        self.input_handler = None
        self.tools = {}
        self.current_tool = None
        self._pending_tools = []
        self._register_tools()


    def set_ui_manager(self, ui_manager):
        self.ui_manager = ui_manager
        self._create_tool_settings()

    def set_input_handler(self, input_handler):
        self.input_handler = input_handler

    def _register_tools(self):
        from UPST.tools.laser_tool import LaserTool
        self.laser_processor = LaserProcessor(self.pm)
        spawn_tools = [
            CircleTool(self.pm),
            RectangleTool(self.pm),
            TriangleTool(self.pm),
            PolyhedronTool(self.pm),
            SpamTool(self.pm),
            HumanTool(self.pm),
            GearTool(self.pm),
        ]
        constraint_tools = [
            SpringTool(self.pm),
            PivotTool(self.pm),
            RigidTool(self.pm)
        ]
        special_tools = [
            ExplosionTool(self.pm),
            StaticLineTool(self.pm),
            LaserTool(self.pm, self.laser_processor),
            DragTool(self.pm),
            MoveTool(self.pm),
            RotateTool(self.pm),
            CutTool(self.pm)
        ]

        self._pending_tools = spawn_tools + constraint_tools + special_tools

    def _create_tool_settings(self):
        if not self.ui_manager:
            return
        for tool in self._pending_tools:
            tool.set_ui_manager(self.ui_manager)
            tool.create_settings_window()
            self.tools[tool.name] = tool
        self._pending_tools.clear()

    def activate_tool(self, tool_name):
        if self.current_tool:
            self.current_tool.deactivate()
        self.current_tool = self.tools[tool_name]
        self.current_tool.activate()
        synthesizer.play_frequency(1630, duration=0.03, waveform='sine')

    def handle_input(self, world_pos):
        if self.current_tool and hasattr(self.current_tool, 'handle_input'):
            self.current_tool.handle_input(world_pos)

    def handle_event(self, event, world_pos):
        if self.current_tool:
            self.current_tool.handle_event(event, world_pos)

    def draw_preview(self, screen, camera):
        if self.current_tool and hasattr(self.current_tool, 'draw_preview'):
            self.current_tool.draw_preview(screen, camera)

    def create_tool_buttons(self):
        if not self.ui_manager:
            return
        panel = UIPanel(relative_rect=pygame.Rect(5, 50, 200, 840), manager=self.ui_manager.manager)
        y = 0

        def add_section(text):
            nonlocal y
            UILabel(relative_rect=pygame.Rect(0, y, 190, 25), text=f"-- {text} --", manager=self.ui_manager.manager,
                    container=panel)
            y += 30

        def add_tool_btn(name, icon_path):
            nonlocal y
            btn = UIButton(relative_rect=pygame.Rect(10, y, 120, 45), text=name, manager=self.ui_manager.manager,
                           container=panel)
            # UIImage(relative_rect=pygame.Rect(135, y + 2, 40, 40), image_surface=pygame.image.load(icon_path),
            #         manager=self.ui_manager.manager, container=panel)
            self.ui_manager.tool_buttons.append(btn)
            y += 45
            return btn

        add_section("Primitives")
        for name in ["Circle", "Rectangle", "Triangle", "Polyhedron", "Spam", "Human", "Gear"]:
            btn = add_tool_btn(name, self.tools[name].icon_path)
            btn.tool_name = name
        add_section("Connections")
        for name in ["Spring", "Pivot", "Rigid"]:
            btn = add_tool_btn(name, self.tools[name].icon_path)
            btn.tool_name = name
        add_section("Tools")
        btn = add_tool_btn("Explosion", self.tools["Explosion"].icon_path)
        btn.tool_name = "Explosion"
        btn = add_tool_btn("StaticLine", self.tools["StaticLine"].icon_path)
        btn.tool_name = "StaticLine"
        btn = add_tool_btn("Laser", self.tools["Laser"].icon_path)
        btn.tool_name = "Laser"
        btn = add_tool_btn("Drag", self.tools["Drag"].icon_path)
        btn.tool_name = "Drag"
        btn = add_tool_btn("Move", self.tools["Move"].icon_path)
        btn.tool_name = "Move"
        btn = add_tool_btn("Rotate", self.tools["Rotate"].icon_path)
        btn.tool_name = "Rotate"
        btn = add_tool_btn("Cut", self.tools["Cut"].icon_path)
        btn.tool_name = "Cut"

class SpringTool(BaseTool):
    name = "Spring"
    icon_path = "sprites/gui/tools/spring.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.first_body = None
        self.first_pos = None

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
                    rest_len = self.first_body.position.get_distance(body.position)
                    spring = pymunk.DampedSpring(self.first_body, body, anchor1, anchor2, rest_len, 200, 10)
                    self.pm.space.add(spring)
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None


class PivotTool(BaseTool):
    name = "Pivot"
    icon_path = "sprites/gui/tools/pivot.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.first_body = None
        self.first_pos = None

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
                    pivot = pymunk.PivotJoint(self.first_body, body, self.first_pos)
                    self.pm.space.add(pivot)
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None


class RigidTool(BaseTool):
    name = "Rigid"
    icon_path = "sprites/gui/tools/rigid.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.first_body = None
        self.first_pos = None

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
                    rigid = pymunk.PinJoint(self.first_body, body, anchor1, anchor2)
                    self.pm.space.add(rigid)
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None


class ExplosionTool(BaseTool):
    name = "Explosion"
    icon_path = "sprites/gui/tools/explosion.png"

    def handle_input(self, world_pos):
        for body in self.pm.space.bodies:
            if body == self.pm.static_body:
                continue
            dist = (body.position - world_pos).length
            if dist < 100:
                impulse = (world_pos - body.position) * (1000 / max(dist, 1))
                body.apply_impulse_at_local_point(impulse)


class StaticLineTool(BaseTool):
    name = "StaticLine"
    icon_path = "sprites/gui/tools/line.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.start_pos = None

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.start_pos = world_pos
            synthesizer.play_frequency(150, duration=0.1, waveform='sine')
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.start_pos:
            end_pos = world_pos
            synthesizer.play_frequency(120, duration=0.1, waveform='sine')
            segment = pymunk.Segment(self.pm.static_body, self.start_pos, end_pos, 5)
            segment.friction = 1.0
            segment.elasticity = 0.5
            self.pm.space.add(segment)
            self.start_pos = None

    def draw_preview(self, screen, camera):
        if self.start_pos:
            start_screen = camera.world_to_screen(self.start_pos)
            end_screen = camera.world_to_screen(pygame.mouse.get_pos())
            pygame.draw.line(screen, (200, 200, 255), start_screen, end_screen, 2)

    def deactivate(self):
        self.start_pos = None


class DragTool(BaseTool):
    name="Drag"
    icon_path="sprites/gui/tools/drag.png"
    def __init__(self,pm):
        super().__init__(pm)
        self.mb=None
        self.tgt=None
        self.pj=None
        self.ds=None
        self.dragging=False
        self.stiff_entry=None
        self.damp_entry=None
        self.rest_entry=None
        self.cb_no_rot=None
        self.cb_center=None
        self.cb_show_force=None
        self.last_force=0
        self.saved_moi=None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, 10, 340, 220),
            manager=self.ui_manager.manager,
            window_display_title="Drag Settings"
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, 80, 20),
            text="Stiff:",
            manager=self.ui_manager.manager,
            container=win
        )
        self.stiff_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(95, 10, 80, 20),
            initial_text="8000",
            manager=self.ui_manager.manager,
            container=win
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 40, 80, 20),
            text="Damp:",
            manager=self.ui_manager.manager,
            container=win
        )
        self.damp_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(95, 40, 80, 20),
            initial_text="200",
            manager=self.ui_manager.manager,
            container=win
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 70, 80, 20),
            text="Rest:",
            manager=self.ui_manager.manager,
            container=win
        )
        self.rest_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(95, 70, 80, 20),
            initial_text="0",
            manager=self.ui_manager.manager,
            container=win
        )

        self.cb_no_rot = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 100, 25, 25),
            text="Отключить вращение",
            manager=self.ui_manager.manager,
            container=win
        )

        self.cb_center = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 125, 25, 25),
            text="Брать за центр массы",
            manager=self.ui_manager.manager,
            container=win
        )

        self.cb_show_force = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 150, 25, 25),
            text="Отображать силу",
            manager=self.ui_manager.manager,
            container=win
        )

        self.settings_window = win

    def _make_mouse_body(self,pos):
        b=pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        b.position=pos
        self.pm.space.add(b)
        return b

    def _start_drag(self,wpos,info):
        self.tgt=info.shape.body
        self.mb=self._make_mouse_body(wpos)
        if self.cb_center.get_state():
            local_anchor=(0,0)
        else:
            local_anchor=self.tgt.world_to_local(wpos)
        k=float(self.stiff_entry.get_text()) if self.stiff_entry else 8000
        d=float(self.damp_entry.get_text()) if self.damp_entry else 200
        rest=float(self.rest_entry.get_text()) if self.rest_entry else 0
        self.pj=pymunk.PivotJoint(self.mb,self.tgt,(0,0),local_anchor)
        self.ds=pymunk.DampedSpring(self.mb,self.tgt,(0,0),local_anchor,rest,k,d)
        self.pm.space.add(self.pj,self.ds)
        if self.cb_no_rot.get_state():
            self.saved_moi=self.tgt.moment
            self.tgt.moment=float("inf")
            self.tgt.angular_velocity=0
        self.dragging=True
        synthesizer.play_frequency(400,0.05,'sine')

    def _stop_drag(self):
        for j in (self.pj,self.ds):
            if j:
                try:self.pm.space.remove(j)
                except:pass
        self.pj=None
        self.ds=None
        if self.mb:
            try:self.pm.space.remove(self.mb)
            except:pass
        self.mb=None
        if self.cb_no_rot.get_state() and self.saved_moi and self.tgt:
            self.tgt.moment=self.saved_moi
        self.saved_moi=None
        self.tgt=None
        self.dragging=False
        synthesizer.play_frequency(250,0.04,'sine')

    def handle_event(self,event,wpos):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            info=self.pm.space.point_query_nearest(wpos,0,pymunk.ShapeFilter())
            body=info.shape.body if info and info.shape and info.shape.body!=self.pm.static_body else None
            if body:self._start_drag(wpos,info)
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            if self.dragging:self._stop_drag()
        elif event.type==pygame.MOUSEMOTION and self.dragging and self.mb:
            self.mb.position=wpos

    def draw_preview(self,screen,camera):
        if self.dragging and self.tgt and self.mb:
            a=camera.world_to_screen(self.mb.position)
            b=camera.world_to_screen(self.tgt.position)
            pygame.draw.line(screen,(200,200,255),a,b,2)
            pygame.draw.circle(screen,(180,180,255),a,5)
            if self.cb_show_force.get_state():
                f=(self.mb.position-self.tgt.position).length
                self.last_force=f
                font=pygame.font.SysFont("Arial",16)
                t=font.render(f"{int(f)}",True,(220,220,255))
                screen.blit(t,(a[0]+10,a[1]-10))

    def deactivate(self):
        if self.dragging:self._stop_drag()


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

    def deactivate(self):
        if self.drag:self._stop_move()



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


class CutTool(BaseTool):
    name = "Cut"
    icon_path = "sprites/gui/tools/cut.png"
    def __init__(self, pm):
        super().__init__(pm)
        self.start_pos=None
        self.thickness_entry=None
        self.remove_circles_cb=None
        self.keep_small_cb=None
        self._tmp_preview=None
    def create_settings_window(self):
        win=pygame_gui.elements.UIWindow(rect=pygame.Rect(200,10,360,160),manager=self.ui_manager.manager,window_display_title="Cut Settings")
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,120,20),text="Толщина (px):",manager=self.ui_manager.manager,container=win)
        self.thickness_entry=pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(130,10,80,20),initial_text="4",manager=self.ui_manager.manager,container=win)
        self.remove_circles_cb=pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10,40,240,20),text="Удалять круги при пересечении",manager=self.ui_manager.manager,container=win)
        self.keep_small_cb=pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10,65,240,20),text="Оставлять мелкие фрагменты",manager=self.ui_manager.manager,container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,95,320,40),text="Рисуйте линию — объекты, пересёкшиеся линией, будут разрезаны/удалены.",manager=self.ui_manager.manager,container=win)
        self.settings_window=win
    def _seg_seg_intersection(self,a1,a2,b1,b2):
        ax,ay=a1; bx,by=a2; cx,cy=b1; dx,dy=b2
        r=(bx-ax,by-ay); s=(dx-cx,dy-cy)
        denom=r[0]*s[1]-r[1]*s[0]
        if abs(denom)<1e-8: return None
        t=((cx-ax)*s[1]-(cy-ay)*s[0])/denom
        u=((cx-ax)*r[1]-(cy-ay)*r[0])/denom
        if 0<=t<=1 and 0<=u<=1:
            return (ax+t*r[0], ay+t*r[1])
        return None
    def _seg_circle_intersect(self,a,b,center,r):
        ax,ay=a; bx,by=b; cx,cy=center
        vx=bx-ax; vy=by-ay; ux=ax-cx; uy=ay-cy
        a_coef=vx*vx+vy*vy
        if a_coef==0: return (ux*ux+uy*uy)<=r*r
        b_coef=2*(ux*vx+uy*vy); c_coef=ux*ux+uy*uy-r*r
        disc=b_coef*b_coef-4*a_coef*c_coef
        if disc<0: return False
        sq=math.sqrt(disc); denom=2*a_coef
        if denom==0: return False
        t1=(-b_coef-sq)/denom; t2=(-b_coef+sq)/denom
        return (0<=t1<=1) or (0<=t2<=1)
    def _seg_circle_intersection_points(self,a,b,center,r):
        ax,ay=a; bx,by=b; cx,cy=center
        vx=bx-ax; vy=by-ay; ux=ax-cx; uy=ay-cy
        a_coef=vx*vx+vy*vy
        if a_coef==0:
            return []
        b_coef=2*(ux*vx+uy*vy); c_coef=ux*ux+uy*uy-r*r
        disc=b_coef*b_coef-4*a_coef*c_coef
        if disc<0: return []
        sq=math.sqrt(disc); denom=2*a_coef
        if denom==0: return []
        t1=(-b_coef-sq)/denom; t2=(-b_coef+sq)/denom
        pts=[]
        for t in (t1,t2):
            if 0<=t<=1:
                pts.append((ax+t*vx, ay+t*vy))
        return pts
    def _point_line_dist(self,p,a,b):
        ax,ay=a; bx,by=b; px,py=p
        lx=bx-ax; ly=by-ay; l2=lx*lx+ly*ly
        if l2==0: return math.hypot(px-ax,py-ay)
        t=max(0,min(1,((px-ax)*lx+(py-ay)*ly)/l2))
        proj=(ax+t*lx, ay+t*ly)
        return math.hypot(px-proj[0], py-proj[1])
    def _polygon_world_pts(self,poly):
        return [poly.body.local_to_world(v) for v in poly.get_vertices()]
    def _area_centroid(self,pts):
        a=0; cx=0; cy=0
        for i in range(len(pts)):
            x1,y1=pts[i]; x2,y2=pts[(i+1)%len(pts)]
            cross=x1*y2-x2*y1; a+=cross; cx+=(x1+x2)*cross; cy+=(y1+y2)*cross
        a=0.5*a
        if abs(a)<1e-8: return 0,(pts[0][0],pts[0][1])
        cx=cx/(6*a); cy=cy/(6*a)
        return abs(a),(cx,cy)
    def _create_poly_body(self,pts,proto_shape):
        area,cent=self._area_centroid(pts)
        if area<1e-2: return None
        local_pts=[(p[0]-cent[0], p[1]-cent[1]) for p in pts]
        mass=area/100
        if mass<=0: mass=0.001
        body=pymunk.Body(mass, pymunk.moment_for_poly(mass, local_pts))
        body.position=cent
        shape=pymunk.Poly(body, local_pts)
        shape.friction=getattr(proto_shape,"friction",0.7)
        shape.elasticity=getattr(proto_shape,"elasticity",0.5)
        shape.color=getattr(proto_shape,"color",(200,200,200,255))
        return body,shape
    def _remove_shape_and_maybe_body(self,shape):
        b=shape.body
        try:
            if shape in self.pm.space.shapes: self.pm.space.remove(shape)
        except Exception: pass
        try:
            if len(b.shapes)==0 and b in self.pm.space.bodies:
                try: self.pm.space.remove(b)
                except Exception: pass
        except Exception: pass
    def _split_poly_by_segment(self,poly,a,b):
        pts=self._polygon_world_pts(poly)
        inters=[]
        for i in range(len(pts)):
            p1=pts[i]; p2=pts[(i+1)%len(pts)]
            ip=self._seg_seg_intersection(a,b,p1,p2)
            if ip: inters.append((i,ip))
        if len(inters)!=2: return None
        (i1,ip1),(i2,ip2)=inters
        if i2<i1: i1,ip1,i2,ip2=i2,ip2,i1,ip1
        poly1=[]; poly1.extend(pts[i1+1:i2+1]); poly1.insert(0,ip1); poly1.append(ip2)
        poly2=[]; poly2.extend(pts[i2+1:]+pts[:i1+1]); poly2.insert(0,ip2); poly2.append(ip1)
        return poly1,poly2
    def _split_circle_by_segment(self, circle_shape, a, b):
        center = circle_shape.body.position; r = circle_shape.radius
        pts = self._seg_circle_intersection_points(a,b,center,r)
        if len(pts)!=2: return None
        p1,p2 = pts
        cx,cy=center
        ang1=math.atan2(p1[1]-cy, p1[0]-cx); ang2=math.atan2(p2[1]-cy, p2[0]-cx)
        def norm(a): return (a+2*math.pi)%(2*math.pi)
        a1=norm(ang1); a2=norm(ang2)
        delta1=(a2-a1)%(2*math.pi); delta2=(a1-a2)%(2*math.pi)
        def make_arc(start,delta):
            samples=max(20, int(delta/(math.pi/20)))
            pts=[(cx+math.cos(start+i*(delta/samples))*r, cy+math.sin(start+i*(delta/samples))*r) for i in range(1,samples)]
            return pts
        arc1 = make_arc(a1,delta1)
        poly1 = [p1] + arc1 + [p2]
        arc2 = make_arc(a2,delta2)
        poly2 = [p2] + arc2 + [p1]
        return [poly1, poly2]
    def _safe_add_body_shape(self,body,shape):
        try:
            self.pm.space.add(body,shape)
            return True
        except Exception:
            try:
                if body in self.pm.space.bodies:
                    try: self.pm.space.remove(body)
                    except Exception: pass
            except Exception: pass
            try:
                if shape in self.pm.space.shapes:
                    try: self.pm.space.remove(shape)
                    except Exception: pass
            except Exception: pass
            return False
    def _process_cut(self,a,b,thickness):
        to_remove_shapes=[]; to_add=[]
        for shape in list(self.pm.space.shapes):
            if shape.body==self.pm.static_body: continue
            if isinstance(shape,pymunk.Segment):
                p1=shape.a; p2=shape.b
                if self._seg_seg_intersection(a,b,p1,p2): to_remove_shapes.append(shape)
            elif isinstance(shape,pymunk.Circle):
                if self._seg_circle_intersect(a,b,shape.body.position,shape.radius):
                    if self.remove_circles_cb.get_state():
                        to_remove_shapes.append(shape)
                    else:
                        res=self._split_circle_by_segment(shape,a,b)
                        if res:
                            for pts in res:
                                new=self._create_poly_body(pts,shape)
                                if new: to_add.append(new)
                            to_remove_shapes.append(shape)
                        else:
                            to_remove_shapes.append(shape)
            elif isinstance(shape,pymunk.Poly):
                res=self._split_poly_by_segment(shape,a,b)
                if res:
                    p1_pts,p2_pts=res
                    new1=self._create_poly_body(p1_pts,shape)
                    new2=self._create_poly_body(p2_pts,shape)
                    if new1: to_add.append(new1)
                    if new2: to_add.append(new2)
                    to_remove_shapes.append(shape)
                else:
                    mind=min(self._point_line_dist(v,a,b) for v in self._polygon_world_pts(shape))
                    if mind<=thickness: to_remove_shapes.append(shape)
        for c in list(self.pm.space.constraints):
            a1=c.a.local_to_world(getattr(c,"anchor_a",(0,0))); a2=c.b.local_to_world(getattr(c,"anchor_b",(0,0)))
            if self._point_line_dist(a1,a,b)<=thickness or self._point_line_dist(a2,a,b)<=thickness:
                try: self.pm.space.remove(c)
                except: pass
        for sh in to_remove_shapes:
            try:
                self._remove_shape_and_maybe_body(sh)
            except Exception: pass
        for body,shape in to_add:
            added=self._safe_add_body_shape(body,shape)
            if not added and self.keep_small_cb and self.keep_small_cb.get_state():
                try:
                    if body in self.pm.space.bodies:
                        try: self.pm.space.remove(body)
                        except Exception: pass
                except Exception: pass
    def handle_event(self,event,world_pos):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            self.start_pos=world_pos; self._tmp_preview=(world_pos,world_pos)
        elif event.type==pygame.MOUSEMOTION and self.start_pos:
            self._tmp_preview=(self.start_pos,world_pos)
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1 and self.start_pos:
            a=self.start_pos; b=world_pos
            try: thickness=float(self.thickness_entry.get_text()) if self.thickness_entry else 4.0
            except: thickness=4.0
            self._process_cut(a,b,thickness)
            self.start_pos=None; self._tmp_preview=None
            synthesizer.play_frequency(300,duration=0.05,waveform='sine')
    def draw_preview(self,screen,camera):
        seg=self._tmp_preview
        if not seg: return
        a_screen=camera.world_to_screen(seg[0]); b_screen=camera.world_to_screen(seg[1])
        try: w=int(float(self.thickness_entry.get_text()) if self.thickness_entry else 4)
        except: w=4
        pygame.draw.line(screen,(255,100,100),a_screen,b_screen,w)


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
