# UPST/modules/node_graph/node_core.py
import uuid, pygame, pymunk, math, time
from typing import Dict, List, Optional, Any, Callable, Tuple, Set, Type
from dataclasses import dataclass, field
from enum import Enum
from UPST.config import config
from UPST.debug.debug_manager import Debug

class PortType(Enum):
    INPUT = 0
    OUTPUT = 1

class DataType(Enum):
    BOOL = 0
    INT = 1
    FLOAT = 2
    STRING = 3
    VECTOR = 4
    OBJECT = 5
    ANY = 6
    BINARY = 7

@dataclass
class NodePort:
    id: str
    name: str
    port_type: PortType
    data_type: DataType
    value: Any = None
    connections: List[str] = field(default_factory=list)
    position: Tuple[float, float] = (0, 0)
    def serialize(self) -> dict:
        return {"id": self.id, "name": self.name, "port_type": self.port_type.value, "data_type": self.data_type.value, "value": self.value, "connections": self.connections, "position": self.position}
    @classmethod
    def deserialize(cls, data: dict) -> 'NodePort':
        return cls(id=data["id"], name=data["name"], port_type=PortType(data["port_type"]), data_type=DataType(data["data_type"]), value=data.get("value"), connections=data.get("connections", []), position=tuple(data.get("position", (0, 0))))

@dataclass
class NodeConnection:
    id: str
    from_node: str
    from_port: str
    to_node: str
    to_port: str
    def serialize(self) -> dict:
        return {"id": self.id, "from_node": self.from_node, "from_port": self.from_port, "to_node": self.to_node, "to_port": self.to_port}
    @classmethod
    def deserialize(cls, data: dict) -> 'NodeConnection':
        return cls(id=data["id"], from_node=data["from_node"], from_port=data["from_port"], to_node=data["to_node"], to_port=data["to_port"])

