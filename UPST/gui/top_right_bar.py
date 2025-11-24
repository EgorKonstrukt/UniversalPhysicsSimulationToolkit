import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UIImage
from UPST.sound.sound_synthesizer import synthesizer

class TopRightBar:
    def __init__(self, screen_width, screen_height, ui_manager, bar_width=45, bar_height=300, app=None, physics_manager=None):
        self.ui_manager = ui_manager
        self.app = app
        self.physics_manager = physics_manager
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.button_width = 40
        self.button_height = 40
        self.padding = 1

        self.panel = UIPanel(
            relative_rect=pygame.Rect(screen_width - self.bar_width, 0, self.bar_width, self.bar_height),
            manager=self.ui_manager
        )

        try:
            self.icon_surfaces = {
                'visualization': pygame.image.load("sprites/gui/visualization.png").convert_alpha(),
                'plot': pygame.image.load("sprites/gui/question_mark.png").convert_alpha(),
            }
        except pygame.error as e:
            print(f"Error loading icons: {e}")
            placeholder = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.rect(placeholder, (255, 0, 0), placeholder.get_rect(), 1)
            self.icon_surfaces = {name: placeholder.copy() for name in [
                'visualization', 'plot'
            ]}

        self.buttons = {}
        self.icons = {}

        y_pos = self.padding
        for name, tooltip in [
            ('visualization', "Visualize all physics properties"),
            ('plot', "Plotter"),
        ]:
            self._create_icon_button(name, y_pos, tooltip)
            y_pos += self.button_height + self.padding

    def _create_icon_button(self, name, y, tooltip):
        btn = UIButton(
            relative_rect=pygame.Rect((self.bar_width - self.button_width) // 2, y, self.button_width, self.button_height),
            text="",
            manager=self.ui_manager,
            container=self.panel,
            tool_tip_text=tooltip
        )

        icon = UIImage(
            relative_rect=pygame.Rect((self.bar_width - 37) // 2, y + (self.button_height - 37) // 2, 37, 37),
            image_surface=self.icon_surfaces[name],
            container=self.panel,
            manager=self.ui_manager
        )

        self.buttons[name] = btn
        self.icons[name] = icon

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons['play']:
                self._on_play_pressed()
            elif event.ui_element == self.buttons['pause']:
                self._on_pause_pressed()
            elif event.ui_element == self.buttons['stop']:
                self._on_stop_pressed()
            elif event.ui_element == self.buttons['step']:
                self._on_step_pressed()
            elif event.ui_element == self.buttons['reset']:
                self._on_reset_pressed()
            elif event.ui_element == self.buttons['record']:
                self._on_record_pressed()
            elif event.ui_element == self.buttons['volume']:
                self._on_volume_pressed()

    def _on_play_pressed(self):
        if self.app and hasattr(self.app, 'simulation_paused'):
            self.app.simulation_paused = False

    def _on_pause_pressed(self):
        if self.app and hasattr(self.app, 'simulation_paused'):
            self.app.simulation_paused = True

    def _on_stop_pressed(self):
        if self.physics_manager:
            self.physics_manager.stop_simulation()

    def _on_step_pressed(self):
        if self.physics_manager:
            self.physics_manager.step_simulation()

    def _on_reset_pressed(self):
        if self.physics_manager:
            self.physics_manager.reset_simulation()

    def _on_record_pressed(self):
        synthesizer.play_frequency(200, duration=0.15, waveform='sine')

    def _on_volume_pressed(self):
        synthesizer.mute = not synthesizer.mute