import random
import pygame, math, pymunk
from UPST.config import config, get_theme_and_palette, sample_color_from_def
from UPST.tools.base_tool import BaseTool
import pygame_gui

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