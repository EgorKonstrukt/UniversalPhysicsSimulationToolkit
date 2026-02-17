# UPST/modules/node_graph/node_types.py
import pygame, math, time
from typing import Any, List, Dict, Tuple, Optional, Type
from UPST.modules.node_graph.node_core import Node, DataType, PortType, NodePort
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import get_gizmos


NODE_TYPE_REGISTRY: Dict[str, Type[Node]] = {}
NODE_TOOL_METADATA: Dict[str, Dict[str, str]] = {}

def register_node_type(type_name: str, display_name: str = None, description: str = None, icon: str = None):
    def decorator(cls: Type[Node]):
        NODE_TYPE_REGISTRY[type_name] = cls
        cls._registered_type_name = type_name
        if display_name: cls.tool_name = display_name
        if description: cls.tool_description = description
        if icon: cls.tool_icon_path = icon
        NODE_TOOL_METADATA[type_name] = {
            'name': cls.tool_name,
            'description': cls.tool_description,
            'icon': cls.tool_icon_path
        }
        return cls
    return decorator

@register_node_type("logic_and", display_name="Logic AND", description="Logical AND gate", icon="sprites/gui/logic_and.png")
class LogicGateNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), gate_type: str = "and", node_id: str = None, name: str = None, node_type: str = None):
        final_name = name or f"Logic_{gate_type.upper()}"
        final_type = node_type or f"logic_{gate_type}"
        super().__init__(node_id=node_id, position=position, name=final_name, node_type=final_type)
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
    def serialize(self) -> dict:
        data = super().serialize()
        data["gate_type"] = self.gate_type
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'LogicGateNode':
        node = super().deserialize(data)
        node.gate_type = data.get("gate_type", "and")
        node.node_type = f"logic_{node.gate_type}"
        node.name = data.get("name", f"Logic_{node.gate_type.upper()}")
        return node

@register_node_type("logic_or", display_name="Logic OR", description="Logical OR gate", icon="sprites/gui/logic_or.png")
class LogicOrNode(LogicGateNode):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(position=position, gate_type="or", node_id=node_id, name=name, node_type=node_type)
    @classmethod
    def deserialize(cls, data: dict) -> 'LogicOrNode':
        return LogicGateNode.deserialize(data)

@register_node_type("logic_not", display_name="Logic NOT", description="Logical NOT gate", icon="sprites/gui/logic_not.png")
class LogicNotNode(LogicGateNode):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(position=position, gate_type="not", node_id=node_id, name=name, node_type=node_type)
    @classmethod
    def deserialize(cls, data: dict) -> 'LogicNotNode':
        return LogicGateNode.deserialize(data)

@register_node_type("logic_xor", display_name="Logic XOR", description="Logical XOR gate", icon="sprites/gui/logic_xor.png")
class LogicXorNode(LogicGateNode):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(position=position, gate_type="xor", node_id=node_id, name=name, node_type=node_type)
    @classmethod
    def deserialize(cls, data: dict) -> 'LogicXorNode':
        return LogicGateNode.deserialize(data)

@register_node_type("math_add", display_name="Math Add", description="Add two numbers", icon="sprites/gui/math_add.png")
class MathNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), op: str = "add", node_id: str = None, name: str = None, node_type: str = None):
        final_name = name or f"Math_{op.upper()}"
        final_type = node_type or f"math_{op}"
        super().__init__(node_id=node_id, position=position, name=final_name, node_type=final_type)
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
    def serialize(self) -> dict:
        data = super().serialize()
        data["op"] = self.op
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'MathNode':
        node = super().deserialize(data)
        node.op = data.get("op", "add")
        node.node_type = f"math_{node.op}"
        node.name = data.get("name", f"Math_{node.op.upper()}")
        return node

@register_node_type("math_sub", display_name="Math Sub", description="Subtract two numbers", icon="sprites/gui/math_sub.png")
class MathSubNode(MathNode):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(position=position, op="sub", node_id=node_id, name=name, node_type=node_type)
    @classmethod
    def deserialize(cls, data: dict) -> 'MathSubNode':
        return MathNode.deserialize(data)

