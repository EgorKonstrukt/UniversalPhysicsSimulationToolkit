import pygame
import pygame_gui
from typing import Optional
from UPST.gui.plotter import Plotter
from UPST.debug.debug_manager import Debug

class PlotterWindow:
    def __init__(self, manager: Optional[object], position=(10,10), size=(600,400), window_title="Data Plotter"):
        orig_mgr = manager
        ui_mgr = manager
        if manager is None:
            Debug.log_warning("PlotterWindow initialized with manager=None", "GUI")
        else:
            if hasattr(manager, "manager") and isinstance(manager.manager, pygame_gui.UIManager):
                ui_mgr = manager.manager
            elif hasattr(manager, "ui_manager") and isinstance(manager.ui_manager, pygame_gui.UIManager):
                ui_mgr = manager.ui_manager
        if not isinstance(ui_mgr, pygame_gui.UIManager):
            raise RuntimeError("PlotterWindow requires pygame_gui.UIManager")
        self._wrapper = orig_mgr
        self.manager = ui_mgr
        self.position = position
        self.size = size
        self.window_title = window_title
        self.window = None
        self.plot_image = None
        self.plotter = None
        self.buttons = {}
        self._create_window()
        try:
            if hasattr(self._wrapper, "register_script_window") and callable(self._wrapper.register_script_window):
                self._wrapper.register_script_window(self)
        except Exception:
            Debug.log_exception("Failed to register PlotterWindow with UI wrapper.", "GUI")
        self._create_buttons()
        self._create_sample_controls()

    def _create_window(self):
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(self.position, self.size),
            manager=self.manager,
            window_display_title=self.window_title,
            resizable=True
        )
        plot_height = self.size[1] - 70
        self.plot_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(0, 60, self.size[0], plot_height),
            image_surface=pygame.Surface((self.size[0], plot_height)).convert(),
            manager=self.manager,
            container=self.window
        )
        self.plotter = Plotter((self.size[0], plot_height), max_samples=120)

    def _create_buttons(self):
        btn_defs = {
            "toggle_mode": ("Toggle Mode", (10, 10, 100, 30)),
            "clear_data": ("Clear Data", (120, 10, 100, 30)),
            "show_all": ("Show All", (230, 10, 100, 30)),
        }
        for key, (txt, rect) in btn_defs.items():
            self.buttons[key] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(rect),
                text=txt,
                manager=self.manager,
                container=self.window
            )

    def _create_sample_controls(self):
        self.sample_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(340, 10, 60, 30),
            manager=self.manager,
            container=self.window
        )
        self.sample_input.set_text(str(self.plotter.max_samples))
        self.sample_inc = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(405, 10, 30, 30),
            text="+",
            manager=self.manager,
            container=self.window
        )
        self.sample_dec = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(440, 10, 30, 30),
            text="-",
            manager=self.manager,
            container=self.window
        )

    def _resize_plot_area(self):
        new_w, new_h = self.window.rect.size
        if new_w <= 0 or new_h <= 70: return
        plot_height = new_h - 70
        self.plotter.surface_size = (new_w, plot_height)
        self.plotter.surface = pygame.Surface((new_w, plot_height), pygame.SRCALPHA)
        self.plot_image.set_dimensions((new_w, plot_height))
        self.plot_image.set_image(self.plotter.get_surface())

    def handle_event(self, event: pygame.event.Event):
        if not self.is_open(): return
        if event.type == pygame_gui.UI_WINDOW_RESIZED and event.ui_element == self.window:
            self._resize_plot_area()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons["toggle_mode"]:
                self.plotter.set_overlay_mode(not self.plotter.overlay_mode)
            elif event.ui_element == self.buttons["clear_data"]:
                self.plotter.clear_data()
            elif event.ui_element == self.buttons["show_all"]:
                for g in self.plotter.get_available_groups():
                    self.plotter.set_group_visibility(g, True)
            elif event.ui_element == self.sample_inc:
                val = int(self.sample_input.get_text()) + 1
                self.plotter.max_samples = val
                self.sample_input.set_text(str(val))
            elif event.ui_element == self.sample_dec:
                val = max(1, int(self.sample_input.get_text()) - 1)
                self.plotter.max_samples = val
                self.sample_input.set_text(str(val))
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.sample_input:
            try:
                val = max(1, int(self.sample_input.get_text()))
                self.plotter.max_samples = val
                self.plotter.clear_data()
            except ValueError:
                self.sample_input.set_text(str(self.plotter.max_samples))

    def is_open(self): return self.window and self.window.alive()
    def show(self): self.window.show()
    def hide(self): self.window.hide()
    def close(self):
        try:
            if self._wrapper and hasattr(self._wrapper, "unregister_script_window"):
                self._wrapper.unregister_script_window(self)
        except Exception:
            Debug.log_exception("Failed to unregister PlotterWindow from UI wrapper.", "GUI")
        if self.window:
            self.window.kill()
    def add_data(self, key, value, group="General"): self.plotter.add_data(key, value, group)
    def clear_data(self): self.plotter.clear_data()
    def update(self, dt: float):
        if not self.is_open(): return
        self.plot_image.set_image(self.plotter.get_surface())