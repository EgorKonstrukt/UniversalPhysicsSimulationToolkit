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
        # self.thermal_manager = ThermalManager(physics_manager, camera)

    @profile("_draw_physics_shapes", "renderer")
    def _draw_physics_shapes(self):
        theme = config.world.themes[config.world.current_theme]
        default_color = (255, 255, 255)
        screen_w, screen_h = self.screen.get_size()
        margin = 2000
        clip_rect = pygame.Rect(-margin, -margin, screen_w + 2 * margin, screen_h + 2 * margin)
        INT16_MIN, INT16_MAX = -32768, 32767
        outline_color = (50, 50, 50, 180)
        outline_thickness = 1

        def safe_coord(v):
            return max(INT16_MIN, min(INT16_MAX, int(round(v))))

        def circle_intersects_rect(center, radius, rect):
            cx, cy = center
            rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
            closest_x = max(rx, min(cx, rx + rw))
            closest_y = max(ry, min(cy, ry + rh))
            dx, dy = cx - closest_x, cy - closest_y
            return dx * dx + dy * dy <= radius * radius

        def draw_circle_filled_and_outline(world_pos, radius_px, color, outline_col, thickness):
            screen_pos = self.camera.world_to_screen(world_pos)
            if radius_px <= 0: return
            if not circle_intersects_rect(screen_pos, radius_px, clip_rect): return
            ix, iy = safe_coord(screen_pos[0]), safe_coord(screen_pos[1])
            ir = min(int(radius_px), 32767)
            if ir <= 0: return
            r, g, b, a = color
            or_, og, ob, oa = outline_col

            # filled
            if a == 255:
                pygame.gfxdraw.filled_circle(self.screen, ix, iy, ir, (r, g, b))
            else:
                size = ir * 2 + 2
                if size <= 65535:
                    temp = pygame.Surface((size, size), pygame.SRCALPHA)
                    cx = ir + 1
                    pygame.gfxdraw.filled_circle(temp, cx, cx, ir, (r, g, b, a))
                    self.screen.blit(temp, (ix - ir - 1, iy - ir - 1))

            # outline
            if oa == 255:
                for _ in range(thickness):
                    pygame.gfxdraw.aacircle(self.screen, ix, iy, ir - _, (or_, og, ob))
            else:
                size = ir * 2 + 2
                if size <= 65535:
                    temp = pygame.Surface((size, size), pygame.SRCALPHA)
                    cx = ir + 1
                    for _ in range(thickness):
                        pygame.gfxdraw.aacircle(temp, cx, cx, ir - _, (or_, og, ob, oa))
                    self.screen.blit(temp, (ix - ir - 1, iy - ir - 1))

            # rotation indicator
            body_angle = body.angle  # radians
            pointer_len = int(ir * 1)
            wedge_angle = math.radians(20)  # 20 degrees wide
            cos_a = math.cos(body_angle)
            sin_a = math.sin(body_angle)
            tip_x = ix + int(cos_a * pointer_len)
            tip_y = iy + int(sin_a * pointer_len)
            left_angle = body_angle - wedge_angle / 2
            right_angle = body_angle + wedge_angle / 2
            left_x = ix + int(math.cos(left_angle) * pointer_len)
            left_y = iy + int(math.sin(left_angle) * pointer_len)
            right_x = ix + int(math.cos(right_angle) * pointer_len)
            right_y = iy + int(math.sin(right_angle) * pointer_len)

            # Draw triangle (wedge)
            wedge_points = [(ix, iy), (left_x, left_y), (right_x, right_y)]
            if all(INT16_MIN <= p[0] <= INT16_MAX and INT16_MIN <= p[1] <= INT16_MAX for p in wedge_points):
                pygame.gfxdraw.filled_polygon(self.screen, wedge_points, (0, 0, 0, 140))
                pygame.gfxdraw.aapolygon(self.screen, wedge_points, (0, 0, 0, 140))

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
            color = getattr(shape, 'color', default_color)
            if len(color) == 3: color = (*color, 255)

            if isinstance(shape, pymunk.Circle):
                world_pos = body.local_to_world(shape.offset)
                radius_px = shape.radius * self.camera.scaling
                draw_circle_filled_and_outline(world_pos, radius_px, color, outline_color, outline_thickness)

            elif isinstance(shape, pymunk.Poly):
                vertices = [self.camera.world_to_screen(body.local_to_world(v)) for v in shape.get_vertices()]
                draw_poly_filled_and_outline(vertices, color, outline_color, outline_thickness)

            elif isinstance(shape, pymunk.Segment):
                a_world = body.local_to_world(shape.a)
                b_world = body.local_to_world(shape.b)
                a_screen = self.camera.world_to_screen(a_world)
                b_screen = self.camera.world_to_screen(b_world)
                radius_px = shape.radius * self.camera.scaling
                draw_segment_with_outline(a_screen, b_screen, radius_px, color, outline_color, outline_thickness)

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