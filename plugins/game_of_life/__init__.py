from __future__ import annotations

from pathlib import Path

import numpy as np
import pygame
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING, Dict, Any
from numba import njit, prange
from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.tools.base_tool import BaseTool

try:
    from plugin_base import Plugin
except ImportError:
    pass


@dataclass
class GameOfLifeConfig:
    enabled: bool = True
    cell_size: float = 1.0
    update_interval: float = 0.25
    birth_rule: str = "3"
    survival_rule: str = "23"
    grid_scale: float = 1.0
    world_origin_x: float = 0.0
    world_origin_y: float = 0.0

PLUGIN_DIR = Path(__file__).parent


class GameOfLifeTool(BaseTool):
    name = "game_of_life"
    category = "Special"
    icon_path = None
    tooltip = "Brush tool for Conway's Game of Life"

    def __init__(self, app):
        super().__init__(app)
        self.active = False
        self.brush_mode = True
        self.brush_radius = 1

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def handle_event(self, event, world_pos) -> bool:
        if not self.active:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.brush_mode = True
                self._apply_brush_from_world(world_pos)
                return True
            elif event.button == 3:
                self.brush_mode = False
                self._apply_brush_from_world(world_pos)
                return True
        elif event.type == pygame.MOUSEMOTION and (event.buttons[0] or event.buttons[2]):
            self._apply_brush_from_world(world_pos)
            return True
        return False

    def _apply_brush_from_world(self, world_pos):
        manager = self.app.plugin_manager.plugin_instances.get("game_of_life")
        if not manager or not hasattr(manager, "manager") or not manager.manager:
            return
        gof_manager = manager.manager
        gof_manager.apply_brush(world_pos, self.brush_mode, self.brush_radius)

class PluginImpl:
    def __init__(self, app: "App"):
        self.app = app
        self.manager = None
        self.enabled = getattr(config.game_of_life, "enabled", True)
        self.tool = GameOfLifeTool(app)

    def on_load(self, plugin_manager, instance):
        if self.enabled:
            self.manager = GameOfLifeManager(self.app.camera)
        Debug.log_info("Game of Life plugin loaded.", "Plugins")

    def on_unload(self, plugin_manager, instance):
        if self.manager:
            self.manager.shutdown()
            self.manager = None
        Debug.log_info("Game of Life plugin unloaded.", "Plugins")

    def on_update(self, plugin_manager, instance, dt: float):
        if self.manager and self.enabled:
            self.manager.update(dt)

    def on_draw(self, plugin_manager, instance):
        if self.manager and self.enabled:
            self.manager.render(self.app.screen, self.app.camera)

    def get_tools(self, app):
        return [self.tool]

    def toggle_enabled(self, value: bool):
        self.enabled = value
        if value and not self.manager:
            self.manager = GameOfLifeManager(self.app.camera)
        elif not value and self.manager:
            self.manager.shutdown()
            self.manager = None
        config.game_of_life.enabled = value
        self.app.config.save()

    def set_cell_size(self, size: float):
        config.game_of_life.cell_size = max(0.01, size)
        self.app.config.save()
        if self.manager:
            self.manager.reconfigure_grid()

    def set_update_interval(self, interval: float):
        config.game_of_life.update_interval = max(0.01, interval)
        self.app.config.save()

    def set_rules(self, birth: str, survival: str):
        config.game_of_life.birth_rule = birth
        config.game_of_life.survival_rule = survival
        self.app.config.save()
        if self.manager:
            self.manager.compile_rules()

    def set_grid_scale(self, scale: float):
        config.game_of_life.grid_scale = max(0.001, scale)
        self.app.config.save()
        if self.manager:
            self.manager.reconfigure_grid()

    def console_toggle(self, expr: str):
        val = expr.strip().lower() in ("1", "true", "on")
        self.toggle_enabled(val)
        return f"Game of Life {'enabled' if val else 'disabled'}."

    def console_set_cell_size(self, expr: str):
        try:
            s = float(expr.strip())
            self.set_cell_size(s)
            return f"Cell size set to {s}."
        except ValueError:
            return "Invalid number."

    def console_set_speed(self, expr: str):
        try:
            inv = float(expr.strip())
            self.set_update_interval(inv)
            return f"Update interval set to {inv}s."
        except ValueError:
            return "Invalid number."

    def console_set_rules(self, expr: str):
        parts = expr.strip().split()
        if len(parts) != 2:
            return "Usage: gol_rules <birth> <survival> (e.g., '3' '23')"
        b, s = parts
        self.set_rules(b, s)
        return f"Rules set: B{b}/S{s}."

    def console_set_scale(self, expr: str):
        try:
            sc = float(expr.strip())
            self.set_grid_scale(sc)
            return f"Grid scale set to {sc}."
        except ValueError:
            return "Invalid number."

