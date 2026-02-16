import pygame
import math
import time
from UPST.modules.node_graph.node_core import Node, DataType, PortType
from UPST.debug.debug_manager import Debug


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
        if self.gate_type == "and":
            res = a and b
        elif self.gate_type == "or":
            res = a or b
        elif self.gate_type == "not":
            res = not a
        elif self.gate_type == "xor":
            res = a != b
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
        if self.op == "add":
            res = a + b
        elif self.op == "sub":
            res = a - b
        elif self.op == "mul":
            res = a * b
        elif self.op == "div":
            res = a / b if b != 0 else 0
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


class OutputNode(Node):
    def __init__(self, position=(0, 0)):
        super().__init__(position=position, name="Output", node_type="output")
        self.color = (200, 50, 50)
        self.add_input("Value", DataType.ANY, None)
        self.add_output("Display", DataType.STRING)

    def _execute_default(self, graph):
        val = self.get_input_value("Value")
        self.set_output_value("Display", str(val))
        from UPST.gizmos.gizmos_manager import get_gizmos
        gm = get_gizmos()
        if gm: gm.draw_text(position=self.position, text=f"Out: {val}", font_size=16, color=(255, 255, 0), duration=0.1,
                            world_space=True)
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
            if port.name == "Input":
                in_val = port.value
            elif port.name == "Trigger":
                trigger_val = port.value if port.value is not None else True

        if trigger_val is None:
            trigger_val = True

        current_val_str = str(in_val)
        should_print = False

        if self._first_run:
            should_print = True
            self._first_run = False
        else:
            if current_val_str != self._last_val_str:
                should_print = True
            elif trigger_val and not self._last_trigger_state:
                should_print = True

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

    def update_params(self, freq=None, amp=None, off=None):
        if freq is not None: self.frequency = max(0.01, freq)
        if amp is not None: self.amplitude = amp
        if off is not None: self.offset = off

    def _execute_default(self, graph):
        dt = 0.016
        self._time += dt

        if not self.enabled:
            val = self.offset
        else:
            val = math.sin(2 * math.pi * self.frequency * self._time) * self.amplitude + self.offset

        self.set_output_value("Signal", val)
        self.set_output_value("Bool", val > 0)
        return True

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