class Node:
    tool_name: str = "Base Node"
    tool_description: str = "A basic node."
    tool_icon_path: str = "sprites/gui/node.png"
    def __init__(self, node_id: str = None, position: Tuple[float, float] = (0, 0), name: str = "Node", node_type: str = "base"):
        self.id = node_id or str(uuid.uuid4())
        self.position = pymunk.Vec2d(*position)
        self.name = name
        self.node_type = node_type
        self.inputs: Dict[str, NodePort] = {}
        self.outputs: Dict[str, NodePort] = {}
        self.script_code: str = ""
        self.enabled: bool = True
        self.color: Tuple[int, int, int] = (100, 100, 150)
        self.size: Tuple[float, float] = (150, 100)
        self._compiled_fn: Optional[Callable] = None
        self._last_output: Dict[str, Any] = {}
        self._execution_order: int = 0
        self.custom_data: Dict[str, Any] = {}
    def add_input(self, name: str, data_type: DataType = DataType.ANY, default: Any = None) -> str:
        port_id = f"in_{name}_{uuid.uuid4().hex[:8]}"
        self.inputs[port_id] = NodePort(id=port_id, name=name, port_type=PortType.INPUT, data_type=data_type, value=default)
        return port_id
    def add_output(self, name: str, data_type: DataType = DataType.ANY) -> str:
        port_id = f"out_{name}_{uuid.uuid4().hex[:8]}"
        self.outputs[port_id] = NodePort(id=port_id, name=name, port_type=PortType.OUTPUT, data_type=data_type)
        return port_id
    def get_input_value(self, port_identifier: str) -> Any:
        if port_identifier in self.inputs: return self.inputs[port_identifier].value
        for pid, port in self.inputs.items():
            if port.name == port_identifier: return port.value
        return None
    def set_output_value(self, port_identifier: str, value: Any):
        if port_identifier in self.outputs:
            self.outputs[port_identifier].value = value
            self._last_output[port_identifier] = value
            return
        for pid, port in self.outputs.items():
            if port.name == port_identifier:
                port.value = value
                self._last_output[pid] = value
                return
    def set_output_value_by_name(self, name: str, value: Any):
        for pid, port in self.outputs.items():
            if port.name == name:
                port.value = value
                self._last_output[pid] = value
                return
    def execute(self, graph: 'NodeGraph') -> bool:
        if not self.enabled: return False
        try:
            if self.script_code and self._compiled_fn:
                ns = {"inputs": {p.name: p.value for p in self.inputs.values()}, "outputs": {}, "graph": graph, "node": self, "pymunk": pymunk, "math": math, "random": __import__("random"), "Debug": Debug, "config": config, "time": time, "custom_data": self.custom_data}
                exec(self._compiled_fn, ns, ns)
                for name, val in ns.get("outputs", {}).items(): self.set_output_value(name, val)
                return True
            return self._execute_default(graph)
        except Exception as e:
            Debug.log_error(f"Node {self.name} execution error: {e}", "NodeGraph")
            return False
    def _execute_default(self, graph: 'NodeGraph') -> bool: return True
    def compile_script(self):
        if self.script_code:
            try: self._compiled_fn = compile(self.script_code, f"<node_{self.id}>", "exec")
            except Exception as e: Debug.log_error(f"Script compilation failed: {e}", "NodeGraph"); self._compiled_fn = None
    def draw(self, scr: pygame.Surface, camera, manager: 'NodeGraphManager'):
        pos = camera.world_to_screen((self.position[0], self.position[1]))
        scale = camera.scaling
        size = (self.size[0] * scale, self.size[1] * scale)
        rx, ry, rw, rh = int(pos[0]), int(pos[1]), int(size[0]), int(size[1])
        rect = pygame.Rect(rx, ry, rw, rh)
        base_color = self.color if self.enabled else (80, 80, 80)
        pygame.gfxdraw.box(scr, rect, base_color)
        border_w = 2 if self in manager.selected_nodes else 1
        pygame.gfxdraw.rectangle(scr, rect, (255, 255, 255))
        if border_w > 1: pygame.gfxdraw.rectangle(scr, rect.inflate(-2, -2), (255, 255, 255))
        font = pygame.font.SysFont("Consolas", 14)
        scr.blit(font.render(self.name, True, (255, 255, 255)), (rx + 5, ry + 5))
        self._draw_ports(scr, pos, size, manager)
        if self in manager.selected_nodes:
            ir = rect.inflate(6, 6)
            pygame.gfxdraw.rectangle(scr, ir, (0, 255, 0))
    def _draw_ports(self, scr, pos, size, manager):
        scale = manager.app.camera.scaling
        y_off, step = 30.0*scale, 20.0*scale
        for pid, port in self.inputs.items():
            px, py = pos[0], pos[1] + y_off
            port.position = (px - pos[0], py - pos[1])
            is_hovered = manager.hovered_port and manager.hovered_port[1].id == self.id and manager.hovered_port[0] == pid
            self._draw_port_circle(scr, int(px), int(py), port.data_type, PortType.INPUT, is_hovered, manager)
            y_off += step
        y_off = 30.0*scale
        for pid, port in self.outputs.items():
            px, py = pos[0] + size[0], pos[1] + y_off
            port.position = (px - pos[0], py - pos[1])
            is_hovered = manager.hovered_port and manager.hovered_port[1].id == self.id and manager.hovered_port[0] == pid
            self._draw_port_circle(scr, int(px), int(py), port.data_type, PortType.OUTPUT, is_hovered, manager)
            y_off += step
    def _draw_port_circle(self, scr, x, y, dtype, ptype, is_hovered, manager):
        color = manager._get_port_color(dtype)
        radius = int(6 * manager.app.camera.scaling)
        if radius < 1: radius = 1
        if radius > 32767: radius = 32767
        pygame.gfxdraw.filled_circle(scr, x, y, radius+2, (40, 40, 40))
        if dtype == DataType.BOOL:
            val = None
            if ptype == PortType.INPUT: val = self.get_input_value(ptype.name.lower() + "_port")
            else:
                if self._last_output: val = list(self._last_output.values())[0]
            if val is True: color = (255, 150, 150)
            elif val is False: color = (100, 0, 0)
        pygame.gfxdraw.filled_circle(scr, x, y, radius, color)
        if is_hovered: pygame.gfxdraw.aacircle(scr, x, y, radius + 4, (0, 255, 0))
    def get_context_menu_items(self, manager: 'NodeGraphManager') -> List:
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items = []
        items.append(ConfigOption(f"Delete Node '{self.name}'", handler=lambda cm: manager.delete_node(self.id), icon="sprites/gui/erase.png"))
        items.append(ConfigOption("---", handler=lambda cm: None))
        items.append(ConfigOption("Disconnect All", handler=lambda cm: manager._disconnect_all_node(self.id), icon="sprites/gui/disconnect.png"))
        return items
    def serialize(self) -> dict:
        return {"id": self.id, "position": (self.position.x, self.position.y), "name": self.name, "node_type": self.node_type, "inputs": {k: v.serialize() for k, v in self.inputs.items()}, "outputs": {k: v.serialize() for k, v in self.outputs.items()}, "script_code": self.script_code, "enabled": self.enabled, "color": self.color, "size": self.size, "execution_order": self._execution_order, "custom_data": self.custom_data}
    @classmethod
    def deserialize(cls, data: dict) -> 'Node':
        node = cls(node_id=data["id"], position=data["position"], name=data["name"], node_type=data["node_type"])
        node.inputs = {k: NodePort.deserialize(v) for k, v in data.get("inputs", {}).items()}
        node.outputs = {k: NodePort.deserialize(v) for k, v in data.get("outputs", {}).items()}
        node.script_code = data.get("script_code", "")
        node.enabled = data.get("enabled", True)
        node.color = tuple(data.get("color", (100, 100, 150)))
        node.size = tuple(data.get("size", (150, 100)))
        node._execution_order = data.get("execution_order", 0)
        node.custom_data = data.get("custom_data", {})
        if node.script_code: node.compile_script()
        return node

