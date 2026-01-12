import pygame, pygame.gfxdraw, math, sys, pymunk
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try: import win32api, win32con
    except ImportError: IS_WINDOWS = False
IS_LINUX = sys.platform.startswith("linux")
if IS_LINUX:
    try:
        from Xlib import X, display
        from Xlib.ext import xtest
        _display = display.Display()
    except ImportError: IS_LINUX = False
from UPST.config import config

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

    def toggle_grid(self): self.enabled = not self.enabled
    def set_grid_enabled(self, enabled): self.enabled = enabled

    def calculate_grid_spacing(self):
        camera_scale = self.camera.scaling
        base_pixels = self.base_grid_size * camera_scale
        multiplier = 1.0
        if base_pixels < self.min_pixel_spacing:
            while base_pixels * multiplier < self.min_pixel_spacing: multiplier *= 10
        elif base_pixels > self.max_pixel_spacing:
            while base_pixels / multiplier > self.max_pixel_spacing and multiplier < 1e9: multiplier *= 10
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
                if distance_pixels < 1e-6: target_x, target_y = nearest_x, nearest_y
                else:
                    t = (self.snap_radius_pixels - distance_pixels) / self.snap_radius_pixels
                    t = max(0.0, min(1.0, t * self.snap_strength + (1.0 - self.snap_strength)))
                    target_x = world_pos[0] + dx_world * t
                    target_y = world_pos[1] + dy_world * t
                target_screen = self.camera.world_to_screen((target_x, target_y))
                target_x_int = int(round(target_screen[0]))
                target_y_int = int(round(target_screen[1]))
                if (target_x_int, target_y_int) != (mouse_x, mouse_y): pygame.mouse.set_pos(target_x_int, target_y_int)
        else:
            if self._snapping_active:
                pygame.event.set_grab(self._was_grabbed)
                pygame.mouse.set_visible(self._was_visible)
                self._snapping_active = False

    def _format_value(self, v):
        av = abs(v)
        if av >= 1e3: return f"{v/1e3:.1f} km"
        if av >= 1: return f"{v:.1f} m"
        if av >= 1e-3: return f"{v*1e3:.1f} mm"
        if av >= 1e-6: return f"{v*1e6:.1f} µm"
        return f"{v*1e9:.1f} nm"

    def draw(self, screen):
        if not self.enabled: return
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()
        self._handle_snapping(grid_spacing_world, grid_spacing_pixels)
        if grid_spacing_pixels >= 5:
            top_left_world = self.camera.screen_to_world((0, 0))
            bottom_right_world = self.camera.screen_to_world((screen.get_width(), screen.get_height()))
            min_x = min(top_left_world[0], bottom_right_world[0]); max_x = max(top_left_world[0], bottom_right_world[0])
            min_y = min(top_left_world[1], bottom_right_world[1]); max_y = max(top_left_world[1], bottom_right_world[1])
            min_x = math.floor(min_x / grid_spacing_world) * grid_spacing_world
            max_x = math.ceil(max_x / grid_spacing_world) * grid_spacing_world
            min_y = math.floor(min_y / grid_spacing_world) * grid_spacing_world
            max_y = math.ceil(max_y / grid_spacing_world) * grid_spacing_world
            for x in _frange(min_x, max_x + grid_spacing_world/2, grid_spacing_world):
                start, end, color, thickness = self._compute_line_params(x, True, top_left_world, bottom_right_world, grid_spacing_world)
                self._draw_line(screen, start, end, color[:3], thickness)
            for y in _frange(min_y, max_y + grid_spacing_world/2, grid_spacing_world):
                start, end, color, thickness = self._compute_line_params(y, False, top_left_world, bottom_right_world, grid_spacing_world)
                self._draw_line(screen, start, end, color[:3], thickness)
            if self.force_field_manager and self.force_field_manager.physics_manager.running_physics: self._draw_gravity_vectors(screen, grid_spacing_world, grid_spacing_pixels)
            self.draw_scale_indicator(screen, grid_spacing_world, grid_spacing_pixels)
            self.draw_rulers(screen)
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world((mx, my))
        status_text = f"X: {self._format_value(wx)}, Y: {self._format_value(wy)}"
        status_surf = self.ruler_font.render(status_text, True, (255, 255, 255))
        screen.blit(status_surf, (5, screen.get_height() - status_surf.get_height() - 5))

    def _compute_line_params(self, coord, is_vertical, top_left_world, bottom_right_world, grid_spacing_world):
        if abs(coord) < 1e-12: color, thickness = self.grid_color_origin, self.origin_line_thickness
        elif abs(coord / grid_spacing_world) % self.major_grid_multiplier < 1e-12: color, thickness = self.grid_color_major, self.major_line_thickness
        else: color, thickness = self.grid_color_minor, self.minor_line_thickness
        if is_vertical:
            start = self.camera.world_to_screen((coord, top_left_world[1]))
            end = self.camera.world_to_screen((coord, bottom_right_world[1]))
        else:
            start = self.camera.world_to_screen((top_left_world[0], coord))
            end = self.camera.world_to_screen((bottom_right_world[0], coord))
        return start, end, color, thickness

    def _draw_line(self, screen, start, end, color, thickness):
        def clamp_coord(c): return max(-32768, min(32767, int(round(c))))
        sx, sy = clamp_coord(start[0]), clamp_coord(start[1]); ex, ey = clamp_coord(end[0]), clamp_coord(end[1])
        if thickness <= 1: pygame.gfxdraw.line(screen, sx, sy, ex, ey, color)
        else:
            dx = ex - sx; dy = ey - sy
            length = max(1, math.hypot(dx, dy))
            ux, uy = dx / length, dy / length
            perp_x, perp_y = -uy * thickness / 2, ux * thickness / 2
            pts = [(sx + perp_x, sy + perp_y), (ex + perp_x, ey + perp_y), (ex - perp_x, ey - perp_y), (sx - perp_x, sy - perp_y)]
            clamped_pts = [(clamp_coord(p[0]), clamp_coord(p[1])) for p in pts]
            pygame.gfxdraw.filled_polygon(screen, clamped_pts, color)

    def _draw_gravity_vectors(self, screen, grid_spacing_world, grid_spacing_pixels):
        if not self.force_field_manager or not any(self.force_field_manager.active_fields.get(f, False) for f in ("attraction", "repulsion", "vortex", "wind")): return
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
                dx = world_mouse[0] - x; dy = world_mouse[1] - y
                dist = math.hypot(dx, dy)
                if dist <= self.force_field_manager.radius:
                    t = 1.0 - dist / self.force_field_manager.radius
                    if self.force_field_manager.active_fields.get("attraction"): fx += dx * t; fy += dy * t
                    if self.force_field_manager.active_fields.get("repulsion"): fx -= dx * t; fy -= dy * t
                    if self.force_field_manager.active_fields.get("vortex"): fx += -dy * t; fy += dx * t
                if self.force_field_manager.active_fields.get("wind"): fx += 1.0
                if abs(fx) < 1e-6 and abs(fy) < 1e-6:
                    y += spacing; continue
                start_world = (x, y); end_world = (x + fx, y + fy)
                start_screen = self.camera.world_to_screen(start_world)
                raw_end_screen = self.camera.world_to_screen(end_world)
                dx_s = raw_end_screen[0] - start_screen[0]; dy_s = raw_end_screen[1] - start_screen[1]
                len_s = math.hypot(dx_s, dy_s)
                if len_s > max_screen_length and len_s > 1e-6:
                    ratio = max_screen_length / len_s
                    dx_s *= ratio; dy_s *= ratio
                final_end_screen = (start_screen[0] + dx_s, start_screen[1] + dy_s)
                pygame.gfxdraw.line(screen, int(start_screen[0]), int(start_screen[1]), int(final_end_screen[0]), int(final_end_screen[1]), (255, 100, 100))
                y += spacing
            x += spacing

    def draw_rulers(self, screen):
        w, h = screen.get_size()
        margin, tick_len, text_off = 5, 6, 3
        min_label_px = 40
        top_left = self.camera.screen_to_world((0, 0))
        bottom_right = self.camera.screen_to_world((w, h))
        grid_spacing_w, grid_spacing_px = self.calculate_grid_spacing()
        if grid_spacing_px < 8: return
        ruler_color = (200, 200, 200)
        cursor_color = (255, 255, 0)
        skip_factor = max(1, getattr(config.grid, 'ruler_skip_factor', 1))
        def draw_axis(values, is_x):
            last_pos = -min_label_px
            for val in values:
                idx = round(val / grid_spacing_w)
                if idx % skip_factor != 0: continue
                pos = self.camera.world_to_screen((val, 0) if is_x else (0, val))[0 if is_x else 1]
                if not (0 <= pos <= (w if is_x else h)): continue
                if pos - last_pos < min_label_px: continue
                if is_x:
                    pygame.gfxdraw.line(screen, int(pos), 0, int(pos), tick_len, ruler_color)
                    txt = self.ruler_font.render(self._format_value(val), True, ruler_color)
                    screen.blit(txt, (int(pos), tick_len + text_off))
                else:
                    pygame.gfxdraw.line(screen, 0, int(pos), tick_len, int(pos), ruler_color)
                    txt = self.ruler_font.render(self._format_value(val), True, ruler_color)
                    screen.blit(txt, (tick_len + text_off, int(pos)))
                last_pos = pos
        min_x = math.floor(min(top_left[0], bottom_right[0]) / grid_spacing_w) * grid_spacing_w
        max_x = math.ceil(max(top_left[0], bottom_right[0]) / grid_spacing_w) * grid_spacing_w
        min_y = math.floor(min(top_left[1], bottom_right[1]) / grid_spacing_w) * grid_spacing_w
        max_y = math.ceil(max(top_left[1], bottom_right[1]) / grid_spacing_w) * grid_spacing_w
        draw_axis(_frange(min_x, max_x + grid_spacing_w/2, grid_spacing_w), True)
        draw_axis(_frange(min_y, max_y + grid_spacing_w/2, grid_spacing_w), False)
        mx, my = pygame.mouse.get_pos()
        if 0 <= mx <= w: pygame.gfxdraw.line(screen, mx, 0, mx, tick_len, cursor_color)
        if 0 <= my <= h: pygame.gfxdraw.line(screen, 0, my, tick_len, my, cursor_color)

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
        if grid_spacing_world >= 100: label = f"{grid_spacing_world / 100:.2f} m"
        elif grid_spacing_world >= 1: label = f"{grid_spacing_world:.0f} cm"
        elif grid_spacing_world >= 1e-3: label = f"{grid_spacing_world * 1e3:.0f} mm"
        elif grid_spacing_world >= 1e-6: label = f"{grid_spacing_world * 1e6:.0f} µm"
        else: label = f"{grid_spacing_world * 1e9:.0f} nm"
        screen_width, screen_height = screen.get_size()
        margin = 30
        bar_length_pixels = int(grid_spacing_pixels)
        start_x = screen_width - margin - bar_length_pixels
        end_x = screen_width - margin
        y_pos = screen_height - margin
        pygame.gfxdraw.line(screen, start_x, y_pos, end_x, y_pos, (255, 255, 255))
        tick_height = 6
        for x in (start_x, end_x):
            pygame.gfxdraw.line(screen, x, y_pos - tick_height // 2, x, y_pos + tick_height // 2, (255, 255, 255))
        text_surf = pygame.font.SysFont("Consolas", 16).render(label, True, (255, 255, 255))
        screen.blit(text_surf, (int(start_x + bar_length_pixels / 2 - text_surf.get_width() / 2), y_pos - 14))

def _frange(start, stop, step):
    while start < stop:
        yield start
        start += step