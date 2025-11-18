import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIHorizontalSlider, UILabel


class AirFrictionWindow:
    def __init__(self, ui_manager, physics_manager, initial_values=None):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.window = UIWindow(
            rect=pygame.Rect(100, 100, 400, 350),
            manager=self.ui_manager,
            window_display_title="Air Friction Settings",
            object_id="#air_friction_window"
        )

        if initial_values is None:
            initial_values = {"linear_term": 0.0100, "quadratic_term": 0.00100, "multiplier": 1.0}

        self.linear_label = UILabel(
            relative_rect=pygame.Rect(20, 30, 200, 30),
            text=f"Linear Term: {initial_values['linear_term']:.3f}",
            manager=self.ui_manager,
            container=self.window
        )

        self.linear_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(20, 60, 350, 20),
            start_value=initial_values["linear_term"],
            value_range=(0.0, 1.0),
            manager=self.ui_manager,
            container=self.window
        )

        self.quadratic_label = UILabel(
            relative_rect=pygame.Rect(20, 100, 200, 30),
            text=f"Quadratic Term: {initial_values['quadratic_term']:.3f}",
            manager=self.ui_manager,
            container=self.window
        )

        self.quadratic_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(20, 130, 350, 20),
            start_value=initial_values["quadratic_term"],
            value_range=(0.0, 0.1),
            manager=self.ui_manager,
            container=self.window
        )

        self.multiplier_label = UILabel(
            relative_rect=pygame.Rect(20, 170, 200, 30),
            text=f"Multiplier: {initial_values['multiplier']:.3f}",
            manager=self.ui_manager,
            container=self.window
        )

        self.multiplier_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(20, 200, 350, 20),
            start_value=initial_values["multiplier"],
            value_range=(0.0, 5.0),
            manager=self.ui_manager,
            container=self.window
        )

        self.formula_label = UILabel(
            relative_rect=pygame.Rect(20, 240, 360, 60),
            text="F = -D * multiplier * (LinearTerm * V + QuadraticTerm * V²)",
            manager=self.ui_manager,
            container=self.window
        )

        self.preview_label = UILabel(
            relative_rect=pygame.Rect(20, 300, 360, 30),
            text="Preview: F = -D * 1.0 * (0.1 * V + 0.01 * V²)",
            manager=self.ui_manager,
            container=self.window
        )

        self._update_preview()

    def process_event(self, event):
        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.linear_slider:
                self.linear_label.set_text(f"Linear Term: {event.value:.3f}")
            elif event.ui_element == self.quadratic_slider:
                self.quadratic_label.set_text(f"Quadratic Term: {event.value:.3f}")
            elif event.ui_element == self.multiplier_slider:
                self.multiplier_label.set_text(f"Multiplier: {event.value:.3f}")
            self._update_preview()
            self._apply_settings()
        return False

    def _update_preview(self):
        linear = self.linear_slider.get_current_value()
        quadratic = self.quadratic_slider.get_current_value()
        multiplier = self.multiplier_slider.get_current_value()
        self.preview_label.set_text(f"Preview: F = -D * {multiplier:.2f} * ({linear:.2f} * V + {quadratic:.2f} * V²)")

    def _apply_settings(self):
        linear = self.linear_slider.get_current_value()
        quadratic = self.quadratic_slider.get_current_value()
        multiplier = self.multiplier_slider.get_current_value()
        self.physics_manager.set_air_friction_params(linear, quadratic, multiplier)

    def close(self):
        self.window.kill()

    def is_alive(self):
        return self.window.alive()