@register_node_type("math_mul", display_name="Math Mul", description="Multiply two numbers", icon="sprites/gui/math_mul.png")
class MathMulNode(MathNode):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(position=position, op="mul", node_id=node_id, name=name, node_type=node_type)
    @classmethod
    def deserialize(cls, data: dict) -> 'MathMulNode':
        return MathNode.deserialize(data)

@register_node_type("math_div", display_name="Math Div", description="Divide two numbers", icon="sprites/gui/math_div.png")
class MathDivNode(MathNode):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(position=position, op="div", node_id=node_id, name=name, node_type=node_type)
    @classmethod
    def deserialize(cls, data: dict) -> 'MathDivNode':
        return MathNode.deserialize(data)

@register_node_type("script", display_name="Script Node", description="Custom Python script", icon="sprites/gui/script.png")
class ScriptNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Script", node_type=node_type or "script")
        self.color = (100, 50, 150)
        self.add_input("Input", DataType.ANY, None)
        self.add_output("Output", DataType.ANY)
        self.script_code = 'val = inputs.get("Input"); outputs["Output"] = (val if val is not None else 0) * 2'
        self.compile_script()
    def get_context_menu_items(self, manager):
        items = super().get_context_menu_items(manager)
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption("Edit Script...", handler=lambda cm: manager.open_script_editor(self)))
        return items

@register_node_type("output", display_name="Output Display", description="Displays value on screen", icon="sprites/gui/output.png")
class OutputNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Output", node_type=node_type or "output")
        self.color = (200, 50, 50)
        self.add_input("Value", DataType.ANY, None)
        self.add_output("Display", DataType.STRING)
    def _execute_default(self, graph):
        val = self.get_input_value("Value")
        self.set_output_value("Display", str(val))
        gm = get_gizmos()
        if gm: gm.draw_text(position=self.position, text=f"Out: {val}", font_size=16, color=(255, 255, 0), duration=0.1, world_space=True)
        return True

@register_node_type("button", display_name="Button", description="Interactive button", icon="sprites/gui/button.png")
class ButtonNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Button", node_type=node_type or "button")
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
        self.set_output_value_by_name("Pressed", out_val)
        return True
    def serialize(self) -> dict:
        data = super().serialize()
        data["is_pressed"] = False
        data["_prev_pressed"] = False
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'ButtonNode':
        node = super().deserialize(data)
        node.is_pressed = False
        node._prev_pressed = False
        return node

@register_node_type("toggle", display_name="Toggle Switch", description="On/Off switch", icon="sprites/gui/toggle.png")
class ToggleNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Toggle", node_type=node_type or "toggle")
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
        self.set_output_value_by_name("State", self.state)
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
        data["_triggered"] = False
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'ToggleNode':
        node = super().deserialize(data)
        node.state = data.get("state", False)
        node._triggered = False
        return node

@register_node_type("print", display_name="Print Log", description="Prints value to debug log", icon="sprites/gui/print.png")
class PrintNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Print", node_type=node_type or "print")
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
    def serialize(self) -> dict:
        data = super().serialize()
        data["_first_run"] = True
        data["_last_val_str"] = ""
        data["_last_trigger_state"] = False
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'PrintNode':
        node = super().deserialize(data)
        node._first_run = True
        node._last_val_str = ""
        node._last_trigger_state = False
        return node

