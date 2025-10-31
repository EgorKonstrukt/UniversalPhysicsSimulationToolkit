import pygame
import math
import pymunk
import time
from UPST.config import config
from UPST.misc import bytes_to_surface
from UPST.modules.texture_processor import TextureProcessor, TextureState
from UPST.modules.profiler import profile, start_profiling, stop_profiling


class Renderer:
    def __init__(self, app, screen, camera, physics_manager, gizmos_manager,
                 grid_manager, input_handler, ui_manager, script_system=None):
        self.app = app
        self.screen = screen
        self.camera = camera
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

    def draw(self):
        start_time = pygame.time.get_ticks()
        theme = config.world.themes[config.world.current_theme]
        self.screen.fill(theme.background_color)

        self.grid_manager.draw(self.screen)
        self.gizmos_manager.draw_debug_gizmos()

        draw_opts = self.camera.get_draw_options(self.screen)
        self.physics_manager.space.debug_draw(draw_opts)

        if self.input_handler.creating_static_line:
            start = draw_opts.transform @ self.input_handler.static_line_start
            pygame.draw.line(self.screen, (255, 255, 255), start, pygame.mouse.get_pos(), 5)

        if self.input_handler.first_joint_body:
            pos = self.camera.world_to_screen(self.input_handler.first_joint_body.position)
            pygame.draw.line(self.screen, (255, 255, 0, 150), pos, pygame.mouse.get_pos(), 3)

        self._draw_textured_bodies()
        self.gizmos_manager.draw()

        if self.script_system:
            self.script_system.draw(self.screen)

        self.ui_manager.draw(self.screen)
        self._draw_cursor_icon()
        self.app.debug_manager.draw_all_debug_info(self.screen, self.physics_manager, self.camera)

        if self.script_system:
            self._draw_script_info()

        pygame.display.flip()
        draw_ms = pygame.time.get_ticks() - start_time
        self.app.debug_manager.set_performance_counter("Draw Time", draw_ms)

    def _get_texture(self, path):
        if not path:
            return None
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
                    print(f"Skipping body: missing or invalid texture_size: {size}")
                    continue
                width, height = size
                if width <= 0 or height <= 0:
                    continue
                cache_key = (body.texture_bytes, size)
                if cache_key not in self.texture_cache:
                    self.texture_cache[cache_key] = bytes_to_surface(body.texture_bytes, size)
                tex = self.texture_cache[cache_key]
            elif hasattr(body, 'texture_path') and body.texture_path:
                tex = self._get_texture(body.texture_path)
            if not tex:
                continue
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
                    processed_tex = pygame.transform.rotate(processed_tex, rotation)

            if any(isinstance(s, pymunk.Circle) for s in body.shapes):
                self._draw_circle_texture(body, processed_tex, scale_mult, stretch, texture_offset)
            elif any(isinstance(s, pymunk.Poly) for s in body.shapes):
                self._draw_poly_texture(body, processed_tex, stretch, scale_mult, texture_offset)

    def _apply_texture_state(self, tex, state: TextureState):
        processed = tex
        if state.mirror_x or state.mirror_y:
            processed = pygame.transform.flip(processed, state.mirror_x, state.mirror_y)
        if state.rotation != 0:
            processed = pygame.transform.rotate(processed, state.rotation)
        return processed

    def _update_texture_cache(self):
        if len(self.texture_cache) > self.texture_cache_size:
            for key in list(self.texture_cache.keys())[:len(self.texture_cache) - self.texture_cache_size]:
                del self.texture_cache[key]

    def _draw_circle_texture(self, body, tex, scale_mult, stretch, offset):
        circle = next(s for s in body.shapes if isinstance(s, pymunk.Circle))
        radius_px = int(circle.radius * self.camera.scaling)
        if radius_px <= 0: return
        diam = radius_px * 2
        pos = self.camera.world_to_screen(body.position)

        scaled_tex = pygame.transform.smoothscale(tex, (diam, diam))
        mask = pygame.Surface((diam, diam), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius_px, radius_px), radius_px)
        scaled_tex.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        angle_deg = math.degrees(-body.angle)
        if abs(angle_deg) > 0.1:
            rotated = pygame.transform.rotate(scaled_tex, angle_deg)
            w, h = rotated.get_size()
            offset_x = offset[0] * self.camera.scaling
            offset_y = offset[1] * self.camera.scaling
            self.screen.blit(rotated, (pos[0] - w // 2 + offset_x, pos[1] - h // 2 + offset_y))
        else:
            offset_x = offset[0] * self.camera.scaling
            offset_y = offset[1] * self.camera.scaling
            self.screen.blit(scaled_tex, (pos[0] - radius_px + offset_x, pos[1] - radius_px + offset_y))

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
        w_scr = int(max_x - min_x)
        h_scr = int(max_y - min_y)
        if w_scr <= 0 or h_scr <= 0: return

        if stretch:
            tex_surf = pygame.transform.smoothscale(tex, (w_scr, h_scr))
        else:
            tex_w, tex_h = tex.get_size()
            scale = min(w_scr / tex_w, h_scr / tex_h)
            tex_surf = pygame.transform.smoothscale_by(tex, scale)
            tex_surf = pygame.transform.smoothscale(tex_surf, (w_scr, h_scr))

        angle_deg = math.degrees(-body.angle)
        if abs(angle_deg) > 0.1:
            tex_surf = pygame.transform.rotate(tex_surf, angle_deg)

        w_rot, h_rot = tex_surf.get_size()
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        screen_pos = (center_x, center_y)

        offset_x = offset[0] * self.camera.scaling
        offset_y = offset[1] * self.camera.scaling

        temp_surf = pygame.Surface((w_rot, h_rot), pygame.SRCALPHA)
        temp_surf.blit(tex_surf, (0, 0))

        rel_offset_x = screen_pos[0] - w_rot // 2
        rel_offset_y = screen_pos[1] - h_rot // 2
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
        if self.ui_manager.manager.get_focus_set():
            return
        tool = self.input_handler.current_tool
        if tool in self.ui_manager.tool_icons:
            icon = pygame.transform.smoothscale(self.ui_manager.tool_icons[tool], (32, 32))
            mouse = pygame.mouse.get_pos()
            self.screen.blit(icon, (mouse[0] + 30, mouse[1] - 20))

    def _draw_script_info(self):
        if not self.script_system: return
        x, y = self.screen.get_width() - 500, 10
        scripts = self.script_system.script_object_manager.get_all_script_objects()
        running = sum(1 for obj in scripts if obj.is_running)
        info = [
            f"Script System: Active",
            f"Total Scripts: {len(scripts)}",
            f"Running: {running}",
            f"IDLE: {'Running' if self.script_system.idle_integration.is_idle_running() else 'Stopped'}"
        ]
        rect = pygame.Rect(x - 10, y - 5, 290, 80)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), rect)
        pygame.draw.rect(self.screen, (100, 100, 100), rect, 2)
        for i, line in enumerate(info):
            txt = self.app.font.render(line, True, (255, 255, 255))
            self.screen.blit(txt, (x, y + i * 18))