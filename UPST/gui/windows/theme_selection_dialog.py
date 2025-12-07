import random
import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIPanel, UIImage, UILabel
from UPST.config import config

class ThemeSelectionDialog(UIWindow):
    def __init__(self, rect, manager, top_left_bar):
        super().__init__(rect, manager, window_display_title="New Scene")
        self.top_left_bar = top_left_bar
        self.themes = list(config.world.themes.keys())
        self.cell_size = 120
        self.grid_cols = 5
        self.container = UIPanel(
            relative_rect=pygame.Rect(10, 30, rect.width - 20, rect.height - 60),
            manager=manager,
            container=self
        )
        self.theme_panels = []
        self._create_theme_grid()

    def _create_theme_grid(self):
        for i, theme_name in enumerate(self.themes):
            row, col = divmod(i, self.grid_cols)
            x = col * self.cell_size
            y = row * self.cell_size
            panel = UIPanel(
                relative_rect=pygame.Rect(x, y, self.cell_size - 15, self.cell_size - 15),
                manager=self.ui_manager,
                container=self.container,
                anchors={'left': 'left', 'top': 'top'}
            )
            img = self._generate_thumbnail(theme_name)
            UIImage(
                relative_rect=pygame.Rect(0, 0, 100, 100),
                image_surface=img,
                manager=self.ui_manager,
                container=panel
            )
            UILabel(
                relative_rect=pygame.Rect(0, 0, 100, 20),
                text=theme_name,
                manager=self.ui_manager,
                container=panel
            )
            panel.theme_name = theme_name
            self.theme_panels.append(panel)

    def process_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for panel in self.theme_panels:
                if panel.get_abs_rect().collidepoint(mouse_pos):
                    if self.get_abs_rect().collidepoint(mouse_pos):
                        self.theme_panels = []
                        self._on_theme_selected(panel.theme_name)
                        self.kill()
        super().process_event(event)

    def _generate_thumbnail(self, theme_name):
        theme = config.world.themes[theme_name]
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        bg = theme.background_color
        if len(bg) == 3:
            bg = (*bg, 255)
        surf.fill(bg)
        for i in range(4):
            for j in range(4):
                r = random.randint(*theme.shape_color_range[0])
                g = random.randint(*theme.shape_color_range[1])
                b = random.randint(*theme.shape_color_range[2])
                pygame.draw.rect(surf, (r, g, b), (i * 25, j * 25, 25, 25))
        return surf

    def _on_theme_selected(self, theme_name):
        config.world.current_theme = theme_name
        self.top_left_bar.physics_manager.reset_with_theme()
        self.kill()