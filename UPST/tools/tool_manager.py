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
        return bool(self.ui_manager.manager.get_focus_set())

    def set_ui_manager(self, ui_manager):
        self.ui_manager = ui_manager
        self._register_tool_settings()

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
            GearTool(self.pm),
            ChainTool(self.pm),
            PlaneTool(self.pm),
        ]
        constraint_tools = [
            SpringTool(self.pm),
            PivotJointTool(self.pm),
            PinJointTool(self.pm),
            FixateTool(self.pm)
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

    def _register_tool_settings(self):
        if not self.ui_manager:
            return
        for tool in self._pending_tools:
            tool.set_ui_manager(self.ui_manager)
            self.tools[tool.name] = tool
        self._pending_tools.clear()

    def activate_tool(self, tool_name):
        if self.current_tool:
            self.current_tool.deactivate()
        self.current_tool = self.tools[tool_name]
        if not hasattr(self.current_tool, 'settings_window') or self.current_tool.settings_window is None:
            self.current_tool.create_settings_window()
        self.current_tool.activate()
        synthesizer.play_frequency(1630, duration=0.03, waveform='sine')

    def handle_input(self, world_pos):
        if self.is_mouse_on_ui():
            return
        if self.current_tool and hasattr(self.current_tool, 'handle_input'):
            self.current_tool.handle_input(world_pos)

    def handle_event(self, event, world_pos):
        if event.type == pygame_gui.UI_WINDOW_CLOSE:
            # Пропускаем, чтобы инструмент сам обработал
            pass
        elif self.is_mouse_on_ui():
            return
        if self.current_tool:
            self.current_tool.handle_event(event, world_pos)

    def draw_preview(self, screen, camera):
        if self.current_tool and hasattr(self.current_tool, 'draw_preview'):
            self.current_tool.draw_preview(screen, camera)

    def create_tool_buttons(self):
        if not self.ui_manager: return
        bs, pad, x0 = 50, 1, 10
        tip_delay = getattr(config, 'TOOLTIP_DELAY', 0.1)
        y = 0
        col = 0
        items = []

        def tt(name):
            return getattr(self.tools[name], 'tooltip', name)

        def add_section(text):
            nonlocal y, col
            items.append(("label", text, y))
            y += 30
            col = 0

        def add_btn(name, icon):
            nonlocal y, col
            x = x0 + col * (bs + pad)
            items.append(("btn", name, icon, x, y))
            col += 1
            if col > 1: col = 0;y += bs + pad

        add_section("Primitives")
        for n in ["Circle", "Rectangle", "Triangle", "Poly", "Polyhedron", "Spam", "Gear", "Chain", "Plane"]:
            add_btn(n, self.tools[n].icon_path)
        if col: y += bs + pad;col = 0
        add_section("Connections")
        for n in ["Spring", "PivotJoint", "PinJoint", "Fixate"]:
            add_btn(n, self.tools[n].icon_path)
        if col: y += bs + pad;col = 0
        add_section("Tools")
        for n in ["Explosion", "StaticLine", "Laser", "Drag", "Move", "Rotate", "Cut", "ScriptTool"]:
            add_btn(n, self.tools[n].icon_path)
        panel = UIPanel(relative_rect=pygame.Rect(5, 50, 75+bs, y + 10), manager=self.ui_manager.manager)
        for it in items:
            if it[0] == "label":
                UILabel(relative_rect=pygame.Rect(0, it[2], 190, 25),
                        text=f"-- {it[1]} --", manager=self.ui_manager.manager, container=panel)
            else:
                _, name, icon, x, y = it
                tip = tt(name)
                btn = UIButton(relative_rect=pygame.Rect(x, y, bs, bs), text="",
                               manager=self.ui_manager.manager, container=panel)
                img = UIImage(relative_rect=pygame.Rect(x + 2, y + 2, bs - 4, bs - 4),
                              image_surface=pygame.image.load(icon),
                              manager=self.ui_manager.manager, container=panel)
                btn.set_tooltip(tip, delay=tip_delay)
                img.set_tooltip(tip, delay=tip_delay)
                btn.tool_name = name
                self.ui_manager.tool_buttons.append(btn)


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


class ChainTool(BaseTool):
    name = "Chain"
    icon_path = "sprites/gui/tools/chain.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.start_pos = None
        self.start_body = None
        self.preview_points = []
        self.segment_length = 15.0
        self.segment_mass = 1.0
        self.segment_radius = 3.0
        self.friction = 0.7
        self.elasticity = 0.3
        self.linked_collision = False
        self.limit_segments = 50

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 320, 320),
            manager=self.ui_manager.manager,
            window_display_title="Chain Settings"
        )
        labels = ["Segment Length:", "Segment Mass:", "Radius:", "Friction:", "Elasticity:", "Max Segments:"]
        defaults = ["15", "1", "3", "0.7", "0.3", "50"]
        entries = []
        y = 10
        for label_text, default in zip(labels, defaults):
            pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, y, 140, 20), text=label_text, manager=self.ui_manager.manager, container=win)
            entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(160, y, 60, 20), initial_text=default, manager=self.ui_manager.manager, container=win)
            entries.append(entry)
            y += 30
        self.length_entry, self.mass_entry, self.radius_entry, self.friction_entry, self.elasticity_entry, self.max_seg_entry = entries
        self.collision_checkbox = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, y, 20, 20),
            text="Enable segment collisions",
            manager=self.ui_manager.manager,
            container=win
        )
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.start_pos = pymunk.Vec2d(*world_pos)  # <-- wrap here
            info = self.pm.space.point_query_nearest(world_pos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
            self.start_body = body
            synthesizer.play_frequency(180, 0.05, 'sine')
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.start_pos:
            end_pos = pymunk.Vec2d(*world_pos)
            self._create_chain(self.start_pos, end_pos)
            self.start_pos = None
            self.start_body = None
            synthesizer.play_frequency(150, 0.05, 'sine')

    def _create_chain(self, p1, p2):
        try:
            seg_len = float(self.length_entry.get_text() or "15")
            mass = float(self.mass_entry.get_text() or "1")
            radius = float(self.radius_entry.get_text() or "3")
            friction = float(self.friction_entry.get_text() or "0.7")
            elasticity = float(self.elasticity_entry.get_text() or "0.3")
            max_segs = int(self.max_seg_entry.get_text() or "50")
            enable_collision = self.collision_checkbox.get_state()
            linked_collision = self.linked_collision
        except ValueError:
            return

        direction = p2 - p1
        dist = direction.length
        if dist == 0:
            return

        segment_count = min(max(2, int(dist / seg_len)), max_segs)
        step = direction / segment_count
        points = [p1 + step * i for i in range(segment_count + 1)]

        bodies = []
        shapes = []
        constraints = []

        for i, pos in enumerate(points):
            body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, radius))
            body.position = pos
            shape = pymunk.Circle(body, radius)
            shape.friction = friction
            shape.elasticity = elasticity
            bodies.append(body)
            shapes.append(shape)

        self.pm.space.add(*bodies, *shapes)

        for i in range(len(bodies) - 1):
            joint = pymunk.PinJoint(bodies[i], bodies[i + 1], (0, 0), (0, 0))
            joint.collide_bodies = enable_collision
            constraints.append(joint)

        self.pm.space.add(*constraints)

        if self.start_body:
            anchor = self.start_body.world_to_local(p1)
            joint = pymunk.PinJoint(self.start_body, bodies[0], anchor, (0, 0))
            joint.collide_bodies = False
            self.pm.space.add(joint)
            constraints.append(joint)

        info_end = self.pm.space.point_query_nearest(p2, radius, pymunk.ShapeFilter())
        end_body = info_end.shape.body if info_end and info_end.shape and info_end.shape.body != self.pm.static_body else None
        if end_body and end_body not in bodies:
            anchor = end_body.world_to_local(p2)
            joint = pymunk.PinJoint(end_body, bodies[-1], anchor, (0, 0))
            joint.collide_bodies = False
            self.pm.space.add(joint)
            constraints.append(joint)

        self.undo_redo.take_snapshot()

    def draw_preview(self, screen, camera):
        if not self.start_pos:
            return
        mouse_pos = pygame.mouse.get_pos()
        world_mouse = pymunk.Vec2d(*camera.screen_to_world(mouse_pos))
        start = pymunk.Vec2d(*self.start_pos)
        direction = world_mouse - start
        if direction.length == 0:
            return

        try:
            seg_len = float(self.length_entry.get_text() or "15")
            max_segs = int(self.max_seg_entry.get_text() or "50")
        except ValueError:
            return

        segment_count = min(max(2, int(direction.length / seg_len)), max_segs)
        step = direction / segment_count
        points = [start + step * i for i in range(segment_count + 1)]
        screen_points = [camera.world_to_screen((p.x, p.y)) for p in points]
        pygame.draw.lines(screen, (180, 200, 255), False, screen_points, 2)
        for p in screen_points:
            pygame.draw.circle(screen, (180, 180, 255), p, 3)

    def deactivate(self):
        self.start_pos = None
        self.start_body = None



