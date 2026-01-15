import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Set
from collections import defaultdict, deque

import pygame

from UPST.config import Config
from dataclasses import dataclass

from packaging.version import Version, InvalidVersion

from UPST.debug.debug_manager import Debug


@dataclass
class Plugin:
    name: str
    version: str
    description: str
    dependency_specs: Dict[str, str]
    config_class: Optional[type] = None
    on_load: Optional[Callable[["PluginManager", Any], None]] = None
    on_unload: Optional[Callable[["PluginManager", Any], None]] = None
    on_update: Optional[Callable[["PluginManager", float], None]] = None
    on_draw: Optional[Callable[["PluginManager"], None]] = None
    on_event: Optional[Callable[["PluginManager", Any], bool]] = None
    console_commands: Dict[str, Callable] = None
    command_help: Dict[str, str] = None  # {"cmd": "brief description"}

    def __post_init__(self):
        if self.console_commands is None:
            self.console_commands = {}
        if self.command_help is None:
            self.command_help = {}

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_instances: Dict[str, Any] = {}
        self.plugin_modules = {}
        self.plugin_dir = Path("plugins").resolve()
        self.plugin_dir.mkdir(exist_ok=True)

    def discover_plugins(self):
        plugins = []
        for item in self.plugin_dir.rglob("*"):
            if item.is_dir() and (item / "__init__.py").exists():
                if item.parent == self.plugin_dir or (item.parent.parent == self.plugin_dir and item.parent != self.plugin_dir):
                    plugins.append(item)
        return sorted(plugins, key=lambda p: str(p))

    def _unload_submodules(self, base_name: str):
        submodules = [name for name in sys.modules if name.startswith(base_name + ".")]
        for mod in submodules:
            del sys.modules[mod]
    def _check_dependency_version(self, dep_name: str, required_spec: str, actual_version: str) -> bool:
        if not required_spec.strip():
            return True
        try:
            actual = Version(actual_version)
            # Поддерживаем только простые операторы: >=, >, ==, <=, <
            if required_spec.startswith(">="):
                return actual >= Version(required_spec[2:].strip())
            elif required_spec.startswith(">"):
                return actual > Version(required_spec[1:].strip())
            elif required_spec.startswith("=="):
                return actual == Version(required_spec[2:].strip())
            elif required_spec.startswith("<="):
                return actual <= Version(required_spec[2:].strip())
            elif required_spec.startswith("<"):
                return actual < Version(required_spec[1:].strip())
            else:
                # интерпретируем как == по умолчанию
                return actual == Version(required_spec.strip())
        except InvalidVersion:
            print(f"Warning: Invalid version format for plugin '{dep_name}': '{actual_version}'")
            return False
    def _topological_sort(self, plugin_dirs: List[Path]) -> List[Path]:
        graph = {}
        name_to_path = {}
        for d in plugin_dirs:
            name = d.name
            graph[name] = []
            name_to_path[name] = d

        for d in plugin_dirs:
            meta = self._read_plugin_metadata(d)
            if meta and hasattr(meta, "dependency_specs"):
                deps = list(meta.dependency_specs.keys())
                graph[d.name].extend(deps)

        all_names = set(graph.keys())
        for name, deps in graph.items():
            for dep in deps:
                if dep not in all_names:
                    raise ImportError(f"Plugin '{name}' depends on non-existent plugin '{dep}'")

        in_degree = {node: 0 for node in graph}
        adj = defaultdict(list)
        for node, deps in graph.items():
            for dep in deps:
                adj[dep].append(node)
                in_degree[node] += 1

        queue = deque([node for node in in_degree if in_degree[node] == 0])
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(graph):
            raise RuntimeError("Circular dependency detected among plugins")

        return [name_to_path[name] for name in order]
    def load_plugin(self, plugin_dir: Path):
        init_path = plugin_dir / "__init__.py"
        module_name = f"plugin_{plugin_dir.relative_to(self.plugin_dir).as_posix().replace('/', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, init_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {init_path}")
        module = importlib.util.module_from_spec(spec)
        module.Plugin = Plugin
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        if not hasattr(module, "PLUGIN"):
            raise AttributeError(f"Plugin at {plugin_dir} missing PLUGIN definition")
        plugin_def: Plugin = module.PLUGIN

        name = plugin_def.name
        if name in self.plugins:
            raise ValueError(f"Plugin name '{name}' already loaded")

        for dep_name, spec_str in plugin_def.dependency_specs.items():
            if dep_name not in self.plugins:
                raise ImportError(f"Plugin '{name}' requires missing dependency '{dep_name}'")
            dep_plugin = self.plugins[dep_name]
            if not self._check_dependency_version(dep_name, spec_str, dep_plugin.version):
                raise ImportError(
                    f"Plugin '{name}' requires {dep_name}{spec_str}, but found {dep_plugin.version}"
                )

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
        plugin_dirs = self.discover_plugins()
        if not plugin_dirs:
            Debug.log_info("No plugins found", "Plugins")
            return

        try:
            sorted_dirs = self._topological_sort(plugin_dirs)
        except (RuntimeError, ImportError) as e:
            Debug.log_error(f"Dependency resolution failed: {e}", "Plugins")
            return

        meta_cache = {}
        for d in plugin_dirs:
            meta = self._read_plugin_metadata(d)
            if meta:
                meta_cache[d] = meta

        self._log_plugin_structure(sorted_dirs, meta_cache)

        loaded_names = set()
        failed_names = set()
        Debug.log(f"Starting plugin loading ({len(plugin_dirs)} found)", "Plugins")

        for plugin_dir in sorted_dirs:
            meta = meta_cache.get(plugin_dir)
            if not meta:
                name = plugin_dir.name
                Debug.log_warning(f"Skipping '{name}': metadata read failed", "Plugins")
                failed_names.add(name)
                continue

            name = meta.name
            deps = list(meta.dependency_specs.keys())
            missing_deps = [d for d in deps if d not in loaded_names]

            if missing_deps:
                Debug.log_warning(f"Skipping '{name}': missing dependencies {missing_deps}", "Plugins")
                failed_names.add(name)
                continue

            try:
                self.load_plugin(plugin_dir)
                loaded_names.add(name)
                if deps:
                    dep_list = ", ".join(deps)
                    Debug.log_success(f"Loaded '{name}' (depends on: {dep_list})", "Plugins")
                else:
                    Debug.log_success(f"Loaded '{name}'", "Plugins")
            except Exception as e:
                Debug.log_error(f"Failed to load '{name}': {e}", "Plugins")
                failed_names.add(name)

        Debug.log_info(f"Plugin loading complete: {len(loaded_names)}/{len(plugin_dirs)} loaded", "Plugins")
    def _log_plugin_structure(self, plugin_dirs: List[Path], meta_cache: dict):
        packs = {}
        for d in plugin_dirs:
            rel_path = d.relative_to(self.plugin_dir)
            if len(rel_path.parts) == 1:
                pack_name = "<root>"
                plugin_name = rel_path.parts[0]
            else:
                pack_name = rel_path.parts[0]
                plugin_name = "/".join(rel_path.parts[1:])
            if pack_name not in packs:
                packs[pack_name] = []
            meta = meta_cache.get(d)
            version = meta.version if meta else "?.?.?"
            packs[pack_name].append((plugin_name, version, d))

        Debug.log_info("=== Plugin Structure ===", "Plugins")
        for pack, items in sorted(packs.items()):
            if pack == "<root>":
                Debug.log_info("📁 (root)", "Plugins")
            else:
                Debug.log_info(f"📁 {pack}", "Plugins")
            for plugin_name, version, path in sorted(items):
                meta = meta_cache.get(path)
                if meta and meta.dependency_specs:
                    deps = ", ".join(meta.dependency_specs.keys())
                    Debug.log_info(f"  └── {plugin_name} v{version} → [{deps}]", "Plugins")
                else:
                    Debug.log_info(f"  └── {plugin_name} v{version}", "Plugins")
    def _read_plugin_metadata(self, plugin_dir: Path) -> Optional[Plugin]:
        name = plugin_dir.name
        init_path = plugin_dir / "__init__.py"
        try:
            spec = importlib.util.spec_from_file_location(f"_meta_{name}", init_path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            module.Plugin = Plugin
            spec.loader.exec_module(module)
            plugin_obj = getattr(module, "PLUGIN", None)
            if isinstance(plugin_obj, Plugin):
                return plugin_obj
        except Exception as e:
            print(f"Metadata load error in {init_path}: {e}")
        finally:
            sys.modules.pop(f"_meta_{name}", None)
        return None
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
                console_handler.register_plugin_command(cmd_name, bound_func, plugin.command_help.get(cmd_name, ""))