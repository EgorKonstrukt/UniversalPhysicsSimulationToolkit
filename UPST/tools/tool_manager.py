import pymunk, pygame, math, random, traceback
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIImage

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
            LaserTool(self.pm, self.laser_processor)
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
        panel = UIPanel(relative_rect=pygame.Rect(5, 50, 200, 640), manager=self.ui_manager.manager)
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

