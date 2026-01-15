from UPST.gui.contex_menu import ConfigOption


def provide_context_items(plugin_manager, plugin_instance, clicked_object):
    if clicked_object is None:
        return [ConfigOption("Global Plugin Action", handler=lambda: print("Global!"))]
    # else:
    #     return [ConfigOption("Inspect with Plugin X", handler=lambda: inspect_obj(clicked_object))]

PLUGIN = Plugin(
    name="context_menu",
    version="1.0.0",
    description="Adds custom context actions",
    author="Test",
    icon_path="sprites/app/fx.png",
    dependency_specs={},
    context_menu_items=provide_context_items
)

class PluginImpl:
    def __init__(self, app): pass