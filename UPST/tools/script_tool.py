import pygame

from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools.base_tool import BaseTool
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.debug.debug_manager import Debug
import time

class ScriptTool(BaseTool):
    name = "ScriptTool"
    icon_path = "sprites/gui/python.png"
    def __init__(self, pm):
        super().__init__(pm)
        self.scripts = []
        self.rects = []
        self.font = pygame.font.SysFont("Consolas", 24)
        self.last_update = 0
        self.update_interval = 0.5
        self.hover_idx = -1
        self.execution_times = {}
    def activate(self):
        super().activate()
        self._refresh_scripts()
        self.undo_redo.take_snapshot()
    def deactivate(self):
        self.scripts.clear()
        self.rects.clear()
        self.execution_times.clear()
        self.undo_redo.take_snapshot()
    def _refresh_scripts(self):
        if hasattr(self.pm, 'script_manager'):
            self.scripts = self.pm.script_manager.get_all_scripts()
            self.rects = []
            y = 200
            for i, script in enumerate(self.scripts):
                rect = pygame.Rect(100, y, 400, 30)
                self.rects.append(rect)
                y += 40
    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(world_pos):
                    script = self.scripts[i]
                    if script.running:
                        self.pm.script_manager.stop_script(script)
                        self.undo_redo.take_snapshot()
                    else:
                        self.pm.script_manager.start_script(script)
                        self.undo_redo.take_snapshot()
                    synthesizer.play_frequency(1200 if script.running else 800, duration=0.05, waveform='sine')
                    return
    def draw_preview(self, screen, camera):
        current_time = time.time()
        if current_time - self.last_update > self.update_interval:
            self._refresh_scripts()
            self.last_update = current_time
        mouse_pos = pygame.mouse.get_pos()
        world_mouse = camera.screen_to_world(mouse_pos)
        self.hover_idx = -1
        for i, rect in enumerate(self.rects):
            world_rect = pygame.Rect(
                camera.world_to_screen((rect.x, rect.y))[0],
                camera.world_to_screen((rect.x, rect.y))[1],
                rect.width * camera.scaling,
                rect.height * camera.scaling
            )
            if world_rect.collidepoint(mouse_pos):
                self.hover_idx = i
            color = (100, 200, 100) if self.scripts[i] else (200, 100, 100)
            if i == self.hover_idx:
                color = (min(color[0]+50, 255), min(color[1]+50, 255), min(color[2]+50, 255))
            pygame.draw.rect(screen, color, world_rect, 2)
            status = "RUNNING" if self.scripts[i].running else "STOPPED"
            delay = self.execution_times.get(self.scripts[i].name, 0)
            text = f"{self.scripts[i].name}: {status} ({delay:.2f}ms)"
            text_surf = self.font.render(text, True, color)
            screen.blit(text_surf, (world_rect.x + 5, world_rect.y + 5))
    def update(self, dt):
        for script in self.scripts:
            if hasattr(script, '_last_exec_time'):
                self.execution_times[script.name] = script._last_exec_time * 1000