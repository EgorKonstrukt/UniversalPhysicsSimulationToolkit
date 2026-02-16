# UPST/modules/node_graph/node_tools.py
import pygame

import pygame_gui
from UPST.modules.node_graph.node_graph_manager import NodeGraphManager
from UPST.debug.debug_manager import Debug
from UPST.tools.base_tool import BaseTool


class NodeGraphEditorTool(BaseTool):
    name = "NodeGraphEditor"
    icon_path = "sprites/gui/node_graph.png"
    category = "Tools"
    tooltip = "Edit and connect nodes (Required for Buttons/Toggles)"

    def __init__(self, app):
        super().__init__(app)
        self.ngm = NodeGraphManager(app=app)
        if not self.ngm.graphs:
            self.ngm.create_graph("MainGraph")

    def activate(self):
        super().activate()
        Debug.log_info("Node Graph Editor Activated. You can now click Buttons/Toggles.", "NodeGraph")

    def deactivate(self):
        super().deactivate()

    def create_settings_window(self):
        if not self.ui_manager: return
        from pygame_gui.elements import UIWindow, UIButton
        from pygame_gui.core import ObjectID
        rect = pygame.Rect(100, 100, 250, 300)
        self.settings_window = UIWindow(rect, self.ui_manager.manager, window_display_title="Graph Settings",
                                        object_id=ObjectID(object_id='#ng_editor_settings'))
        y = 10
        btn = UIButton(relative_rect=pygame.Rect(10, y, 230, 30), text="Create New Graph",
                       manager=self.ui_manager.manager, container=self.settings_window,
                       object_id=ObjectID(object_id='#ng_btn_new'))
        y += 40
        for gid, graph in self.ngm.graphs.items():
            btn = UIButton(relative_rect=pygame.Rect(10, y, 230, 30), text=graph.name,
                           manager=self.ui_manager.manager, container=self.settings_window,
                           object_id=ObjectID(object_id=f'#ng_btn_{gid}'))
            btn.graph_id = gid
            y += 35

    def handle_event(self, event, world_pos):
        if self.ui_manager.manager.get_focus_set():
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                self.ngm.handle_key_down(event)
            return

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self.ngm.handle_key_down(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.ngm.handle_mouse_down(world_pos, event.button)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.ngm.handle_mouse_up(world_pos, event.button)

        elif event.type == pygame.MOUSEMOTION:
            self.ngm.handle_mouse_motion(world_pos, pygame.mouse.get_pressed())

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if hasattr(event.ui_element, 'graph_id'):
                self.ngm.active_graph = self.ngm.graphs[event.ui_element.graph_id]
            elif event.ui_element.text == "Create New Graph":
                self.ngm.create_graph()
                self.create_settings_window()

    def draw_preview(self, scr, camera):
        if self.ngm.active_graph:
            self.ngm.draw(scr, camera)
        else:
            txt = self.font.render("No Active Graph.", True, (255, 255, 0))
            scr.blit(txt, (10, 10))

    def serialize_for_save(self) -> dict:
        return self.ngm.serialize_for_save()

    def deserialize_from_save(self, data: dict):
        self.ngm.deserialize_from_save(data)

class NodeSpawnTool(BaseTool):
    category = "Node Spawners"

    def __init__(self, app, node_type: str, name: str, color: tuple):
        super().__init__(app)
        self.node_type = node_type
        self.name = name
        self.color = color
        self.icon_path = "sprites/gui/node.png"
        self.tooltip = f"Spawn {name} node"
        self.ngm = NodeGraphManager(app=app)

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.ui_manager.manager.get_focus_set():
            if not self.ngm.active_graph: self.ngm.create_graph()
            node = self.ngm.create_node(self.node_type, world_pos)
            if node: Debug.log_info(f"Spawned {self.name} at {world_pos}", "NodeTool")

    def draw_preview(self, scr, camera):
        mpos = self.app.camera.get_cursor_world_position()
        pos = camera.world_to_screen(mpos)
        pygame.draw.circle(scr, self.color, (int(pos[0]), int(pos[1])), 10)
        if self.ngm.active_graph:
            self.ngm.draw(scr, camera)
        else:
            txt = self.font.render("No Active Graph. Create one in settings.", True, (255, 255, 0))
            scr.blit(txt, (10, 10))


class LogicAndTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "logic_and", "Logic AND", (150, 100, 50))


class LogicOrTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "logic_or", "Logic OR", (150, 100, 50))


class LogicNotTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "logic_not", "Logic NOT", (150, 100, 50))


class MathAddTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "math_add", "Math Add", (50, 150, 100))


class MathSubTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "math_sub", "Math Sub", (50, 150, 100))


class MathMulTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "math_mul", "Math Mul", (50, 150, 100))


class MathDivTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "math_div", "Math Div", (50, 150, 100))


class ScriptNodeTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "script", "Script Node", (100, 50, 150))


class OutputNodeTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "output", "Output Node", (200, 50, 50))

class ButtonTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "button", "Button", (200, 100, 100))

class ToggleTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "toggle", "Toggle", (100, 200, 100))

class PrintTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "print", "Print", (100, 100, 200))

class OscillatorTool(NodeSpawnTool):
    def __init__(self, app): super().__init__(app, "oscillator", "Oscillator", (200, 200, 100))

class KeyInputTool(NodeSpawnTool):
    def __init__(self, app):
        super().__init__(app, "key_input", "Key Input", (150, 150, 255))
class LightBulbTool(NodeSpawnTool):
    def __init__(self, app):
        super().__init__(app, "light_bulb", "Light Bulb", (255, 255, 100))