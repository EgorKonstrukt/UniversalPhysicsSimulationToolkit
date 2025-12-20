import pickle

import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIButton, UIPanel, UISelectionList, UILabel
from pygame_gui.elements import UIProgressBar

from UPST.config import config

from UPST.utils import surface_to_bytes


class PublishMetaWindow(UIWindow):
    def __init__(self, manager, on_submit, initial_meta=None):
        super().__init__(pygame.Rect(300,200,320,220), manager, "Publish Scene")
        self.on_submit = on_submit
        self.initial_meta = initial_meta or {}
        self.title = pygame_gui.elements.UITextEntryLine(
            pygame.Rect(10,40,300,25), manager, container=self)
        self.author = pygame_gui.elements.UITextEntryLine(
            pygame.Rect(10,80,300,25), manager, container=self)
        self.desc = pygame_gui.elements.UITextBox(
            "", pygame.Rect(10,120,300,50), manager, container=self)
        self.ok = UIButton(pygame.Rect(110,180,100,30), "Publish", manager, container=self)

        # Заполнение полей если есть метаданные
        self.title.set_text(self.initial_meta.get("title", ""))
        self.author.set_text(self.initial_meta.get("author", ""))
        self.desc.set_text(self.initial_meta.get("description", ""))

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.ok:
            meta = {
                "title": self.title.get_text(),
                "author": self.author.get_text(),
                "description": self.desc.html_text,
            }
            self.on_submit(meta)
            self.kill()





class RepositoryWindow(UIWindow):
    def __init__(self, rect, manager, app):
        super().__init__(rect, manager, window_display_title="Repository")
        self.app = app

        self.panel = UIPanel(
            relative_rect=pygame.Rect(0,0,rect.width,rect.height),
            manager=manager,
            container=self
        )
        self.progress = UIProgressBar(
            relative_rect=pygame.Rect(10, rect.height - 100, rect.width - 20, 15),
            manager=manager,
            container=self.panel
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
        self.display_items = []
        self.item_map = {}
        for i, it in enumerate(self.items):
            label = f"{it['title']} | {it['author']} | {it['id'][:8]}"
            self.display_items.append(label)
            self.item_map[label] = i
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

    def _update_progress(self, value):
        self.progress.set_current_progress(value * 100)

    def _download_selected(self):
        sel = self.list.get_single_selection()
        if not sel: return
        idx = self.item_map.get(sel)
        if idx is None: return
        self.status.set_text("Downloading...")
        fp = self.app.repository_manager.download(
            self.items[idx]["id"],
            self.items[idx]["title"],
            self._update_progress
        )
        payload = self.app.save_load_manager._load_data_with_fallback(fp)
        scene = pickle.loads(payload["data"])
        self.app.save_load_manager._apply_loaded_data(scene)
        self.app.current_scene_meta = payload.get("meta", {})

    def _publish_current(self):
        current_meta = getattr(self.app, "current_scene_meta", None) or {}
        PublishMetaWindow(self.ui_manager, self._on_publish_submit, initial_meta=current_meta)

    def _on_publish_submit(self, meta):
        data = self.app.save_load_manager.capture_snapshot_data()
        data["_repo_meta"] = meta
        preview = self.app.save_load_manager.render_preview(data)
        data["_preview"] = surface_to_bytes(preview)
        self.app.repository_manager.publish(data, self._update_progress)
        self.status.set_text("Published successfully")
