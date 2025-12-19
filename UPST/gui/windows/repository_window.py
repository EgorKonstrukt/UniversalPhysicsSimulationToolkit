import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIButton, UIPanel, UISelectionList, UILabel

class RepositoryWindow(UIWindow):
    def __init__(self, rect, manager, app):
        super().__init__(rect, manager, window_display_title="Repository")
        self.app = app

        self.panel = UIPanel(
            relative_rect=pygame.Rect(0,0,rect.width,rect.height),
            manager=manager,
            container=self
        )

        self.list = UISelectionList(
            relative_rect=pygame.Rect(10,40,rect.width-20,rect.height-120),
            item_list=[],
            manager=manager,
            container=self.panel
        )

        self.refresh_btn = UIButton(
            relative_rect=pygame.Rect(10,10,90,25),
            text="Refresh",
            manager=manager,
            container=self.panel
        )

        self.open_btn = UIButton(
            relative_rect=pygame.Rect(110,rect.height-70,160,30),
            text="Download & Open",
            manager=manager,
            container=self.panel
        )

        self.publish_btn = UIButton(
            relative_rect=pygame.Rect(rect.width-200,rect.height-70,180,30),
            text="Publish current scene",
            manager=manager,
            container=self.panel
        )

        self.status = UILabel(
            relative_rect=pygame.Rect(10,rect.height-35,rect.width-20,25),
            text="Ready",
            manager=manager,
            container=self.panel
        )

        self._load_list()

    def _load_list(self):
        self.items = self.app.repository_manager.fetch_list()
        self.display_items = [f"{i['title']} | {i['author']}" for i in self.items]
        self.list.set_item_list(self.display_items)
        self.status.set_text(f"Loaded {len(self.items)} items")

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.refresh_btn:
                self._load_list()
            elif event.ui_element == self.open_btn:
                self._download_selected()
            elif event.ui_element == self.publish_btn:
                self._publish_current()

    def _download_selected(self):
        sel = self.list.get_single_selection()
        if not sel: return
        try:
            idx = self.display_items.index(sel)
        except ValueError:
            return
        data = self.app.repository_manager.download(self.items[idx]["id"])
        self.app.save_load_manager._apply_loaded_data(data)
        self.status.set_text("Scene loaded")

    def _publish_current(self):
        data = self.app.save_load_manager.capture_snapshot_data()
        self.app.repository_manager.publish(data)
        self.status.set_text("Published successfully")
