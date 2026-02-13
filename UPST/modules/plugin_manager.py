import json
import os
import sys
import importlib
import importlib.util
from functools import partial
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Set
from collections import defaultdict, deque

import pygame

from dataclasses import dataclass, asdict, field

from packaging.version import Version, InvalidVersion

from UPST.debug.debug_manager import Debug
from UPST.config import config, Config
from UPST.gui.windows.context_menu.config_option import ConfigOption


@dataclass
class Plugin:
    name: str
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    icon_path: Optional[str] = None
    dependency_specs: Dict[str, str] = field(default_factory=dict)
    config_class: Optional[type] = None
    on_load: Optional[Callable[["PluginManager", Any], None]] = None
    on_unload: Optional[Callable[["PluginManager", Any], None]] = None
    on_update: Optional[Callable[["PluginManager", float, Any], None]] = None
    on_draw: Optional[Callable[["PluginManager", Any], None]] = None
    on_event: Optional[Callable[["PluginManager", Any, Any], bool]] = None
    console_commands: Dict[str, Callable] = field(default_factory=dict)
    command_help: Dict[str, str] = field(default_factory=dict)
    context_menu_items: Optional[Callable[["PluginManager", Any, Any], List[Any]]] = None
    scripting_symbols: Dict[str, Any] = field(default_factory=dict)
    scripting_hooks: Optional[Callable[["PluginManager", Dict[str, Any]], None]] = None

    def __post_init__(self):
        if self.console_commands is None:
            self.console_commands = {}
        if self.command_help is None:
            self.command_help = {}
        if self.scripting_symbols is None:
            self.scripting_symbols = {}

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_instances: Dict[str, Any] = {}
        self.plugin_modules = {}
        self.plugin_paths: Dict[str, Path] = {}
        self.plugin_dir = Path("plugins").resolve()
        self.plugin_dir.mkdir(exist_ok=True)
        self.context_menu_contributors: List[tuple[str, Callable]] = []
    def register_context_menu_contributor(self, plugin_name: str, contributor: Callable):
        self.context_menu_contributors.append((plugin_name, contributor))

    def unregister_context_menu_contributor(self, plugin_name: str):
        self.context_menu_contributors = [(n, c) for n, c in self.context_menu_contributors if n != plugin_name]

    def get_context_menu_items(self, clicked_object) -> List[ConfigOption]:
        items = []
        for _, contributor in self.context_menu_contributors:
            try:
                contributed = contributor(self, clicked_object)
                if contributed:
                    items.extend(contributed)
            except Exception as e:
                Debug.log_error(f"Plugin context menu contributor failed: {e}", "Plugins")
        return items
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
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise RuntimeError(f"Failed to execute plugin module '{module_name}'") from e

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

        plugin_config_path = plugin_dir / "config.json"
        config_instance = None
        if plugin_def.config_class:
            Config.register_plugin_config(name, plugin_def.config_class)
            if plugin_config_path.exists():
                try:
                    with open(plugin_config_path, "r", encoding="utf-8") as f:
                        cfg_data = json.load(f)
                    if hasattr(plugin_def.config_class, '_from_dict_custom'):
                        config_instance = plugin_def.config_class._from_dict_custom(cfg_data)
                    else:
                        config_instance = plugin_def.config_class(**cfg_data)
                except (json.JSONDecodeError, OSError, TypeError) as e:
                    Debug.log_warning(f"Failed to load config for plugin '{name}' ({e}). Using defaults.", "Plugins")
                    config_instance = plugin_def.config_class()
            else:
                config_instance = plugin_def.config_class()
            cfg_dict = asdict(config_instance)
            if hasattr(config_instance, '_to_dict_custom'):
                cfg_dict = config_instance._to_dict_custom(cfg_dict)
            plugin_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(plugin_config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=4, ensure_ascii=False)
            setattr(self.app.config, name, config_instance)

        plugin_instance = None
        if hasattr(module, "PluginImpl"):
            try:
                plugin_instance = module.PluginImpl(self.app)
            except Exception as e:
                raise RuntimeError(f"Failed to instantiate PluginImpl for '{name}'") from e
        else:
            plugin_instance = object()  # заглушка

        self.plugins[name] = plugin_def
        self.plugin_instances[name] = plugin_instance
        self.plugin_modules[name] = module
        self.plugin_paths[name] = plugin_dir

        if plugin_def.on_load:
            try:
                plugin_def.on_load(self, plugin_instance)
            except Exception as e:
                Debug.log_exception(f"Plugin '{name}' on_load handler failed", "Plugins")
                raise

        if plugin_def.context_menu_items:
            self.register_context_menu_contributor(name, lambda pm, obj, pd=plugin_def,
                                                                pi=plugin_instance: pd.context_menu_items(pm, pi, obj))

        if hasattr(plugin_instance, 'get_tools') and callable(getattr(plugin_instance, 'get_tools')):
            try:
                tools = plugin_instance.get_tools(self.app)
                for i, tool in enumerate(tools):
                    if not hasattr(tool, '__class__'):
                        Debug.log_error(f"Plugin '{name}': tool[{i}] is not a valid object", "Plugins")
                        continue
                    # Validate BaseTool contract
                    base_init = getattr(tool.__class__.__bases__[0], '__init__',
                                        None) if tool.__class__.__bases__ else None
                    if base_init and hasattr(base_init, '__code__'):
                        argcount = base_init.__code__.co_argcount
                        if argcount != 2:  # self + app
                            Debug.log_error(f"Plugin '{name}': BaseTool.__init__ expects 2 args, got {argcount}",
                                            "Plugins")
                    self.app.tool_manager.register_tool(tool)
            except Exception as e:
                import traceback
                tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
                Debug.log_error(f"Failed to register tools from plugin '{name}': {e}\n{''.join(tb_lines)}", "Plugins")
                raise
        return plugin_instance

    def unload_plugin(self, name: str):
        if name not in self.plugins:
            return
        plugin_def = self.plugins[name]
        plugin_instance = self.plugin_instances[name]
        if hasattr(self.app, 'console_handler'):
            for cmd in list(plugin_def.console_commands.keys()):
                try:
                    self.app.console_handler.unregister_plugin_command(cmd)
                except Exception as e:
                    Debug.log_warning(f"Failed to unregister command '{cmd}' for plugin '{name}': {e}", "Plugins")
        if plugin_def.on_unload:
            try:
                plugin_def.on_unload(self, plugin_instance)
            except Exception as e:
                Debug.log_exception(f"Plugin '{name}' on_unload handler failed", "Plugins")
        mod_name = self.plugin_modules[name].__name__
        self._unload_submodules(mod_name)
        sys.modules.pop(mod_name, None)
        del self.plugins[name]
        del self.plugin_instances[name]
        del self.plugin_modules[name]
        del self.plugin_paths[name]
        self.unregister_context_menu_contributor(name)

    def reload_plugin(self, name: str):
        if name not in self.plugin_paths:
            raise FileNotFoundError(f"Plugin {name} was not loaded from a known path")
        plugin_dir = self.plugin_paths[name]
        if not plugin_dir.exists():
            raise FileNotFoundError(f"Plugin {name} directory not found at {plugin_dir}")
        old_def = self.plugins.get(name)
        old_inst = self.plugin_instances.get(name)
        old_mod = self.plugin_modules.get(name)
        try:
            if hasattr(self.app, 'console_handler'):
                for cmd in list(old_def.console_commands.keys() if old_def else []):
                    try:
                        self.app.console_handler.unregister_plugin_command(cmd)
                    except Exception:
                        pass
            self.unload_plugin(name)
            importlib.invalidate_caches()
            new_instance = self.load_plugin(plugin_dir)
            if hasattr(self.app, 'console_handler'):
                self.register_console_commands(self.app.console_handler)

            Debug.log_success(f"Plugin '{name}' reloaded successfully", "Plugins")

        except Exception as e:
            Debug.log_error(f"Failed to reload plugin '{name}', restoring previous state: {e}", "Plugins")
            if old_def is not None:
                self.plugins[name] = old_def
            if old_inst is not None:
                self.plugin_instances[name] = old_inst
            if old_mod is not None:
                self.plugin_modules[name] = old_mod
                sys.modules[old_mod.__name__] = old_mod
            raise

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
            Debug.log_info("No plugins found.", "Plugins")
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
        Debug.log_info(f"Loading {len(plugin_dirs)} plugin(s)...", "Plugins")

        for plugin_dir in sorted_dirs:
            meta = meta_cache.get(plugin_dir)
            if not meta:
                name = plugin_dir.name
                Debug.log_warning(f"Skipped '{name}': metadata unavailable", "Plugins")
                failed_names.add(name)
                continue

            name = meta.name
            deps = list(meta.dependency_specs.keys())
            missing_deps = [d for d in deps if d not in loaded_names]

            if missing_deps:
                Debug.log_warning(f"Skipped '{name}': missing dependencies {missing_deps}", "Plugins")
                failed_names.add(name)
                continue

            try:
                self.load_plugin(plugin_dir)
                loaded_names.add(name)
                status = f"Loaded '{name}'" + (f" (deps: {', '.join(deps)})" if deps else "")
                Debug.log_success(status, "Plugins")
            except Exception as e:
                Debug.log_error(f"Failed to load '{name}': {e}", "Plugins")
                failed_names.add(name)

        total = len(plugin_dirs)
        success = len(loaded_names)
        Debug.log_info(f"Plugin loading complete: {success}/{total} succeeded.", "Plugins")
        if failed_names:
            Debug.log_warning(f"Failed plugins: {', '.join(sorted(failed_names))}", "Plugins")
        if loaded_names:
            self.app.config.save()

    def _log_plugin_structure(self, plugin_dirs: List[Path], meta_cache: dict):
        packs = defaultdict(list)
        for d in plugin_dirs:
            rel_path = d.relative_to(self.plugin_dir)
            pack_name = rel_path.parts[0] if len(rel_path.parts) > 1 else "<root>"
            plugin_name = "/".join(rel_path.parts[1:]) if len(rel_path.parts) > 1 else rel_path.parts[0]
            meta = meta_cache.get(d)
            version = meta.version if meta else "?.?.?"
            packs[pack_name].append((plugin_name, version, d))

        Debug.log_colored("┌──────────────────────┐", (100, 200, 255), "Plugins")
        Debug.log_colored("│   Plugin Structure   │", (100, 200, 255), "Plugins")
        Debug.log_colored("└──────────────────────┘", (100, 200, 255), "Plugins")

        for pack in sorted(packs.keys()):
            if pack == "<root>":
                Debug.log_info("📦 [Root Plugins]", "Plugins")
            else:
                Debug.log_colored(f"📁 Pack: {pack}", (180, 180, 255), "Plugins")
            for plugin_name, version, path in sorted(packs[pack]):
                meta = meta_cache.get(path)
                if not meta:
                    continue
                deps = list(meta.dependency_specs.keys()) if meta.dependency_specs else []
                dep_str = f" → [{', '.join(deps)}]" if deps else ""
                author_str = f" by {meta.author}" if meta.author else ""
                color = (220, 220, 100) if deps else (200, 200, 200)
                Debug.log_colored(f"  └─ {plugin_name} v{version}{author_str}{dep_str}", color, "Plugins")

    def _read_plugin_metadata(self, plugin_dir: Path) -> Optional[Plugin]:
        name = plugin_dir.name
        init_path = plugin_dir / "__init__.py"
        if not init_path.exists():
            Debug.log_error(f"Plugin '{name}' skipped: {init_path} not found", "Plugins")
            return None

        temp_module_name = f"_meta_{name}_{id(plugin_dir)}"
        try:
            spec = importlib.util.spec_from_file_location(temp_module_name, init_path)
            if spec is None or spec.loader is None:
                Debug.log_error(f"Plugin '{name}' skipped: could not create module spec for {init_path}", "Plugins")
                return None

            module = importlib.util.module_from_spec(spec)
            module.Plugin = Plugin
            sys.modules[temp_module_name] = module

            try:
                spec.loader.exec_module(module)
            except Exception as exec_err:
                import traceback
                tb_str = ''.join(traceback.format_exception(type(exec_err), exec_err, exec_err.__traceback__))
                Debug.log_error(f"Plugin '{name}' skipped: exception while executing {init_path}\n{tb_str}", "Plugins")
                return None

            plugin_obj = getattr(module, "PLUGIN", None)
            if plugin_obj is None:
                Debug.log_error(f"Plugin '{name}' skipped: global variable 'PLUGIN' not found in {init_path}",
                                "Plugins")
                return None

            if not isinstance(plugin_obj, Plugin):
                actual_type = type(plugin_obj).__name__
                Debug.log_error(
                    f"Plugin '{name}' skipped: 'PLUGIN' in {init_path} is of type '{actual_type}', expected 'Plugin'",
                    "Plugins")
                return None

            if not hasattr(plugin_obj, 'name') or not isinstance(plugin_obj.name, str) or not plugin_obj.name.strip():
                Debug.log_error(
                    f"Plugin '{name}' skipped: 'PLUGIN.name' is missing, empty, or not a string in {init_path}",
                    "Plugins")
                return None

            return plugin_obj

        except Exception as e:
            Debug.log_exception(f"Unexpected error while reading metadata for plugin '{name}'", "Plugins")
            return None
        finally:
            sys.modules.pop(temp_module_name, None)

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
                inst = self.plugin_instances[name]
                if hasattr(cmd_func, '__code__') and cmd_func.__code__.co_argcount >= 2:
                    bound_func = partial(cmd_func, inst)
                else:
                    bound_func = lambda expr, i=inst, f=cmd_func: f(i, expr)
                console_handler.register_plugin_command(
                    cmd_name, bound_func, plugin.command_help.get(cmd_name, "")
                )



