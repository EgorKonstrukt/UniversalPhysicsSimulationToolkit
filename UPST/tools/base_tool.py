import pygame
import pygame_gui
from UPST.modules.undo_redo_manager import get_undo_redo

class BaseTool:
    def __init__(self, app):
        self.pm = app.physics_manager
        self.app = app
        self.ui_manager = None
        self.drag_start = None
        self.preview = None
        self.settings_window = None
        self.tool_system = app.tool_manager
        self.undo_redo = get_undo_redo()
        self.font = pygame.font.SysFont('Consolas', 14)
        self._last_hatch_offset = 0.0

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
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame_gui.UI_WINDOW_CLOSE and event.ui_element == self.settings_window:
            self.settings_window = None
        # if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        #     self.drag_start = world_pos
        # elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        #     if self.drag_start:
        #         self.spawn_dragged(self.drag_start, world_pos)
        #     self.drag_start = None
        # elif event.type == pygame.MOUSEMOTION and self.drag_start:
        #     self.preview = self._calc_preview(world_pos)

    def spawn_dragged(self, start, end):
        pass

    def _calc_preview(self, end_pos):
        return None

    def draw_preview(self, screen, camera):
        if not self.preview: return
        current_time = pygame.time.get_ticks() / 1000.0
        self._last_hatch_offset = (current_time * 40) % 20
        self._draw_custom_preview(screen, camera)
        self._draw_metrics(screen, camera)

    def _draw_custom_preview(self, screen, camera):
        pass

    def _draw_metrics(self, screen, camera):
        if not self.preview: return
        lines = self._get_metric_lines()
        base_pos = camera.world_to_screen(self.preview['position'])
        zoom = camera.scaling
        font_size = max(8, int(14))
        try:
            font = pygame.font.SysFont('Consolas', font_size)
        except:
            font = pygame.font.Font(None, font_size)
        dy = 0
        for line in lines:
            surf = font.render(line, True, (255, 255, 255))
            screen.blit(surf, (base_pos[0] + 10, base_pos[1] + dy))
            dy += int(16)

    def _get_metric_lines(self):
        return []