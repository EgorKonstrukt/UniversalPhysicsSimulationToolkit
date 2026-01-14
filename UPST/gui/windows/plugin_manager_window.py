import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIPanel, UIButton, UILabel, UIScrollingContainer

class PluginManagerWindow(UIWindow):
    def __init__(self, rect: pygame.Rect, manager: pygame_gui.UIManager, app: "App"):
        super().__init__(rect, manager, window_display_title="Plugin Manager", object_id="#plugin_manager_window")
        self.app = app
        self.plugin_manager = app.plugin_manager
        self.buttons = {}
        self.panels = []
        self.container = UIPanel(
            relative_rect=pygame.Rect(10, 30, rect.width - 20, rect.height - 80),
            manager=manager,
            container=self
        )
        self.scrolling_container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, self.container.rect.width, self.container.rect.height),
            manager=manager,
            container=self.container
        )
        self._create_plugin_grid()
        self._create_control_buttons(rect)

    def _create_plugin_grid(self):
        plugin_names = list(self.plugin_manager.plugins.keys())
        if not plugin_names:
            UILabel(
                relative_rect=pygame.Rect(10, 10, 200, 30),
                text="No plugins found",
                manager=self.ui_manager,
                container=self.scrolling_container
            )
            self.scrolling_container.set_scrollable_area_dimensions((self.scrolling_container.rect.width, 50))
            return

        y_offset = 0
        for name in plugin_names:
            panel = UIPanel(
                relative_rect=pygame.Rect(10, y_offset, self.scrolling_container.rect.width - 20, 50),
                manager=self.ui_manager,
                container=self.scrolling_container
            )
            UILabel(
                relative_rect=pygame.Rect(10, 10, 150, 30),
                text=name,
                manager=self.ui_manager,
                container=panel
            )
            reload_btn = UIButton(
                relative_rect=pygame.Rect(170, 10, 80, 30),
                text="Reload",
                manager=self.ui_manager,
                container=panel
            )
            disable_btn = UIButton(
                relative_rect=pygame.Rect(260, 10, 80, 30),
                text="Disable",
                manager=self.ui_manager,
                container=panel
            )
            self.buttons[f"{name}_reload"] = reload_btn
            self.buttons[f"{name}_disable"] = disable_btn
            panel.plugin_name = name
            self.panels.append(panel)
            y_offset += 60

        self.scrolling_container.set_scrollable_area_dimensions((self.scrolling_container.rect.width, y_offset))

    def _create_control_buttons(self, rect: pygame.Rect):
        btn_width = 120
        gap = 10
        total_width = 3 * btn_width + 2 * gap
        start_x = (rect.width - total_width) // 2

        self.reload_all_btn = UIButton(
            relative_rect=pygame.Rect(start_x, rect.height - 60, btn_width, 30),
            text="Reload All",
            manager=self.ui_manager,
            container=self
        )
        self.disable_all_btn = UIButton(
            relative_rect=pygame.Rect(start_x + btn_width + gap, rect.height - 60, btn_width, 30),
            text="Disable All",
            manager=self.ui_manager,
            container=self
        )
        self.close_btn = UIButton(
            relative_rect=pygame.Rect(start_x + 2 * (btn_width + gap), rect.height - 60, btn_width, 30),
            text="Close",
            manager=self.ui_manager,
            container=self
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_btn:
                self.kill()
            elif event.ui_element == self.reload_all_btn:
                for name in list(self.plugin_manager.plugins.keys()):
                    try:
                        self.plugin_manager.reload_plugin(name)
                    except Exception as e:
                        print(f"Failed to reload plugin {name}: {e}")
                self._rebuild_ui()
            elif event.ui_element == self.disable_all_btn:
                for name in list(self.plugin_manager.plugins.keys()):
                    self.plugin_manager.unload_plugin(name)
                self._rebuild_ui()
            else:
                for name in list(self.plugin_manager.plugins.keys()):
                    if event.ui_element == self.buttons.get(f"{name}_reload"):
                        try:
                            self.plugin_manager.reload_plugin(name)
                            self._rebuild_ui()
                        except Exception as e:
                            print(f"Failed to reload plugin {name}: {e}")
                    elif event.ui_element == self.buttons.get(f"{name}_disable"):
                        self.plugin_manager.unload_plugin(name)
                        self._rebuild_ui()
        super().process_event(event)

    def _rebuild_ui(self):
        for panel in self.panels:
            panel.kill()
        self.panels.clear()
        self.buttons.clear()
        self._create_plugin_grid()