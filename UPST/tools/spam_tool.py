import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class SpamTool(BaseTool):
    name = "Spam"
    icon_path = "sprites/gui/spawn/spam.png"

    def spawn_at(self, pos):
        for _ in range(10):
            shape_type = random.choice(["circle", "rectangle", "triangle", "polyhedron"])
            offset = (pos[0] + random.uniform(-150, 150), pos[1] + random.uniform(-150, 150))
            if self.ui_manager and self.ui_manager.tool_system:
                tool = self.ui_manager.tool_system.tools.get(shape_type.capitalize())
                if tool:
                    tool.spawn_at(offset)
        self.undo_redo.take_snapshot()





