import math
import pymunk
from typing import Callable, Tuple, Optional

class WorldSpaceGraph:
    def __init__(self, base_func: Optional[Callable[[float], float]] = None):
        self.base_func = base_func or (lambda x: math.sin(x))
        self.color = (0, 200, 255)
        self.y_scale = 20.0
        self.min_points = 50
        self.max_points = 1000
        self.time_offset = 0.0

    def set_base_function(self, func: Callable[[float], float]):
        self.base_func = func

    def set_color(self, r: int, g: int, b: int):
        self.color = (r, g, b)

    def set_y_scale(self, scale: float):
        self.y_scale = scale

    def update_time(self, dt: float, speed: float = 1.0):
        self.time_offset += dt * speed

    def save(self):
        return {"color": self.color, "y_scale": self.y_scale, "time_offset": self.time_offset}

    def load(self, data):
        self.color = tuple(data.get("color", (0, 200, 255)))
        self.y_scale = float(data.get("y_scale", 1.0))
        self.time_offset = float(data.get("time_offset", 0.0))

    def _get_visible_x_range(self) -> Tuple[float, float]:
        cam = Camera._instance
        left = cam.screen_to_world((0, 0))[0]
        right = cam.screen_to_world((cam.screen_width, 0))[0]
        return (min(left, right), max(left, right))

    def _adaptive_step(self, x_min: float, x_max: float) -> float:
        visible_width = x_max - x_min
        num_points = max(self.min_points, min(self.max_points, int(visible_width * 5)))
        return visible_width / max(1, num_points)

    def draw(self):
        x_min, x_max = self._get_visible_x_range()
        x_step = self._adaptive_step(x_min, x_max)
        points = []
        x = x_min
        while x <= x_max:
            try:
                y = self.base_func(x + self.time_offset)
                points.append((x, y * self.y_scale))
            except (ValueError, OverflowError, ZeroDivisionError):
                pass
            x += x_step
        for i in range(1, len(points)):
            Gizmos.draw_line(points[i - 1], points[i], color=self.color, world_space=True, thickness=5)

graph: Optional[WorldSpaceGraph] = None
def complex_trig_demo(x: float) -> float:
    def real_pow(val: float, exp: float) -> float:
        return math.copysign(abs(val) ** exp, val) if val != 0.0 else 0.0

    return (
        0.8 * math.sin(x * 0.9 + 0.3) +
        0.5 * math.cos(x * 1.7 - 0.5) +
        0.3 * math.sin(x * 3.2) * math.cos(x * 0.4) +
        0.2 * math.sin(real_pow(x, 0.9) * 2.1 + math.sin(x * 0.6)) +
        0.15 * math.sin(x * 5.0 + math.cos(x * 1.1))
    )
def save_state():
    return {"graph": graph.save() if graph else {}}

def load_state(state):
    global graph
    graph = graph or WorldSpaceGraph(lambda x: math.sin(x) * math.cos(x * 0.7))
    graph.load(state.get("graph", {}))

def start():
    global graph
    graph = WorldSpaceGraph(complex_trig_demo)
    graph.y_scale = 800.0  # уменьшаем масштаб, так как амплитуда ~2.0

def update(dt):
    global graph
    if graph is None:
        graph = WorldSpaceGraph(complex_trig_demo)
    graph.update_time(dt, speed=10.0)
    graph.draw()