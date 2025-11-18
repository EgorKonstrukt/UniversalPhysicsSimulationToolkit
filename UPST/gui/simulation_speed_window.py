import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UIImage, UIWindow, UIHorizontalSlider, UILabel
from UPST.modules.undo_redo_manager import get_undo_redo
from UPST.gui.air_friction_window import AirFrictionWindow
from UPST.config import config


class SimulationSpeedWindow:
    def __init__(self, ui_manager, physics_manager, initial_speed=60, initial_multiplier=1.0, initial_iterations=10):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.window = UIWindow(
            rect=pygame.Rect(0, 0, 350, 340),
            manager=ui_manager,
            window_display_title="Simulation Settings",
            object_id="#simulation_settings_window"
        )

        self.frequency_label = UILabel(
            relative_rect=pygame.Rect(10, 30, 330, 30),
            text=f"Frequency: {initial_speed} Hz",
            manager=ui_manager,
            container=self.window,
            object_id="#freq_label"
        )

        self.frequency_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(10, 70, 310, 20),
            start_value=initial_speed,
            value_range=(1, 240),
            manager=ui_manager,
            container=self.window,
            object_id="#freq_slider"
        )

        self.speed_label = UILabel(
            relative_rect=pygame.Rect(10, 110, 330, 30),
            text=f"Speed Multiplier: {initial_multiplier:.2f}x",
            manager=ui_manager,
            container=self.window,
            object_id="#speed_label"
        )

        self.speed_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(10, 150, 310, 20),
            start_value=initial_multiplier,
            value_range=(0.1, 10.0),
            manager=ui_manager,
            container=self.window,
            object_id="#speed_slider"
        )

        self.iterations_label = UILabel(
            relative_rect=pygame.Rect(10, 190, 330, 30),
            text=f"Iterations: {initial_iterations}",
            manager=ui_manager,
            container=self.window,
            object_id="#iterations_label"
        )

        self.iterations_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(10, 230, 310, 20),
            start_value=initial_iterations,
            value_range=(1, 50),
            manager=ui_manager,
            container=self.window,
            object_id="#iterations_slider"
        )

        self.reset_button = UIButton(
            relative_rect=pygame.Rect(10, 270, 310, 30),
            text="Reset to Defaults",
            manager=ui_manager,
            container=self.window,
            object_id="#reset_button"
        )

        self.current_frequency = initial_speed
        self.current_multiplier = initial_multiplier
        self.current_iterations = initial_iterations
        self.default_frequency = 100
        self.default_multiplier = 1.0
        self.default_iterations = 256
        self._center_window()

    def _center_window(self):
        screen_w, screen_h = pygame.display.get_surface().get_size()
        win_w, win_h = self.window.get_abs_rect().width, self.window.get_abs_rect().height
        center_x = (screen_w - win_w) // 2
        center_y = (screen_h - win_h) // 2
        self.window.set_position((center_x, center_y))

    def process_event(self, event):
        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.frequency_slider:
                self.current_frequency = int(event.value)
                self.frequency_label.set_text(f"Frequency: {self.current_frequency} Hz")
                self.physics_manager.set_simulation_frequency(self.current_frequency)
                return True
            elif event.ui_element == self.speed_slider:
                self.current_multiplier = round(event.value, 2)
                self.speed_label.set_text(f"Speed Multiplier: {self.current_multiplier}x")
                self.physics_manager.set_simulation_speed_multiplier(self.current_multiplier)
                return True
            elif event.ui_element == self.iterations_slider:
                self.current_iterations = int(event.value)
                self.iterations_label.set_text(f"Iterations: {self.current_iterations}")
                self.physics_manager.set_iterations(self.current_iterations)
                return True
        elif event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.reset_button:
            self._reset_to_defaults()
            return True
        return False

    def _reset_to_defaults(self):
        self.frequency_slider.set_current_value(self.default_frequency)
        self.speed_slider.set_current_value(self.default_multiplier)
        self.iterations_slider.set_current_value(self.default_iterations)

        self.current_frequency = self.default_frequency
        self.current_multiplier = self.default_multiplier
        self.current_iterations = self.default_iterations

        self.frequency_label.set_text(f"Frequency: {self.default_frequency} Hz")
        self.speed_label.set_text(f"Speed Multiplier: {self.default_multiplier}x")
        self.iterations_label.set_text(f"Iterations: {self.default_iterations}")

        self.physics_manager.set_simulation_frequency(self.default_frequency)
        self.physics_manager.set_simulation_speed_multiplier(self.default_multiplier)
        self.physics_manager.set_iterations(self.default_iterations)

    def is_alive(self):
        return self.window.alive()