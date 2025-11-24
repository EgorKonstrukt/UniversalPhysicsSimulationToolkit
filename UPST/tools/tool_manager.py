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
from UPST.tools.drag_tool import DragTool

from UPST.modules.undo_redo_manager import get_undo_redo

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
        self.undo_redo = get_undo_redo()

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
            PolyTool(self.pm),
            PolyhedronTool(self.pm),
            SpamTool(self.pm),
            HumanTool(self.pm),
            GearTool(self.pm),
        ]
        constraint_tools = [
            SpringTool(self.pm),
            PivotJointTool(self.pm),
            PinJointTool(self.pm)
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
            UIImage(relative_rect=pygame.Rect(135, y + 2, 40, 40), image_surface=pygame.image.load(icon_path),
                    manager=self.ui_manager.manager, container=panel)
            self.ui_manager.tool_buttons.append(btn)
            y += 45
            return btn

        add_section("Primitives")
        for name in ["Circle", "Rectangle", "Triangle", "Poly", "Polyhedron", "Spam", "Human", "Gear"]:
            btn = add_tool_btn(name, self.tools[name].icon_path)
            btn.tool_name = name
        add_section("Connections")
        for name in ["Spring", "PivotJoint", "PinJoint"]:
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
        self.stiffness = 200.0
        self.damping = 10.0
        self.rest_length = 0.0

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 300, 200),
            manager=self.ui_manager.manager,
            window_display_title="Spring Settings"
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Stiffness:", manager=self.ui_manager.manager, container=win)
        self.stiffness_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="200", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 40, 120, 20), text="Damping:", manager=self.ui_manager.manager, container=win)
        self.damping_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 40, 60, 20), initial_text="10", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 70, 120, 20), text="Rest Length:", manager=self.ui_manager.manager, container=win)
        self.rest_len_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 70, 60, 20), initial_text="auto", manager=self.ui_manager.manager, container=win)
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

                        rest_len_text = self.rest_len_entry.get_text().strip()
                        rest_len = self.first_body.position.get_distance(body.position) if rest_len_text == "auto" else float(rest_len_text)
                        stiffness = float(self.stiffness_entry.get_text() or "200")
                        damping = float(self.damping_entry.get_text() or "10")
                        spring = pymunk.DampedSpring(self.first_body, body, anchor1, anchor2, rest_len, stiffness, damping)
                        self.pm.space.add(spring)
                        self.undo_redo.take_snapshot()
                    except ValueError:
                        pass
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None


class PivotJointTool(BaseTool):
    name = "PivotJoint"
    icon_path = "sprites/gui/tools/pivot.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.first_body = None
        self.first_pos = None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 300, 130),
            manager=self.ui_manager.manager,
            window_display_title="Pivot Joint Settings"
        )
        self.collide_checkbox = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 10, 20, 20),
            text="Enable Collision",
            manager=self.ui_manager.manager,
            container=win
        )
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
                    pivot = pymunk.PivotJoint(self.first_body, body, self.first_pos)
                    pivot.collide_bodies = self.collide_checkbox.get_state()
                    self.pm.space.add(pivot)
                    self.undo_redo.take_snapshot()
                self.first_body = None

    def deactivate(self):
        self.first_body = None
        self.first_pos = None


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
    icon_path = "sprites/app/line.png"

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
            self.pm.static_lines.append(segment)
            self.undo_redo.take_snapshot()
            self.start_pos = None

    def draw_preview(self, screen, camera):
        if self.start_pos:
            start_screen = camera.world_to_screen(self.start_pos)
            end_screen = camera.world_to_screen(pygame.mouse.get_pos())
            pygame.draw.line(screen, (200, 200, 255), start_screen, end_screen, 2)

    def deactivate(self):
        self.start_pos = None






class PolyTool(BaseTool):
    name = "Poly"
    icon_path = "sprites/gui/tools/polygon.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.points = []
        self.preview_closed = False

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, 10, 300, 160),
            manager=self.ui_manager.manager,
            window_display_title="Poly Settings"
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Min vertices:", manager=self.ui_manager.manager, container=win)
        self.min_vertices_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="3", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 40, 120, 20), text="Friction:", manager=self.ui_manager.manager, container=win)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 40, 60, 20), initial_text="0.7", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 70, 120, 20), text="Elasticity:", manager=self.ui_manager.manager, container=win)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 70, 60, 20), initial_text="0.3", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.points.append(world_pos)
                synthesizer.play_frequency(300, 0.02, 'sine')
            elif event.button == 3 and len(self.points) >= int(self.min_vertices_entry.get_text() or "3"):
                self._finalize_polygon()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and len(self.points) >= int(self.min_vertices_entry.get_text() or "3"):
            self._finalize_polygon()

    def _finalize_polygon(self):
        if len(self.points) < 3: return
        try:
            friction = float(self.friction_entry.get_text() or "0.7")
            elasticity = float(self.elasticity_entry.get_text() or "0.3")
            vertices = [pymunk.Vec2d(x, y) for x, y in self.points]
            xs, ys = zip(*self.points)
            centroid = pymunk.Vec2d(sum(xs) / len(xs), sum(ys) / len(ys))
            local_vertices = [v - centroid for v in vertices]
            if self._signed_area(local_vertices) < 0:
                local_vertices.reverse()
            body = pymunk.Body(1, 100)
            body.position = centroid
            shape = pymunk.Poly(body, local_vertices, radius=0)
            shape.friction = friction
            shape.elasticity = elasticity
            self.pm.space.add(body, shape)
            self.undo_redo.take_snapshot()
        except Exception as e:
            traceback.print_exc()
        self.points.clear()

    def _signed_area(self, vertices):
        area = 0.0
        n = len(vertices)
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            area += (x2 - x1) * (y2 + y1)
        return -area

    def draw_preview(self, screen, camera):
        if not self.points: return
        pts = [camera.world_to_screen(p) for p in self.points]
        if len(pts) > 1:
            pygame.draw.lines(screen, (200, 200, 255), False, pts, 2)
        for p in pts:
            pygame.draw.circle(screen, (180, 180, 255), p, 3)
        if len(self.points) >= 3:
            pygame.draw.line(screen, (180, 255, 180), pts[-1], pts[0], 1)

    def deactivate(self):
        self.points.clear()





