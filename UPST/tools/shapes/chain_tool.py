import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools.base_tool import BaseTool
import pygame_gui

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
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.start_pos = pymunk.Vec2d(*world_pos)
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


        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drag_start = world_pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_start:
                self.spawn_dragged(self.drag_start, world_pos)
            self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start:
            self.preview = self._calc_preview(world_pos)

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