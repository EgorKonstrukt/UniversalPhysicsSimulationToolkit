# UPST/modules/node_graph/node_graph_manager.py
import math, time, pygame, pymunk
from typing import Dict, List, Optional, Tuple, Set
from UPST.modules.node_graph.node_core import NodeGraph, Node, NodePort, PortType, DataType, NodeConnection
from UPST.debug.debug_manager import Debug
from UPST.modules.node_graph.node_types import ScriptNode, OscillatorNode, ToggleNode, KeyInputNode, ButtonNode, LightBulbNode, LogicGateNode, MathNode, PrintNode, OutputNode
from UPST.modules.undo_redo_manager import get_undo_redo
class NodeGraphManager:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None: cls._instance = super().__new__(cls)
        return cls._instance
    def __init__(self, app=None):
        if hasattr(self, '_initialized'): return
        self._initialized = True
        self.app = app
        self.graphs: Dict[str, NodeGraph] = {}
        self.active_graph: Optional[NodeGraph] = None
        self.selected_nodes: List[Node] = []
        self.selected_connections: List[str] = []
        self.dragging_node: Optional[Node] = None
        self.drag_offset: Tuple[float, float] = (0, 0)
        self.drag_connection_start: Optional[Tuple[str, str, PortType, DataType, Tuple[int, int]]] = None
        self.hovered_port: Optional[Tuple[str, Node, NodePort, PortType]] = None
        self.node_types: Dict[str, type] = {}
        self._register_default_node_types()
    def _register_default_node_types(self):
        mappings = [("logic_and", LogicGateNode), ("logic_or", LogicGateNode), ("logic_not", LogicGateNode), ("logic_xor", LogicGateNode), ("script", ScriptNode), ("output", OutputNode), ("math_add", MathNode), ("math_sub", MathNode), ("math_mul", MathNode), ("math_div", MathNode), ("button", ButtonNode), ("toggle", ToggleNode), ("print", PrintNode), ("oscillator", OscillatorNode), ("key_input", KeyInputNode), ("light_bulb", LightBulbNode)]
        for type_name, cls in mappings: self.register_node_type(type_name, cls)
    def register_node_type(self, type_name: str, node_class: type):
        self.node_types[type_name] = node_class
    def create_graph(self, name: str = "NewGraph") -> NodeGraph:
        graph = NodeGraph(name=name)
        self.graphs[graph.id] = graph
        if not self.active_graph: self.active_graph = graph
        Debug.log_info(f"Created node graph: {name}", "NodeGraph")
        return graph
    def create_node(self, node_type: str, position: tuple, graph: NodeGraph = None) -> Optional[Node]:
        graph = graph or self.active_graph
        if not graph: graph = self.create_graph()
        if node_type not in self.node_types: return None
        node_class = self.node_types[node_type]
        node = node_class(position=position)
        node.node_type = node_type
        graph.add_node(node)
        get_undo_redo().take_snapshot()
        Debug.log_info(f"Created node: {node.name} at {position}", "NodeGraph")
        return node
    def delete_node(self, node_id: str, graph: NodeGraph = None):
        graph = graph or self.active_graph
        if graph and node_id in graph.nodes:
            graph.remove_node(node_id)
            self.selected_nodes = [n for n in self.selected_nodes if n.id != node_id]
            self.selected_connections = [c for c in self.selected_connections if c in graph.connections]
            get_undo_redo().take_snapshot()
            Debug.log_info(f"Deleted node: {node_id}", "NodeGraph")
    def delete_connection(self, conn_id: str, graph: NodeGraph = None):
        graph = graph or self.active_graph
        if graph and conn_id in graph.connections:
            graph.disconnect(conn_id)
            if conn_id in self.selected_connections: self.selected_connections.remove(conn_id)
            get_undo_redo().take_snapshot()
            Debug.log_info(f"Deleted connection: {conn_id}", "NodeGraph")
    def _are_types_compatible(self, type_a: DataType, type_b: DataType) -> bool:
        if type_a == DataType.ANY or type_b == DataType.ANY: return True
        if type_a == type_b: return True
        compatible_pairs: Set[frozenset] = {frozenset({DataType.INT, DataType.FLOAT})}
        return frozenset({type_a, type_b}) in compatible_pairs
    def connect_nodes(self, from_node: str, from_port: str, to_node: str, to_port: str, graph: NodeGraph = None) -> Optional[str]:
        graph = graph or self.active_graph
        if not graph or from_node not in graph.nodes or to_node not in graph.nodes: return None
        f_node, t_node = graph.nodes[from_node], graph.nodes[to_node]
        if from_port not in f_node.outputs or to_port not in t_node.inputs: return None
        f_port, t_port = f_node.outputs[from_port], t_node.inputs[to_port]
        if not self._are_types_compatible(f_port.data_type, t_port.data_type):
            Debug.log_warning(f"Type mismatch: Cannot connect {f_port.data_type.name} to {t_port.data_type.name}", "NodeGraph")
            return None
        for conn in graph.connections.values():
            if conn.from_node == from_node and conn.from_port == from_port and conn.to_node == to_node and conn.to_port == to_port: return None
        conn_id = graph.connect(from_node, from_port, to_node, to_port)
        get_undo_redo().take_snapshot()
        Debug.log_info(f"Connected {from_node}.{from_port} to {to_node}.{to_port}", "NodeGraph")
        return conn_id
    def update(self, dt: float):
        keys_pressed = pygame.key.get_pressed()
        for graph in self.graphs.values():
            for node in graph.nodes.values():
                if node.node_type == "key_input" and hasattr(node, 'update_state'): node.update_state(keys_pressed)
            graph.evaluate()
    def serialize_for_save(self) -> dict:
        return {"graphs": {k: v.serialize() for k, v in self.graphs.items()}, "active_graph": self.active_graph.id if self.active_graph else None}
    def deserialize_from_save(self, data: dict):
        self.graphs.clear()
        self.selected_nodes.clear()
        self.selected_connections.clear()
        self.drag_connection_start = None
        self.hovered_port = None
        for gid, gdata in data.get("graphs", {}).items():
            self.graphs[gid] = self._deserialize_graph_with_types(gdata)
        active_id = data.get("active_graph")
        self.active_graph = self.graphs.get(active_id) if active_id else None
        if not self.active_graph and self.graphs: self.active_graph = list(self.graphs.values())[0]
        Debug.log_success("Node graph data loaded", "NodeGraph")
    def _deserialize_graph_with_types(self, data: dict) -> NodeGraph:
        graph = NodeGraph(graph_id=data["id"], name=data["name"])
        graph.world_space = data.get("world_space", True)
        for nid, ndata in data.get("nodes", {}).items():
            node_type = ndata.get("node_type", "base")
            if node_type in self.node_types:
                node = self.node_types[node_type].deserialize(ndata)
            else:
                node = Node.deserialize(ndata)
            graph.nodes[nid] = node
        graph.connections = {k: NodeConnection.deserialize(v) for k, v in data.get("connections", {}).items()}
        graph.execution_order = data.get("execution_order", [])
        graph._dirty = True
        return graph
    def get_node_at_world_pos(self, world_pos: tuple) -> Optional[Node]:
        return self.active_graph.get_node_at_position(world_pos) if self.active_graph else None
    def _get_port_color(self, data_type: DataType) -> Tuple[int, int, int]:
        colors = {DataType.BOOL: (255, 100, 100), DataType.INT: (100, 200, 100), DataType.FLOAT: (100, 150, 255), DataType.STRING: (255, 200, 100), DataType.VECTOR: (200, 100, 255), DataType.OBJECT: (255, 255, 100), DataType.ANY: (200, 200, 200)}
        return colors.get(data_type, (200, 200, 200))
    def _get_port_at_screen_pos(self, screen_pos: Tuple[int, int]) -> Optional[Tuple[str, Node, NodePort, PortType]]:
        if not self.active_graph: return None
        click_radius = 8.0 * self.app.camera.scaling
        for node in self.active_graph.nodes.values():
            node_scr_pos = self.app.camera.world_to_screen((node.position.x, node.position.y))
            scale = self.app.camera.scaling
            y_off, step = 30.0, 20.0
            for pid, port in node.inputs.items():
                px, py = node_scr_pos[0], node_scr_pos[1] + y_off
                if (screen_pos[0] - px) ** 2 + (screen_pos[1] - py) ** 2 < (click_radius ** 2): return (pid, node, port, PortType.INPUT)
                y_off += step
            y_off = 30.0
            for pid, port in node.outputs.items():
                px, py = node_scr_pos[0] + (node.size[0] * scale), node_scr_pos[1] + y_off
                if (screen_pos[0] - px) ** 2 + (screen_pos[1] - py) ** 2 < (click_radius ** 2): return (pid, node, port, PortType.OUTPUT)
                y_off += step
        return None
    def _get_connection_at_screen_pos(self, screen_pos: Tuple[int, int]) -> Optional[str]:
        if not self.active_graph: return None
        click_threshold = 6.0
        for conn_id, conn in self.active_graph.connections.items():
            if conn.from_node not in self.active_graph.nodes or conn.to_node not in self.active_graph.nodes: continue
            f_node, t_node = self.active_graph.nodes[conn.from_node], self.active_graph.nodes[conn.to_node]
            if conn.from_port not in f_node.outputs or conn.to_port not in t_node.inputs: continue
            f_ns = self.app.camera.world_to_screen((f_node.position.x, f_node.position.y))
            t_ns = self.app.camera.world_to_screen((t_node.position.x, t_node.position.y))
            start = (f_ns[0] + f_node.outputs[conn.from_port].position[0], f_ns[1] + f_node.outputs[conn.from_port].position[1])
            end = (t_ns[0] + t_node.inputs[conn.to_port].position[0], t_ns[1] + t_node.inputs[conn.to_port].position[1])
            dist = abs(end[0] - start[0])
            ctrl_offset = max(dist * 0.5, 50)
            ctrl1, ctrl2 = (start[0] + ctrl_offset, start[1]), (end[0] - ctrl_offset, end[1])
            for i in range(21):
                t_val = i / 20.0
                it = 1.0 - t_val
                bx = (it ** 3 * start[0]) + (3 * it ** 2 * t_val * ctrl1[0]) + (3 * it * t_val ** 2 * ctrl2[0]) + (t_val ** 3 * end[0])
                by = (it ** 3 * start[1]) + (3 * it ** 2 * t_val * ctrl1[1]) + (3 * it * t_val ** 2 * ctrl2[1]) + (t_val ** 3 * end[1])
                if ((screen_pos[0] - bx) ** 2 + (screen_pos[1] - by) ** 2) ** 0.5 < click_threshold: return conn_id
        return None
    def handle_key_down(self, event):
        if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            deleted = False
            for conn_id in list(self.selected_connections): self.delete_connection(conn_id); deleted = True
            for node in list(self.selected_nodes): self.delete_node(node.id); deleted = True
            if deleted: self.selected_connections.clear(); self.selected_nodes.clear()
    def handle_node_interaction(self, world_pos: tuple, button: int, event_type: str):
        if not self.active_graph: return False
        node = self.get_node_at_world_pos(world_pos)
        if not node: return False
        handled = False
        if event_type == "down" and hasattr(node, 'on_mouse_down'): handled = node.on_mouse_down(world_pos, button)
        elif event_type == "up" and hasattr(node, 'on_mouse_up'): handled = node.on_mouse_up(world_pos, button)
        return handled
    def handle_mouse_down(self, world_pos: tuple, button: int):
        if button != 1 or not self.active_graph: return
        screen_pos = self.app.camera.world_to_screen(world_pos)
        mods = pygame.key.get_mods()
        self.handle_node_interaction(world_pos, button, "down")
        node = self.get_node_at_world_pos(world_pos)
        conn_id = self._get_connection_at_screen_pos(screen_pos)
        if conn_id:
            if mods & pygame.KMOD_CTRL: self.delete_connection(conn_id)
            else: self.selected_connections = [conn_id]; self.selected_nodes.clear()
            return
        port_hit = self._get_port_at_screen_pos(screen_pos)
        if port_hit:
            pid, n, port, ptype = port_hit
            self.drag_connection_start = (n.id, pid, ptype, port.data_type, screen_pos)
            self.selected_connections.clear()
            return
        if node:
            if not (mods & pygame.KMOD_SHIFT): self.selected_nodes = [node]
            else:
                if node in self.selected_nodes: self.selected_nodes.remove(node)
                else: self.selected_nodes.append(node)
            self.selected_connections.clear()
            self.dragging_node = node
            self.drag_offset = (world_pos[0] - node.position[0], world_pos[1] - node.position[1])
        else:
            if not (mods & pygame.KMOD_SHIFT): self.selected_nodes.clear(); self.selected_connections.clear()
    def handle_mouse_up(self, world_pos: tuple, button: int):
        if button != 1: return
        screen_pos = self.app.camera.world_to_screen(world_pos)
        self.handle_node_interaction(world_pos, button, "up")
        if self.drag_connection_start:
            from_nid, from_pid, from_ptype, from_dtype, _ = self.drag_connection_start
            target_hit = self._get_port_at_screen_pos(screen_pos)
            if target_hit:
                to_pid, to_node, to_port, to_ptype = target_hit
                if to_node.id != from_nid and from_ptype != to_ptype:
                    if from_ptype == PortType.OUTPUT: self.connect_nodes(from_nid, from_pid, to_node.id, to_pid)
                    else: self.connect_nodes(to_node.id, to_pid, from_nid, from_pid)
            self.drag_connection_start = None; self.hovered_port = None
            return
        if self.dragging_node: self.dragging_node = None; get_undo_redo().take_snapshot()
    def get_context_menu_items(self, world_pos: tuple):
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items = []
        node = self.get_node_at_world_pos(world_pos)
        if node:
            items.append(ConfigOption(f"Delete Node '{node.name}'", handler=lambda cm: self.delete_node(node.id), icon="sprites/gui/erase.png"))
            items.append(ConfigOption("---", handler=lambda cm: None))
            items.append(ConfigOption("Disconnect All", handler=lambda cm: self._disconnect_all_node(node.id), icon="sprites/gui/disconnect.png"))
            if isinstance(node, ScriptNode): items.append(ConfigOption("Edit Script...", handler=lambda cm: self._open_script_editor(node)))
            elif isinstance(node, OscillatorNode): items.append(ConfigOption(f"Toggle Power ({'ON' if node.enabled else 'OFF'})", handler=lambda cm: self._toggle_oscillator(node)))
            elif isinstance(node, ToggleNode): items.append(ConfigOption(f"Force State ({'ON' if node.state else 'OFF'})", handler=lambda cm: self._toggle_force(node)))
            elif isinstance(node, KeyInputNode): items.append(ConfigOption("Change Key...", handler=lambda cm: self._prompt_change_key(node)))
        else:
            if self.active_graph:
                items.append(ConfigOption("Create Node Here", handler=lambda cm: self._open_spawn_menu(world_pos), icon="sprites/gui/add.png"))
                items.append(ConfigOption("Create New Graph", handler=lambda cm: self.create_graph(), icon="sprites/gui/node_graph.png"))
        return items
    def prompt_change_key(self, node):
        common_keys = [pygame.K_SPACE, pygame.K_RETURN, pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_UP, pygame.K_DOWN]
        try: idx = common_keys.index(node.key_code); next_key = common_keys[(idx + 1) % len(common_keys)]
        except ValueError: next_key = pygame.K_SPACE
        node.set_key(next_key)
        Debug.log_success(f"Key changed to: {pygame.key.name(next_key).upper()}", "NodeGraph")
    def _disconnect_all_node(self, node_id: str):
        if not self.active_graph: return
        to_remove = [cid for cid, conn in self.active_graph.connections.items() if conn.from_node == node_id or conn.to_node == node_id]
        for cid in to_remove: self.delete_connection(cid)
    def _toggle_oscillator(self, node): node.enabled = not node.enabled
    def _toggle_force(self, node): node.state = not node.state
    def _open_script_editor(self, node): Debug.log_info(f"Opening script editor for {node.name}", "NodeGraph")
    def _open_spawn_menu(self, pos): Debug.log_info(f"Open spawn menu at {pos}", "NodeGraph")
    def handle_mouse_motion(self, world_pos: tuple, buttons: tuple):
        screen_pos = self.app.camera.world_to_screen(world_pos)
        if self.drag_connection_start:
            hit = self._get_port_at_screen_pos(screen_pos)
            if hit:
                h_pid, h_node, h_port, h_ptype = hit
                s_nid, s_pid, s_ptype, s_dtype, _ = self.drag_connection_start
                if h_node.id != s_nid and s_ptype != h_ptype and self._are_types_compatible(s_dtype, h_port.data_type): self.hovered_port = hit
                else: self.hovered_port = None
            else: self.hovered_port = None
        else: self.hovered_port = self._get_port_at_screen_pos(screen_pos)
        if self.dragging_node and buttons[0] and self.active_graph:
            self.dragging_node.position = pymunk.Vec2d(world_pos[0] - self.drag_offset[0], world_pos[1] - self.drag_offset[1])
            self.active_graph._dirty = True
    def _draw_bezier(self, scr: pygame.Surface, start: Tuple[int, int], end: Tuple[int, int], color: Tuple[int, int, int], width: int):
        dist = abs(end[0] - start[0])
        ctrl_offset = max(dist * 0.5, 50)
        ctrl1, ctrl2 = (start[0] + ctrl_offset, start[1]), (end[0] - ctrl_offset, end[1])
        pygame.draw.lines(scr, color, False, [start, ctrl1, ctrl2, end], width)
    def draw(self, scr: pygame.Surface, camera):
        if not self.active_graph: return
        for conn_id, conn in self.active_graph.connections.items():
            if conn.from_node not in self.active_graph.nodes or conn.to_node not in self.active_graph.nodes: continue
            f_node, t_node = self.active_graph.nodes[conn.from_node], self.active_graph.nodes[conn.to_node]
            if conn.from_port not in f_node.outputs or conn.to_port not in t_node.inputs: continue
            f_port = f_node.outputs[conn.from_port]
            f_ns = camera.world_to_screen((f_node.position.x, f_node.position.y))
            t_ns = camera.world_to_screen((t_node.position.x, t_node.position.y))
            start_pos = (int(f_ns[0] + f_port.position[0]), int(f_ns[1] + f_port.position[1]))
            t_port = t_node.inputs[conn.to_port]
            end_pos = (int(t_ns[0] + t_port.position[0]), int(t_ns[1] + t_port.position[1]))
            is_selected = conn_id in self.selected_connections
            color = self._get_port_color(f_port.data_type)
            width = 5 if is_selected else 3
            draw_color = (255, 255, 255) if is_selected else color
            self._draw_bezier(scr, start_pos, end_pos, draw_color, width)
        if self.drag_connection_start:
            fnid, fpid, fptype, fdtype, start_screen = self.drag_connection_start
            if fnid in self.active_graph.nodes:
                node = self.active_graph.nodes[fnid]
                ns = camera.world_to_screen((node.position.x, node.position.y))
                port = node.outputs.get(fpid) or node.inputs.get(fpid)
                if port:
                    start_pos = (int(ns[0] + port.position[0]), int(ns[1] + port.position[1]))
                    end_pos = pygame.mouse.get_pos()
                    line_color = (0, 255, 0) if self.hovered_port else (255, 50, 50)
                    self._draw_bezier(scr, start_pos, end_pos, line_color, 2)
        for node in self.active_graph.nodes.values(): node.draw(scr, camera, self)