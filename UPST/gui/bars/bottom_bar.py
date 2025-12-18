import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UIImage

from UPST.gui.windows.simulation_speed_window import SimulationSpeedWindow
from UPST.modules.undo_redo_manager import get_undo_redo
from UPST.gui.windows.air_friction_window import AirFrictionWindow
from UPST.config import config

class BottomBar:
    def __init__(self, screen_width, screen_height, ui_manager, physics_manager, bar_width=400, bar_height=60):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.air_window = None
        self.speed_window = None
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.button_width = 50
        self.button_height = 50
        self.padding = 3
        self.separator_width = 2

        self.undo_redo = get_undo_redo()

        panel_x = (screen_width - self.bar_width) // 2
        self.panel = UIPanel(
            relative_rect=pygame.Rect(panel_x, screen_height - self.bar_height, self.bar_width, self.bar_height),
            manager=self.ui_manager
        )

        try:
            self.icon_surfaces = {
                'pause': pygame.image.load("sprites/gui/pause.png").convert_alpha(),
                'play': pygame.image.load("sprites/gui/play.png").convert_alpha(),
                'grid_on': pygame.image.load("sprites/gui/grid.png").convert_alpha(),
                'grid_off': pygame.image.load("sprites/gui/grid.png").convert_alpha(),
                'air_on': pygame.image.load("sprites/gui/air.png").convert_alpha(),
                'air_off': pygame.image.load("sprites/gui/air.png").convert_alpha(),
                'gravity_on': pygame.image.load("sprites/gui/gravity.png").convert_alpha(),
                'gravity_off': pygame.image.load("sprites/gui/gravity.png").convert_alpha(),
                'undo': pygame.image.load("sprites/gui/undo.png").convert_alpha(),
                'redo': pygame.image.load("sprites/gui/redo.png").convert_alpha()
            }
        except pygame.error as e:
            print(f"Error loading icons: {e}")
            placeholder = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.rect(placeholder, (255, 0, 0), placeholder.get_rect(), 2)
            self.icon_surfaces = {name: placeholder.copy() for name in [
                'pause', 'play', 'grid_on', 'grid_off',
                'air_on', 'air_off', 'gravity_on', 'gravity_off',
                'undo', 'redo'
            ]}

        self.buttons = {}
        self.icons = {}
        self.states = {
            'paused': physics_manager.running_physics,
            'grid': False,
            'air': physics_manager.air_friction,
            'gravity': True
        }

        total_buttons_width = 6 * self.button_width + 5 * self.separator_width + 5 * self.padding
        start_x = (self.bar_width - total_buttons_width) // 2
        x_pos = start_x

        x_pos += self.separator_width + self.padding
        self._create_icon_button('undo', x_pos, "Undo Last Action")
        x_pos += self.button_width + self.padding

        x_pos += self.separator_width + self.padding
        self._create_icon_button('pause', x_pos, "Pause/Resume Simulation")
        x_pos += self.button_width + self.padding

        x_pos += self.separator_width + self.padding
        self._create_icon_button('redo', x_pos, "Redo Last Action")
        x_pos += self.button_width + self.padding
        self._create_separator(x_pos)
        x_pos += self.separator_width + self.padding
        self._create_icon_button('grid', x_pos, "Toggle Grid")
        x_pos += self.button_width + self.padding

        x_pos += self.separator_width + self.padding
        self._create_icon_button('air', x_pos, "Toggle Air Friction")
        x_pos += self.button_width + self.padding

        x_pos += self.separator_width + self.padding
        self._create_icon_button('gravity', x_pos, "Toggle Gravity")

        self._update_button_states()

    def _create_icon_button(self, name, x, tooltip):
        btn = UIButton(
            relative_rect=pygame.Rect(x, (self.bar_height - self.button_height - 5) // 2, self.button_width,
                                      self.button_height),
            text="",
            manager=self.ui_manager,
            container=self.panel,
            tool_tip_text=tooltip
        )

        icon_name = name
        if name in ['grid', 'air', 'gravity']:
            state_suffix = '_on' if self.states[name] else '_off'
            icon_name = name + state_suffix
        elif name == 'pause':
            icon_name = 'play' if self.states['paused'] else 'pause'

        icon = UIImage(
            relative_rect=pygame.Rect(x + (self.button_width - 38) // 2,
                                      (self.bar_height - 42) // 2, 38, 36),
            image_surface=self.icon_surfaces[icon_name],
            container=self.panel,
            manager=self.ui_manager
        )

        self.buttons[name] = btn
        self.icons[name] = icon

    def _create_separator(self, x):
        separator = pygame.Surface((self.separator_width, self.button_height - 10))
        separator.fill((100, 100, 100))
        UIImage(
            relative_rect=pygame.Rect(x, (self.bar_height - self.button_height - 5) // 2 + 5, self.separator_width,
                                      self.button_height - 10),
            image_surface=separator,
            container=self.panel,
            manager=self.ui_manager
        )

    def _update_button_states(self):
        pause_icon = 'play' if self.states['paused'] else 'pause'
        grid_icon = 'grid_on' if self.states['grid'] else 'grid_off'
        air_icon = 'air_on' if self.states['air'] else 'air_off'
        gravity_icon = 'gravity_on' if self.states['gravity'] else 'gravity_off'

        self.icons['pause'].set_image(self.icon_surfaces[pause_icon])
        self.icons['grid'].set_image(self.icon_surfaces[grid_icon])
        self.icons['air'].set_image(self.icon_surfaces[air_icon])
        self.icons['gravity'].set_image(self.icon_surfaces[gravity_icon])

    def process_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.physics_manager.toggle_pause()
            self.states['paused'] = not self.physics_manager.running_physics
            self._update_button_states()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons['pause']:
                self.physics_manager.toggle_pause()
                self.states['paused'] = not self.physics_manager.running_physics
            elif event.ui_element == self.buttons['grid']:
                self.states['grid'] = not self.states['grid']
                self._on_grid_toggled()
            elif event.ui_element == self.buttons['air']:
                self.states['air'] = not self.states['air']
                self._on_air_friction_toggled()
            elif event.ui_element == self.buttons['gravity']:
                self.states['gravity'] = not self.states['gravity']
                self._on_gravity_toggled()
            elif event.ui_element == self.buttons['undo']:
                self._on_undo_pressed()
            elif event.ui_element == self.buttons['redo']:
                self._on_redo_pressed()
            self._update_button_states()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            mouse_pos = pygame.mouse.get_pos()
            if self.buttons['pause'].get_abs_rect().collidepoint(mouse_pos):
                self._open_simulation_speed_window()
            elif self.buttons['air'].get_abs_rect().collidepoint(mouse_pos):
                self._open_air_friction_window()

        if self.air_window:
            if self.air_window.process_event(event):
                return
        if self.speed_window:
            if self.speed_window.process_event(event):
                return

    def _open_air_friction_window(self):
        if not self.air_window or not self.air_window.is_alive():
            self.air_window = AirFrictionWindow(
                ui_manager=self.ui_manager,
                physics_manager=self.physics_manager,
                initial_values={
                    "linear_term": self.physics_manager.air_friction_linear,
                    "quadratic_term": self.physics_manager.air_friction_quadratic,
                    "multiplier": self.physics_manager.air_friction_multiplier
                }
            )

    def _open_simulation_speed_window(self):
        if not self.speed_window or not self.speed_window.is_alive():
            current_freq = self.physics_manager.simulation_frequency
            current_multiplier = getattr(self.physics_manager, 'simulation_speed_multiplier', 1.0)
            self.speed_window = SimulationSpeedWindow(
                ui_manager=self.ui_manager,
                physics_manager=self.physics_manager,
                initial_speed=current_freq,
                initial_multiplier=current_multiplier,
                initial_iterations=self.physics_manager.space.iterations
            )

    def _on_grid_toggled(self):
        config.grid.is_visible = not self.states['grid']

    def _on_air_friction_toggled(self):

        self.physics_manager.air_friction_multiplier = 0.0
        self.undo_redo.take_snapshot()
        pass

    def _on_gravity_toggled(self):

        g = (0, 981) if self.states['gravity'] else (0, 0)
        self.physics_manager.set_gravity_mode(g=g)
        self.undo_redo.take_snapshot()

    def _on_undo_pressed(self):
        self.undo_redo.undo()

    def _on_redo_pressed(self):
        self.undo_redo.redo()

    def update_from_physics(self):
        self.states['paused'] = not self.physics_manager.running_physics
        self._update_button_states()

    def set_grid_state(self, enabled):
        self.states['grid'] = enabled
        self._update_button_states()

    def set_air_state(self, enabled):
        self.states['air'] = enabled
        self._update_button_states()

    def set_gravity_state(self, enabled):
        self.states['gravity'] = enabled
        self.undo_redo.take_snapshot()
        self._update_button_states()

    def resize(self, screen_width, screen_height):
        panel_x = (screen_width - self.bar_width) // 2
        self.panel.set_position((panel_x, screen_height - self.bar_height))
        self.panel.set_dimensions((self.bar_width, self.bar_height))

    def _reposition_button(self, name, x):
        btn = self.buttons[name]
        icon = self.icons[name]
        y = (self.bar_height - self.button_height - 5) // 2
        btn.set_position((x, y))
        icon.set_position((x + (self.button_width - 38) // 2, (self.bar_height - 42) // 2))