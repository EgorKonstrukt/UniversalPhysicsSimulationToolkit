from pygame_gui.elements import UIWindow, UISelectionList, UIButton
import pygame
import pygame_gui


class ScriptManagementWindow(UIWindow):
    def __init__(self, rect, manager, script_manager):
        super().__init__(rect, manager, window_display_title="Running Scripts", object_id="#script_management_window")
        self.script_manager = script_manager
        panel_rect = pygame.Rect(0, 0, rect.width - 20, rect.height - 60)
        panel_rect.topleft = (10, 30)
        self.list = UISelectionList(relative_rect=panel_rect, item_list=[], manager=manager, container=self)
        btn_rect = pygame.Rect(10, panel_rect.bottom + 10, 100, 30)
        self.refresh_btn = UIButton(relative_rect=btn_rect, text="Refresh", manager=manager, container=self)
        self.refresh_list()

    def refresh_list(self):
        items = []
        for s in self.script_manager.get_all_scripts():
            if s.running:
                owner_desc = "World" if s.owner is None else f"Body@{id(s.owner)}"
                items.append(f"{s.name} ({'Threaded' if s.threaded else 'Main'}) - {owner_desc}")
        self.list.set_item_list(items)

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.refresh_btn: self.refresh_list()
        if event.type == pygame_gui.UI_SELECTION_LIST_DOUBLE_CLICKED_SELECTION and event.ui_element == self.list:
            selected = event.text
            for s in self.script_manager.get_all_scripts():
                if s.running:
                    owner_desc = "World" if s.owner is None else f"Body@{id(s.owner)}"
                    if f"{s.name} ({'Threaded' if s.threaded else 'Main'}) - {owner_desc}" == selected:
                        s.stop()
                        self.refresh_list()
                        break