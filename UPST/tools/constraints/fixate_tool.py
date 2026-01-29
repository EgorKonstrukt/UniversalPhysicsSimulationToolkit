import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools.base_tool import BaseTool
import pygame_gui

class FixateTool(BaseTool):
    name = "Fixate"
    icon_path = "sprites/gui/tools/fixate.png"

    def __init__(self, app):
        super().__init__(app)
        self.first_body = None
        self.first_anchor = None
        self.distance = 0.0

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
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 120, 20), text="Distance:", manager=self.ui_manager.manager, container=win)
        self.distance_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(135, 10, 60, 20), initial_text="0", manager=self.ui_manager.manager, container=win)
        self.settings_window = win

    def handle_event(self, event, world_pos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        info = self.app.physics_manager.space.point_query_nearest(world_pos, 0, pymunk.ShapeFilter())
        body = info.shape.body if info and info.shape and info.shape.body != self.app.physics_manager.static_body else None
        if self.first_body is None:
            if body:
                self.first_body = body
                self.first_anchor = self.first_body.world_to_local(world_pos)
                synthesizer.play_frequency(300, duration=0.03, waveform='sine')
        else:
            target_body = body if body else self.app.physics_manager.static_body
            target_anchor = world_pos if target_body == self.app.physics_manager.static_body else target_body.world_to_local(world_pos)
            try:
                dist_text = self.distance_entry.get_text().strip()
                dist = float(dist_text) if dist_text not in ("", "auto") else 0.0
                pin = pymunk.PinJoint(self.first_body, target_body, self.first_anchor, target_anchor)
                pin.distance = dist
                angle = self.first_body.angle
                rot = pymunk.RotaryLimitJoint(self.first_body, target_body, angle, angle)
                self.app.physics_manager.weld_bodies(self.first_body, target_body)
                self.undo_redo.take_snapshot()

                synthesizer.play_frequency(400, duration=0.04, waveform='sine')
            except Exception:
                pass
            self.first_body = None
            self.first_anchor = None

    def deactivate(self):
        self.first_body = None
        self.first_anchor = None