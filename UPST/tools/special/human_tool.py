import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui


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