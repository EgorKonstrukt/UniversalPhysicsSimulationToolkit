from UPST.tools.base_tool import BaseTool
import pygame

from pathlib import Path

PLUGIN_DIR = Path(__file__).parent

PLUGIN = Plugin(
    name="ExampleToolPlugin",
    version="1.0.0",
    description="Example tool plugin",
    author="Zarrakun",
    icon_path="texture.png",
    dependency_specs={},
)

class PluginImpl:
    def __init__(self, app):
        self.app = app

    def get_tools(self, app):
        tool = MyNewTool(app.physics_manager, app)
        return [tool]

class MyNewTool(BaseTool):
    name = "MyNewTool"
    category = "Tools"
    icon_path=str(PLUGIN_DIR / "texture.png")
    tooltip = "Example custom tool from plugin"

    def __init__(self, physics_manager, app):
        super().__init__(physics_manager, app)
        self.active = False

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def handle_input(self, world_pos):
        if self.active:
            print(f"[MyNewTool] Input at {world_pos}")

    def draw_preview(self, screen, camera):
        if self.active:
            pos = camera.world_to_screen((0, 0))
            pygame.draw.circle(screen, (0, 255, 0), pos, 10, 2)