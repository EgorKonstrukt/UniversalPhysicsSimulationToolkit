import pickle
import threading

import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIButton, UIPanel, UISelectionList, UILabel, UIProgressBar, UITextEntryLine, \
    UITextBox, UITextEntryBox
from UPST.config import config
from UPST.utils import surface_to_bytes
from UPST.debug.debug_manager import Debug


REPO_LIST_LOADED_EVENT = pygame.event.custom_type()

class PublishMetaWindow(UIWindow):
    def __init__(self, manager, on_submit, initial_meta=None):
        super().__init__(pygame.Rect(300, 200, 320, 220), manager, window_display_title="Publish Scene")
        self.on_submit = on_submit
        meta = initial_meta or {}
        self.title = UITextEntryLine(pygame.Rect(10, 40, 300, 25), manager, container=self)
        self.author = UITextEntryLine(pygame.Rect(10, 80, 300, 25), manager, container=self)
        self.desc = UITextEntryBox(pygame.Rect(10, 120, 300, 50), manager=manager, container=self)
        self.ok = UIButton(pygame.Rect(110, 180, 100, 30), "Publish", manager, container=self)
        self.title.set_text(str(meta.get("title", "")))
        self.author.set_text(str(meta.get("author", "")))
        self.desc.set_text(str(meta.get("description", "")))

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.ok:
            meta = {"title": self.title.get_text(), "author": self.author.get_text(), "description": self.desc.get_text()}
            self.on_submit(meta)
            self.kill()

class RepositoryWindow(UIWindow):
    def __init__(self, rect, manager, app):
        super().__init__(rect, manager, window_display_title="Repository")
        self.app = app
        self.panel = UIPanel(
            relative_rect=pygame.Rect(0, 0, rect.width, rect.height),
            manager=manager,
            container=self
        )

        self.progress = UIProgressBar(
            relative_rect=pygame.Rect(10, rect.height - 100, rect.width - 20, 15),
            manager=manager,
            container=self.panel
        )

        self.list = UISelectionList(
            relative_rect=pygame.Rect(10, 40, rect.width - 20, rect.height - 120),
            item_list=[],
            manager=manager,
            container=self.panel
        )

        self.refresh_btn = UIButton(
            relative_rect=pygame.Rect(10, 10, 90, 25),
            text="Refresh",
            manager=manager,
            container=self.panel
        )

        self.open_btn = UIButton(
            relative_rect=pygame.Rect(110, rect.height - 70, 160, 30),
            text="Download & Open",
            manager=manager,
            container=self.panel
        )

        self.publish_btn = UIButton(
            relative_rect=pygame.Rect(rect.width - 200, rect.height - 70, 180, 30),
            text="Publish current scene",
            manager=manager,
            container=self.panel
        )

        self.status = UILabel(
            relative_rect=pygame.Rect(10, rect.height - 35, rect.width - 20, 25),
            text="Ready",
            manager=manager,
            container=self.panel
        )
        self.page = 0
        self.page_label = UILabel(relative_rect=pygame.Rect(10, rect.height - 115, 200, 20),
                                  text="Page 0",
                                  manager=manager,
                                  container=self.panel)
        self.prev_btn = UIButton(relative_rect=pygame.Rect(220, rect.height - 115, 40, 20),
                                 text="<",
                                 manager=manager,
                                 container=self.panel)
        self.next_btn = UIButton(pygame.Rect(270, rect.height - 115, 40, 20),
                                 text=">",
                                 manager=manager,
                                 container=self.panel)

        self.items = []
        self.item_map = {}
        self._load_list()

    def _load_list(self):
        def _bg():
            items = self.app.repository_manager.fetch_list(page=self.page, limit=50)
            event = pygame.event.Event(REPO_LIST_LOADED_EVENT, {"items": items})
            pygame.event.post(event)
        threading.Thread(target=_bg, daemon=True).start()

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.refresh_btn:
                self._load_list()
            elif event.ui_element == self.open_btn:
                self._download_selected()
            elif event.ui_element == self.publish_btn:
                self._publish_current()
            elif event.ui_element == self.prev_btn:
                if self.page > 0:
                    self.page -= 1
                    self._load_list()
            elif event.ui_element == self.next_btn:
                self.page += 1
                self._load_list()
        elif event.type == REPO_LIST_LOADED_EVENT:
            self.items = event.dict["items"]
            display_items = [f"{it['title']} | {it['author']} | {it['id'][:8]}" for it in self.items]
            self.item_map = {label: i for i, label in enumerate(display_items)}
            self.list.set_item_list(display_items)
            self.page_label.set_text(f"Page {self.page}")
            self.status.set_text(f"Page {self.page}, {len(self.items)} items")

    def _update_progress(self, value: float):
        self.progress.set_current_progress(min(max(value, 0.0), 1.0) * 100)

    def _download_selected(self):
        sel = self.list.get_single_selection()
        if not sel or sel not in self.item_map:
            return
        idx = self.item_map[sel]
        item = self.items[idx]
        try:
            self.status.set_text("Downloading...")
            fp = self.app.repository_manager.download(item["id"], item["title"], self._update_progress)
            with open(fp, "rb") as f:
                data = pickle.load(f)
            scene_data = dict(data)
            meta = scene_data.pop("_repo_meta", {})
            self.app.save_load_manager._apply_loaded_data(scene_data)
            self.app.current_scene_meta = meta
            self.status.set_text("Scene loaded")
        except Exception as e:
            Debug.log(f"Download/load failed: {e}")
            self.status.set_text(f"Error: {str(e)[:50]}")

    def _publish_current(self):
        current_meta = getattr(self.app, "current_scene_meta", {})
        PublishMetaWindow(self.ui_manager, self._on_publish_submit, initial_meta=current_meta)

    def _on_publish_submit(self, meta):
        try:
            raw_data = self.app.save_load_manager.capture_snapshot_data()
            publish_data = raw_data.copy()
            publish_data["_repo_meta"] = meta
            preview = self.app.save_load_manager.render_preview(raw_data)
            publish_data["_preview"] = surface_to_bytes(preview)
            self.app.repository_manager.publish(publish_data, self._update_progress)
            self.status.set_text("Published successfully")
        except Exception as e:
            Debug.log(f"Publish failed: {e}")
            self.status.set_text(f"Publish failed: {str(e)[:40]}")