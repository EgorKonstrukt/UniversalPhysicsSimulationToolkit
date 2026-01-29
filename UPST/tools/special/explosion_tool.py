import pygame
import pygame_gui
import pymunk
import math
from UPST.modules.undo_redo_manager import get_undo_redo
from UPST.config import config, get_theme_and_palette
from UPST.tools.base_tool import BaseTool

class ExplosionTool(BaseTool):
    name = "Explosion"
    icon_path = "sprites/gui/tools/explosion.png"

    def __init__(self, app):
        super().__init__(app)
        self.radius = 100.0
        self.strength = 1000.0
        self.preview_pos = None
        self.color = pygame.Color(255, 64, 64, 128)

    def create_settings_window(self):
        screen_w, screen_h = self.ui_manager.manager.window_resolution
        win_size = (300, 400)
        pos = self.tool_system._find_non_overlapping_position(win_size, pygame.Rect(0, 0, screen_w, screen_h))
        rect = pygame.Rect(*pos, *win_size)
        self.settings_window = pygame_gui.elements.UIWindow(
            rect=rect,
            manager=self.ui_manager.manager,
            window_display_title=f"{self.name} Settings",
            resizable=True
        )
        container = self.settings_window.get_container()
        y = 10
        self.radius_slider = pygame_gui.elements.UIHorizontalSlider(
            pygame.Rect(10, y, 280, 25), start_value=self.radius, value_range=(10.0, 500.0),
            manager=self.ui_manager.manager, container=container
        )
        self.radius_label = pygame_gui.elements.UILabel(
            pygame.Rect(10, y - 20, 280, 20), f"Radius: {self.radius:.1f}",
            manager=self.ui_manager.manager, container=container
        )
        y += 50
        self.strength_slider = pygame_gui.elements.UIHorizontalSlider(
            pygame.Rect(10, y, 280, 25), start_value=self.strength, value_range=(100.0, 10000.0),
            manager=self.ui_manager.manager, container=container
        )
        self.strength_label = pygame_gui.elements.UILabel(
            pygame.Rect(10, y - 20, 280, 20), f"Strength: {self.strength:.0f}",
            manager=self.ui_manager.manager, container=container
        )

    def handle_event(self, event, world_pos):
        super().handle_event(event, world_pos)
        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.radius_slider:
                self.radius = event.value
                self.radius_label.set_text(f"Radius: {self.radius:.1f}")
            elif event.ui_element == self.strength_slider:
                self.strength = event.value
                self.strength_label.set_text(f"Strength: {self.strength:.0f}")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.preview_pos = world_pos
            self._trigger_explosion(world_pos)
        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[0]:
                self.preview_pos = world_pos
                self._trigger_explosion(world_pos)

    def _trigger_explosion(self, pos):
        affected = []
        for body in self.app.physics_manager.space.bodies:
            if body == self.app.physics_manager.static_body or body.body_type == pymunk.Body.STATIC:
                continue
            offset = body.position - pos
            dist = offset.length
            if dist < self.radius:
                impulse_mag = self.strength / max(dist, 1.0)
                impulse = offset * impulse_mag
                body.apply_impulse_at_local_point(impulse)
                affected.append((body, impulse))
        # if affected:
        #     self.undo_redo.push({
        #         'type': 'explosion',
        #         'pos': pos,
        #         'affected': [(b, tuple(i)) for b, i in affected]
        #     })

    def draw_preview(self, screen, camera):
        if not self.preview_pos:
            return
        screen_pos = camera.world_to_screen(self.preview_pos)
        radius_px = int(self.radius * camera.scaling)
        surf = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, self.color, (radius_px, radius_px), radius_px, 2)
        screen.blit(surf, (screen_pos[0] - radius_px, screen_pos[1] - radius_px))