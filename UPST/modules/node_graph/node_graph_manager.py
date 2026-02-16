# UPST/modules/node_graph/node_graph_manager.py
import math
import time

import pygame, pymunk
from typing import Dict, List, Optional, Tuple, Set
from UPST.modules.node_graph.node_core import NodeGraph, Node, NodePort, PortType, DataType
from UPST.debug.debug_manager import Debug
from UPST.modules.node_graph.node_types import OscillatorNode, ToggleNode, LogicGateNode, MathNode, ButtonNode, \
    PrintNode, OutputNode, ScriptNode, KeyInputNode, LightBulbNode
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
        mappings = [
            ("logic_and", LogicGateNode), ("logic_or", LogicGateNode), ("logic_not", LogicGateNode),
            ("logic_xor", LogicGateNode), ("script", ScriptNode), ("output", OutputNode),
            ("math_add", MathNode), ("math_sub", MathNode), ("math_mul", MathNode), ("math_div", MathNode),
            ("button", ButtonNode), ("toggle", ToggleNode),
            ("print", PrintNode), ("oscillator", OscillatorNode), ("key_input", KeyInputNode),
            ("light_bulb", LightBulbNode)
        ]
        for type_name, cls in mappings:
            self.register_node_type(type_name, cls)

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

    def connect_nodes(self, from_node: str, from_port: str, to_node: str, to_port: str, graph: NodeGraph = None) -> \
    Optional[str]:
        graph = graph or self.active_graph
        if not graph or from_node not in graph.nodes or to_node not in graph.nodes: return None
        f_node, t_node = graph.nodes[from_node], graph.nodes[to_node]
        if from_port not in f_node.outputs or to_port not in t_node.inputs: return None
        f_port, t_port = f_node.outputs[from_port], t_node.inputs[to_port]
        if not self._are_types_compatible(f_port.data_type, t_port.data_type):
            Debug.log_warning(f"Type mismatch: Cannot connect {f_port.data_type.name} to {t_port.data_type.name}",
                              "NodeGraph")
            return None
        for conn in graph.connections.values():
            if conn.from_node == from_node and conn.from_port == from_port and conn.to_node == to_node and conn.to_port == to_port:
                return None
        conn_id = graph.connect(from_node, from_port, to_node, to_port)
        get_undo_redo().take_snapshot()
        Debug.log_info(f"Connected {from_node}.{from_port} to {to_node}.{to_port}", "NodeGraph")
        return conn_id

    def update(self, dt: float):
        keys_pressed = pygame.key.get_pressed()
        for graph in self.graphs.values():
            for node in graph.nodes.values():
                if node.node_type == "key_input" and hasattr(node, 'update_state'):
                    node.update_state(keys_pressed)
            graph.evaluate()

    def serialize_for_save(self) -> dict:
        return {"graphs": {k: v.serialize() for k, v in self.graphs.items()},
                "active_graph": self.active_graph.id if self.active_graph else None}

    def deserialize_from_save(self, data: dict):
        self.graphs.clear()
        self.selected_nodes.clear()
        self.selected_connections.clear()
        self.drag_connection_start = None
        self.hovered_port = None
        for gid, gdata in data.get("graphs", {}).items():
            self.graphs[gid] = NodeGraph.deserialize(gdata)
        active_id = data.get("active_graph")
        self.active_graph = self.graphs.get(active_id) if active_id else None
        if not self.active_graph and self.graphs:
            self.active_graph = list(self.graphs.values())[0]
        Debug.log_success("Node graph data loaded", "NodeGraph")

    def get_node_at_world_pos(self, world_pos: tuple) -> Optional[Node]:
        return self.active_graph.get_node_at_position(world_pos) if self.active_graph else None

    def _get_port_color(self, data_type: DataType) -> Tuple[int, int, int]:
        colors = {
            DataType.BOOL: (255, 100, 100), DataType.INT: (100, 200, 100), DataType.FLOAT: (100, 150, 255),
            DataType.STRING: (255, 200, 100), DataType.VECTOR: (200, 100, 255), DataType.OBJECT: (255, 255, 100),
            DataType.ANY: (200, 200, 200)
        }
        return colors.get(data_type, (200, 200, 200))

    def _get_port_at_screen_pos(self, screen_pos: Tuple[int, int]) -> Optional[Tuple[str, Node, NodePort, PortType]]:
        if not self.active_graph: return None
        click_radius = 8.0 * self.app.camera.scaling
        for node in self.active_graph.nodes.values():
            node_scr_pos = self.app.camera.world_to_screen((node.position.x, node.position.y))
            scale = self.app.camera.scaling
            y_off = 30.0
            step = 20.0
            for pid, port in node.inputs.items():
                px, py = node_scr_pos[0], node_scr_pos[1] + y_off
                dist_sq = (screen_pos[0] - px) ** 2 + (screen_pos[1] - py) ** 2
                if dist_sq < (click_radius ** 2): return (pid, node, port, PortType.INPUT)
                y_off += step
            y_off = 30.0
            for pid, port in node.outputs.items():
                px, py = node_scr_pos[0] + (node.size[0] * scale), node_scr_pos[1] + y_off
                dist_sq = (screen_pos[0] - px) ** 2 + (screen_pos[1] - py) ** 2
                if dist_sq < (click_radius ** 2): return (pid, node, port, PortType.OUTPUT)
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
            start = (f_ns[0] + f_node.outputs[conn.from_port].position[0],
                     f_ns[1] + f_node.outputs[conn.from_port].position[1])
            end = (t_ns[0] + t_node.inputs[conn.to_port].position[0], t_ns[1] + t_node.inputs[conn.to_port].position[1])
            dist = abs(end[0] - start[0])
            ctrl_offset = max(dist * 0.5, 50)
            ctrl1, ctrl2 = (start[0] + ctrl_offset, start[1]), (end[0] - ctrl_offset, end[1])
            steps = 20
            for i in range(steps + 1):
                t_val = i / steps
                it = 1.0 - t_val
                bx = (it ** 3 * start[0]) + (3 * it ** 2 * t_val * ctrl1[0]) + (3 * it * t_val ** 2 * ctrl2[0]) + (
                            t_val ** 3 * end[0])
                by = (it ** 3 * start[1]) + (3 * it ** 2 * t_val * ctrl1[1]) + (3 * it * t_val ** 2 * ctrl2[1]) + (
                            t_val ** 3 * end[1])
                if ((screen_pos[0] - bx) ** 2 + (screen_pos[1] - by) ** 2) ** 0.5 < click_threshold:
                    return conn_id
        return None

    def handle_key_down(self, event):
        if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            deleted = False
            for conn_id in list(self.selected_connections):
                self.delete_connection(conn_id)
                deleted = True
            for node in list(self.selected_nodes):
                self.delete_node(node.id)
                deleted = True
            if deleted:
                self.selected_connections.clear()
                self.selected_nodes.clear()

    def handle_node_interaction(self, world_pos: tuple, button: int, event_type: str):
        if not self.active_graph: return False
        node = self.get_node_at_world_pos(world_pos)
        if not node: return False
        handled = False
        if event_type == "down" and hasattr(node, 'on_mouse_down'):
            handled = node.on_mouse_down(world_pos, button)
        elif event_type == "up" and hasattr(node, 'on_mouse_up'):
            handled = node.on_mouse_up(world_pos, button)
        return handled

    def handle_mouse_down(self, world_pos: tuple, button: int):
        if button != 1 or not self.active_graph: return
        screen_pos = self.app.camera.world_to_screen(world_pos)
        mods = pygame.key.get_mods()
        self.handle_node_interaction(world_pos, button, "down")
        node = self.get_node_at_world_pos(world_pos)
        conn_id = self._get_connection_at_screen_pos(screen_pos)
        if conn_id:
            if mods & pygame.KMOD_CTRL:
                self.delete_connection(conn_id)
            else:
                self.selected_connections = [conn_id]
                self.selected_nodes.clear()
            return
        port_hit = self._get_port_at_screen_pos(screen_pos)
        if port_hit:
            pid, n, port, ptype = port_hit
            self.drag_connection_start = (n.id, pid, ptype, port.data_type, screen_pos)
            self.selected_connections.clear()
            return
        if node:
            if not (mods & pygame.KMOD_SHIFT):
                self.selected_nodes = [node]
            else:
                if node in self.selected_nodes:
                    self.selected_nodes.remove(node)
                else:
                    self.selected_nodes.append(node)
            self.selected_connections.clear()
            self.dragging_node = node
            self.drag_offset = (world_pos[0] - node.position[0], world_pos[1] - node.position[1])
        else:
            if not (mods & pygame.KMOD_SHIFT):
                self.selected_nodes.clear()
                self.selected_connections.clear()

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
                    if from_ptype == PortType.OUTPUT:
                        self.connect_nodes(from_nid, from_pid, to_node.id, to_pid)
                    else:
                        self.connect_nodes(to_node.id, to_pid, from_nid, from_pid)
            self.drag_connection_start = None
            self.hovered_port = None
            return
        if self.dragging_node:
            self.dragging_node = None
            get_undo_redo().take_snapshot()

    def get_context_menu_items(self, world_pos: tuple):
        from UPST.gui.windows.context_menu.config_option import ConfigOption
        items = []
        node = self.get_node_at_world_pos(world_pos)
        if node:
            items.append(ConfigOption(f"Delete Node '{node.name}'", handler=lambda cm: self.delete_node(node.id),
                                      icon="sprites/gui/erase.png"))
            items.append(ConfigOption("---", handler=lambda cm: None))
            items.append(ConfigOption("Disconnect All", handler=lambda cm: self._disconnect_all_node(node.id),
                                      icon="sprites/gui/disconnect.png"))

            if isinstance(node, ScriptNode):
                items.append(ConfigOption("---", handler=lambda cm: None))
                items.append(ConfigOption("Edit Script...", handler=lambda cm: self._open_script_editor(node)))
            elif isinstance(node, OscillatorNode):
                items.append(ConfigOption("---", handler=lambda cm: None))
                items.append(ConfigOption(f"Toggle Power ({'ON' if node.enabled else 'OFF'})",
                                          handler=lambda cm: self._toggle_oscillator(node)))
                items.append(
                    ConfigOption("Set Frequency...", handler=lambda cm: self._open_param_dialog(node, "frequency")))
                items.append(
                    ConfigOption("Set Amplitude...", handler=lambda cm: self._open_param_dialog(node, "amplitude")))
            elif isinstance(node, ToggleNode):
                items.append(ConfigOption("---", handler=lambda cm: None))
                items.append(ConfigOption(f"Force State ({'ON' if node.state else 'OFF'})",
                                          handler=lambda cm: self._toggle_force(node)))
            elif isinstance(node, KeyInputNode):
                items.append(ConfigOption("---", handler=lambda cm: None))
                items.append(ConfigOption("Change Key...", handler=lambda cm: self._prompt_change_key(node)))
        else:
            if self.active_graph:
                items.append(ConfigOption("Create Node Here", handler=lambda cm: self._open_spawn_menu(world_pos),
                                          icon="sprites/gui/add.png"))
                items.append(ConfigOption("Create New Graph", handler=lambda cm: self.create_graph(),
                                          icon="sprites/gui/node_graph.png"))
        return items

    def prompt_change_key(self, node: 'KeyInputNode'):
        """Открывает диалог ожидания нажатия клавиши"""
        Debug.log_info(f"Waiting for key press for node {node.name}...", "NodeGraph")
        common_keys = [pygame.K_SPACE, pygame.K_RETURN, pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_UP,
                       pygame.K_DOWN]
        try:
            idx = common_keys.index(node.key_code)
            next_key = common_keys[(idx + 1) % len(common_keys)]
        except ValueError:
            next_key = pygame.K_SPACE

        node.set_key(next_key)
        Debug.log_success(f"Key changed to: {pygame.key.name(next_key).upper()}", "NodeGraph")
    def _disconnect_all_node(self, node_id: str):
        if not self.active_graph: return
        to_remove = [cid for cid, conn in self.active_graph.connections.items() if
                     conn.from_node == node_id or conn.to_node == node_id]
        for cid in to_remove: self.delete_connection(cid)

    def _toggle_oscillator(self, node: 'OscillatorNode'):
        node.enabled = not node.enabled
        Debug.log_info(f"Oscillator {node.name} set to {node.enabled}", "NodeGraph")

    def _toggle_force(self, node: 'ToggleNode'):
        node.state = not node.state
        Debug.log_info(f"Toggle {node.name} forced to {node.state}", "NodeGraph")

    def _open_script_editor(self, node: 'ScriptNode'):
        Debug.log_info(f"Opening script editor for {node.name}", "NodeGraph")
        Debug.log_info(f"Current Script:\n{node.script_code}", "NodeGraph")

    def _open_param_dialog(self, node, param_name: str):
        Debug.log_info(f"Edit parameter {param_name} for {node.name}. (UI Dialog needed)", "NodeGraph")
        if param_name == "frequency" and isinstance(node, OscillatorNode):
            node.update_params(freq=node.frequency * 1.5)

    def _open_spawn_menu(self, pos):
        Debug.log_info(f"Open spawn menu at {pos}", "NodeGraph")

    def handle_mouse_motion(self, world_pos: tuple, buttons: tuple):
        screen_pos = self.app.camera.world_to_screen(world_pos)
        if self.drag_connection_start:
            hit = self._get_port_at_screen_pos(screen_pos)
            if hit:
                h_pid, h_node, h_port, h_ptype = hit
                s_nid, s_pid, s_ptype, s_dtype, _ = self.drag_connection_start
                if h_node.id != s_nid and s_ptype != h_ptype and self._are_types_compatible(s_dtype, h_port.data_type):
                    self.hovered_port = hit
                else:
                    self.hovered_port = None
            else:
                self.hovered_port = None
        else:
            self.hovered_port = self._get_port_at_screen_pos(screen_pos)

        if self.dragging_node and buttons[0] and self.active_graph:
            self.dragging_node.position = pymunk.Vec2d(world_pos[0] - self.drag_offset[0],
                                                       world_pos[1] - self.drag_offset[1])
            self.active_graph._dirty = True

    def _draw_bezier(self, scr: pygame.Surface, start: Tuple[int, int], end: Tuple[int, int],
                     color: Tuple[int, int, int], width: int):
        dist = abs(end[0] - start[0])
        ctrl_offset = max(dist * 0.5, 50)
        ctrl1, ctrl2 = (start[0] + ctrl_offset, start[1]), (end[0] - ctrl_offset, end[1])
        points = [start, ctrl1, ctrl2, end]
        pygame.draw.lines(scr, color, False, points, width)

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

        for node in self.active_graph.nodes.values():
            self._draw_node(scr, camera, node)

    def _draw_node(self, scr: pygame.Surface, camera, node: Node):
        pos = camera.world_to_screen((node.position[0], node.position[1]))
        scale = camera.scaling
        size = (node.size[0] * scale, node.size[1] * scale)
        rect = pygame.Rect(int(pos[0]), int(pos[1]), int(size[0]), int(size[1]))

        base_color = node.color if node.enabled else (80, 80, 80)
        color = base_color
        indicator_drawn = False

        if isinstance(node, ButtonNode):
            if node.is_pressed:
                color = tuple(min(255, c + 60) for c in base_color)
                inner_rect = rect.inflate(-4 * scale, -4 * scale)
                pygame.draw.rect(scr, (255, 255, 255), inner_rect, border_radius=4)
                indicator_drawn = True
        elif isinstance(node, ToggleNode):
            if node.state:
                color = tuple(min(255, c + 40) for c in base_color)

                center = (int(pos[0] + size[0] - 15 * scale), int(pos[1] + 15 * scale))
                pygame.draw.circle(scr, (0, 255, 0), center, int(7 * scale))
                pygame.draw.circle(scr, (255, 255, 255), center, int(3 * scale), 2)
                indicator_drawn = True
            else:
                color = tuple(max(0, c - 40) for c in base_color)
                center = (int(pos[0] + size[0] - 15 * scale), int(pos[1] + 15 * scale))
                pygame.draw.circle(scr, (100, 100, 100), center, int(7 * scale))
                indicator_drawn = True
        elif isinstance(node, OscillatorNode):

            if node.enabled:
                wave_color = (255, 255, 100)
                start_x = int(pos[0] + 10 * scale)
                end_x = int(pos[0] + size[0] - 10 * scale)
                mid_y = int(pos[1] + size[1] / 2)
                amp = int(15 * scale)
                pts = []
                steps = 20
                for i in range(steps + 1):
                    x = start_x + (end_x - start_x) * (i / steps)
                    y = mid_y + math.sin(i * 0.5 + time.time() * node.frequency * 6) * amp
                    pts.append((x, y))
                pygame.draw.lines(scr, wave_color, False, pts, 2)
                indicator_drawn = True

        if isinstance(node, LightBulbNode):
            draw_color = node.current_color
            center = (int(pos[0] + size[0] / 2), int(pos[1] + size[1] / 2))
            radius = int(min(size[0], size[1]) / 2 - 5)

            if node._is_on:
                for i in range(3, 0, -1):
                    glow_radius = radius + (i * 4 * scale)
                    glow_alpha = 100 // i
                    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (*draw_color, glow_alpha), (glow_radius, glow_radius), glow_radius)
                    scr.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius))

                pygame.draw.circle(scr, (255, 255, 255), center, int(radius * 0.6))

            pygame.draw.circle(scr, draw_color, center, radius)
            pygame.draw.circle(scr, (255, 255, 255), center, radius, 2)  # Обводк

        pygame.draw.rect(scr, color, rect, border_radius=4)
        pygame.draw.rect(scr, (255, 255, 255), rect, 2 if node in self.selected_nodes else 1, border_radius=4)

        # Заголовок
        font = pygame.font.SysFont("Consolas", 14)
        title_surf = font.render(node.name, True, (255, 255, 255))
        scr.blit(title_surf, (pos[0] + 5, pos[1] + 5))

        y_off = 30.0
        step = 20.0
        for pid, port in node.inputs.items():
            px, py = pos[0], pos[1] + y_off
            port.position = (px - pos[0], py - pos[1])
            is_hovered = (self.hovered_port and self.hovered_port[1].id == node.id and
                          self.hovered_port[0] == pid and self.drag_connection_start and
                          self._are_types_compatible(self.drag_connection_start[3], port.data_type))
            self._draw_port_circle(scr, int(px), int(py), port.data_type, PortType.INPUT, is_hovered)
            y_off += step

        y_off = 30.0
        for pid, port in node.outputs.items():
            px, py = pos[0] + size[0], pos[1] + y_off
            port.position = (px - pos[0], py - pos[1])
            is_hovered = (self.hovered_port and self.hovered_port[1].id == node.id and
                          self.hovered_port[0] == pid and self.drag_connection_start and
                          self._are_types_compatible(self.drag_connection_start[3], port.data_type))
            self._draw_port_circle(scr, int(px), int(py), port.data_type, PortType.OUTPUT, is_hovered)
            y_off += step

        if node in self.selected_nodes:
            pygame.draw.rect(scr, (0, 255, 0), rect.inflate(6, 6), 2, border_radius=6)

    def _draw_port_circle(self, scr: pygame.Surface, x: int, y: int, dtype: DataType, ptype: PortType,
                          is_hovered: bool):
        color = self._get_port_color(dtype)
        radius = 6
        pygame.draw.circle(scr, (40, 40, 40), (x, y), radius + 2)
        pygame.draw.circle(scr, color, (x, y), radius)
        pygame.draw.circle(scr, (255, 255, 255), (x, y), 2)
        if is_hovered:
            pygame.draw.circle(scr, (0, 255, 0), (x, y), radius + 4, 2)

    def register_console_commands(self, console_handler):
        pass