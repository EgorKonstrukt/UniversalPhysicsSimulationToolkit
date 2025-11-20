import pymunk, pygame, math, random, traceback
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIImage, UICheckBox

from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
import pygame_gui

from UPST.tools.laser_processor import LaserProcessor
from UPST.tools.base_tool import BaseTool



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
            HumanTool(self.pm)
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
        for name in ["Circle", "Rectangle", "Triangle", "Polyhedron", "Spam", "Human"]:
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

class CircleTool(BaseTool):
    name = "Circle"
    icon_path = "sprites/gui/spawn/circle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.ui_manager.manager,
                                           window_display_title="Circle Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.radius_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                                relative_rect=pygame.Rect(30, 10, 100, 20),
                                                                container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 20, 20), text="R:", container=win,
                                    manager=self.ui_manager.manager)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.7",
                                                                  relative_rect=pygame.Rect(80, 55, 100, 20),
                                                                  container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 55, 80, 20), text="Friction:", container=win,
                                    manager=self.ui_manager.manager)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.5",
                                                                    relative_rect=pygame.Rect(90, 75, 105, 20),
                                                                    container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 75, 85, 20), text="Elasticity:", container=win,
                                    manager=self.ui_manager.manager)
        self.color_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 105, 100, 25), text="Pick Color",
                                                      manager=self.ui_manager.manager, container=win)
        self.rand_cb = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 130, 20, 20), text="",
                                                    manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(28, 130, 100, 20), text="Random", container=win,
                                    manager=self.ui_manager.manager)
        self.rand_img = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(5, 130, 20, 20),
                                                    image_surface=pygame.image.load("sprites/gui/checkbox_true.png"),
                                                    container=win, manager=self.ui_manager.manager)
        self.settings_window = win

    def spawn_at(self, pos):
        r = float(self.radius_entry.get_text())
        mass = r * math.pi / 10
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
        body.position = pos
        shape = pymunk.Circle(body, r)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('circle')
        self.pm.add_body_shape(body, shape)

    def spawn_dragged(self, start, end):
        start_vec = pymunk.Vec2d(*start)
        end_vec = pymunk.Vec2d(*end)
        r = (start_vec - end_vec).length
        if r <= 0:
            return
        mass = r * math.pi / 10
        body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
        body.position = start
        shape = pymunk.Circle(body, r)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('circle')
        self.pm.add_body_shape(body, shape)

    def _calc_preview(self, end_pos):
        start_vec = pymunk.Vec2d(*self.drag_start)
        end_vec = pymunk.Vec2d(*end_pos)
        r = (start_vec - end_vec).length
        return {"type": "circle", "position": self.drag_start, "radius": r, "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        pygame.draw.circle(screen, self.preview['color'], sp, int(self.preview['radius']), 1)

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme = config.world.themes.get(config.world.current_theme, config.world.themes["Classic"])
            r_range, g_range, b_range = theme.shape_color_range
            return (random.randint(r_range[0], r_range[1]), random.randint(g_range[0], g_range[1]),
                    random.randint(b_range[0], b_range[1]), 255)
        return getattr(self.ui_manager, f"shape_colors")[shape_type]


class RectangleTool(BaseTool):
    name = "Rectangle"
    icon_path = "sprites/gui/spawn/rectangle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.ui_manager.manager,
                                           window_display_title="Rectangle Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.w_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                           relative_rect=pygame.Rect(30, 10, 100, 20), container=win,
                                                           manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 20, 20), text="W:", container=win,
                                    manager=self.ui_manager.manager)
        self.h_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                           relative_rect=pygame.Rect(30, 30, 100, 20), container=win,
                                                           manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 30, 20, 20), text="H:", container=win,
                                    manager=self.ui_manager.manager)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.7",
                                                                  relative_rect=pygame.Rect(80, 55, 100, 20),
                                                                  container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 55, 80, 20), text="Friction:", container=win,
                                    manager=self.ui_manager.manager)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.5",
                                                                    relative_rect=pygame.Rect(90, 75, 105, 20),
                                                                    container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 75, 85, 20), text="Elasticity:", container=win,
                                    manager=self.ui_manager.manager)
        self.color_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 105, 100, 25), text="Pick Color",
                                                      manager=self.ui_manager.manager, container=win)
        self.rand_cb = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 130, 20, 20), text="",
                                                    manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(28, 130, 100, 20), text="Random", container=win,
                                    manager=self.ui_manager.manager)
        self.rand_img = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(5, 130, 20, 20),
                                                    image_surface=pygame.image.load("sprites/gui/checkbox_true.png"),
                                                    container=win, manager=self.ui_manager.manager)
        self.settings_window = win

    def spawn_at(self, pos):
        w = float(self.w_entry.get_text())
        h = float(self.h_entry.get_text())
        mass = (w * h) / 200
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w * 2, h * 2)))
        body.position = pos
        shape = pymunk.Poly.create_box(body, (w * 2, h * 2))
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('rectangle')
        self.pm.add_body_shape(body, shape)

    def spawn_dragged(self, start, end):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        w = abs(dx) / 2
        h = abs(dy) / 2
        if w <= 0 or h <= 0:
            return
        center = (start[0] + dx / 2, start[1] + dy / 2)
        mass = (w * h) / 200
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, (w * 2, h * 2)))
        body.position = center
        shape = pymunk.Poly.create_box(body, (w * 2, h * 2))
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('rectangle')
        self.pm.add_body_shape(body, shape)

    def _calc_preview(self, end_pos):
        dx = end_pos[0] - self.drag_start[0]
        dy = end_pos[1] - self.drag_start[1]
        center = (self.drag_start[0] + dx / 2, self.drag_start[1] + dy / 2)
        return {"type": "rect", "position": center, "width": abs(dx), "height": abs(dy), "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        r = pygame.Rect(0, 0, self.preview['width'], self.preview['height'])
        r.center = sp
        pygame.draw.rect(screen, self.preview['color'], r, 1)

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme = config.world.themes.get(config.world.current_theme, config.world.themes["Classic"])
            r_range, g_range, b_range = theme.shape_color_range
            return (random.randint(r_range[0], r_range[1]), random.randint(g_range[0], g_range[1]),
                    random.randint(b_range[0], b_range[1]), 255)
        return getattr(self.ui_manager, f"shape_colors")[shape_type]


class TriangleTool(BaseTool):
    name = "Triangle"
    icon_path = "sprites/gui/spawn/triangle.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.ui_manager.manager,
                                           window_display_title="Triangle Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.size_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                              relative_rect=pygame.Rect(60, 10, 100, 20), container=win,
                                                              manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 50, 20), text="Size:", container=win,
                                    manager=self.ui_manager.manager)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.7",
                                                                  relative_rect=pygame.Rect(80, 55, 100, 20),
                                                                  container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 55, 80, 20), text="Friction:", container=win,
                                    manager=self.ui_manager.manager)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.5",
                                                                    relative_rect=pygame.Rect(90, 75, 105, 20),
                                                                    container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 75, 85, 20), text="Elasticity:", container=win,
                                    manager=self.ui_manager.manager)
        self.color_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 105, 100, 25), text="Pick Color",
                                                      manager=self.ui_manager.manager, container=win)
        self.rand_cb = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 130, 20, 20), text="",
                                                    manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(28, 130, 100, 20), text="Random", container=win,
                                    manager=self.ui_manager.manager)
        self.rand_img = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(5, 130, 20, 20),
                                                    image_surface=pygame.image.load("sprites/gui/checkbox_true.png"),
                                                    container=win, manager=self.ui_manager.manager)
        self.settings_window = win

    def spawn_at(self, pos):
        size = float(self.size_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / 3), size * math.sin(i * 2 * math.pi / 3)) for i in range(3)]
        mass = (size ** 2) / 200
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = pos
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('triangle')
        self.pm.add_body_shape(body, shape)

    def spawn_dragged(self, start, end):
        delta = pymunk.Vec2d(end[0] - start[0], end[1] - start[1])
        size = delta.length / 2
        if size <= 0:
            return
        points = [(size * math.cos(i * 2 * math.pi / 3), size * math.sin(i * 2 * math.pi / 3)) for i in range(3)]
        mass = (size ** 2) / 200
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = start
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('triangle')
        self.pm.add_body_shape(body, shape)

    def _calc_preview(self, end_pos):
        delta = pymunk.Vec2d(end_pos[0] - self.drag_start[0], end_pos[1] - self.drag_start[1])
        size = delta.length / 2
        points = [(size * math.cos(i * 2 * math.pi / 3), size * math.sin(i * 2 * math.pi / 3)) for i in range(3)]
        return {"type": "poly", "position": self.drag_start, "points": points, "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        pts = [(sp[0] + p[0], sp[1] + p[1]) for p in self.preview['points']]
        pygame.draw.polygon(screen, self.preview['color'], pts, 1)

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme = config.world.themes.get(config.world.current_theme, config.world.themes["Classic"])
            r_range, g_range, b_range = theme.shape_color_range
            return (random.randint(r_range[0], r_range[1]), random.randint(g_range[0], g_range[1]),
                    random.randint(b_range[0], b_range[1]), 255)
        return getattr(self.ui_manager, f"shape_colors")[shape_type]


class PolyhedronTool(BaseTool):
    name = "Polyhedron"
    icon_path = "sprites/gui/spawn/polyhedron.png"

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, 10, 400, 300), manager=self.ui_manager.manager,
                                           window_display_title="Polyhedron Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215, 5, 50, 50),
                                    image_surface=pygame.image.load(self.icon_path), container=win,
                                    manager=self.ui_manager.manager)
        self.size_entry = pygame_gui.elements.UITextEntryLine(initial_text="30",
                                                              relative_rect=pygame.Rect(60, 10, 100, 20), container=win,
                                                              manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 50, 20), text="Size:", container=win,
                                    manager=self.ui_manager.manager)
        self.faces_entry = pygame_gui.elements.UITextEntryLine(initial_text="6",
                                                               relative_rect=pygame.Rect(60, 30, 100, 20),
                                                               container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 30, 50, 20), text="Faces:", container=win,
                                    manager=self.ui_manager.manager)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.7",
                                                                  relative_rect=pygame.Rect(80, 55, 100, 20),
                                                                  container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 55, 80, 20), text="Friction:", container=win,
                                    manager=self.ui_manager.manager)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(initial_text="0.5",
                                                                    relative_rect=pygame.Rect(90, 75, 105, 20),
                                                                    container=win, manager=self.ui_manager.manager)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5, 75, 85, 20), text="Elasticity:", container=win,
                                    manager=self.ui_manager.manager)
        self.color_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 105, 100, 25), text="Pick Color",
                                                      manager=self.ui_manager.manager, container=win)
        self.rand_cb = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5, 130, 20, 20), text="",
                                                    manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(28, 130, 100, 20), text="Random", container=win,
                                    manager=self.ui_manager.manager)
        self.rand_img = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(5, 130, 20, 20),
                                                    image_surface=pygame.image.load("sprites/gui/checkbox_true.png"),
                                                    container=win, manager=self.ui_manager.manager)
        self.settings_window = win

    def spawn_at(self, pos):
        size = float(self.size_entry.get_text())
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in
                  range(faces)]
        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        mass = abs(area) / 2 / 100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = pos
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('polyhedron')
        self.pm.add_body_shape(body, shape)

    def spawn_dragged(self, start, end):
        delta = pymunk.Vec2d(end[0] - start[0], end[1] - start[1])
        size = delta.length / 2
        if size <= 0:
            return
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in
                  range(faces)]
        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        mass = abs(area) / 2 / 100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, points))
        body.position = start
        shape = pymunk.Poly(body, points)
        shape.friction = float(self.friction_entry.get_text())
        shape.elasticity = float(self.elasticity_entry.get_text())
        shape.color = self._get_color('polyhedron')
        self.pm.add_body_shape(body, shape)

    def _calc_preview(self, end_pos):
        delta = pymunk.Vec2d(end_pos[0] - self.drag_start[0], end_pos[1] - self.drag_start[1])
        size = delta.length / 2
        faces = int(self.faces_entry.get_text())
        points = [(size * math.cos(i * 2 * math.pi / faces), size * math.sin(i * 2 * math.pi / faces)) for i in
                  range(faces)]
        return {"type": "poly", "position": self.drag_start, "points": points, "color": (200, 200, 255, 100)}

    def _draw_custom_preview(self, screen, camera):
        sp = camera.world_to_screen(self.preview['position'])
        pts = [(sp[0] + p[0], sp[1] + p[1]) for p in self.preview['points']]
        pygame.draw.polygon(screen, self.preview['color'], pts, 1)

    def _get_color(self, shape_type):
        if getattr(self.ui_manager, f"{shape_type}_color_random", True):
            theme = config.world.themes.get(config.world.current_theme, config.world.themes["Classic"])
            r_range, g_range, b_range = theme.shape_color_range
            return (random.randint(r_range[0], r_range[1]), random.randint(g_range[0], g_range[1]),
                    random.randint(b_range[0], b_range[1]), 255)
        return getattr(self.ui_manager, f"shape_colors")[shape_type]