PLUGIN = Plugin(
    name="game_of_life",
    version="1.0.0",
    description="Conway's Game of Life accelerated with Numba, operating in world space.",
    author="Zarrakun",
    icon_path=None,
    dependency_specs={},
    config_class=GameOfLifeConfig,
    on_load=lambda pm, inst: inst.on_load(pm, inst),
    on_unload=lambda pm, inst: inst.on_unload(pm, inst),
    on_update=lambda pm, inst, dt: inst.on_update(pm, inst, dt),
    on_draw=lambda pm, inst: inst.on_draw(pm, inst),
    console_commands={
        "gol_toggle": lambda inst, expr: inst.console_toggle(expr),
        "gol_cell_size": lambda inst, expr: inst.console_set_cell_size(expr),
        "gol_speed": lambda inst, expr: inst.console_set_speed(expr),
        "gol_rules": lambda inst, expr: inst.console_set_rules(expr),
        "gol_scale": lambda inst, expr: inst.console_set_scale(expr),
    },
    command_help={
        "gol_toggle": "Enable/disable Game of Life simulation",
        "gol_cell_size": "Set real-world size of each cell (in meters)",
        "gol_speed": "Set simulation update interval in seconds",
        "gol_rules": "Set cellular automaton rules (e.g., '3' '23' for Conway)",
        "gol_scale": "Set rendering scale factor for grid cells",
    }
)

@njit(parallel=True, fastmath=True)
def step_kernel(grid, next_grid, w, h, birth_mask, survival_mask):
    for i in prange(w):
        for j in range(h):
            alive = grid[i, j]
            neighbors = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < w and 0 <= nj < h:
                        neighbors += grid[ni, nj]
            if alive:
                next_grid[i, j] = (survival_mask >> neighbors) & 1
            else:
                next_grid[i, j] = (birth_mask >> neighbors) & 1

