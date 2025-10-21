import pygame
import pygame.gfxdraw
import math
import sys
import os

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


from UPST.config import Config
from UPST.gizmos_manager import Gizmos
from UPST.profiler import profile, profile_context, start_profiling, stop_profiling


class GridManager:
    def __init__(self, camera):
        self.camera = camera
        self.enabled = True

        self.grid_color_major = (80, 80, 80, 255)
        self.grid_color_minor = (40, 40, 40, 255)
        self.grid_color_origin = (120, 120, 120, 255)

        self.base_grid_size = Config.GRID_BASE_SIZE
        self.major_grid_multiplier = Config.GRID_MAJOR_MULTIPLIER
        self.min_pixel_spacing = Config.GRID_MIN_PIXEL_SPACING
        self.max_pixel_spacing = Config.GRID_MAX_PIXEL_SPACING

        self.minor_line_thickness = Config.GRID_MINOR_LINE_THICKNESS
        self.major_line_thickness = Config.GRID_MAJOR_LINE_THICKNESS
        self.origin_line_thickness = Config.GRID_ORIGIN_LINE_THICKNESS

        self.ruler_font = pygame.font.SysFont("Consolas", 12)

        self._was_grabbed = False
        self._snapping_active = False

    def toggle_grid(self):
        self.enabled = not self.enabled

    def set_grid_enabled(self, enabled):
        self.enabled = enabled

    def calculate_grid_spacing(self):
        camera_scale = self.camera.target_scaling
        base_pixels = self.base_grid_size * camera_scale
        multiplier = 1
        if base_pixels < self.min_pixel_spacing:
            while base_pixels * multiplier < self.min_pixel_spacing:
                multiplier *= 10
        elif base_pixels > self.max_pixel_spacing:
            while base_pixels / multiplier > self.max_pixel_spacing and multiplier < 100:
                multiplier *= 10
            multiplier = 1 / multiplier
        grid_spacing_world = self.base_grid_size * multiplier
        grid_spacing_pixels = grid_spacing_world * camera_scale
        return grid_spacing_world, grid_spacing_pixels

    def _handle_snapping(self):
        keys = pygame.key.get_pressed()
        active = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])

        if active and pygame.mouse.get_focused():
            if not self._snapping_active:
                self._was_grabbed = pygame.event.get_grab()
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
                self._snapping_active = True

            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_pos = self.camera.screen_to_world((mouse_x, mouse_y))
            snapped_world_x = round(world_pos[0])
            snapped_world_y = round(world_pos[1])
            snapped_screen = self.camera.world_to_screen((snapped_world_x, snapped_world_y))
            target_x, target_y = int(snapped_screen[0]), int(snapped_screen[1])

            pygame.mouse.set_pos(target_x, target_y)
        else:
            if self._snapping_active:
                if self._was_grabbed:
                    pygame.event.set_grab(True)
                self._snapping_active = False

    @profile("grid", "app")
    def draw(self, screen):
        self._handle_snapping()
        if not self.enabled:
            return

        screen_width = screen.get_width()
        screen_height = screen.get_height()
        grid_spacing_world, grid_spacing_pixels = self.calculate_grid_spacing()

        if grid_spacing_pixels < 5:
            return

        top_left_world = self.camera.screen_to_world((0, 0))
        bottom_right_world = self.camera.screen_to_world((screen_width, screen_height))

        min_x = math.floor(top_left_world[0] / grid_spacing_world) * grid_spacing_world
        max_x = math.ceil(bottom_right_world[0] / grid_spacing_world) * grid_spacing_world
        min_y = math.floor(top_left_world[1] / grid_spacing_world) * grid_spacing_world
        max_y = math.ceil(bottom_right_world[1] / grid_spacing_world) * grid_spacing_world

        def draw_thick_line(surface, color, start_pos, end_pos, thickness):
            if thickness == 1:
                pygame.gfxdraw.line(surface, int(start_pos[0]), int(start_pos[1]),
                                    int(end_pos[0]), int(end_pos[1]), color[:3])
            else:
                for i in range(thickness):
                    offset = i - thickness // 2
                    if start_pos[0] == end_pos[0]:
                        pygame.gfxdraw.line(surface, int(start_pos[0]) + offset, int(start_pos[1]),
                                            int(end_pos[0]) + offset, int(end_pos[1]), color[:3])
                    else:
                        pygame.gfxdraw.line(surface, int(start_pos[0]), int(start_pos[1]) + offset,
                                            int(end_pos[0]), int(end_pos[1]) + offset, color[:3])

        def get_line_params(coord, is_vertical):
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
                start_screen = self.camera.world_to_screen((coord, top_left_world[1]))
                end_screen = self.camera.world_to_screen((coord, bottom_right_world[1]))
            else:
                start_screen = self.camera.world_to_screen((top_left_world[0], coord))
                end_screen = self.camera.world_to_screen((bottom_right_world[0], coord))

            return start_screen, end_screen, color, thickness

        x = min_x
        while x <= max_x:
            start, end, color, thickness = get_line_params(x, is_vertical=True)
            draw_thick_line(screen, color, start, end, thickness)
            x += grid_spacing_world

        y = min_y
        while y <= max_y:
            start, end, color, thickness = get_line_params(y, is_vertical=False)
            draw_thick_line(screen, color, start, end, thickness)
            y += grid_spacing_world

        self.draw_scale_indicator(screen, grid_spacing_world, grid_spacing_pixels)
        self.draw_rulers(screen)

    def draw_rulers(self, screen):
        screen_width = screen.get_width()
        screen_height = screen.get_height()
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

        def format_number(val):
            abs_val = abs(val)
            if abs_val >= 1e6:
                return f"{val / 1e6:.1f}e6"
            else:
                return f"{val:.0f}"

        last_label_x = -min_label_spacing
        x = min_x
        while x <= max_x:
            screen_x = self.camera.world_to_screen((x, 0))[0]
            if 0 <= screen_x <= screen_width:
                if screen_x - last_label_x >= min_label_spacing:
                    pygame.draw.line(screen, (200, 200, 200), (screen_x, 0), (screen_x, tick_length))
                    label = format_number(x)
                    text_surface = self.ruler_font.render(label, True, (200, 200, 200))
                    screen.blit(text_surface, (screen_x - text_surface.get_width() // 2, tick_length + text_offset))
                    last_label_x = screen_x
            x += grid_spacing_world

        last_label_y = -min_label_spacing
        y = min_y
        while y <= max_y:
            screen_y = self.camera.world_to_screen((0, y))[1]
            if 0 <= screen_y <= screen_height:
                if screen_y - last_label_y >= min_label_spacing:
                    pygame.draw.line(screen, (200, 200, 200), (0, screen_y), (tick_length, screen_y))
                    label = format_number(y)
                    text_surface = self.ruler_font.render(label, True, (200, 200, 200))
                    screen.blit(text_surface, (tick_length + text_offset, screen_y - text_surface.get_height() // 2))
                    last_label_y = screen_y
            y += grid_spacing_world

        mouse_pos = pygame.mouse.get_pos()
        world_mouse = self.camera.screen_to_world(mouse_pos)

        cursor_x_screen = mouse_pos[0]
        if 0 <= cursor_x_screen <= screen_width:
            pygame.draw.line(screen, (255, 255, 0), (cursor_x_screen, 0), (cursor_x_screen, tick_length * 2), 2)
            cursor_x_label = format_number(world_mouse[0])
            cursor_x_text = self.ruler_font.render(cursor_x_label, True, (255, 255, 0))
            screen.blit(cursor_x_text,
                        (cursor_x_screen - cursor_x_text.get_width() // 2, tick_length * 2 + text_offset))

        cursor_y_screen = mouse_pos[1]
        if 0 <= cursor_y_screen <= screen_height:
            pygame.draw.line(screen, (255, 255, 0), (0, cursor_y_screen), (tick_length * 2, cursor_y_screen), 2)
            cursor_y_label = format_number(world_mouse[1])
            cursor_y_text = self.ruler_font.render(cursor_y_label, True, (255, 255, 0))
            screen.blit(cursor_y_text,
                        (tick_length * 2 + text_offset, cursor_y_screen - cursor_y_text.get_height() // 2))

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
        if theme_name in Config.WORLD_THEMES:
            theme = Config.WORLD_THEMES[theme_name]
            bg_color = theme["background_color"]
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

        start_pos = (start_x, y_pos)
        end_pos = (end_x, y_pos)

        Gizmos.draw_line(start=start_pos, end=end_pos, color="white", thickness=3, duration=0.05, world_space=False)

        tick_height = 6
        for x in (start_x, end_x):
            Gizmos.draw_line(
                start=(x, y_pos - tick_height // 2),
                end=(x, y_pos + tick_height // 2),
                color="white",
                thickness=3,
                duration=0.05,
                world_space=False,
            )

        Gizmos.draw_text(
            position=((start_x + bar_length_pixels / 2), y_pos - 14),
            text=label,
            color="white",
            font_size=16,
            duration=0.05,
            font_name="Consolas",
            world_space=False,
            font_world_space=False,
        )