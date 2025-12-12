import pygame
import math
import pymunk
import time
import random
import os

from pymunk import Vec2d

from UPST.config import config
from UPST.utils import bytes_to_surface
from UPST.modules.texture_processor import TextureProcessor, TextureState
from UPST.modules.profiler import profile, start_profiling, stop_profiling
from UPST.modules.cloud_manager import CloudManager, CloudRenderer
from UPST.physics.thermal_manager import ThermalManager

import pygame.gfxdraw

class Renderer:
    def __init__(self, app, screen, camera, physics_manager, gizmos_manager,
                 grid_manager, input_handler, ui_manager, script_system=None, tool_manager=None):
        self.app = app
        self.screen = screen
        self.camera = camera
        self.tool_manager = tool_manager
        self.physics_manager = physics_manager
        self.gizmos_manager = gizmos_manager
        self.grid_manager = grid_manager
        self.input_handler = input_handler
        self.ui_manager = ui_manager
        self.script_system = script_system
        self.texture_cache = {}
        self.texture_processor = TextureProcessor()
        self.texture_cache_size = 100
        self.texture_cache_access_order = []
        self.last_texture_update = 0
        self.texture_update_interval = 0.1
        self.clouds = CloudManager(folder="sprites/background", cell_size=3000, clouds_per_cell=2)
        self.clouds.set_physics_manager(physics_manager)
        self.cloud_renderer = CloudRenderer(screen, camera, self.clouds, min_px=10)

        self.theme = config.world.themes[config.world.current_theme]
        self.default_color = (255, 255, 255)
        self.screen_w, self.screen_h = self.screen.get_size()
        self.margin = 2000
        self.clip_rect = pygame.Rect(-self.margin, -self.margin, self.screen_w + 2 * self.margin, self.screen_h + 2 * self.margin)
        self.INT16_MIN, self.INT16_MAX = -32768, 32767
        self.outline_color = (50, 50, 50, 180)
        self.outline_thickness = 1
        # self.thermal_manager = ThermalManager(physics_manager, camera)

    @profile("_draw_constraints", "renderer")
    def _draw_constraints(self):
        theme = config.world.themes[config.world.current_theme]
        default_color = (*getattr(theme, 'constraint_color', (200, 200, 255)), 200)
        outline_color = (50, 50, 50, 180)
        margin = 2000
        screen_w, screen_h = self.screen.get_size()
        clip_rect = pygame.Rect(-margin, -margin, screen_w + 2 * margin, screen_h + 2 * margin)
        safe_coord = lambda v: max(-32768, min(32767, int(round(v))))

        spring_tex_path = getattr(config.rendering, 'spring_texture', '')
        use_segmented = getattr(config.rendering, 'spring_texture_segmented', True)
        tile_world_width = getattr(config.rendering, 'spring_texture_tile_world_width', 20.0)
        base_tex = self._get_texture(spring_tex_path) if spring_tex_path and use_segmented else None
        seg_cache = {}
        if base_tex:
            tex_w, tex_h = base_tex.get_size()
            scaled_h = max(1, int(tex_h * self.camera.scaling / 10))
            base_scaled = pygame.transform.smoothscale(base_tex, (tex_w, scaled_h)) if tex_h != scaled_h else base_tex
        else:
            base_scaled = None

        for constraint in self.physics_manager.space.constraints:
            if not isinstance(constraint,
                              (pymunk.DampedSpring, pymunk.PinJoint, pymunk.SlideJoint, pymunk.PivotJoint)) or getattr(
                    constraint, 'hidden', False):
                continue

            a_world = constraint.a.local_to_world(constraint.anchor_a)
            b_world = constraint.b.local_to_world(constraint.anchor_b)
            a_scr = self.camera.world_to_screen(a_world)
            b_scr = self.camera.world_to_screen(b_world)

            dx_scr = b_scr[0] - a_scr[0]
            dy_scr = b_scr[1] - a_scr[1]
            if not (clip_rect.collidepoint(a_scr) or clip_rect.collidepoint(b_scr)):
                lsq = dx_scr * dx_scr + dy_scr * dy_scr
                if lsq == 0: continue
                t = max(0.0, min(1.0, ((clip_rect.x - a_scr[0]) * dx_scr + (clip_rect.y - a_scr[1]) * dy_scr) / lsq))
                cx, cy = a_scr[0] + t * dx_scr, a_scr[1] + t * dy_scr
                if not clip_rect.collidepoint(cx, cy): continue

            if isinstance(constraint, pymunk.DampedSpring) and base_scaled is not None:
                rest_len = constraint.rest_length
                curr_vec = b_world - a_world
                curr_len = curr_vec.length
                if rest_len <= 0.1 or curr_len <= 0.1: continue
                screen_len = math.hypot(dx_scr, dy_scr)
                if screen_len < 1e-3: continue
                num_segments = max(1, int(round(rest_len / tile_world_width)))
                seg_len_scr = screen_len / num_segments
                angle = math.atan2(dy_scr, dx_scr)
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                for i in range(num_segments):
                    seg_x0 = a_scr[0] + i * seg_len_scr * cos_a
                    seg_y0 = a_scr[1] + i * seg_len_scr * sin_a
                    key = (round(seg_len_scr, 1), round(angle, 2))
                    if key not in seg_cache:
                        stretched = pygame.transform.smoothscale(base_scaled,
                                                                 (max(1, int(seg_len_scr)), base_scaled.get_height()))
                        rotated = pygame.transform.rotate(stretched, math.degrees(-angle))
                        seg_cache[key] = rotated
                    sprite = seg_cache[key]
                    cx = seg_x0 + seg_len_scr * cos_a * 0.5
                    cy = seg_y0 + seg_len_scr * sin_a * 0.5
                    self.screen.blit(sprite, (int(cx - sprite.get_width() // 2), int(cy - sprite.get_height() // 2)))
            else:
                width = max(1, int(2 * self.camera.scaling))
                pygame.draw.line(self.screen, default_color[:3], a_scr, b_scr, width)

            for anchor_scr, tex_key in [(a_scr, 'spring_point_a_texture'), (b_scr, 'spring_point_b_texture')]:
                tex_path = getattr(config.rendering, tex_key, '')
                if tex_path:
                    pt_tex = self._get_scaled_texture(tex_path, self.camera.scaling / 4)
                    if pt_tex:
                        self.screen.blit(pt_tex, (anchor_scr[0] - pt_tex.get_width() // 2,
                                                  anchor_scr[1] - pt_tex.get_height() // 2))
                else:
                    r = max(1, int(1 * self.camera.scaling))
                    pygame.gfxdraw.filled_circle(self.screen, safe_coord(anchor_scr[0]), safe_coord(anchor_scr[1]), r,
                                                 default_color)
                    pygame.gfxdraw.aacircle(self.screen, safe_coord(anchor_scr[0]), safe_coord(anchor_scr[1]), r,
                                            (50, 50, 50))

    def safe_coord(self, v):
        return max(self.INT16_MIN, min(self.INT16_MAX, int(round(v))))

    @profile("_draw_physics_shapes", "renderer")
    def _draw_physics_shapes(self):


        draw_circle = self._draw_circle_opt
        draw_poly = self._draw_poly_opt
        draw_segment = self._draw_segment_opt

        for shape in self.physics_manager.space.shapes:
            body = shape.body
            color = (*getattr(shape, 'color', self.default_color[:3]), 255) if len(
                getattr(shape, 'color', self.default_color)) == 3 else getattr(shape, 'color', self.default_color)

            if isinstance(shape, pymunk.Circle):
                world_pos = body.local_to_world(shape.offset)
                radius_px = shape.radius * self.camera.scaling
                draw_circle(world_pos, radius_px, color, self.outline_color, self.outline_thickness, body, self.clip_rect, self.safe_coord)
            elif isinstance(shape, pymunk.Poly):
                vertices = [self.camera.world_to_screen(body.local_to_world(v)) for v in shape.get_vertices()]
                draw_poly(vertices, color, self.outline_color, self.outline_thickness, self.clip_rect, self.safe_coord)
            elif isinstance(shape, pymunk.Segment):
                a_scr = self.camera.world_to_screen(body.local_to_world(shape.a))
                b_scr = self.camera.world_to_screen(body.local_to_world(shape.b))
                radius_px = shape.radius * self.camera.scaling
                draw_segment(a_scr, b_scr, radius_px, color, self.outline_color, self.outline_thickness, self.clip_rect, self.safe_coord)

    def _draw_circle_opt(self, world_pos, radius_px, color, outline_col, thickness, body, clip_rect, safe_coord):
        if radius_px <= 0: return
        screen_pos = self.camera.world_to_screen(world_pos)
        if not (clip_rect.collidepoint(*screen_pos) or (
        dx := max(clip_rect.x, min(screen_pos[0], clip_rect.x + clip_rect.w)) - screen_pos[0]) ** 2 + (
                dy := max(clip_rect.y, min(screen_pos[1], clip_rect.y + clip_rect.h)) - screen_pos[
                    1]) ** 2 <= radius_px * radius_px): return
        ix, iy = safe_coord(screen_pos[0]), safe_coord(screen_pos[1])
        ir = min(int(radius_px), 32767)
        if ir <= 0: return

        r, g, b, a = color
        or_, og, ob, oa = outline_col

        if a == 255:
            pygame.gfxdraw.filled_circle(self.screen, ix, iy, ir, (r, g, b))
        else:
            size = ir * 2 + 2
            if size <= 65535:
                temp = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.gfxdraw.filled_circle(temp, ir + 1, ir + 1, ir, (r, g, b, a))
                self.screen.blit(temp, (ix - ir - 1, iy - ir - 1))

        if oa == 255:
            for _ in range(thickness):
                pygame.gfxdraw.aacircle(self.screen, ix, iy, ir - _, (or_, og, ob))
        else:
            size = ir * 2 + 2
            if size <= 65535:
                temp = pygame.Surface((size, size), pygame.SRCALPHA)
                for _ in range(thickness):
                    pygame.gfxdraw.aacircle(temp, ir + 1, ir + 1, ir - _, (or_, og, ob, oa))
                self.screen.blit(temp, (ix - ir - 1, iy - ir - 1))

        body_angle = body.angle
        pointer_len = ir
        wedge_angle = math.radians(20)
        cos_a, sin_a = math.cos(body_angle), math.sin(body_angle)
        tip = (ix + int(cos_a * pointer_len), iy + int(sin_a * pointer_len))
        left = (ix + int(math.cos(body_angle - wedge_angle / 2) * pointer_len),
                iy + int(math.sin(body_angle - wedge_angle / 2) * pointer_len))
        right = (ix + int(math.cos(body_angle + wedge_angle / 2) * pointer_len),
                 iy + int(math.sin(body_angle + wedge_angle / 2) * pointer_len))
        wedge = [(ix, iy), left, right]
        if all(self.INT16_MIN <= p[0] <= self.INT16_MAX and self.INT16_MIN <= p[1] <= self.INT16_MAX for p in wedge):
            pygame.gfxdraw.filled_polygon(self.screen, wedge, (0, 0, 0, 140))
            pygame.gfxdraw.aapolygon(self.screen, wedge, (0, 0, 0, 140))

    def _draw_poly_opt(self, vertices, color, outline_col, thickness, clip_rect, safe_coord):
        if len(vertices) < 3: return
        xs, ys = zip(*vertices)
        obj_rect = pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        if not obj_rect.colliderect(clip_rect): return
        int_v = [(safe_coord(vx), safe_coord(vy)) for vx, vy in vertices]
        r, g, b, a = color
        or_, og, ob, oa = outline_col

        if a == 255:
            pygame.gfxdraw.filled_polygon(self.screen, int_v, (r, g, b))
        else:
            min_x, max_x = min(v[0] for v in int_v), max(v[0] for v in int_v)
            min_y, max_y = min(v[1] for v in int_v), max(v[1] for v in int_v)
            w, h = max_x - min_x + 2, max_y - min_y + 2
            if w > 0 and h > 0 and w <= 65535 and h <= 65535:
                temp = pygame.Surface((w, h), pygame.SRCALPHA)
                shifted = [(x - min_x + 1, y - min_y + 1) for x, y in int_v]
                pygame.gfxdraw.filled_polygon(temp, shifted, (r, g, b, a))
                self.screen.blit(temp, (min_x - 1, min_y - 1))

        if oa == 255:
            pygame.gfxdraw.aapolygon(self.screen, int_v, (or_, og, ob))
        else:
            min_x, max_x = min(v[0] for v in int_v), max(v[0] for v in int_v)
            min_y, max_y = min(v[1] for v in int_v), max(v[1] for v in int_v)
            w, h = max_x - min_x + 2, max_y - min_y + 2
            if w > 0 and h > 0 and w <= 65535 and h <= 65535:
                temp = pygame.Surface((w, h), pygame.SRCALPHA)
                shifted = [(x - min_x + 1, y - min_y + 1) for x, y in int_v]
                pygame.gfxdraw.aapolygon(temp, shifted, (or_, og, ob, oa))
                self.screen.blit(temp, (min_x - 1, min_y - 1))

    def _draw_segment_opt(self, a_scr, b_scr, radius, color, outline_col, thickness, clip_rect, safe_coord):
        ax, ay, bx, by = a_scr[0], a_scr[1], b_scr[0], b_scr[1]
        if not (clip_rect.collidepoint(ax, ay) or clip_rect.collidepoint(bx, by)):
            dx, dy = bx - ax, by - ay
            lsq = dx * dx + dy * dy
            if lsq == 0: return
            t = max(0, min(1, ((clip_rect.x - ax) * dx + (clip_rect.y - ay) * dy) / lsq))
            cx, cy = ax + t * dx, ay + t * dy
            if not clip_rect.collidepoint(cx, cy): return
        ix1, iy1 = safe_coord(ax), safe_coord(ay)
        ix2, iy2 = safe_coord(bx), safe_coord(by)
        r, g, b_col, a_col = color
        or_, og, ob, oa = outline_col
        line_thick = max(1, int(radius))

        if a_col == 255:
            pygame.draw.line(self.screen, (r, g, b_col), (ix1, iy1), (ix2, iy2), line_thick)
        else:
            w, h = abs(ix2 - ix1) + 4, abs(iy2 - iy1) + 4
            temp = pygame.Surface((w, h), pygame.SRCALPHA)
            off_x, off_y = min(ix1, ix2) - 2, min(iy1, iy2) - 2
            pygame.draw.line(temp, (r, g, b_col, a_col), (ix1 - off_x, iy1 - off_y), (ix2 - off_x, iy2 - off_y),
                             line_thick)
            self.screen.blit(temp, (off_x, off_y))

        full_thick = line_thick + 2 * thickness
        if oa == 255:
            pygame.draw.line(self.screen, (or_, og, ob), (ix1, iy1), (ix2, iy2), full_thick)
            pygame.draw.line(self.screen, (r, g, b_col), (ix1, iy1), (ix2, iy2), line_thick)
        else:
            w, h = abs(ix2 - ix1) + full_thick + 2, abs(iy2 - iy1) + full_thick + 2
            temp = pygame.Surface((w, h), pygame.SRCALPHA)
            off_x, off_y = min(ix1, ix2) - full_thick // 2 - 1, min(iy1, iy2) - full_thick // 2 - 1
            pygame.draw.line(temp, (or_, og, ob, oa), (ix1 - off_x, iy1 - off_y), (ix2 - off_x, iy2 - off_y),
                             full_thick)
            pygame.draw.line(temp, (r, g, b_col, a_col), (ix1 - off_x, iy1 - off_y), (ix2 - off_x, iy2 - off_y),
                             line_thick)
            self.screen.blit(temp, (off_x, off_y))
        @profile("draw_poly_filled_and_outline", "_draw_physics_shapes")
        def draw_poly_filled_and_outline(vertices, color, outline_col, thickness):
            if len(vertices) < 3: return
            xs, ys = zip(*vertices)
            obj_rect = pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            if not obj_rect.colliderect(clip_rect): return
            int_vertices = [(safe_coord(vx), safe_coord(vy)) for vx, vy in vertices]
            r, g, b, a = color
            or_, og, ob, oa = outline_col
            # filled
            if a == 255:
                pygame.gfxdraw.filled_polygon(self.screen, int_vertices, (r, g, b))
            else:
                min_xp = min(v[0] for v in int_vertices)
                max_xp = max(v[0] for v in int_vertices)
                min_yp = min(v[1] for v in int_vertices)
                max_yp = max(v[1] for v in int_vertices)
                w, h = max_xp - min_xp + 2, max_yp - min_yp + 2
                if w > 0 and h > 0 and w <= 65535 and h <= 65535:
                    temp = pygame.Surface((w, h), pygame.SRCALPHA)
                    shifted = [(x - min_xp + 1, y - min_yp + 1) for x, y in int_vertices]
                    pygame.gfxdraw.filled_polygon(temp, shifted, (r, g, b, a))
                    self.screen.blit(temp, (min_xp - 1, min_yp - 1))
            # outline
            if oa == 255:
                for _ in range(thickness):
                    offset_verts = [(x + _, y) for x, y in int_vertices]  # simple inset; sufficient for 1px
                    pygame.gfxdraw.aapolygon(self.screen, offset_verts, (or_, og, ob))
            else:
                min_xp = min(v[0] for v in int_vertices)
                max_xp = max(v[0] for v in int_vertices)
                min_yp = min(v[1] for v in int_vertices)
                max_yp = max(v[1] for v in int_vertices)
                w, h = max_xp - min_xp + 2, max_yp - min_yp + 2
                if w > 0 and h > 0 and w <= 65535 and h <= 65535:
                    temp = pygame.Surface((w, h), pygame.SRCALPHA)
                    shifted = [(x - min_xp + 1, y - min_yp + 1) for x, y in int_vertices]
                    for _ in range(thickness):
                        pygame.gfxdraw.aapolygon(temp, shifted, (or_, og, ob, oa))
                    self.screen.blit(temp, (min_xp - 1, min_yp - 1))
        @profile("draw_segment_with_outline", "_draw_physics_shapes")
        def draw_segment_with_outline(a_scr, b_scr, radius, color, outline_col, thickness):
            ax, ay = a_scr
            bx, by = b_scr
            if not (clip_rect.collidepoint(ax, ay) or clip_rect.collidepoint(bx, by)):
                dx = bx - ax
                dy = by - ay
                lsq = dx * dx + dy * dy
                if lsq == 0: return
                t = max(0, min(1, ((clip_rect.x - ax) * dx + (clip_rect.y - ay) * dy) / lsq))
                cx, cy = ax + t * dx, ay + t * dy
                if not clip_rect.collidepoint(cx, cy): return
            ix1, iy1 = safe_coord(ax), safe_coord(ay)
            ix2, iy2 = safe_coord(bx), safe_coord(by)
            r, g, b_col, a_col = color
            or_, og, ob, oa = outline_col
            line_thickness = max(1, int(radius))
            if a_col == 255:
                pygame.draw.line(self.screen, (r, g, b_col), (ix1, iy1), (ix2, iy2), line_thickness)
            else:
                temp = pygame.Surface((abs(ix2 - ix1) + 4, abs(iy2 - iy1) + 4), pygame.SRCALPHA)
                off_x, off_y = min(ix1, ix2) - 2, min(iy1, iy2) - 2
                pygame.draw.line(temp, (r, g, b_col, a_col), (ix1 - off_x, iy1 - off_y), (ix2 - off_x, iy2 - off_y),
                                 line_thickness)
                self.screen.blit(temp, (off_x, off_y))
            # outline
            if oa == 255:
                pygame.draw.line(self.screen, (or_, og, ob), (ix1, iy1), (ix2, iy2),
                                 min(line_thickness + 2 * thickness, 32767))
                pygame.draw.line(self.screen, (r, g, b_col), (ix1, iy1), (ix2, iy2), line_thickness)
            else:
                full_thick = line_thickness + 2 * thickness
                temp = pygame.Surface((abs(ix2 - ix1) + full_thick + 2, abs(iy2 - iy1) + full_thick + 2),
                                      pygame.SRCALPHA)
                off_x = min(ix1, ix2) - full_thick // 2 - 1
                off_y = min(iy1, iy2) - full_thick // 2 - 1
                pygame.draw.line(temp, (or_, og, ob, oa), (ix1 - off_x, iy1 - off_y), (ix2 - off_x, iy2 - off_y),
                                 full_thick)
                pygame.draw.line(temp, (r, g, b_col, a_col), (ix1 - off_x, iy1 - off_y), (ix2 - off_x, iy2 - off_y),
                                 line_thickness)
                self.screen.blit(temp, (off_x, off_y))

        for shape in self.physics_manager.space.shapes:
            body = shape.body
            color = getattr(shape, 'color', self.default_color)
            if len(color) == 3: color = (*color, 255)

            if isinstance(shape, pymunk.Circle):
                world_pos = body.local_to_world(shape.offset)
                radius_px = shape.radius * self.camera.scaling
                self._draw_circle_opt(world_pos, radius_px, color, self.outline_color, self.outline_thickness)

            elif isinstance(shape, pymunk.Poly):
                vertices = [self.camera.world_to_screen(body.local_to_world(v)) for v in shape.get_vertices()]
                draw_poly_filled_and_outline(vertices, color, self.outline_color, self.outline_thickness)

            elif isinstance(shape, pymunk.Segment):
                a_world = body.local_to_world(shape.a)
                b_world = body.local_to_world(shape.b)
                a_screen = self.camera.world_to_screen(a_world)
                b_screen = self.camera.world_to_screen(b_world)
                radius_px = shape.radius * self.camera.scaling
                draw_segment_with_outline(a_screen, b_screen, radius_px, color, self.outline_color, self.outline_thickness)

    @profile("_get_scaled_texture_by_camera", "_draw_physics_shapes")
    def _get_scaled_texture_by_camera(self, path, base_scale=1.0):
        if not path:
            return None
        scale = self.camera.scaling * base_scale
        key = (path, round(scale, 3))
        if key not in self.texture_cache:
            base = self._get_texture(path)
            if not base:
                return None
            w, h = base.get_size()
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            self.texture_cache[key] = pygame.transform.smoothscale(base, (new_w, new_h))
        return self.texture_cache[key]

    def draw(self):
        dt = self.app.clock.get_time() / 1000.0
        start_time = pygame.time.get_ticks()
        theme = config.world.themes[config.world.current_theme]
        self.screen.fill(theme.background_color)
        self.cloud_renderer.draw()
        self.grid_manager.draw(self.screen)
        self.gizmos_manager.draw_debug_gizmos()
        # self.thermal_manager.draw_hover_temperature()
        self._draw_physics_shapes()
        self._draw_constraints()
        self.tool_manager.laser_processor.update()
        self.tool_manager.laser_processor.draw(self.screen, self.camera)
        self._draw_textured_bodies()
        self.gizmos_manager.draw()
        # self.thermal_manager.render_heatmap(self.screen)
        if self.script_system: self.script_system.draw(self.screen)
        self.ui_manager.draw(self.screen)
        self._draw_cursor_icon()
        self.app.debug_manager.draw_all_debug_info(self.screen, self.physics_manager, self.camera)
        if self.script_system: self._draw_script_info()
        pygame.display.flip()
        draw_ms = pygame.time.get_ticks() - start_time
        self.app.debug_manager.set_performance_counter("Draw Time", draw_ms)

        pygame.display.flip()
        draw_ms = pygame.time.get_ticks() - start_time
        self.app.debug_manager.set_performance_counter("Draw Time", draw_ms)

    def set_clouds_folder(self, folder):
        self.clouds.set_folder(folder)

    def _get_texture(self, path):
        if not path: return None
        if path not in self.texture_cache:
            try:
                self.texture_cache[path] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                self.texture_cache[path] = None
        return self.texture_cache[path]

    @profile("_draw_textured_bodies", "renderer")
    def _draw_textured_bodies(self):
        current_time = time.time()
        if current_time - self.last_texture_update > self.texture_update_interval:
            self._update_texture_cache()
            self.last_texture_update = current_time
        for body in self.physics_manager.space.bodies:
            tex = None
            if hasattr(body, 'texture_bytes') and body.texture_bytes is not None:
                size = getattr(body, 'texture_size', None)
                if size is None or not isinstance(size, (tuple, list)) or len(size) != 2:
                    continue
                width, height = size
                if width <= 0 or height <= 0: continue
                cache_key = (body.texture_bytes, size)
                if cache_key not in self.texture_cache:
                    self.texture_cache[cache_key] = bytes_to_surface(body.texture_bytes, size)
                tex = self.texture_cache[cache_key]
            elif hasattr(body, 'texture_path') and body.texture_path:
                tex = self._get_texture(body.texture_path)
            if not tex: continue
            scale_mult = getattr(body, 'texture_scale', 1.0)
            stretch = getattr(body, 'stretch_texture', True)
            rotation = getattr(body, 'texture_rotation', 0.0)
            mirror_x = getattr(body, 'texture_mirror_x', False)
            mirror_y = getattr(body, 'texture_mirror_y', False)
            texture_state = getattr(body, 'texture_state', None)
            texture_offset = getattr(body, 'texture_offset', (0, 0))
            if texture_state:
                processed_tex = self._apply_texture_state(tex, texture_state)
            else:
                processed_tex = tex
                if mirror_x or mirror_y:
                    processed_tex = pygame.transform.flip(processed_tex, mirror_x, mirror_y)
                if rotation != 0:
                    processed_tex = pygame.transform.rotozoom(processed_tex, rotation, 1.0)
            if any(isinstance(s, pymunk.Circle) for s in body.shapes):
                self._draw_circle_texture(body, processed_tex, scale_mult, stretch, texture_offset)
            elif any(isinstance(s, pymunk.Poly) for s in body.shapes):
                self._draw_poly_texture(body, processed_tex, stretch, scale_mult, texture_offset)

    def _apply_texture_state(self, tex, state: TextureState):
        processed = tex
        if state.mirror_x or state.mirror_y:
            processed = pygame.transform.flip(processed, state.mirror_x, state.mirror_y)
        if state.rotation != 0:
            processed = pygame.transform.rotozoom(processed, state.rotation, 1.0)
        return processed

    def _update_texture_cache(self):
        if len(self.texture_cache) > self.texture_cache_size:
            for key in list(self.texture_cache.keys())[:len(self.texture_cache) - self.texture_cache_size]:
                del self.texture_cache[key]

    def _draw_circle_texture(self, body, tex, scale_mult, stretch, offset):
        circle = next(s for s in body.shapes if isinstance(s, pymunk.Circle))
        radius_px = circle.radius * self.camera.scaling
        if radius_px <= 0: return
        diam = radius_px * 2
        pos = self.camera.world_to_screen(body.position)
        scaled_tex = pygame.transform.smoothscale(tex, (max(1, int(diam)), max(1, int(diam))))
        mask = pygame.Surface((scaled_tex.get_width(), scaled_tex.get_height()), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (scaled_tex.get_width() // 2, scaled_tex.get_height() // 2), int(radius_px))
        scaled_tex.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        angle_deg = math.degrees(-body.angle)
        if abs(angle_deg) > 0.1:
            rotated = pygame.transform.rotozoom(scaled_tex, angle_deg, 1.0)
            offset_x = offset[0] * self.camera.scaling
            offset_y = offset[1] * self.camera.scaling
            self.screen.blit(rotated, (pos[0] - rotated.get_width() / 2 + offset_x, pos[1] - rotated.get_height() / 2 + offset_y))
        else:
            offset_x = offset[0] * self.camera.scaling
            offset_y = offset[1] * self.camera.scaling
            self.screen.blit(scaled_tex, (pos[0] - scaled_tex.get_width() / 2 + offset_x, pos[1] - scaled_tex.get_height() / 2 + offset_y))

    def _draw_poly_texture(self, body, tex, stretch, scale_mult, offset):
        poly = next(s for s in body.shapes if isinstance(s, pymunk.Poly))
        local_verts = poly.get_vertices()
        if len(local_verts) < 3: return
        world_verts = [body.local_to_world(v) for v in local_verts]
        screen_verts = [self.camera.world_to_screen(v) for v in world_verts]
        if not screen_verts: return
        min_x = min(v[0] for v in screen_verts)
        max_x = max(v[0] for v in screen_verts)
        min_y = min(v[1] for v in screen_verts)
        max_y = max(v[1] for v in screen_verts)
        w_scr = max_x - min_x
        h_scr = max_y - min_y
        if w_scr <= 0 or h_scr <= 0: return
        if stretch:
            tex_surf = pygame.transform.smoothscale(tex, (max(1, int(w_scr)), max(1, int(h_scr))))
        else:
            tex_w, tex_h = tex.get_size()
            scale = min(w_scr / tex_w, h_scr / tex_h)
            scaled = pygame.transform.smoothscale_by(tex, scale)
            tex_surf = pygame.transform.smoothscale(scaled, (max(1, int(w_scr)), max(1, int(h_scr))))
        angle_deg = math.degrees(-body.angle)
        if abs(angle_deg) > 0.1:
            tex_surf = pygame.transform.rotozoom(tex_surf, angle_deg, 1.0)
        w_rot, h_rot = tex_surf.get_size()
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        offset_x = offset[0] * self.camera.scaling
        offset_y = offset[1] * self.camera.scaling
        temp_surf = pygame.Surface((w_rot, h_rot), pygame.SRCALPHA)
        temp_surf.blit(tex_surf, (0, 0))
        rel_offset_x = center_x - w_rot / 2
        rel_offset_y = center_y - h_rot / 2
        rel_verts = [(sx - rel_offset_x, sy - rel_offset_y) for sx, sy in screen_verts]
        mask = pygame.Surface((w_rot, h_rot), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), rel_verts)
        temp_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(temp_surf, (rel_offset_x + offset_x, rel_offset_y + offset_y))

    def _get_scaled_texture(self, path, scale):
        key = (path, round(scale, 3))
        if key not in self.texture_cache:
            base = self._get_texture(path)
            if not base: return None
            size = (int(base.get_width() * scale), int(base.get_height() * scale))
            self.texture_cache[key] = pygame.transform.smoothscale(base, size) if scale != 1.0 else base
        return self.texture_cache[key]

    def _draw_cursor_icon(self):
        pass
        # if self.ui_manager.manager.get_focus_set(): return
        # tool = self.input_handler.current_tool
        # if tool in self.ui_manager.tool_icons:
        #     icon = pygame.transform.smoothscale(self.ui_manager.tool_icons[tool], (32, 32))
        #     mouse = pygame.mouse.get_pos()
        #     self.screen.blit(icon, (mouse[0] + 30, mouse[1] - 20))

    def _draw_script_info(self):
        if not self.script_system: return
        x, y = self.screen.get_width() - 500, 10
        scripts = self.script_system.script_object_manager.get_all_script_objects()
        running = sum(1 for obj in scripts if obj.is_running)
        info = [f"Script System: Active", f"Total Scripts: {len(scripts)}", f"Running: {running}", f"IDLE: {'Running' if self.script_system.idle_integration.is_idle_running() else 'Stopped'}"]
        rect = pygame.Rect(x - 10, y - 5, 290, 80)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), rect)
        pygame.draw.rect(self.screen, (100, 100, 100), rect, 2)
        for i, line in enumerate(info):
            txt = self.app.font.render(line, True, (255, 255, 255))
            self.screen.blit(txt, (x, y + i * 18))