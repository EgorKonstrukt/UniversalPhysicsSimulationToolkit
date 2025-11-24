import pygame
from UPST.modules.undo_redo_manager import get_undo_redo


class BaseTool:
    def __init__(self, pm):
        self.pm = pm
        self.ui_manager = None
        self.drag_start = None
        self.preview = None
        self.settings_window = None
        self.undo_redo = get_undo_redo()

    def set_ui_manager(self, ui_manager):
        self.ui_manager = ui_manager

    def create_settings_window(self):
        pass

    def activate(self):
        if self.ui_manager:
            self.ui_manager.hide_all_object_windows()
        if self.settings_window:
            self.settings_window.show()

    def deactivate(self):
        if self.settings_window:
            self.settings_window.hide()
        self.drag_start = None
        self.preview = None

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drag_start = world_pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_start:
                self.spawn_dragged(self.drag_start, world_pos)
            self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start:
            self.preview = self._calc_preview(world_pos)

    def spawn_dragged(self, start, end):
        pass

    def _calc_preview(self, end_pos):
        return None

    def draw_preview(self, screen, camera):
        if not self.preview: return
        self._draw_custom_preview(screen, camera)

    def _draw_custom_preview(self, screen, camera):
        pass