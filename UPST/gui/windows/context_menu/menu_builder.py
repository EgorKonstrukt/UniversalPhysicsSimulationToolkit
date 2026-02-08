from .config_option import ConfigOption
import pygame
import pymunk
from UPST.debug.debug_manager import Debug
from UPST.config import config

def build_world_menu(app, plugin_manager):
    return [
        ConfigOption("Scripts", children=[
            ConfigOption("Run Python Script", handler=lambda cm: cm.ui_manager.show_inline_script_editor(owner=None), icon="sprites/gui/erase.png"),
            ConfigOption("Script Management", handler=lambda cm: cm.open_script_management())
        ], icon="sprites/gui/python.png"),
        ConfigOption("Center to Scene", handler=lambda cm: cm.center_to_scene(), icon="sprites/gui/zoom2scene.png"),
        ConfigOption("Center to Origin", handler=lambda cm: cm.center_to_origin()),
        ConfigOption("Open Plotter", handler=lambda cm: cm.open_plotter(), icon="sprites/gui/plot.png")
    ] + plugin_manager.get_context_menu_items(None)

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
        ConfigOption("Load Contraption...", handler=lambda cm: cm.load_contraption_from(), icon="sprites/gui/load.png"),
    ]
    return base + plugin_manager.get_context_menu_items(list(app.physics_manager.selected_bodies))

def build_object_menu(obj, app, plugin_manager):
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
            ConfigOption(name="Rotate with object", is_checkbox=True, get_state=lambda cm: cm.ui_manager.camera.rotate_with_target, set_state=lambda cm, v: setattr(cm.ui_manager.camera, 'rotate_with_target', v))
        ], icon="sprites/gui/camera.png"),
        ConfigOption("Scripts", children=[
            ConfigOption("Run Python Script", handler=lambda cm: cm.ui_manager.show_inline_script_editor(owner=obj)),
            ConfigOption("Edit Script", handler=lambda cm: cm.edit_script()),
            ConfigOption("Script Management", handler=lambda cm: cm.open_script_management())
        ], icon="sprites/gui/python.png"),
        ConfigOption("Plot Data", handler=lambda cm: cm.open_plotter(), icon="sprites/gui/plot.png")
    ]
    return base + plugin_manager.get_context_menu_items(obj)

def build_menu_structure(clicked_object, app, plugin_manager):
    if isinstance(clicked_object, list):
        return build_selection_menu(app, plugin_manager)
    elif clicked_object is None:
        return build_world_menu(app, plugin_manager)
    else:
        return build_object_menu(clicked_object, app, plugin_manager)