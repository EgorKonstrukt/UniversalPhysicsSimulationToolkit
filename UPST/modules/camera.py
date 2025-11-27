import pymunk
import pygame
from pymunk import Vec2d
from UPST.config import config
import pymunk.pygame_util
import time


class Camera:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_game, screen_width, screen_height, screen):
        if hasattr(self, 'screen'):
            return
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
        self.rotate_with_target = False
        self.tracking_smoothness = 0.05
        self.tracking_offset = Vec2d(0, 0)
        self.tracking_deadzone = 5.0
        self.last_middle_click = 0
        self.double_click_thresh = 0.3
        self.anim_active = False
        self.anim_start = 0
        self.anim_duration = 0.25
        self.anim_start_tx = Vec2d(0, 0)
        self.anim_target_tx = Vec2d(0, 0)
        self.track_vel = Vec2d(0, 0)
        self.track_smooth = 0.25

    def ease_in_out_expo(self, t):
        if t == 0:
            return 0
        if t == 1:
            return 1
        if t < 0.5:
            return 0.5 * pow(2, 20 * t - 10)
        return 0.5 * (2 - pow(2, -20 * t + 10))

    def update(self, keys):
        if self.tracking_enabled and self.tracking_target is not None:
            self._update_tracking()
        if self.is_mouse_on_ui():
            return
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
        if self.anim_active:
            elapsed = time.time() - self.anim_start
            if elapsed >= self.anim_duration:
                self.translation = pymunk.Transform.translation(
                    self.anim_target_tx.x,
                    self.anim_target_tx.y,
                )
                self.anim_active = False
            else:
                t = elapsed / self.anim_duration
                eased = self.ease_in_out_expo(t)
                new_tx = self.anim_start_tx.x + (self.anim_target_tx.x - self.anim_start_tx.x) * eased
                new_ty = self.anim_start_tx.y + (self.anim_target_tx.y - self.anim_start_tx.y) * eased
                self.translation = pymunk.Transform.translation(new_tx, new_ty)
        if self.tracking_enabled and self.tracking_target and self.rotate_with_target:
            if hasattr(self.tracking_target, "angle"):
                self.rotation = -float(self.tracking_target.angle)

    def _update_tracking(self):
        tgt = self.tracking_target
        if not tgt: return
        if hasattr(tgt, 'position'):
            wx, wy = tgt.position
        else:
            wx, wy = tgt
        half_w = self.screen_width * 0.5
        half_h = self.screen_height * 0.5
        cam_x = self.translation.tx
        cam_y = self.translation.ty
        des_x = -(wx - half_w)
        des_y = -(wy - half_h)
        dt = 1 / 60
        st = self.track_smooth
        om = 2 / st
        x = om * dt
        e = 1 / (1 + x + 0.48 * x * x + 0.235 * x * x * x)
        dx = cam_x - des_x
        dy = cam_y - des_y
        tvx = self.track_vel.x + om * dx
        tvy = self.track_vel.y + om * dy
        tvx *= dt
        tvy *= dt
        new_vx = (self.track_vel.x - om * tvx) * e
        new_vy = (self.track_vel.y - om * tvy) * e
        self.track_vel = Vec2d(new_vx, new_vy)
        nx = des_x + (dx + tvx) * e
        ny = des_y + (dy + tvy) * e
        self.translation = pymunk.Transform.translation(nx, ny)

    def world_to_screen_simple(self, world_x, world_y):
        screen_x = (world_x - self.translation.tx) * self.scaling + self.screen_width / 2
        screen_y = (world_y - self.translation.ty) * self.scaling + self.screen_height / 2
        return screen_x, screen_y

    def set_tracking_target(self, target_pos):
        self.tracking_target = target_pos
        self.tracking_enabled = True

    def enable_tracking(self, enabled=True):
        self.tracking_enabled = enabled

    def set_tracking_smoothness(self, smoothness):
        self.tracking_smoothness = max(0.001, min(1.0, smoothness))

    def set_tracking_offset(self, offset_x, offset_y):
        self.tracking_offset = Vec2d(offset_x, offset_y)

    def set_tracking_deadzone(self, deadzone):
        self.tracking_deadzone = max(0, deadzone)

    def handle_mouse_event(self, event):
        if self.is_mouse_on_ui():
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:
                current_time = time.time()
                if current_time - self.last_middle_click < self.double_click_thresh:
                    self.last_middle_click = 0
                    self.panning = False
                    self.last_mouse_pos = None
                    self.tracking_enabled = False
                    self.velocity = Vec2d(0, 0)
                    self.mouse_velocity = Vec2d(0, 0)
                    cursor_x, cursor_y = pygame.mouse.get_pos()
                    world_x = (cursor_x - self.screen_width / 2) / self.scaling + self.translation.tx
                    world_y = (cursor_y - self.screen_height / 2) / self.scaling + self.translation.ty
                    self.anim_start = current_time
                    self.anim_active = True
                    self.anim_start_tx = Vec2d(self.translation.tx, self.translation.ty)
                    cx, cy = self.translation.tx, self.translation.ty
                    self.anim_target_tx = Vec2d(2 * cx - world_x, 2 * cy - world_y)

                else:
                    self.panning = True
                    self.last_mouse_pos = pygame.mouse.get_pos()
                    self.tracking_enabled = False
                    self.last_middle_click = current_time

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
                self.translation = self.translation.translated(self.mouse_velocity.x, self.mouse_velocity.y)
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
        draw_options.shape_outline_color = (255, 255, 255)
        draw_options.DRAW_COLLISION_POINTS = False
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
        return -(world_x * self.target_scaling) + self.screen_width // 2 - (self.offset_x * self.target_scaling)

    def world_to_screen_y(self, world_y):
        return self.screen_height // 2 - (world_y * self.target_scaling) - (self.offset_y * self.target_scaling)

    def screen_to_world_x(self, screen_x):
        return ((screen_x - self.screen_width // 2) / self.target_scaling) + self.offset_x

    def screen_to_world_y(self, screen_y):
        return ((self.screen_height // 2 - screen_y) / self.target_scaling) + self.offset_y

    def get_cursor_world_position(self):
        mouse_pos = pygame.mouse.get_pos()
        return self.screen_to_world(mouse_pos)

    @property
    def position(self):
        return Vec2d(-self.translation.tx, -self.translation.ty)
