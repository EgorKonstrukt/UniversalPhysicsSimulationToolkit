from __future__ import annotations
import threading
import time
import math
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
import pygame
import pygame.gfxdraw
import pymunk
from numba import njit, prange
import numpy as np

from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import get_gizmos

try:
    from plugin_base import Plugin
except ImportError:
    pass

@njit(fastmath=True)
def celsius_to_kelvin(c: float) -> float:
    return c + 273.15

@njit(parallel=True, fastmath=True)
def compute_thermal_step_celsius(
    positions: np.ndarray,
    temperatures_c: np.ndarray,
    heat_capacities: np.ndarray,
    conductivities: np.ndarray,
    dt: float,
    ambient_temp_c: float,
    radiation_coeff: float,
    air_conductivity: float,
    world_half_w: float,
    world_half_h: float
) -> np.ndarray:
    N = len(temperatures_c)
    dT = np.zeros(N, dtype=np.float32)
    sigma = 5.670374419e-8
    ambient_k = celsius_to_kelvin(ambient_temp_c)
    interaction_radius = world_half_w * 0.25
    r_limit_sq = interaction_radius * interaction_radius
    for i in prange(N):
        T_c = temperatures_c[i]
        T_k = celsius_to_kelvin(T_c)
        C = heat_capacities[i]
        k_i = conductivities[i]
        power = 0.0
        for j in range(N):
            if i == j: continue
            dx = positions[j, 0] - positions[i, 0]
            dy = positions[j, 1] - positions[i, 1]
            if abs(dx) > world_half_w or abs(dy) > world_half_h: continue
            r2 = dx*dx + dy*dy
            if r2 < 1e-6 or r2 > r_limit_sq: continue
            r = math.sqrt(r2)
            T_j = temperatures_c[j]
            k_j = conductivities[j]
            k_eff = (2.0 * k_i * k_j) / (k_i + k_j + 1e-6)
            power += k_eff * (T_j - T_c) / r
        air_power = air_conductivity * (ambient_temp_c - T_c)
        radiative = radiation_coeff * sigma * (ambient_k**4 - T_k**4)
        dT[i] = (power + air_power + radiative) * dt / C
    return temperatures_c + dT

@dataclass
class ThermalConfig:
    enabled: bool = True
    ambient_temperature: float = 20.0
    radiation_coeff: float = 0.8
    air_conductivity: float = 100.0
    dt: float = 1.0 / 60.0

class PluginImpl:
    def __init__(self, app: "UniversalPhysicsSimulationToolkit"):
        self.app = app
        self.manager = None
        self.enabled = getattr(config.thermal_simulation, "enabled", True)

    def on_load(self, plugin_manager, instance):
        if self.enabled:
            self.manager = ThermalManager(self.app.physics_manager, self.app.camera)
        Debug.log_info("Thermal simulation plugin loaded.", "Plugins")

    def on_unload(self, plugin_manager, instance):
        if self.manager:
            self.manager.shutdown()
            self.manager = None
        Debug.log_info("Thermal simulation plugin unloaded.", "Plugins")

    def on_update(self, plugin_manager, instance, dt: float):
        pass  # управление в отдельном потоке

    def on_draw(self, plugin_manager, instance):
        if self.manager and self.enabled:
            self.manager.render_heatmap(self.app.screen)
            self.manager.draw_hover_temperature()

    def on_event(self, plugin_manager, instance, event) -> bool:
        return False

    def toggle_enabled(self, value: bool):
        self.enabled = value
        if value and not self.manager:
            self.manager = ThermalManager(self.app.physics_manager, self.app.camera)
        elif not value and self.manager:
            self.manager.shutdown()
            self.manager = None
        config.thermal_simulation.enabled = value
        self.app.config.save()

    def set_ambient_temp(self, temp: float):
        if self.manager:
            self.manager.ambient_temperature = temp
        config.thermal_simulation.ambient_temperature = temp
        self.app.config.save()

    def console_toggle(self, expr: str):
        val = expr.strip().lower() in ("1", "true", "on")
        self.toggle_enabled(val)
        return f"Thermal simulation {'enabled' if val else 'disabled'}."

    def console_set_ambient(self, expr: str):
        try:
            t = float(expr.strip())
            self.set_ambient_temp(t)
            return f"Ambient temperature set to {t}°C."
        except ValueError:
            return "Invalid number."

PLUGIN = Plugin(
    name="thermal_simulation",
    version="1.0.0",
    description="Real-time thermal conduction and radiation simulation with JIT acceleration.",
    author="Zarrakun",
    icon_path=None,
    dependency_specs={},
    config_class=ThermalConfig,
    on_load=lambda pm, inst: inst.on_load(pm, inst),
    on_unload=lambda pm, inst: inst.on_unload(pm, inst),
    on_update=lambda pm, inst, dt: inst.on_update(pm, inst, dt),
    on_draw=lambda pm, inst: inst.on_draw(pm, inst),
    on_event=lambda pm, inst, ev: inst.on_event(pm, inst, ev),
    console_commands={
        "thermal_toggle": lambda inst, expr: inst.console_toggle(expr),
        "thermal_ambient": lambda inst, expr: inst.console_set_ambient(expr),
    },
    command_help={
        "thermal_toggle": "Enable/disable thermal simulation (usage: thermal_toggle [true/false])",
        "thermal_ambient": "Set ambient temperature in °C (usage: thermal_ambient <value>)",
    }
)

