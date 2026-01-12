from typing import Tuple, Optional
import pymunk
import pygame
from pymunk import Vec2d
from UPST.config import config
import pymunk.pygame_util
import time
from UPST.modules.fast_math import screen_to_world_impl, world_to_screen_impl, compose_transform_fast
from UPST.modules.profiler import profile


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
        self.inv_scaling = 1.0
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
        self._cx = screen_width * 0.5
        self._cy = screen_height * 0.5
        self._last_update_time = time.time()
        self.zoom_anchor_screen: Optional[Tuple[float, float]] = None
        self.zoom_anchor_world: Optional[Tuple[float, float]] = None

    def animate_to(self, target_tx, target_ty, duration=0.5):
        self.anim_start = time.time()
        self.anim_duration = duration
        self.anim_start_tx = Vec2d(self.translation.tx, self.translation.ty)
        self.anim_target_tx = Vec2d(target_tx, target_ty)
        self.anim_active = True

    def center_to_scene(self, duration=0.5):
        if not self.app or not hasattr(self.app, 'physics_manager'):
            return
        space = self.app.physics_manager.space
        if not space.bodies:
            self.center_to_origin(duration)
            return
        points = []
        for body in space.bodies:
            for shape in body.shapes:
                if isinstance(shape, pymunk.Circle):
                    p = body.local_to_world(shape.offset)
                    points.append(p)
                elif isinstance(shape, pymunk.Poly):
                    for v in shape.get_vertices():
                        points.append(body.local_to_world(v))
                elif isinstance(shape, pymunk.Segment):
                    a = body.local_to_world(shape.a)
                    b = body.local_to_world(shape.b)
                    points.append(a)
                    points.append(b)
        if not points:
            self.center_to_origin(duration)
            return
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        self.animate_to(-center_x, -center_y, duration)

    def center_to_origin(self, duration=0.5):
        self.animate_to(0.0, 0.0, duration)

    def ease_in_out_expo(self, t):
        if t == 0:
            return 0
        if t == 1:
            return 1
        if t < 0.5:
            return 0.5 * pow(2, 20 * t - 10)
        return 0.5 * (2 - pow(2, -20 * t + 10))

    @profile("camera_update")
    def update(self, keys):
        current_time = time.time()
        dt = current_time - self._last_update_time
        self._last_update_time = current_time
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
        acceleration = self.acceleration_factor * self.shift_speed * self.inv_scaling
        self.velocity += direction * acceleration
        self.velocity *= pow(self.friction, dt * 60)
        self.translation = self.translation.translated(self.velocity.x * dt * 60, self.velocity.y * dt * 60)
        if not self.panning and self.mouse_velocity.length > 0.01:
            self.translation = self.translation.translated(self.mouse_velocity.x * dt * 60, self.mouse_velocity.y * dt * 60)
            self.mouse_velocity *= pow(self.mouse_friction, dt * 60)
        old_scaling = self.scaling
        scale_dt = min(dt * 60, 1.0)
        self.scaling += (self.target_scaling - self.scaling) * (1.0 - pow(1.0 - self.smoothness, scale_dt))
        if self.scaling != old_scaling:
            self._update_scaling_cache()
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
        if self.zoom_anchor_screen is not None and self.zoom_anchor_world is not None:
            cx, cy = self.zoom_anchor_screen
            wx, wy = self.zoom_anchor_world
            new_tx = wx - (cx - self._cx) / self.scaling
            new_ty = wy + (cy - self._cy) / self.scaling
            self.translation = pymunk.Transform.translation(new_tx, new_ty)
            if abs(self.scaling - self.target_scaling) < 1e-6:
                self.zoom_anchor_screen = None
                self.zoom_anchor_world = None
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
        des_x = (wx - half_w)
        des_y = (wy - half_h)
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
        screen_y = self.screen_height / 2 - (world_y - self.translation.ty) * self.scaling
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
                self.zoom_anchor_screen = None
                self.zoom_anchor_world = None
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
                self.mouse_velocity = Vec2d(-dx, dy) * (self.pan_sensitivity / self.scaling)
                self.translation = self.translation.translated(self.mouse_velocity.x, self.mouse_velocity.y)
                self.last_mouse_pos = current_pos
        elif event.type == pygame.MOUSEWHEEL:
            zoom_factor = 1.0
            if event.y > 0:
                zoom_factor = 1 + self.zoom_speed
            elif event.y < 0:
                zoom_factor = 1 - self.zoom_speed
            self._zoom_at_cursor(zoom_factor)

    def _update_scaling_cache(self):
        self.inv_scaling = 1.0 / self.scaling if self.scaling != 0 else 0.0

    def _zoom_at_cursor(self, zoom_factor: float) -> None:
        new_target = self.target_scaling * zoom_factor
        new_target = max(config.camera.min_zoom_scale, min(config.camera.max_zoom_scale, new_target))
        cx, cy = pygame.mouse.get_pos()
        wx, wy = self.screen_to_world((cx, cy))
        self.zoom_anchor_screen = (cx, cy)
        self.zoom_anchor_world = (wx, wy)
        self.target_scaling = new_target

    def get_draw_options(self, screen):
        draw_options = pymunk.pygame_util.DrawOptions(screen)
        draw_options.shape_outline_color = (255, 255, 255)
        draw_options.DRAW_COLLISION_POINTS = False
        a, b, c, d, e, f = compose_transform_fast(
            self.translation.tx,
            self.translation.ty,
            self.scaling,
            self.rotation,
            self.screen_width,
            self.screen_height
        )
        draw_options.transform = pymunk.Transform(a, b, c, d, e, f)
        return draw_options

    @profile("screen_to_world")
    def screen_to_world(self, sp):
        return screen_to_world_impl(sp[0], sp[1], self.inv_scaling, self.translation.tx, self.translation.ty, self._cx,
                                    self._cy)

    @profile("world_to_screen")
    def world_to_screen(self, wp):
        return world_to_screen_impl(wp[0], wp[1], self.scaling, self.translation.tx, self.translation.ty, self._cx,
                                    self._cy)

    def is_mouse_on_ui(self):
        return self.app.ui_manager.manager.get_focus_set()

    def get_cursor_world_position(self):
        mouse_pos = pygame.mouse.get_pos()
        return self.screen_to_world(mouse_pos)

    def get_viewport_size(self) -> Tuple[float, float]:
        return (
            self.screen_width / self.scaling,
            self.screen_height / self.scaling
        )

    @property
    def position(self):
        return Vec2d(-self.translation.tx, -self.translation.ty)