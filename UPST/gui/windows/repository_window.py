import pickle
import threading

import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIButton, UIPanel, UILabel, UIProgressBar, UITextEntryLine, \
    UITextEntryBox, UIImage
from UPST.utils.utils import surface_to_bytes, bytes_to_surface
from UPST.debug.debug_manager import Debug



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

REPO_LIST_LOADED_EVENT = pygame.event.custom_type()
REPO_PREVIEW_READY_EVENT = pygame.event.custom_type()

class RepositoryWindow(UIWindow):
    def __init__(self, rect, manager, app):
        super().__init__(rect, manager, window_display_title="Repository")
        self.app = app
        self.manager = manager
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

        self.refresh_btn = UIButton(
            relative_rect=pygame.Rect(10, 10, 90, 25),
            text="Refresh",
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
        self.next_btn = UIButton(relative_rect=pygame.Rect(270, rect.height - 115, 40, 20),
                                 text=">",
                                 manager=manager,
                                 container=self.panel)

        self.items = []
        self.item_panels = []
        self.preview_cache = {}
        self._load_list()

    def _load_list(self):
        def _bg():
            items = self.app.repository_manager.fetch_list(page=self.page, limit=50)
            event = pygame.event.Event(REPO_LIST_LOADED_EVENT, {"items": items})
            pygame.event.post(event)
        threading.Thread(target=_bg, daemon=True).start()

    def _clear_items(self):
        for entry in self.item_panels:
            if isinstance(entry, tuple):
                panel = entry[0]
            else:
                panel = entry
            panel.kill()
        self.item_panels.clear()

    def _layout_items(self):
        self._clear_items()
        if not self.items:
            return
        item_width, item_height = 160, 220
        cols = max(1, (self.panel.rect.width - 40) // item_width)
        spacing_x = (self.panel.rect.width - 20 - cols * item_width) // max(1, cols - 1) if cols > 1 else 0
        start_y = 50
        for idx, item in enumerate(self.items):
            row = idx // cols
            col = idx % cols
            x = 10 + col * (item_width + spacing_x)
            y = start_y + row * item_height
            panel = UIPanel(
                relative_rect=pygame.Rect(x, y, item_width, item_height),
                manager=self.manager,
                container=self.panel,
                margins={"left": 0, "right": 0, "top": 0, "bottom": 0}
            )
            title = item.get("title", "Untitled")[:20]
            label = UILabel(
                relative_rect=pygame.Rect(5, item_height - 60, item_width - 10, 20),
                text=title,
                manager=self.manager,
                container=panel
            )
            btn = UIButton(
                relative_rect=pygame.Rect((item_width - 80) // 2, item_height - 30, 80, 25),
                text="Download",
                manager=self.manager,
                container=panel
            )
            btn._item_index = idx
            preview_rect = pygame.Rect((item_width - 128) // 2, 5, 128, 128)
            preview_img = UIImage(
                relative_rect=preview_rect,
                image_surface=pygame.Surface((128, 128)),
                manager=self.manager,
                container=panel
            )
            preview_img._item_index = idx
            self.item_panels.append((panel, label, btn, preview_img))
            self._request_preview(idx, item)

    def _request_preview(self, idx, item):
        preview_bytes = item.get("_preview")
        if preview_bytes in self.preview_cache:
            surf = self.preview_cache[preview_bytes]
            self._set_preview(idx, surf)
        elif preview_bytes:
            def _load_preview():
                try:
                    surf = bytes_to_surface(preview_bytes, (128, 128))
                    if surf:
                        self.preview_cache[preview_bytes] = surf
                        event = pygame.event.Event(REPO_PREVIEW_READY_EVENT, {"index": idx, "surface": surf})
                        pygame.event.post(event)
                except Exception as e:
                    Debug.log(f"Preview decode failed for idx {idx}: {e}")
            threading.Thread(target=_load_preview, daemon=True).start()
        else:
            self._set_preview(idx, self._default_preview())

    def _default_preview(self):
        surf = pygame.Surface((128, 128))
        surf.fill((40, 40, 40))
        pygame.draw.line(surf, (80, 80, 80), (0, 0), (128, 128), 2)
        pygame.draw.line(surf, (80, 80, 80), (128, 0), (0, 128), 2)
        return surf

    def _set_preview(self, idx, surf):
        for panel, label, btn, img in self.item_panels:
            if hasattr(img, "_item_index") and img._item_index == idx:
                img.set_image(surf)
                break

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.refresh_btn:
                self._load_list()
            elif event.ui_element == self.publish_btn:
                self._publish_current()
            elif event.ui_element == self.prev_btn:
                if self.page > 0:
                    self.page -= 1
                    self._load_list()
            elif event.ui_element == self.next_btn:
                self.page += 1
                self._load_list()
            else:
                for panel, label, btn, img in self.item_panels:
                    if event.ui_element == btn:
                        self._download_item(btn._item_index)
                        return
        elif event.type == REPO_LIST_LOADED_EVENT:
            self.items = event.dict["items"]
            self._layout_items()
            self.page_label.set_text(f"Page {self.page}")
            self.status.set_text(f"Page {self.page}, {len(self.items)} items")
        elif event.type == REPO_PREVIEW_READY_EVENT:
            self._set_preview(event.dict["index"], event.dict["surface"])

    def _update_progress(self, value: float):
        self.progress.set_current_progress(min(max(value, 0.0), 1.0) * 100)

    def _download_item(self, idx):
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