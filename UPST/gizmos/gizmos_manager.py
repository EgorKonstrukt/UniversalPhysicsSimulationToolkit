import math
import threading
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict, Callable, Any
import pygame
import pygame.gfxdraw
from concurrent.futures import ThreadPoolExecutor, as_completed

from UPST.config import config
from UPST.modules.profiler import profile, start_profiling, stop_profiling
from UPST.debug.debug_manager import Debug

class GizmoType(Enum):
    POINT = "point"
    LINE = "line"
    CIRCLE = "circle"
    RECT = "rect"
    ARROW = "arrow"
    CROSS = "cross"
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
    _adjusted_screen_pos: Optional[Tuple[int, int]] = None
    on_click: Optional[Callable[[], None]] = None
    unique_id: Optional[str] = None

def _process_gizmo_chunk(args):
    gizmos_chunk, cam_pos, cam_scale, screen_size, cull_margin, distance_culling_enabled = args
    visible = []
    for g in gizmos_chunk:
        if g.world_space:
            sx = (g.position[0] - cam_pos[0]) * cam_scale + screen_size[0] / 2
            sy = (g.position[1] - cam_pos[1]) * cam_scale + screen_size[1] / 2
        else:
            sx, sy = g.position[0], g.position[1]
        screen_pos = (int(sx), int(sy))
        if g.gizmo_type in (GizmoType.POINT, GizmoType.CIRCLE, GizmoType.CROSS):
            screen_size_val = g.size * cam_scale if g.world_space else g.size
        elif g.gizmo_type == GizmoType.RECT:
            screen_size_val = max(g.width, g.height) * (cam_scale if g.world_space else 1.0) * 0.5
        elif g.gizmo_type in (GizmoType.LINE, GizmoType.ARROW) and g.end_position:
            dx = g.end_position[0] - g.position[0]
            dy = g.end_position[1] - g.position[1]
            screen_size_val = math.hypot(dx, dy) * (cam_scale if g.world_space else 1.0) * 0.5
        elif g.gizmo_type == GizmoType.TEXT:
            fs = g.font_size * (cam_scale if (g.font_world_space and g.world_space) else 1.0)
            screen_size_val = fs * len(g.text) * 0.3
        else:
            screen_size_val = 10.0
        x, y = screen_pos
        r = screen_size_val
        w, h = screen_size
        if (x + r < -cull_margin or x - r > w + cull_margin or
                y + r < -cull_margin or y - r > h + cull_margin):
            continue
        if distance_culling_enabled and g.cull_distance > 0 and g.world_space:
            dx = g.position[0] - cam_pos[0]
            dy = g.position[1] - cam_pos[1]
            if dx * dx + dy * dy > g.cull_distance * g.cull_distance:
                continue
        if g.cull_bounds:
            min_x, min_y, max_x, max_y = g.cull_bounds
            px, py = g.position
            if px < min_x or px > max_x or py < min_y or py > max_y:
                continue
        visible.append((g, screen_pos, screen_size_val))
    return visible

