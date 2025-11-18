import pygame
import pygame_gui
from typing import Optional
from UPST.gui.plotter import Plotter

class PlotterWindow:
    def __init__(self, manager: pygame_gui.UIManager, position: tuple = (10, 10), size: tuple = (600, 400), window_title: str = "PID Plotter"):
        self.manager = manager
        self.position = position
        self.size = size
        self.window_title = window_title
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.plot_image: Optional[pygame_gui.elements.UIImage] = None
        self.plotter: Optional[Plotter] = None
        self._plot_surface = pygame.Surface((size[0], size[1] - 35), pygame.SRCALPHA)
        self._create_window()

    def _create_window(self):
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(self.position, self.size),
            manager=self.manager,
            window_display_title=self.window_title,
            object_id="#plotter_window"
        )
        self.plot_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(0, 35, self.size[0], self.size[1] - 35),
            image_surface=self._plot_surface,
            manager=self.manager,
            container=self.window,
            object_id="#plot_image"
        )
        self.plotter = Plotter((self.size[0], self.size[1] - 35), max_samples=120)

    def show(self): self.window.show()
    def hide(self): self.window.hide()
    def is_open(self) -> bool: return self.window is not None and self.window.alive()

    def add_data(self, key: str, value: float, group: str = "PID"): self.plotter.add_data(key, value, group)
    def clear_data(self): self.plotter.clear_data()

    def update(self, dt: float):
        if not self.is_open(): return
        plot_surf = self.plotter.get_surface()
        if plot_surf.get_size() != self._plot_surface.get_size():
            self._plot_surface = pygame.Surface(plot_surf.get_size(), pygame.SRCALPHA)
            self.plot_image.set_image(self._plot_surface)
        self._plot_surface.blit(plot_surf, (0, 0))
        self.plot_image.set_image(self._plot_surface)