class GameOfLifeManager:
    def __init__(self, camera):
        self.camera = camera
        self.cell_size = config.game_of_life.cell_size
        self.update_interval = config.game_of_life.update_interval
        self.grid_scale = config.game_of_life.grid_scale
        self.origin = np.array([config.game_of_life.world_origin_x, config.game_of_life.world_origin_y], dtype=np.float32)
        self.last_update = 0.0
        self.running = True
        self.compile_rules()
        self.reconfigure_grid()

    def compile_rules(self):
        b_str = config.game_of_life.birth_rule
        s_str = config.game_of_life.survival_rule
        self.birth_neighbors = set(int(c) for c in b_str if c.isdigit())
        self.survival_neighbors = set(int(c) for c in s_str if c.isdigit())

    def reconfigure_grid(self):
        self.cell_size = config.game_of_life.cell_size
        self.grid_scale = config.game_of_life.grid_scale
        self.world_to_grid_factor = 1.0 / self.cell_size
        self.grid_shape = (0, 0)
        self.offset = (0, 0)
        self.grid = np.zeros((0, 0), dtype=np.int8)
        self.next_grid = np.zeros((0, 0), dtype=np.int8)

    def _world_to_grid_index(self, x: float, y: float):
        gx = int((x - self.origin[0]) * self.world_to_grid_factor)
        gy = int((y - self.origin[1]) * self.world_to_grid_factor)
        return gx, gy

    def _ensure_grid_capacity(self, gx: int, gy: int):
        margin = 64
        min_gx, max_gx = min(gx - margin, self.offset[0]), max(gx + margin, self.offset[0] + self.grid_shape[0])
        min_gy, max_gy = min(gy - margin, self.offset[1]), max(gy + margin, self.offset[1] + self.grid_shape[1])
        new_w = max_gx - min_gx
        new_h = max_gy - min_gy
        if new_w <= 0 or new_h <= 0:
            return
        if (new_w, new_h) != self.grid_shape or (min_gx, min_gy) != self.offset:
            old_grid = self.grid if self.grid_shape[0] > 0 else None
            self.grid = np.zeros((new_w, new_h), dtype=np.int8)
            self.next_grid = np.zeros((new_w, new_h), dtype=np.int8)
            if old_grid is not None:
                dx = self.offset[0] - min_gx
                dy = self.offset[1] - min_gy
                w_old, h_old = self.grid_shape
                x0, x1 = max(0, dx), min(w_old + dx, new_w)
                y0, y1 = max(0, dy), min(h_old + dy, new_h)
                if x0 < x1 and y0 < y1:
                    self.grid[x0:x1, y0:y1] = old_grid[max(0, -dx):max(0, -dx)+(x1-x0),
                                                       max(0, -dy):max(0, -dy)+(y1-y0)]
            self.offset = (min_gx, min_gy)
            self.grid_shape = (new_w, new_h)

    def update(self, dt: float):
        self.last_update += dt
        if self.last_update < self.update_interval:
            return
        self.last_update = 0.0
        if self.grid_shape[0] == 0:
            return
        birth_mask = sum(1 << n for n in self.birth_neighbors)
        survival_mask = sum(1 << n for n in self.survival_neighbors)
        step_kernel(self.grid, self.next_grid, self.grid_shape[0], self.grid_shape[1], birth_mask, survival_mask)
        self.grid, self.next_grid = self.next_grid, self.grid

    def apply_brush(self, world_pos, mode: bool, radius: int = 1):
        gx, gy = self._world_to_grid_index(world_pos[0], world_pos[1])
        self._ensure_grid_capacity(gx, gy)
        idx_x = gx - self.offset[0]
        idx_y = gy - self.offset[1]
        if not (0 <= idx_x < self.grid_shape[0] and 0 <= idx_y < self.grid_shape[1]):
            return
        val = 1 if mode else 0
        self.grid[idx_x, idx_y] = val

    def render(self, screen: pygame.Surface, camera):
        if self.grid_shape[0] == 0:
            return
        cam_x, cam_y = camera.position
        half_w = camera.screen_width / camera.scaling * 0.6
        half_h = camera.screen_height / camera.scaling * 0.6
        min_x = cam_x - half_w
        max_x = cam_x + half_w
        min_y = cam_y - half_h
        max_y = cam_y + half_h
        g_min_x = int((min_x - self.origin[0]) * self.world_to_grid_factor) - 2
        g_max_x = int((max_x - self.origin[0]) * self.world_to_grid_factor) + 2
        g_min_y = int((min_y - self.origin[1]) * self.world_to_grid_factor) - 2
        g_max_y = int((max_y - self.origin[1]) * self.world_to_grid_factor) + 2
        g_min_x = max(g_min_x, self.offset[0])
        g_max_x = min(g_max_x, self.offset[0] + self.grid_shape[0])
        g_min_y = max(g_min_y, self.offset[1])
        g_max_y = min(g_max_y, self.offset[1] + self.grid_shape[1])
        if g_min_x >= g_max_x or g_min_y >= g_max_y:
            return
        for gx in range(g_min_x, g_max_x):
            for gy in range(g_min_y, g_max_y):
                if self.grid[gx - self.offset[0], gy - self.offset[1]]:
                    wx = self.origin[0] + gx * self.cell_size
                    wy = self.origin[1] + gy * self.cell_size
                    sx, sy = camera.world_to_screen((wx, wy))
                    r = max(1, int(self.grid_scale * camera.scaling))
                    pygame.draw.rect(screen, (0, 255, 0), (sx - r // 2, sy - r // 2, r, r))

    def shutdown(self):
        self.running = False