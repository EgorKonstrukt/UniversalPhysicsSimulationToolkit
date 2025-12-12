from pygame_gui.elements import (UIWindow, UISelectionList, UIButton,
                                 UITextEntryBox)
from pygame_gui.windows import UIColourPickerDialog
import pygame
import pygame_gui

from UPST.gui.context_script_menu import ContextScriptMenu
from UPST.scripting.script_instance import ScriptInstance
from UPST.config import config

class ScriptManagementWindow(UIWindow):
    def __init__(self, rect, manager, script_manager):
        super().__init__(rect, manager, window_display_title="Script Manager", object_id="#script_management_window")
        self.script_manager = script_manager
        self.manager = manager
        w, h = rect.width - 20, rect.height - 140
        panel_rect = pygame.Rect(10, 30, w, h)
        self.list = UISelectionList(relative_rect=panel_rect, item_list=[], manager=manager, container=self)
        y = panel_rect.bottom + 10
        btn_w, btn_h, gap = 110, 30, 10
        self.refresh_btn = UIButton(pygame.Rect(10, y, btn_w, btn_h), "Refresh", manager, self)
        self.pause_btn = UIButton(pygame.Rect(10 + (btn_w + gap) * 1, y, btn_w, btn_h), "Pause All", manager, self)
        self.resume_btn = UIButton(pygame.Rect(10 + (btn_w + gap) * 2, y, btn_w, btn_h), "Resume All", manager, self)
        self.reload_btn = UIButton(pygame.Rect(10 + (btn_w + gap) * 3, y, btn_w, btn_h), "Reload All", manager, self)
        self.auto_reload = False
        self.edit_box = None
        self.refresh_list()

    def get_script_display_text(self, s: ScriptInstance) -> str:
        owner = "World" if s.owner is None else f"{type(s.owner).__name__}@{id(s.owner)}"
        status = "PAUSED" if s.is_paused() else ("RUNNING" if s.running else "STOPPED")
        mode = "Threaded" if s.threaded else "Main"
        return f"{s.name} [{status}] ({mode}) - {owner}"

    def refresh_list(self):
        items = [self.get_script_display_text(s) for s in self.script_manager.get_all_scripts()]
        self.list.set_item_list(items)

    def show_edit_box(self, script: ScriptInstance):
        if self.edit_box: self.edit_box.kill()
        rect = pygame.Rect(50, 50, self.rect.width - 100, self.rect.height - 120)
        self.edit_box = UITextEntryBox(rect, script.code, self.manager, container=self)
        self.editing_script = script

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.refresh_btn:
                self.refresh_list()
            elif event.ui_element == self.pause_btn:
                self.script_manager.pause_all_scripts()
                self.refresh_list()
            elif event.ui_element == self.resume_btn:
                self.script_manager.resume_all_scripts()
                self.refresh_list()
            elif event.ui_element == self.reload_btn:
                self.script_manager.reload_all_scripts()
                self.refresh_list()
        elif event.type == pygame_gui.UI_SELECTION_LIST_DOUBLE_CLICKED_SELECTION and event.ui_element == self.list:
            selected = event.text
            for s in self.script_manager.get_all_scripts():
                if self.get_script_display_text(s) == selected:
                    s.pause() if s.running else s.start()
                    self.refresh_list()
                    break
        elif event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION and event.ui_element == self.list:
            if not self.list.get_single_selection(): return
            selected = self.list.get_single_selection()
            for s in self.script_manager.get_all_scripts():
                if self.get_script_display_text(s) == selected:
                    ctx = ContextScriptMenu(pygame.Rect(pygame.mouse.get_pos(), (200, 200)), self.manager, s, self)
                    break
