import pymunk
import pygame
from pymunk import Vec2d
from UPST.config import config
import pymunk.pygame_util


class Camera:
    """
    Manages camera transformations like zoom, pan, and rotation.
    """

    def __init__(self, app_game, screen_width, screen_height, screen):

        self.screen = screen

        self.app = app_game
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.translation = pymunk.Transform()
        self.rotation = 0.0
        self.scaling = 1.0
        self.inverse_scaling = 1.0
        self.target_scaling = 1.0
        self.smoothness = config.camera.smoothness
        self.shift_speed = config.camera.shift_speed

        self.mouse_velocity = Vec2d(0, 0)
        self.mouse_friction = config.camera.mouse_friction

        self.velocity = Vec2d(0, 0)
        self.friction = config.camera.friction
        self.acceleration_factor = config.camera.acceleration_factor
        self.zoom_speed = config.camera.zoom_speed

        self.offset_x = 0.0
        self.offset_y = 0.0

        self.panning = False
        self.last_mouse_pos = None
        self.pan_sensitivity = 1.0

        self.tracking_enabled = False
        self.tracking_target = None
        self.tracking_smoothness = 0.05
        self.tracking_offset = Vec2d(0, 0)
        self.tracking_deadzone = 5.0
    def update(self, keys):
        if self.is_mouse_on_ui():
            return
        if self.tracking_enabled and self.tracking_target is not None:
            self._update_tracking()

        # zoom_in = keys[pygame.K_a]
        # zoom_out = keys[pygame.K_z]
        # if zoom_in or zoom_out:
        #     zoom_factor = 1.0
        #     if zoom_in:
        #         zoom_factor *= 1.1
        #     if zoom_out:
        #         zoom_factor *= 0.9
        #     self._zoom_at_cursor(zoom_factor)

        # rotate_left = int(keys[pygame.K_s])
        # rotate_right = int(keys[pygame.K_x])
        # self.rotation += 0.01 * rotate_left - 0.01 * rotate_right
        left = int(keys[pygame.K_LEFT])
        right = int(keys[pygame.K_RIGHT])
        up = int(keys[pygame.K_UP])
        down = int(keys[pygame.K_DOWN])
        direction = Vec2d(left - right, up - down)
        if direction.length > 0:
            direction = direction.normalized()
        if self.tracking_enabled and direction.length > 0:
            self.tracking_enabled = False
        acceleration = self.acceleration_factor * self.shift_speed / self.scaling
        self.velocity += direction * acceleration
        self.velocity *= self.friction
        self.translation = self.translation.translated(self.velocity.x, self.velocity.y)
        if not self.panning and self.mouse_velocity.length > 0.01:
            self.translation = self.translation.translated(self.mouse_velocity.x, self.mouse_velocity.y)
            self.mouse_velocity *= self.mouse_friction
        self.scaling += (self.target_scaling - self.scaling) * self.smoothness

    def _update_tracking(self):
        """Обновляет позицию камеры для слежения за целью"""
        if not self.tracking_target:
            return
        target_x, target_y = self.tracking_target
        desired_screen_x = self.screen_width / 2 + self.tracking_offset.x
        desired_screen_y = self.screen_height / 2 + self.tracking_offset.y
        current_screen_pos = self.world_to_screen_simple(target_x, target_y)
        dx = desired_screen_x - current_screen_pos[0]
        dy = desired_screen_y - current_screen_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5
        if distance < self.tracking_deadzone:
            return
        move_x = dx * self.tracking_smoothness / self.scaling
        move_y = dy * self.tracking_smoothness / self.scaling
        self.translation = self.translation.translated(move_x, move_y)

    def world_to_screen_simple(self, world_x, world_y):
        """Простое преобразование мировых координат в экранные для слежения"""
        screen_x = (world_x - self.translation.tx) * self.scaling + self.screen_width / 2
        screen_y = (world_y - self.translation.ty) * self.scaling + self.screen_height / 2
        return (screen_x, screen_y)

    def set_tracking_target(self, target_pos):
        """Устанавливает цель для слежения"""
        self.tracking_target = target_pos
        self.tracking_enabled = True

    def enable_tracking(self, enabled=True):
        """Включает/выключает слежение"""
        self.tracking_enabled = enabled

    def set_tracking_smoothness(self, smoothness):
        """Устанавливает скорость сглаживания слежения (0.01 - медленно, 0.1 - быстро)"""
        self.tracking_smoothness = max(0.001, min(1.0, smoothness))

    def set_tracking_offset(self, offset_x, offset_y):
        """Устанавливает смещение относительно цели"""
        self.tracking_offset = Vec2d(offset_x, offset_y)

    def set_tracking_deadzone(self, deadzone):
        """Устанавливает размер мертвой зоны в пикселях"""
        self.tracking_deadzone = max(0, deadzone)

    def handle_mouse_event(self, event):
        """Обрабатывает события мыши для панорамирования и зума"""
        if self.is_mouse_on_ui():
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:
                self.panning = True
                self.last_mouse_pos = pygame.mouse.get_pos()
                self.tracking_enabled = False
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                self.panning = False
                self.last_mouse_pos = None
        elif event.type == pygame.MOUSEMOTION:
            if self.panning and self.last_mouse_pos:
                current_pos = pygame.mouse.get_pos()
                dx = current_pos[0] - self.last_mouse_pos[0]
                dy = current_pos[1] - self.last_mouse_pos[1]
                self.mouse_velocity = Vec2d(dx, dy) * (self.pan_sensitivity / self.scaling)
                self.translation = self.translation.translated(
                    self.mouse_velocity.x,
                    self.mouse_velocity.y
                )
                self.last_mouse_pos = current_pos
        elif event.type == pygame.MOUSEWHEEL:
            zoom_factor = 1.0
            if event.y > 0:
                zoom_factor = 1 + self.zoom_speed
            elif event.y < 0:
                zoom_factor = 1 - self.zoom_speed
            self._zoom_at_cursor(zoom_factor)

    def _zoom_at_cursor(self, zoom_factor: float) -> None:
        min_scale, max_scale = 0.000001, 1_00
        new_target = self.target_scaling * zoom_factor
        self.target_scaling = max(min_scale, min(max_scale, new_target))
        cursor_pos = pygame.mouse.get_pos()
        before = Vec2d(*self.screen_to_world(cursor_pos))
        old_scaling = self.scaling
        self.scaling = self.target_scaling
        after = Vec2d(*self.screen_to_world(cursor_pos))
        self.scaling = old_scaling
        delta = after - before
        self.translation = self.translation.translated(delta.x, delta.y)

    def get_draw_options(self, screen):
        draw_options = pymunk.pygame_util.DrawOptions(screen)
        draw_options.transform = (
                pymunk.Transform.translation(self.screen_width / 2, self.screen_height / 2)
                @ pymunk.Transform.scaling(self.scaling)
                @ self.translation
                @ pymunk.Transform.rotation(self.rotation)
                @ pymunk.Transform.translation(-self.screen_width / 2, -self.screen_height / 2)
        )
        return draw_options

    def screen_to_world(self, screen_pos):
        cursor_pos = Vec2d(screen_pos[0], screen_pos[1])
        inverse_translation = pymunk.Transform.translation(-self.screen_width / 2, -self.screen_height / 2)
        inverse_rotation = pymunk.Transform.rotation(-self.rotation)
        self.inverse_scaling = pymunk.Transform.scaling(1 / self.scaling)
        inverse_transform = self.inverse_scaling @ inverse_rotation @ inverse_translation
        inverse_translation_cam = pymunk.Transform.translation(-self.translation.tx, -self.translation.ty)
        world_cursor_pos = inverse_transform @ cursor_pos
        world_translation = inverse_translation_cam @ Vec2d(0, 0)

        return (
            world_cursor_pos.x + world_translation.x + self.screen_width / 2,
            world_cursor_pos.y + world_translation.y + self.screen_height / 2,
        )

    def world_to_screen(self, world_pos):
        draw_options = pymunk.pygame_util.DrawOptions(self.screen)
        draw_options.transform = (
                pymunk.Transform.translation(self.screen_width / 2, self.screen_height / 2)
                @ pymunk.Transform.scaling(self.scaling)
                @ self.translation
                @ pymunk.Transform.rotation(self.rotation)
                @ pymunk.Transform.translation(-self.screen_width / 2, -self.screen_height / 2)
        )
        return draw_options.transform @ world_pos

    def is_mouse_on_ui(self):
        return self.app.ui_manager.manager.get_focus_set()

    def world_to_screen_x(self, world_x):
        """Преобразует мировую координату X в экранную координату X"""
        return -(world_x * self.target_scaling) + self.screen_width // 2 - (self.offset_x * self.target_scaling)

    def world_to_screen_y(self, world_y):
        """Преобразует мировую координату Y в экранную координату Y"""
        return self.screen_height // 2 - (world_y * self.target_scaling) - (self.offset_y * self.target_scaling)

    def screen_to_world_x(self, screen_x):
        """Преобразует экранную координату X в мировую координату X"""
        return ((screen_x - self.screen_width // 2) / self.target_scaling) + self.offset_x

    def screen_to_world_y(self, screen_y):
        """Преобразует экранную координату Y в мировую координату Y"""
        return ((self.screen_height // 2 - screen_y) / self.target_scaling) + self.offset_y

    @property
    def position(self):
        return (-self.translation.tx, -self.translation.ty)