class FixateTool(BaseTool):
    name = "Fixate"
    icon_path = "sprites/gui/tools/fixate.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.first_body = None
        self.first_anchor = None
        self.distance = 0.0

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 300, 130),
            manager=self.ui_manager.manager,
            window_display_title="Fixate Settings"
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Distance:", manager=self.ui_manager.manager, container=win)
        self.distance_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="0", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        info = self.pm.space.point_query_nearest(world_pos, 0, pymunk.ShapeFilter())
        body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
        if self.first_body is None:
            if body:
                self.first_body = body
                self.first_anchor = self.first_body.world_to_local(world_pos)
                synthesizer.play_frequency(300, duration=0.03, waveform='sine')
        else:
            target_body = body if body else self.pm.static_body
            target_anchor = world_pos if target_body == self.pm.static_body else target_body.world_to_local(world_pos)
            try:
                dist_text = self.distance_entry.get_text().strip()
                dist = float(dist_text) if dist_text not in ("", "auto") else 0.0
                # PinJoint для позиции
                pin = pymunk.PinJoint(self.first_body, target_body, self.first_anchor, target_anchor)
                pin.distance = dist
                # RotaryLimitJoint для полной блокировки поворота
                angle = self.first_body.angle
                rot = pymunk.RotaryLimitJoint(self.first_body, target_body, angle, angle)
                self.pm.space.add(pin, rot)
                self.undo_redo.take_snapshot()
                synthesizer.play_frequency(400, duration=0.04, waveform='sine')
            except Exception:
                pass
            self.first_body = None
            self.first_anchor = None

    def deactivate(self):
        self.first_body = None
        self.first_anchor = None

