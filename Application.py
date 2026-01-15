import ctypes
import pygame
import math
import pymunk
import time

from UPST.scripting.script_manager import ScriptManager
from UPST.splash_screen import SplashScreen, FreezeWatcher
from UPST.config import config
from UPST.modules.camera import Camera
from UPST.modules.console_handler import ConsoleHandler
from UPST.debug.debug_manager import DebugManager, Debug, set_debug
from UPST.physics.force_field_manager import ForceFieldManager
from UPST.demos.gizmos_demo import GizmosDemo
from UPST.gizmos.gizmos_manager import GizmosManager, set_gizmos
from UPST.modules.grid_manager import GridManager
from UPST.modules.input_handler import InputHandler
from UPST.modules.object_spawner import ObjectSpawner
from UPST.physics.physics_debug_manager import PhysicsDebugManager
from UPST.physics.physics_manager import PhysicsManager
from UPST.gui.plotter import Plotter
from UPST.modules.profiler import Profiler, profile
from UPST.modules.save_load_manager import SaveLoadManager
from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools import tool_manager
from UPST.modules.snapshot_manager import SnapshotManager
from UPST.modules.undo_redo_manager import UndoRedoManager
from UPST.sound.sound_manager import SoundManager
from UPST.network.network_manager import NetworkManager
from UI_manager import UIManager
from UPST.modules.renderer import Renderer
from UPST.modules.statistics import stats

from UPST.tools.tool_manager import ToolSystem

from UPST.network.repository_manager import RepositoryManager

from UPST.modules.plugin_manager import PluginManager

import sys

# sys.set_int_max_str_digits(0)

class WorldWrapper:
    def __init__(self, physics_manager):
        self._physics = physics_manager

    @property
    def objects(self):
        return [b for b in self._physics.space.bodies if b.body_type == pymunk.Body.DYNAMIC]


