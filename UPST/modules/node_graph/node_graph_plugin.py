# UPST/modules/node_graph/node_graph_plugin.py
from UPST.modules.node_graph.node_core import Node, DataType
from UPST.modules.node_graph.node_graph_manager import NodeGraphManager
from typing import Dict, Callable
class NodeGraphPlugin:
    def __init__(self, plugin_manager):
        self.pm = plugin_manager
        self.custom_nodes: Dict[str, type] = {}
    def register_custom_node(self, node_type: str, node_class: type):
        self.custom_nodes[node_type] = node_class
        ngm = NodeGraphManager()
        ngm.register_node_type(node_type, node_class)
    def get_node_types(self) -> Dict[str, type]:
        return self.custom_nodes
    def serialize(self, plugin_manager, instance) -> dict:
        return {"custom_nodes": list(self.custom_nodes.keys())}
    def deserialize(self, plugin_manager, instance, state: dict):
        for node_type in state.get("custom_nodes", []):
            if node_type in self.custom_nodes:
                ngm = NodeGraphManager()
                ngm.register_node_type(node_type, self.custom_nodes[node_type])
def setup_plugin_integration(plugin_manager):
    plugin = NodeGraphPlugin(plugin_manager)
    plugin_manager.plugins["node_graph_plugin"] = type('PluginDef', (), {
        "name": "NodeGraphPlugin", "version": "1.0.0", "description": "Custom node support",
        "serialize": plugin.serialize, "deserialize": plugin.deserialize,
        "scripting_symbols": {"CustomNode": Node, "DataType": DataType, "NodeGraphManager": NodeGraphManager}
    })()
    plugin_manager.plugin_instances["node_graph_plugin"] = plugin
    return plugin

