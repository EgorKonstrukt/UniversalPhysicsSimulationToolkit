import os
import psutil
import time
import pygame
from UPST.tools.base_tool import BaseTool
from UPST.sound.sound_synthesizer import synthesizer
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.debug.debug_manager import Debug

class ScriptTool(BaseTool):
    name = "ScriptTool"
    icon_path = "sprites/gui/python.png"

    def __init__(self, pm, app):
        super().__init__(pm, app)
        self.scripts = []
        self.rects = []
        self.font = pygame.font.SysFont("Consolas", 14)
        self.last_update = 0
        self.update_interval = 0.3
        self.hover_idx = -1
        self.execution_times = {}
        self.memory_usage = {}

    def activate(self):
        super().activate()
        self._refresh_scripts()
        self.undo_redo.take_snapshot()

    def deactivate(self):
        self.scripts.clear()
        self.rects.clear()
        self.execution_times.clear()
        self.memory_usage.clear()
        self.undo_redo.take_snapshot()

    def _refresh_scripts(self):
        if hasattr(self.pm, 'script_manager'):
            self.scripts = self.pm.script_manager.get_all_scripts()
            self.rects = []
            y = 100
            for script in self.scripts:
                rect = pygame.Rect(50, y, 500, 28)
                self.rects.append(rect)
                y += 35

    def handle_event(self, event, world_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(world_pos):
                    script = self.scripts[i]
                    if script.running:
                        self.pm.script_manager.stop_script(script)
                    else:
                        self.pm.script_manager.start_script(script)
                    synthesizer.play_frequency(1200 if script.running else 800, 0.05, 'sine')
                    self.undo_redo.take_snapshot()
                    return

    def draw_preview(self, screen, camera):
        now = time.time()
        if now - self.last_update > self.update_interval:
            self._refresh_scripts()
            self.last_update = now
        mouse = pygame.mouse.get_pos()
        self.hover_idx = -1
        for i, rect in enumerate(self.rects):
            world_rect = pygame.Rect(
                *camera.world_to_screen((rect.x, rect.y)),
                rect.width * camera.scaling,
                rect.height * camera.scaling
            )
            if world_rect.collidepoint(mouse):
                self.hover_idx = i
            script = self.scripts[i]
            base = (100, 200, 100) if script.running else (200, 100, 100)
            if script.is_paused(): base = (200, 200, 100)
            color = tuple(min(c + 50, 255) for c in base) if i == self.hover_idx else base
            pygame.draw.rect(screen, color, world_rect, 2)
            exec_ms = self.execution_times.get(script.name, 0)
            mem_kb = self.memory_usage.get(script.name, 0)
            status = "PAUSED" if script.is_paused() else ("RUNNING" if script.running else "STOPPED")
            label = f"{script.name} | {status} | {exec_ms:.1f}ms | {mem_kb:.0f}KB"
            surf = self.font.render(label, True, color)
            screen.blit(surf, (world_rect.x + 5, world_rect.y + 5))

    def update(self, dt):
        for script in self.scripts:
            if hasattr(script, '_last_exec_time'):
                self.execution_times[script.name] = script._last_exec_time * 1000
            try:
                pid = os.getpid()
                proc = psutil.Process(pid)
                self.memory_usage[script.name] = proc.memory_info().rss / 1024
            except Exception:
                self.memory_usage[script.name] = 0