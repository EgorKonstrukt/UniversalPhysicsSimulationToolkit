import ctypes
import pygame
import math
import pymunk

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
from UPST.tools.tool_manager import ToolManager
from UPST.modules.snapshot_manager import SnapshotManager
from UPST.modules.undo_redo_manager import UndoRedoManager
from UPST.sound.sound_manager import SoundManager
from UPST.network.network_manager import NetworkManager
from UI_manager import UIManager
from UPST.demos.demo_all_gizmos import demo_all_gizmos
# from UPST.script_system.script_system_main import integrate_script_system
from UPST.modules.renderer import Renderer


class Application:
    def __init__(self):
        pygame.init()
        config.load_from_file()
        self.screen = self.setup_screen()
        self.font = pygame.font.SysFont("Consolas", 16)
        pygame.display.set_caption(f"{config.app.version}")
        pygame.display.set_icon(pygame.image.load("logo.ico"))
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("UPSTAppID")
        self.clock = pygame.time.Clock()
        self.running = True
        self.world_theme = config.world.current_theme
        Debug.log("World Theme initialized successfully", "Init")
        self.sound_manager = SoundManager()
        Debug.log("SoundManager initialized successfully", "Init")
        self.physics_manager = PhysicsManager(self, undo_redo_manager=None)
        Debug.log("PhysicsManager initialized successfully", "Init")
        self.camera = Camera(self, config.app.screen_width, config.app.screen_height, self.screen)
        Debug.log("Camera initialized successfully", "Init")
        self.force_field_manager = ForceFieldManager(self.physics_manager, self.camera)
        Debug.log("ForceFieldManager initialized successfully", "Init")
        self.grid_manager = GridManager(self.camera, force_field_manager=self.force_field_manager)
        Debug.log("GridManager initialized successfully", "Init")
        self.grid_manager.set_theme_colors(self.world_theme)
        self.gizmos_manager = GizmosManager(self.camera, self.screen)
        self.debug_manager = DebugManager()
        self.snapshot_manager = SnapshotManager(physics_manager=self.physics_manager, camera=self.camera)
        Debug.log("SnapshotManager initialized successfully", "Init")
        self.undo_redo_manager = UndoRedoManager(snapshot_manager=self.snapshot_manager)
        Debug.log("UndoRedoManager initialized successfully", "Init")
        self.physics_manager.undo_redo_manager = self.undo_redo_manager
        self.ui_manager = UIManager(config.app.screen_width, config.app.screen_height,
                                    self.physics_manager, self.camera, None, self.screen, self.font,
                                    network_manager=None)
        self.input_handler = InputHandler(self, gizmos_manager=self.gizmos_manager,
                                          debug_manager=self.debug_manager,
                                          undo_redo_manager=self.undo_redo_manager,
                                          ui_manager=self.ui_manager)
        self.ui_manager.input_handler = self.input_handler
        Debug.log("InputHandler initialized successfully", "Init")
        self.plotter = Plotter(surface_size=(580, 300))
        Debug.log("UIManager initialized successfully", "Init")
        self.ui_manager.set_plotter(self.plotter)
        self.spawner = ObjectSpawner(physics_manager=self.physics_manager,
                                     ui_manager=self.ui_manager,
                                     sound_manager=self.sound_manager)
        Debug.log("ObjectSpawner initialized successfully", "Init")
        self.tool_manager = ToolManager(physics_manager=self.physics_manager,
                                        ui_manager=self.ui_manager,
                                        input_handler=self.input_handler,
                                        sound_manager=self.sound_manager,
                                        spawner=self.spawner)
        Debug.log("ToolManager initialized successfully", "Init")
        self.tool_manager.create_tool_buttons()
        self.save_load_manager = SaveLoadManager(self.physics_manager, self.camera,
                                                 self.ui_manager, self.sound_manager)
        Debug.log("SaveLoadManager initialized successfully", "Init")
        self.console_handler = ConsoleHandler(self.ui_manager, self.physics_manager)
        Debug.log("ConsoleHandler initialized successfully", "Init")
        self.network_manager = NetworkManager(physics_manager=self.physics_manager,
                                              ui_manager=self.ui_manager,
                                              spawner=self.spawner,
                                              gizmos=self.gizmos_manager,
                                              console=self.console_handler)
        self.ui_manager.network_manager = self.network_manager
        self.ui_manager.init_network_menu()
        synthesizer.set_volume(0.5)
        self.physics_debug_manager = PhysicsDebugManager(self.physics_manager, self.camera, self.plotter)
        Debug.log("PhysicsDebugManager initialized successfully", "Init")
        self.ui_manager.set_physics_debug_manager(self.physics_debug_manager)
        self.gizmos_demo = GizmosDemo(self.camera)
        set_debug(self.debug_manager)
        set_gizmos(self.gizmos_manager)
        self.profiler = Profiler(self.ui_manager.manager)
        Debug.log("Profiler initialized successfully", "Init")
        self.profiler.toggle()
        self.undo_redo_manager.take_snapshot()
        Debug.log_info(str(pygame.display.Info()), "Init")
        Debug.log_info(str(pygame.display.get_wm_info()), "Init")
        Debug.log_info(str(pygame.display.get_surface()), "Init")
        Debug.log_info("Refresh rate: "+str(pygame.display.get_current_refresh_rate()), "Init")
        Debug.log_info("Displays: "+str(pygame.display.get_num_displays()), "Init")
        # try:
        #     self.script_system = integrate_script_system(self)
        #     Debug.log("Python Scripting System initialized successfully", "ScriptSystem")
        #     self.ui_manager.console_window.add_output_line_to_log("=== Python Scripting System Loaded ===")
        #     self.ui_manager.console_window.add_output_line_to_log("Press F5 to run all auto-run scripts")
        #     self.ui_manager.console_window.add_output_line_to_log("Press F6 to launch IDLE IDE")
        #     self.ui_manager.console_window.add_output_line_to_log("Press F7 to open Script Editor")
        #     self.ui_manager.console_window.add_output_line_to_log("Right-click script objects to interact")
        #     self.ui_manager.console_window.add_output_line_to_log("=====================================")
        # except Exception as e:
        #     Debug.log_error(f"Failed to initialize Python Scripting System: {e}", "ScriptSystem")
        #     self.script_system = None
        Debug.log("Application initialized successfully", "Application")
        self.renderer = Renderer(app=self, screen=self.screen, camera=self.camera,
                                 physics_manager=self.physics_manager, gizmos_manager=self.gizmos_manager,
                                 grid_manager=self.grid_manager, input_handler=self.input_handler,
                                 ui_manager=self.ui_manager, script_system=None)

    def setup_screen(self):
        flags = pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE
        if config.app.fullscreen: flags |= pygame.FULLSCREEN
        if not config.app.use_system_dpi:
            try: ctypes.windll.user32.SetProcessDPIAware()
            except AttributeError: pass
        return pygame.display.set_mode((config.app.screen_width, config.app.screen_height), flags)

    def run(self):
        synthesizer.play_note("A3", duration=0.1, waveform="sine", adsr=(0.01, 0.1, 0.7, 0.1), volume=0.5, pan=0.0)
        while self.running:
            time_delta = self.clock.tick(config.app.clock_tickrate) / 1000.0
            self.debug_manager.update(time_delta)
            self.gizmos_manager.update(time_delta)
            self.profiler.start("physics debug", "physics")
            self.physics_debug_manager.update(time_delta)
            self.physics_debug_manager.draw_physics_info_panel()
            self.profiler.stop("physics debug")
            events = pygame.event.get()
            # for event in events:
            #     if self.script_system: self.script_system.handle_event(event)
            self.input_handler.process_events(profiler=self.profiler, events=events)
            self.gizmos_demo.draw(time_delta)
            self.update(time_delta)
            self.draw()
        # if self.script_system: self.script_system.shutdown()
        pygame.quit()

    @profile("MAIN_LOOP")
    def update(self, time_delta):
        # demo_all_gizmos()
        Debug.set_performance_counter("Update Time", time_delta * 1000)
        self.profiler.start("camera", "app")
        self.camera.update(pygame.key.get_pressed())
        self.profiler.stop("camera")
        self.profiler.start("physics solver", "physics")
        self.physics_manager.update(self.camera.rotation)
        self.profiler.stop("physics solver")
        world_mouse_pos = self.camera.screen_to_world(pygame.mouse.get_pos())
        self.profiler.start("force_field", "physics")
        self.force_field_manager.update(world_mouse_pos, self.screen)
        self.profiler.stop("force_field")
        self.profiler.start("gui", "gui")
        self.ui_manager.update(time_delta, self.clock)
        self.profiler.stop("gui")
        # if self.script_system:
        #     self.profiler.start("script_system", "scripting")
        #     self.script_system.update(time_delta)
        #     self.profiler.stop("script_system")
        self.undo_redo_manager.update()

    def draw(self):
        self.renderer.draw()

    def toggle_grid(self):
        self.grid_manager.toggle_grid()
        Debug.log(f"Grid toggled: {config.grid.is_visible}", "Grid")

    def set_world_theme(self, theme_name):
        if theme_name in config.world.themes:
            self.world_theme = theme_name
            self.grid_manager.set_theme_colors(theme_name)
            Debug.log(f"World theme changed to: {theme_name}", "Theme")

    # def create_example_script_world(self):
    #     if not self.script_system: return
    #     self.physics_manager.delete_all()
    #     for i in range(5):
    #         x = (i - 2) * 100
    #         y = -200
    #         self.spawner.spawn_circle((x, y))
    #     for i in range(-5, 6):
    #         x = i * 100
    #         y = 300
    #         self.spawner.spawn_rectangle((x, y), (80, 20))
    #     self.script_system.script_object_manager.execute_all_auto_run()
    #     Debug.log("Example script world created!", "ScriptSystem")


if __name__ == '__main__':
    try:
        game_app = Application()
        # game_app.create_example_script_world()
        game_app.run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()