class SpamTool(BaseTool):
    name = "Spam"
    icon_path = "sprites/gui/spawn/spam.png"

    def spawn_at(self, pos):
        for _ in range(50):
            shape_type = random.choice(["circle", "rectangle", "triangle", "polyhedron"])
            offset = (pos[0] + random.uniform(-150, 150), pos[1] + random.uniform(-150, 150))
            if self.ui_manager and self.ui_manager.tool_system:
                tool = self.ui_manager.tool_system.tools.get(shape_type.capitalize())
                if tool:
                    tool.spawn_at(offset)


class HumanTool(BaseTool):
    name = "Human"
    icon_path = "sprites/gui/spawn/human.png"

    def spawn_at(self, pos):
        head = pymunk.Body(10, pymunk.moment_for_circle(10, 0, 30))
        head.position = pos
        head_shape = pymunk.Circle(head, 30)
        self.pm.add_body_shape(head, head_shape)
        torso = pymunk.Body(20, pymunk.moment_for_box(20, (20, 80)))
        torso.position = (pos[0], pos[1] - 70)
        torso_shape = pymunk.Poly.create_box(torso, (20, 80))
        self.pm.add_body_shape(torso, torso_shape)
        self.pm.space.add(pymunk.PinJoint(head, torso, (0, -30), (0, 40)))


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
        self.start_pos = None
        self.thickness_entry = None
        self.remove_circles_cb = None
        self.keep_small_cb = None
        self._tmp_preview = None

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, 10, 360, 160),
            manager=self.ui_manager.manager,
            window_display_title="Cut Settings"
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, 120, 20),
            text="Толщина (px):",
            manager=self.ui_manager.manager,
            container=win
        )
        self.thickness_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(130, 10, 80, 20),
            initial_text="4",
            manager=self.ui_manager.manager,
            container=win
        )
        self.remove_circles_cb = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 40, 240, 20),
            text="Удалять круги при пересечении",
            manager=self.ui_manager.manager,
            container=win
        )
        self.keep_small_cb = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 65, 240, 20),
            text="Оставлять мелкие фрагменты",
            manager=self.ui_manager.manager,
            container=win
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 95, 320, 40),
            text="Рисуйте линию — объекты, пересёкшиеся линией, будут разрезаны/удалены.",
            manager=self.ui_manager.manager,
            container=win
        )
        self.settings_window = win

    def _seg_seg_intersection(self, a1, a2, b1, b2):
        ax,ay=a1; bx,by=a2; cx,cy=b1; dx,dy=b2
        r=(bx-ax,by-ay); s=(dx-cx,dy-cy)
        denom = r[0]*s[1]-r[1]*s[0]
        if abs(denom) < 1e-8: return None
        t = ((cx-ax)*s[1]-(cy-ay)*s[0]) / denom
        u = ((cx-ax)*r[1]-(cy-ay)*r[0]) / denom
        if 0<=t<=1 and 0<=u<=1:
            return (ax + t*r[0], ay + t*r[1])
        return None

    def _seg_circle_intersect(self, a, b, center, r):
        ax, ay = a
        bx, by = b
        cx, cy = center

        vx = bx - ax
        vy = by - ay
        ux = ax - cx
        uy = ay - cy

        a_coef = vx * vx + vy * vy
        if a_coef == 0:
            return (ux * ux + uy * uy) <= r * r

        b_coef = 2 * (ux * vx + uy * vy)
        c_coef = ux * ux + uy * uy - r * r

        disc = b_coef * b_coef - 4 * a_coef * c_coef
        if disc < 0:
            return False

        sq = math.sqrt(disc)
        denom = 2 * a_coef
        if denom == 0:
            return False

        t1 = (-b_coef - sq) / denom
        t2 = (-b_coef + sq) / denom

        return (0 <= t1 <= 1) or (0 <= t2 <= 1)

    def _point_line_dist(self, p, a, b):
        ax,ay=a; bx,by=b; px,py=p
        lx=bx-ax; ly=by-ay
        l2=lx*lx+ly*ly
        if l2==0: return math.hypot(px-ax, py-ay)
        t=max(0, min(1, ((px-ax)*lx+(py-ay)*ly)/l2))
        proj=(ax+t*lx, ay+t*ly)
        return math.hypot(px-proj[0], py-proj[1])

    def _polygon_world_pts(self, poly):
        return [poly.body.local_to_world(v) for v in poly.get_vertices()]

    def _area_centroid(self, pts):
        a=0; cx=0; cy=0
        for i in range(len(pts)):
            x1,y1=pts[i]; x2,y2=pts[(i+1)%len(pts)]
            cross = x1*y2-x2*y1
            a += cross
            cx += (x1+x2)*cross
            cy += (y1+y2)*cross
        a = a * 0.5
        if abs(a) < 1e-8: return 0, (pts[0][0], pts[0][1])
        cx = cx/(6*a); cy = cy/(6*a)
        return abs(a), (cx,cy)

    def _split_poly_by_segment(self, poly, a, b):
        pts = self._polygon_world_pts(poly)
        inters=[]
        for i in range(len(pts)):
            p1=pts[i]; p2=pts[(i+1)%len(pts)]
            ip = self._seg_seg_intersection(a,b,p1,p2)
            if ip:
                inters.append((i, ip))
        if len(inters) != 2:
            return None
        (i1, ip1), (i2, ip2) = inters
        if i2 < i1:
            i1,ip1,i2,ip2 = i2,ip2,i1,ip1
        poly1 = []
        poly1.extend(pts[i1+1:i2+1])
        poly1.insert(0, ip1); poly1.append(ip2)
        poly2 = []
        poly2.extend(pts[i2+1:] + pts[:i1+1])
        poly2.insert(0, ip2); poly2.append(ip1)
        return poly1, poly2

    def _create_poly_body(self, pts, proto_shape):
        area,cent = self._area_centroid(pts)
        if area < 1e-2:
            return None
        local_pts = [(p[0]-cent[0], p[1]-cent[1]) for p in pts]
        mass = area/100
        body = pymunk.Body(mass, pymunk.moment_for_poly(mass, local_pts))
        body.position = cent
        shape = pymunk.Poly(body, local_pts)
        shape.friction = getattr(proto_shape, "friction", 0.7)
        shape.elasticity = getattr(proto_shape, "elasticity", 0.5)
        shape.color = getattr(proto_shape, "color", (200,200,200,255))
        return body, shape

    def _remove_shape_and_maybe_body(self, shape):
        b = shape.body
        try:
            if shape in self.pm.space.shapes: self.pm.space.remove(shape)
        except Exception: pass
        if len(b.shapes) == 0:
            try: self.pm.space.remove(b)
            except Exception: pass

    def _process_cut(self, a, b, thickness):
        to_remove_shapes = []
        to_add = []
        for shape in list(self.pm.space.shapes):
            if shape.body == self.pm.static_body: continue
            if isinstance(shape, pymunk.Segment):
                p1 = shape.a; p2 = shape.b
                if self._seg_seg_intersection(a,b,p1,p2):
                    to_remove_shapes.append(shape)
            elif isinstance(shape, pymunk.Circle):
                if self._seg_circle_intersect(a,b,shape.body.position, shape.radius):
                    if self.remove_circles_cb.get_state():
                        to_remove_shapes.append(shape)
                    else:
                        to_remove_shapes.append(shape)
            elif isinstance(shape, pymunk.Poly):
                res = self._split_poly_by_segment(shape, a, b)
                if res:
                    p1_pts, p2_pts = res
                    new1 = self._create_poly_body(p1_pts, shape)
                    new2 = self._create_poly_body(p2_pts, shape)
                    if new1:
                        to_add.append(new1)
                    if new2:
                        to_add.append(new2)
                    to_remove_shapes.append(shape)
                else:
                    mind = min(self._point_line_dist(v, a, b) for v in self._polygon_world_pts(shape))
                    if mind <= thickness:
                        to_remove_shapes.append(shape)
        for c in list(self.pm.space.constraints):
            a1 = c.a.local_to_world(getattr(c, "anchor_a", (0,0)))
            a2 = c.b.local_to_world(getattr(c, "anchor_b", (0,0)))
            if self._point_line_dist(a1, a, b) <= thickness or self._point_line_dist(a2, a, b) <= thickness:
                try: self.pm.space.remove(c)
                except: pass
        for sh in to_remove_shapes:
            try:
                for s in list(sh.body.shapes):
                    if s==sh: continue
                self._remove_shape_and_maybe_body(sh)
            except Exception: pass
        for body_shape in to_add:
            body, shape = body_shape
            try: self.pm.add_body_shape(body, shape)
            except Exception:
                try: self.pm.space.add(body, shape)
                except Exception: pass

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.start_pos = world_pos
            self._tmp_preview = (world_pos, world_pos)
        elif event.type == pygame.MOUSEMOTION and self.start_pos:
            self._tmp_preview = (self.start_pos, world_pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.start_pos:
            a = self.start_pos; b = world_pos
            try:
                thickness = float(self.thickness_entry.get_text()) if self.thickness_entry else 4.0
            except Exception:
                thickness = 4.0
            self._process_cut(a, b, thickness)
            self.start_pos = None
            self._tmp_preview = None
            synthesizer.play_frequency(300, duration=0.05, waveform='sine')

    def draw_preview(self, screen, camera):
        seg = self._tmp_preview
        if not seg: return
        a_screen = camera.world_to_screen(seg[0]); b_screen = camera.world_to_screen(seg[1])
        pygame.draw.line(screen, (255, 100, 100), a_screen, b_screen, int(float(self.thickness_entry.get_text()) if self.thickness_entry else 4))
