import math
import cmath
from typing import List, Tuple

class MandelbrotFourierSeries:
    def __init__(self):
        self.max_iter = 500
        self.boundary_samples = 2000
        self.zoom = 3000
        self.mandelbrot_contours: List[List[Tuple[float, float]]] = []
        self.fourier_data_list: List[List[Tuple[int, complex]]] = []
        self.drawing_points_list: List[List[Tuple[float, float]]] = []
        self.num_terms = 100
        self.phase = 0.0
        self.screen_center = (0, 0)
        self.fractal_center = (-0.5, 0.0)
        self.scale = self.zoom

        self._init_contour_and_fourier()

    def _init_contour_and_fourier(self):
        contour = self._generate_mandelbrot_contour(self.screen_center, self.fractal_center, self.scale,
                                                    self.boundary_samples, self.max_iter)
        fourier = self._compute_fourier_series(contour, self.num_terms)
        self.mandelbrot_contours.append(contour)
        self.fourier_data_list.append(fourier)
        self.drawing_points_list.append([])

    def _is_in_mandelbrot(self, c: complex, max_iter: int) -> bool:
        z = 0j
        for _ in range(max_iter):
            z = z * z + c
            if abs(z) > 2:
                return False
        return True

    def _generate_mandelbrot_contour(self, screen_center: Tuple[float, float], fractal_center: Tuple[float, float],
                                     scale: float, samples: int, max_iter: int) -> List[Tuple[float, float]]:
        cx, cy = fractal_center
        sx, sy = screen_center
        x_min, x_max = -2.5, 1.5
        y_min, y_max = -1.5, 1.5
        grid_size = 300
        dx = (x_max - x_min) / grid_size
        dy = (y_max - y_min) / grid_size
        grid = [[self._is_in_mandelbrot(complex(x_min + i * dx, y_min + j * dy), max_iter)
                 for i in range(grid_size + 1)] for j in range(grid_size + 1)]
        boundary_points = []
        for j in range(grid_size):
            for i in range(grid_size):
                corners = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
                if not all(corners) and any(corners):
                    x_quad = x_min + i * dx
                    y_quad = y_min + j * dy
                    for sub_i in range(3):
                        for sub_j in range(3):
                            x_test = x_quad + (sub_i * dx / 3)
                            y_test = y_quad + (sub_j * dy / 3)
                            if self._is_boundary_point(complex(x_test, y_test), max_iter):
                                refined_point = self._refine_boundary_point(complex(x_test, y_test), max_iter)
                                if refined_point:
                                    x_pix = sx + scale * (refined_point.real - cx)
                                    y_pix = sy + scale * (refined_point.imag - cy)
                                    boundary_points.append((x_pix, y_pix))
        if boundary_points:
            center_x = sum(p[0] for p in boundary_points) / len(boundary_points)
            center_y = sum(p[1] for p in boundary_points) / len(boundary_points)
            def angle_from_center(point):
                return math.atan2(point[1] - center_y, point[0] - center_x)
            boundary_points.sort(key=angle_from_center)
            if len(boundary_points) > samples:
                step = len(boundary_points) / samples
                boundary_points = [boundary_points[int(i * step)] for i in range(samples)]
            return boundary_points
        return self._generate_fallback_contour(screen_center, scale, samples)

    def _is_boundary_point(self, c: complex, max_iter: int) -> bool:
        epsilon = 0.01
        offsets = [epsilon, -epsilon]
        center_in = self._is_in_mandelbrot(c, max_iter)
        for dx in offsets:
            for dy in offsets:
                if dx == 0 and dy == 0: continue
                neighbor = c + complex(dx, dy)
                neighbor_in = self._is_in_mandelbrot(neighbor, max_iter)
                if neighbor_in != center_in:
                    return True
        return False

    def _refine_boundary_point(self, c: complex, max_iter: int) -> complex:
        if self._is_in_mandelbrot(c, max_iter):
            for angle in [0, math.pi / 4, math.pi / 2, 3 * math.pi / 4, math.pi, 5 * math.pi / 4, 3 * math.pi / 2, 7 * math.pi / 4]:
                direction = complex(math.cos(angle), math.sin(angle))
                low, high = 0.0, 0.1
                for _ in range(20):
                    mid = (low + high) / 2
                    test_point = c + mid * direction
                    if self._is_in_mandelbrot(test_point, max_iter):
                        low = mid
                    else:
                        high = mid
                if high - low < 0.001:
                    return c + high * direction
        return c

    def _generate_fallback_contour(self, screen_center: Tuple[float, float], scale: float, samples: int) -> List[Tuple[float, float]]:
        sx, sy = screen_center
        points = []
        for i in range(samples):
            t = 2 * math.pi * i / samples
            if -math.pi / 2 <= t <= math.pi / 2:
                r = 0.5 * (1 - math.cos(t))
                x = r * math.cos(t) + 0.25
                y = r * math.sin(t)
            else:
                r = 0.25
                x = r * math.cos(t) - 0.75
                y = r * math.sin(t)
            x_pix = sx + scale * x
            y_pix = sy + scale * y
            points.append((x_pix, y_pix))
        return points

    def _compute_fourier_series(self, path_points: List[Tuple[float, float]], num_terms: int = 20000) -> List[Tuple[int, complex]]:
        N = len(path_points)
        complex_pts = [complex(x, y) for x, y in path_points]
        coeffs = []
        for k in range(-num_terms // 2, num_terms // 2):
            c_k = sum(complex_pts[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N)) / N
            coeffs.append((k, c_k))
        return sorted(coeffs, key=lambda x: abs(x[1]), reverse=True)

    def update(self, dt: float):
        self.phase += dt * 2.0
        if self.fourier_data_list and self.drawing_points_list:
            self._draw_fourier_epicycles(self.screen_center, self.fourier_data_list[0], self.drawing_points_list[0], self.phase)

    @profile("_draw_fourier_epicycles", "demo")
    def _draw_fourier_epicycles(self, origin: Tuple[float, float], fourier_data: List[Tuple[int, complex]],
                                drawing_points: List[Tuple[float, float]], phase: float):
        cx, cy = origin
        cur = complex(cx, cy)
        for k, coef in fourier_data:
            freq = k
            amp = abs(coef)
            shift = cmath.phase(coef)
            nxt = cur + amp * cmath.exp(1j * (freq * phase / 16 + shift))
            Gizmos.draw_circle((cur.real, cur.imag), amp, 'gray', False, 1, True, 0.1)
            Gizmos.draw_line((cur.real, cur.imag), (nxt.real, nxt.imag), 'white', 2, True, 0.1)
            cur = nxt
        drawing_points.insert(0, (cur.real, cur.imag))
        if len(drawing_points) > 2000:
            drawing_points.pop()
        for i in range(len(drawing_points) - 1):
            Gizmos.draw_line(drawing_points[i], drawing_points[i + 1], 'red', 2, True, 0.1)


def start():
    global mandelbrot_fourier_series
    mandelbrot_fourier_series = MandelbrotFourierSeries()

def update(dt):
    global mandelbrot_fourier_series
    if not 'mandelbrot_fourier_series' in globals() or mandelbrot_fourier_series is None:
        mandelbrot_fourier_series = MandelbrotFourierSeries()
    mandelbrot_fourier_series.update(dt)