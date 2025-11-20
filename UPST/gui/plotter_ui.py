import pygame
import pygame_gui

class PlotterUI:
    def __init__(self, manager):
        self.manager = manager
        self.plotter_window = pygame_gui.elements.UIWindow(pygame.Rect(50,50,600,400), manager=self.manager, window_display_title="Physics Plotter")
        self.plotter_window.hide()
        self.plot_surface = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(10,10,580,300), image_surface=pygame.Surface((580,300), pygame.SRCALPHA), container=self.plotter_window, manager=self.manager)
        self.dropdown = pygame_gui.elements.UIDropDownMenu(options_list=['Select Parameter'], starting_option='Select Parameter', relative_rect=pygame.Rect(10,320,150,30), container=self.plotter_window, manager=self.manager)
        self.add_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(170,320,80,30), text='Add Plot', container=self.plotter_window, manager=self.manager)
        self.clear_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(260,320,80,30), text='Clear Plots', container=self.plotter_window, manager=self.manager)
        self.plotter = None

    def set_plotter(self, plotter):
        self.plotter = plotter

    def update_surface(self, surface):
        self.plot_surface.set_image(surface)

    def resize(self):
        pass