@register_node_type("oscillator", display_name="Oscillator", description="Sine wave generator", icon="sprites/gui/oscillator.png")
class OscillatorNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Oscillator", node_type=node_type or "oscillator")
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
        self.set_output_value_by_name("Signal", val)
        self.set_output_value_by_name("Bool", val > 0)
        return True

    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        if self.enabled:
            pos = camera.world_to_screen((self.position[0], self.position[1]))
            scale = camera.scaling
            size = (self.size[0] * scale, self.size[1] * scale)
            wave_color = (255, 255, 100)
            start_x, end_x = int(pos[0] + 10 * scale), int(pos[0] + size[0] - 10 * scale)
            mid_y = int(pos[1] + size[1] / 2)
            max_amp_px = int(size[1] / 2 - 10 * scale)
            pts = []
            for i in range(21):
                t = i / 20.0
                x = start_x + (end_x - start_x) * t
                wave_val = math.sin(2 * math.pi * self.frequency * self._time + i * 0.5) * self.amplitude
                y_offset = wave_val * max_amp_px
                y_offset = max(-max_amp_px, min(max_amp_px, y_offset))
                y = mid_y + y_offset
                pts.append((x, y))
            if len(pts) > 1: pygame.draw.lines(scr, wave_color, False, pts, 2)
    def get_context_menu_items(self, manager):
        items = super().get_context_menu_items(manager)
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption(f"Toggle Power ({'ON' if self.enabled else 'OFF'})", handler=lambda cm: manager._toggle_oscillator(self)))
        items.append(ConfigOption("Configure Oscillator...", handler=lambda cm: manager.open_oscillator_config(self)))
        return items
    def serialize(self) -> dict:
        data = super().serialize()
        data["frequency"] = self.frequency
        data["amplitude"] = self.amplitude
        data["offset"] = self.offset
        data["enabled"] = self.enabled
        data["_time"] = 0.0
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'OscillatorNode':
        node = super().deserialize(data)
        node.frequency = data.get("frequency", 1.0)
        node.amplitude = data.get("amplitude", 1.0)
        node.offset = data.get("offset", 0.0)
        node.enabled = data.get("enabled", True)
        node._time = 0.0
        return node

@register_node_type("key_input", display_name="Key Input", description="Keyboard input detector", icon="sprites/gui/key.png")
class KeyInputNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Key Input", node_type=node_type or "key_input")
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
        self.set_output_value_by_name("Pressed", self._is_pressed)
        just_pressed = self._is_pressed and not self._was_pressed
        self.set_output_value_by_name("JustPressed", just_pressed)
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
        data["_is_pressed"] = False
        data["_was_pressed"] = False
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'KeyInputNode':
        node = super().deserialize(data)
        node.set_key(data.get("key_code", pygame.K_SPACE))
        node._is_pressed = False
        node._was_pressed = False
        return node

@register_node_type("light_bulb", display_name="Light Bulb", description="Visual indicator", icon="sprites/gui/bulb.png")
class LightBulbNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Light Bulb", node_type=node_type or "light_bulb")
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
        pygame.draw.circle(scr, draw_color, center, radius)
        pygame.draw.circle(scr, (255, 255, 255), center, radius, 2)
        pygame.draw.rect(scr, self.color if self.enabled else (80, 80, 80), rect, border_radius=4)
        pygame.draw.rect(scr, (255, 255, 255), rect, 2 if self in manager.selected_nodes else 1, border_radius=4)
        font = pygame.font.SysFont("Consolas", 14)
        if self._is_on:
            for i in range(3, 0, -1):
                glow_radius = radius + (i * 4 * scale)
                glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*draw_color, 100 // i), (glow_radius, glow_radius), glow_radius)
                scr.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius))
            pygame.draw.circle(scr, (255, 255, 255), center, int(radius * 0.6))
        scr.blit(font.render(self.name, True, (255, 255, 255)), (pos[0] + 5, pos[1] + 5))
        self._draw_ports(scr, pos, size, manager)
    def serialize(self) -> dict:
        data = super().serialize()
        data["_is_on"] = False
        data["current_color"] = self.color_off
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'LightBulbNode':
        node = super().deserialize(data)
        node._is_on = False
        node.current_color = node.color_off
        return node

