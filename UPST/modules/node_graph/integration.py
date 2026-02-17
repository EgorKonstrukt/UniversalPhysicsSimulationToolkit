# UPST/modules/node_graph/integration.py
import pickle
import pygame
from UPST.modules.node_graph.node_graph_manager import NodeGraphManager
from UPST.debug.debug_manager import Debug
from UPST.modules.node_graph.node_tools import get_all_node_tools

def extend_snapshot_manager(snapshot_manager):
    orig_collect = snapshot_manager._collect_snapshot_data
    orig_load = snapshot_manager.load_snapshot
    def new_collect(self):
        data = orig_collect()
        ngm = NodeGraphManager()
        data["node_graph"] = ngm.serialize_for_save()
        return data
    def new_load(self, snapshot_bytes):
        data = pickle.loads(snapshot_bytes)
        result = orig_load(snapshot_bytes)
        if "node_graph" in data:
            ngm = NodeGraphManager()
            ngm.deserialize_from_save(data["node_graph"])
        return result
    snapshot_manager._collect_snapshot_data = new_collect.__get__(snapshot_manager)
    snapshot_manager.load_snapshot = new_load.__get__(snapshot_manager)
    Debug.log_info("Node Graph integrated with SnapshotManager", "NodeGraph")

def extend_save_load_manager(save_load_manager):
    orig_prepare = save_load_manager._prepare_save_data
    orig_apply = save_load_manager._apply_loaded_data
    def new_prepare(self):
        data = orig_prepare()
        ngm = NodeGraphManager()
        data["node_graph"] = ngm.serialize_for_save()
        return data
    def new_apply(self, data):
        orig_apply(data)
        if "node_graph" in data:
            ngm = NodeGraphManager()
            ngm.deserialize_from_save(data["node_graph"])
    save_load_manager._prepare_save_data = new_prepare.__get__(save_load_manager)
    save_load_manager._apply_loaded_data = new_apply.__get__(save_load_manager)
    Debug.log_info("Node Graph integrated with SaveLoadManager", "NodeGraph")

def register_context_menu(plugin_manager):
    from UPST.gui.windows.context_menu.config_option import ConfigOption
    from UPST.modules.node_graph.node_graph_manager import NodeGraphManager
    def get_items(pm, obj, world_pos=None):
        ngm = NodeGraphManager()
        items = []
        node_at_pos = None
        if world_pos and ngm.active_graph:
            node_at_pos = ngm.get_node_at_world_pos(world_pos)
        target_node = None
        if node_at_pos:
            target_node = node_at_pos
        elif obj and hasattr(obj, 'id') and ngm.active_graph and obj.id in ngm.active_graph.nodes:
            target_node = ngm.active_graph.nodes[obj.id]
        if target_node:
            items.append(ConfigOption(f"Delete Node '{target_node.name}'", handler=lambda cm: ngm.delete_node(target_node.id), icon="sprites/gui/erase.png"))
            items.append(ConfigOption("---", handler=lambda cm: None))
            items.append(ConfigOption("Disconnect All", handler=lambda cm: ngm._disconnect_all_node(target_node.id), icon="sprites/gui/disconnect.png"))
            return items
        if obj is None and world_pos and ngm.active_graph:
            items.append(ConfigOption("Create Node Here", handler=lambda cm: ngm._open_spawn_menu(world_pos), icon="sprites/gui/add.png"))
            items.append(ConfigOption("Create New Graph", handler=lambda cm: ngm.create_graph(), icon="sprites/gui/node_graph.png"))
        return items
    plugin_manager.register_context_menu_contributor("node_graph", get_items)

def register_tools(tool_system):
    tools = get_all_node_tools(tool_system.app)
    for tool in tools:
        tool_system.register_tool(tool)
    Debug.log_info("Node Graph tools registered (auto-discovered)", "NodeGraph")