class NodeGraph:
    def __init__(self, graph_id: str = None, name: str = "NodeGraph"):
        self.id = graph_id or str(uuid.uuid4())
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.connections: Dict[str, NodeConnection] = {}
        self.world_space: bool = True
        self.execution_order: List[str] = []
        self._dirty: bool = True
        self._last_evaluation: float = 0
    def add_node(self, node: Node) -> str: self.nodes[node.id] = node; self._dirty = True; return node.id
    def remove_node(self, node_id: str):
        if node_id in self.nodes:
            for conn_id, conn in list(self.connections.items()):
                if conn.from_node == node_id or conn.to_node == node_id: del self.connections[conn_id]
            del self.nodes[node_id]
            self._dirty = True
    def connect(self, from_node: str, from_port: str, to_node: str, to_port: str) -> str:
        conn_id = f"conn_{uuid.uuid4().hex[:8]}"
        self.connections[conn_id] = NodeConnection(id=conn_id, from_node=from_node, from_port=from_port, to_node=to_node, to_port=to_port)
        if from_node in self.nodes and from_port in self.nodes[from_node].outputs: self.nodes[from_node].outputs[from_port].connections.append(conn_id)
        if to_node in self.nodes and to_port in self.nodes[to_node].inputs: self.nodes[to_node].inputs[to_port].connections.append(conn_id)
        self._dirty = True
        return conn_id
    def disconnect(self, conn_id: str):
        if conn_id in self.connections:
            conn = self.connections[conn_id]
            if conn.from_node in self.nodes and conn.from_port in self.nodes[conn.from_node].outputs:
                outs = self.nodes[conn.from_node].outputs[conn.from_port].connections
                if conn_id in outs: outs.remove(conn_id)
            if conn.to_node in self.nodes and conn.to_port in self.nodes[conn.to_node].inputs:
                ins = self.nodes[conn.to_node].inputs[conn.to_port].connections
                if conn_id in ins: ins.remove(conn_id)
            del self.connections[conn_id]
            self._dirty = True
    def _compute_execution_order(self):
        in_degree = {nid: 0 for nid in self.nodes}
        adj = {nid: [] for nid in self.nodes}
        for conn in self.connections.values():
            if conn.from_node in adj and conn.to_node in in_degree:
                adj[conn.from_node].append(conn.to_node)
                in_degree[conn.to_node] += 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0: queue.append(neighbor)
        self.execution_order = order if len(order) == len(self.nodes) else list(self.nodes.keys())
        for i, nid in enumerate(self.execution_order):
            if nid in self.nodes: self.nodes[nid]._execution_order = i
    def evaluate(self):
        if self._dirty: self._compute_execution_order(); self._dirty = False
        for node_id in self.execution_order:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                for conn in self.connections.values():
                    if conn.to_node == node_id and conn.from_node in self.nodes:
                        from_node = self.nodes[conn.from_node]
                        if conn.from_port in from_node.outputs:
                            val = from_node.outputs[conn.from_port].value
                            if conn.to_port in node.inputs: node.inputs[conn.to_port].value = val
                node.execute(self)
        self._last_evaluation = pygame.time.get_ticks() / 1000.0
    def get_node_at_position(self, world_pos: Tuple[float, float]) -> Optional[Node]:
        for node in self.nodes.values():
            x, y = node.position.x, node.position.y
            w, h = node.size
            if x <= world_pos[0] <= x + w and y <= world_pos[1] <= y + h: return node
        return None
    def get_nodes_in_rect(self, rect: pygame.Rect) -> List[Node]:
        selected = []
        for node in self.nodes.values():
            nx, ny = node.position.x, node.position.y
            nw, nh = node.size
            node_rect = pygame.Rect(nx, ny, nw, nh)
            if rect.colliderect(node_rect): selected.append(node)
        return selected
    def serialize(self) -> dict:
        return {"id": self.id, "name": self.name, "world_space": self.world_space, "nodes": {k: v.serialize() for k, v in self.nodes.items()}, "connections": {k: v.serialize() for k, v in self.connections.items()}, "execution_order": self.execution_order}
    @classmethod
    def deserialize(cls, data: dict) -> 'NodeGraph':
        graph = cls(graph_id=data["id"], name=data["name"])
        graph.world_space = data.get("world_space", True)
        graph.nodes = {k: Node.deserialize(v) for k, v in data.get("nodes", {}).items()}
        graph.connections = {k: NodeConnection.deserialize(v) for k, v in data.get("connections", {}).items()}
        graph.execution_order = data.get("execution_order", [])
        graph._dirty = True
        return graph