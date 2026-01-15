import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIPanel, UIButton, UILabel, UIScrollingContainer, UIImage, UITooltip

class PluginManagerWindow(UIWindow):
    def __init__(self, rect: pygame.Rect, manager: pygame_gui.UIManager, app: "App"):
        super().__init__(rect, manager, window_display_title="Plugin Manager",
                         object_id="#plugin_manager_window",resizable=True)
        self.app = app
        self.plugin_manager = app.plugin_manager
        self.buttons = {}
        self.panels = []
        self.container = UIPanel(
            relative_rect=pygame.Rect(10, 30, rect.width - 20, rect.height - 80),
            manager=manager,
            container=self,
            anchors={'left': 'left', 'right': 'right', 'top': 'top', 'bottom': 'bottom'}
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
            UILabel(relative_rect=pygame.Rect(10, 10, 200, 30), text="No plugins found", manager=self.ui_manager, container=self.scrolling_container)
            self.scrolling_container.set_scrollable_area_dimensions((self.scrolling_container.rect.width, 50))
            return

        y_offset = 0
        for name in plugin_names:
            plugin = self.plugin_manager.plugins[name]
            panel_h = 80
            panel = UIPanel(relative_rect=pygame.Rect(10, y_offset, self.scrolling_container.rect.width - 20, panel_h), manager=self.ui_manager, container=self.scrolling_container)
            panel.plugin_name = name

            x = 10
            icon_w = 55
            if plugin.icon_path:
                icon_full_path = self.plugin_manager.plugin_dir / name / plugin.icon_path
                if icon_full_path.exists():
                    try:
                        icon_surf = pygame.image.load(icon_full_path).convert_alpha()
                        icon_surf = pygame.transform.scale(icon_surf, (icon_w, icon_w))
                        img = UIImage(relative_rect=pygame.Rect(x, 10, icon_w, icon_w), image_surface=icon_surf, manager=self.ui_manager, container=panel)
                        x += icon_w + 10
                    except Exception:
                        x += icon_w + 10
                else:
                    x += icon_w + 10
            else:
                x += icon_w + 10

            name_max_w = 400
            author_max_w = 400
            desc_max_w = 400
            btn_w = 70
            gap = 5

            name_text = f"{name} v{plugin.version}"
            author_text = f"by {plugin.author}" if plugin.author else ""
            desc_text = plugin.description if plugin.description else ""

            name_label = UILabel(relative_rect=pygame.Rect(x, 5, name_max_w, 20), text=name_text, manager=self.ui_manager, container=panel, object_id="#plugin_name_label")
            author_label = UILabel(relative_rect=pygame.Rect(x, 25, author_max_w, 20), text=author_text, manager=self.ui_manager, container=panel, object_id="#author_label")
            desc_label = UILabel(relative_rect=pygame.Rect(x, 45, desc_max_w, 20), text=desc_text, manager=self.ui_manager, container=panel, object_id="#description_label")

            reload_btn = UIButton(relative_rect=pygame.Rect(self.scrolling_container.rect.width - btn_w * 2 - gap-40, 25, btn_w, 30), text="Reload", manager=self.ui_manager, container=panel)
            disable_btn = UIButton(relative_rect=pygame.Rect(self.scrolling_container.rect.width - btn_w-40, 25, btn_w, 30), text="Disable", manager=self.ui_manager, container=panel)

            self.buttons[f"{name}_reload"] = reload_btn
            self.buttons[f"{name}_disable"] = disable_btn

            deps_str = ", ".join([f"{d} {v}" for d, v in plugin.dependency_specs.items()]) if plugin.dependency_specs else "None"
            tooltip_text = f"Dependencies:\n{deps_str}" if plugin.dependency_specs else "No dependencies"
            name_label.tool_tip = UITooltip(tooltip_text, self.ui_manager, parent_element=name_label)

            self.panels.append(panel)
            y_offset += panel_h + 5

        total_h = max(y_offset, 50)
        self.scrolling_container.set_scrollable_area_dimensions((self.scrolling_container.rect.width, total_h))

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

    def update(self, time_delta: float):
        super().update(time_delta)
        for panel in self.panels:
            if hasattr(panel, 'plugin_name'):
                plugin = self.plugin_manager.plugins.get(panel.plugin_name)
                if plugin and not plugin.on_draw:
                    for btn in [self.buttons.get(f"{panel.plugin_name}_reload"), self.buttons.get(f"{panel.plugin_name}_disable")]:
                        if btn:
                            btn.disable()