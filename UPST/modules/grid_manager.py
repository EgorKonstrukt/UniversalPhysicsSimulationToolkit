import pygame
import pygame.gfxdraw
import math
import sys
import pymunk
from concurrent.futures import ThreadPoolExecutor
from functools import partial

IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import win32api
        import win32con
    except ImportError:
        IS_WINDOWS = False

IS_LINUX = sys.platform.startswith("linux")
if IS_LINUX:
    try:
        from Xlib import X, display
        from Xlib.ext import xtest

        _display = display.Display()
    except ImportError:
        IS_LINUX = False

from UPST.config import config
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.modules.profiler import profile


class GridManager:
    def __init__(self, camera, force_field_manager=None):
        self.camera = camera
        self.force_field_manager = force_field_manager
        self.enabled = True
        self.grid_color_major = (80, 80, 80, 255)
        self.grid_color_minor = (40, 40, 40, 255)
        self.grid_color_origin = (120, 120, 120, 255)
        self.base_grid_size = config.grid.base_size
        self.major_grid_multiplier = config.grid.major_multiplier
        self.min_pixel_spacing = config.grid.min_pixel_spacing
        self.max_pixel_spacing = config.grid.max_pixel_spacing
        self.minor_line_thickness = config.grid.minor_line_thickness
        self.major_line_thickness = config.grid.major_line_thickness
        self.origin_line_thickness = config.grid.origin_line_thickness
        self.snap_radius_pixels = config.grid.snap_radius_pixels
        self.snap_strength = config.grid.snap_strength
        self.ruler_font = pygame.font.SysFont("Consolas", 12)
        self._was_grabbed = False
        self._was_visible = False
        self._snapping_active = False
        self._executor = ThreadPoolExecutor(max_workers=config.multithreading.grid_max_workers)

    def toggle_grid(self):
        self.enabled = not self.enabled

    def set_grid_enabled(self, enabled):
        self.enabled = enabled

    def calculate_grid_spacing(self):
        camera_scale = self.camera.target_scaling
        base_pixels = self.base_grid_size * camera_scale
        multiplier = 1.0
        if base_pixels < self.min_pixel_spacing:
            while base_pixels * multiplier < self.min_pixel_spacing:
                multiplier *= 10
        elif base_pixels > self.max_pixel_spacing:
            while base_pixels / multiplier > self.max_pixel_spacing and multiplier < 100:
                multiplier *= 10
            multiplier = 1.0 / multiplier
        grid_spacing_world = self.base_grid_size * multiplier
        grid_spacing_pixels = grid_spacing_world * camera_scale
        return grid_spacing_world, grid_spacing_pixels

    def _handle_snapping(self, grid_spacing_world, grid_spacing_pixels):
        keys = pygame.key.get_pressed()
        active = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        mouse_focused = pygame.mouse.get_focused()
        if active and mouse_focused:
            if not self._snapping_active:
                self._was_grabbed = pygame.event.get_grab()
                self._was_visible = pygame.mouse.get_visible()
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
                self._snapping_active = True
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_pos = self.camera.screen_to_world((mouse_x, mouse_y))
            if grid_spacing_world <= 1e-5:
                return
            nearest_x = round(world_pos[0] / grid_spacing_world) * grid_spacing_world
            nearest_y = round(world_pos[1] / grid_spacing_world) * grid_spacing_world
            dx_world = nearest_x - world_pos[0]
            dy_world = nearest_y - world_pos[1]
            dx_pixels = dx_world * self.camera.target_scaling
            dy_pixels = dy_world * self.camera.target_scaling
            distance_pixels = math.hypot(dx_pixels, dy_pixels)
            if distance_pixels <= max(self.snap_radius_pixels, 0.5):
                if distance_pixels < 1e-4:
                    target_x, target_y = nearest_x, nearest_y
                else:
                    t = (self.snap_radius_pixels - distance_pixels) / self.snap_radius_pixels
                    t = max(0.0, min(1.0, t))
                    t = t * self.snap_strength + (1.0 - self.snap_strength)
                    target_x = world_pos[0] + dx_world * t
                    target_y = world_pos[1] + dy_world * t
                target_screen = self.camera.world_to_screen((target_x, target_y))
                target_x_int = int(round(target_screen[0]))
                target_y_int = int(round(target_screen[1]))
                if (target_x_int, target_y_int) != (mouse_x, mouse_y):
                    pygame.mouse.set_pos(target_x_int, target_y_int)
        else:
            if self._snapping_active:
                pygame.event.set_grab(self._was_grabbed)
                pygame.mouse.set_visible(self._was_visible)
                self._snapping_active = False

    @profile("grid", "app")
    def draw(self, screen):
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        self._handle_snapping(grid_spacing_world, grid_spacing_pixels)
        if not self.enabled or grid_spacing_pixels < 5:
            return
        top_left_world = self.camera.screen_to_world((0, 0))
        bottom_right_world = self.camera.screen_to_world((screen.get_width(), screen.get_height()))
        min_x = math.floor(top_left_world[0] / grid_spacing_world) * grid_spacing_world
        max_x = math.ceil(bottom_right_world[0] / grid_spacing_world) * grid_spacing_world
        min_y = math.floor(top_left_world[1] / grid_spacing_world) * grid_spacing_world
        max_y = math.ceil(bottom_right_world[1] / grid_spacing_world) * grid_spacing_world

        tasks = []
        x = min_x
        while x <= max_x:
            tasks.append(
                partial(self._compute_line_params, x, True, top_left_world, bottom_right_world, grid_spacing_world))
            x += grid_spacing_world
        y = min_y
        while y <= max_y:
            tasks.append(
                partial(self._compute_line_params, y, False, top_left_world, bottom_right_world, grid_spacing_world))
            y += grid_spacing_world

        futures = [self._executor.submit(task) for task in tasks]
        for future in futures:
            start, end, color, thickness, world_space = future.result()
            Gizmos.draw_line(start=start, end=end, color=color, thickness=thickness, duration=0.05,
                             world_space=world_space, layer=-1)

        if self.force_field_manager and self.force_field_manager.physics_manager.running_physics:
            self._draw_gravity_vectors(screen, grid_spacing_world, grid_spacing_pixels)

        self.draw_scale_indicator(screen, grid_spacing_world, grid_spacing_pixels)
        self.draw_rulers()

    def _compute_line_params(self, coord, is_vertical, top_left_world, bottom_right_world, grid_spacing_world):
        if abs(coord) < 0.001:
            color = self.grid_color_origin
            thickness = self.origin_line_thickness
        elif abs(coord / grid_spacing_world) % self.major_grid_multiplier < 0.001:
            color = self.grid_color_major
            thickness = self.major_line_thickness
        else:
            color = self.grid_color_minor
            thickness = self.minor_line_thickness
        if is_vertical:
            start = (coord, top_left_world[1])
            end = (coord, bottom_right_world[1])
        else:
            start = (top_left_world[0], coord)
            end = (bottom_right_world[0], coord)
        return (start, end, color, thickness, True)

    def _draw_gravity_vectors(self, screen, grid_spacing_world, grid_spacing_pixels):
        if not self.force_field_manager or not any(
                self.force_field_manager.active_fields.get(f, False)
                for f in ("attraction", "repulsion", "vortex", "wind")
        ):
            return
        if grid_spacing_pixels < 10:
            return
        px, py = pygame.mouse.get_pos()
        world_mouse = self.camera.screen_to_world((px, py))
        top_left = self.camera.screen_to_world((0, 0))
        bottom_right = self.camera.screen_to_world((screen.get_width(), screen.get_height()))
        spacing = grid_spacing_world
        max_screen_length = 20.0
        x = math.floor(top_left[0] / spacing) * spacing
        while x <= bottom_right[0]:
            y = math.floor(top_left[1] / spacing) * spacing
            while y <= bottom_right[1]:
                fx = fy = 0.0
                dx = world_mouse[0] - x
                dy = world_mouse[1] - y
                dist = math.hypot(dx, dy)
                if dist <= self.force_field_manager.radius:
                    t = 1.0 - dist / self.force_field_manager.radius
                    if self.force_field_manager.active_fields.get("attraction"):
                        fx += dx * t
                        fy += dy * t
                    if self.force_field_manager.active_fields.get("repulsion"):
                        fx -= dx * t
                        fy -= dy * t
                    if self.force_field_manager.active_fields.get("vortex"):
                        fx += -dy * t
                        fy += dx * t
                if self.force_field_manager.active_fields.get("wind"):
                    fx += 1.0
                if abs(fx) < 1e-4 and abs(fy) < 1e-4:
                    y += spacing
                    continue
                start_world = (x, y)
                end_world = (x + fx, y + fy)
                start_screen = self.camera.world_to_screen(start_world)
                raw_end_screen = self.camera.world_to_screen(end_world)
                dx_s = raw_end_screen[0] - start_screen[0]
                dy_s = raw_end_screen[1] - start_screen[1]
                len_s = math.hypot(dx_s, dy_s)
                if len_s > max_screen_length and len_s > 1e-6:
                    ratio = max_screen_length / len_s
                    dx_s *= ratio
                    dy_s *= ratio
                final_end_screen = (start_screen[0] + dx_s, start_screen[1] + dy_s)
                Gizmos.draw_line(
                    start=start_screen,
                    end=final_end_screen,
                    color=(255, 100, 100),
                    thickness=1,
                    duration=0.05,
                    world_space=False,
                    layer = -1
                )
                y += spacing
            x += spacing

    def draw_rulers(self):
        screen_width, screen_height = pygame.display.get_surface().get_size()
        margin = 5
        tick_length = 6
        text_offset = 3
        min_label_spacing = 40
        top_left_world = self.camera.screen_to_world((0, 0))
        bottom_right_world = self.camera.screen_to_world((screen_width, screen_height))
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        if grid_spacing_pixels < 10:
            return
        min_x = math.floor(top_left_world[0] / grid_spacing_world) * grid_spacing_world
        max_x = math.ceil(bottom_right_world[0] / grid_spacing_world) * grid_spacing_world
        min_y = math.floor(top_left_world[1] / grid_spacing_world) * grid_spacing_world
        max_y = math.ceil(bottom_right_world[1] / grid_spacing_world) * grid_spacing_world
        skip = max(1, getattr(config.grid, 'ruler_skip_factor', 1))

        def format_number(val):
            abs_val = abs(val)
            if abs_val >= 1e6:
                return f"{val / 1e6:.1f}e6"
            else:
                return f"{val:.0f}"

        last_label_x = -min_label_spacing
        x = min_x
        while x <= max_x:
            tick_index = round(x / grid_spacing_world)
            if tick_index % skip == 0:
                screen_x = self.camera.world_to_screen((x, 0))[0]
                if 0 <= screen_x <= screen_width and screen_x - last_label_x >= min_label_spacing:
                    Gizmos.draw_line(start=(screen_x, 0), end=(screen_x, tick_length), color=(200, 200, 200),
                                     thickness=1, duration=0.05, world_space=False, layer=-1)
                    label = format_number(x)
                    Gizmos.draw_text(position=(screen_x, tick_length + text_offset), text=label, color=(200, 200, 200),
                                     font_size=12, font_name="Consolas", world_space=False, font_world_space=False,
                                     duration=0.05, layer=-1)
                    last_label_x = screen_x
            x += grid_spacing_world

        last_label_y = -min_label_spacing
        y = min_y
        while y <= max_y:
            tick_index = round(y / grid_spacing_world)
            if tick_index % skip == 0:
                screen_y = self.camera.world_to_screen((0, y))[1]
                if 0 <= screen_y <= screen_height and screen_y - last_label_y >= min_label_spacing:
                    Gizmos.draw_line(start=(0, screen_y), end=(tick_length, screen_y), color=(200, 200, 200),
                                     thickness=1, duration=0.05, world_space=False, layer=-1)
                    label = format_number(y)
                    Gizmos.draw_text(position=(tick_length + text_offset, screen_y), text=label, color=(200, 200, 200),
                                     font_size=12, font_name="Consolas", world_space=False, font_world_space=False,
                                     duration=0.05, layer=-1)
                    last_label_y = screen_y
            y += grid_spacing_world

        mouse_pos = pygame.mouse.get_pos()
        world_mouse = self.camera.screen_to_world(mouse_pos)
        cursor_x_screen, cursor_y_screen = mouse_pos
        if 0 <= cursor_x_screen <= screen_width:
            Gizmos.draw_line(start=(cursor_x_screen, 0), end=(cursor_x_screen, tick_length * 2), color=(255, 255, 0),
                             thickness=2, duration=0.05, world_space=False, layer=-1)
            cursor_x_label = format_number(world_mouse[0])
            Gizmos.draw_text(position=(cursor_x_screen, tick_length * 2 + text_offset), text=cursor_x_label,
                             color=(255, 255, 0), font_size=12, font_name="Consolas", world_space=False,
                             font_world_space=False, duration=0.05, layer=-1)
        if 0 <= cursor_y_screen <= screen_height:
            Gizmos.draw_line(start=(0, cursor_y_screen), end=(tick_length * 2, cursor_y_screen), color=(255, 255, 0),
                             thickness=2, duration=0.05, world_space=False, layer=-1)
            cursor_y_label = format_number(world_mouse[1])
            Gizmos.draw_text(position=(tick_length * 2 + text_offset, cursor_y_screen), text=cursor_y_label,
                             color=(255, 255, 0), font_size=12, font_name="Consolas", world_space=False,
                             font_world_space=False, duration=0.05, layer=-1)

    def get_grid_info(self):
        if not self.enabled:
            return "Grid: Disabled"
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        if grid_spacing_world >= 100:
            spacing_str = f"{grid_spacing_world / 100:.2f}m"
        elif grid_spacing_world >= 1:
            spacing_str = f"{grid_spacing_world:.1f}cm"
        else:
            spacing_str = f"{grid_spacing_world * 10:.1f}mm"
        return f"Grid: {spacing_str} ({grid_spacing_pixels:.1f}px)"

    def set_colors(self, major_color=None, minor_color=None, origin_color=None):
        if major_color:
            self.grid_color_major = major_color
        if minor_color:
            self.grid_color_minor = minor_color
        if origin_color:
            self.grid_color_origin = origin_color

    def set_theme_colors(self, theme_name):
        if theme_name in config.world.themes:
            theme = config.world.themes[theme_name]
            bg_color = theme.background_color
            if sum(bg_color[:3]) > 382:
                self.grid_color_minor = (60, 60, 60, 255)
                self.grid_color_major = (100, 100, 100, 255)
                self.grid_color_origin = (140, 140, 140, 255)
            else:
                self.grid_color_minor = (40, 40, 40, 255)
                self.grid_color_major = (80, 80, 80, 255)
                self.grid_color_origin = (120, 120, 120, 255)

    def draw_scale_indicator(self, screen, grid_spacing_world, grid_spacing_pixels):
        if grid_spacing_world >= 100:
            label = f"{grid_spacing_world / 100:.2f} m"
        elif grid_spacing_world >= 1:
            label = f"{grid_spacing_world:.0f} cm"
        else:
            label = f"{grid_spacing_world * 10:.0f} mm"
        screen_width, screen_height = screen.get_size()
        margin = 30
        bar_length_pixels = int(grid_spacing_pixels)
        start_x = screen_width - margin - bar_length_pixels
        end_x = screen_width - margin
        y_pos = screen_height - margin
        Gizmos.draw_line(start=(start_x, y_pos), end=(end_x, y_pos), color="white", thickness=3, duration=0.01,
                         world_space=False, layer=-1)
        tick_height = 6
        for x in (start_x, end_x):
            Gizmos.draw_line(start=(x, y_pos - tick_height // 2), end=(x, y_pos + tick_height // 2), color="white",
                             thickness=3, duration=0.05, world_space=False, layer=-1)
        Gizmos.draw_text(position=((start_x + bar_length_pixels / 2), y_pos - 14), text=label, color="white",
                         font_size=16, duration=0.05, font_name="Consolas", world_space=False,
                         font_world_space=False, layer=-1)
