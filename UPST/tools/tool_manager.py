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
from UPST.tools.gear_tool import GearTool
from UPST.tools.move_tool import MoveTool
from UPST.tools.rotate_tool import RotateTool
from UPST.tools.cut_tool import CutTool
from UPST.tools.script_tool import ScriptTool

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

    def is_mouse_on_ui(self):
        return self.ui_manager.manager.get_focus_set()

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
            CutTool(self.pm),
            ScriptTool(self.pm),
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
        if self.is_mouse_on_ui:
            return
        if self.current_tool and hasattr(self.current_tool, 'handle_input'):
            self.current_tool.handle_input(world_pos)

    def handle_event(self, event, world_pos):
        if self.is_mouse_on_ui:
            return
        if self.current_tool:
            self.current_tool.handle_event(event, world_pos)

    def draw_preview(self, screen, camera):
        if self.current_tool and hasattr(self.current_tool, 'draw_preview'):
            self.current_tool.draw_preview(screen, camera)

    def create_tool_buttons(self):
        if not self.ui_manager:
            return
        panel = UIPanel(relative_rect=pygame.Rect(5, 50, 200, 940), manager=self.ui_manager.manager)
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
        btn = add_tool_btn("ScriptTool", self.tools["ScriptTool"].icon_path)
        btn.tool_name = "ScriptTool"

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