@register_node_type("seven_segment", display_name="7-Segment Display", description="Digital number display", icon="sprites/gui/7seg.png")
class SevenSegmentNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "7-Segment", node_type=node_type or "seven_segment")
        self.color: Tuple[int, int, int] = (50, 50, 60)
        self.size: Tuple[int, int] = (140, 200)
        self.seg_active_color: Tuple[int, int, int] = (255, 40, 40)
        self.seg_inactive_color: Tuple[int, int, int] = (70, 20, 20)
        self.segments: list = [False] * 8
        self._seg_rects: list = []
        for i in range(7): self.add_input(f"S{i}", DataType.BOOL, False)
        self.add_input("DP", DataType.BOOL, False)
    def _execute_default(self, graph) -> bool:
        for i in range(8):
            val: bool = bool(self.get_input_value(f"S{i}" if i < 7 else "DP"))
            self.segments[i] = val
        return True
    def _update_segments(self, w: int, h: int, x: int, y: int) -> None:
        sw = max(8, int(w * 0.1))
        hw, hh = int(w * 0.35), int(h * 0.22)
        cx, cy = x + w // 2, y + h // 2
        top_y = y + int(h * 0.18)
        mid_y = y + h // 2
        bot_y = y + int(h * 0.82)
        left_x = x + int(w * 0.2)
        right_x = x + int(w * 0.8)
        dp_r = max(4, int(sw * 0.6))
        dp_x = right_x + int(sw * 1.5)
        dp_y = bot_y + int(sw * 1.5)
        self._seg_rects = [
            {"rect": pygame.Rect(left_x, top_y - sw//2, right_x - left_x, sw), "type": "h"},
            {"rect": pygame.Rect(right_x - sw//2, top_y, sw, mid_y - top_y), "type": "v"},
            {"rect": pygame.Rect(right_x - sw//2, mid_y, sw, bot_y - mid_y), "type": "v"},
            {"rect": pygame.Rect(left_x, bot_y - sw//2, right_x - left_x, sw), "type": "h"},
            {"rect": pygame.Rect(left_x - sw//2, mid_y, sw, bot_y - mid_y), "type": "v"},
            {"rect": pygame.Rect(left_x - sw//2, top_y, sw, mid_y - top_y), "type": "v"},
            {"rect": pygame.Rect(left_x, mid_y - sw//2, right_x - left_x, sw), "type": "h"},
            {"rect": pygame.Rect(dp_x - dp_r, dp_y - dp_r, dp_r*2, dp_r*2), "type": "dot"}
        ]
    def draw(self, scr: pygame.Surface, camera: Any, manager: Any) -> None:
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen(self.position)
        scale = camera.scaling
        w, h = int(self.size[0] * scale), int(self.size[1] * scale)
        x, y = int(pos[0]), int(pos[1])
        self._update_segments(w, h, x, y)
        for i, seg in enumerate(self._seg_rects):
            if i >= len(self.segments): break
            color = self.seg_active_color if self.segments[i] else self.seg_inactive_color
            if seg["type"] == "dot":
                pygame.draw.circle(scr, color, seg["rect"].center, seg["rect"].width // 2)
            else:
                pygame.draw.rect(scr, color, seg["rect"], border_radius=int(seg["rect"].height // 2))
    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()
        data["segments"] = self.segments
        data["size"] = self.size
        data["color"] = list(self.color)
        return data
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'SevenSegmentNode':
        node = super().deserialize(data)
        node.segments = data.get("segments", [False] * 8)
        if len(node.segments) != 8: node.segments = [False] * 8
        node.size = tuple(data.get("size", (140, 200)))
        node.color = tuple(data.get("color", (50, 50, 60)))
        return node


@register_node_type("bin_to_dec", display_name="Bin -> Dec", description="Converts 8-bit binary input to decimal value", icon="sprites/gui/bin_dec.png")
class BinaryToDecimalNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Bin2Dec", node_type=node_type or "bin_to_dec")
        self.color = (100, 150, 200)
        self.size = (140, 220)
        self._in_ids = []
        for i in range(8):
            pname = f"B{i}"
            self.add_input(pname, DataType.BOOL, False)
            self._in_ids.append(pname)
        self._out_val_id = self.add_output("Value", DataType.BINARY)
        self._out_str_id = self.add_output("Str", DataType.STRING)
    def _execute_default(self, graph):
        val = 0
        bits = []
        for i, pname in enumerate(self._in_ids):
            b = bool(self.get_input_value(pname))
            bits.append('1' if b else '0')
            if b: val += (1 << i)
        self.outputs[self._out_val_id].value = val
        self.outputs[self._out_str_id].value = "".join(reversed(bits))
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        w, h = self.size[0] * scale, self.size[1] * scale
        x, y = int(pos[0]), int(pos[1])
        val = self.outputs[self._out_val_id].value
        if val is None: val = 0
        font = pygame.font.SysFont("Consolas", int(12 * scale))
        start_y = y + int(30 * scale)
        row_h = int(20 * scale)
        for i, pname in enumerate(self._in_ids):
            is_high = bool(self.get_input_value(pname))
            color = (0, 255, 0) if is_high else (60, 60, 60)
            rect = pygame.Rect(x + int(10 * scale), start_y + i * row_h, int(15 * scale), int(15 * scale))
            pygame.draw.rect(scr, color, rect, border_radius=int(3 * scale))
            lbl = font.render(f"{7-i}", True, (200, 200, 200))
            scr.blit(lbl, (rect.right + int(5 * scale), rect.top))
        res_txt = font.render(f"Dec: {int(val)}", True, (255, 255, 100))
        scr.blit(res_txt, (x + int(10 * scale), y + int(h - 25 * scale)))
    def serialize(self) -> dict: return super().serialize()
    @classmethod
    def deserialize(cls, data: dict) -> 'BinaryToDecimalNode':
        node = super().deserialize(data)
        node._in_ids = [p.name for p in node.inputs.values()]
        for pid, port in node.outputs.items():
            if port.name == "Value": node._out_val_id = pid
            elif port.name == "Str": node._out_str_id = pid
        return node

@register_node_type("dec_to_bool", display_name="Dec -> Bool", description="Splits binary/decimal value into 8 boolean outputs", icon="sprites/gui/dec_bool.png")
class BinaryToBoolNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Dec2Bool", node_type=node_type or "dec_to_bool")
        self.color = (200, 150, 100)
        self.size = (140, 220)
        self._in_id = self.add_input("Value", DataType.BINARY, 0)
        self._out_ids = []
        for i in range(8):
            pname = f"B{i}"
            self.add_output(pname, DataType.BOOL)
            self._out_ids.append(pname)
    def _execute_default(self, graph):
        val = self.inputs[self._in_id].value
        if val is None: val = 0
        try: val = int(val)
        except (ValueError, TypeError): val = 0
        for i, pname in enumerate(self._out_ids):
            bit = bool((val >> i) & 1)
            self.set_output_value_by_name(pname, bit)
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        w, h = self.size[0] * scale, self.size[1] * scale
        x, y = int(pos[0]), int(pos[1])
        val = self.inputs[self._in_id].value
        if val is None: val = 0
        try: val = int(val)
        except (ValueError, TypeError): val = 0
        font = pygame.font.SysFont("Consolas", int(12 * scale))
        start_y = y + int(30 * scale)
        row_h = int(20 * scale)
        inp_txt = font.render(f"In: {val}", True, (255, 255, 100))
        scr.blit(inp_txt, (x + int(10 * scale), y + int(10 * scale)))
        for i, pname in enumerate(self._out_ids):
            is_high = bool(self.set_output_value_by_name(pname, bool((val >> i) & 1)) or ((val >> i) & 1))
            # Получаем актуальное значение из порта для отрисовки
            port_val = self.outputs[[pid for pid, p in self.outputs.items() if p.name == pname][0]].value
            is_high = bool(port_val)
            color = (0, 255, 0) if is_high else (60, 60, 60)
            rect = pygame.Rect(x + int(10 * scale), start_y + i * row_h, int(15 * scale), int(15 * scale))
            pygame.draw.rect(scr, color, rect, border_radius=int(3 * scale))
            lbl = font.render(f"{7-i}", True, (200, 200, 200))
            scr.blit(lbl, (rect.right + int(5 * scale), rect.top))
    def serialize(self) -> dict: return super().serialize()
    @classmethod
    def deserialize(cls, data: dict) -> 'BinaryToBoolNode':
        node = super().deserialize(data)
        for pid, port in node.inputs.items():
            if port.name == "Value": node._in_id = pid
        node._out_ids = [p.name for p in node.outputs.values()]
        return node

@register_node_type("bin_to_7seg", display_name="Bin -> 7-Seg", description="Converts 4-bit binary to 7-segment signals (0-9, A-F)", icon="sprites/gui/bin_7seg.png")
class BinaryTo7SegNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "Bin27Seg", node_type=node_type or "bin_to_7seg")
        self.color = (150, 100, 200)
        self.size = (140, 180)
        self._in_ids = []
        for i in range(4):
            pname = f"B{i}"
            self.add_input(pname, DataType.BOOL, False)
            self._in_ids.append(pname)
        self._out_ids = []
        segs = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "DP"]
        for s in segs:
            self.add_output(s, DataType.BOOL)
            self._out_ids.append(s)
        self._seg_map = [
            [1,1,1,1,1,1,0], # 0
            [0,1,1,0,0,0,0], # 1
            [1,1,0,1,1,0,1], # 2
            [1,1,1,1,0,0,1], # 3
            [0,1,1,0,0,1,1], # 4
            [1,0,1,1,0,1,1], # 5
            [1,0,1,1,1,1,1], # 6
            [1,1,1,0,0,0,0], # 7
            [1,1,1,1,1,1,1], # 8
            [1,1,1,1,0,1,1], # 9
            [1,1,1,0,1,1,1], # A
            [0,0,1,1,1,1,1], # b
            [1,0,0,1,1,1,0], # C
            [0,1,1,1,1,0,1], # d
            [1,0,0,1,1,1,1], # E
            [1,0,0,0,1,1,1]  # F
        ]
    def _execute_default(self, graph):
        val = 0
        for i, pid in enumerate(self._in_ids):
            if bool(self.get_input_value(pid)): val |= (1 << i)
        val = val & 0xF
        pattern = self._seg_map[val]
        for i, sid in enumerate(self._out_ids):
            v = bool(pattern[i]) if i < 7 else False
            self.set_output_value_by_name(sid, v)
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        x, y = int(pos[0]), int(pos[1])
        val = 0
        for i, pid in enumerate(self._in_ids):
            if bool(self.get_input_value(pid)): val |= (1 << i)
        val = val & 0xF
        hex_chars = "0123456789ABCDEF"
        font = pygame.font.SysFont("Consolas", int(24 * scale))
        txt = font.render(hex_chars[val], True, (255, 255, 100))
        rect = txt.get_rect(center=(x + self.size[0]*scale/2, y + self.size[1]*scale/2))
        scr.blit(txt, rect)
    def serialize(self) -> dict: return super().serialize()
    @classmethod
    def deserialize(cls, data: dict) -> 'BinaryTo7SegNode':
        node = super().deserialize(data)
        node._in_ids = [p.name for p in node.inputs.values()]
        node._out_ids = [p.name for p in node.outputs.values()]
        return node

@register_node_type("full_adder", display_name="Full Adder", description="Adds two bits with carry input", icon="sprites/gui/full_adder.png")
class FullAdderNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "FullAdder", node_type=node_type or "full_adder")
        self.color = (120, 180, 140)
        self.size = (130, 140)
        self._in_a = self.add_input("A", DataType.BOOL, False)
        self._in_b = self.add_input("B", DataType.BOOL, False)
        self._in_cin = self.add_input("Cin", DataType.BOOL, False)
        self._out_sum = self.add_output("Sum", DataType.BOOL)
        self._out_cout = self.add_output("Cout", DataType.BOOL)
    def _execute_default(self, graph):
        a = bool(self.get_input_value("A"))
        b = bool(self.get_input_value("B"))
        cin = bool(self.get_input_value("Cin"))
        s = a ^ b ^ cin
        cout = (a and b) or (cin and (a ^ b))
        self.outputs[self._out_sum].value = s
        self.outputs[self._out_cout].value = cout
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        x, y = int(pos[0]), int(pos[1])
        w, h = self.size[0] * scale, self.size[1] * scale
        font = pygame.font.SysFont("Consolas", int(14 * scale))
        a = bool(self.get_input_value("A"))
        b = bool(self.get_input_value("B"))
        cin = bool(self.get_input_value("Cin"))
        s = a ^ b ^ cin
        cout = (a and b) or (cin and (a ^ b))
        labels = [
            (f"A: {'1' if a else '0'}", (200, 200, 200)),
            (f"B: {'1' if b else '0'}", (200, 200, 200)),
            (f"Cin: {'1' if cin else '0'}", (200, 200, 200)),
            ("---", (100, 100, 100)),
            (f"Sum: {'1' if s else '0'}", (100, 255, 100) if s else (150, 150, 150)),
            (f"Cout: {'1' if cout else '0'}", (255, 100, 100) if cout else (150, 150, 150))
        ]
        start_y = y + int(35 * scale)
        # for i, (txt, color) in enumerate(labels):
        #     surf = font.render(txt, True, color)
        #     scr.blit(surf, (x + int(10 * scale), start_y + i * int(18 * scale)))
    def serialize(self) -> dict: return super().serialize()
    @classmethod
    def deserialize(cls, data: dict) -> 'FullAdderNode':
        node = super().deserialize(data)
        node._in_a = node._in_b = node._in_cin = node._out_sum = node._out_cout = None
        for pid, port in node.inputs.items():
            if port.name == "A": node._in_a = pid
            elif port.name == "B": node._in_b = pid
            elif port.name == "Cin": node._in_cin = pid
        for pid, port in node.outputs.items():
            if port.name == "Sum": node._out_sum = pid
            elif port.name == "Cout": node._out_cout = pid
        return node

@register_node_type("clk_random", display_name="Clocked Random", description="Generates random value on clock rising edge", icon="sprites/gui/random_clk.png")
class ClockedRandomNode(Node):
    def __init__(self, position: Tuple[float, float] = (0, 0), node_id: str = None, name: str = None, node_type: str = None):
        super().__init__(node_id=node_id, position=position, name=name or "ClkRandom", node_type=node_type or "clk_random")
        self.color = (180, 140, 220)
        self.size = (140, 160)
        self.add_input("Clock", DataType.BOOL, False)
        self.add_input("Min", DataType.FLOAT, 0.0)
        self.add_input("Max", DataType.FLOAT, 1.0)
        self.add_output("Value", DataType.FLOAT)
        self.add_output("Int", DataType.INT)
        self.add_output("Bool", DataType.BOOL)
        self._prev_clk = False
        self._current_val = 0.0
        import random
        self._random = random
    def _execute_default(self, graph):
        clk = bool(self.get_input_value("Clock"))
        min_v = float(self.get_input_value("Min") or 0.0)
        max_v = float(self.get_input_value("Max") or 1.0)
        if max_v < min_v: min_v, max_v = max_v, min_v
        if clk and not self._prev_clk:
            self._current_val = self._random.uniform(min_v, max_v)
        self._prev_clk = clk
        val = self._current_val
        self.set_output_value_by_name("Value", val)
        self.set_output_value_by_name("Int", int(val))
        self.set_output_value_by_name("Bool", val > (min_v + (max_v - min_v) * 0.5))
        return True
    def draw(self, scr, camera, manager):
        super().draw(scr, camera, manager)
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        x, y = int(pos[0]), int(pos[1])
        font = pygame.font.SysFont("Consolas", int(12 * scale))
        clk = bool(self.get_input_value("Clock"))
        edge = clk and not self._prev_clk
        val = self._current_val
        min_v = float(self.get_input_value("Min") or 0.0)
        max_v = float(self.get_input_value("Max") or 1.0)
        lines = [
            (f"Range: [{min_v:.1f}, {max_v:.1f}]", (200, 200, 200)),
            (f"Out: {val:.3f}", (255, 255, 100)),
            # (f"Int: {int(val)}", (200, 200, 200)),
            # (f"Clk: {'EDGE' if edge else 'HIGH' if clk else 'LOW'}", (0, 255, 0) if edge else (200, 200, 200))
        ]
        start_y = y + int(30 * scale)
        for i, (txt, color) in enumerate(lines):
            surf = font.render(txt, True, color)
            scr.blit(surf, (x + int(10 * scale), start_y + i * int(18 * scale)))
        # if edge:
        #     center = (int(x + self.size[0]*scale/2), int(y + self.size[1]*scale/2))
        #     pygame.draw.circle(scr, (0, 255, 0), center, int(5 * scale))
    def serialize(self) -> dict:
        data = super().serialize()
        data["_prev_clk"] = False
        return data
    @classmethod
    def deserialize(cls, data: dict) -> 'ClockedRandomNode':
        node = super().deserialize(data)
        node._prev_clk = False
        import random
        node._random = random
        return node