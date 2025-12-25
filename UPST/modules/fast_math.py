# fast_math.py
import math
from typing import Tuple, List, Optional

def process_gizmo_chunk(
    gizmos_chunk,
    cam_tx: float,
    cam_ty: float,
    cam_scale: float,
    screen_w: int,
    screen_h: int,
    cull_margin: float,
    distance_culling_enabled: bool
):
    visible = []
    half_w = screen_w * 0.5
    half_h = screen_h * 0.5
    for g in gizmos_chunk:
        if g.world_space:
            sx = (g.position[0] - cam_tx) * cam_scale + half_w
            sy = half_h - (g.position[1] - cam_ty) * cam_scale
        else:
            sx, sy = g.position[0], g.position[1]
        screen_pos = (int(sx), int(sy))
        if g.gizmo_type in ("point", "circle", "cross"):
            screen_size_val = g.size * cam_scale if g.world_space else g.size
        elif g.gizmo_type == "rect":
            screen_size_val = max(g.width, g.height) * (cam_scale if g.world_space else 1.0) * 0.5
        elif g.gizmo_type in ("line", "arrow") and g.end_position:
            dx = g.end_position[0] - g.position[0]
            dy = g.end_position[1] - g.position[1]
            screen_size_val = math.hypot(dx, dy) * (cam_scale if g.world_space else 1.0) * 0.5
        elif g.gizmo_type == "text":
            fs = g.font_size * (cam_scale if (g.font_world_space and g.world_space) else 1.0)
            screen_size_val = fs * len(g.text) * 0.3
        else:
            screen_size_val = 10.0

        x, y = screen_pos
        r = screen_size_val
        if (x + r < -cull_margin or x - r > screen_w + cull_margin or
                y + r < -cull_margin or y - r > screen_h + cull_margin):
            continue
        if distance_culling_enabled and g.cull_distance > 0 and g.world_space:
            dx = g.position[0] - cam_tx
            dy = g.position[1] - cam_ty
            if dx * dx + dy * dy > g.cull_distance * g.cull_distance:
                continue
        if g.cull_bounds:
            min_x, min_y, max_x, max_y = g.cull_bounds
            px, py = g.position
            if px < min_x or px > max_x or py < min_y or py > max_y:
                continue
        visible.append((g, screen_pos, screen_size_val))
    return visible

def resolve_text_collisions_parallel(
    text_entries,
    screen_w: int,
    screen_h: int
):
    if not text_entries:
        return []
    zone_width = screen_w // 8
    zones = [[] for _ in range(8)]
    for entry in text_entries:
        g, screen_pos = entry[0], entry[1]
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
            rect[0] = max(0, min(rect[0], screen_w - tw))
            rect[1] = max(0, min(rect[1], screen_h - th))
            adjusted_pos = (rect[0] + tw // 2, rect[1] + th // 2)
            result.append((g, screen_pos, adjusted_pos))
            occupied.append(rect)
    return result

def screen_to_world_impl(x, y, inv_s, tx, ty, cx, cy):
    return ((x - cx) * inv_s + tx, (cy - y) * inv_s + ty)

def world_to_screen_impl(x, y, s, tx, ty, cx, cy):
    return ((x - tx) * s + cx, cy - (y - ty) * s)
