from .config_option import ConfigOption
import pygame
import pymunk
from UPST.debug.debug_manager import Debug
from UPST.config import config
from UPST.modules.node_graph.node_graph_manager import NodeGraphManager


def _get_node_graph_items(obj, app, plugin_manager, world_pos=None):
    """Получает пункты меню от плагинов (включая NodeGraph) для конкретного объекта."""
    items = []

    if not hasattr(plugin_manager, 'context_menu_contributors'):
        return items

    contributors = plugin_manager.context_menu_contributors

    for item in contributors:
        func = None
        name = "Unknown"

        if isinstance(item, tuple) and len(item) >= 2:
            name, func = item[0], item[1]
        elif callable(item):
            func = item
        else:
            continue

        if not callable(func):
            continue

        try:
            res = func(plugin_manager, obj, world_pos=world_pos)
            if res:
                if isinstance(res, list):
                    items.extend(res)
                else:
                    items.append(res)
        except Exception as e:
            Debug.log_error(f"Context menu contributor '{name}' failed: {e}", "ContextMenu")

    return items


def build_world_menu(app, plugin_manager, world_pos=None):
    base = [
        ConfigOption("Scripts", children=[
            ConfigOption("Run Python Script", handler=lambda cm: cm.ui_manager.show_inline_script_editor(owner=None),
                         icon="sprites/gui/erase.png"),
            ConfigOption("Script Management", handler=lambda cm: cm.open_script_management())
        ], icon="sprites/gui/python.png"),
        ConfigOption("Center to Scene", handler=lambda cm: cm.center_to_scene(), icon="sprites/gui/zoom2scene.png"),
        ConfigOption("Center to Origin", handler=lambda cm: cm.center_to_origin()),
        ConfigOption("Load Contraption...", handler=lambda cm: cm.load_contraption_from(), icon="sprites/gui/load.png"),
    ]

    base.extend(_get_node_graph_items(None, app, plugin_manager, world_pos=world_pos))
    return base


def build_selection_menu(app, plugin_manager):
    base = [
        ConfigOption("Erase All", handler=lambda cm: cm.delete_selected_objects()),
        ConfigOption("Group Manipulate", children=[
            ConfigOption("Freeze/Unfreeze All", handler=lambda cm: cm.toggle_freeze_selected()),
            ConfigOption("Make Static", handler=lambda cm: cm.make_static_selected()),
            ConfigOption("Make Dynamic", handler=lambda cm: cm.make_dynamic_selected()),
            ConfigOption("Reset Positions", handler=lambda cm: cm.reset_positions_selected())
        ]),
        ConfigOption("Save Contraption...", handler=lambda cm: cm.save_contraption_as(), icon="sprites/gui/save.png"),
    ]
    selected = list(app.physics_manager.selected_bodies)
    base.extend(_get_node_graph_items(selected, app, plugin_manager))
    return base


def build_object_menu(obj, app, plugin_manager, world_pos=None):
    ngm = NodeGraphManager()
    is_node = False
    if ngm.active_graph and hasattr(obj, 'id') and obj.id in ngm.active_graph.nodes:
        is_node = True

    if is_node:
        node_items = _get_node_graph_items(obj, app, plugin_manager, world_pos=world_pos)
        if node_items:
            return node_items

    base = [
        ConfigOption("Erase", handler=lambda cm: cm.delete_object(), icon="sprites/gui/erase.png"),
        ConfigOption("Properties", handler=lambda cm: cm.open_properties_window(), icon="sprites/gui/settings.png"),
        ConfigOption("Set Name...", handler=lambda cm: cm.open_rename_dialog(), icon="sprites/gui/text.png"),
        ConfigOption("Duplicate", handler=lambda cm: cm.duplicate_object(), icon="sprites/gui/clone.png"),
        ConfigOption("Freeze/Unfreeze", handler=lambda cm: cm.toggle_freeze_object(), icon="sprites/gui/glue.png"),
        ConfigOption("Set Texture", handler=lambda cm: cm.open_texture_window(), icon="sprites/gui/texture.png"),
        ConfigOption("Reset", children=[
            ConfigOption("Reset Position", handler=lambda cm: cm.reset_position()),
            ConfigOption("Reset Rotation", handler=lambda cm: cm.reset_rotation())
        ], icon="sprites/gui/reload.png"),
        ConfigOption("Body Type", children=[
            ConfigOption("Make Static", handler=lambda cm: cm.make_static()),
            ConfigOption("Make Dynamic", handler=lambda cm: cm.make_dynamic())
        ], icon="sprites/gui/tools/box.png"),
        ConfigOption("Select for Debug", handler=lambda cm: cm.select_for_debug(), icon="sprites/gui/info.png"),
        ConfigOption("Camera", children=[
            ConfigOption("Follow This Object", handler=lambda cm: cm.set_camera_target()),
            ConfigOption(name="Rotate with object", is_checkbox=True,
                         get_state=lambda cm: cm.ui_manager.camera.rotate_with_target,
                         set_state=lambda cm, v: setattr(cm.ui_manager.camera, 'rotate_with_target', v))
        ], icon="sprites/gui/camera.png"),
        ConfigOption("Scripts", children=[
            ConfigOption("Run Python Script", handler=lambda cm: cm.ui_manager.show_inline_script_editor(owner=obj)),
            ConfigOption("Edit Script", handler=lambda cm: cm.edit_script()),
            ConfigOption("Script Management", handler=lambda cm: cm.open_script_management())
        ], icon="sprites/gui/python.png"),
        ConfigOption("Plot Data", handler=lambda cm: cm.open_plotter(), icon="sprites/gui/plot.png")
    ]

    base.extend(_get_node_graph_items(obj, app, plugin_manager, world_pos=world_pos))
    return base


def build_menu_structure(clicked_object, app, plugin_manager, world_pos=None):
    if isinstance(clicked_object, list):
        return build_selection_menu(app, plugin_manager)
    elif clicked_object is None:
        return build_world_menu(app, plugin_manager, world_pos=world_pos)
    else:
        return build_object_menu(clicked_object, app, plugin_manager, world_pos=world_pos)