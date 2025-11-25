import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UIImage
from UPST.sound.sound_synthesizer import synthesizer
from UPST.modules.profiler import get_profiler

class TopLeftBar:
    def __init__(self, screen_width, screen_height, ui_manager, bar_width=375, bar_height=45, app=None, physics_manager=None):
        self.ui_manager = ui_manager
        self.app = app
        self.physics_manager = physics_manager
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.button_width = 40
        self.button_height = 40
        self.padding = 1
        self.separator_width = 2

        self.panel = UIPanel(
            relative_rect=pygame.Rect(0, 0, self.bar_width, self.bar_height),
            manager=self.ui_manager
        )

        try:
            self.icon_surfaces = {
                'new': pygame.image.load("sprites/gui/new.png").convert_alpha(),
                'open': pygame.image.load("sprites/gui/open.png").convert_alpha(),
                'save': pygame.image.load("sprites/gui/save.png").convert_alpha(),
                'repository': pygame.image.load("sprites/gui/repository.png").convert_alpha(),
                'profiler': pygame.image.load("sprites/gui/plot.png").convert_alpha(),
                'console': pygame.image.load("sprites/gui/window_visibility.png").convert_alpha(),
                'settings': pygame.image.load("sprites/gui/settings.png").convert_alpha(),
                'about': pygame.image.load("sprites/gui/about.png").convert_alpha()
            }
        except pygame.error as e:
            print(f"Error loading icons: {e}")
            placeholder = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.rect(placeholder, (255, 0, 0), placeholder.get_rect(), 1)
            self.icon_surfaces = {name: placeholder.copy() for name in [
                'new', 'open', 'save', 'repository', 'profiler', 'console', 'settings', 'about'
            ]}

        self.buttons = {}
        self.icons = {}

        total_buttons_width = 7 * self.button_width + 6 * self.separator_width + 6 * self.padding
        x_pos = self.padding

        self._create_icon_button('new', x_pos, "New Scene")
        x_pos += self.button_width + self.padding

        self._create_icon_button('open', x_pos, "Open Scene")
        x_pos += self.button_width + self.padding

        self._create_icon_button('save', x_pos, "Save Scene")
        x_pos += self.button_width + self.padding

        self._create_icon_button('repository', x_pos, "Repository")
        x_pos += self.button_width + self.padding

        x_pos += 15
        self._create_separator(x_pos)
        x_pos += self.separator_width + self.padding
        x_pos += 15
        self._create_icon_button('profiler', x_pos, "Profiler")
        x_pos += self.button_width + self.padding

        self._create_icon_button('console', x_pos, "Console")
        x_pos += self.button_width + self.padding

        self._create_icon_button('settings', x_pos, "Settings")
        x_pos += self.button_width + self.padding

        self._create_icon_button('about', x_pos, "About")

    def _create_icon_button(self, name, x, tooltip):
        btn = UIButton(
            relative_rect=pygame.Rect(x, (self.bar_height - self.button_height-6) // 2, self.button_width,
                                      self.button_height),
            text="",
            manager=self.ui_manager,
            container=self.panel,
            tool_tip_text=tooltip
        )

        icon = UIImage(
            relative_rect=pygame.Rect(x + (self.button_width - 32) // 2,
                                      (self.bar_height - 32-6) // 2, 32, 32),
            image_surface=self.icon_surfaces[name],
            container=self.panel,
            manager=self.ui_manager
        )

        self.buttons[name] = btn
        self.icons[name] = icon

    def _create_separator(self, x):
        separator = pygame.Surface((self.separator_width, self.button_height - 10))
        separator.fill((100, 100, 100))
        UIImage(
            relative_rect=pygame.Rect(x, (self.bar_height - self.button_height) // 2 + 5, self.separator_width,
                                      self.button_height - 10),
            image_surface=separator,
            container=self.panel,
            manager=self.ui_manager
        )


    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons['new']:
                self._on_new_scene_pressed()
            elif event.ui_element == self.buttons['open']:
                self._on_open_scene_pressed()
            elif event.ui_element == self.buttons['save']:
                self._on_save_scene_pressed()
            elif event.ui_element == self.buttons['profiler']:
                self._on_profiler_pressed()
            elif event.ui_element == self.buttons['console']:
                self._on_console_pressed()
            elif event.ui_element == self.buttons['settings']:
                self._on_settings_pressed()
            elif event.ui_element == self.buttons['about']:
                self._on_about_pressed()

    def _on_new_scene_pressed(self):
        self.physics_manager.delete_all()

    def _on_open_scene_pressed(self):
        synthesizer.play_frequency(100, duration=0.2, waveform='sine')
        self.app.save_load_manager.load_world()

    def _on_save_scene_pressed(self):
        synthesizer.play_frequency(100, duration=0.2, waveform='sine')
        self.app.save_load_manager.save_world()
        pass

    def _on_profiler_pressed(self):
        profiler = get_profiler()
        if profiler:
            profiler.toggle_window()

    def _on_console_pressed(self):
        pass

    def _on_settings_pressed(self):
        pass

    def _on_about_pressed(self):
        pass