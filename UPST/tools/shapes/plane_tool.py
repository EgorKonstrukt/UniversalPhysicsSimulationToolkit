import random
import pygame, math, pymunk
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools.base_tool import BaseTool
import pygame_gui
from UPST.modules.statistics import stats

class PlaneTool(BaseTool):
    name = "Plane"
    icon_path = "sprites/gui/tools/plane.png"

    def __init__(self, app):
        super().__init__(app)
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
        if self.ui_manager.manager.get_focus_set():
            return
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

        body = self.app.physics_manager.static_body
        shape = pymunk.Poly(body, corners)
        shape.friction = friction
        shape.elasticity = elasticity
        shape.filter = pymunk.ShapeFilter(group=1)

        self.app.physics_manager.space.add(shape)
        self.app.physics_manager.static_lines.append(shape)
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