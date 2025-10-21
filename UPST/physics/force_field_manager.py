import random
import pygame
import math


class ForceFieldManager:
    def __init__(self, physics_manager, camera):
        self.physics_manager = physics_manager
        self.camera = camera
        self.strength = 500
        self.radius = 500
        self.active_fields = {
            "attraction": False, "repulsion": False, "ring": False,
            "spiral": False, "freeze": False
        }
        self.shuffled_bodies = []

    def toggle_field(self, field_name):
        if field_name in self.active_fields:
            self.active_fields[field_name] = not self.active_fields[field_name]
            if field_name == "ring" and self.active_fields[field_name]:
                self.shuffled_bodies = random.sample(self.physics_manager.space.bodies,
                                                     len(self.physics_manager.space.bodies))
            return self.active_fields[field_name]
        return False

    def update(self, world_mouse_pos, screen):
        if not self.physics_manager.running_physics:
            return

        for field, is_active in self.active_fields.items():
            if is_active:
                method = getattr(self, f"apply_{field}", None)
                if method:
                    method(world_mouse_pos)
                pygame.draw.circle(screen, (255, 0, 0, 100), pygame.mouse.get_pos(), self.radius * self.camera.scaling,
                                   2)

    def apply_attraction(self, pos):
        for body in self.physics_manager.space.bodies:
            dist_sq = (pos[0] - body.position.x) ** 2 + (pos[1] - body.position.y) ** 2
            if dist_sq <= self.radius ** 2:
                force_vector = ((pos[0] - body.position.x) * 2, (pos[1] - body.position.y) * 2)
                body.velocity = force_vector

    def apply_repulsion(self, pos):
        for body in self.physics_manager.space.bodies:
            r = body.position - pos
            if r.length_squared <= self.radius ** 2 and r.length_squared > 0:
                force = r.normalized() * self.strength * 3000
                body.apply_force_at_local_point(force, (0, 0))

    def apply_ring(self, pos):
        num_bodies = len(self.shuffled_bodies)
        if num_bodies == 0: return
        angle_increment = 2 * math.pi / num_bodies
        for i, body in enumerate(self.shuffled_bodies):
            angle = i * angle_increment
            target_x = pos[0] + self.radius * math.cos(angle)
            target_y = pos[1] + self.radius * math.sin(angle)
            force_vector = ((target_x - body.position.x) * 2, (target_y - body.position.y) * 2)
            body.velocity = force_vector

    def apply_spiral(self, pos):
        num_bodies = len(self.physics_manager.space.bodies)
        if num_bodies == 0: return

        spiral_radius = 50
        spiral_spacing = self.radius / 100
        angle_increment = math.pi / 10
        angle = 0

        for body in self.physics_manager.space.bodies:
            target_x = pos[0] + spiral_radius * math.cos(angle)
            target_y = pos[1] + spiral_radius * math.sin(angle)
            force_vector = ((target_x - body.position.x) * 2, (target_y - body.position.y) * 2)
            body.velocity = force_vector
            spiral_radius += spiral_spacing
            angle += angle_increment

    def apply_freeze(self, pos):
        for body in self.physics_manager.space.bodies:
            dist_sq = (pos[0] - body.position.x) ** 2 + (pos[1] - body.position.y) ** 2
            if dist_sq <= self.radius ** 2:
                body.velocity = (0, 0)