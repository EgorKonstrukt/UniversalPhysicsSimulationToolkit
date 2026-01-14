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

    @profile("_draw_constraints", "renderer")
    def _draw_constraints(self):
        cam_scale = self.camera.scaling
        if cam_scale > 100: return
        theme = config.world.themes[config.world.current_theme]
        default_color = (*getattr(theme, 'constraint_color', (200, 200, 255)), 200)
        margin, screen_w, screen_h = 2000, self.screen_w, self.screen_h
        clip_rect = pygame.Rect(-margin, -margin, screen_w + 2 * margin, screen_h + 2 * margin)
        safe_coord = lambda v: max(-32768, min(32767, int(round(v))))
        spring_tex_path = getattr(config.rendering, 'spring_texture', '')
        use_segmented = getattr(config.rendering, 'spring_texture_segmented', True)
        tile_world_width = getattr(config.rendering, 'spring_texture_tile_world_width', 20.0)
        base_scaled = seg_cache = None
        if spring_tex_path and use_segmented:
            base_tex = self._get_texture(spring_tex_path)
            if base_tex:
                tex_h = base_tex.get_height()
                scaled_h = max(1, int(tex_h * cam_scale / 15))
                base_scaled = pygame.transform.smoothscale(base_tex, (base_tex.get_width(), scaled_h)) if tex_h != scaled_h else base_tex
                seg_cache = {}
        screen, draw_line = self.screen, pygame.draw.line
        for constraint in self.physics_manager.space.constraints:
            if not isinstance(constraint, (pymunk.DampedSpring, pymunk.PinJoint, pymunk.SlideJoint, pymunk.PivotJoint)) or getattr(constraint, 'hidden', False): continue
            a_world = constraint.a.local_to_world(constraint.anchor_a)
            b_world = constraint.b.local_to_world(constraint.anchor_b)
            a_scr = self.camera.world_to_screen(a_world)
            b_scr = self.camera.world_to_screen(b_world)
            dx, dy = b_scr[0] - a_scr[0], b_scr[1] - a_scr[1]
            if not (clip_rect.collidepoint(a_scr) or clip_rect.collidepoint(b_scr)):
                lsq = dx * dx + dy * dy
                if lsq == 0: continue
                t = ((clip_rect.x - a_scr[0]) * dx + (clip_rect.y - a_scr[1]) * dy) / lsq
                t = max(0.0, min(1.0, t))
                cx, cy = a_scr[0] + t * dx, a_scr[1] + t * dy
                if not clip_rect.collidepoint(cx, cy): continue
            constraint_color = getattr(constraint, 'color', default_color)
            if len(constraint_color) == 3: constraint_color = (*constraint_color, 200)
            if isinstance(constraint, pymunk.DampedSpring) and base_scaled is not None:
                rest_len, curr_len = constraint.rest_length, (b_world - a_world).length
                if rest_len <= 0.1 or curr_len <= 0.1: continue
                screen_len = math.hypot(dx, dy)
                if screen_len < 1e-3: continue
                num_segments = max(1, int(round(rest_len / tile_world_width)))
                seg_len_scr = screen_len / num_segments
                angle = math.atan2(dy, dx)
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                color_rgb = constraint_color[:3]
                for i in range(num_segments):
                    seg_x0 = a_scr[0] + i * seg_len_scr * cos_a
                    seg_y0 = a_scr[1] + i * seg_len_scr * sin_a
                    key = (round(seg_len_scr, 1), round(angle, 2))
                    if key not in seg_cache:
                        stretched = pygame.transform.smoothscale(base_scaled, (max(1, int(seg_len_scr)), base_scaled.get_height()))
                        rotated = pygame.transform.rotate(stretched, math.degrees(-angle))
                        seg_cache[key] = rotated
                    sprite = seg_cache[key]
                    colored = sprite.copy()
                    colored.fill((*color_rgb, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    cx = seg_x0 + seg_len_scr * cos_a * 0.5
                    cy = seg_y0 + seg_len_scr * sin_a * 0.5
                    screen.blit(colored, (int(cx - colored.get_width() // 2), int(cy - colored.get_height() // 2)))
            else:
                width = max(1, int(2 * cam_scale))
                draw_line(screen, constraint_color[:3], a_scr, b_scr, width)
            for anchor_scr, tex_key in [(a_scr, 'spring_point_a_texture'), (b_scr, 'spring_point_b_texture')]:
                tex_path = getattr(config.rendering, tex_key, '')
                if tex_path:
                    pt_tex = self._get_scaled_texture(tex_path, 0.1 * cam_scale)
                    if pt_tex: screen.blit(pt_tex, (anchor_scr[0] - pt_tex.get_width() // 2, anchor_scr[1] - pt_tex.get_height() // 2))
                else:
                    r = max(1, int(1 * cam_scale))
                    x, y = safe_coord(anchor_scr[0]), safe_coord(anchor_scr[1])
                    pygame.gfxdraw.filled_circle(screen, x, y, r, constraint_color)
                    pygame.gfxdraw.aacircle(screen, x, y, r, (50, 50, 50))

    def safe_coord(self, v): return max(self.INT16_MIN, min(self.INT16_MAX, int(round(v))))

    @profile("_draw_physics_shapes", "renderer")
    def _draw_physics_shapes(self):
        screen, camera, clip, safe = self.screen, self.camera, self.clip_rect, self.safe_coord
        cam_scale = camera.scaling
        circles, polys, segments = [], [], []
        space_shapes = self.physics_manager.space.shapes
        for shape in space_shapes:
            if not hasattr(shape, 'color'): continue
            body = shape.body
            color = getattr(shape, 'color', getattr(body, 'color', (200, 200, 200, 255)))
            if len(color) == 3: color = (*color, 255)
            if isinstance(shape, pymunk.Circle):
                world_pos = body.local_to_world(shape.offset)
                if not (math.isfinite(world_pos.x) and math.isfinite(world_pos.y)): continue
                scr_x, scr_y = camera.world_to_screen(world_pos)
                if not (math.isfinite(scr_x) and math.isfinite(scr_y)): continue
                r_px = shape.radius * cam_scale
                if r_px <= 0: continue
                dx = max(clip.x, min(scr_x, clip.x + clip.w)) - scr_x
                dy = max(clip.y, min(scr_y, clip.y + clip.h)) - scr_y
                if dx * dx + dy * dy > r_px * r_px: continue
                circles.append((scr_x, scr_y, r_px, color, body.angle))
            elif isinstance(shape, pymunk.Poly):
                verts = [camera.world_to_screen(body.local_to_world(v)) for v in shape.get_vertices()]
                valid_verts = [(x, y) for x, y in verts if math.isfinite(x) and math.isfinite(y)]
                if len(valid_verts) < 3: continue
                try:
                    xs, ys = zip(*valid_verts)
                    min_x, max_x = min(xs), max(xs)
                    min_y, max_y = min(ys), max(ys)
                    if not (math.isfinite(min_x) and math.isfinite(max_x) and math.isfinite(min_y) and math.isfinite(
                            max_y)):
                        continue
                    obj_rect = pygame.Rect(int(min_x), int(min_y), int(max_x - min_x) + 1, int(max_y - min_y) + 1)
                except (ValueError, TypeError):
                    continue
                if not obj_rect.colliderect(clip): continue
                polys.append(([(safe(x), safe(y)) for x, y in valid_verts], color))
            elif isinstance(shape, pymunk.Segment):
                a_world, b_world = body.local_to_world(shape.a), body.local_to_world(shape.b)
                if not all(math.isfinite(v) for v in (a_world.x, a_world.y, b_world.x, b_world.y)): continue
                a_scr, b_scr = camera.world_to_screen(a_world), camera.world_to_screen(b_world)
                if not all(math.isfinite(v) for v in (*a_scr, *b_scr)): continue
                if not (clip.collidepoint(*a_scr) or clip.collidepoint(*b_scr)):
                    dx, dy = b_scr[0] - a_scr[0], b_scr[1] - a_scr[1]
                    lsq = dx * dx + dy * dy
                    if lsq == 0: continue
                    t = max(0, min(1, ((clip.x - a_scr[0]) * dx + (clip.y - a_scr[1]) * dy) / lsq))
                    cx, cy = a_scr[0] + t * dx, a_scr[1] + t * dy
                    if not clip.collidepoint(cx, cy): continue
                r_px = shape.radius * cam_scale
                segments.append((a_scr[0], a_scr[1], b_scr[0], b_scr[1], r_px, color))
        outline, othick = self.outline_color, self.outline_thickness
        gfx_filled_circle = pygame.gfxdraw.filled_circle
        gfx_aacircle = pygame.gfxdraw.aacircle
        gfx_filled_polygon = pygame.gfxdraw.filled_polygon
        gfx_aapolygon = pygame.gfxdraw.aapolygon
        draw_line = pygame.draw.line
        for x, y, r, col, ang in circles:
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(r)): continue
            ix, iy, ir = safe(x), safe(y), min(self.INT16_MAX, max(0, int(r)))
            if ir <= 0: continue
            r8, g8, b8, a8 = col
            or8, og8, ob8, oa8 = outline
            if a8 == 255:
                gfx_filled_circle(screen, ix, iy, ir, (r8, g8, b8))
                for t in range(othick): gfx_aacircle(screen, ix, iy, max(0, ir - t), (or8, og8, ob8))
            else:
                self._draw_circle_transparent(screen, ix, iy, ir, col, outline, othick)
            if ir > 3: self._draw_circle_pointer(screen, ix, iy, ir, -ang)
        for verts, col in polys:
            if not all(math.isfinite(vx) and math.isfinite(vy) for vx, vy in verts): continue
            r8, g8, b8, a8 = col
            or8, og8, ob8, oa8 = outline
            if a8 == 255:
                gfx_filled_polygon(screen, verts, (r8, g8, b8))
                gfx_aapolygon(screen, verts, (or8, og8, ob8))
            else:
                self._draw_poly_transparent(screen, verts, col, outline, othick)
        for x1, y1, x2, y2, r, col in segments:
            if not all(math.isfinite(v) for v in (x1, y1, x2, y2, r)): continue
            ix1, iy1, ix2, iy2 = safe(x1), safe(y1), safe(x2), safe(y2)
            thick = max(1, int(r))
            othick2 = thick + 2 * othick
            r8, g8, b8, a8 = col
            or8, og8, ob8, oa8 = outline
            if a8 == 255 and oa8 == 255:
                draw_line(screen, (or8, og8, ob8), (ix1, iy1), (ix2, iy2), othick2)
                draw_line(screen, (r8, g8, b8), (ix1, iy1), (ix2, iy2), thick)
            else:
                self._draw_segment_transparent(screen, ix1, iy1, ix2, iy2, thick, othick2, col, outline)

    def _draw_circle_transparent(self, surf, ix, iy, ir, col, outline, othick):
        size = ir * 2 + 2
        if size > 65535 or size <= 0: return
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(temp, col, (ir + 1, ir + 1), ir)
        for t in range(othick): pygame.draw.circle(temp, outline, (ir + 1, ir + 1), ir - t, 1)
        surf.blit(temp, (ix - ir - 1, iy - ir - 1))

    def _draw_poly_transparent(self, surf, verts, col, outline, othick):
        if len(verts) < 3: return
        min_x = min(v[0] for v in verts)
        max_x = max(v[0] for v in verts)
        min_y = min(v[1] for v in verts)
        max_y = max(v[1] for v in verts)
        w, h = max_x - min_x + 2, max_y - min_y + 2
        if w <= 0 or h <= 0 or w > 65535 or h > 65535: return
        temp = pygame.Surface((w, h), pygame.SRCALPHA)
        shifted = [(x - min_x + 1, y - min_y + 1) for x, y in verts]
        pygame.draw.polygon(temp, col, shifted)
        pygame.draw.polygon(temp, outline, shifted, othick)
        surf.blit(temp, (min_x - 1, min_y - 1))

    def _draw_segment_transparent(self, surf, x1, y1, x2, y2, thick, othick2, col, outline):
        w = int(abs(x2 - x1) + othick2 + 2)
        h = int(abs(y2 - y1) + othick2 + 2)
        if w <= 0 or h <= 0 or w > 65535 or h > 65535: return
        temp = pygame.Surface((w, h), pygame.SRCALPHA)
        ox = min(x1, x2) - othick2 // 2 - 1
        oy = min(y1, y2) - othick2 // 2 - 1
        pygame.draw.line(temp, outline, (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), othick2)
        pygame.draw.line(temp, col, (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), thick)
        surf.blit(temp, (ox, oy))

    def _draw_circle_pointer(self, surf, ix, iy, ir, angle):
        if not config.rendering.draw_circle_pointer:
            return
        plen = ir
        wa = math.radians(20)
        ca, sa = math.cos(angle), math.sin(angle)
        tip = (ix + int(ca * plen), iy + int(sa * plen))
        lft = (ix + int(math.cos(angle - wa / 2) * plen), iy + int(math.sin(angle - wa / 2) * plen))
        rgt = (ix + int(math.cos(angle + wa / 2) * plen), iy + int(math.sin(angle + wa / 2) * plen))
        wedge = [(ix, iy), lft, rgt]
        if all(self.INT16_MIN <= x <= self.INT16_MAX and self.INT16_MIN <= y <= self.INT16_MAX for x, y in wedge):
            pygame.gfxdraw.filled_polygon(surf, wedge, (0, 0, 0, 140))
            pygame.gfxdraw.aapolygon(surf, wedge, (0, 0, 0, 140))

    @profile("_get_scaled_texture_by_camera", "_draw_physics_shapes")
    def _get_scaled_texture_by_camera(self, path, base_scale=1.0):
        if not path: return None
        scale = self.camera.scaling * base_scale
        key = (path, round(scale, 3))
        if key not in self.texture_cache:
            base = self._get_texture(path)
            if not base: return None
            w, h = base.get_size()
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            self.texture_cache[key] = pygame.transform.smoothscale(base, (new_w, new_h))
        return self.texture_cache[key]

    @profile("draw", "renderer")
    def draw(self):
        start_time = pygame.time.get_ticks()
        theme = config.world.themes[config.world.current_theme]
        self.screen.fill(theme.background_color)
        self.gizmos_manager.draw_debug_gizmos()
        self._draw_physics_shapes()
        self._draw_constraints()
        self.tool_manager.laser_processor.update()
        self.tool_manager.laser_processor.draw(self.screen, self.camera)
        self._draw_textured_bodies()
        if hasattr(self.ui_manager.app, 'console_handler'): self.ui_manager.app.console_handler.draw_graph()
        self.grid_manager.draw(self.screen)
        self.gizmos_manager.draw()
        if self.script_system: self.script_system.draw(self.screen)
        if self.ui_manager.app.plugin_manager: self.ui_manager.app.plugin_manager.draw()
        self.ui_manager.draw(self.screen)
        self._draw_cursor_icon()
        self.app.debug_manager.draw_all_debug_info(self.screen, self.physics_manager, self.camera)
        if self.script_system: self._draw_script_info()
        pygame.display.flip()
        draw_ms = pygame.time.get_ticks() - start_time
        self.app.debug_manager.set_performance_counter("Draw Time", draw_ms)

    def set_clouds_folder(self, folder): self.clouds.set_folder(folder)

    def _get_texture(self, path):
        if not path: return None
        if path not in self.texture_cache:
            try: self.texture_cache[path] = pygame.image.load(path).convert_alpha()
            except pygame.error: self.texture_cache[path] = None
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
                if not (size and isinstance(size, (tuple, list)) and len(size) == 2): continue
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
            processed_tex = tex
            if texture_state:
                processed_tex = self._apply_texture_state(tex, texture_state)
            else:
                if mirror_x or mirror_y: processed_tex = pygame.transform.flip(processed_tex, mirror_x, mirror_y)
                if rotation != 0: processed_tex = pygame.transform.rotozoom(processed_tex, rotation, 1.0)
            if any(isinstance(s, pymunk.Circle) for s in body.shapes):
                self._draw_circle_texture(body, processed_tex, scale_mult, stretch, texture_offset)
            elif any(isinstance(s, pymunk.Poly) for s in body.shapes):
                self._draw_poly_texture(body, processed_tex, stretch, scale_mult, texture_offset)

    def _apply_texture_state(self, tex, state: TextureState):
        processed = tex
        if state.mirror_x or state.mirror_y: processed = pygame.transform.flip(processed, state.mirror_x, state.mirror_y)
        if state.rotation != 0: processed = pygame.transform.rotozoom(processed, state.rotation, 1.0)
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
        angle_deg = math.degrees(body.angle)
        offset_x = offset[0] * self.camera.scaling
        offset_y = offset[1] * self.camera.scaling
        if abs(angle_deg) > 0.1:
            rotated = pygame.transform.rotozoom(scaled_tex, angle_deg, 1.0)
            self.screen.blit(rotated, (pos[0] - rotated.get_width() / 2 + offset_x, pos[1] - rotated.get_height() / 2 + offset_y))
        else:
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
        angle_deg = math.degrees(body.angle)
        if abs(angle_deg) > 0.1: tex_surf = pygame.transform.rotozoom(tex_surf, angle_deg, 1.0)
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

    def _draw_cursor_icon(self): pass

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