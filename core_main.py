import ctypes

import pygame

##____________________________________
from UI_manager import UIManager
from UPST.camera import Camera
from UPST.config import Config
from UPST.console_handler import ConsoleHandler
from UPST.debug_manager import DebugManager, Debug, set_debug
from UPST.force_field_manager import ForceFieldManager
from UPST.gizmos_demo import GizmosDemo
from UPST.gizmos_manager import GizmosManager, set_gizmos
from UPST.grid_manager import GridManager
from UPST.input_handler import InputHandler
from UPST.music_composer import InfiniteAmbientComposer
from UPST.object_spawner import ObjectSpawner
from UPST.physics_debug_manager import PhysicsDebugManager
from UPST.physics_manager import PhysicsManager
from UPST.plotter import Plotter
from UPST.profiler import Profiler, profile
from UPST.save_load_manager import SaveLoadManager
from UPST.sound_synthesizer import synthesizer
from UPST.tool_manager import ToolManager
from UPST.snapshot_manager import SnapshotManager
from UPST.undo_redo_manager import UndoRedoManager
from sound_manager import SoundManager


##____________________________________


class Application:
    """
    Main application class that orchestrates everything.
    """

    def __init__(self):
        pygame.init()

        self.screen = self.setup_screen()
        self.font = pygame.font.SysFont("Consolas", 16)

        pygame.display.set_caption(Config.VERSION)
        pygame.display.set_icon(pygame.image.load("laydigital.png"))
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NewgodooAppID")

        self.clock = pygame.time.Clock()
        self.running = True
        self.world_theme = Config.CURRENT_THEME

        self.sound_manager = SoundManager()
        self.physics_manager = PhysicsManager(self, undo_redo_manager=None)
        self.camera = Camera(self, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)

        self.grid_manager = GridManager(self.camera)
        self.grid_manager.set_theme_colors(self.world_theme)
        self.gizmos_manager = GizmosManager(self.camera, self.screen)
        self.debug_manager = DebugManager()
        self.snapshot_manager = SnapshotManager(physics_manager=self.physics_manager,
                                                camera=self.camera)
        self.undo_redo_manager = UndoRedoManager(snapshot_manager=self.snapshot_manager,
                                                 max_snapshots=50)
        self.physics_manager.undo_redo_manager = self.undo_redo_manager
        self.input_handler = InputHandler(self,
                                          gizmos_manager=self.gizmos_manager,
                                          debug_manager=self.debug_manager,
                                          undo_redo_manager=self.undo_redo_manager)

        self.plotter = Plotter(surface_size=(580, 300)) # Instantiate Plotter

        self.ui_manager = UIManager(Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT,
                                    self.physics_manager, self.camera,
                                    self.input_handler, self.screen, self.font)
        self.ui_manager.set_plotter(self.plotter) # Pass plotter to UI_manager

        self.spawner = ObjectSpawner(physics_manager=self.physics_manager,
                                     ui_manager=self.ui_manager,
                                     sound_manager=self.sound_manager)
        self.tool_manager = ToolManager(
            physics_manager=self.physics_manager,
            ui_manager=self.ui_manager,
            input_handler=self.input_handler,
            sound_manager=self.sound_manager,
            spawner=self.spawner
        )
        self.tool_manager.create_tool_buttons()

        self.force_field_manager = ForceFieldManager(self.physics_manager, self.camera)
        self.save_load_manager = SaveLoadManager(self.physics_manager, self.camera,
                                                 self.ui_manager, self.sound_manager)
        self.console_handler = ConsoleHandler(self.ui_manager, self.physics_manager)


        self.physics_debug_manager = PhysicsDebugManager(self.physics_manager, self.camera, self.plotter) # Pass plotter to PhysicsDebugManager
        self.ui_manager.set_physics_debug_manager(self.physics_debug_manager)
        self.gizmos_demo = GizmosDemo()
        set_debug(self.debug_manager)
        set_gizmos(self.gizmos_manager)

        self.profiler = Profiler(self.ui_manager.manager)
        self.profiler.toggle()

        self.undo_redo_manager.take_snapshot()

        Debug.log("Application initialized successfully", "Application")
        synthesizer.set_volume(0.5)

    def setup_screen(self):
        flags = pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE
        if Config.FULLSCREEN:
            flags |= pygame.FULLSCREEN
        if not Config.USE_SYSTEM_DPI:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except AttributeError:
                pass
        return pygame.display.set_mode((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT), flags)


    def run(self):

        synthesizer.play_note("A#4", duration=0.1, waveform="sine",
                              adsr=(0.01, 0.1, 0.7, 0.1), volume=0.5,
                              detune=0.0, apply_effects=True, pan=0.0)

        print("\nDemo complete!")
        while self.running:
            time_delta = self.clock.tick(Config.CLOCK_TICKRATE) / 1000.0

            self.debug_manager.update(time_delta)
            self.gizmos_manager.update(time_delta)


            self.profiler.start("physics debug", "physics")
            self.physics_debug_manager.update(time_delta)
            self.physics_debug_manager.draw_physics_info_panel()
            self.profiler.stop("physics debug")

            self.profiler.update_graph()
            self.input_handler.process_events(profiler=self.profiler)
            self.gizmos_demo.draw(time_delta)



            self.update(time_delta)
            self.draw()



        pygame.quit()

    @profile("MAIN_LOOP")
    def update(self, time_delta):
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

        self.profiler.start("ui", "ui")
        self.ui_manager.update(time_delta, self.clock)
        self.profiler.stop("ui")

        self.undo_redo_manager.update()

        synthesizer.update_visualization()

    def draw(self):
        start_time = pygame.time.get_ticks()

        self.screen.fill(Config.WORLD_THEMES[self.world_theme]["background_color"])

        self.grid_manager.draw(self.screen)
        self.gizmos_manager.draw_debug_gizmos()

        draw_options = self.camera.get_draw_options(self.screen)
        self.physics_manager.space.debug_draw(draw_options)

        if self.input_handler.creating_static_line:
            start_screen = draw_options.transform @ self.input_handler.static_line_start
            pygame.draw.line(self.screen, (255, 255, 255), start_screen, pygame.mouse.get_pos(), 5)

        if self.input_handler.first_joint_body:
            body_screen_pos = self.camera.world_to_screen(
                self.input_handler.first_joint_body.position, draw_options)
            mouse_pos = pygame.mouse.get_pos()
            pygame.draw.line(self.screen, (255, 255, 0, 150), body_screen_pos,
                             mouse_pos, 3)

        self.gizmos_manager.draw()
        self.ui_manager.draw(self.screen)
        self.draw_cursor_icon()

        self.debug_manager.draw_all_debug_info(self.screen, self.physics_manager, self.camera)


        pygame.display.flip()

        draw_time = pygame.time.get_ticks() - start_time
        Debug.set_performance_counter("Draw Time", draw_time)

    def draw_cursor_icon(self):
        is_mouse_on_ui = self.ui_manager.manager.get_focus_set()
        if not is_mouse_on_ui:
            tool = self.input_handler.current_tool
            if tool in self.ui_manager.tool_icons:
                icon = self.ui_manager.tool_icons[tool]

                target_size = (32, 32)
                icon = pygame.transform.smoothscale(icon, target_size)

                mouse_pos = pygame.mouse.get_pos()
                icon_rect = icon.get_rect(center=(mouse_pos[0] + 30, mouse_pos[1] - 20))
                self.screen.blit(icon, icon_rect)

    def toggle_grid(self):
        self.grid_manager.toggle_grid()
        Debug.log(f"Grid toggled: {self.grid_manager.toggle_grid()}", "Grid")

    def set_world_theme(self, theme_name):
        if theme_name in Config.WORLD_THEMES:
            self.world_theme = theme_name
            self.grid_manager.set_theme_colors(theme_name)
            Debug.log(f"World theme changed to: {theme_name}", "Theme")


if __name__ == '__main__':
    game_app = Application()
    game_app.run()

