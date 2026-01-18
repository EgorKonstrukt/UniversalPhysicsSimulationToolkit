import pygame
import pygame.gfxdraw
import math
import sys
import pymunk

IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import win32api, win32con
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

class GridManager:
    def __init__(self, camera, force_field_manager=None):
        self.camera = camera
        self.force_field_manager = force_field_manager
        self.enabled = config.grid.enabled_by_default
        self.polar_enabled = config.grid.polar.enabled_by_default
        self.base_grid_size = config.grid.base_size
        self.major_grid_multiplier = config.grid.major_multiplier
        self.min_pixel_spacing = config.grid.min_pixel_spacing
        self.max_pixel_spacing = config.grid.max_pixel_spacing
        self.minor_line_thickness = config.grid.minor_line_thickness
        self.major_line_thickness = config.grid.major_line_thickness
        self.origin_line_thickness = config.grid.origin_line_thickness
        self.snap_radius_pixels = config.grid.snap_radius_pixels
        self.snap_strength = config.grid.snap_strength
        self.alpha_fade_enabled = config.grid.alpha_fade_enabled
        self.min_alpha = config.grid.min_alpha
        self.max_alpha = config.grid.max_alpha
        self.ruler_skip_factor = config.grid.ruler_skip_factor
        self.coordinate_display_mode = "screen"
        self._was_grabbed = False
        self._was_visible = False
        self._snapping_active = False
        self.ruler_font = pygame.font.SysFont("Consolas", config.grid.label_font_size if hasattr(config.grid, 'label_font_size') else 12)
        self._apply_grid_colors()
        self._apply_polar_colors()
        self._polar_cache = None
        self._polar_cache_scale = 0.0
        self._polar_cache_pos = (0, 0)

    def toggle_coordinate_display_mode(self):
        self.coordinate_display_mode = "world" if self.coordinate_display_mode == "screen" else "screen"

    def toggle_polar_grid(self):
        self.polar_enabled = not self.polar_enabled

    def draw(self, screen):
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        self._handle_snapping(grid_spacing_world, grid_spacing_pixels)
        if not self.enabled or grid_spacing_pixels < 5: return
        top_left_world = self.camera.screen_to_world((0, 0))
        bottom_right_world = self.camera.screen_to_world((screen.get_width(), screen.get_height()))
        min_x = min(top_left_world[0], bottom_right_world[0])
        max_x = max(top_left_world[0], bottom_right_world[0])
        min_y = min(top_left_world[1], bottom_right_world[1])
        max_y = max(top_left_world[1], bottom_right_world[1])

        min_x = math.floor(min_x / grid_spacing_world) * grid_spacing_world
        max_x = math.ceil(max_x / grid_spacing_world) * grid_spacing_world
        min_y = math.floor(min_y / grid_spacing_world) * grid_spacing_world
        max_y = math.ceil(max_y / grid_spacing_world) * grid_spacing_world

        for x in _frange(min_x, max_x + grid_spacing_world / 2, grid_spacing_world):
            start, end, color, thickness = self._compute_line_params(x, True, top_left_world, bottom_right_world, grid_spacing_world)
            self._draw_line(screen, start, end, color[:3], thickness)
            if self.coordinate_display_mode == "world":
                self._draw_world_label(screen, x, 0, is_x=True)
        for y in _frange(min_y, max_y + grid_spacing_world / 2, grid_spacing_world):
            start, end, color, thickness = self._compute_line_params(y, False, top_left_world, bottom_right_world, grid_spacing_world)
            self._draw_line(screen, start, end, color[:3], thickness)
            if self.coordinate_display_mode == "world":
                self._draw_world_label(screen, 0, y, is_x=False)

        if self.polar_enabled:
            self._draw_polar_grid(screen, top_left_world, bottom_right_world)

        if self.coordinate_display_mode == "world":
            self._draw_axis_labels(screen)
            self._draw_cursor_coordinates(screen)

        if self.force_field_manager and self.force_field_manager.physics_manager.running_physics:
            self._draw_gravity_vectors(screen, grid_spacing_world, grid_spacing_pixels)

        self.draw_scale_indicator(screen, grid_spacing_world, grid_spacing_pixels)
        if self.coordinate_display_mode == "screen":
            self.draw_rulers(screen)
    def _apply_grid_colors(self):
        scheme = config.grid.default_colors
        self.grid_color_major = (*scheme.major, 255) if len(scheme.major) == 3 else scheme.major
        self.grid_color_minor = (*scheme.minor, 255) if len(scheme.minor) == 3 else scheme.minor
        self.grid_color_origin = (*scheme.origin, 255) if len(scheme.origin) == 3 else scheme.origin

    def _apply_polar_colors(self):
        polar = config.grid.polar
        self.polar_color_radial = polar.radial_line_color
        self.polar_color_circular = polar.circular_line_color

    def _draw_polar_grid(self, screen, top_left, bottom_right):
        if not config.grid.polar.visible:
            return
        polar = config.grid.polar
        origin = (0.0, 0.0)
        origin_screen = self.camera.world_to_screen(origin)
        screen_w, screen_h = screen.get_width(), screen.get_height()

        corner_world = self.camera.screen_to_world((screen_w, screen_h))
        max_radius_world = math.hypot(-corner_world[0], -corner_world[1]) * 1.05
        grid_spacing_world, _ = self.calculate_grid_spacing()
        if grid_spacing_world <= 1e-12:
            return
        num_circles = min(int(max_radius_world / grid_spacing_world) + 1, polar.max_circles)

        alpha = polar.max_alpha
        if polar.fade_with_zoom:
            _, pixel_spacing = self.calculate_grid_spacing()
            t = min(1.0, max(0.0, (pixel_spacing - self.min_pixel_spacing) / (
                        self.max_pixel_spacing - self.min_pixel_spacing)))
            alpha = int(polar.min_alpha + (polar.max_alpha - polar.min_alpha) * (1.0 - t))
        circle_color = (*self.polar_color_circular[:3], alpha)
        radial_color = (*self.polar_color_radial[:3], alpha)
        label_font = pygame.font.SysFont("Consolas", polar.label_font_size)

        def clamp(c):
            return max(-32768, min(32767, int(round(c))))

        for i in range(1, num_circles + 1):
            radius = i * grid_spacing_world
            radius_px = radius * self.camera.scaling
            if radius_px < 1.0:
                continue
            if radius_px > 32767:
                break

            steps = 8 if radius_px < 5 else (16 if radius_px < 20 else polar.circular_resolution_theta_steps)
            pts = []
            for j in range(steps):
                theta = 2 * math.pi * j / steps
                x = radius * math.cos(theta)
                y = radius * math.sin(theta)
                sx, sy = self.camera.world_to_screen((x, y))
                pts.append((clamp(sx), clamp(sy)))
            # if len(pts) > 2:
            #     pygame.gfxdraw.filled_polygon(screen, pts, (*circle_color[:3], min(30, alpha // 8)))
            #     pygame.gfxdraw.aapolygon(screen, pts, circle_color[:3])


        angle_step_rad = math.radians(polar.angle_step_deg)
        theta = 0.0
        while theta < 2 * math.pi + angle_step_rad / 2:
            deg = int(round(math.degrees(theta)) % 360)
            dx, dy = math.cos(theta), math.sin(theta)

            end_world = (dx * max_radius_world, dy * max_radius_world)
            end_screen = self.camera.world_to_screen(end_world)
            ox, oy = clamp(origin_screen[0]), clamp(origin_screen[1])
            ex, ey = clamp(end_screen[0]), clamp(end_screen[1])
            if -32768 <= ex <= 32767 and -32768 <= ey <= 32767:
                pygame.gfxdraw.line(screen, ox, oy, ex, ey, radial_color)

            if polar.enable_labels and deg % polar.major_angle_step_deg == 0 and deg != 0:
                label_offset = polar.min_radius_label_distance_px
                label_x = origin_screen[0] + dx * label_offset
                label_y = origin_screen[1] + dy * label_offset
                if 0 <= label_x < screen_w and 0 <= label_y < screen_h:
                    label = f"{deg}°"
                    text_surf = label_font.render(label, True, polar.label_color_radial)
                    screen.blit(text_surf, (clamp(label_x) - text_surf.get_width() // 2,
                                            clamp(label_y) - text_surf.get_height() // 2))
            theta += angle_step_rad
    def _draw_axis_labels(self, screen):
        offset = 1.5 * self.calculate_grid_spacing()[0]
        x_label_pos = self.camera.world_to_screen((offset, 0))
        y_label_pos = self.camera.world_to_screen((0, offset))
        font = pygame.font.SysFont("Consolas", 14, bold=True)
        x_surf = font.render("X", True, (200, 200, 200))
        y_surf = font.render("Y", True, (200, 200, 200))
        screen.blit(x_surf, (int(x_label_pos[0]), int(x_label_pos[1] - x_surf.get_height() - 2)))
        screen.blit(y_surf, (int(y_label_pos[0] + 2), int(y_label_pos[1])))
    def _draw_world_label(self, screen, x, y, is_x):
        if abs(x) < 1e-12 and abs(y) < 1e-12:
            return
        world_pos = (x, y)
        screen_pos = self.camera.world_to_screen(world_pos)
        label = self._format_number(x if is_x else y)
        text_surf = self.ruler_font.render(label, True, (200, 200, 200))
        offset = 4
        if is_x:
            pos = (int(screen_pos[0] - text_surf.get_width() / 2), int(screen_pos[1] + offset))
        else:
            pos = (int(screen_pos[0] + offset), int(screen_pos[1] - text_surf.get_height() / 2))
        screen.blit(text_surf, pos)

    def _format_number(self, val):
        abs_val = abs(val)
        if abs_val >= 1e6: return f"{val / 1e6:.1f}e6"
        elif abs_val >= 1: return f"{val:.0f}"
        elif abs_val >= 1e-3: return f"{val * 1e3:.0f}mm"
        elif abs_val >= 1e-6: return f"{val * 1e6:.0f}µm"
        else: return f"{val * 1e9:.0f}nm"
    def _draw_cursor_coordinates(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        world_mouse = self.camera.screen_to_world(mouse_pos)
        label_x = f"X: {self._format_number(world_mouse[0])}"
        label_y = f"Y: {self._format_number(world_mouse[1])}"
        text_x = self.ruler_font.render(label_x, True, (255, 255, 0))
        text_y = self.ruler_font.render(label_y, True, (255, 255, 0))
        margin = 8
        screen.blit(text_x, (mouse_pos[0] + margin, mouse_pos[1] + margin))
        screen.blit(text_y, (mouse_pos[0] + margin, mouse_pos[1] + margin + text_x.get_height() + 2))
    def draw_rulers(self, screen):
        screen_width, screen_height = screen.get_size()
        margin = 5
        tick_length = 6
        text_offset = 3
        min_label_spacing = 40
        top_left_world = self.camera.screen_to_world((0, 0))
        bottom_right_world = self.camera.screen_to_world((screen_width, screen_height))
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        if grid_spacing_pixels < 10: return
        min_x = min(top_left_world[0], bottom_right_world[0])
        max_x = max(top_left_world[0], bottom_right_world[0])
        min_y = min(top_left_world[1], bottom_right_world[1])
        max_y = max(top_left_world[1], bottom_right_world[1])

        min_x = math.floor(min_x / grid_spacing_world) * grid_spacing_world
        max_x = math.ceil(max_x / grid_spacing_world) * grid_spacing_world
        min_y = math.floor(min_y / grid_spacing_world) * grid_spacing_world
        max_y = math.ceil(max_y / grid_spacing_world) * grid_spacing_world
        skip = max(1, getattr(config.grid, 'ruler_skip_factor', 1))

        def format_number(val):
            abs_val = abs(val)
            if abs_val >= 1e6: return f"{val / 1e6:.1f}e6"
            elif abs_val >= 1: return f"{val:.0f}"
            elif abs_val >= 1e-3: return f"{val * 1e3:.0f}mm"
            elif abs_val >= 1e-6: return f"{val * 1e6:.0f}µm"
            else: return f"{val * 1e9:.0f}nm"

        last_label_x = -min_label_spacing
        for x in _frange(min_x, max_x + grid_spacing_world / 2, grid_spacing_world):
            tick_index = round(x / grid_spacing_world)
            if tick_index % skip == 0:
                screen_x = self.camera.world_to_screen((x, 0))[0]
                if 0 <= screen_x <= screen_width and screen_x - last_label_x >= min_label_spacing:
                    pygame.gfxdraw.line(screen, int(screen_x), 0, int(screen_x), tick_length, (200, 200, 200))
                    label = format_number(x)
                    text_surf = self.ruler_font.render(label, True, (200, 200, 200))
                    screen.blit(text_surf, (int(screen_x), tick_length + text_offset))
                    last_label_x = screen_x

        last_label_y = -min_label_spacing
        for y in _frange(min_y, max_y + grid_spacing_world / 2, grid_spacing_world):
            tick_index = round(y / grid_spacing_world)
            if tick_index % skip == 0:
                screen_y = self.camera.world_to_screen((0, y))[1]
                if 0 <= screen_y <= screen_height and screen_y - last_label_y >= min_label_spacing:
                    pygame.gfxdraw.line(screen, 0, int(screen_y), tick_length, int(screen_y), (200, 200, 200))
                    label = format_number(y)
                    text_surf = self.ruler_font.render(label, True, (200, 200, 200))
                    screen.blit(text_surf, (tick_length + text_offset, int(screen_y)))
                    last_label_y = screen_y

        mouse_pos = pygame.mouse.get_pos()
        world_mouse = self.camera.screen_to_world(mouse_pos)
        cursor_x_screen, cursor_y_screen = mouse_pos
        if 0 <= cursor_x_screen <= screen_width:
            pygame.gfxdraw.line(screen, int(cursor_x_screen), 0, int(cursor_x_screen), tick_length * 2, (255, 255, 0))
            cursor_x_label = format_number(world_mouse[0])
            text_surf = self.ruler_font.render(cursor_x_label, True, (255, 255, 0))
            screen.blit(text_surf, (int(cursor_x_screen), tick_length * 2 + text_offset))
        if 0 <= cursor_y_screen <= screen_height:
            pygame.gfxdraw.line(screen, 0, int(cursor_y_screen), tick_length * 2, int(cursor_y_screen), (255, 255, 0))
            cursor_y_label = format_number(world_mouse[1])
            text_surf = self.ruler_font.render(cursor_y_label, True, (255, 255, 0))
            screen.blit(text_surf, (tick_length * 2 + text_offset, int(cursor_y_screen)))

    def toggle_grid(self):
        self.enabled = not self.enabled

    def set_grid_enabled(self, enabled):
        self.enabled = enabled

    def calculate_grid_spacing(self):
        camera_scale = self.camera.scaling
        base_pixels = self.base_grid_size * camera_scale
        multiplier = 1.0
        if base_pixels < self.min_pixel_spacing:
            while base_pixels * multiplier < self.min_pixel_spacing:
                multiplier *= 10
        elif base_pixels > self.max_pixel_spacing:
            while base_pixels / multiplier > self.max_pixel_spacing and multiplier < 1e9:
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
            if grid_spacing_world <= 1e-12: return
            nearest_x = round(world_pos[0] / grid_spacing_world) * grid_spacing_world
            nearest_y = round(world_pos[1] / grid_spacing_world) * grid_spacing_world
            dx_world = nearest_x - world_pos[0]
            dy_world = nearest_y - world_pos[1]
            dx_pixels = dx_world * self.camera.scaling
            dy_pixels = dy_world * self.camera.scaling
            distance_pixels = math.hypot(dx_pixels, dy_pixels)
            if distance_pixels <= max(self.snap_radius_pixels, 0.5):
                if distance_pixels < 1e-6:
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

    def _compute_line_params(self, coord, is_vertical, top_left_world, bottom_right_world, grid_spacing_world):
        if abs(coord) < 1e-12:
            color = self.grid_color_origin
            thickness = self.origin_line_thickness
        elif abs(coord / grid_spacing_world) % self.major_grid_multiplier < 1e-12:
            color = self.grid_color_major
            thickness = self.major_line_thickness
        else:
            color = self.grid_color_minor
            thickness = self.minor_line_thickness
        if is_vertical:
            start = self.camera.world_to_screen((coord, top_left_world[1]))
            end = self.camera.world_to_screen((coord, bottom_right_world[1]))
        else:
            start = self.camera.world_to_screen((top_left_world[0], coord))
            end = self.camera.world_to_screen((bottom_right_world[0], coord))
        return start, end, color, thickness

    def _draw_line(self, screen, start, end, color, thickness):
        def clamp_coord(c):
            return max(-32768, min(32767, int(round(c))))

        sx, sy = clamp_coord(start[0]), clamp_coord(start[1])
        ex, ey = clamp_coord(end[0]), clamp_coord(end[1])
        if thickness <= 1:
            pygame.gfxdraw.line(screen, sx, sy, ex, ey, color)
        else:
            dx = ex - sx
            dy = ey - sy
            length = max(1, math.hypot(dx, dy))
            ux, uy = dx / length, dy / length
            perp_x, perp_y = -uy * thickness / 2, ux * thickness / 2
            pts = [
                (sx + perp_x, sy + perp_y),
                (ex + perp_x, ey + perp_y),
                (ex - perp_x, ey - perp_y),
                (sx - perp_x, sy - perp_y)
            ]
            clamped_pts = [(clamp_coord(p[0]), clamp_coord(p[1])) for p in pts]
            pygame.gfxdraw.filled_polygon(screen, clamped_pts, color)

    def _draw_gravity_vectors(self, screen, grid_spacing_world, grid_spacing_pixels):
        if not self.force_field_manager or not any(self.force_field_manager.active_fields.get(f, False) for f in ("attraction", "repulsion", "vortex", "wind")):
            return
        if grid_spacing_pixels < 10: return
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
                        fx += dx * t; fy += dy * t
                    if self.force_field_manager.active_fields.get("repulsion"):
                        fx -= dx * t; fy -= dy * t
                    if self.force_field_manager.active_fields.get("vortex"):
                        fx += -dy * t; fy += dx * t
                if self.force_field_manager.active_fields.get("wind"):
                    fx += 1.0
                if abs(fx) < 1e-6 and abs(fy) < 1e-6:
                    y += spacing; continue
                start_world = (x, y)
                end_world = (x + fx, y + fy)
                start_screen = self.camera.world_to_screen(start_world)
                raw_end_screen = self.camera.world_to_screen(end_world)
                dx_s = raw_end_screen[0] - start_screen[0]
                dy_s = raw_end_screen[1] - start_screen[1]
                len_s = math.hypot(dx_s, dy_s)
                if len_s > max_screen_length and len_s > 1e-6:
                    ratio = max_screen_length / len_s
                    dx_s *= ratio; dy_s *= ratio
                final_end_screen = (start_screen[0] + dx_s, start_screen[1] + dy_s)
                pygame.gfxdraw.line(screen, int(start_screen[0]), int(start_screen[1]), int(final_end_screen[0]), int(final_end_screen[1]), (255, 100, 100))
                y += spacing
            x += spacing

    def get_grid_info(self):
        if not self.enabled: return "Grid: Disabled"
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        if grid_spacing_world >= 100: spacing_str = f"{grid_spacing_world / 100:.2f}m"
        elif grid_spacing_world >= 1: spacing_str = f"{grid_spacing_world:.1f}cm"
        elif grid_spacing_world >= 1e-3: spacing_str = f"{grid_spacing_world * 1e3:.1f}mm"
        elif grid_spacing_world >= 1e-6: spacing_str = f"{grid_spacing_world * 1e6:.1f}µm"
        else: spacing_str = f"{grid_spacing_world * 1e9:.1f}nm"
        return f"Grid: {spacing_str} ({grid_spacing_pixels:.1f}px)"

    def set_colors(self, major_color=None, minor_color=None, origin_color=None):
        if major_color: self.grid_color_major = major_color
        if minor_color: self.grid_color_minor = minor_color
        if origin_color: self.grid_color_origin = origin_color

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
        elif grid_spacing_world >= 1e-3:
            label = f"{grid_spacing_world * 1e3:.0f} mm"
        elif grid_spacing_world >= 1e-6:
            label = f"{grid_spacing_world * 1e6:.0f} µm"
        else:
            label = f"{grid_spacing_world * 1e9:.0f} nm"
        screen_width, screen_height = screen.get_size()
        margin = 30
        bar_length_pixels = int(grid_spacing_pixels)
        start_x = screen_width - margin - bar_length_pixels
        end_x = screen_width - margin
        y_pos = screen_height - margin

        def clamp_coord(c):
            return max(-32768, min(32767, int(round(c))))

        cx1, cy = clamp_coord(start_x), clamp_coord(y_pos)
        cx2 = clamp_coord(end_x)
        if abs(cx2 - cx1) > 0 and abs(cy) <= 32767:
            pygame.gfxdraw.line(screen, cx1, cy, cx2, cy, (255, 255, 255))
            tick_height = 6
            for x in (cx1, cx2):
                pygame.gfxdraw.line(screen, x, cy - tick_height // 2, x, cy + tick_height // 2, (255, 255, 255))
            text_surf = pygame.font.SysFont("Consolas", 16).render(label, True, (255, 255, 255))
            screen.blit(text_surf,
                        (clamp_coord(cx1 + (cx2 - cx1) / 2 - text_surf.get_width() / 2), clamp_coord(cy - 14)))

def _frange(start, stop, step):
    while start < stop:
        yield start
        start += step