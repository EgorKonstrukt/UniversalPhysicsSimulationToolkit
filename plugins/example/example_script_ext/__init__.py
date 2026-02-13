def my_custom_func(x: float) -> float:
    return x ** 2 + 1

def inject_hooks(plugin_manager, namespace):
    namespace["dynamic_hook_var"] = len(plugin_manager.plugins)  # Example value

class PluginImpl:
    def __init__(self, app):
        self.app = app

PLUGIN = Plugin(
    name="ExampleScriptExt",
    version="1.0.0",
    description="Adds custom functions to scripting",
    scripting_symbols={
        "square_plus_one": my_custom_func,
        "PI_SQ": 9.869604401089358,
    },
    scripting_hooks=inject_hooks,
)