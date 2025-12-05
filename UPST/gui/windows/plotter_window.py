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
        self._plot_surface = pygame.Surface((size[0], size[1] - 60)).convert()
        self._create_window()
        try:
            if hasattr(self._wrapper, "register_script_window") and callable(self._wrapper.register_script_window):
                self._wrapper.register_script_window(self)
        except Exception:
            Debug.log_exception("Failed to register PlotterWindow with UI wrapper.", "GUI")
        self._create_buttons()

    def _create_window(self):
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(self.position, self.size),
            manager=self.manager,
            window_display_title=self.window_title
        )
        self.plot_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(0, 60, self.size[0], self.size[1] - 70),
            image_surface=self._plot_surface,
            manager=self.manager,
            container=self.window
        )
        self.plotter = Plotter((self.size[0], self.size[1] - 60), max_samples=120)

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

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED and self.is_open():
            for key, btn in self.buttons.items():
                if event.ui_element == btn:
                    if key == "toggle_mode":
                        self.plotter.set_overlay_mode(not self.plotter.overlay_mode)
                    elif key == "clear_data":
                        self.plotter.clear_data()
                    elif key == "show_all":
                        for g in self.plotter.get_available_groups():
                            self.plotter.set_group_visibility(g, True)

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
