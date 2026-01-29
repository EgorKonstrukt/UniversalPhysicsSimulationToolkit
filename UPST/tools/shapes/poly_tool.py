import random
import traceback
import pygame, math, pymunk
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools.base_tool import BaseTool
import pygame_gui
from UPST.modules.statistics import stats

class PolyTool(BaseTool):
    name = "Poly"
    category = "Shapes"
    icon_path = "sprites/gui/tools/polygon.png"

    def __init__(self, app):
        super().__init__(app)
        self.points = []
        self.preview_closed = False

    def create_settings_window(self):
        screen_w, screen_h = self.ui_manager.manager.window_resolution
        win_size = (300, 400)
        pos = self.tool_system._find_non_overlapping_position(win_size, pygame.Rect(0, 0, screen_w, screen_h))
        rect = pygame.Rect(*pos, *win_size)
        win = pygame_gui.elements.UIWindow(
            rect=rect,
            manager=self.ui_manager.manager,
            window_display_title=f"{self.name} Settings",
            resizable=True
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Min vertices:", manager=self.ui_manager.manager, container=win)
        self.min_vertices_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="3", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 40, 120, 20), text="Friction:", manager=self.ui_manager.manager, container=win)
        self.friction_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 40, 60, 20), initial_text="0.7", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 70, 120, 20), text="Elasticity:", manager=self.ui_manager.manager, container=win)
        self.elasticity_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 70, 60, 20), initial_text="0.3", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.points.append(world_pos)
                synthesizer.play_frequency(300, 0.02, 'sine')
            elif event.button == 3 and len(self.points) >= int(self.min_vertices_entry.get_text() or "3"):
                self._finalize_polygon()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and len(self.points) >= int(self.min_vertices_entry.get_text() or "3"):
            self._finalize_polygon()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drag_start = world_pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_start:
                self.spawn_dragged(self.drag_start, world_pos)
            self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start:
            self.preview = self._calc_preview(world_pos)

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
            self.app.physics_manager.space.add(body, shape)
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