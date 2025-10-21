import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict, Callable

import pygame
import pygame.gfxdraw

from UPST.config import Config
from UPST.modules.profiler import profile


class GizmoType(Enum):
    POINT = "point"
    LINE = "line"
    CIRCLE = "circle"
    RECT = "rect"
    ARROW = "arrow"
    CROSS = "cross"
    SPHERE = "sphere"
    CUBE = "cube"
    TEXT = "text"
    BUTTON = "button"


@dataclass
class GizmoData:
    gizmo_type: GizmoType
    position: Tuple[float, float]
    color: Tuple[int, int, int] = (255, 255, 255)
    background_color: Optional[Tuple[int, int, int, int]] = None
    pressed_background_color: Optional[Tuple[int, int, int, int]] = None
    border_thickness: int = 2
    collision: bool = False
    size: float = 1.0
    duration: float = 0.0
    text: str = ""
    end_position: Optional[Tuple[float, float]] = None
    width: float = 120.0
    height: float = 40.0
    filled: bool = True
    thickness: int = 1
    alpha: int = 255
    layer: int = 0
    world_space: bool = True
    font_size: int = 18
    font_name: str = "Consolas"
    font_world_space: bool = False
    cull_distance: float = -1.0
    cull_bounds: Optional[Tuple[float, float, float, float]] = None
    _screen_pos: Optional[Tuple[int, int]] = None
    _screen_size: Optional[float] = None
    _is_visible: Optional[bool] = None
    _text_surface_key: Optional[Tuple[str, Tuple[int, int, int], str, int]] = None
    on_click: Optional[Callable[[], None]] = None
    unique_id: Optional[str] = None


