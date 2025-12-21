import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UIImage

from UPST.config import config
from UPST.gui.windows.about_window import AboutWindow
from UPST.sound.sound_synthesizer import synthesizer
from UPST.modules.profiler import get_profiler
from UPST.gui.windows.theme_selection_dialog import ThemeSelectionDialog
from UPST.gui.windows.theme_editor_window import ThemeEditorWindow
from UPST.utils import get_resource_path

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

        self.theme_dialog = None
        self.about_window = None
        self.repo_window = None

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
            elif event.ui_element == self.buttons['repository']:
                self._on_repository_pressed()
            elif event.ui_element == self.buttons['profiler']:
                self._on_profiler_pressed()
            elif event.ui_element == self.buttons['console']:
                self._on_console_pressed()
            elif event.ui_element == self.buttons['settings']:
                self.open_theme_editor()
            elif event.ui_element == self.buttons['about']:
                self._on_about_pressed()
        if self.theme_dialog:
            self.theme_dialog.process_event(event)

    def _on_new_scene_pressed(self):
        if not self.theme_dialog or not self.theme_dialog.alive():
            self.theme_dialog = ThemeSelectionDialog(
                pygame.Rect(100, 100, 620, 480),
                self.ui_manager,
                self
            )

    def _on_repository_pressed(self):
        if self.repo_window is None or not self.repo_window.alive():
            from UPST.gui.windows.repository_window import RepositoryWindow
            self.repo_window = RepositoryWindow(
                pygame.Rect(150, 80, 1000, 600),
                self.ui_manager,
                self.app
            )

    def open_theme_editor(self):
        if hasattr(self, '_theme_editor') and self._theme_editor.alive():
            self._theme_editor.kill()
        self._theme_editor = ThemeEditorWindow(
            rect=pygame.Rect(100, 50, 800, 600),
            manager=self.ui_manager,
            theme_path=get_resource_path('theme.json'),
            ui_manager_ref=self
        )

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
        if not self.about_window or not self.about_window.alive():
            self.about_window = AboutWindow(pygame.Rect(config.app.screen_width/2-210,
                                                        config.app.screen_height/2-315,
                                                        420,
                                                        630), self.ui_manager, self.app)