from dataclasses import dataclass
from typing import Any, Dict
from UPST.modules.plugin_manager import Plugin

@dataclass
class ExamplePluginConfig:
    enabled: bool = True
    counter: int = 0
    message: str = "Hello from plugin"

def on_load(manager, instance):
    print(f"[ExamplePlugin] Loaded with config: {instance.cfg}")

def on_unload(manager, instance):
    print("[ExamplePlugin] Unloaded")

def on_update(manager, instance, dt):
    if instance.cfg.enabled and instance.cfg.counter < 100:
        instance.cfg.counter += 1

def on_draw(manager, instance):
    app = manager.app
    if hasattr(app, 'gui') and instance.cfg.enabled:
        app.gui.draw_text(f"Plugin Counter: {instance.cfg.counter}", (10, 50), color=(255, 255, 0))

PLUGIN = Plugin(
    name="example_plugin",
    version="1.0.0",
    author="Test",
    icon_path="",
    dependency_specs={},
    description="Demonstrates plugin integration with save/load and config.",
    config_class=ExamplePluginConfig,
    on_load=on_load,
    on_unload=on_unload,
    on_update=on_update,
    on_draw=on_draw,
    console_commands={
        "plugin_inc": lambda inst, _: setattr(inst.cfg, 'counter', inst.cfg.counter + 1),
        "plugin_reset": lambda inst, _: setattr(inst.cfg, 'counter', 0)
    }
)

class PluginImpl:
    def __init__(self, app):
        self.app = app
        self.cfg = getattr(app.config, 'example_plugin')

    def serialize(self) -> Dict[str, Any]:
        return {"counter": self.cfg.counter}

    def deserialize(self, state: Dict[str, Any]):
        self.cfg.counter = state.get("counter", 0)