class GizmosManager:
    def __init__(self, camera, screen):
        self.camera = camera
        self.screen = screen
        self.gizmos: List[GizmoData] = []
        self.persistent_gizmos: List[GizmoData] = []
        self.unique_gizmos: Dict[str, GizmoData] = {}
        self.used_unique_gizmos: set = set()
        self.enabled = True
        self.font_cache: Dict[Tuple[str, int], pygame.font.Font] = {}
        self.text_cache: Dict[Tuple[str, Tuple[int, int, int], str, int], pygame.Surface] = {}
        self.time_accumulator = 0.0
        self.occlusion_culling_enabled = True
        self.frustum_culling_enabled = True
        self.distance_culling_enabled = True
        self.cull_margin = 50.0
        self.stats = {'total_gizmos': 0, 'culled_frustum': 0, 'culled_distance': 0, 'drawn_gizmos': 0}
        self.colors = {'white': (255, 255, 255), 'black': (0, 0, 0), 'red': (255, 0, 0), 'green': (0, 255, 0),
                       'blue': (0, 0, 255), 'yellow': (255, 255, 0), 'cyan': (0, 255, 255), 'magenta': (255, 0, 255),
                       'gray': (128, 128, 128), 'orange': (255, 165, 0), 'purple': (128, 0, 128)}
        self._screen_width = screen.get_width()
        self._screen_height = screen.get_height()
        self._half_screen_width = self._screen_width // 2
        self._half_screen_height = self._screen_height // 2
        self._alpha_surfaces: Dict[int, pygame.Surface] = {}
        self._alpha_surface_frame: Dict[int, int] = {}
        self._frame_id = 0
        self._last_camera_pos = None
        self._last_camera_scale = None
        self._visibility_cache_valid = False
        self._point_cache = {}
        self._line_cache = {}
        self._circle_cache = {}
        self._rect_cache = {}

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        mx, my = event.pos
        all_gizmos = list(self.unique_gizmos.values()) + self.gizmos + self.persistent_gizmos
        for g in reversed(all_gizmos):
            if g.gizmo_type != GizmoType.BUTTON or g.on_click is None:
                continue
            self._update_gizmo_cache(g)
            w = int(g.width * (self.camera.target_scaling if g.world_space else 1))
            h = int(g.height * (self.camera.target_scaling if g.world_space else 1))
            r = pygame.Rect(0, 0, w, h)
            sx, sy = g._screen_pos
            r.center = (sx, sy)
            if r.collidepoint(mx, my):
                g.on_click()
                break

    def get_font(self, font_name: str, font_size: int) -> pygame.font.Font:
        key = (font_name, font_size)
        if key not in self.font_cache:
            try:
                self.font_cache[key] = pygame.font.SysFont(font_name, font_size)
            except:
                self.font_cache[key] = pygame.font.SysFont(None, font_size)
        return self.font_cache[key]

    def _get_text_surface(self, text: str, color: Tuple[int, int, int], font_name: str,
                          font_size: int) -> pygame.Surface:
        key = (text, color, font_name, font_size)
        if key not in self.text_cache:
            font = self.get_font(font_name, font_size)
            self.text_cache[key] = font.render(text, True, color)
        return self.text_cache[key]

    def update(self, delta_time: float):
        self.time_accumulator += delta_time
        current_time = self.time_accumulator
        self.gizmos = [g for g in self.gizmos if g.duration <= 0 or current_time - g.duration < 1.0]

        unused_keys = set(self.unique_gizmos.keys()) - self.used_unique_gizmos
        for key in unused_keys:
            del self.unique_gizmos[key]

        self.used_unique_gizmos.clear()

        camera_pos = self.camera.screen_to_world((self._half_screen_width, self._half_screen_height))
        camera_scale = self.camera.target_scaling
        if self._last_camera_pos != camera_pos or self._last_camera_scale != camera_scale:
            self._invalidate_visibility_cache()
            self._last_camera_pos = camera_pos
            self._last_camera_scale = camera_scale

    def _invalidate_visibility_cache(self):
        self._visibility_cache_valid = False
        all_gizmos = list(self.unique_gizmos.values()) + self.gizmos + self.persistent_gizmos
        for gizmo in all_gizmos:
            gizmo._screen_pos = None
            gizmo._screen_size = None
            gizmo._is_visible = None

    @profile("_update_gizmo_cache", "gizmos")
    def _update_gizmo_cache(self, gizmo: GizmoData):
        if gizmo._screen_pos is None:
            gizmo._screen_pos = self.camera.world_to_screen(gizmo.position
                                                            ) if gizmo.world_space else gizmo.position
        if gizmo._screen_size is None:
            gizmo._screen_size = self._get_gizmo_screen_size(gizmo)

    @profile("is_gizmo_visible", "gizmos")
    def is_gizmo_visible(self, gizmo: GizmoData) -> bool:
        if not self.occlusion_culling_enabled:
            return True
        if gizmo._is_visible is not None:
            return gizmo._is_visible
        self._update_gizmo_cache(gizmo)
        if self.frustum_culling_enabled and gizmo.world_space:
            x, y = gizmo._screen_pos
            r = gizmo._screen_size
            if x + r < -self.cull_margin or x - r > self._screen_width + self.cull_margin or y + r < -self.cull_margin or y - r > self._screen_height + self.cull_margin:
                gizmo._is_visible = False
                self.stats['culled_frustum'] += 1
                return False
        if self.distance_culling_enabled and gizmo.cull_distance > 0 and gizmo.world_space:
            dx = gizmo.position[0] - self._last_camera_pos[0]
            dy = gizmo.position[1] - self._last_camera_pos[1]
            if dx * dx + dy * dy > gizmo.cull_distance * gizmo.cull_distance:
                gizmo._is_visible = False
                self.stats['culled_distance'] += 1
                return False
        if gizmo.cull_bounds:
            min_x, min_y, max_x, max_y = gizmo.cull_bounds
            if gizmo.position[0] < min_x or gizmo.position[0] > max_x or gizmo.position[1] < min_y or gizmo.position[
                1] > max_y:
                gizmo._is_visible = False
                return False
        gizmo._is_visible = True
        return True

    def _get_gizmo_screen_size(self, gizmo: GizmoData) -> float:
        scale = self.camera.target_scaling if gizmo.world_space else 1.0
        if gizmo.gizmo_type in (GizmoType.POINT, GizmoType.CIRCLE, GizmoType.CROSS):
            return gizmo.size * scale
        if gizmo.gizmo_type == GizmoType.RECT:
            return max(gizmo.width, gizmo.height) * scale * 0.5
        if gizmo.gizmo_type in (GizmoType.LINE, GizmoType.ARROW) and gizmo.end_position:
            dx = gizmo.end_position[0] - gizmo.position[0]
            dy = gizmo.end_position[1] - gizmo.position[1]
            return math.hypot(dx, dy) * scale * 0.5
        if gizmo.gizmo_type == GizmoType.TEXT:
            fs = gizmo.font_size * (scale if gizmo.font_world_space else 1.0)
            return fs * len(gizmo.text) * 0.3
        return 10.0

    def _get_temp_surface(self, alpha: int) -> pygame.Surface:
        if alpha not in self._alpha_surfaces:
            self._alpha_surfaces[alpha] = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            self._alpha_surface_frame[alpha] = -1
        if self._alpha_surface_frame[alpha] != self._frame_id:
            self._alpha_surfaces[alpha].fill((0, 0, 0, 0))
            self._alpha_surface_frame[alpha] = self._frame_id
        return self._alpha_surfaces[alpha]

    @profile("gizmos_draw", "gizmos")
    def draw(self):
        if not self.enabled:
            return

        all_gizmos = list(self.unique_gizmos.values()) + self.gizmos + self.persistent_gizmos
        if not all_gizmos:
            return
        self._frame_id += 1
        all_gizmos.sort(key=lambda g: g.layer)
        draw_options = self.camera.get_draw_options(self.screen)
        self.stats = {
            'total_gizmos': len(all_gizmos),
            'culled_frustum': 0,
            'culled_distance': 0,
            'culled_occlusion': 0,
            'drawn_gizmos': 0
        }
        alpha_used = set()
        texts = []
        others = []
        is_visible = self.is_gizmo_visible
        append_text = texts.append
        append_other = others.append
        for gizmo in all_gizmos:
            if not is_visible(gizmo):
                continue
            gt = gizmo.gizmo_type
            if gt is GizmoType.TEXT and gizmo.collision:
                append_text(gizmo)
            else:
                append_other(gizmo)
        texts.sort(key=lambda g: (g._screen_pos[1], g._screen_pos[0]))
        cell_size = 64
        grid = {}
        max_collisions = 8
        screen_rect = pygame.Rect(0, 0, self._screen_width, self._screen_height)
        for g in texts:
            size = int(g.font_size * self.camera.target_scaling) if (
                    g.font_world_space and g.world_space) else g.font_size
            surf = self._get_text_surface(g.text, g.color, g.font_name, size)
            rect = surf.get_rect(center=(int(g._screen_pos[0]), int(g._screen_pos[1])))
            if not rect.colliderect(screen_rect):
                self.stats['culled_occlusion'] += 1
                g.collision = False
                continue
            w2, h2 = rect.width >> 1, rect.height >> 1
            cx = min(max(rect.centerx, w2), self._screen_width - w2)
            cy = min(max(rect.centery, h2), self._screen_height - h2)
            rect.center = (cx, cy)
            collision_attempts = 0
            while collision_attempts < max_collisions:
                bx, by = rect.centerx // cell_size, rect.centery // cell_size
                bucket = grid.get((bx, by))
                if bucket is None:
                    break
                overlap_found = False
                for r in bucket:
                    if rect.colliderect(r):
                        rect.top = r.bottom + 2
                        overlap_found = True
                        break
                if not overlap_found:
                    break
                collision_attempts += 1
            if collision_attempts == max_collisions:
                g.collision = False
                self.stats['culled_occlusion'] += 1
                continue
            g._adjusted_screen_pos = rect.center
            left_cell = rect.left // cell_size
            right_cell = rect.right // cell_size
            top_cell = rect.top // cell_size
            bottom_cell = rect.bottom // cell_size
            for ix in range(left_cell, right_cell + 1):
                for iy in range(top_cell, bottom_cell + 1):
                    grid.setdefault((ix, iy), []).append(rect)
        for g in others:
            self._draw_gizmo(g, draw_options, alpha_used)
        for g in texts:
            if not hasattr(g, '_adjusted_screen_pos'):
                continue
            pos = g._screen_pos
            adj = g._adjusted_screen_pos
            surf_target = self.screen if g.alpha == 255 else self._get_temp_surface(g.alpha)
            if g.alpha != 255:
                alpha_used.add(g.alpha)
            self._draw_line_gfx(surf_target, pos, adj, g.color, 2)
            size = int(g.font_size * self.camera.target_scaling) if (
                    g.font_world_space and g.world_space) else g.font_size
            surf = self._get_text_surface(g.text, g.color, g.font_name, size)
            r = surf.get_rect(center=adj)
            if g.background_color:
                bg = pygame.Surface((r.width + 4, r.height + 4), pygame.SRCALPHA)
                bg.fill(g.background_color)
                surf_target.blit(bg, (r.left - 2, r.top - 2))
            surf_target.blit(surf, r)
            self.stats['drawn_gizmos'] += 1
        for a in alpha_used:
            self.screen.blit(self._alpha_surfaces[a], (0, 0))

    @profile("_draw_line_gfx", "gizmos")
    def _draw_line_gfx(self, surface, start, end, color, thickness):
        x1, y1 = map(int, start)
        x2, y2 = map(int, end)
        if thickness <= 1:
            pygame.gfxdraw.line(surface, x1, y1, x2, y2, color)
        else:
            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length == 0:
                return
            nx = dy / length
            ny = -dx / length
            offset = thickness // 2
            for i in range(thickness):
                factor = i - offset
                ox = int(nx * factor)
                oy = int(ny * factor)
                lx1 = max(min(x1 + ox, 32767), -32768)
                ly1 = max(min(y1 + oy, 32767), -32768)
                lx2 = max(min(x2 + ox, 32767), -32768)
                ly2 = max(min(y2 + oy, 32767), -32768)
                color = tuple(int(min(255, max(0, c))) for c in color)
                pygame.gfxdraw.line(surface, lx1, ly1, lx2, ly2, color)

    @profile("_draw_gizmo", "gizmos")
    def _draw_gizmo(self, gizmo: GizmoData, draw_options, alpha_used):
        pos = gizmo._screen_pos
        surface = self.screen if gizmo.alpha == 255 else self._get_temp_surface(gizmo.alpha)
        if gizmo.alpha < 255:
            alpha_used.add(gizmo.alpha)
        color = gizmo.color
        scale = self.camera.target_scaling if gizmo.world_space else 1.0

        if gizmo.gizmo_type == GizmoType.POINT:
            r = int(gizmo.size * scale)
            if r > 0:
                pygame.gfxdraw.filled_circle(surface, int(pos[0]), int(pos[1]), r, color)

        elif gizmo.gizmo_type == GizmoType.LINE and gizmo.end_position:
            end_screen = self.camera.world_to_screen(gizmo.end_position) if gizmo.world_space else gizmo.end_position
            self._draw_line_gfx(surface, pos, end_screen, color, gizmo.thickness)

        elif gizmo.gizmo_type == GizmoType.CIRCLE:
            r = int(gizmo.size * scale)
            self._draw_circle_gfx(surface, pos, r, color, gizmo.filled, gizmo.thickness)

        elif gizmo.gizmo_type == GizmoType.RECT:
            w = int(gizmo.width * scale)
            h = int(gizmo.height * scale)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = pos
            self._draw_rect_gfx(surface, rect, color, gizmo.filled, gizmo.thickness)

        elif gizmo.gizmo_type == GizmoType.ARROW and gizmo.end_position:
            end_screen = self.camera.world_to_screen(gizmo.end_position) if gizmo.world_space else gizmo.end_position
            self._draw_line_gfx(surface, pos, end_screen, color, gizmo.thickness)
            dx = end_screen[0] - pos[0]
            dy = end_screen[1] - pos[1]
            length = math.hypot(dx, dy)
            if length > 0:
                nx, ny = dx / length, dy / length
                arrow_size = min(length * 0.3, 20)
                left = (end_screen[0] - arrow_size * (nx * 0.8 + ny * 0.6),
                        end_screen[1] - arrow_size * (ny * 0.8 - nx * 0.6))
                right = (end_screen[0] - arrow_size * (nx * 0.8 - ny * 0.6),
                         end_screen[1] - arrow_size * (ny * 0.8 + nx * 0.6))
                self._draw_line_gfx(surface, end_screen, left, color, gizmo.thickness)
                self._draw_line_gfx(surface, end_screen, right, color, gizmo.thickness)

        elif gizmo.gizmo_type == GizmoType.CROSS:
            s = gizmo.size * scale
            h = s * 0.5
            self._draw_line_gfx(surface, (pos[0] - h, pos[1]), (pos[0] + h, pos[1]), color, gizmo.thickness)
            self._draw_line_gfx(surface, (pos[0], pos[1] - h), (pos[0], pos[1] + h), color, gizmo.thickness)

        elif gizmo.gizmo_type == GizmoType.TEXT:
            font_size = int(gizmo.font_size * (scale if gizmo.font_world_space else 1.0))
            txt_surf = self._get_text_surface(gizmo.text, color, gizmo.font_name, font_size)
            surf_rect = txt_surf.get_rect(center=pos)
            if gizmo.background_color:
                bg = pygame.Surface((surf_rect.width + 4, surf_rect.height + 4), pygame.SRCALPHA)
                bg.fill(gizmo.background_color)
                surface.blit(bg, (surf_rect.left - 2, surf_rect.top - 2))
            surface.blit(txt_surf, surf_rect)

        elif gizmo.gizmo_type == GizmoType.BUTTON:
            w = int(gizmo.width * scale)
            h = int(gizmo.height * scale)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = pos
            mouse_pos = pygame.mouse.get_pos()
            is_pressed = pygame.mouse.get_pressed()[0] and rect.collidepoint(mouse_pos)
            bg_color = gizmo.pressed_background_color if is_pressed and gizmo.pressed_background_color else gizmo.background_color
            if bg_color:
                bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                bg_surf.fill(bg_color)
                surface.blit(bg_surf, rect.topleft)
            for i in range(gizmo.border_thickness):
                border_rect = pygame.Rect(rect.x - i, rect.y - i, rect.width + 2 * i, rect.height + 2 * i)
                pygame.draw.rect(surface, color, border_rect, 1)
            font_size = int(gizmo.font_size * (scale if gizmo.font_world_space else 1.0))
            txt_surf = self.get_font(gizmo.font_name, font_size).render(gizmo.text, True, color)
            txt_rect = txt_surf.get_rect(center=rect.center)
            surface.blit(txt_surf, txt_rect)
            self.stats['drawn_gizmos'] += 1
            return

        self.stats['drawn_gizmos'] += 1


    def clear(self):
        self.gizmos.clear()
        self._invalidate_visibility_cache()

    def clear_persistent(self):
        self.persistent_gizmos.clear()
        self._invalidate_visibility_cache()

    def clear_unique(self):
        self.unique_gizmos.clear()
        self._invalidate_visibility_cache()

    def toggle(self):
        self.enabled = not self.enabled

    def toggle_occlusion_culling(self):
        self.occlusion_culling_enabled = not self.occlusion_culling_enabled

    def toggle_frustum_culling(self):
        self.frustum_culling_enabled = not self.frustum_culling_enabled

    def toggle_distance_culling(self):
        self.distance_culling_enabled = not self.distance_culling_enabled

    def set_cull_margin(self, margin: float):
        self.cull_margin = margin

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()

    def _reuse_or_create_button(self, key: str, **kwargs) -> GizmoData:
        if key in self.unique_gizmos:
            g = self.unique_gizmos[key]
            g.position = kwargs["position"]
            g.text = kwargs["text"]
            g.color = kwargs["color"]
            g.background_color = kwargs["background_color"]
            g.pressed_background_color = kwargs["pressed_background_color"]
            g.border_thickness = kwargs["border_thickness"]
            g.width = kwargs["width"]
            g.height = kwargs["height"]
            g.filled = True
            g.font_size = kwargs["font_size"]
            g.font_name = kwargs["font_name"]
            g.font_world_space = kwargs["font_world_space"]
            g.layer = kwargs["layer"]
            g.world_space = kwargs["world_space"]
            g.on_click = kwargs["on_click"]
            g.cull_distance = kwargs["cull_distance"]
            return g
        g = GizmoData(
            gizmo_type=GizmoType.BUTTON,
            position=kwargs["position"],
            text=kwargs["text"],
            color=kwargs["color"],
            background_color=kwargs["background_color"],
            pressed_background_color=kwargs["pressed_background_color"],
            border_thickness=kwargs["border_thickness"],
            width=kwargs["width"],
            height=kwargs["height"],
            filled=True,
            font_size=kwargs["font_size"],
            font_name=kwargs["font_name"],
            font_world_space=kwargs["font_world_space"],
            layer=kwargs["layer"],
            world_space=kwargs["world_space"],
            on_click=kwargs["on_click"],
            cull_distance=kwargs["cull_distance"],
            unique_id=key
        )
        self.unique_gizmos[key] = g
        return g

    def draw_button(self, position: Tuple[float, float], text: str,
                    on_click: Callable[[], None],
                    width: float = 120, height: float = 40,
                    color='white',
                    background_color=(10, 10, 10, 255),
                    pressed_background_color=(100, 100, 100, 255),
                    border_thickness: int = 2,
                    layer=0, world_space=True, font_size=18, font_name="Consolas",
                    font_world_space=False, cull_distance=-1.0, unique_id: Optional[str] = None):
        key = unique_id if unique_id is not None else f"{hash((position, text, layer, world_space))}"
        self.used_unique_gizmos.add(key)
        cfg = {
            "position": position,
            "text": text,
            "color": self.colors.get(color, color) if isinstance(color, str) else color,
            "background_color": background_color,
            "pressed_background_color": pressed_background_color,
            "border_thickness": border_thickness,
            "width": width,
            "height": height,
            "font_size": font_size,
            "font_name": font_name,
            "font_world_space": font_world_space,
            "layer": layer,
            "world_space": world_space,
            "on_click": on_click,
            "cull_distance": cull_distance
        }
        self._reuse_or_create_button(key, **cfg)

    @profile("_draw_circle_gfx", "gizmos")
    def _draw_circle_gfx(self, surface, center, radius, color, filled, thickness):
        x, y = int(center[0]), int(center[1])
        r = int(radius)
        if r <= 0:
            return
        if filled:
            pygame.gfxdraw.filled_circle(surface, x, y, r, color)
        else:
            if thickness == 1:
                pygame.gfxdraw.circle(surface, x, y, r, color)
            else:
                for i in range(thickness):
                    if r - i > 0:
                        pygame.gfxdraw.circle(surface, x, y, r - i, color)

    @profile("_draw_rect_gfx", "gizmos")
    def _draw_rect_gfx(self, surface, rect, color, filled, thickness):
        x, y, w, h = int(rect.x), int(rect.y), int(rect.width), int(rect.height)
        if w <= 0 or h <= 0:
            return
        if filled:
            pygame.gfxdraw.box(surface, (x, y, w, h), color)
        else:
            if thickness == 1:
                pygame.gfxdraw.rectangle(surface, (x, y, w, h), color)
            else:
                for i in range(thickness):
                    pygame.gfxdraw.rectangle(surface, (x - i, y - i, w + 2 * i, h + 2 * i), color)

    @profile("_draw_arrow_gfx", "gizmos")
    def _draw_arrow_gfx(self, surface, start_pos, end_pos, color, thickness, draw_options, world_space):
        end_screen = self.camera.world_to_screen(end_pos) if world_space else end_pos
        self._draw_line_gfx(surface, start_pos, end_screen, color, thickness)
        dx = end_screen[0] - start_pos[0]
        dy = end_screen[1] - start_pos[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx = dx / length
        ny = dy / length
        arrow_size = min(length * 0.3, 20)
        left = (end_screen[0] - arrow_size * (nx * 0.8 + ny * 0.6),
                end_screen[1] - arrow_size * (ny * 0.8 - nx * 0.6))
        right = (end_screen[0] - arrow_size * (nx * 0.8 - ny * 0.6),
                 end_screen[1] - arrow_size * (ny * 0.8 + nx * 0.6))
        self._draw_line_gfx(surface, end_screen, left, color, thickness)
        self._draw_line_gfx(surface, end_screen, right, color, thickness)

    @profile("_draw_cross_gfx", "gizmos")
    def _draw_cross_gfx(self, surface, pos, color, size, thickness, world_space):
        s = size * self.camera.target_scaling if world_space else size
        h = s * 0.5
        self._draw_line_gfx(surface, (pos[0] - h, pos[1]), (pos[0] + h, pos[1]), color, thickness)
        self._draw_line_gfx(surface, (pos[0], pos[1] - h), (pos[0], pos[1] + h), color, thickness)

    @profile("draw_point", "gizmos")
    def draw_point(self, position: Tuple[float, float], color='white', size=3.0, duration=0.1, layer=0,
                   world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.POINT, position=position,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, size=size,
                      duration=duration, layer=layer, world_space=world_space, cull_distance=cull_distance,
                      cull_bounds=cull_bounds)
        self._add_gizmo(g)

    @profile("draw_line", "gizmos")
    def draw_line(self, start: Tuple[float, float], end: Tuple[float, float], color='white', thickness=1, duration=0.1,
                  layer=0, world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.LINE, position=start, end_position=end,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, thickness=thickness,
                      duration=duration, layer=layer, world_space=world_space, cull_distance=cull_distance,
                      cull_bounds=cull_bounds)
        self._add_gizmo(g)
    @profile("draw_circle", "gizmos")
    def draw_circle(self, center: Tuple[float, float], radius: float, color='white', filled=False, thickness=1,
                    duration=0.1, layer=0, world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.CIRCLE, position=center,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, size=radius,
                      filled=filled, thickness=thickness, duration=duration, layer=layer, world_space=world_space,
                      cull_distance=cull_distance, cull_bounds=cull_bounds)
        self._add_gizmo(g)
    @profile("draw_rect", "gizmos")
    def draw_rect(self, center: Tuple[float, float], width: float, height: float, color='white', filled=False,
                  thickness=1, duration=0.1, layer=0, world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.RECT, position=center,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, width=width,
                      height=height, filled=filled, thickness=thickness, duration=duration, layer=layer,
                      world_space=world_space, cull_distance=cull_distance, cull_bounds=cull_bounds)
        self._add_gizmo(g)
    @profile("draw_arrow", "gizmos")
    def draw_arrow(self, start: Tuple[float, float], end: Tuple[float, float], color='white', thickness=2, duration=0.1,
                   layer=0, world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.ARROW, position=start, end_position=end,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, thickness=thickness,
                      duration=duration, layer=layer, world_space=world_space, cull_distance=cull_distance,
                      cull_bounds=cull_bounds)
        self._add_gizmo(g)
    @profile("draw_cross", "gizmos")
    def draw_cross(self, center: Tuple[float, float], size: float, color='white', thickness=1, duration=0.1, layer=0,
                   world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.CROSS, position=center,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, size=size,
                      thickness=thickness, duration=duration, layer=layer, world_space=world_space,
                      cull_distance=cull_distance, cull_bounds=cull_bounds)
        self._add_gizmo(g)
    @profile("draw_text", "gizmos")
    def draw_text(self, position: Tuple[float, float], text: str, color='white',
                  background_color: Optional[Tuple[int, int, int, int]] = None,
                  duration=0.1, layer=0,
                  world_space=True,
                  font_name="Consolas", font_size=14, font_world_space=False, cull_distance=-1.0, cull_bounds=None,
                  collision=False,
                  ):
        g = GizmoData(
            gizmo_type=GizmoType.TEXT,
            position=position,
            text=text,
            color=self.colors.get(color, color) if isinstance(color, str) else color,
            duration=duration,
            layer=layer,
            world_space=world_space,
            font_name=font_name,
            font_size=font_size,
            font_world_space=font_world_space,
            cull_distance=cull_distance,
            cull_bounds=cull_bounds,
            background_color=background_color,
            collision=collision
        )
        self._add_gizmo(g)

    def _add_gizmo(self, gizmo: GizmoData):
        if gizmo.duration == -1:
            self.persistent_gizmos.append(gizmo)
        else:
            self.gizmos.append(gizmo)

    def draw_debug_gizmos(self):
        if not Config.debug.gizmos:
            return
        if hasattr(Gizmos, 'get_stats'):
            stats = Gizmos.get_stats()
            if stats:
                Gizmos.draw_text(
                    (500, 30),
                    f"Gizmos: {stats.get('drawn_gizmos', 0)}/{stats.get('total_gizmos', 0)}"
                    f"\nculled_frustum: {stats.get('culled_frustum', 0)}/{stats.get('culled_distance', 0)}",
                    'white',
                    font_size=16,
                    world_space=False,
                    duration=0.1,
                    font_world_space=False
                )


_gizmos_instance: Optional[GizmosManager] = None


def get_gizmos():
    return _gizmos_instance


def set_gizmos(gizmos_manager):
    global _gizmos_instance
    _gizmos_instance = gizmos_manager


class Gizmos:
    @staticmethod
    def draw_button(position: Tuple[float, float], text: str,
                    on_click: Callable[[], None],
                    width: float = 120, height: float = 40,
                    color='white',
                    background_color=(10, 10, 10, 255),
                    pressed_background_color=(100, 100, 100, 255),
                    border_thickness: int = 2,
                    layer=0, world_space=True, font_size=18, font_name="Consolas",
                    font_world_space: bool = False,
                    cull_distance=-1.0, unique_id: Optional[str] = None):
        if _gizmos_instance:
            _gizmos_instance.draw_button(position, text, on_click,
                                         width, height,
                                         color, background_color,
                                         pressed_background_color, border_thickness,
                                         layer, world_space, font_size, font_name,
                                         font_world_space, cull_distance, unique_id)

    @staticmethod
    def draw_point(position, color='white', size=3.0, duration=0.1, layer=0, world_space=True, cull_distance=-1.0,
                   cull_bounds=None):
        if _gizmos_instance:
            _gizmos_instance.draw_point(position, color, size, duration, layer, world_space, cull_distance, cull_bounds)

    @staticmethod
    def draw_line(start, end, color='white', thickness=1, duration=0.1, layer=0, world_space=True, cull_distance=-1.0,
                  cull_bounds=None):
        if _gizmos_instance:
            _gizmos_instance.draw_line(start, end, color, thickness, duration, layer, world_space, cull_distance,
                                       cull_bounds)

    @staticmethod
    def draw_circle(center, radius, color='white', filled=False, thickness=1, duration=0.1, layer=0, world_space=True,
                    cull_distance=-1.0, cull_bounds=None):
        if _gizmos_instance:
            _gizmos_instance.draw_circle(center, radius, color, filled, thickness, duration, layer, world_space,
                                         cull_distance, cull_bounds)

    @staticmethod
    def draw_rect(center, width, height, color='white', filled=False, thickness=1, duration=0.1, layer=0,
                  world_space=True, cull_distance=-1.0, cull_bounds=None):
        if _gizmos_instance:
            _gizmos_instance.draw_rect(center, width, height, color, filled, thickness, duration, layer, world_space,
                                       cull_distance, cull_bounds)

    @staticmethod
    def draw_arrow(start, end, color='white', thickness=2, duration=0.1, layer=0, world_space=True, cull_distance=-1.0,
                   cull_bounds=None):
        if _gizmos_instance:
            _gizmos_instance.draw_arrow(start, end, color, thickness, duration, layer, world_space, cull_distance,
                                        cull_bounds)

    @staticmethod
    def draw_cross(center, size, color='white', thickness=1, duration=0.1, layer=0, world_space=True,
                   cull_distance=-1.0, cull_bounds=None):
        if _gizmos_instance:
            _gizmos_instance.draw_cross(center, size, color, thickness, duration, layer, world_space, cull_distance,
                                        cull_bounds)

    @staticmethod
    def draw_text(position, text, color='white', background_color=(0, 0, 0, 0), duration=0.1, layer=0, world_space=True,
                  font_name="Consolas", font_size=14, font_world_space=False, cull_distance=-1.0, cull_bounds=None,
                  collision=False):
        if _gizmos_instance:
            _gizmos_instance.draw_text(position, text, color, background_color, duration, layer, world_space, font_name,
                                       font_size, font_world_space, cull_distance, cull_bounds, collision)

    @staticmethod
    def clear():
        if _gizmos_instance:
            _gizmos_instance.clear()

    @staticmethod
    def clear_persistent():
        if _gizmos_instance:
            _gizmos_instance.clear_persistent()

    @staticmethod
    def toggle():
        if _gizmos_instance:
            _gizmos_instance.toggle()

    @staticmethod
    def toggle_occlusion_culling():
        if _gizmos_instance:
            _gizmos_instance.toggle_occlusion_culling()

    @staticmethod
    def toggle_frustum_culling():
        if _gizmos_instance:
            _gizmos_instance.toggle_frustum_culling()

    @staticmethod
    def toggle_distance_culling():
        if _gizmos_instance:
            _gizmos_instance.toggle_distance_culling()

    @staticmethod
    def set_cull_margin(margin: float):
        if _gizmos_instance:
            _gizmos_instance.set_cull_margin(margin)

    @staticmethod
    def get_stats():
        if _gizmos_instance:
            return _gizmos_instance.get_stats()
        return {}