class ThermalManager:
    def __init__(self, physics_manager, camera):
        self.physics_manager = physics_manager
        self.camera = camera
        self.running = True
        self.dt = config.thermal_simulation.dt
        self.ambient_temperature = config.thermal_simulation.ambient_temperature
        self.radiation_coeff = config.thermal_simulation.radiation_coeff
        self.air_conductivity = config.thermal_simulation.air_conductivity
        self._thread = threading.Thread(target=self._thermal_loop, daemon=True)
        self._thread.start()
        Debug.log_info("ThermalManager initialized (°C mode, JIT).", "Thermal")

    def _thermal_loop(self):
        while self.running:
            try:
                visible_bodies = self._get_visible_bodies()
                if not visible_bodies:
                    time.sleep(0.016)
                    continue
                N = len(visible_bodies)
                pos = np.empty((N, 2), dtype=np.float32)
                temp = np.empty(N, dtype=np.float32)
                heat_cap = np.empty(N, dtype=np.float32)
                cond = np.empty(N, dtype=np.float32)
                for i, body in enumerate(visible_bodies):
                    pos[i, 0] = body.position.x
                    pos[i, 1] = body.position.y
                    temp[i] = getattr(body, 'temperature', self.ambient_temperature)
                    heat_cap[i] = max(1.0, getattr(body, 'heat_capacity', 1000.0))
                    cond[i] = max(0.01, getattr(body, 'thermal_conductivity', 1.0))
                half_w = self.camera.screen_width / self.camera.scaling * 0.6
                half_h = self.camera.screen_height / self.camera.scaling * 0.6
                new_temp = compute_thermal_step_celsius(
                    pos, temp, heat_cap, cond, self.dt,
                    self.ambient_temperature, self.radiation_coeff,
                    self.air_conductivity, half_w, half_h
                )
                for i, body in enumerate(visible_bodies):
                    body.temperature = float(new_temp[i])
                time.sleep(self.dt)
            except Exception as e:
                Debug.log_error(f"ThermalManager thread error: {e}", "Thermal")
                time.sleep(0.1)

    def _get_visible_bodies(self) -> List[pymunk.Body]:
        cam_x, cam_y = self.camera.position
        half_w = self.camera.get_viewport_size()[0] * 0.6
        half_h = self.camera.get_viewport_size()[1] * 0.6
        visible = []
        for body in self.physics_manager.space.bodies:
            if body.body_type != pymunk.Body.DYNAMIC: continue
            if abs(body.position.x - cam_x) > half_w: continue
            if abs(body.position.y - cam_y) > half_h: continue
            visible.append(body)
        return visible

    def render_heatmap(self, screen: pygame.Surface):
        bodies = self._get_visible_bodies()
        if not bodies: return
        temps = [getattr(b, 'temperature', self.ambient_temperature) for b in bodies]
        min_t, max_t = min(temps), max(temps)
        t_range = max(1.0, max_t - min_t)
        for body, t in zip(bodies, temps):
            t_norm = (t - min_t) / t_range
            r = int(255 * (1 - t_norm))
            g = int(255 * (0.5 + 0.5 * math.sin(t_norm * math.pi)))
            b = int(255 * t_norm)
            if any(isinstance(s, pymunk.Circle) for s in body.shapes):
                circle = next(s for s in body.shapes if isinstance(s, pymunk.Circle))
                screen_pos = self.camera.world_to_screen(body.position)
                radius = int(circle.radius * self.camera.scaling)
                if radius < 1: continue
                pygame.gfxdraw.filled_circle(screen, int(screen_pos[0]), int(screen_pos[1]), radius, (r, g, b, 80))
                pygame.gfxdraw.aacircle(screen, int(screen_pos[0]), int(screen_pos[1]), radius, (r, g, b))
            elif any(isinstance(s, pymunk.Poly) for s in body.shapes):
                poly = next(s for s in body.shapes if isinstance(s, pymunk.Poly))
                world_verts = [body.local_to_world(v) for v in poly.get_vertices()]
                screen_verts = [self.camera.world_to_screen(v) for v in world_verts]
                if len(screen_verts) >= 3:
                    pygame.gfxdraw.filled_polygon(screen, screen_verts, (r, g, b, 80))
                    pygame.gfxdraw.aapolygon(screen, screen_verts, (r, g, b))

    def draw_hover_temperature(self):
        mouse_world = self.camera.get_cursor_world_position()
        query = self.physics_manager.space.point_query_nearest(mouse_world, 0, pymunk.ShapeFilter())
        if query and query.shape and query.shape.body:
            body = query.shape.body
            temp = getattr(body, 'temperature', self.ambient_temperature)
            screen_pos = pygame.mouse.get_pos()
            gizmos = get_gizmos()
            if gizmos:
                gizmos.draw_text(
                    position=(screen_pos[0] + 15, screen_pos[1] - 10),
                    text=f"{temp:.1f}°C",
                    font_name="Consolas",
                    font_size=16,
                    color=(255, 255, 255),
                    duration=0.1,
                    world_space=False
                )

    def shutdown(self):
        self.running = False
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        Debug.log_info("ThermalManager shutdown complete.", "Thermal")