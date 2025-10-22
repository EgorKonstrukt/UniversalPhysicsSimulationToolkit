import math
import random
import pymunk
import pygame

from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos


class ForceFieldManager:
    def __init__(self, physics_manager, camera):
        self.physics_manager = physics_manager
        self.camera = camera
        self.radius = 250.0
        self.strength = 1.0
        self.falloff_mode = "inv2"
        self.active_fields = {
            "attraction": False,
            "repulsion": False,
            "ring": False,
            "spiral": False,
            "freeze": False,
            "wind": False,
            "vortex": False,
            "noise": False
        }
        self.shuffled_bodies = []
        Debug.log_info("ForceFieldManager initialized.", "ForceField")

    def set_radius(self, r: float):
        self.radius = max(1.0, float(r))

    def set_strength(self, s: float):
        self.strength = float(s)

    def set_falloff_mode(self, mode: str):
        if mode in ("linear", "inv", "inv2"):
            self.falloff_mode = mode

    def toggle_field(self, name: str, state=None):
        if name not in self.active_fields:
            return
        if state is None:
            self.active_fields[name] = not self.active_fields[name]
        else:
            self.active_fields[name] = bool(state)
        Debug.log_info(f"Field '{name}' set to {self.active_fields[name]}.", "ForceField")

    def update(self, world_mouse_pos, screen):
        if not self.physics_manager.running_physics:
            return
        for field, is_active in self.active_fields.items():
            if not is_active:
                continue
            fn = getattr(self, f"apply_{field}", None)
            if fn:
                fn(world_mouse_pos)
        if screen is not None:
            pygame.draw.circle(
                screen,
                (255, 0, 0),
                pygame.mouse.get_pos(),
                int(self.radius * self.camera.scaling),
                2
            )

    def _falloff(self, dist: float) -> float:
        if dist <= 1e-5:
            return 1.0
        r = max(1e-5, float(self.radius))
        x = min(1.0, dist / r)
        if self.falloff_mode == "linear":
            return 1.0 - x
        if self.falloff_mode == "inv":
            return 1.0 / (1.0 + 9.0 * x)
        return 1.0 / (1.0 + 9.0 * (x * x))

    def apply_attraction(self, pos):
        px, py = pos
        for body in self.physics_manager.space.bodies:
            if body.body_type != pymunk.Body.DYNAMIC:
                continue
            dx = px - body.position.x
            dy = py - body.position.y
            dist = math.hypot(dx, dy)
            if dist > self.radius:
                continue
            k = self._falloff(dist)
            fx = (dx / (dist + 1e-6)) * self.strength * k
            fy = (dy / (dist + 1e-6)) * self.strength * k
            body.apply_force_at_world_point((fx, fy), body.position)

    def apply_repulsion(self, pos):
        px, py = pos
        for body in self.physics_manager.space.bodies:
            if body.body_type != pymunk.Body.DYNAMIC:
                continue
            dx = body.position.x - px
            dy = body.position.y - py
            dist = math.hypot(dx, dy)
            if 0 < dist <= self.radius:
                k = self._falloff(dist)
                fx = (dx / (dist + 1e-6)) * self.strength * 3000 * k
                fy = (dy / (dist + 1e-6)) * self.strength * 3000 * k
                body.apply_force_at_world_point((fx, fy), body.position)

    def apply_ring(self, pos):
        px, py = pos
        bodies = [b for b in self.physics_manager.space.bodies if b.body_type == pymunk.Body.DYNAMIC]
        if not bodies:
            return
        if not self.shuffled_bodies or len(self.shuffled_bodies) != len(bodies):
            self.shuffled_bodies = bodies[:]
            random.shuffle(self.shuffled_bodies)
        n = len(self.shuffled_bodies)
        angle_inc = 2 * math.pi / max(1, n)
        for i, body in enumerate(self.shuffled_bodies):
            ang = i * angle_inc
            tx = px + self.radius * math.cos(ang)
            ty = py + self.radius * math.sin(ang)
            dx = tx - body.position.x
            dy = ty - body.position.y
            dist = math.hypot(dx, dy)
            k = self._falloff(dist)
            body.apply_impulse_at_world_point((dx * 0.5 * k, dy * 0.5 * k), body.position)

    def apply_spiral(self, pos):
        px, py = pos
        bodies = [b for b in self.physics_manager.space.bodies if b.body_type == pymunk.Body.DYNAMIC]
        if not bodies:
            return
        spiral_radius = 50.0
        spiral_spacing = max(1.0, self.radius / 100.0)
        angle_increment = math.pi / 10.0
        angle = 0.0
        for body in bodies:
            tx = px + spiral_radius * math.cos(angle)
            ty = py + spiral_radius * math.sin(angle)
            dx = tx - body.position.x
            dy = ty - body.position.y
            dist = math.hypot(dx, dy)
            k = self._falloff(dist)
            body.apply_impulse_at_world_point((dx * 0.4 * k, dy * 0.4 * k), body.position)
            spiral_radius += spiral_spacing
            angle += angle_increment

    def apply_freeze(self, pos):
        px, py = pos
        for body in self.physics_manager.space.bodies:
            if body.body_type != pymunk.Body.DYNAMIC:
                continue
            dist = pymunk.Vec2d(body.position.x - px, body.position.y - py).length
            if dist <= self.radius:
                body.velocity = (0, 0)
                body.angular_velocity = 0

    def apply_wind(self, pos):
        wind = (self.strength * 0.2, 0.0)
        for body in self.physics_manager.space.bodies:
            if body.body_type == pymunk.Body.DYNAMIC:
                body.apply_force_at_world_point(wind, body.position)

    def apply_vortex(self, pos):
        px, py = pos
        circulation = self.strength
        for body in self.physics_manager.space.bodies:
            if body.body_type != pymunk.Body.DYNAMIC:
                continue
            r = pymunk.Vec2d(body.position.x - px, body.position.y - py)
            dist = r.length
            if 0 < dist <= self.radius:
                t = r.perpendicular_normal()
                k = self._falloff(dist)
                f = t * (circulation * k / max(1.0, dist))
                body.apply_force_at_world_point(f, body.position)

    def apply_noise(self, pos):
        for body in self.physics_manager.space.bodies:
            if body.body_type != pymunk.Body.DYNAMIC:
                continue
            nx = (random.random() - 0.5) * self.strength
            ny = (random.random() - 0.5) * self.strength
            body.apply_force_at_world_point((nx, ny), body.position)

