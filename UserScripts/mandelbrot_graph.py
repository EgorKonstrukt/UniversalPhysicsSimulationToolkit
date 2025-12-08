import math
from typing import List, Tuple

class MandelbrotGraph:
    def __init__(self):
        self.color = (0, 200, 255)
        self.max_iter = 500
        self.threshold = 4.0
        self.detail_level = 0.0  # накапливается из dt
        self._contour_cache = None
        self._last_view = None

    def update_time(self, dt: float):
        self.detail_level = min(self.detail_level + dt * 10.0, 1000.0)

    def _get_view_key(self) -> Tuple[float, float, float]:
        cam = Camera._instance
        x_min, x_max = cam.screen_to_world((0, 0))[0], cam.screen_to_world((cam.screen_width, 0))[0]
        y_min, y_max = cam.screen_to_world((0, cam.screen_height))[1], cam.screen_to_world((0, 0))[1]
        scale = abs(x_max - x_min) / cam.screen_width
        return (round(x_min, 6), round(y_min, 6), round(scale, 6))

    def _mandelbrot_iter(self, cx: float, cy: float) -> int:
        x = y = 0.0
        for i in range(self.max_iter):
            x2, y2 = x * x, y * y
            if x2 + y2 > self.threshold:
                return i
            y = 2 * x * y + cy
            x = x2 - y2 + cx
        return self.max_iter

    def _generate_contours(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        cam = Camera._instance
        x_min, x_max = cam.screen_to_world((0, 0))[0], cam.screen_to_world((cam.screen_width, 0))[0]
        y_min, y_max = cam.screen_to_world((0, cam.screen_height))[1], cam.screen_to_world((0, 0))[1]
        width = abs(x_max - x_min)
        height = abs(y_max - y_min)
        res = max(32, min(256, int(60 + self.detail_level)))
        dx = width / res
        dy = height / res
        lines = []
        grid = [[0] * (res + 1) for _ in range(res + 1)]
        for i in range(res + 1):
            for j in range(res + 1):
                x = x_min + i * dx
                y = y_min + j * dy
                grid[j][i] = self._mandelbrot_iter(x, y)
        for i in range(res):
            for j in range(res):
                v00, v01 = grid[j][i], grid[j][i + 1]
                v10, v11 = grid[j + 1][i], grid[j + 1][i + 1]
                center_val = (v00 + v01 + v10 + v11) / 4.0
                if abs(v00 - center_val) > 2 or abs(v01 - center_val) > 2 or \
                   abs(v10 - center_val) > 2 or abs(v11 - center_val) > 2:
                    x0, y0 = x_min + i * dx, y_min + j * dy
                    x1, y1 = x0 + dx, y0 + dy
                    lines.append(((x0, y0), (x1, y0)))
                    lines.append(((x1, y0), (x1, y1)))
                    lines.append(((x1, y1), (x0, y1)))
                    lines.append(((x0, y1), (x0, y0)))
        return lines

    def draw(self):
        view_key = self._get_view_key()
        if self._last_view != view_key:
            self._last_view = view_key
            self._contour_cache = self._generate_contours()
        if self._contour_cache:
            for p0, p1 in self._contour_cache:
                Gizmos.draw_line(p0, p1, color=self.color, world_space=True, thickness=2)


mandelbrot_graph = None

def start():
    global mandelbrot_graph
    mandelbrot_graph = MandelbrotGraph()

def update(dt):
    global mandelbrot_graph
    if mandelbrot_graph is None:
        mandelbrot_graph = MandelbrotGraph()
    mandelbrot_graph.update_time(dt)
    mandelbrot_graph.draw()

def save_state():
    return {}

def load_state(_):
    pass