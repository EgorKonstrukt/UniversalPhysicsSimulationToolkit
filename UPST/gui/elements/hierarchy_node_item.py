import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel

class HierarchyNodeItem:
    def __init__(self, ui_manager, container, node, depth=0, on_click=None, on_double_click=None, on_right_click=None):
        self.node = node
        self.depth = depth
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.on_right_click = on_right_click
        self.expanded = False
        self.children_ui = []
        indent = depth * 20
        height = 24
        self.panel = UIPanel(
            relative_rect=pygame.Rect(indent, 0, container.rect.width - indent, height),
            manager=ui_manager,
            container=container,
            margins={'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
            object_id='#hierarchy_item'
        )
        self.button = UIButton(
            relative_rect=pygame.Rect(0, 0, self.panel.rect.width, height),
            text=self._get_display_text(),
            manager=ui_manager,
            container=self.panel,
            object_id='#hierarchy_button'
        )
        self.panel.join_focus_sets(self.button)
        self._last_click = 0

    def _get_display_text(self):
        prefix = "▼ " if self.node.children else "  "
        return prefix + getattr(self.node, 'name', 'Unnamed')

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.button.get_abs_rect().collidepoint(event.pos):
                if self.on_right_click:
                    self.on_right_click(self.node, event.pos)
                return True
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.button:
                now = pygame.time.get_ticks()
                if now - self._last_click < 300:
                    if self.on_double_click: self.on_double_click(self.node)
                else:
                    if self.on_click: self.on_click(self.node)
                self._last_click = now
                return True
        return False