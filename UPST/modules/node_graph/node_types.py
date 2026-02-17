# UPST/modules/node_graph/node_types.py
import pygame, math, time
from typing import Any, List
from UPST.modules.node_graph.node_core import Node, DataType, PortType
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import get_gizmos
class LogicGateNode(Node):
    def __init__(self, position=(0, 0), gate_type="and"):
        super().__init__(position=position, name=f"Logic_{gate_type.upper()}", node_type=f"logic_{gate_type}")
        self.gate_type = gate_type
        self.color = (150, 100, 50)
        self.add_input("A", DataType.BOOL, False)
        self.add_input("B", DataType.BOOL, False)
        self.add_output("Out", DataType.BOOL)
    def _execute_default(self, graph):
        a = bool(self.get_input_value("A"))
        b = bool(self.get_input_value("B"))
        res = False
        if self.gate_type == "and": res = a and b
        elif self.gate_type == "or": res = a or b
        elif self.gate_type == "not": res = not a
        elif self.gate_type == "xor": res = a != b
        self.set_output_value("Out", res)
        return True
class MathNode(Node):
    def __init__(self, position=(0, 0), op="add"):
        super().__init__(position=position, name=f"Math_{op.upper()}", node_type=f"math_{op}")
        self.op = op
        self.color = (50, 150, 100)
        self.add_input("A", DataType.FLOAT, 0)
        self.add_input("B", DataType.FLOAT, 0)
        self.add_output("Result", DataType.FLOAT)
    def _execute_default(self, graph):
        a = float(self.get_input_value("A") or 0)
        b = float(self.get_input_value("B") or 0)
        res = 0
        if self.op == "add": res = a + b
        elif self.op == "sub": res = a - b
        elif self.op == "mul": res = a * b
        elif self.op == "div": res = a / b if b != 0 else 0
        self.set_output_value("Result", res)
        return True
class ScriptNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Script", node_type="script")
        self.color = (100, 50, 150)
        self.add_input("Input", DataType.ANY, None)
        self.add_output("Output", DataType.ANY)
        self.script_code = 'outputs["Output"] = inputs.get("Input", 0) * 2'
        self.compile_script()
    def get_context_menu_items(self, manager):
        items = super().get_context_menu_items(manager)
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption("Edit Script...", handler=lambda cm: manager._open_script_editor(self)))
        return items
class OutputNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Output", node_type="output")
        self.color = (200, 50, 50)
        self.add_input("Value", DataType.ANY, None)
        self.add_output("Display", DataType.STRING)
    def _execute_default(self, graph):
        val = self.get_input_value("Value")
        self.set_output_value("Display", str(val))
        gm = get_gizmos()
        if gm: gm.draw_text(position=self.position, text=f"Out: {val}", font_size=16, color=(255, 255, 0), duration=0.1, world_space=True)
        return True
class ButtonNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Button", node_type="button")
        self.color = (200, 100, 100)
        self.add_output("Pressed", DataType.BOOL)
        self.is_pressed = False
        self._prev_pressed = False
        self.size = (120, 60)
    def on_mouse_down(self, world_pos, button):
        x, y = self.position.x, self.position.y
        w, h = self.size
        if x <= world_pos[0] <= x + w and y <= world_pos[1] <= y + h:
            self.is_pressed = True
            return True
        return False
    def on_mouse_up(self, world_pos, button):
        if self.is_pressed:
            self.is_pressed = False
            return True
        return False
    def _execute_default(self, graph):
        out_val = self.is_pressed and not self._prev_pressed
        self._prev_pressed = self.is_pressed
        self.set_output_value("Pressed", out_val)
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        if self.is_pressed:
            pos = camera.world_to_screen((self.position[0], self.position[1]))
            scale = camera.scaling
            size = (self.size[0] * scale, self.size[1] * scale)
            inner_rect = pygame.Rect(int(pos[0]), int(pos[1]), int(size[0]), int(size[1])).inflate(-4 * scale, -4 * scale)
            pygame.draw.rect(scr, (255, 255, 255), inner_rect, border_radius=4)
    def serialize(self) -> dict:
        data = super().serialize()
        data["is_pressed"] = False
        return data
class ToggleNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Toggle", node_type="toggle")
        self.color = (100, 200, 100)
        self.add_output("State", DataType.BOOL)
        self.state = False
        self._triggered = False
        self.size = (120, 60)
    def on_mouse_down(self, world_pos, button):
        x, y = self.position.x, self.position.y
        w, h = self.size
        if x <= world_pos[0] <= x + w and y <= world_pos[1] <= y + h:
            if not self._triggered:
                self.state = not self.state
                self._triggered = True
                return True
        return False
    def on_mouse_up(self, world_pos, button):
        self._triggered = False
        return False
    def _execute_default(self, graph):
        self.set_output_value("State", self.state)
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        size = (self.size[0] * scale, self.size[1] * scale)
        center = (int(pos[0] + size[0] - 15 * scale), int(pos[1] + 15 * scale))
        if self.state:
            pygame.draw.circle(scr, (0, 255, 0), center, int(7 * scale))
            pygame.draw.circle(scr, (255, 255, 255), center, int(3 * scale), 2)
        else:
            pygame.draw.circle(scr, (100, 100, 100), center, int(7 * scale))
    def get_context_menu_items(self, manager):
        items = super().get_context_menu_items(manager)
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption(f"Force State ({'ON' if self.state else 'OFF'})", handler=lambda cm: manager._toggle_force(self)))
        return items
    def serialize(self) -> dict:
        data = super().serialize()
        data["state"] = self.state
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'ToggleNode':
        node = super().deserialize(data)
        node.state = data.get("state", False)
        return node
class PrintNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Print", node_type="print")
        self.color = (100, 100, 200)
        self.add_input("Input", DataType.ANY, None)
        self.add_input("Trigger", DataType.BOOL, True)
        self._last_val_str = ""
        self._first_run = True
        self._last_trigger_state = False
    def _execute_default(self, graph):
        in_val = None
        trigger_val = True
        for pid, port in self.inputs.items():
            if port.name == "Input": in_val = port.value
            elif port.name == "Trigger": trigger_val = port.value if port.value is not None else True
        if trigger_val is None: trigger_val = True
        current_val_str = str(in_val)
        should_print = False
        if self._first_run:
            should_print = True
            self._first_run = False
        else:
            if current_val_str != self._last_val_str: should_print = True
            elif trigger_val and not self._last_trigger_state: should_print = True
        if should_print:
            Debug.log_info(f"[PrintNode '{self.name}']: {in_val}", "NodeGraph")
            self._last_val_str = current_val_str
        self._last_trigger_state = bool(trigger_val)
        return True
class OscillatorNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Oscillator", node_type="oscillator")
        self.color = (200, 200, 100)
        self.add_output("Signal", DataType.FLOAT)
        self.add_output("Bool", DataType.BOOL)
        self.enabled = True
        self.frequency = 1.0
        self.amplitude = 1.0
        self.offset = 0.0
        self._time = 0.0
        self.size = (140, 80)
    def _execute_default(self, graph):
        dt = 0.016
        self._time += dt
        if not self.enabled: val = self.offset
        else: val = math.sin(2 * math.pi * self.frequency * self._time) * self.amplitude + self.offset
        self.set_output_value("Signal", val)
        self.set_output_value("Bool", val > 0)
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        if self.enabled:
            pos = camera.world_to_screen((self.position[0], self.position[1]))
            scale = camera.scaling
            size = (self.size[0] * scale, self.size[1] * scale)
            wave_color = (255, 255, 100)
            start_x, end_x = int(pos[0] + 10 * scale), int(pos[0] + size[0] - 10 * scale)
            mid_y, amp = int(pos[1] + size[1] / 2), int(15 * scale)
            pts = [(start_x + (end_x - start_x) * (i / 20.0), mid_y + math.sin(i * 0.5 + time.time() * self.frequency * 6) * amp) for i in range(21)]
            pygame.draw.lines(scr, wave_color, False, pts, 2)
    def get_context_menu_items(self, manager):
        items = super().get_context_menu_items(manager)
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption(f"Toggle Power ({'ON' if self.enabled else 'OFF'})", handler=lambda cm: manager._toggle_oscillator(self)))
        return items
    def serialize(self) -> dict:
        data = super().serialize()
        data["frequency"] = self.frequency
        data["amplitude"] = self.amplitude
        data["offset"] = self.offset
        data["enabled"] = self.enabled
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'OscillatorNode':
        node = super().deserialize(data)
        node.frequency = data.get("frequency", 1.0)
        node.amplitude = data.get("amplitude", 1.0)
        node.offset = data.get("offset", 0.0)
        node.enabled = data.get("enabled", True)
        return node
class KeyInputNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Key Input", node_type="key_input")
        self.color = (150, 150, 255)
        self.add_output("Pressed", DataType.BOOL)
        self.add_output("JustPressed", DataType.BOOL)
        self.key_code: int = pygame.K_SPACE
        self._is_pressed: bool = False
        self._was_pressed: bool = False
        self.size = (140, 70)
    def set_key(self, key_code: int):
        self.key_code = key_code
        key_name = pygame.key.name(key_code) if hasattr(pygame, 'key') else str(key_code)
        self.name = f"Key: {key_name.upper()}"
    def update_state(self, keys_pressed):
        self._was_pressed = self._is_pressed
        self._is_pressed = keys_pressed[self.key_code] if self.key_code in keys_pressed else False
    def _execute_default(self, graph):
        self.set_output_value("Pressed", self._is_pressed)
        just_pressed = self._is_pressed and not self._was_pressed
        self.set_output_value("JustPressed", just_pressed)
        return True
    def get_context_menu_items(self, manager):
        items = super().get_context_menu_items(manager)
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption(f"Current Key: {pygame.key.name(self.key_code).upper()}", handler=lambda cm: None))
        items.append(ConfigOption("Change Key (Cycle)", handler=lambda cm: manager.prompt_change_key(self)))
        return items
    def serialize(self) -> dict:
        data = super().serialize()
        data["key_code"] = self.key_code
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'KeyInputNode':
        node = super().deserialize(data)
        node.set_key(data.get("key_code", pygame.K_SPACE))
        return node
class LightBulbNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Light Bulb", node_type="light_bulb")
        self.color_off = (60, 60, 60)
        self.color_on = (255, 255, 100)
        self.current_color = self.color_off
        self.add_input("Power", DataType.BOOL, False)
        self._is_on = False
        self.size = (100, 100)
    def _execute_default(self, graph):
        power_val = False
        for pid, port in self.inputs.items():
            if port.name == "Power":
                power_val = bool(port.value) if port.value is not None else False
                break
        self._is_on = power_val
        self.current_color = self.color_on if self._is_on else self.color_off
        return True
    def draw(self, scr, camera, manager):
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        size = (self.size[0] * scale, self.size[1] * scale)
        rect = pygame.Rect(int(pos[0]), int(pos[1]), int(size[0]), int(size[1]))
        draw_color = self.current_color
        center = (int(pos[0] + size[0] / 2), int(pos[1] + size[1] / 2))
        radius = int(min(size[0], size[1]) / 2 - 5)
        if self._is_on:
            for i in range(3, 0, -1):
                glow_radius = radius + (i * 4 * scale)
                glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*draw_color, 100 // i), (glow_radius, glow_radius), glow_radius)
                scr.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius))
        pygame.draw.circle(scr, (255, 255, 255), center, int(radius * 0.6))
        pygame.draw.circle(scr, draw_color, center, radius)
        pygame.draw.circle(scr, (255, 255, 255), center, radius, 2)
        pygame.draw.rect(scr, self.color if self.enabled else (80, 80, 80), rect, border_radius=4)
        pygame.draw.rect(scr, (255, 255, 255), rect, 2 if self in manager.selected_nodes else 1, border_radius=4)
        font = pygame.font.SysFont("Consolas", 14)
        scr.blit(font.render(self.name, True, (255, 255, 255)), (pos[0] + 5, pos[1] + 5))
        self._draw_ports(scr, pos, size, manager)