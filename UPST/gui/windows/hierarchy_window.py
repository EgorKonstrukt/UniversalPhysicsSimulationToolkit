# UPST/gui/windows/hierarchy_window.py
import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIPanel, UIScrollingContainer, UIButton
from UPST.gui.elements.hierarchy_node_item import HierarchyNodeItem

class HierarchyWindow:
    def __init__(self, rect, manager, root_nodes):
        self.manager = manager
        self.root_nodes = root_nodes
        self.window = UIWindow(
            rect=rect,
            manager=manager,
            window_display_title="Hierarchy",
            object_id='#hierarchy_window'
        )
        self.container = UIScrollingContainer(
            relative_rect=pygame.Rect(5, 30, rect.width - 10, rect.height - 80),
            manager=manager,
            container=self.window
        )
        self.items = []
        self.refresh()

    def refresh(self):
        # Clear all
        for item in self.items:
            item.panel.kill()
        self.items.clear()

        y_offset = 0
        for node in self.root_nodes:
            self._build_node_tree(node, depth=0, y=y_offset)
            y_offset += self._count_visible_nodes(node) * 24

    def _build_node_tree(self, node, depth, y):
        item = HierarchyNodeItem(
            ui_manager=self.manager,
            container=self.container,
            node=node,
            depth=depth,
            on_click=self._on_select,
            on_double_click=self._on_rename
        )
        item.panel.set_relative_position((0, y))
        self.items.append(item)

        if getattr(item, 'expanded', False):
            for child in node.children:
                y += 24
                y = self._build_node_tree(child, depth + 1, y)
        return y

    def _count_visible_nodes(self, node):
        count = 1
        # For simplicity, assume all collapsed; expand logic later
        return count

    def _on_select(self, node):
        print(f"Selected: {node.name}")

    def _on_rename(self, node):
        print(f"Rename: {node.name}")

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for item in self.items:
                item.handle_click(event)

    def is_alive(self):
        return self.window.alive()