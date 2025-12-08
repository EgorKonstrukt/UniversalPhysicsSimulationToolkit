import math
from typing import Tuple

class SierpinskiDrawer:
    def __init__(self, min_depth: int = 1, max_depth: int = 5, color: Tuple[int, int, int] = (0, 200, 255), world_center: Tuple[float, float] = (0, 0), base_size: float = 1024.0):
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.color = color
        self.world_center = world_center
        self.base_size = base_size

    def _draw_tri(self, a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float], depth: int):
        if depth <= 0:
            Gizmos.draw_line(a, b, color=self.color, world_space=True, thickness=1)
            Gizmos.draw_line(b, c, color=self.color, world_space=True, thickness=1)
            Gizmos.draw_line(c, a, color=self.color, world_space=True, thickness=1)
            return
        ab = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
        bc = ((b[0] + c[0]) * 0.5, (b[1] + c[1]) * 0.5)
        ca = ((c[0] + a[0]) * 0.5, (c[1] + a[1]) * 0.5)
        self._draw_tri(a, ab, ca, depth - 1)
        self._draw_tri(ab, b, bc, depth - 1)
        self._draw_tri(ca, bc, c, depth - 1)

    def draw(self):
        cam = Camera._instance
        world_px_size = 1.0 / cam.scaling
        visible_world_diameter = max(cam.screen_width, cam.screen_height) * world_px_size
        current_size = self.base_size
        scale_factor = visible_world_diameter / current_size
        if scale_factor <= 0:
            return
        depth = max(self.min_depth, min(self.max_depth, int(self.max_depth - math.log2(scale_factor + 1e-6))))
        cx, cy = self.world_center
        h = current_size / math.sqrt(3)
        a = (cx, cy - h)
        b = (cx - current_size * 0.5, cy + h * 0.5)
        c = (cx + current_size * 0.5, cy + h * 0.5)
        self._draw_tri(a, b, c, depth)

sierpinski: SierpinskiDrawer = None

def start():
    global sierpinski
    sierpinski = SierpinskiDrawer(min_depth=1, max_depth=9, world_center=(0, 0), base_size=1024.0)

def update(dt):
    global sierpinski
    if sierpinski is None:
        sierpinski = SierpinskiDrawer()
    sierpinski.draw()