class PlaneTool(BaseTool):
    name = "Plane"
    icon_path = "sprites/gui/tools/plane.png"

    def __init__(self, pm):
        super().__init__(pm)
        self.start_pos = None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(210, 10, 300, 100),
            manager=self.ui_manager.manager,
            window_display_title="Plane Settings"
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Friction:", manager=self.ui_manager.manager, container=win)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="1.0", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 40, 120, 20), text="Elasticity:", manager=self.ui_manager.manager, container=win)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 40, 60, 20), initial_text="0.0", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.start_pos = pymunk.Vec2d(*world_pos)
            synthesizer.play_frequency(200, duration=0.05, waveform='sine')
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.start_pos:
            end_pos = pymunk.Vec2d(*world_pos)
            self._create_plane(self.start_pos, end_pos)
            self.start_pos = None

    def _create_plane(self, p1, p2):
        try:
            friction = float(self.friction_entry.get_text() or "1.0")
            elasticity = float(self.elasticity_entry.get_text() or "0.0")
        except ValueError:
            return

        direction = (p2 - p1)
        if direction.length == 0:
            normal = pymunk.Vec2d(0, 1)
        else:
            normal = direction.normalized().perpendicular()
        center = (p1 + p2) * 0.5

        # Define a huge half-space polygon (10km x 10km)
        extent = 500000  # 5km in each direction
        perp = normal.perpendicular()
        corners = [
            center + normal * 10 + perp * (-extent),
            center + normal * 10 + perp * extent,
            center - normal * extent + perp * extent,
            center - normal * extent + perp * (-extent),
        ]

        body = self.pm.static_body
        shape = pymunk.Poly(body, corners)
        shape.friction = friction
        shape.elasticity = elasticity
        shape.filter = pymunk.ShapeFilter(group=1)

        self.pm.space.add(shape)
        self.pm.static_lines.append(shape)
        self.undo_redo.take_snapshot()
        synthesizer.play_frequency(150, duration=0.05, waveform='sine')

    def draw_preview(self, screen, camera):
        if self.start_pos is None:
            return
        mouse_world = camera.screen_to_world(pygame.mouse.get_pos())
        p1 = self.start_pos
        p2 = pymunk.Vec2d(*mouse_world)
        direction = p2 - p1
        normal = direction.normalized().perpendicular() if direction.length > 0 else pymunk.Vec2d(0, 1)
        center = (p1 + p2) * 0.5

        # Preview as a thick line with fill hint
        perp = normal.perpendicular()
        half_len = 2000
        a = center + normal * 10 + perp * (-half_len)
        b = center + normal * 10 + perp * half_len
        a_scr = camera.world_to_screen(a)
        b_scr = camera.world_to_screen(b)
        pygame.draw.line(screen, (180, 220, 255), a_scr, b_scr, 4)
        for offset in [0, 5, 10]:
            line_a = camera.world_to_screen(center + normal * offset + perp * (-half_len))
            line_b = camera.world_to_screen(center + normal * offset + perp * half_len)
            pygame.draw.line(screen, (180, 220, 255, 100), line_a, line_b, 1)

    def deactivate(self):
        self.start_pos = None