class Application:
    def __init__(self):
        pygame.init()
        self.freeze_watcher = None
        self.stats = stats
        config.load_from_file()
        self.config = config
        self.debug = Debug
        self.screen = self.setup_screen()
        self.font = pygame.font.SysFont("Consolas", 16)
        pygame.display.set_caption(f"{config.app.version}")
        pygame.display.set_icon(pygame.image.load("logo.ico"))
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("UPSTAppID")
        self.clock = pygame.time.Clock()
        self.running = True

        self.world_theme = config.world.current_theme
        self.script_manager = ScriptManager(self)
        Debug.log("World Theme initialized successfully", "Init")
        self.sound_manager = SoundManager()
        Debug.log("SoundManager initialized successfully", "Init")

        self.physics_manager = PhysicsManager(self, undo_redo_manager=None, script_manager=self.script_manager)
        self.world = WorldWrapper(self.physics_manager)
        Debug.log("PhysicsManager initialized successfully", "Init")

        self.camera = Camera(self, config.app.screen_width, config.app.screen_height, self.screen)
        Debug.log("Camera initialized successfully", "Init")
        self.force_field_manager = ForceFieldManager(self.physics_manager, self.camera)
        Debug.log("ForceFieldManager initialized successfully", "Init")
        self.grid_manager = GridManager(self.camera, force_field_manager=self.force_field_manager)
        Debug.log("GridManager initialized successfully", "Init")
        self.grid_manager.set_theme_colors(self.world_theme)
        self.gizmos = GizmosManager(self.camera, self.screen)
        self.debug_manager = DebugManager()

        self.snapshot_manager = SnapshotManager(physics_manager=self.physics_manager, camera=self.camera,
                                                script_manager=self.script_manager)
        Debug.log("SnapshotManager initialized successfully", "Init")
        self.undo_redo_manager = UndoRedoManager(snapshot_manager=self.snapshot_manager)
        Debug.log("UndoRedoManager initialized successfully", "Init")

        self.physics_manager.undo_redo_manager = self.undo_redo_manager


        self.tool_manager = ToolSystem(physics_manager=self.physics_manager,
                                       sound_manager=self.sound_manager)
        self.plugin_manager = PluginManager(self)

        self.ui_manager = UIManager(config.app.screen_width, config.app.screen_height,
                                    self.physics_manager, self.camera, None, self.screen, self.font,
                                    network_manager=None, app=self,
                                    tool_system=self.tool_manager)

        self.input_handler = InputHandler(self, gizmos_manager=self.gizmos,
                                          debug_manager=self.debug_manager,
                                          undo_redo_manager=self.undo_redo_manager,
                                          ui_manager=self.ui_manager,
                                          tool_system=self.tool_manager)

        self.tool_manager.set_ui_manager(self.ui_manager)
        self.tool_manager.set_input_handler(self.input_handler)
        self.ui_manager.input_handler = self.input_handler
        Debug.log("InputHandler initialized successfully", "Init")

        self.plotter = Plotter(surface_size=(580, 300))
        Debug.log("UIManager initialized successfully", "Init")
        self.spawner = ObjectSpawner(physics_manager=self.physics_manager,
                                     ui_manager=self.ui_manager,
                                     sound_manager=self.sound_manager)
        Debug.log("ObjectSpawner initialized successfully", "Init")
        # self.tool_manager = ToolManager(physics_manager=self.physics_manager,
        #                                 ui_manager=self.ui_manager,
        #                                 input_handler=self.input_handler,
        #                                 sound_manager=self.sound_manager,
        #                                 spawner=self.spawner)
        Debug.log("ToolManager initialized successfully", "Init")
        self.tool_manager.create_tool_buttons()
        self.save_load_manager = SaveLoadManager(self.physics_manager, self.camera,
                                                 self.ui_manager, self.sound_manager, app=self)
        Debug.log("SaveLoadManager initialized successfully", "Init")
        self.console_handler = ConsoleHandler(self.ui_manager, self.physics_manager)
        Debug.log("ConsoleHandler initialized successfully", "Init")
        self.network_manager = NetworkManager(physics_manager=self.physics_manager,
                                              ui_manager=self.ui_manager,
                                              spawner=self.spawner,
                                              gizmos=self.gizmos,
                                              console=self.console_handler)
        self.ui_manager.network_manager = self.network_manager
        # self.ui_manager.init_network_menu()
        synthesizer.set_volume(0.5)
        self.physics_debug_manager = PhysicsDebugManager(self.physics_manager, self.camera, self.plotter)
        Debug.log("PhysicsDebugManager initialized successfully", "Init")
        self.ui_manager.set_physics_debug_manager(self.physics_debug_manager)
        set_debug(self.debug_manager)
        set_gizmos(self.gizmos)
        self.profiler = Profiler(self.ui_manager.manager)
        Debug.log("Profiler initialized successfully", "Init")
        self.undo_redo_manager.take_snapshot()
        Debug.log_info(str(pygame.display.Info()), "Init")
        Debug.log_info(str(pygame.display.get_wm_info()), "Init")
        Debug.log_info(str(pygame.display.get_surface()), "Init")
        Debug.log_info("Refresh rate: " + str(pygame.display.get_current_refresh_rate()), "Init")
        Debug.log_info("Displays: " + str(pygame.display.get_num_displays()), "Init")
        Debug.log("Application initialized successfully", "Application")
        self.renderer = Renderer(app=self, screen=self.screen, camera=self.camera,
                                 physics_manager=self.physics_manager, gizmos_manager=self.gizmos,
                                 grid_manager=self.grid_manager, input_handler=self.input_handler,
                                 ui_manager=self.ui_manager, script_system=None, tool_manager=self.tool_manager)
        self.repository_manager = RepositoryManager()

        self.plugin_manager.load_all_plugins()
        self.plugin_manager.register_console_commands(self.console_handler)

    def setup_screen(self):
        flags = pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.SWSURFACE | pygame.SRCALPHA
        if config.app.fullscreen: flags |= pygame.FULLSCREEN
        if not config.app.use_system_dpi:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except AttributeError:
                pass
        return pygame.display.set_mode((config.app.screen_width, config.app.screen_height), flags)


    def run(self):
        # synthesizer.play_note("A3", duration=0.1, waveform="sine", adsr=(0.01, 0.1, 0.7, 0.1), volume=0.5, pan=0.0)
        self.freeze_watcher = FreezeWatcher(threshold_sec=0.1)
        self.freeze_watcher.start()
        stats.accumulate_session_time()
        stats.session_start = time.time()
        while self.running:
            self.freeze_watcher.ping()
            time_delta = self.clock.tick(config.app.clock_tickrate) / 1000.0
            self.debug_manager.update(time_delta)
            self.gizmos.update(time_delta)
            self.physics_debug_manager.update(time_delta)
            events = pygame.event.get()
            self.input_handler.process_events(profiler=self.profiler, events=events)
            self.update(time_delta)

            self.renderer.draw()
        stats.accumulate_session_time()
        stats.save()
        self.save_load_manager.create_snapshot()
        pygame.quit()

    @profile("MAIN")
    def update(self, time_delta):
        Debug.set_performance_counter("Update Time", time_delta * 1000)
        self.camera.update(pygame.key.get_pressed())
        self.physics_manager.update(self.camera.rotation)
        world_mouse_pos = self.camera.screen_to_world(pygame.mouse.get_pos())
        # self.force_field_manager.update(world_mouse_pos, self.screen)
        self.ui_manager.update(time_delta, self.clock)
        self.plugin_manager.update(time_delta)
        self.undo_redo_manager.update()
        self.physics_manager.update_scripts(time_delta)

    def toggle_grid(self):
        self.grid_manager.toggle_grid()
        Debug.log(f"Grid toggled: {config.grid.is_visible}", "Grid")

    def set_world_theme(self, theme_name):
        if theme_name in config.world.themes:
            self.world_theme = theme_name
            self.grid_manager.set_theme_colors(theme_name)
            Debug.log(f"World theme changed to: {theme_name}", "Theme")


if __name__ == '__main__':
    try:
        splash = SplashScreen()
        try:
            game_app = Application()
            splash.destroy()
            game_app.run()
        except Exception as inner_e:
            splash.destroy()
            raise inner_e
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()

print(1)