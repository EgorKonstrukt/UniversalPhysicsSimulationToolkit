import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import pygame

from UPST.config import Config
from dataclasses import dataclass

@dataclass
class Plugin:
    name: str
    version: str
    description: str
    config_class: Optional[type] = None
    on_load: Optional[Callable[["PluginManager", Any], None]] = None
    on_unload: Optional[Callable[["PluginManager", Any], None]] = None
    on_update: Optional[Callable[["PluginManager", float], None]] = None
    on_draw: Optional[Callable[["PluginManager"], None]] = None
    on_event: Optional[Callable[["PluginManager", Any], bool]] = None
    console_commands: Dict[str, Callable] = None

    def __post_init__(self):
        if self.console_commands is None:
            self.console_commands = {}

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_instances: Dict[str, Any] = {}
        self.plugin_modules = {}
        self.plugin_dir = Path("plugins").resolve()
        self.plugin_dir.mkdir(exist_ok=True)
        self.load_all_plugins()

    def discover_plugins(self):
        return [d for d in self.plugin_dir.iterdir() if d.is_dir() and (d / "__init__.py").exists()]

    def _unload_submodules(self, base_name: str):
        submodules = [name for name in sys.modules if name.startswith(base_name + ".")]
        for mod in submodules:
            del sys.modules[mod]

    def load_plugin(self, plugin_dir: Path):
        name = plugin_dir.name
        init_path = plugin_dir / "__init__.py"
        spec = importlib.util.spec_from_file_location(name, init_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {init_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        if not hasattr(module, "PLUGIN"):
            raise AttributeError(f"Plugin {name} missing PLUGIN definition")
        plugin_def: Plugin = module.PLUGIN
        if plugin_def.config_class:
            Config.register_plugin_config(name, plugin_def.config_class)
            config_instance = plugin_def.config_class()
            setattr(self.app.config, name, config_instance)
        plugin_instance = module.PluginImpl(self.app)
        self.plugins[name] = plugin_def
        self.plugin_instances[name] = plugin_instance
        self.plugin_modules[name] = module
        if plugin_def.on_load:
            plugin_def.on_load(self, plugin_instance)
        return plugin_instance

    def unload_plugin(self, name: str):
        if name not in self.plugins:
            return
        plugin_def = self.plugins[name]
        plugin_instance = self.plugin_instances[name]
        if plugin_def.on_unload:
            plugin_def.on_unload(self, plugin_instance)
        self._unload_submodules(name)
        sys.modules.pop(name, None)
        del self.plugins[name]
        del self.plugin_instances[name]
        del self.plugin_modules[name]
        if hasattr(self.app.console_handler, 'unregister_plugin_command'):
            for cmd in plugin_def.console_commands:
                self.app.console_handler.unregister_plugin_command(cmd)

    def reload_plugin(self, name: str):
        plugin_dir = self.plugin_dir / name
        if not plugin_dir.exists():
            raise FileNotFoundError(f"Plugin {name} directory not found")
        self.unload_plugin(name)
        importlib.invalidate_caches()
        self.load_plugin(plugin_dir)
        if hasattr(self.app, 'console_handler'):
            self.register_console_commands(self.app.console_handler)

    def reload_all_plugins(self):
        plugin_names = list(self.plugins.keys())
        for name in plugin_names:
            try:
                self.reload_plugin(name)
                print(f"Reloaded PLUGIN: {name}")
            except Exception as e:
                print(f"Failed to reload plugin {name}: {e}")

    def load_all_plugins(self):
        for plugin_dir in self.discover_plugins():
            try:
                self.load_plugin(plugin_dir)
                print(f"Loaded PLUGIN: {plugin_dir.name}")
            except Exception as e:
                print(f"Failed to load plugin {plugin_dir.name}: {e}")

    def update(self, dt: float):
        for name, plugin in self.plugins.items():
            instance = self.plugin_instances[name]
            if plugin.on_update:
                plugin.on_update(self, instance, dt)

    def draw(self):
        for name, plugin in self.plugins.items():
            instance = self.plugin_instances[name]
            if plugin.on_draw:
                plugin.on_draw(self, instance)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if event.key == pygame.K_F10 and (mods & pygame.KMOD_SHIFT):
                self.reload_all_plugins()
                return True
        for name, plugin in self.plugins.items():
            instance = self.plugin_instances[name]
            if plugin.on_event and plugin.on_event(self, instance, event):
                return True
        return False

    def register_console_commands(self, console_handler):
        console_handler.clear_plugin_commands()
        for name, plugin in self.plugins.items():
            for cmd_name, cmd_func in plugin.console_commands.items():
                bound_func = lambda expr, inst=self.plugin_instances[name], f=cmd_func: f(inst, expr)
                console_handler.register_plugin_command(cmd_name, bound_func)