def _resolve_text_collisions_parallel(text_entries, screen_size):
    if not text_entries:
        return []
    zone_width = screen_size[0] // 8
    zones = [[] for _ in range(8)]
    for entry in text_entries:
        g, screen_pos, _ = entry
        zone_idx = min(7, max(0, int(screen_pos[0] / zone_width)))
        zones[zone_idx].append(entry)

    result = []
    for zone in zones:
        if not zone:
            continue
        zone.sort(key=lambda x: x[1][1])
        occupied = []
        for g, screen_pos, _ in zone:
            size = int(g.font_size * 1.0)
            tw = int(size * len(g.text) * 0.6)
            th = size
            cx, cy = screen_pos
            rect = [cx - tw // 2, cy - th // 2, tw, th]
            for other in occupied:
                if (rect[0] < other[0] + other[2] and rect[0] + rect[2] > other[0] and
                        rect[1] < other[1] + other[3] and rect[1] + rect[3] > other[1]):
                    rect[1] = other[1] + other[3] + 2
            rect[0] = max(0, min(rect[0], screen_size[0] - tw))
            rect[1] = max(0, min(rect[1], screen_size[1] - th))
            adjusted_pos = (rect[0] + tw // 2, rect[1] + th // 2)
            result.append((g, screen_pos, adjusted_pos))
            occupied.append(rect)
    return result

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
        self._screen_width = config.app.screen_width
        self._screen_height = config.app.screen_height
        self._half_screen_width = self._screen_width // 2
        self._half_screen_height = self._screen_height // 2
        self._alpha_surfaces: Dict[int, pygame.Surface] = {}
        self._alpha_surface_frame: Dict[int, int] = {}
        self._frame_id = 0

        self._executor = ThreadPoolExecutor(max_workers=config.multithreading.gizmos_max_workers)
        self._prepared_data = None

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.WINDOWRESIZED:
            self._screen_width = event.x
            self._screen_height = event.y
            self._half_screen_width = self._screen_width // 2
            self._half_screen_height = self._screen_height // 2
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        mx, my = event.pos
        all_gizmos = list(self.unique_gizmos.values()) + self.gizmos + self.persistent_gizmos
        for g in all_gizmos:
            if g.gizmo_type == GizmoType.BUTTON and g._screen_pos is None:
                g._screen_pos = self.camera.world_to_screen(g.position) if g.world_space else g.position
        for g in reversed(all_gizmos):
            if g.gizmo_type != GizmoType.BUTTON or g.on_click is None:
                continue
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
        key = (text, tuple(color), font_name, font_size)
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

    def _get_temp_surface(self, alpha: int) -> pygame.Surface:
        if alpha not in self._alpha_surfaces:
            self._alpha_surfaces[alpha] = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            self._alpha_surface_frame[alpha] = -1
        if self._alpha_surface_frame[alpha] != self._frame_id:
            self._alpha_surfaces[alpha].fill((0, 0, 0, 0))
            self._alpha_surface_frame[alpha] = self._frame_id
        return self._alpha_surfaces[alpha]

    @profile("draw", "gizmos")
    def draw(self):
        if not self.enabled:
            return
        try:
            all_gizmos = list(self.unique_gizmos.values()) + self.gizmos + self.persistent_gizmos
            if not all_gizmos:
                return
            self._frame_id += 1

            for g in all_gizmos:
                g._screen_pos = None
                g._adjusted_screen_pos = None
                g._is_visible = None

            cam_pos = self.camera.screen_to_world((self._half_screen_width, self._half_screen_height))
            cam_scale = self.camera.target_scaling
            screen_size = (self._screen_width, self._screen_height)
            chunk_size = max(1, len(all_gizmos) // 4)
            chunks = [all_gizmos[i:i + chunk_size] for i in range(0, len(all_gizmos), chunk_size)]
            futures = []
            for chunk in chunks:
                args = (chunk, cam_pos, cam_scale, screen_size, self.cull_margin, self.distance_culling_enabled)
                future = self._executor.submit(_process_gizmo_chunk, args)
                futures.append(future)
            visible_entries = []
            for future in as_completed(futures):
                visible_entries.extend(future.result())

            text_entries = [e for e in visible_entries if e[0].gizmo_type == GizmoType.TEXT and e[0].collision]
            other_entries = [e for e in visible_entries if not (e[0].gizmo_type == GizmoType.TEXT and e[0].collision)]
            adjusted_texts = _resolve_text_collisions_parallel(text_entries, screen_size) if text_entries else []

            alpha_used = set()
            self._render_non_text_gizmos(other_entries, alpha_used)
            self._render_adjusted_texts(adjusted_texts, alpha_used)
            self._blit_alpha_surfaces(alpha_used)

            self.stats = {
                'total_gizmos': len(all_gizmos),
                'culled_frustum': len(all_gizmos) - len(visible_entries),
                'culled_distance': 0,
                'culled_occlusion': len(text_entries) - len(adjusted_texts),
                'drawn_gizmos': len(other_entries) + len(adjusted_texts)
            }
        except Exception as e:
            Debug.log_error(f"Error in Gizmos: {e}", "Gizmos")
    def _render_non_text_gizmos(self, entries, alpha_used):
        for g, screen_pos, _ in entries:
            self._draw_gizmo(g, screen_pos, alpha_used)

    def _render_adjusted_texts(self, adjusted_texts, alpha_used):
        for g, orig_pos, adj_pos in adjusted_texts:
            surf_target = self.screen if g.alpha == 255 else self._get_temp_surface(g.alpha)
            if g.alpha != 255:
                alpha_used.add(g.alpha)
            self._draw_line_gfx(surf_target, orig_pos, adj_pos, g.color, 2)
            size = int(g.font_size * self.camera.target_scaling) if (
                        g.font_world_space and g.world_space) else g.font_size
            surf = self._get_text_surface(g.text, g.color, g.font_name, size)
            r = surf.get_rect(center=adj_pos)
            if g.background_color:
                bg = pygame.Surface((r.width + 4, r.height + 4), pygame.SRCALPHA)
                bg.fill(g.background_color)
                surf_target.blit(bg, (r.left - 2, r.top - 2))
            surf_target.blit(surf, r)

    def _blit_alpha_surfaces(self, alpha_used):
        for a in alpha_used:
            self.screen.blit(self._alpha_surfaces[a], (0, 0))

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

    def _draw_gizmo(self, gizmo: GizmoData, pos: Tuple[int, int], alpha_used):
        surface = self.screen if gizmo.alpha == 255 else self._get_temp_surface(gizmo.alpha)
        if gizmo.alpha < 255:
            alpha_used.add(gizmo.alpha)
        color = gizmo.color
        scale = self.camera.target_scaling if gizmo.world_space else 1.0

        if gizmo.gizmo_type == GizmoType.POINT:
            start_profiling("POINT", "gizmos")
            r = int(gizmo.size * scale)
            if r > 0:
                pygame.gfxdraw.filled_circle(surface, int(pos[0]), int(pos[1]), r, color)
            stop_profiling("POINT")

        elif gizmo.gizmo_type == GizmoType.LINE and gizmo.end_position:
            start_profiling("LINE", "gizmos")
            end_screen = self.camera.world_to_screen(gizmo.end_position) if gizmo.world_space else gizmo.end_position
            self._draw_line_gfx(surface, pos, end_screen, color, gizmo.thickness)
            stop_profiling("LINE")

        elif gizmo.gizmo_type == GizmoType.CIRCLE:
            start_profiling("CIRCLE", "gizmos")
            r = int(gizmo.size * scale)
            self._draw_circle_gfx(surface, pos, r, color, gizmo.filled, gizmo.thickness)
            stop_profiling("CIRCLE")

        elif gizmo.gizmo_type == GizmoType.RECT:
            start_profiling("RECT", "gizmos")
            w = int(gizmo.width * scale)
            h = int(gizmo.height * scale)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = pos
            self._draw_rect_gfx(surface, rect, color, gizmo.filled, gizmo.thickness)
            stop_profiling("RECT")

        elif gizmo.gizmo_type == GizmoType.ARROW and gizmo.end_position:
            start_profiling("ARROW", "gizmos")
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
            stop_profiling("ARROW")

        elif gizmo.gizmo_type == GizmoType.CROSS:
            start_profiling("CROSS", "gizmos")
            s = gizmo.size * scale
            h = s * 0.5
            self._draw_line_gfx(surface, (pos[0] - h, pos[1]), (pos[0] + h, pos[1]), color, gizmo.thickness)
            self._draw_line_gfx(surface, (pos[0], pos[1] - h), (pos[0], pos[1] + h), color, gizmo.thickness)
            stop_profiling("CROSS")

        elif gizmo.gizmo_type == GizmoType.TEXT:
            start_profiling("TEXT", "gizmos")
            font_size = int(gizmo.font_size * (scale if gizmo.font_world_space else 1.0))
            txt_surf = self._get_text_surface(gizmo.text, color, gizmo.font_name, font_size)
            surf_rect = txt_surf.get_rect(center=pos)
            if gizmo.background_color:
                bg = pygame.Surface((surf_rect.width + 4, surf_rect.height + 4), pygame.SRCALPHA)
                bg.fill(gizmo.background_color)
                surface.blit(bg, (surf_rect.left - 2, surf_rect.top - 2))
            surface.blit(txt_surf, surf_rect)
            stop_profiling("TEXT")

        elif gizmo.gizmo_type == GizmoType.BUTTON:
            start_profiling("BUTTON", "gizmos")
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
            stop_profiling("BUTTON")

    def clear(self):
        self.gizmos.clear()

    def clear_persistent(self):
        self.persistent_gizmos.clear()

    def clear_unique(self):
        self.unique_gizmos.clear()

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
            for k, v in kwargs.items():
                setattr(g, k, v)
            return g
        g = GizmoData(gizmo_type=GizmoType.BUTTON, unique_id=key, **kwargs)
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
            "filled": True,
            "font_size": font_size,
            "font_name": font_name,
            "font_world_space": font_world_space,
            "layer": layer,
            "world_space": world_space,
            "on_click": on_click,
            "cull_distance": cull_distance
        }
        self._reuse_or_create_button(key, **cfg)

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

    def draw_point(self, position, color='white', size=3.0, duration=0.1, layer=0, world_space=True, cull_distance=-1.0,
                   cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.POINT, position=position,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, size=size,
                      duration=duration, layer=layer, world_space=world_space, cull_distance=cull_distance,
                      cull_bounds=cull_bounds)
        self._add_gizmo(g)

    def draw_line(self, start, end, color='white', thickness=1, duration=0.1, layer=0, world_space=True,
                  cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.LINE, position=start, end_position=end,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, thickness=thickness,
                      duration=duration, layer=layer, world_space=world_space, cull_distance=cull_distance,
                      cull_bounds=cull_bounds)
        self._add_gizmo(g)

    def draw_circle(self, center, radius, color='white', filled=False, thickness=1, duration=0.1, layer=0,
                    world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.CIRCLE, position=center,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, size=radius,
                      filled=filled, thickness=thickness, duration=duration, layer=layer, world_space=world_space,
                      cull_distance=cull_distance, cull_bounds=cull_bounds)
        self._add_gizmo(g)

    def draw_rect(self, center, width, height, color='white', filled=False, thickness=1, duration=0.1, layer=0,
                  world_space=True, cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.RECT, position=center,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, width=width,
                      height=height, filled=filled, thickness=thickness, duration=duration, layer=layer,
                      world_space=world_space, cull_distance=cull_distance, cull_bounds=cull_bounds)
        self._add_gizmo(g)

    def draw_arrow(self, start, end, color='white', thickness=2, duration=0.1, layer=0, world_space=True,
                   cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.ARROW, position=start, end_position=end,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, thickness=thickness,
                      duration=duration, layer=layer, world_space=world_space, cull_distance=cull_distance,
                      cull_bounds=cull_bounds)
        self._add_gizmo(g)

    def draw_cross(self, center, size, color='white', thickness=1, duration=0.1, layer=0, world_space=True,
                   cull_distance=-1.0, cull_bounds=None):
        g = GizmoData(gizmo_type=GizmoType.CROSS, position=center,
                      color=self.colors.get(color, color) if isinstance(color, str) else color, size=size,
                      thickness=thickness, duration=duration, layer=layer, world_space=world_space,
                      cull_distance=cull_distance, cull_bounds=cull_bounds)
        self._add_gizmo(g)

    def draw_text(self, position, text, color='white', background_color=None, duration=0.1, layer=0,
                  world_space=True, font_name="Consolas", font_size=14, font_world_space=False,
                  cull_distance=-1.0, cull_bounds=None, collision=False):
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
        if not config.debug.gizmos:
            return
        st = self.get_stats()
        if not st:
            return
        d, t = st['drawn_gizmos'], st['total_gizmos']
        f, ds = st['culled_frustum'], st['culled_distance']
        x, y = config.app.screen_width - 520, 40
        lines = [
            f"Gizmos: {d}/{t}",
            f"Frustum cull: {f}",
            f"Distance cull: {ds}",
            f"Active: {len(self.gizmos)}",
            f"Persistent: {len(self.persistent_gizmos)}",
            f"Unique: {len(self.unique_gizmos)}",
            f"Threads: {str(config.multithreading.gizmos_max_workers)}"
        ]
        for i, ln in enumerate(lines):
            self.draw_text((x, y + i * 22), ln, 'white', font_size=18, world_space=False, duration=0.1)

    def __del__(self):
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

_gizmos_instance: Optional[GizmosManager] = None

def get_gizmos(): return _gizmos_instance

def set_gizmos(gizmos_manager): global _gizmos_instance; _gizmos_instance = gizmos_manager

class Gizmos:
    @staticmethod
    def draw_button(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_button(*args, **kwargs)

    @staticmethod
    def draw_point(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_point(*args, **kwargs)

    @staticmethod
    def draw_line(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_line(*args, **kwargs)

    @staticmethod
    def draw_circle(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_circle(*args, **kwargs)

    @staticmethod
    def draw_rect(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_rect(*args, **kwargs)

    @staticmethod
    def draw_arrow(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_arrow(*args, **kwargs)

    @staticmethod
    def draw_cross(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_cross(*args, **kwargs)

    @staticmethod
    def draw_text(*args, **kwargs):
        if _gizmos_instance:
            _gizmos_instance.draw_text(*args, **kwargs)

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
