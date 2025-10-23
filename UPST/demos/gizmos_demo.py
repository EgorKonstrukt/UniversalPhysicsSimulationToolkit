from __future__ import annotations

from numba import njit
import math
import time
import random
import cmath
import numpy as np
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.modules.profiler import profile
from UPST.sound.sound_synthesizer import synthesizer


class GizmosDemo:

    def __init__(self, camera):

        self.camera = camera

        self.phase: float = 0.0
        self.last_time: float = time.time()
        self.time_scale: float = 1.0

        self.signal_types = ["sine", "triangle", "sawtooth", "square"]
        self.signal_index: int = 0
        self.frequency: float = 2.0
        self.amplitude: float = 80.0
        self.sample_points: int = 300

        self.auto_cycle: bool = True
        self.cycle_timer: float = 0.0
        self.cycle_interval: float = 3.0

        self.multi_channel: bool = False
        self.channel_count: int = 3

        self.max_iter = 500
        self.boundary_samples = 2000
        self.zoom = 200
        self.mandelbrot_contours = []
        self.fourier_data_list = []
        self.drawing_points_list = []
        self.num_terms = 1500

        self._lorenz_pts = [(0.1, 0.0, 0.0)]
        self._dp_state = [math.pi / 2, math.pi / 2, 0.0, 0.0]
        self._boids = None
        self._sort_arr = None
        self._life_grid = None
        self._fern_pts = [(0.0, 0.0)]

        self._qf_nodes:list
        self._qf_connections:list
        self._qf_particles:list
        self._qf_waveforms:list

        self._langton_ant_pos = None
        self._langton_ant_dir = None
        self._langton_steps = 0
        self._langton_directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        self._langton_grid = None

        self.notes = [
            ('C3', False), ('C#3', True), ('D3', False), ('D#3', True), ('E3', False),
            ('F3', False), ('F#3', True), ('G3', False), ('G#3', True), ('A3', False),
            ('A#3', True), ('B3', False),

            ('C4', False), ('C#4', True), ('D4', False), ('D#4', True), ('E4', False),
            ('F4', False), ('F#4', True), ('G4', False), ('G#4', True), ('A4', False),
            ('A#4', True), ('B4', False),

            ('C5', False), ('C#5', True), ('D5', False), ('D#5', True), ('E5', False),
            ('F5', False), ('F#5', True), ('G5', False), ('G#5', True), ('A5', False),
            ('A#5', True), ('B5', False),

            ('C6', False)
        ]

        self._demo_index = 0

        self._demos = {
            "demo_turing_machine": {
                "title": "demo_turing_machine",
                "description": "",
                "function": self.demo_turing_machine
            },
            "demo_stirling_engine": {
                "title": "Двигатель Стирлинга",
                "description": "Численная термодинамическая модель двигателя Стирлинга с визуализацией давления, объема и КПД.",
                "function": self.demo_stirling_engine
            },
            "demo_fluid_dynamics": {
                "title": "Динамика жидкости",
                "description": "Симуляция движения жидкости с визуализацией векторов потока и давления.",
                "function": self.demo_fluid_dynamics
            },
            "step_scalar_phi4": {
                "title": "step_scalar_phi4",
                "description": "",
                "function": self.step_scalar_phi4
            },
            "demo_piano": {
                "title": "Пианино",
                "description": "Простое пианино использующее внутренний синтезатор программы UPST.",
                "function": self.demo_piano
            },
            "demo_boids": {
                "title": "Боиды",
                "description": "Простая модель стаи, имеющая три базовых правила: Separation, Alignment и Cohesion",
                "function": self.demo_boids
            },
            "demo_hypercube": {
                "title": "Тессеракт",
                "description": "Фигура четырехмерного пространства, с вращением по всем осям.",
                "function": self.demo_hypercube
            },
            "demo_penteract": {
                "title": "Пентеракт",
                "description": "",
                "function": self.demo_penteract
            },
            "demo_4d_torus": {
                "title": "demo_4d_torus",
                "description": "",
                "function": self.demo_4d_torus
            },
            "demo_cube_wireframe": {
                "title": "Куб",
                "description": "Фигура трехмерного пространства",
                "function": self.demo_cube_wireframe
            },
            "demo_langton_ant": {
                "title": "RL Муравей Лэнгтона",
                "description": "Двумерный клеточный автомат с очень простыми правилами. Муравья можно также считать двумерной машиной Тьюринга с 2 символами и 4 состояниями.",
                "function": self.demo_langton_ant
            },
            "demo_spiral": {
                "title": "demo_spiral",
                "description": "",
                "function": self.demo_spiral
            },
            "demo_am_signal": {
                "title": "demo_am_signal",
                "description": "",
                "function": self.demo_am_signal
            },
            # "demo_quantum_fractal": {
            #     "title": "demo_quantum_fractal",
            #     "description": "",
            #     "function": self.demo_quantum_fractal
            # },
            "demo_quantum_swarm": {
                "title": "demo_quantum_swarm",
                "description": "",
                "function": self.demo_quantum_swarm
            },
            "demo_audio_bars": {
                "title": "demo_audio_bars",
                "description": "",
                "function": self.demo_audio_bars
            },
            "demo_bubble_sort": {
                "title": "demo_bubble_sort",
                "description": "",
                "function": self.demo_bubble_sort
            },
            "demo_double_pendulum": {
                "title": "demo_double_pendulum",
                "description": "",
                "function": self.demo_double_pendulum
            },
            "demo_cellular_life_simulation": {
                "title": "demo_cellular_life_simulation",
                "description": "",
                "function": self.demo_cellular_life_simulation
            },
            "demo_dynamic_arrow": {
                "title": "demo_dynamic_arrow",
                "description": "",
                "function": self.demo_dynamic_arrow
            },
            "demo_raycast_game": {
                "title": "demo_raycast_game",
                "description": "",
                "function": self.demo_raycast_game
            },
            "demo_supermodel": {
                "title": "demo_supermodel",
                "description": "",
                "function": self.demo_supermodel
            },
            # "demo_lorenz_attractor": {
            #     "title": "demo_lorenz_attractor",
            #     "description": "",
            #     "function": self.demo_lorenz_attractor
            # },
            "demo_planet_orbits": {
                "title": "demo_planet_orbits",
                "description": "",
                "function": self.demo_planet_orbits
            },
            "demo_graphing_calculator": {
                "title": "demo_graphing_calculator",
                "description": "",
                "function": self.demo_graphing_calculator
            },
            "demo_fractal_tree": {
                "title": "demo_fractal_tree",
                "description": "",
                "function": self.demo_fractal_tree
            },
            "demo_game_of_life": {
                "title": "demo_game_of_life",
                "description": "",
                "function": self.demo_game_of_life
            },
            "demo_vector_field": {
                "title": "demo_vector_field",
                "description": "",
                "function": self.demo_vector_field
            },
            "demo_galaxy_simulation": {
                "title": "demo_galaxy_simulation",
                "description": "",
                "function": self.demo_galaxy_simulation
            },
            "demo_barnsley_fern": {
                "title": "demo_barnsley_fern",
                "description": "",
                "function": self.demo_barnsley_fern
            },
            "demo_rose_curve": {
                "title": "demo_rose_curve",
                "description": "",
                "function": self.demo_rose_curve
            },
            "demo_wavy_circle": {
                "title": "demo_wavy_circle",
                "description": "",
                "function": self.demo_wavy_circle
            },
            "demo_rotating_arrows": {
                "title": "demo_rotating_arrows",
                "description": "",
                "function": self.demo_rotating_arrows
            },
            "demo_spring": {
                "title": "demo_spring",
                "description": "",
                "function": self.demo_spring
            },
            "demo_axes": {
                "title": "demo_axes",
                "description": "",
                "function": self.demo_axes
            },
            "demo_wave_grid": {
                "title": "demo_wave_grid",
                "description": "",
                "function": self.demo_wave_grid
            },
        }


        # contour = self._generate_mandelbrot_contour(
        #     screen_center=(200, 0),
        #     fractal_center=(0, 0),
        #     scale=self.zoom,
        #     samples=self.boundary_samples,
        #     max_iter=self.max_iter,
        # )
        # self.mandelbrot_contours.append(contour)
        # self.fourier_data_list.append(self._compute_fourier_series(contour, self.num_terms))
        # self.drawing_points_list.append([])



    @profile("demo_4d_torus", "demo")
    def demo_4d_torus(self, position=(0, 0)):
        cx, cy = position
        t = self.phase
        angle_xy = t * 0.4
        angle_zw = t * 0.5
        angle_xz = t * 0.3
        angle_yw = t * 0.6

        def rotate(p, i, j, a):
            c, s = math.cos(a), math.sin(a)
            pi, pj = p[i], p[j]
            p[i] = pi * c - pj * s
            p[j] = pi * s + pj * c

        points = []
        for u in range(0, 360, 12):
            for v in range(0, 360, 12):
                u_rad = math.radians(u)
                v_rad = math.radians(v)
                R, r = 2.0, 0.8
                x = (R + r * math.cos(v_rad)) * math.cos(u_rad)
                y = (R + r * math.cos(v_rad)) * math.sin(u_rad)
                z = r * math.sin(v_rad)
                w = 0.5 * math.sin(2 * v_rad)  # добавляем 4D-компоненту
                points.append([x, y, z, w])

        def project_4d_to_2d(p4):
            p = p4[:]
            rotate(p, 0, 1, angle_xy)
            rotate(p, 2, 3, angle_zw)
            rotate(p, 0, 2, angle_xz)
            rotate(p, 1, 3, angle_yw)
            x, y, z, w = p
            scale = 200 / (3 - w)
            sx = x * scale + cx
            sy = y * scale + cy
            sz = z * scale
            return sx, sy, sz

        projected = [project_4d_to_2d(p) for p in points]

        for (x, y, z) in projected:
            depth_factor = max(0.3, 1.0 - abs(z) / 300)
            intensity = int(200 * depth_factor)
            color = (intensity, intensity // 2, 255 - intensity // 2)
            Gizmos.draw_circle((x, y), int(3 * depth_factor), color=color, duration=0.1)

    def _is_in_mandelbrot(self, c, max_iter):
        z = 0j
        for _ in range(max_iter):
            z = z * z + c
            if abs(z) > 2:
                return False
        return True

    def _generate_mandelbrot_contour(self, screen_center, fractal_center, scale, samples, max_iter):
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

                corners = [
                    grid[j][i],  # левый нижний
                    grid[j][i + 1],  # правый нижний
                    grid[j + 1][i + 1],  # правый верхний
                    grid[j + 1][i]  # левый верхний
                ]

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
                                    x_pix = sx + scale * refined_point.real
                                    y_pix = sy + scale * refined_point.imag
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

        return boundary_points if boundary_points else self._generate_fallback_contour(screen_center, scale, samples)

    def _is_boundary_point(self, c, max_iter):
        epsilon = 0.01
        offsets = [epsilon, -epsilon]

        center_in = self._is_in_mandelbrot(c, max_iter)

        for dx in offsets:
            for dy in offsets:
                if dx == 0 and dy == 0:
                    continue
                neighbor = c + complex(dx, dy)
                neighbor_in = self._is_in_mandelbrot(neighbor, max_iter)
                if neighbor_in != center_in:
                    return True
        return False

    def _refine_boundary_point(self, c, max_iter):
        if self._is_in_mandelbrot(c, max_iter):
            for angle in [0, math.pi / 4, math.pi / 2, 3 * math.pi / 4, math.pi, 5 * math.pi / 4, 3 * math.pi / 2,
                          7 * math.pi / 4]:
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

    def _generate_fallback_contour(self, screen_center, scale, samples):
        sx, sy = screen_center
        points = []
        for i in range(samples):
            t = 2 * math.pi * i / samples
            if -math.pi / 2 <= t <= math.pi / 2:
                r = 0.5 * (1 - math.cos(t))
                x = r * math.cos(t) + 0.25
                y = r * math.sin(t)
            # Круг (голова)
            else:
                r = 0.25
                x = r * math.cos(t) - 0.75
                y = r * math.sin(t)

            x_pix = sx + scale * x
            y_pix = sy + scale * y
            points.append((x_pix, y_pix))

        return points

    def _compute_fourier_series(self, path_points, num_terms=20000):
        N = len(path_points)
        complex_pts = [complex(x, y) for x, y in path_points]
        coeffs = []
        for k in range(-num_terms // 2, num_terms // 2):
            c_k = sum(
                complex_pts[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N)
            ) / N
            coeffs.append((k, c_k))
        return sorted(coeffs, key=lambda x: abs(x[1]), reverse=True)
    @profile("_draw_fourier_epicycles", "demo")
    def _draw_fourier_epicycles(self, origin, fourier_data, drawing_points, phase):
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
        if len(drawing_points) > 3000:
            drawing_points.pop()
        # хвост траектории
        for i in range(len(drawing_points) - 1):
            Gizmos.draw_line(drawing_points[i], drawing_points[i + 1], 'red', 2, True, 0.1)

    def _get_signal_value(self, t: float, signal_type: str = "sine", frequency: float | None = None,
                          amplitude: float | None = None) -> float:
        if frequency is None:
            frequency = self.frequency
        if amplitude is None:
            amplitude = self.amplitude
        phase = t * frequency * 2 * math.pi
        if signal_type == "sine":
            return math.sin(phase) * amplitude
        if signal_type == "triangle":
            normalized = (phase / (2 * math.pi)) % 1
            return ((4 * normalized - 1) if normalized < 0.5 else (3 - 4 * normalized)) * amplitude
        if signal_type == "sawtooth":
            normalized = (phase / (2 * math.pi)) % 1
            return (2 * normalized - 1) * amplitude
        if signal_type == "square":
            return amplitude if math.sin(phase) > 0 else -amplitude
        return 0.0

    def _draw_oscilloscope_grid(self, origin, width, height):
        x0, y0 = origin
        Gizmos.draw_rect((x0, y0), width, height, 'gray', False, 2, True, 0.1)
        grid = 8
        for i in range(1, grid):
            y = y0 - height / 2 + height * i / grid
            Gizmos.draw_line((x0 - width / 2, y), (x0 + width / 2, y), 'gray', 1, True, 0.1)
            x = x0 - width / 2 + width * i / grid
            Gizmos.draw_line((x, y0 - height / 2), (x, y0 + height / 2), 'gray', 1, True, 0.1)
        Gizmos.draw_line((x0 - width / 2, y0), (x0 + width / 2, y0), 'white', 2, True, 0.1)
        Gizmos.draw_line((x0, y0 - height / 2), (x0, y0 + height / 2), 'white', 2, True, 0.1)

    def _draw_signal_trace(self, origin, width, height, signal_type, color,
                            frequency=None, amplitude=None, offset=0):
        x0, y0 = origin
        frequency = frequency or self.frequency
        amplitude = amplitude or self.amplitude
        time_window = 2.0
        pts = []
        for i in range(self.sample_points):
            t = (i / self.sample_points) * time_window + self.phase
            x = x0 - width / 2 + width * i / self.sample_points
            y = y0 + self._get_signal_value(t, signal_type, frequency, amplitude) + offset
            y = max(y0 - height / 2, min(y0 + height / 2, y))
            pts.append((x, y))
        for i in range(len(pts) - 1):
            Gizmos.draw_line(pts[i], pts[i + 1], color, 3, True, 0.1)
        cv = self._get_signal_value(self.phase, signal_type, frequency, amplitude)
        cy = max(y0 - height / 2, min(y0 + height / 2, y0 + cv + offset))
        Gizmos.draw_circle((x0 + width / 2 - 20, cy), 5, color, True, True, 0.1)

    def _draw_oscilloscope_info(self, origin, width, height):
        x0, y0 = origin
        Gizmos.draw_text(position=(x0, y0 + height / 2 + 40), text="GIZMOS OSCILLOSCOPE", color='white'
                         , duration=0.1, font_name="Consolas", font_size=25, font_world_space=True,
                         world_space=True, background_color=(0,0,0,128))
        Gizmos.draw_text((x0 - width / 2 + 100, y0 + height / 2 + 20),
                         f"Signal: {self.signal_types[self.signal_index].upper()}"
                         , duration=0.1, font_name="Consolas", font_size=18, font_world_space=True,
                         world_space=True, background_color=(0, 0, 0, 128))
        Gizmos.draw_text((x0 - width / 2 + 100, y0 - height / 2 - 20),
                         f"Frequency: {self.frequency:.1f} Hz", 'yellow'
                         , duration=0.1, font_name="Consolas", font_size=18, font_world_space=True,
                         world_space=True, background_color=(0, 0, 0, 128))
        Gizmos.draw_text((x0 - width / 2 + 100, y0 - height / 2 - 40),
                         f"Amplitude: {self.amplitude:.1f}", 'yellow'
                         , duration=0.1, font_name="Consolas", font_size=18, font_world_space=True,
                         world_space=True, background_color=(0, 0, 0, 128))
        if self.multi_channel:
            colors = ['green', 'red', 'blue']
            names = ['sine', 'triangle', 'square']
            for i, (c, n) in enumerate(zip(colors, names)):
                Gizmos.draw_text((x0 + width / 2 - 100, y0 + height / 2 - 30 - i * 20),
                                 f"CH{i + 1}: {n}", c, 12, True, 0.1, True)

    @profile("demo_oscilloscope", "demo")
    def draw_oscilloscope(self, origin=(-500, -800), width=1000, height=200):
        self.draw_controls(origin, width, height)

        self._draw_oscilloscope_grid(origin, width, height)
        if self.multi_channel:
            pass
        else:
            current = self.signal_types[self.signal_index]
            self._draw_signal_trace(origin, width, height, current, 'green')
        self._draw_oscilloscope_info(origin, width, height)

        x_tick = origin[0] - width / 2 + ((self.phase * 50) % width)
        Gizmos.draw_line((x_tick, origin[1] - height / 2),
                         (x_tick, origin[1] + height / 2),
                         'red', 1, True, 0.1)
    def increase_frequency(self):
        self.frequency = min(self.frequency + 0.5, 20.0)

    def decrease_frequency(self):
        self.frequency = max(self.frequency - 0.5, 0.1)

    def increase_amplitude(self):
        self.amplitude = min(self.amplitude + 10.0, 200.0)

    def decrease_amplitude(self):
        self.amplitude = max(self.amplitude - 10.0, 10.0)

    def next_signal(self):
        self.signal_index = (self.signal_index + 1) % len(self.signal_types)

    def toggle_auto_cycle(self):
        self.auto_cycle = not self.auto_cycle

    def toggle_multi_channel(self):
        self.multi_channel = not self.multi_channel

    def draw_controls(self, origin=(-500, -800), width=1000, height=200):
        x0, y0 = origin
        panel_y = y0 - height / 2 - 100
        btn_size = 40
        spacing = 10

        Gizmos.draw_button(
            position=(x0 - width / 2, panel_y),
            text="-F",
            on_click=self.decrease_frequency,
            width=btn_size, height=btn_size,
            font_size=20, font_world_space=True, world_space=True
        )
        Gizmos.draw_button(
            position=(x0 - width / 2 + btn_size + spacing, panel_y),
            text="+F",
            on_click=self.increase_frequency,
            width=btn_size, height=btn_size,
            font_size=20, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(x0 - width / 2 + (btn_size + spacing) * 2, panel_y),
            text="-A",
            on_click=self.decrease_amplitude,
            width=btn_size, height=btn_size,
            font_size=20, font_world_space=True, world_space=True
        )
        Gizmos.draw_button(
            position=(x0 - width / 2 + (btn_size + spacing) * 3, panel_y),
            text="+A",
            on_click=self.increase_amplitude,
            width=btn_size, height=btn_size,
            font_size=20, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(x0 + width / 2 - (btn_size + spacing) * 2, panel_y),
            text="Next Sig",
            on_click=self.next_signal,
            width=btn_size * 2, height=btn_size,
            font_size=18, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(x0 + width / 2 - (btn_size + spacing) * 2, panel_y - btn_size - spacing),
            text="Auto" if self.auto_cycle else "Manual",
            on_click=self.toggle_auto_cycle,
            width=btn_size * 2, height=btn_size,
            font_size=18, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(x0 + width / 2 - (btn_size + spacing) * 2, panel_y - 2 * (btn_size + spacing)),
            text="Multi" if not self.multi_channel else "Single",
            on_click=self.toggle_multi_channel,
            width=btn_size * 2, height=btn_size,
            font_size=18, font_world_space=True, world_space=True
        )
    @profile("demo_particle_swarm", "demo")
    def demo_particle_swarm(self, position=(0, 0)):
        for i in range(100):
            t = self.phase + i * 0.05
            x = math.sin(t * 3) * 100 + 300
            y = math.sin(t * 2) * 100 + 300
            Gizmos.draw_circle((x, y), 2, 'white', True, True, 0.1)
    @profile("demo_spiral", "demo")
    def demo_spiral(self, position=(0, 0)):
        pts = []
        for theta in range(0, 1500, 5):
            a = math.radians(theta)
            r = 5 * a
            pts.append((r * math.cos(a) - 300, r * math.sin(a) + 300))
        for i in range(len(pts) - 1):
            Gizmos.draw_line(pts[i], pts[i + 1], 'white', 2, True, 0.1)
    @profile("demo_dynamic_arrow", "demo")
    def demo_dynamic_arrow(self, position=(0, 0)):
        angle = self.phase
        length = 100 + 50 * math.sin(self.phase)
        end = (math.cos(angle) * length, math.sin(angle) * length)
        Gizmos.draw_arrow((0, 0), end, 'orange', 4, True, 0.1)
        Gizmos.draw_text((end[0] + 20, end[1]), f"|Z|={length:.1f}", 'orange', 14, True, 0.1, True)
        Gizmos.draw_text((end[0], end[1] + 20), f"∠={math.degrees(angle):.1f}°", 'orange', 14, True, 0.1, True)
    @profile("demo_wavy_circle", "demo")
    def demo_wavy_circle(self, position=(0, 0)):
        num = 64
        R = 120
        for i in range(num):
            ang = 2 * math.pi * i / num
            offset = math.sin(self.phase * 4 + i * 0.4) * 20
            x = (R + offset) * math.cos(ang) - 400
            y = (R + offset) * math.sin(ang) + 200
            Gizmos.draw_circle((x, y), 2, 'blue', True, True, 0.1)
    @profile("demo_audio_bars", "demo")
    def demo_audio_bars(self, position=(0, 0)):
        bars = 32
        bw = 10
        for i in range(bars):
            freq = self.frequency + i * 0.3
            amp = abs(self._get_signal_value(self.phase, self.signal_types[self.signal_index], freq, self.amplitude)) * 0.5
            x = -300 + i * (bw + 2)
            Gizmos.draw_rect((x, -50), bw, amp, 'red', True, True, 0.1)
    @profile("demo_fractal_tree", "demo")
    def demo_fractal_tree(self, position=(0, 0)):
        def branch(x, y, length, angle, depth):
            if depth == 0:
                return
            rad = math.radians(angle)
            nx = x + math.cos(rad) * length
            ny = y + math.sin(rad) * length
            Gizmos.draw_line((x, y), (nx, ny), 'green', 2, True, 0.1)
            branch(nx, ny, length * 0.7, angle - 25, depth - 1)
            branch(nx, ny, length * 0.7, angle + 25, depth - 1)
        branch(0, 0, 60, -90, 6)
    @profile("demo_rotating_arrows", "demo")
    def demo_rotating_arrows(self, position=(0, 0)):
        center = (300, -300)
        arms = 10
        radius = 100 + 30 * math.sin(self.phase)
        for i in range(arms):
            ang = 2 * math.pi * i / arms + self.phase * 0.2
            end = (math.cos(ang) * radius + center[0], math.sin(ang) * radius + center[1])
            Gizmos.draw_arrow(center, end, 'red', 2, True, 0.1)
    @profile("demo_planet_orbits", "demo")
    def demo_planet_orbits(self, position=(0, 0)):
        center = (0, 0)
        for i in range(1, 10):
            orbit = i * 40
            ang = self.phase * (0.2 + i * 0.1)
            px = center[0] + math.cos(ang) * orbit
            py = center[1] + math.sin(ang) * orbit
            Gizmos.draw_circle((px, py), 8, 'yellow', True, True, 0.1)
            Gizmos.draw_circle(center, orbit, 'gray', False, 1, True, 0.1)
    @profile("demo_spring", "demo")
    def demo_spring(self, position=(0, 0)):
        pts = []
        turns = 20
        L = 300
        for i in range(turns):
            t = i / turns
            x = -200 + t * L
            y = math.sin(t * 10 * math.pi + self.phase * 5) * 20
            pts.append((x, y))
        for i in range(len(pts) - 1):
            Gizmos.draw_line(pts[i], pts[i + 1], 'orange', 2, True, 0.1)
    @profile("demo_wave_grid", "demo")
    def demo_wave_grid(self, position=(0, 0)):
        for x in range(-3, 4):
            for y in range(-3, 4):
                px, py = x * 50, y * 50
                dx = math.sin(py * 0.02 + self.phase) * 40
                dy = math.cos(px * 0.02 + self.phase) * 40
                Gizmos.draw_arrow((px, py), (px + dx, py + dy), 'purple', 1, True, 0.1)
    @profile("demo_rose_curve", "demo")
    def demo_rose_curve(self, position=(0, 0)):
        k = 5
        pts = []
        for deg in range(0, 360, 2):
            t = math.radians(deg)
            r = math.sin(k * t) * 80
            x = r * math.cos(t) + 500
            y = r * math.sin(t)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            Gizmos.draw_line(pts[i], pts[i + 1], 'purple', 2, True, 0.1)
    @profile("demo_am_signal", "demo")
    def demo_am_signal(self, position=(0, 0)):
        carrier = self.frequency * 4
        mod_f = self.frequency
        for i in range(self.sample_points):
            t = (i / self.sample_points) * 2.0 + self.phase
            mod = math.sin(t * mod_f * 2 * math.pi)
            amp = (mod + 1) * 0.5 * self.amplitude
            y = math.sin(t * carrier * 2 * math.pi) * amp
            x = -400 + (i / self.sample_points) * 800
            Gizmos.draw_circle((x, y), 2, 'white', True, True, 0.1)
    @profile("demo_lorenz_attractor", "demo")
    def demo_lorenz_attractor(self, position=(0, 0)):
        σ, ρ, β = 10.0, 28.0, 8 / 3
        h = 0.01
        x, y, z = self._lorenz_pts[-1]
        dx = σ * (y - x) * h
        dy = (x * (ρ - z) - y) * h
        dz = (x * y - β * z) * h
        self._lorenz_pts.append((x + dx, y + dy, z + dz))
        self._lorenz_pts = self._lorenz_pts[-2000:]
        for i in range(len(self._lorenz_pts) - 1):
            a = self._lorenz_pts[i]
            b = self._lorenz_pts[i + 1]
            Gizmos.draw_line((a[0] * 8 + 250, a[1] * 8), (b[0] * 8 + 250, b[1] * 8), 'white', 1, True, 0.1)

    @profile("demo_double_pendulum", "demo")
    def demo_double_pendulum(self, position=(0, 0)):
        import random
        import math

        g, L1, L2, m1, m2 = 9.8, 1.0, 1.0, 1.0, 1.0
        dt = 0.016

        if not hasattr(self, '_dp_pendulums'):
            self._dp_pendulums = []
            self._dp_trajectories = []
            self._dp_colors = ['red', 'blue', 'green', 'yellow', 'magenta', 'cyan', 'orange', 'purple']

        if not hasattr(self, '_dp_joint_count'):
            self._dp_joint_count = 0

        panel_x, panel_y = -450, 250
        btn_width, btn_height = 120, 40
        btn_spacing = 10

        def add_pendulum():
            if len(self._dp_pendulums) < 8:
                base_angle = math.pi / 2
                small_variation = random.uniform(-0.01, 0.01)
                new_state = [base_angle + small_variation, base_angle + small_variation, 0, 0]
                self._dp_pendulums.append(new_state)
                self._dp_trajectories.append([])
                self._dp_joint_count = len(self._dp_pendulums) * 2

        def clear_pendulums():
            self._dp_pendulums.clear()
            self._dp_trajectories.clear()
            self._dp_joint_count = 0

        def add_chaos_set():
            self._dp_pendulums.clear()
            self._dp_trajectories.clear()

            base_angle = math.pi / 2
            for i in range(5):
                variation = i * 0.001
                new_state = [base_angle + variation, base_angle + variation, 0, 0]
                self._dp_pendulums.append(new_state)
                self._dp_trajectories.append([])

            self._dp_joint_count = len(self._dp_pendulums) * 2

        def reset_pendulums():
            for i in range(len(self._dp_pendulums)):
                base_angle = math.pi / 2
                small_variation = random.uniform(-0.01, 0.01)
                self._dp_pendulums[i] = [base_angle + small_variation, base_angle + small_variation, 0, 0]
                self._dp_trajectories[i].clear()

        Gizmos.draw_button(
            position=(panel_x, panel_y),
            text="Add Pendulum",
            on_click=add_pendulum,
            width=btn_width, height=btn_height,
            font_size=14, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(panel_x + btn_width + btn_spacing, panel_y),
            text="Clear All",
            on_click=clear_pendulums,
            width=btn_width, height=btn_height,
            font_size=14, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(panel_x, panel_y - btn_height - btn_spacing),
            text="Add Chaos Set",
            on_click=add_chaos_set,
            width=btn_width, height=btn_height,
            font_size=14, font_world_space=True, world_space=True
        )

        Gizmos.draw_button(
            position=(panel_x + btn_width + btn_spacing, panel_y - btn_height - btn_spacing),
            text="Reset All",
            on_click=reset_pendulums,
            width=btn_width, height=btn_height,
            font_size=14, font_world_space=True, world_space=True
        )

        info_text = f"Pendulums: {len(self._dp_pendulums)}\nJoints: {self._dp_joint_count}"
        Gizmos.draw_text((panel_x, panel_y - 100), info_text, 'white', 16)

        for i, (state, trajectory) in enumerate(zip(self._dp_pendulums, self._dp_trajectories)):
            θ1, θ2, ω1, ω2 = state

            Δ = θ2 - θ1
            cos_Δ = math.cos(Δ)
            sin_Δ = math.sin(Δ)

            den1 = (m1 + m2) * L1 - m2 * L1 * cos_Δ * cos_Δ
            den2 = (L2 / L1) * den1

            num1 = (-m2 * L1 * ω1 * ω1 * sin_Δ * cos_Δ +
                    m2 * g * math.sin(θ2) * cos_Δ +
                    m2 * L2 * ω2 * ω2 * sin_Δ -
                    (m1 + m2) * g * math.sin(θ1))

            num2 = (-m2 * L2 * ω2 * ω2 * sin_Δ * cos_Δ +
                    (m1 + m2) * g * math.sin(θ1) * cos_Δ -
                    (m1 + m2) * L1 * ω1 * ω1 * sin_Δ -
                    (m1 + m2) * g * math.sin(θ2))

            α1 = num1 / den1
            α2 = num2 / den2

            ω1 += α1 * dt
            ω2 += α2 * dt
            θ1 += ω1 * dt
            θ2 += ω2 * dt

            self._dp_pendulums[i] = [θ1, θ2, ω1, ω2]

            origin = (0, 0)
            scale = 250

            p1 = (origin[0] + L1 * scale * math.sin(θ1),
                  origin[1] + L1 * scale * math.cos(θ1))
            p2 = (p1[0] + L2 * scale * math.sin(θ2),
                  p1[1] + L2 * scale * math.cos(θ2))

            trajectory.append(p2)

            if len(trajectory) > 100:
                trajectory.pop(0)

            color = self._dp_colors[i % len(self._dp_colors)]

            if len(trajectory) > 1:
                for j in range(1, len(trajectory)):
                    alpha = j / len(trajectory) * 0.4
                    Gizmos.draw_line(trajectory[j - 1], trajectory[j], color, 1, True, alpha)

            line_alpha = 0.6 if len(self._dp_pendulums) > 1 else 0.8
            Gizmos.draw_line(origin, p1, color, 4, True, line_alpha)
            Gizmos.draw_line(p1, p2, color, 4, True, line_alpha)

            bob_size = 8 if len(self._dp_pendulums) > 3 else 10
            Gizmos.draw_circle(p1, bob_size, color, True, True, 0.8)
            Gizmos.draw_circle(p2, bob_size, color, True, True, 0.9)

        if len(self._dp_pendulums) > 0:
            Gizmos.draw_circle((0, 0), 4, 'white', True, True, 0.9)
    @profile("demo_boids", "demo")
    def demo_boids(self, pos=(0, 0)):
        N = 20
        if self._boids is None:
            self._boids = [[random.uniform(-400, 400), random.uniform(-200, 200), random.uniform(-50, 50), random.uniform(-50, 50)] for _ in range(N)]
        align, coh, sep = 0.05, 0.01, 0.15
        for b in self._boids:
            px, py, vx, vy = b
            avg_vx = avg_vy = avg_px = avg_py = cx = cy = 0.0
            neighbors = 0
            for nb in self._boids:
                if nb is b:
                    continue
                dx, dy = nb[0] - px, nb[1] - py
                dist2 = dx * dx + dy * dy
                if dist2 < 16000:
                    neighbors += 1
                    avg_vx += nb[2]
                    avg_vy += nb[3]
                    avg_px += nb[0]
                    avg_py += nb[1]
                    if dist2 < 2500:
                        cx -= dx
                        cy -= dy
            if neighbors:
                vx += align * ((avg_vx / neighbors) - vx)
                vy += align * ((avg_vy / neighbors) - vy)
                vx += coh * ((avg_px / neighbors) - px)
                vy += coh * ((avg_py / neighbors) - py)
                vx += sep * cx
                vy += sep * cy
            speed = math.hypot(vx, vy)
            if speed > 80:
                vx *= 80 / speed
                vy *= 80 / speed
            b[0] += vx * 0.016
            b[1] += vy * 0.016
            b[2] = vx
            b[3] = vy
            b[0] = (b[0] + 500) % 1000 - 500
            b[1] = (b[1] + 400) % 800 - 400
            Gizmos.draw_arrow((b[0], b[1]), (b[0] + vx * 4, b[1] + vy * 4), 'cyan', 1, True, 0.1)
    @profile("demo_cube_wireframe", "demo")
    def demo_cube_wireframe(self, pos=(0, 0)):
        size = 100
        cx, cy = 250, 0
        ay = self.phase
        ax = self.phase * 0.7
        pts = []
        for dx in (-1, 1):
            for dy in (-1, 1):
                for dz in (-1, 1):
                    x, y, z = dx * size, dy * size, dz * size
                    xz = x * math.cos(ay) - z * math.sin(ay)
                    zz = x * math.sin(ay) + z * math.cos(ay)
                    yz = y * math.cos(ax) - zz * math.sin(ax)
                    zz2 = y * math.sin(ax) + zz * math.cos(ax)
                    f = 400 / (400 + zz2)
                    pts.append((cx + xz * f, cy + yz * f))
        edges = [(0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)]
        for a, b in edges:
            Gizmos.draw_line(pts[a], pts[b], 'white', 5, True, 0.1)
    @profile("demo_bubble_sort", "demo")
    def demo_bubble_sort(self, position=(0, 0)):
        if self._sort_arr is None:
            self._sort_arr = [random.uniform(20, 180) for _ in range(60)]
            self._sort_i = self._sort_j = 0
        arr = self._sort_arr
        i, j = self._sort_i, self._sort_j
        if i < len(arr) - 1:
            if j < len(arr) - i - 1:
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                self._sort_j += 1
            else:
                self._sort_j = 0
                self._sort_i += 1
        for idx, h in enumerate(arr):
            x = -450 + idx * 15
            Gizmos.draw_rect((x, -300), 10, h, 'green', True, True, 0.1)
    @profile("demo_vector_field", "demo")
    def demo_vector_field(self, position=(0, 0)):
        for gx in range(-6, 7):
            for gy in range(-4, 5):
                px, py = gx * 70, gy * 70
                dx = math.sin(py * 0.02 + self.phase) * 40
                dy = math.cos(px * 0.02 + self.phase) * 40
                Gizmos.draw_arrow((px, py), (px + dx, py + dy), 'purple', 1, True, 0.1)
    @profile("demo_game_of_life", "demo")
    def demo_game_of_life(self, position=(0, 0)):
        W, H = 50, 50
        if self._life_grid is None:
            self._life_grid = [[random.choice([0, 1]) for _ in range(W)] for _ in range(H)]
            self._life_timer = 0.0
        self._life_timer += 1
        if self._life_timer > 0.2:
            self._life_timer = 0.0
            nxt = [[0] * W for _ in range(H)]
            for y in range(H):
                for x in range(W):
                    s = sum(self._life_grid[(y + dy) % H][(x + dx) % W] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
                    nxt[y][x] = 1 if (s == 3 or (s == 2 and self._life_grid[y][x])) else 0
            self._life_grid = nxt
        for y in range(H):
            for x in range(W):
                if self._life_grid[y][x]:
                    Gizmos.draw_rect((x * 15 - 375, y * 15 - 225), 14, 14, 'white', True, True, 0.1)

    @profile("demo_barnsley_fern", "demo")
    def demo_barnsley_fern(self, position=(0, 0)):
        for _ in range(200):
            x, y = self._fern_pts[-1]
            r = random.random()
            if r < 0.01:
                x, y = 0.0, 0.16 * y
            elif r < 0.86:
                x, y = 0.85 * x + 0.04 * y, -0.04 * x + 0.85 * y + 1.6
            elif r < 0.93:
                x, y = 0.2 * x - 0.26 * y, 0.23 * x + 0.22 * y + 1.6
            else:
                x, y = -0.15 * x + 0.28 * y, 0.26 * x + 0.24 * y + 0.44
            self._fern_pts.append((x, y))
        self._fern_pts = self._fern_pts[-20000:]
        for (x, y) in self._fern_pts[-2000:]:
            Gizmos.draw_circle((x * 60 - 250, y * 60 - 340), 1,
                               'green', True, True, 0.1)
    @profile("demo_torus_knot", "demo")
    def demo_torus_knot(self, position=(0, 0)):
        n, m = 2, 3  # p, q
        R, r = 140, 40
        pts = []
        for deg in range(0, 360, 4):
            ang = math.radians(deg + self.phase * 30)
            x = (R + r * math.cos(m * ang)) * math.cos(n * ang) + 250
            y = (R + r * math.cos(m * ang)) * math.sin(n * ang) + 120
            z = r * math.sin(m * ang)
            scale = 1 + z / 120
            pts.append((x * scale, y * scale))
        for i in range(len(pts) - 1):
            Gizmos.draw_line(pts[i], pts[i + 1], 'red', 2, True, 0.1)
    @profile("demo_axes", "demo")
    def demo_axes(self, position=(0, 0)):
        Gizmos.draw_cross((0, 0), 200, 'red', 5, True, 0.1)
        Gizmos.draw_text((200, 0), "X", 'red', 100, True, 0.1, True)
        Gizmos.draw_text((0, -200), "Y", 'green', 100, True, 0.1, True)
    @profile("demo_rotating_circle_arrow", "demo")
    def demo_rotating_circle_arrow(self, position=(0, 0)):
        circle_pos = (math.cos(self.phase * 0.5) * 300, math.sin(self.phase * 0.5) * 300)
        Gizmos.draw_circle(circle_pos, 30, 'cyan', False, 2, True, 0.1)
        arrow_end = (math.cos(self.phase * 0.7) * 150, math.sin(self.phase * 0.7) * 150)
        Gizmos.draw_arrow((0, 0), arrow_end, 'magenta', 3, True, 0.1)
    @profile("demo_pulsing_text", "demo")
    def demo_pulsing_text(self, position=(0, 0)):
        scale = 2.0 + 0.5 * math.sin(self.phase * 2)
        Gizmos.draw_text((500, 0), "Pulsing Text", 'yellow', int(20 * scale), duration=True, font_world_space=True)
    @profile("demo_trail", "demo")
    def demo_trail(self, position=(0, 0)):
        pts = [(math.cos(self.phase + i * 0.5) * 400, math.sin(self.phase + i * 0.5) * 400) for i in range(20)]
        for i in range(len(pts) - 1):
            Gizmos.draw_line(pts[i], pts[i + 1], 'blue', 1, True, 0.1)
    @profile("demo_basic_shapes", "demo")
    def demo_basic_shapes(self, position=(0, 0)):
        Gizmos.draw_rect((-600, -400), 100, 50, 'orange', True, True, 0.1)
        tri = [(-600, -300), (-550, -300), (-575, -250)]
        for i in range(3):
            Gizmos.draw_line(tri[i], tri[(i + 1) % 3], 'purple', 3, True, 0.1)

    @profile("demo_hypercube", "demo")
    def demo_hypercube(self, position=(0, 0)):
        cx, cy = position
        angle_xy = self.phase * 0.3
        angle_xz = self.phase * 0.4
        angle_xw = self.phase * 0.5
        angle_yz = self.phase * 0.6
        angle_yw = self.phase * 0.7
        angle_zw = self.phase * 0.8

        vertices = []
        for w in [-1, 1]:
            for z in [-1, 1]:
                for y in [-1, 1]:
                    for x in [-1, 1]:
                        vertices.append([x, y, z, w])

        def rotate(p, a, b, angle):
            c, s = math.cos(angle), math.sin(angle)
            pa, pb = p[a], p[b]
            p[a] = pa * c - pb * s
            p[b] = pa * s + pb * c

        def project_4d_to_2d(point):
            p = point[:]
            rotate(p, 0, 1, angle_xy)
            rotate(p, 0, 2, angle_xz)
            rotate(p, 0, 3, angle_xw)
            rotate(p, 1, 2, angle_yz)
            rotate(p, 1, 3, angle_yw)
            rotate(p, 2, 3, angle_zw)

            x, y, z, w = p
            scale = 400 / (4 - w)
            sx = (x * scale) + cx
            sy = (y * scale) + cy
            sz = (z * scale)
            return (sx, sy, sz)

        projected = [project_4d_to_2d(v) for v in vertices]

        edges = []
        for i in range(len(vertices)):
            for j in range(i + 1, len(vertices)):
                diff = sum(abs(vertices[i][k] - vertices[j][k]) for k in range(4))
                if diff == 2:
                    edges.append((i, j))

        for a, b in edges:
            x1, y1, z1 = projected[a]
            x2, y2, z2 = projected[b]

            depth = (z1 + z2) / 2
            brightness = max(0.3, 1.0 - abs(depth) / 200)

            if vertices[a][3] == vertices[b][3]:
                if vertices[a][3] == 1:
                    color = (int(255 * brightness), int(100 * brightness), int(100 * brightness))
                else:
                    color = (int(100 * brightness), int(100 * brightness), int(255 * brightness))
            else:
                color = (int(100 * brightness), int(255 * brightness), int(100 * brightness))

            thickness = max(6, int(10 * brightness))

            Gizmos.draw_line((x1, y1), (x2, y2), color=color, thickness=thickness, duration=0.1)

        for i, (x, y, z) in enumerate(projected):
            w_coord = vertices[i][3]
            if w_coord == 1:
                vertex_color = (255, 150, 150)
            else:
                vertex_color = (150, 150, 255)

            depth_factor = max(0.4, 1.0 - abs(z) / 200)
            radius = int(16 * depth_factor)

            adjusted_color = (
                int(vertex_color[0] * depth_factor),
                int(vertex_color[1] * depth_factor),
                int(vertex_color[2] * depth_factor)
            )

            Gizmos.draw_circle((x, y), radius, color=adjusted_color, duration=0.1)

    @profile("demo_penteract", "demo")
    def demo_penteract(self, position=(0, 0)):
        cx, cy = position
        phase = self.phase
        angles = [phase * (0.3 + i * 0.1) for i in range(10)]

        vertices = [[x, y, z, w, v] for v in (-1, 1) for w in (-1, 1)
                    for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)]

        def rotate(p, i, j, angle):
            c, s = math.cos(angle), math.sin(angle)
            pi, pj = p[i], p[j]
            p[i] = pi * c - pj * s
            p[j] = pi * s + pj * c

        def project_5d_to_2d(point):
            p = point[:]
            idx = 0
            for i in range(5):
                for j in range(i + 1, 5):
                    rotate(p, i, j, angles[idx])
                    idx += 1
            x, y, z, w, v = p
            scale = 300 / (5 - v)
            sx = x * scale + cx
            sy = y * scale + cy
            sz = (z + w) * scale * 0.5
            return (sx, sy, sz)

        projected = [project_5d_to_2d(v) for v in vertices]

        edges = []
        n = len(vertices)
        for i in range(n):
            for j in range(i + 1, n):
                diff = sum(abs(vertices[i][k] - vertices[j][k]) for k in range(5))
                if diff == 2:
                    edges.append((i, j))

        for a, b in edges:
            x1, y1, z1 = projected[a]
            x2, y2, z2 = projected[b]
            depth = (z1 + z2) * 0.5
            brightness = max(0.3, 1.0 - abs(depth) / 250)
            v_a, v_b = vertices[a][4], vertices[b][4]
            if v_a == v_b:
                base = (255, 100, 100) if v_a == 1 else (100, 100, 255)
            else:
                base = (100, 255, 100)
            color = tuple(int(c * brightness) for c in base)
            thickness = max(5, int(9 * brightness))
            Gizmos.draw_line((x1, y1), (x2, y2), color=color, thickness=thickness, duration=0.1)

        for i, (x, y, z) in enumerate(projected):
            v_coord = vertices[i][4]
            base_color = (255, 150, 150) if v_coord == 1 else (150, 150, 255)
            depth_factor = max(0.4, 1.0 - abs(z) / 250)
            radius = int(14 * depth_factor)
            color = tuple(int(c * depth_factor) for c in base_color)
            Gizmos.draw_circle((x, y), radius, color=color, duration=0.1)
    @profile("demo_langton_ant", "demo")
    def demo_langton_ant(self, position=(0, 0)):
        if not hasattr(self, 'grid_size'):
            self.grid_size = 30
        cell_size = 10
        def plus():
            self.grid_size += 1
            self._langton_grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
            self._langton_ant_pos = [self.grid_size // 2, self.grid_size // 2]
            self._langton_dir = 0
        def minus():
            if self.grid_size > 1:
                self.grid_size -= 1
                self._langton_grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
                self._langton_ant_pos = [self.grid_size // 2, self.grid_size // 2]
                self._langton_dir = 0
        Gizmos.draw_button(
            position=(position[0] + 300, position[1] + 100),
            text="+",
            on_click=plus,
            width=50,
            height=50,
            font_size=38,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(position[0] + 300, position[1] + 160),
            text="-",
            on_click=minus,
            width=50,
            height=50,
            font_size=38,
            font_world_space=True,
            world_space=True
        )
        cx, cy = position
        if self._langton_ant_pos is None:
            self._langton_ant_pos = [self.grid_size // 2, self.grid_size // 2]
            self._langton_ant_dir = 0  # 0: up, 1: right, 2: down, 3: left
            self._langton_grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
            self._langton_steps = 0
        x, y = self._langton_ant_pos
        direction = self._langton_ant_dir
        if self._langton_grid[y][x] == 0:
            direction = (direction + 1) % 4
            self._langton_grid[y][x] = 1
        else:
            direction = (direction - 1) % 4
            self._langton_grid[y][x] = 0
        self._langton_ant_dir = direction
        dx, dy = self._langton_directions[direction]
        x += dx
        y += dy
        if not (0 <= x < self.grid_size and 0 <= y < self.grid_size):
            self._langton_ant_pos = [self.grid_size // 2, self.grid_size // 2]
            self._langton_ant_dir = 0
            self._langton_grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
            self._langton_steps = 0
            return
        self._langton_ant_pos = [x, y]
        self._langton_steps += 1
        for gy in range(self.grid_size):
            for gx in range(self.grid_size):
                px = gx * cell_size + cx - self.grid_size * cell_size // 2
                py = gy * cell_size + cy - self.grid_size * cell_size // 2
                color = 'black' if self._langton_grid[gy][gx] else 'white'
                Gizmos.draw_rect((px, py), cell_size, cell_size, color, True, True, 0.1)
        ax, ay = self._langton_ant_pos
        px = ax * cell_size + cx - self.grid_size * cell_size // 2
        py = ay * cell_size + cy - self.grid_size * cell_size // 2
        Gizmos.draw_circle((px + cell_size // 2, py + cell_size // 2), 3, 'red', True, True, 0.1)

    @profile("demo_piano", "demo")
    def demo_piano(self, position=(0, 0)):
        key_width = 40
        key_height = 160
        black_key_width = 28
        black_key_height = 100
        spacing = 2
        base_x, base_y = position
        white_key_index = 0
        white_key_positions = {}
        for i, (note, is_black) in enumerate(self.notes):
            if not is_black:
                x = base_x + white_key_index * (key_width + spacing)
                y = base_y
                white_key_positions[note] = x
                def make_on_click(n=note):
                    return lambda: synthesizer.play_note(
                        n, duration=0.2, waveform='sine',
                        adsr=(0.01, 0.1, 0.7, 0.1),
                        volume=0.5, detune=0.0, apply_effects=False, pan=0.0
                    )
                Gizmos.draw_button(
                    position=(x, y),
                    text=note,
                    on_click=make_on_click(),
                    width=key_width,
                    height=key_height,
                    font_name="Consolas",
                    font_size=14,
                    font_world_space=True,
                    color='black',
                    background_color=(240, 240, 240, 255),
                    pressed_background_color=(100, 100, 100, 255),
                    world_space=True
                )
                white_key_index += 1
        black_key_mapping = {
            'C#4': 'C4',
            'D#4': 'D4',
            'F#4': 'F4',
            'G#4': 'G4',
            'A#4': 'A4',
        }
        for note, is_black in self.notes:
            if is_black:
                left_note = black_key_mapping.get(note)
                if left_note in white_key_positions:
                    x = white_key_positions[left_note] + key_width - black_key_width // 2
                    y = base_y
                    def make_on_click(n=note):
                        return lambda: synthesizer.play_note(
                            n, duration=0.2, waveform='sine',
                            adsr=(0.01, 0.1, 0.7, 0.1),
                            volume=0.5, detune=0.0, apply_effects=False, pan=0.0
                        )
                    Gizmos.draw_button(
                        position=(x, y),
                        text=note,
                        on_click=make_on_click(),
                        width=black_key_width,
                        height=black_key_height,
                        font_name="Consolas",
                        font_size=12,
                        font_world_space=True,
                        color='white',
                        background_color=(10, 10, 10, 255),
                        pressed_background_color=(100, 100, 100, 255),
                        world_space=True
                    )
    @profile("demo_graphing_calculator", "demo")
    def demo_graphing_calculator(self, position=(0, 0)):
        self.draw_controls()
        if not hasattr(self, '_calc_function_index'):
            self._calc_function_index = 0
            self._calc_scale = 100.0
            self._calc_offset_x = 0.0
            self._calc_offset_y = 0.0
            self._calc_frequency = 1.0
            self._calc_amplitude = 1.0
            self._calc_show_grid = True
            self._calc_show_axes = True
            self._calc_resolution = 1
        functions = [
            ("sin(x)", lambda x: math.sin(x)),
            ("cos(x)", lambda x: math.cos(x)),
            ("tan(x)", lambda x: math.tan(x) if abs(math.cos(x)) > 0.01 else 0),
            ("x²", lambda x: x * x),
            ("x³", lambda x: x * x * x),
            ("√x", lambda x: math.sqrt(abs(x))),
            ("1/x", lambda x: 1 / x if abs(x) > 0.01 else 0),
            ("e^x", lambda x: math.exp(min(x, 10))),
            ("ln(x)", lambda x: math.log(abs(x)) if abs(x) > 0.01 else 0),
            ("x*sin(x)", lambda x: x * math.sin(x)),
            ("sin(x)/x", lambda x: math.sin(x) / x if abs(x) > 0.01 else 1),
            ("|x|", lambda x: abs(x))
        ]
        cx, cy = position
        def next_function():
            self._calc_function_index = (self._calc_function_index + 1) % len(functions)
        def prev_function():
            self._calc_function_index = (self._calc_function_index - 1) % len(functions)
        Gizmos.draw_button(
            position=(cx - 400, cy - 400),
            text="◀",
            on_click=prev_function,
            width=40, height=40,
            font_size=20,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx + 360, cy - 400),
            text="▶",
            on_click=next_function,
            width=40, height=40,
            font_size=20,
            font_world_space=True,
            world_space=True
        )
        current_func_name = functions[self._calc_function_index][0]
        Gizmos.draw_text(
            position=(cx, cy - 400),
            text=f"f(x) = {current_func_name}",
            font_size=20,
            color='white',
            font_world_space=True,
            world_space=True,
            duration=0.1
        )
        def zoom_in():
            self._calc_scale *= 1.2
        def zoom_out():
            self._calc_scale *= 0.8
        Gizmos.draw_button(
            position=(cx - 400, cy - 350),
            text="Zoom +",
            on_click=zoom_in,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx - 300, cy - 350),
            text="Zoom -",
            on_click=zoom_out,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        def freq_up():
            self._calc_frequency *= 1.2
        def freq_down():
            self._calc_frequency *= 0.8
        Gizmos.draw_button(
            position=(cx - 200, cy - 350),
            text="Freq +",
            on_click=freq_up,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx - 100, cy - 350),
            text="Freq -",
            on_click=freq_down,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        def amp_up():
            self._calc_amplitude *= 1.2
        def amp_down():
            self._calc_amplitude *= 0.8
        Gizmos.draw_button(
            position=(cx, cy - 350),
            text="Amp +",
            on_click=amp_up,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx + 100, cy - 350),
            text="Amp -",
            on_click=amp_down,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        def move_left():
            self._calc_offset_x -= 10
        def move_right():
            self._calc_offset_x += 10
        def move_up():
            self._calc_offset_y -= 10
        def move_down():
            self._calc_offset_y += 10
        Gizmos.draw_button(
            position=(cx + 200, cy - 380),
            text="↑",
            on_click=move_up,
            width=30, height=30,
            font_size=16,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx + 170, cy - 350),
            text="←",
            on_click=move_left,
            width=30, height=30,
            font_size=16,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx + 230, cy - 350),
            text="→",
            on_click=move_right,
            width=30, height=30,
            font_size=16,
            font_world_space=True,
            world_space=True
        )
        Gizmos.draw_button(
            position=(cx + 200, cy - 320),
            text="↓",
            on_click=move_down,
            width=30, height=30,
            font_size=16,
            font_world_space=True,
            world_space=True
        )
        def reset():
            self._calc_scale = 100.0
            self._calc_offset_x = 0.0
            self._calc_offset_y = 0.0
            self._calc_frequency = 1.0
            self._calc_amplitude = 1.0
        Gizmos.draw_button(
            position=(cx + 300, cy - 350),
            text="Reset",
            on_click=reset,
            width=80, height=30,
            font_size=12,
            font_world_space=True,
            world_space=True
        )
        def toggle_axes():
            self._calc_show_axes = not self._calc_show_axes
        Gizmos.draw_button(
            position=(cx - 300, cy - 300),
            text=f"Axes: {'ON' if self._calc_show_axes else 'OFF'}",
            on_click=toggle_axes,
            width=80, height=30,
            font_size=10,
            font_world_space=True,
            world_space=True
        )
        current_func = functions[self._calc_function_index][1]
        points = []
        for screen_x in range(int(cx - 400), int(cx + 400), self._calc_resolution):
            math_x = (screen_x - cx - self._calc_offset_x) / self._calc_scale * self._calc_frequency
            try:
                math_y = current_func(math_x) * self._calc_amplitude
                screen_y = cy - math_y * self._calc_scale + self._calc_offset_y
                if -400 <= screen_y <= 400:
                    points.append((screen_x, screen_y))
            except:
                continue
        if len(points) > 1:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                if abs(y2 - y1) < 200:
                    color_map = {
                        0: (255, 100, 100),  # sin - красный
                        1: (100, 255, 100),  # cos - зеленый
                        2: (100, 100, 255),  # tan - синий
                        3: (255, 255, 100),  # x² - желтый
                        4: (255, 100, 255),  # x³ - фиолетовый
                        5: (100, 255, 255),  # √x - голубой
                        6: (255, 150, 100),  # 1/x - оранжевый
                        7: (200, 100, 255),  # e^x - лиловый
                        8: (100, 200, 100),  # ln(x) - темно-зеленый
                        9: (255, 200, 100),  # x*sin(x) - персиковый
                        10: (100, 150, 255),  # sin(x)/x - светло-синий
                        11: (200, 200, 200)  # |x| - серый
                    }
                    line_color = color_map.get(self._calc_function_index, (255, 255, 255))
                    Gizmos.draw_line(
                        (x1, y1), (x2, y2),
                        color=line_color, thickness=3, duration=0.1
                    )
        for x, y in points[::5]:
            Gizmos.draw_circle(
                (x, y), 2,
                color=(255, 255, 255), filled=True, duration=0.1
            )
        info_text = [
            f"Function: {current_func_name}",
            f"Scale: {self._calc_scale:.1f}",
            f"Frequency: {self._calc_frequency:.2f}",
            f"Amplitude: {self._calc_amplitude:.2f}",
            f"Offset: ({self._calc_offset_x:.0f}, {self._calc_offset_y:.0f})"
        ]
        for i, text in enumerate(info_text):
            Gizmos.draw_text(
                position=(cx - 400, cy + 250 + i * 20),
                text=text,
                font_size=12,
                color='white',
                font_world_space=True,
                world_space=True,
                duration=0.1
            )
        help_text = [
            "Controls:",
            "◀▶ - Change function",
            "Zoom +/- - Scale graph",
            "Freq +/- - Change frequency",
            "Amp +/- - Change amplitude",
            "Arrow keys - Move graph",
            "Reset - Reset all parameters"
        ]
        for i, text in enumerate(help_text):
            Gizmos.draw_text(
                position=(cx + 100, cy + 200 + i * 20),
                text=text,
                font_size=10,
                color=(200, 200, 200),
                font_world_space=True,
                world_space=True,
                duration=0.1
            )

    @profile("quantum_mandala", "demo")
    def quantum_mandala(self, position=(0, 0)):
        if not hasattr(self, '_qm_phase'):
            self._qm_phase = 0
            self._qm_particles = []
            self._qm_quantum_state = 0
            self._qm_energy = 1.0
            self._qm_dimension = 0

        self._qm_phase += 0.05
        self._qm_quantum_state += 0.02
        cx, cy = position

        for layer in range(7):
            radius = 50 + layer * 80
            nodes = 8 + layer * 4
            quantum_offset = math.sin(self._qm_quantum_state + layer * 0.5) * 20

            for i in range(nodes):
                angle = (i / nodes) * 2 * math.pi + self._qm_phase * (1 + layer * 0.3)
                x = cx + (radius + quantum_offset) * math.cos(angle)
                y = cy + (radius + quantum_offset) * math.sin(angle)

                inner_radius = 15 + math.sin(self._qm_phase * 3 + i * 0.3) * 8
                color_hue = (self._qm_phase * 50 + layer * 60 + i * 20) % 360
                r = int(127 + 127 * math.sin(math.radians(color_hue)))
                g = int(127 + 127 * math.sin(math.radians(color_hue + 120)))
                b = int(127 + 127 * math.sin(math.radians(color_hue + 240)))

                Gizmos.draw_circle((x, y), inner_radius, color=(r, g, b), filled=True, duration=0.1)

                if layer > 0:
                    prev_angle = ((i - 1) / nodes) * 2 * math.pi + self._qm_phase * (1 + layer * 0.3)
                    prev_x = cx + (radius + quantum_offset) * math.cos(prev_angle)
                    prev_y = cy + (radius + quantum_offset) * math.sin(prev_angle)
                    Gizmos.draw_line((x, y), (prev_x, prev_y), color=(r // 2, g // 2, b // 2), thickness=5,
                                     duration=0.1)

                if layer < 6:
                    next_layer_angle = (i / (nodes + 4)) * 2 * math.pi + self._qm_phase * (1 + (layer + 1) * 0.3)
                    next_radius = 50 + (layer + 1) * 80
                    next_quantum = math.sin(self._qm_quantum_state + (layer + 1) * 0.5) * 20
                    next_x = cx + (next_radius + next_quantum) * math.cos(next_layer_angle)
                    next_y = cy + (next_radius + next_quantum) * math.sin(next_layer_angle)
                    Gizmos.draw_line((x, y), (next_x, next_y), color=(r // 3, g // 3, b // 3), thickness=4,
                                     duration=0.1)

        for i in range(20):
            spiral_angle = self._qm_phase * 2 + i * 0.8
            spiral_radius = 30 + i * 15
            sx = cx + spiral_radius * math.cos(spiral_angle)
            sy = cy + spiral_radius * math.sin(spiral_angle)

            energy_pulse = math.sin(self._qm_phase * 4 + i * 0.2) * 0.5 + 0.5
            size = 3 + energy_pulse * 8
            intensity = int(100 + energy_pulse * 155)

            Gizmos.draw_point((sx, sy), color=(intensity, intensity // 2, intensity), size=size, duration=0.1)

        center_energy = math.sin(self._qm_phase * 5) * 0.3 + 0.7
        center_size = 25 + center_energy * 15
        center_color = (int(255 * center_energy), int(200 * center_energy), int(100 * center_energy))
        Gizmos.draw_circle((cx, cy), center_size, color=center_color, filled=True, duration=0.1)

        for dim in range(4):
            dim_angle = self._qm_phase + dim * math.pi / 2
            dim_x = cx + 400 * math.cos(dim_angle)
            dim_y = cy + 400 * math.sin(dim_angle)

            portal_size = 20 + math.sin(self._qm_phase * 3 + dim) * 10
            portal_color = (
                int(100 + 100 * math.sin(dim_angle)),
                int(100 + 100 * math.cos(dim_angle)),
                int(150 + 50 * math.sin(dim_angle + math.pi / 4))
            )

            Gizmos.draw_circle((dim_x, dim_y), portal_size, color=portal_color, filled=True, duration=0.1)
            Gizmos.draw_line((cx, cy), (dim_x, dim_y),
                             color=(portal_color[0] // 2, portal_color[1] // 2, portal_color[2] // 2), thickness=3,
                             duration=0.1)

        if len(self._qm_particles) < 30:
            self._qm_particles.append({
                'angle': random.random() * 2 * math.pi,
                'radius': random.uniform(100, 300),
                'speed': random.uniform(0.01, 0.05),
                'color': (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            })

        for particle in self._qm_particles:
            particle['angle'] += particle['speed']
            px = cx + particle['radius'] * math.cos(particle['angle'])
            py = cy + particle['radius'] * math.sin(particle['angle'])
            Gizmos.draw_point((px, py), color=particle['color'], size=2, duration=0.1)

        quantum_text = f"Quantum State: {self._qm_quantum_state:.2f}"
        Gizmos.draw_text((cx - 200, cy - 500), quantum_text, color='white', font_size=16, duration=0.1)

    @profile("demo_quantum_swarm", "demo")
    def demo_quantum_swarm(self, position=(0, 0)):
        if not hasattr(self, '_quantum_particles'):
            self._quantum_particles = []
            self._quantum_attractors = []
            self._quantum_phase = 0
            self._quantum_energy = 0
            for i in range(150):
                self._quantum_particles.append({
                    'pos': [random.uniform(-800, 800), random.uniform(-600, 600)],
                    'vel': [random.uniform(-2, 2), random.uniform(-2, 2)],
                    'quantum_state': random.random(),
                    'entangled_with': random.randint(0, 149),
                    'spin': random.choice([-1, 1]),
                    'energy': random.uniform(0.1, 1.0),
                    'tunnel_prob': random.random(),
                    'wave_func': random.random() * 2 * math.pi
                })
            for i in range(8):
                self._quantum_attractors.append({
                    'pos': [random.uniform(-600, 600), random.uniform(-400, 400)],
                    'strength': random.uniform(0.5, 2.0),
                    'frequency': random.uniform(0.1, 0.5),
                    'phase': random.random() * 2 * math.pi,
                    'type': random.choice(['attract', 'repel', 'vortex'])
                })

        self._quantum_phase += 0.03
        self._quantum_energy = (math.sin(self._quantum_phase * 0.7) + 1) * 0.5

        for attractor in self._quantum_attractors:
            attractor['phase'] += attractor['frequency']
            pulse = math.sin(attractor['phase']) * 0.3 + 0.7
            size = 20 + pulse * 15

            if attractor['type'] == 'attract':
                color = (int(255 * pulse), int(100 * pulse), int(255 * (1 - pulse)))
            elif attractor['type'] == 'repel':
                color = (int(255 * pulse), int(255 * (1 - pulse)), int(100 * pulse))
            else:
                color = (int(255 * pulse), int(255 * pulse), int(255 * (1 - pulse)))

            Gizmos.draw_circle(attractor['pos'], size, color=color, filled=True, duration=0.1)

            for i in range(12):
                angle = (i * 30 + attractor['phase'] * 180 / math.pi) * math.pi / 180
                if attractor['type'] == 'vortex':
                    angle += self._quantum_phase * 2
                spiral_x = attractor['pos'][0] + math.cos(angle) * size * 1.5
                spiral_y = attractor['pos'][1] + math.sin(angle) * size * 1.5
                Gizmos.draw_line(attractor['pos'], (spiral_x, spiral_y), color=color, thickness=2, duration=0.1)

        entanglement_pairs = set()
        for i, particle in enumerate(self._quantum_particles):
            particle['wave_func'] += 0.1 + particle['energy'] * 0.05

            for attractor in self._quantum_attractors:
                dx = attractor['pos'][0] - particle['pos'][0]
                dy = attractor['pos'][1] - particle['pos'][1]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist > 0:
                    force_magnitude = attractor['strength'] * 100 / (dist * dist + 1)

                    if attractor['type'] == 'attract':
                        force_x = dx * force_magnitude / dist
                        force_y = dy * force_magnitude / dist
                    elif attractor['type'] == 'repel':
                        force_x = -dx * force_magnitude / dist
                        force_y = -dy * force_magnitude / dist
                    else:
                        force_x = -dy * force_magnitude / dist
                        force_y = dx * force_magnitude / dist

                    particle['vel'][0] += force_x * 0.01
                    particle['vel'][1] += force_y * 0.01

            if random.random() < particle['tunnel_prob'] * 0.001:
                particle['pos'][0] = random.uniform(-800, 800)
                particle['pos'][1] = random.uniform(-600, 600)
                particle['vel'][0] *= 0.1
                particle['vel'][1] *= 0.1

            particle['quantum_state'] = (particle['quantum_state'] + 0.01) % 1.0

            if particle['quantum_state'] < 0.3:
                uncertainty = 50 * (0.3 - particle['quantum_state'])
                particle['pos'][0] += random.uniform(-uncertainty, uncertainty)
                particle['pos'][1] += random.uniform(-uncertainty, uncertainty)

            particle['vel'][0] *= 0.99
            particle['vel'][1] *= 0.99
            particle['pos'][0] += particle['vel'][0]
            particle['pos'][1] += particle['vel'][1]

            if abs(particle['pos'][0]) > 850:
                particle['vel'][0] *= -0.8
            if abs(particle['pos'][1]) > 650:
                particle['vel'][1] *= -0.8

            wave_amplitude = math.sin(particle['wave_func']) * 20
            interference = math.sin(particle['wave_func'] + self._quantum_phase) * 10

            probability = particle['quantum_state']
            if probability > 0.7:
                alpha = int(255 * (probability - 0.7) / 0.3)
                color = (255, 255, 255, alpha)
            else:
                intensity = int(255 * probability)
                color = (intensity, intensity // 2, 255 - intensity // 2)

            size = 2 + abs(wave_amplitude) * 0.1 + particle['energy'] * 3

            Gizmos.draw_circle(particle['pos'], size, color=color, filled=True, duration=0.1)

            if particle['spin'] == 1:
                Gizmos.draw_circle(particle['pos'], size + 5, color=(255, 255, 255, 50), filled=False, thickness=1,
                                   duration=0.1)

            for j in range(6):
                angle = j * 60 + particle['wave_func'] * 180 / math.pi
                wave_x = particle['pos'][0] + math.cos(angle * math.pi / 180) * wave_amplitude
                wave_y = particle['pos'][1] + math.sin(angle * math.pi / 180) * wave_amplitude
                Gizmos.draw_line(particle['pos'], (wave_x, wave_y), color=(100, 200, 255, 100), thickness=1,
                                 duration=0.1)

            entangled_idx = particle['entangled_with']
            if entangled_idx != i and entangled_idx < len(self._quantum_particles):
                pair = tuple(sorted([i, entangled_idx]))
                if pair not in entanglement_pairs:
                    entanglement_pairs.add(pair)
                    entangled = self._quantum_particles[entangled_idx]
                    dist = math.sqrt((particle['pos'][0] - entangled['pos'][0]) ** 2 + (
                                particle['pos'][1] - entangled['pos'][1]) ** 2)
                    if dist < 200:
                        connection_strength = 1.0 - dist / 200
                        color_intensity = int(255 * connection_strength)
                        entangle_color = (255, color_intensity, 0, int(100 * connection_strength))
                        Gizmos.draw_line(particle['pos'], entangled['pos'], color=entangle_color, thickness=2,
                                         duration=0.1)

                        mid_x = (particle['pos'][0] + entangled['pos'][0]) / 2
                        mid_y = (particle['pos'][1] + entangled['pos'][1]) / 2
                        Gizmos.draw_circle((mid_x, mid_y), 3, color=(255, 255, 0), filled=True, duration=0.1)

        energy_bar_width = 400
        energy_bar_height = 20
        energy_fill = int(energy_bar_width * self._quantum_energy)

        Gizmos.draw_rect((-600, -650), energy_bar_width, energy_bar_height, color=(50, 50, 50), filled=True,
                         duration=0.1)
        Gizmos.draw_rect((-600 + energy_fill // 2, -650), energy_fill, energy_bar_height, color=(255, 100, 255),
                         filled=True, duration=0.1)

        Gizmos.draw_text((-600, -680), f"Quantum Energy: {self._quantum_energy:.2f}", color=(255, 255, 255),
                         font_size=12, font_world_space=True, world_space=True, duration=0.1)

        field_strength = self._quantum_energy * 50
        for x in range(-800, 801, 100):
            for y in range(-600, 601, 100):
                field_x = math.sin(x * 0.01 + self._quantum_phase) * field_strength
                field_y = math.cos(y * 0.01 + self._quantum_phase) * field_strength
                Gizmos.draw_arrow((x, y), (x + field_x, y + field_y), color=(100, 255, 100, 50), thickness=1,
                                  duration=0.1)

    @profile("demo_quantum_fractal", "demo")
    def demo_quantum_fractal(self, position=(0, 0)):

        self._qf_energy:float
        self._qf_quantum_states:list
        self._qf_field_strength:float
        self._qf_dimension = 3
        self._qf_collapse_prob = 0.02
        self._qf_time += 0.016
        cx, cy = position
        def quantum_wave(x, y, t, freq=1.0, amplitude=100.0):
            return amplitude * math.sin(freq * math.sqrt(x * x + y * y) - t * 5) * math.exp(
                -math.sqrt(x * x + y * y) * 0.002)
        def strange_attractor(x, y, z, dt=0.01):
            a, b, c = 10.0, 28.0, 8.0 / 3.0
            dx = a * (y - x)
            dy = x * (b - z) - y
            dz = x * y - c * z
            return x + dx * dt, y + dy * dt, z + dz * dt
        def fractal_dimension(x, y, iterations=50):
            zx, zy = x, y
            for i in range(iterations):
                if zx * zx + zy * zy > 4:
                    return i
                zx, zy = zx * zx - zy * zy + x, 2 * zx * zy + y
            return iterations
        def hsv_to_rgb(h, s, v):
            c = v * s
            x = c * (1 - abs((h / 60) % 2 - 1))
            m = v - c
            if 0 <= h < 60:
                r, g, b = c, x, 0
            elif 60 <= h < 120:
                r, g, b = x, c, 0
            elif 120 <= h < 180:
                r, g, b = 0, c, x
            elif 180 <= h < 240:
                r, g, b = 0, x, c
            elif 240 <= h < 300:
                r, g, b = x, 0, c
            else:
                r, g, b = c, 0, x
            return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
        if len(self._qf_nodes) < 200:
            angle = self._qf_time * 0.3 + len(self._qf_nodes) * 0.1
            radius = 50 + len(self._qf_nodes) * 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            z = 100 * math.sin(self._qf_time * 0.5 + len(self._qf_nodes) * 0.05)
            self._qf_nodes.append([x, y, z, angle, radius])

            if len(self._qf_nodes) > 1:
                self._qf_connections.append([len(self._qf_nodes) - 2, len(self._qf_nodes) - 1])
        for i in range(min(20, len(self._qf_nodes))):
            if random.random() < 0.1:
                node = self._qf_nodes[i]
                vx = random.uniform(-2, 2)
                vy = random.uniform(-2, 2)
                vz = random.uniform(-1, 1)
                life = random.uniform(2, 5)
                self._qf_particles.append([node[0], node[1], node[2], vx, vy, vz, life, life])
        for particle in self._qf_particles[:]:
            particle[0] += particle[3]
            particle[1] += particle[4]
            particle[2] += particle[5]
            particle[3] *= 0.99
            particle[4] *= 0.99
            particle[5] *= 0.99
            particle[6] -= 0.016
            if particle[6] <= 0:
                self._qf_particles.remove(particle)
        for node in self._qf_nodes:
            node[0] += 0.5 * math.sin(self._qf_time * 0.8 + node[3])
            node[1] += 0.5 * math.cos(self._qf_time * 0.7 + node[3])
            node[2] += 2 * math.sin(self._qf_time * 0.6 + node[3] * 0.5)
            node[3] += 0.01
            node[4] += 0.1
        for y in range(-300, 300, 30):
            for x in range(-300, 300, 30):
                world_x = cx + x
                world_y = cy + y
                wave_val = quantum_wave(x / 100, y / 100, self._qf_time)
                if abs(wave_val) > 20:
                    fractal_val = fractal_dimension(x / 200, y / 200)
                    hue = (fractal_val * 30 + self._qf_time * 50) % 360
                    color = hsv_to_rgb(hue, 0.8, min(1.0, abs(wave_val) / 50))
                    size = max(1, min(8, abs(wave_val) / 10))
                    Gizmos.draw_circle((world_x, world_y), size, color=color, filled=True, duration=0.1)
        for i, node in enumerate(self._qf_nodes):
            proj_x = node[0] + node[2] * 0.3
            proj_y = node[1] + node[2] * 0.2
            distance_from_center = math.sqrt((node[0] - cx) ** 2 + (node[1] - cy) ** 2)
            energy_level = math.sin(self._qf_time * 2 + i * 0.1) * 0.5 + 0.5
            hue = (i * 10 + self._qf_time * 30) % 360
            color = hsv_to_rgb(hue, 0.9, energy_level)
            radius = 3 + energy_level * 5 + math.sin(self._qf_time * 3 + i * 0.2) * 2
            Gizmos.draw_circle((proj_x, proj_y), radius, color=color, filled=True, duration=0.1)
            if random.random() < self._qf_collapse_prob:
                explosion_size = 50 + energy_level * 30
                Gizmos.draw_circle((proj_x, proj_y), explosion_size, color=color, filled=False, thickness=3,
                                   duration=0.1)
            if i > 0:
                Gizmos.draw_line((proj_x, proj_y), (self._qf_nodes[i - 1][0] + self._qf_nodes[i - 1][2] * 0.3,
                                                    self._qf_nodes[i - 1][1] + self._qf_nodes[i - 1][2] * 0.2),
                                 color=color, thickness=2, duration=0.1)
        for conn in self._qf_connections:
            if conn[0] < len(self._qf_nodes) and conn[1] < len(self._qf_nodes):
                n1, n2 = self._qf_nodes[conn[0]], self._qf_nodes[conn[1]]
                distance = math.sqrt((n1[0] - n2[0]) ** 2 + (n1[1] - n2[1]) ** 2)
                if distance < 100:
                    energy_flow = math.sin(self._qf_time * 5 + distance * 0.1) * 0.5 + 0.5
                    color = hsv_to_rgb((distance + self._qf_time * 20) % 360, 0.7, energy_flow)
                    thickness = max(1, int(energy_flow * 5))
                    Gizmos.draw_arrow((n1[0], n1[1]), (n2[0], n2[1]), color=color, thickness=thickness, duration=0.1)
        for particle in self._qf_particles:
            life_ratio = particle[6] / particle[7]
            hue = (self._qf_time * 100 + particle[0] * 0.1) % 360
            color = hsv_to_rgb(hue, 0.9, life_ratio)
            size = life_ratio * 4 + 1
            Gizmos.draw_point((particle[0], particle[1]), color=color, size=size, duration=0.1)

            if random.random() < 0.3:
                trail_x = particle[0] - particle[3] * 5
                trail_y = particle[1] - particle[4] * 5
                Gizmos.draw_line((particle[0], particle[1]), (trail_x, trail_y), color=color, thickness=1, duration=0.1)
        for angle in range(0, 360, 5):
            rad = math.radians(angle)
            base_radius = 200
            wave_offset = quantum_wave(math.cos(rad), math.sin(rad), self._qf_time, 2.0, 20.0)
            radius = base_radius + wave_offset
            x = cx + radius * math.cos(rad)
            y = cy + radius * math.sin(rad)
            next_angle = angle + 5
            next_rad = math.radians(next_angle)
            next_wave_offset = quantum_wave(math.cos(next_rad), math.sin(next_rad), self._qf_time, 2.0, 20.0)
            next_radius = base_radius + next_wave_offset
            next_x = cx + next_radius * math.cos(next_rad)
            next_y = cy + next_radius * math.sin(next_rad)
            hue = (angle + self._qf_time * 40) % 360
            color = hsv_to_rgb(hue, 0.6, 0.8)
            Gizmos.draw_line((x, y), (next_x, next_y), color=color, thickness=2, duration=0.1)
        if hasattr(self, '_qf_attractor_pos'):
            x, y, z = self._qf_attractor_pos
            x, y, z = strange_attractor(x, y, z)
            self._qf_attractor_pos = (x, y, z)
            proj_x = cx + x * 3
            proj_y = cy + y * 3
            if hasattr(self, '_qf_attractor_trail'):
                self._qf_attractor_trail.append((proj_x, proj_y))
                if len(self._qf_attractor_trail) > 100:
                    self._qf_attractor_trail.pop(0)
            else:
                self._qf_attractor_trail = [(proj_x, proj_y)]

            for i in range(len(self._qf_attractor_trail) - 1):
                alpha = i / len(self._qf_attractor_trail)
                color = hsv_to_rgb((self._qf_time * 60 + i * 3) % 360, 0.8, alpha)
                Gizmos.draw_line(self._qf_attractor_trail[i], self._qf_attractor_trail[i + 1], color=color, thickness=3,
                                 duration=0.1)
        else:
            self._qf_attractor_pos = (1.0, 1.0, 1.0)
        center_energy = math.sin(self._qf_time * 4) * 0.3 + 0.7
        for layer in range(5):
            layer_radius = 30 + layer * 20
            layer_alpha = center_energy * (1 - layer * 0.15)
            color = hsv_to_rgb((self._qf_time * 80 + layer * 60) % 360, 0.9, layer_alpha)
            Gizmos.draw_circle((cx, cy), layer_radius, color=color, filled=False, thickness=4, duration=0.1)
        info_texts = [
            f"Quantum Time: {self._qf_time:.2f}",
            f"Nodes: {len(self._qf_nodes)}",
            f"Particles: {len(self._qf_particles)}",
            f"Energy: {center_energy:.2f}",
            f"Dimension: {self._qf_dimension}D"
        ]
        for i, text in enumerate(info_texts):
            color = hsv_to_rgb((i * 72 + self._qf_time * 20) % 360, 0.8, 0.9)
            Gizmos.draw_text((cx - 400, cy - 400 + i * 25), text, color=color, font_size=16, font_world_space=True,
                             world_space=True, duration=0.1)
        quantum_phase = self._qf_time * 3
        for i in range(8):
            angle = i * math.pi / 4 + quantum_phase
            inner_radius = 150
            outer_radius = 300
            inner_x = cx + inner_radius * math.cos(angle)
            inner_y = cy + inner_radius * math.sin(angle)
            outer_x = cx + outer_radius * math.cos(angle)
            outer_y = cy + outer_radius * math.sin(angle)
            energy_pulse = math.sin(quantum_phase * 2 + i * 0.8) * 0.5 + 0.5
            color = hsv_to_rgb((i * 45 + self._qf_time * 30) % 360, 0.9, energy_pulse)
            thickness = max(1, int(energy_pulse * 6))
            Gizmos.draw_arrow((inner_x, inner_y), (outer_x, outer_y), color=color, thickness=thickness, duration=0.1)
            cross_size = 10 + energy_pulse * 15
            Gizmos.draw_cross((outer_x, outer_y), cross_size, color=color, thickness=thickness, duration=0.1)

    @profile("demo_cellular_life_simulation", "demo")
    def demo_cellular_life_simulation(self, center=(0, 0)):
        if not hasattr(self, '_evo_cells'):
            self._evo_cells = []
            self._evo_tick = 0
            for _ in range(50):
                self._evo_cells.append({
                    'pos': [random.uniform(-300, 300), random.uniform(-300, 300)],
                    'vel': [random.uniform(-1, 1), random.uniform(-1, 1)],
                    'size': random.uniform(5, 12),
                    'color': [random.randint(50, 255) for _ in range(3)],
                    'energy': random.uniform(50, 100),
                    'id': random.randint(0, 100000)
                })
        self._evo_tick += 1
        next_gen = []
        for cell in self._evo_cells:
            cell['pos'][0] += cell['vel'][0]
            cell['pos'][1] += cell['vel'][1]
            cell['energy'] -= 0.2
            if random.random() < 0.01:
                cell['vel'][0] += random.uniform(-0.5, 0.5)
                cell['vel'][1] += random.uniform(-0.5, 0.5)
            Gizmos.draw_circle(cell['pos'], cell['size'], color=tuple(cell['color']), filled=True, duration=0.1)
            Gizmos.draw_arrow(cell['pos'], (cell['pos'][0] + cell['vel'][0] * 5, cell['pos'][1] + cell['vel'][1] * 5),
                              color=tuple(cell['color']), thickness=1, duration=0.1)
            Gizmos.draw_text((cell['pos'][0], cell['pos'][1] - 10), f"{int(cell['energy'])}", color='white',
                             font_size=8,
                             font_world_space=True, world_space=True, duration=0.1)
            for other in self._evo_cells:
                if cell['id'] == other['id']: continue
                dx = other['pos'][0] - cell['pos'][0]
                dy = other['pos'][1] - cell['pos'][1]
                dist_sq = dx * dx + dy * dy
                if dist_sq < (cell['size'] + other['size']) ** 2:
                    if cell['energy'] > other['energy']:
                        cell['energy'] += other['energy'] * 0.5
                        other['energy'] = 0
                        Gizmos.draw_line(cell['pos'], other['pos'], color='red', thickness=2, duration=0.1)
                    elif other['energy'] > cell['energy']:
                        other['energy'] += cell['energy'] * 0.5
                        cell['energy'] = 0
                        Gizmos.draw_line(cell['pos'], other['pos'], color='purple', thickness=2, duration=0.1)
                    else:
                        Gizmos.draw_line(cell['pos'], other['pos'], color='gray', thickness=1, duration=0.1)
            if cell['energy'] > 180 and len(next_gen) < 100:
                for _ in range(2):
                    child = {
                        'pos': [cell['pos'][0] + random.uniform(-10, 10), cell['pos'][1] + random.uniform(-10, 10)],
                        'vel': [random.uniform(-1, 1), random.uniform(-1, 1)],
                        'size': max(4, min(15, cell['size'] + random.uniform(-1, 1))),
                        'color': [min(255, max(0, c + random.randint(-10, 10))) for c in cell['color']],
                        'energy': cell['energy'] * 0.4,
                        'id': random.randint(0, 100000)
                    }
                    next_gen.append(child)
                cell['energy'] *= 0.3
            if 0 < cell['energy'] < 200:
                next_gen.append(cell)
            elif cell['energy'] <= 0:
                Gizmos.draw_cross(cell['pos'], cell['size'], color='black', thickness=2, duration=0.5)
        self._evo_cells = next_gen
    @profile("demo_gravity_galaxy", "demo")
    def demo_gravity_galaxy(self, center=(0, 0)):
        if not hasattr(self, '_galaxy_particles'):
            self._galaxy_particles = []
            self._galaxy_tick = 0
            center_mass = {
                'pos': [0, 0],
                'vel': [0, 0],
                'mass': 5000,
                'size': 20,
                'color': [255, 255, 100],
                'type': 'center'
            }
            self._galaxy_particles.append(center_mass)
            for i in range(200):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(50, 400)
                pos_x = radius * math.cos(angle)
                pos_y = radius * math.sin(angle)
                orbital_speed = math.sqrt(center_mass['mass'] / radius) * 0.8
                vel_x = -orbital_speed * math.sin(angle) + random.uniform(-0.3, 0.3)
                vel_y = orbital_speed * math.cos(angle) + random.uniform(-0.3, 0.3)
                particle = {
                    'pos': [pos_x, pos_y],
                    'vel': [vel_x, vel_y],
                    'mass': random.uniform(1, 10),
                    'size': random.uniform(2, 6),
                    'color': [random.randint(100, 255), random.randint(100, 255), random.randint(200, 255)],
                    'type': 'star',
                    'trail': []
                }
                self._galaxy_particles.append(particle)
        self._galaxy_tick += 1
        G = 0.1
        for i, particle in enumerate(self._galaxy_particles):
            if particle['type'] == 'center':
                continue
            force_x = 0
            force_y = 0
            for j, other in enumerate(self._galaxy_particles):
                if i == j:
                    continue
                dx = other['pos'][0] - particle['pos'][0]
                dy = other['pos'][1] - particle['pos'][1]
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1:
                    dist_sq = 1
                dist = math.sqrt(dist_sq)
                force_magnitude = G * particle['mass'] * other['mass'] / dist_sq
                force_x += force_magnitude * dx / dist
                force_y += force_magnitude * dy / dist
            acc_x = force_x / particle['mass']
            acc_y = force_y / particle['mass']
            particle['vel'][0] += acc_x * 0.01
            particle['vel'][1] += acc_y * 0.01
            particle['pos'][0] += particle['vel'][0]
            particle['pos'][1] += particle['vel'][1]
            particle['trail'].append([particle['pos'][0], particle['pos'][1]])
            if len(particle['trail']) > 30:
                particle['trail'].pop(0)
            for k in range(len(particle['trail']) - 1):
                alpha = k / len(particle['trail'])
                trail_color = [int(c * alpha) for c in particle['color']]
                if k < len(particle['trail']) - 1:
                    Gizmos.draw_line(particle['trail'][k], particle['trail'][k + 1],
                                     color=tuple(trail_color), thickness=1, duration=0.1)
            Gizmos.draw_circle(particle['pos'], particle['size'],
                               color=tuple(particle['color']), filled=True, duration=0.1)
            if particle['type'] == 'star':
                glow_size = particle['size'] * 1.5
                glow_color = [int(c * 0.3) for c in particle['color']]
                Gizmos.draw_circle(particle['pos'], glow_size,
                                   color=tuple(glow_color), filled=False, duration=0.1)
        center_particle = self._galaxy_particles[0]
        Gizmos.draw_circle(center_particle['pos'], center_particle['size'],
                           color=tuple(center_particle['color']), filled=True, duration=0.1)
        for radius in [100, 200, 300, 400]:
            circle_color = [50, 50, 50]
            Gizmos.draw_circle(center_particle['pos'], radius,
                               color=tuple(circle_color), filled=False, duration=0.1)
        info_text = f"Частиц: {len(self._galaxy_particles) - 1} | Время: {self._galaxy_tick}"
        Gizmos.draw_text((-400, 350), info_text, color='white', font_size=12,
                         font_world_space=True, world_space=True, duration=0.1)
    @profile("demo_galaxy_simulation", "demo")
    def demo_galaxy_simulation(self, center=(0, 0)):
        if not hasattr(self, '_galaxy_particles'):
            num_particles = 800
            self._galaxy_particles = np.zeros((num_particles, 2), dtype=np.float64)
            self._galaxy_velocities = np.zeros((num_particles, 2), dtype=np.float64)
            self._galaxy_masses = np.zeros(num_particles, dtype=np.float64)
            self._galaxy_forces = np.zeros((num_particles, 2), dtype=np.float64)
            self._galaxy_colors = []
            self._galaxy_sizes = []
            central_mass = 5000000.0
            self._galaxy_particles[0] = [center[0], center[1]]
            self._galaxy_velocities[0] = [0.0, 0.0]
            self._galaxy_masses[0] = central_mass
            self._galaxy_colors.append((255, 255, 100))
            self._galaxy_sizes.append(15.0)
            for i in range(1, num_particles):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(50, 400)
                spiral_factor = 2.0
                spiral_angle = angle + spiral_factor * radius / 100.0
                x = center[0] + radius * math.cos(spiral_angle)
                y = center[1] + radius * math.sin(spiral_angle)
                self._galaxy_particles[i] = [x, y]
                orbital_speed = math.sqrt(0.1 * central_mass / radius) * 0.8
                perp_angle = spiral_angle + math.pi / 2
                vx = orbital_speed * math.cos(perp_angle)
                vy = orbital_speed * math.sin(perp_angle)
                noise_factor = 0.3
                vx += random.uniform(-noise_factor, noise_factor)
                vy += random.uniform(-noise_factor, noise_factor)
                self._galaxy_velocities[i] = [vx, vy]
                mass = random.uniform(0.5, 3.0)
                self._galaxy_masses[i] = mass
                distance_from_center = math.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
                color_factor = min(1.0, distance_from_center / 300.0)
                if random.random() < 0.1:
                    self._galaxy_colors.append((255, 200, 200))
                elif random.random() < 0.3:
                    self._galaxy_colors.append((200, 200, 255))
                else:
                    r = int(255 * (1 - color_factor * 0.5))
                    g = int(255 * (1 - color_factor * 0.3))
                    b = int(255 * (1 - color_factor * 0.1))
                    self._galaxy_colors.append((r, g, b))
                size = 2.0 + mass * 1.5
                self._galaxy_sizes.append(size)
        calculate_forces(self._galaxy_particles, self._galaxy_masses, self._galaxy_forces)
        update_particles(self._galaxy_particles, self._galaxy_velocities, self._galaxy_masses, self._galaxy_forces)
        for i in range(len(self._galaxy_particles)):
            pos = self._galaxy_particles[i]
            color = self._galaxy_colors[i]
            size = self._galaxy_sizes[i]
            Gizmos.draw_circle(pos, size, color=color, filled=True, duration=0.1)
        arms = 4
        arm_length = 350.0
        for arm in range(arms):
            base_angle = (arm * 2 * math.pi / arms) + self.phase * 0.1
            for t in range(0, 100, 10):
                progress = t / 100.0
                angle = base_angle + progress * 2.0 * math.pi
                radius = progress * arm_length
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                alpha = int(100 * (1 - progress))
                spiral_color = (100, 100, 150, alpha)
                Gizmos.draw_circle([x, y], 3.0, color=spiral_color, filled=True, duration=0.1)

    @profile("demo_raycast_game", "demo")
    def demo_raycast_game(self, position=(0, 0)):
        import math, random
        CELL_SIZE = 40
        if not hasattr(self, '_pr_player_x'):
            self._pr_player_x = 100.0
            self._pr_player_y = 100.0
            self._pr_player_angle = 0.0
            self._pr_fov = math.pi / 2
            self._pr_num_rays = 120
            self._pr_max_depth = 1100
            self._pr_reflection_depth = 3
            self._pr_mirror_render_limit = 600  # ← NEW: max distance to render mirror reflections
            self._pr_fog_density = 0.01
            self._pr_fog_color = (30, 30, 30)
            self._pr_grid = [
                "###################",
                "#.........#......##",
                "#..##.............#",
                "#..##.....#......##",
                "#.........#.......#",
                "#######.#####..####",
                "##..........#.....#",
                "#...........#.....#",
                "#..#.#.#.#........#",
                "#..#.#.#.#.......##",
                "###################",
            ]
            self._pr_rows = len(self._pr_grid)
            self._pr_cols = len(self._pr_grid[0])
            self._pr_map = []
            for row in range(self._pr_rows):
                for col in range(self._pr_cols):
                    if self._pr_grid[row][col] == '#':
                        x0, y0 = col * CELL_SIZE, row * CELL_SIZE
                        x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
                        self._pr_map.extend(
                            [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))])
            self._pr_mirrors_rect = [((140, 190), (240, 200))]
            for (p1, p2) in self._pr_mirrors_rect:
                x0, y0 = min(p1[0], p2[0]), min(p1[1], p2[1])
                x1, y1 = max(p1[0], p2[0]), max(p1[1], p2[1])
                for wall in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
                    self._pr_map.append((wall, 'mirror'))
            self._pr_mirrors_circ = [((350, 150), 30)]
            self._pr_entity_x, self._pr_entity_y = 200.0, 300.0
            self._pr_entity_angle = 0.0
            self._pr_entity_speed = 5.0
            self._pr_entity_direction_timer = 0
            self._pr_entity_direction_duration = 60

        cx, cy = position

        def apply_fog(color, distance):
            fog_factor = max(0, min(1, math.exp(-self._pr_fog_density * distance)))
            return tuple(int(color[i] * fog_factor + self._pr_fog_color[i] * (1 - fog_factor)) for i in range(3))

        def can_move_to(nx, ny):
            col, row = int(nx // CELL_SIZE), int(ny // CELL_SIZE)
            return 0 <= row < self._pr_rows and 0 <= col < self._pr_cols and self._pr_grid[row][col] != '#'

        def update_entity():
            self._pr_entity_direction_timer += 2
            if self._pr_entity_direction_timer >= self._pr_entity_direction_duration:
                self._pr_entity_angle = random.uniform(0, 2 * math.pi)
                self._pr_entity_direction_timer = 0
            nx = self._pr_entity_x + math.cos(self._pr_entity_angle) * self._pr_entity_speed
            ny = self._pr_entity_y + math.sin(self._pr_entity_angle) * self._pr_entity_speed
            if can_move_to(nx, ny):
                self._pr_entity_x, self._pr_entity_y = nx, ny
            else:
                self._pr_entity_angle = random.uniform(0, 2 * math.pi)
                self._pr_entity_direction_timer = 0

        update_entity()

        for row in range(self._pr_rows):
            for col in range(self._pr_cols):
                color = (200, 200, 200) if self._pr_grid[row][col] == '#' else (50, 50, 50)
                Gizmos.draw_rect(
                    (cx + col * CELL_SIZE * 0.5 + CELL_SIZE * 0.25, cy + row * CELL_SIZE * 0.5 + CELL_SIZE * 0.25),
                    CELL_SIZE * 0.5, CELL_SIZE * 0.5, color=color, filled=True, world_space=True)

        for (x0, y0), (x1, y1) in self._pr_mirrors_rect:
            Gizmos.draw_rect((cx + (x0 + x1) / 4, cy + (y0 + y1) / 4), abs(x1 - x0) / 2, abs(y1 - y0) / 2,
                             color=(180, 180, 220), filled=True, world_space=True)

        for (mx, my), mr in self._pr_mirrors_circ:
            Gizmos.draw_circle((cx + mx * 0.5, cy + my * 0.5), mr * 0.5, color=(180, 180, 220), filled=True,
                               world_space=True)

        Gizmos.draw_circle((cx + self._pr_player_x * 0.5, cy + self._pr_player_y * 0.5), 5, color=(255, 255, 0),
                           filled=True, world_space=True)
        Gizmos.draw_circle((cx + self._pr_entity_x * 0.5, cy + self._pr_entity_y * 0.5), 8, color=(255, 0, 0),
                           filled=True, world_space=True)

        screen_x_offset = cx - 1000
        grad_steps, top_color, mid_color = 50, (30, 30, 100), (60, 60, 140)
        floor_top, floor_bot = (60, 40, 30), (120, 80, 60)

        for i in range(grad_steps):
            t = i / grad_steps
            base_color = tuple(int(top_color[j] * (1 - t) + mid_color[j] * t) for j in range(3))
            fogged_color = apply_fog(base_color, 200 + i * 300 / grad_steps)
            y = cy - 200 + i * 200 / grad_steps
            Gizmos.draw_rect((screen_x_offset + 400, y), 800, 200 / grad_steps, color=fogged_color, filled=True,
                             world_space=True)

        for i in range(grad_steps):
            t = i / grad_steps
            base_color = tuple(int(floor_top[j] * (1 - t) + floor_bot[j] * t) for j in range(3))
            fogged_color = apply_fog(base_color, 200 + i * 300 / grad_steps)
            y = cy + i * 200 / grad_steps
            Gizmos.draw_rect((screen_x_offset + 400, y), 800, 200 / grad_steps, color=fogged_color, filled=True,
                             world_space=True)

        start_angle = self._pr_player_angle - self._pr_fov / 2

        def cast_ray(x0, y0, angle, depth_left, distance_accumulated=0):
            sin_a, cos_a = math.sin(angle), math.cos(angle)
            nearest_depth, nearest_hit, nearest_type, nearest_normal = self._pr_max_depth, None, None, None

            for obj in self._pr_map:
                obj_type = 'wall'
                if isinstance(obj, tuple) and len(obj) == 2 and isinstance(obj[1], str):
                    (p1, p2), obj_type = obj
                else:
                    p1, p2 = obj
                x1, y1 = p1;
                x2, y2 = p2
                denom = cos_a * (y1 - y2) - sin_a * (x1 - x2)
                if abs(denom) < 1e-10: continue
                t = (cos_a * (y1 - y0) - sin_a * (x1 - x0)) / denom
                u = -((x1 - x2) * (y1 - y0) - (y1 - y2) * (x1 - x0)) / denom
                if 0 <= t <= 1 and 0.01 < u < nearest_depth:
                    nearest_depth, nearest_hit, nearest_type = u, (x0 + cos_a * u, y0 + sin_a * u), obj_type
                    dx, dy = x2 - x1, y2 - y1
                    length = math.hypot(dx, dy)
                    if length != 0:
                        normal = (-dy / length, dx / length)
                        if normal[0] * cos_a + normal[1] * sin_a > 0:
                            normal = (-normal[0], -normal[1])
                        nearest_normal = normal

            for (mx, my), mr in self._pr_mirrors_circ:
                dx, dy = x0 - mx, y0 - my
                b, c = 2 * (cos_a * dx + sin_a * dy), dx * dx + dy * dy - mr * mr
                delta = b * b - 4 * c
                if delta >= 0:
                    u1 = (-b - math.sqrt(delta)) / 2
                    if 0.01 < u1 < nearest_depth:
                        nearest_depth, nearest_hit, nearest_type = u1, (x0 + cos_a * u1, y0 + sin_a * u1), 'mirror'
                        nx, ny = (nearest_hit[0] - mx) / mr, (nearest_hit[1] - my) / mr
                        l = math.hypot(nx, ny)
                        if l != 0: nearest_normal = (nx / l, ny / l)

            entity_dx, entity_dy = self._pr_entity_x - x0, self._pr_entity_y - y0
            entity_dot = entity_dx * cos_a + entity_dy * sin_a
            if entity_dot > 0:
                entity_perp_dist = abs(entity_dx * (-sin_a) + entity_dy * cos_a)
                if entity_perp_dist < 8:
                    entity_distance = entity_dot
                    if 0.01 < entity_distance < nearest_depth:
                        nearest_depth, nearest_hit, nearest_type = entity_distance, (x0 + cos_a * entity_distance,
                                                                                     y0 + sin_a * entity_distance), 'entity'

            if nearest_hit:
                hit_x, hit_y = nearest_hit
                total_depth = distance_accumulated + nearest_depth
                if total_depth > self._pr_mirror_render_limit and depth_left < self._pr_reflection_depth:
                    return  # ← EARLY EXIT: don't render distant reflections
                Gizmos.draw_line((cx + x0 * 0.5, cy + y0 * 0.5), (cx + hit_x * 0.5, cy + hit_y * 0.5),
                                 color=(255, 0, 0), thickness=1, world_space=True)
                corrected_depth = total_depth * math.cos(angle - self._pr_player_angle)
                proj_height = min(400, 20000 / (corrected_depth + 1e-4))
                base_brightness = max(50, 255 - int(total_depth * 0.2))
                col_w = 800 / self._pr_num_rays + 1
                col_x = screen_x_offset + i * col_w
                if nearest_type == 'entity':
                    final_color = apply_fog((255, 0, 0), total_depth)
                    Gizmos.draw_rect((col_x + col_w / 2, cy), col_w, proj_height, color=final_color, filled=True,
                                     world_space=True)
                elif nearest_type != 'mirror':
                    final_color = apply_fog((base_brightness,) * 3, total_depth)
                    Gizmos.draw_rect((col_x + col_w / 2, cy), col_w, proj_height, color=final_color, filled=True,
                                     world_space=True)
                if nearest_type == 'mirror' and nearest_normal and depth_left > 0:
                    dot = cos_a * nearest_normal[0] + sin_a * nearest_normal[1]
                    reflect_x = cos_a - 2 * dot * nearest_normal[0]
                    reflect_y = sin_a - 2 * dot * nearest_normal[1]
                    new_angle = math.atan2(reflect_y, reflect_x)
                    EPSILON = 20.0
                    new_x = hit_x + nearest_normal[0] * EPSILON
                    new_y = hit_y + nearest_normal[1] * EPSILON
                    cast_ray(new_x, new_y, new_angle, depth_left - 1, total_depth)
            else:
                total_depth = distance_accumulated + self._pr_max_depth
                corrected_depth = total_depth * math.cos(angle - self._pr_player_angle)
                proj_height = min(400, 20000 / (corrected_depth + 1e-4))
                base_brightness = max(30, 255 - int(total_depth * 0.2))
                col_w = 400 / self._pr_num_rays + 2
                col_x = screen_x_offset + i * col_w
                if depth_left == self._pr_reflection_depth:
                    final_color = apply_fog((base_brightness // 3,) * 3, total_depth)
                    Gizmos.draw_rect((col_x + col_w / 2, cy), col_w, proj_height, color=final_color, filled=True,
                                     world_space=True)

        for i in range(self._pr_num_rays):
            ray_angle = start_angle + i * self._pr_fov / self._pr_num_rays
            cast_ray(self._pr_player_x, self._pr_player_y, ray_angle, self._pr_reflection_depth)

        def move_forward():
            nx, ny = self._pr_player_x + math.cos(self._pr_player_angle) * 5, self._pr_player_y + math.sin(
                self._pr_player_angle) * 5
            if can_move_to(nx, ny):
                synthesizer.play_frequency(200, duration=0.04, waveform='sine', volume=0.2)
                self._pr_player_x, self._pr_player_y = nx, ny
            else:
                synthesizer.play_frequency(330, duration=0.04, waveform='sine', volume=0.1)

        def move_back():
            nx, ny = self._pr_player_x - math.cos(self._pr_player_angle) * 5, self._pr_player_y - math.sin(
                self._pr_player_angle) * 5
            if can_move_to(nx, ny):
                synthesizer.play_frequency(200, duration=0.04, waveform='sine', volume=0.2)
                self._pr_player_x, self._pr_player_y = nx, ny
            else:
                synthesizer.play_frequency(330, duration=0.04, waveform='sine', volume=0.1)

        def turn_left():
            self._pr_player_angle -= 0.11
            synthesizer.play_frequency(230, duration=0.015, waveform='sine', volume=0.1)

        def turn_right():
            self._pr_player_angle += 0.11
            synthesizer.play_frequency(230, duration=0.015, waveform='sine', volume=0.1)

        def increase_fog():
            self._pr_fog_density = min(0.01, self._pr_fog_density + 0.0005)

        def decrease_fog():
            self._pr_fog_density = max(0.0005, self._pr_fog_density - 0.0005)

        btns = [("W", move_forward, (350, -300)), ("S", move_back, (350, -250)),
                ("A", turn_left, (300, -275)), ("D", turn_right, (400, -275)),
                ("F+", increase_fog, (450, -250)), ("F-", decrease_fog, (450, -300))]
        for label, cb, (dx, dy) in btns:
            Gizmos.draw_button((cx + dx, cy + dy), label, on_click=cb, width=40, height=40,
                               font_size=20 if label in "WASD" else 16, world_space=True)

        texts = [
            f"Pos: ({int(self._pr_player_x)}, {int(self._pr_player_y)})",
            f"Angle: {self._pr_player_angle:.2f}",
            f"Rays: {self._pr_num_rays}",
            f"Fog: {self._pr_fog_density:.4f}",
            f"Entity: ({int(self._pr_entity_x)}, {int(self._pr_entity_y)})"
        ]
        for i, txt in enumerate(texts):
            Gizmos.draw_text((cx - 400, cy - 400 + i * 30), txt, font_size=16, world_space=True)

        Gizmos.draw_rect((screen_x_offset + 400, cy), 800, 400, color=(50, 50, 50), filled=False, thickness=2,
                         world_space=True)
    @profile("demo_quantum_field", "demo")
    def step_scalar_phi4(self, position=(0, 0)):
        """
        Реалистичная 2D-сцена: скалярное поле φ с φ^4-взаимодействием на решётке.
        Уравнение движения (в безразмерных единицах, a=1):
            ∂_t^2 φ = Δφ - m^2 φ - λ φ^3
        Интегратор: leapfrog (симплектический), периодические ГУ.
        Визуализация: тепловая карта φ(x,y), стрелки для ∇φ, скаляр энергии.
        """
        import math
        import random

        cx, cy = position

        # --- Инициализация один раз ---
        if not hasattr(self, "_lqf_init"):
            self._lqf_init = True

            # Параметры решётки и модели
            self._Nx = 30  # число узлов по X
            self._Ny = 30  # число узлов по Y
            self._a = 1.0  # шаг решётки (единица длины)
            self._m2 = 10.5  # m^2 (массовый параметр)
            self._lam = 10.1  # λ (сила φ^4)
            self._dt = 0.1  # шаг по времени (должен удовлетворять условию Куранта)

            # Состояние поля: φ и его канонический импульс π = ∂_t φ на полушаге
            self._phi = [[0.0 for _ in range(self._Ny)] for _ in range(self._Nx)]
            self._pi = [[0.0 for _ in range(self._Ny)] for _ in range(self._Nx)]

            # Малое случайное возмущение для старта (эллиптическая «горбинка»)
            for i in range(self._Nx):
                for j in range(self._Ny):
                    x = (i - self._Nx / 2) / self._Nx
                    y = (j - self._Ny / 2) / self._Ny
                    bump = math.exp(-80 * (x * x + (1.4 * y) * (1.4 * y)))
                    self._phi[i][j] = 0.3 * bump + (random.random() - 0.5) * 0.01
                    self._pi[i][j] = 0.0

            # Служебное «время» и шаг визуализации
            self._t = 0.0
            self._viz_skip = 1  # рисуем каждый кадр; можно увеличить для ускорения

            # Проверка устойчивости для волнового уравнения (в 2D ≈ dt <= a/√d)
            if self._dt > self._a / math.sqrt(2):
                raise ValueError("Нарушено условие устойчивости: уменьшите dt или увеличьте a.")

        # --- Вспом. функции с PBC ---
        Nx, Ny = self._Nx, self._Ny
        a, dt = self._a, self._dt
        m2, lam = self._m2, self._lam

        def idx(i, n):  # периодические границы
            return (i + n) % n

        def laplacian(i, j):
            # Δφ ≈ (φ_{i+1,j}+φ_{i-1,j}+φ_{i,j+1}+φ_{i,j-1}-4φ_{i,j})/a^2
            ph = self._phi
            return (ph[idx(i + 1, Nx)][j] + ph[idx(i - 1, Nx)][j] +
                    ph[i][idx(j + 1, Ny)] + ph[i][idx(j - 1, Ny)] -
                    4.0 * ph[i][j]) / (a * a)

        # --- Один шаг leapfrog ---
        # π(t+dt/2) = π(t-dt/2) + dt * (Δφ - m^2 φ - λ φ^3)
        # φ(t+dt)   = φ(t) + dt * π(t+dt/2)
        new_pi = [[0.0 for _ in range(Ny)] for _ in range(Nx)]
        for i in range(Nx):
            for j in range(Ny):
                force = laplacian(i, j) - m2 * self._phi[i][j] - lam * (self._phi[i][j] ** 3)
                new_pi[i][j] = self._pi[i][j] + dt * force

        new_phi = [[0.0 for _ in range(Ny)] for _ in range(Nx)]
        for i in range(Nx):
            for j in range(Ny):
                new_phi[i][j] = self._phi[i][j] + dt * new_pi[i][j]

        self._phi = new_phi
        self._pi = new_pi
        self._t += dt

        # --- Энергия (для контроля корректности интегрирования) ---
        # H = Σ a^2 [ 1/2 π^2 + 1/2 (∇φ)^2 + 1/2 m^2 φ^2 + λ/4 φ^4 ]
        total_E = 0.0
        for i in range(Nx):
            for j in range(Ny):
                # градиент по конечным разностям
                dphix = (self._phi[idx(i + 1, Nx)][j] - self._phi[i][j]) / a
                dphiy = (self._phi[i][idx(j + 1, Ny)] - self._phi[i][j]) / a
                density = 0.5 * (self._pi[i][j] ** 2) + 0.5 * (dphix * dphix + dphiy * dphiy) \
                          + 0.5 * m2 * (self._phi[i][j] ** 2) + 0.25 * lam * (self._phi[i][j] ** 4)
                total_E += density
        # (абсолютная величина не важна, важно, что она почти сохраняется во времени)

        # --- Визуализация (заменяет прежние Gizmos-эффекты) ---
        # 1) Тепловая карта φ: цвет по значению φ (с обрезкой)
        # 2) Редкие стрелки градиента ∇φ (направление потока)
        # 3) Текстовые метрики: t, Energy, dt, Nx×Ny, m^2, λ
        grid_px = 19.0  # размер клетки в пикселях для рендера
        halfx = (Nx * grid_px) / 2
        halfy = (Ny * grid_px) / 2

        # Подложка/рамка
        Gizmos.draw_rect((cx, cy), Nx * grid_px, Ny * grid_px,
                         color=(40, 40, 40), filled=False, thickness=2, world_space=True)

        # Цветовая шкала
        # Нормируем φ по перцентилю (простая статическая шапка ±φ_clip)
        phi_clip = 1.0
        for i in range(Nx):
            for j in range(Ny):
                val = max(-phi_clip, min(phi_clip, self._phi[i][j]))
                # плавный мэппинг: отрицательные -> синие, положительные -> красные
                # intensity в [0,255]
                tcol = 0.5 * (val / phi_clip + 1.0)  # 0..1
                r = int(255 * tcol)
                b = int(255 * (1.0 - tcol))
                g = int(70 + 60 * abs(0.5 - tcol))  # немного «зелени» в середине
                # координаты клетки
                px = cx - halfx + (i + 0.5) * grid_px
                py = cy - halfy + (j + 0.5) * grid_px
                Gizmos.draw_rect((px, py), grid_px * 0.95, grid_px * 0.95,
                                 color=(r, g, b), filled=True, world_space=True)

        # Векторы ∇φ через одну клетку, чтобы не засорять
        step = 6
        for i in range(0, Nx, step):
            for j in range(0, Ny, step):
                dphix = (self._phi[idx(i + 1, Nx)][j] - self._phi[idx(i - 1, Nx)][j]) / (2 * a)
                dphiy = (self._phi[i][idx(j + 1, Ny)] - self._phi[i][idx(j - 1, Ny)]) / (2 * a)
                px = cx - halfx + (i + 0.5) * grid_px
                py = cy - halfy + (j + 0.5) * grid_px
                scale = 2.0
                Gizmos.draw_line((px, py), (px + scale * dphix, py + scale * dphiy),
                                 color=(255, 255, 0), thickness=1, world_space=True)

        # HUD
        Gizmos.draw_text((cx - halfx + 8, cy - halfy - 20),
                         f"t = {self._t:.2f}, E ≈ {total_E:.3f}", font_size=16,
                         color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((cx - halfx + 8, cy - halfy - 4),
                         f"Nx×Ny={Nx}×{Ny}, dt={dt:.3f}, m^2={m2}, λ={lam}",
                         font_size=16, color=(200, 200, 200), world_space=True)

    @profile("demo_fluid_dynamics", "demo")
    def demo_fluid_dynamics(self, position=(0, 0)):
        cx, cy = position
        N = 64
        dt = 0.01
        diff = 0.0
        visc = 0.0001
        if not hasattr(self, "_fd_init"):
            self._fd_init = True
            self._fd_u = np.zeros((N, N), dtype=np.float32)
            self._fd_v = np.zeros((N, N), dtype=np.float32)
            self._fd_u_prev = np.zeros((N, N), dtype=np.float32)
            self._fd_v_prev = np.zeros((N, N), dtype=np.float32)
            self._fd_p = np.zeros((N, N), dtype=np.float32)
            self._fd_div = np.zeros((N, N), dtype=np.float32)
        u, v = self._fd_u, self._fd_v
        u_prev, v_prev = self._fd_u_prev, self._fd_v_prev
        p, div = self._fd_p, self._fd_div
        @njit(cache=True)
        def add_source(x, s, dt):
            x += dt * s
        @njit(cache=True)
        def diffuse(b, x, x0, diff, dt):
            a = dt * diff * N * N
            for _ in range(4):
                for i in range(1, N - 1):
                    for j in range(1, N - 1):
                        x[i, j] = (x0[i, j] + a * (x[i + 1, j] + x[i - 1, j] + x[i, j + 1] + x[i, j - 1])) / (1 + 4 * a)
        @njit(cache=True)
        def advect(b, d, d0, u, v, dt):
            for i in range(1, N - 1):
                for j in range(1, N - 1):
                    x = i - dt * u[i, j] * N
                    y = j - dt * v[i, j] * N
                    if x < 0.5: x = 0.5
                    if x > N - 1.5: x = N - 1.5
                    if y < 0.5: y = 0.5
                    if y > N - 1.5: y = N - 1.5
                    i0 = int(x)
                    i1 = i0 + 1
                    j0 = int(y)
                    j1 = j0 + 1
                    s1 = x - i0
                    s0 = 1 - s1
                    t1 = y - j0
                    t0 = 1 - t1
                    d[i, j] = s0 * (t0 * d0[i0, j0] + t1 * d0[i0, j1]) + s1 * (t0 * d0[i1, j0] + t1 * d0[i1, j1])
        @njit(cache=True)
        def project(u, v, p, div):
            for i in range(1, N - 1):
                for j in range(1, N - 1):
                    div[i, j] = -0.5 * (u[i + 1, j] - u[i - 1, j] + v[i, j + 1] - v[i, j - 1]) / N
                    p[i, j] = 0
            for _ in range(4):
                for i in range(1, N - 1):
                    for j in range(1, N - 1):
                        p[i, j] = (div[i, j] + p[i + 1, j] + p[i - 1, j] + p[i, j + 1] + p[i, j - 1]) / 4
            for i in range(1, N - 1):
                for j in range(1, N - 1):
                    u[i, j] -= 0.5 * (p[i + 1, j] - p[i - 1, j]) * N
                    v[i, j] -= 0.5 * (p[i, j + 1] - p[i, j - 1]) * N
        u_prev.fill(0)
        v_prev.fill(0)
        src_x, src_y = N // 4, N // 2
        force = 2000.0
        size = 5
        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                i = src_x + dx
                j = src_y + dy
                if 1 <= i < N - 1 and 1 <= j < N - 1:
                    u_prev[i, j] = force
                    v_prev[i, j] = 0
        add_source(u, u_prev, dt)
        add_source(v, v_prev, dt)
        u0, v0 = u.copy(), v.copy()
        diffuse(1, u, u0, visc, dt)
        diffuse(2, v, v0, visc, dt)
        project(u, v, p, div)
        u0, v0 = u.copy(), v.copy()
        advect(1, u, u0, u0, v0, dt)
        advect(2, v, v0, u0, v0, dt)
        project(u, v, p, div)
        scale = 20
        half = N // 2
        for i in range(N):
            for j in range(N):
                x = cx + (i - half) * scale
                y = cy + (j - half) * scale
                vel = math.sqrt(u[i, j] ** 2 + v[i, j] ** 2)
                col = min(255, int(vel * 8))
                Gizmos.draw_rect((x, y), scale - 1, scale - 1, color=(col, col, 255), filled=True, world_space=True)

        Gizmos.draw_rect((cx + (src_x - half) * scale, cy + (src_y - half) * scale), scale, scale, color=(255, 0, 0),
                         filled=True, world_space=True)

    @profile("demo_supermodel", "demo")
    def demo_supermodel(self, pos=(0, 0)):
        if not hasattr(self, '_s'): self._s, self._r, self._b, self._pts, self._st = 10., 28., 2.667, [
            (0., 1., 1.05)], 1000
        cx, cy = pos
        for _ in range(3):
            x, y, z = self._pts[-1]
            dx = self._s * (y - x);
            dy = x * (self._r - z) - y;
            dz = x * y - self._b * z
            self._pts.append((x + dx * 0.01, y + dy * 0.01, z + dz * 0.01))
        self._pts = self._pts[-self._st:]
        for (x1, y1, z1), (x2, y2, z2) in zip(self._pts, self._pts[1:]):
            c = int(255 * (z1 / max(30, z1))), int(255 * (1 - z1 / max(30, z1))), 150
            Gizmos.draw_line((cx + x1 * 10, cy + y1 * 10), (cx + x2 * 10, cy + y2 * 10), color=c, thickness=2)
        px, py, pz = self._pts[-1]
        Gizmos.draw_point((cx + px * 10, cy + py * 10), color=(255, 255, 255), size=5)
        Gizmos.draw_arrow((cx, cy), (cx + px * 10, cy + py * 10), thickness=2)
        Gizmos.draw_cross((cx, cy), 50)
        for i, (n, v) in enumerate([("σ", self._s), ("ρ", self._r), ("β", self._b)]):
            Gizmos.draw_text((cx - 200, cy + 200 - 20 * i), f"{n}={v:.3f}", font_size=14)
            Gizmos.draw_button((cx - 100, cy + 195 - 20 * i), "+",
                               on_click=lambda n=n: setattr(self, '_' + {'σ': 's', 'ρ': 'r', 'β': 'b'}[n], getattr(self,
                                                                                                                   '_' +
                                                                                                                   {
                                                                                                                       'σ': 's',
                                                                                                                       'ρ': 'r',
                                                                                                                       'β': 'b'}[
                                                                                                                       n]) * 1.1),
                               width=20, height=20)
            Gizmos.draw_button((cx - 70, cy + 195 - 20 * i), "-",
                               on_click=lambda n=n: setattr(self, '_' + {'σ': 's', 'ρ': 'r', 'β': 'b'}[n], getattr(self,
                                                                                                                   '_' +
                                                                                                                   {
                                                                                                                       'σ': 's',
                                                                                                                       'ρ': 'r',
                                                                                                                       'β': 'b'}[
                                                                                                                       n]) * 0.9),
                               width=20, height=20)
        Gizmos.draw_rect((cx, cy + 250), 400, 60, filled=True, color=(0, 0, 0, 100))
        Gizmos.draw_text((cx, cy + 250), "Lorenz Attractor Demo", font_size=18)

    @profile("demo_stirling_engine", "demo")
    def demo_stirling_engine(self, position=(0, 0)):
        """
        Улучшенная численная модель двигателя Стирлинга (вся логика в одной функции).

        Модель учитывает:
        - два объёма (горячая и холодная полости) с общим давлением;
        - нестационарный обмен теплом с горячим/холодным источниками по закону Ньютона;
        - регенератор с собственной тепловой ёмкостью, который обменивает тепло с протекающим через него газом;
        - расчёт давления по уравнению состояния идеального газа для двух объёмов: P = m*R / (Vh/Th + Vc/Tc);
        - работа рассчитывается через P * dV (разность объёмов за шаг) и аккумулируется;
        - вычисление мощности, крутящего момента, КПД на основе суммарного входящего тепла.

        Визуализация через Gizmos (цилиндры, поршни, маховик, графики, управляющие кнопки).

        Примечание: функция рассчитана на вызов в игровом цикле с dt ~ 0.016 с.
        """

        cx, cy = position

        # --- Параметры модели (инициализируются один раз) ---
        if not hasattr(self, '_stirling_init'):
            # state flags
            self._stirling_init = True
            # kinematic
            self._stirling_angle = 0.0  # crank angle (rad)
            self._stirling_displacer_angle = 0.0  # displacer crank angle (rad)
            self._stirling_phase_shift = np.pi / 2  # фазовый сдвиг между кривошипами

            # geometry (мм -> m where appropriate)
            self._stirling_base_volume = 50e-6  # базовый объём в каждом цилиндре, m^3 (50 cm^3 -> 50e-6 m^3)
            self._stirling_dead_volume = 20e-6  # мертвый объём, m^3
            self._stirling_stroke = 40e-3  # ход поршня, m (40 мм)
            self._stirling_area = 0.008  # эффективная площадь поршня, m^2 (пример)

            # gas properties
            self._stirling_working_gas = 'air'
            self._stirling_gas_constant = 287.0  # R (J/(kg·K)) для воздуха
            self._stirling_cp = 1005.0  # J/(kg·K)
            self._stirling_cv = self._stirling_cp - self._stirling_gas_constant
            self._stirling_gamma = self._stirling_cp / self._stirling_cv

            # masses / initial temperatures
            self._stirling_gas_mass = 0.001  # kg (1 g)
            self._stirling_temp_hot = 600.0  # K (source temperature)
            self._stirling_temp_cold = 300.0  # K (sink temperature)
            self._stirling_regenerator_temp = 450.0  # K (regenerator mean temperature)

            # heat transfer coefficients & surfaces (very approximate)
            self._stirling_h_hot = 50.0  # W/(m^2 K)
            self._stirling_h_cold = 30.0  # W/(m^2 K)
            self._stirling_area_hot = 0.01  # m^2
            self._stirling_area_cold = 0.01  # m^2
            self._stirling_regen_capacity = 5.0  # J/K (effective thermal capacity of regenerator)
            self._stirling_regen_efficiency = 0.85  # fraction of enthalpy exchange recovered

            # dynamic / control
            self._stirling_frequency = 2.0  # Hz
            self._stirling_load_torque = 0.0  # external load torque (N·m)
            self._stirling_mechanical_loss = 0.05  # fraction of power lost to friction etc.

            # diagnostics
            self._stirling_pressure = 1.0  # initial guess (Pa)
            self._stirling_power = 0.0
            self._stirling_efficiency = 0.0
            self._stirling_work_done = 0.0
            self._stirling_heat_in = 0.0
            self._stirling_heat_out = 0.0
            self._stirling_pressure_history = []
            self._stirling_volume_history = []
            self._stirling_work_history = []
            self._stirling_temp_gas_hot = 500.0  # gas temperatures in compartments
            self._stirling_temp_gas_cold = 400.0
            self._stirling_prev_total_volume = None

        # --- time step (fixed) ---
        dt = 0.016  # seconds; вызывается из игрового цикла

        # --- kinematics: обновляем углы и положения поршней ---
        omega = self._stirling_frequency * 2 * np.pi  # angular velocity (rad/s)
        self._stirling_angle += omega * dt
        self._stirling_displacer_angle = self._stirling_angle + self._stirling_phase_shift

        # нормируем углы
        if self._stirling_angle > 2 * np.pi:
            self._stirling_angle -= 2 * np.pi
        if self._stirling_displacer_angle > 2 * np.pi:
            self._stirling_displacer_angle -= 2 * np.pi

        # поршни (линейная зависимость от cos)
        piston_hot_pos = 0.5 * (1 + np.cos(self._stirling_angle))  # от 0..1
        piston_cold_pos = 0.5 * (1 + np.cos(self._stirling_displacer_angle))

        # объёмы (m^3)
        Vh = self._stirling_base_volume + self._stirling_dead_volume + self._stirling_area * (
                    piston_hot_pos * self._stirling_stroke)
        Vc = self._stirling_base_volume + self._stirling_dead_volume + self._stirling_area * (
                    piston_cold_pos * self._stirling_stroke)
        V_total = Vh + Vc

        # --- теплопередача с горячим и холодным источником ---
        # считаем мгновенные мощности тепла (вход в газ) по закону Ньютона: Qdot = h*A*(T_source - T_gas)
        Qdot_hot = self._stirling_h_hot * self._stirling_area_hot * (
                    self._stirling_temp_hot - self._stirling_temp_gas_hot)
        Qdot_cold = self._stirling_h_cold * self._stirling_area_cold * (
                    self._stirling_temp_cold - self._stirling_temp_gas_cold)

        # интеграция тепла в газ в каждой камере
        dQ_hot = Qdot_hot * dt
        dQ_cold = Qdot_cold * dt

        # --- регенератор: перенос тепла между потоками газа при перемещении объёма ---
        # вычислим мгновенный массовый поток через регенератор из-за изменения объёмов
        # предположение: при изменении объёма часть газа переливается из одной камеры в другую
        # масса распределяется пропорционально объёмам; скорость переноса массы ~ rho * dV/dt

        # плотность газа в каждой камере (из уравнения состояния: rho = P/(R*T) * (m распределение) )
        # Но сначала нужно найти давление P, используя уравнение P = m*R / (Vh/Th + Vc/Tc)
        Th = max(1.0, self._stirling_temp_gas_hot)
        Tc = max(1.0, self._stirling_temp_gas_cold)
        m = self._stirling_gas_mass
        R = self._stirling_gas_constant

        denom = Vh / Th + Vc / Tc
        # защита от нуля
        if denom <= 0:
            P = 101325.0
        else:
            P = m * R / denom

        # плотности (локальные масс-части) - число молей распределено по V/T
        # m_h = P*Vh/(R*Th) ; m_c = P*Vc/(R*Tc)  (это будет суммироваться в m)
        m_h = P * Vh / (R * Th)
        m_c = P * Vc / (R * Tc)

        # массовые потоки из-за изменения объёмов
        # dV/dt для каждой камеры
        # сохраняем предыдущий общий объём для расчёта dV
        if self._stirling_prev_total_volume is None:
            self._stirling_prev_total_volume = V_total
        dV_total = V_total - self._stirling_prev_total_volume
        self._stirling_prev_total_volume = V_total

        # приближённый массопоток через регенератор (kg/s) — когда один объем уменьшается, другой увеличивается
        # mass flow ~ (dV_hot/dt) * P/(R*T_mean)
        dVh = Vh - (self._stirling_volume_history[-1] / 2 if len(self._stirling_volume_history) else Vh)
        # guard
        dVh_dt = dVh / dt
        T_mean_flow = 0.5 * (Th + Tc)
        rho_mean = P / (R * T_mean_flow)
        m_flow = abs(rho_mean * dVh_dt)

        # тепло, отданное/полученное регенератором при проходе массы m_flow за dt
        # Q_reg = m_flow * cp * (T_sender - T_reg) * eff
        # определим направление: если газ переходит из горячей в холодную, регенератор нагревается и отдает тепло обратно
        Q_reg = 0.0
        if m_flow > 0:
            # доля газа, проходящая через регенератор за шаг
            frac = min(1.0, m_flow * dt / (m + 1e-12))
            # если dVh_dt < 0 — горячая камера сжимается -> газ идёт в холодную
            if dVh_dt < 0:
                # горячий газ проходит через регенератор к холодной
                Q_reg = m_flow * self._stirling_cp * (
                            Th - self._stirling_regenerator_temp) * self._stirling_regen_efficiency * dt
                # регенератор меняет температуру
                dT_reg = -Q_reg / (self._stirling_regen_capacity + 1e-12)
                self._stirling_regenerator_temp += dT_reg
                # газ в холодной получает часть тепла (символически)
                dQ_cold += Q_reg
            else:
                # холодный газ проходит к горячей (при расширении горячей камеры)
                Q_reg = m_flow * self._stirling_cp * (
                            Tc - self._stirling_regenerator_temp) * self._stirling_regen_efficiency * dt
                dT_reg = -Q_reg / (self._stirling_regen_capacity + 1e-12)
                self._stirling_regenerator_temp += dT_reg
                dQ_hot += Q_reg

        # --- обновляем температуры газа в камерах (приближённо, раздельно) ---
        # dT = Q/(m_segment * cp)
        # используем m_h и m_c как локальные массы
        if m_h > 0:
            dT_h = dQ_hot / (m_h * self._stirling_cp + 1e-12)
        else:
            dT_h = 0.0
        if m_c > 0:
            dT_c = dQ_cold / (m_c * self._stirling_cp + 1e-12)
        else:
            dT_c = 0.0

        self._stirling_temp_gas_hot = max(1.0, Th + dT_h)
        self._stirling_temp_gas_cold = max(1.0, Tc + dT_c)

        # --- работа: dW = P * dV_total (положительная при расширении) ---
        # используем dV_total, рассчитанный выше
        work_out = P * dV_total  # J (может быть отрицательным)

        # сила и момент на маховике: мощность = работа/dt
        power_raw = work_out / (dt + 1e-12)

        # на мощность влияют механические потери и нагрузка
        mechanical_losses = abs(power_raw) * self._stirling_mechanical_loss
        power_net = power_raw - mechanical_losses - (self._stirling_load_torque * omega)

        torque = power_net / (omega + 1e-12)

        # аккумулируем тепловые величины и работу
        self._stirling_work_done = work_out
        self._stirling_power = power_net
        self._stirling_torque = torque

        # входящее тепло — положительное, когда газ получает тепло от горячего источника
        Q_in = max(0.0, dQ_hot)
        Q_out = max(0.0, -dQ_cold) if dQ_cold < 0 else 0.0

        self._stirling_heat_in = Q_in
        self._stirling_heat_out = Q_out

        # КПД (просчитываем как полезная механическая энергия / тепловой вход) за текущий шаг
        if Q_in > 1e-12:
            self._stirling_efficiency = max(0.0, (work_out - mechanical_losses) / Q_in) * 100.0
        else:
            self._stirling_efficiency = 0.0

        # rpm и прочие параметры
        self._stirling_rpm = self._stirling_frequency * 60.0

        # сохраняем истории для графиков
        self._stirling_pressure = P
        self._stirling_pressure_history.append(P)
        self._stirling_volume_history.append(V_total)
        self._stirling_work_history.append(work_out)

        if len(self._stirling_pressure_history) > 200:
            self._stirling_pressure_history.pop(0)
            self._stirling_volume_history.pop(0)
            self._stirling_work_history.pop(0)

        # размеры для рисования (пиксели) — масштабируем для удобства отображения
        cylinder_width = 80
        cylinder_height = 150
        piston_height = 20

        hot_cylinder_x = cx - 150
        hot_cylinder_y = cy - 100
        cold_cylinder_x = cx + 150
        cold_cylinder_y = cy - 100

        Gizmos.draw_rect((hot_cylinder_x, hot_cylinder_y), cylinder_width, cylinder_height,
                         color=(200, 50, 50), filled=False, thickness=3, world_space=True)
        Gizmos.draw_rect((cold_cylinder_x, cold_cylinder_y), cylinder_width, cylinder_height,
                         color=(50, 50, 200), filled=False, thickness=3, world_space=True)

        # позиции поршней для отображения (переводим piston_pos 0..1 в y-позицию)
        hot_piston_y = hot_cylinder_y - cylinder_height / 2 + piston_hot_pos * cylinder_height
        cold_piston_y = cold_cylinder_y - cylinder_height / 2 + piston_cold_pos * cylinder_height

        Gizmos.draw_rect((hot_cylinder_x, hot_piston_y), cylinder_width - 10, piston_height,
                         color=(150, 150, 150), filled=True, world_space=True)
        Gizmos.draw_rect((cold_cylinder_x, cold_piston_y), cylinder_width - 10, piston_height,
                         color=(150, 150, 150), filled=True, world_space=True)

        # визуализация газа внутри
        gas_hot_height = hot_piston_y - (hot_cylinder_y - cylinder_height / 2)
        gas_cold_height = cold_piston_y - (cold_cylinder_y - cylinder_height / 2)

        hot_intensity = min(255, int(self._stirling_temp_gas_hot / 4))
        cold_intensity = min(255, int(self._stirling_temp_gas_cold / 2))

        Gizmos.draw_rect((hot_cylinder_x, hot_cylinder_y - cylinder_height / 2 + gas_hot_height / 2),
                         cylinder_width - 15, gas_hot_height,
                         color=(hot_intensity, hot_intensity // 4, 0, 100), filled=True, world_space=True)
        Gizmos.draw_rect((cold_cylinder_x, cold_cylinder_y - cylinder_height / 2 + gas_cold_height / 2),
                         cylinder_width - 15, gas_cold_height,
                         color=(0, cold_intensity // 4, cold_intensity, 100), filled=True, world_space=True)

        # маховик
        flywheel_x = cx
        flywheel_y = cy + 150
        flywheel_radius = 60

        Gizmos.draw_circle((flywheel_x, flywheel_y), flywheel_radius,
                           color=(100, 100, 100), filled=False, thickness=5, world_space=True)

        for i in range(8):
            angle = i * np.pi / 4 + self._stirling_angle
            spoke_x = flywheel_x + np.cos(angle) * flywheel_radius * 0.8
            spoke_y = flywheel_y + np.sin(angle) * flywheel_radius * 0.8
            Gizmos.draw_line((flywheel_x, flywheel_y), (spoke_x, spoke_y),
                             color=(80, 80, 80), thickness=3, world_space=True)

        crank_x = flywheel_x + np.cos(self._stirling_angle) * flywheel_radius * 0.7
        crank_y = flywheel_y + np.sin(self._stirling_angle) * flywheel_radius * 0.7

        Gizmos.draw_line((hot_cylinder_x, hot_piston_y), (crank_x, crank_y),
                         color=(120, 120, 120), thickness=4, world_space=True)

        displacer_crank_x = flywheel_x + np.cos(self._stirling_displacer_angle) * flywheel_radius * 0.5
        displacer_crank_y = flywheel_y + np.sin(self._stirling_displacer_angle) * flywheel_radius * 0.5

        Gizmos.draw_line((cold_cylinder_x, cold_piston_y), (displacer_crank_x, displacer_crank_y),
                         color=(120, 120, 120), thickness=4, world_space=True)

        Gizmos.draw_line((hot_cylinder_x + cylinder_width / 2, hot_cylinder_y + cylinder_height / 2),
                         (cold_cylinder_x - cylinder_width / 2, cold_cylinder_y + cylinder_height / 2),
                         color=(200, 200, 0), thickness=6, world_space=True)

        # текстовая информация
        info_x = cx - 400
        info_y = cy + 300

        Gizmos.draw_text((info_x, info_y), f"Давление: {self._stirling_pressure / 101325:.3f} атм",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 25), f"Объём общий: {V_total * 1e6:.1f} см³",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 50), f"Мощность: {self._stirling_power:.2f} Вт",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 75), f"КПД (шаг): {self._stirling_efficiency:.2f}%",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 100), f"Обороты: {self._stirling_rpm:.0f} об/мин",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 125), f"Крутящий момент: {self._stirling_torque:.3f} Н·м",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 150), f"T_gas_hot: {self._stirling_temp_gas_hot:.1f} K",
                         font_size=12, color=(255, 200, 200), world_space=True)
        Gizmos.draw_text((info_x, info_y + 170), f"T_gas_cold: {self._stirling_temp_gas_cold:.1f} K",
                         font_size=12, color=(200, 200, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 190), f"T_regen: {self._stirling_regenerator_temp:.1f} K",
                         font_size=12, color=(255, 255, 0), world_space=True)

        # controls
        controls_x = cx + 200
        controls_y = cy + 250

        Gizmos.draw_text((controls_x, controls_y), f"T_гор: {self._stirling_temp_hot:.0f}K",
                         font_size=12, color=(255, 200, 200), world_space=True)
        Gizmos.draw_button((controls_x + 100, controls_y), "+",
                           on_click=lambda: setattr(self, '_stirling_temp_hot',
                                                    min(1000, self._stirling_temp_hot + 25)),
                           width=20, height=20, world_space=True)
        Gizmos.draw_button((controls_x + 125, controls_y), "-",
                           on_click=lambda: setattr(self, '_stirling_temp_hot', max(350, self._stirling_temp_hot - 25)),
                           width=20, height=20, world_space=True)

        Gizmos.draw_text((controls_x, controls_y + 25), f"T_хол: {self._stirling_temp_cold:.0f}K",
                         font_size=12, color=(200, 200, 255), world_space=True)
        Gizmos.draw_button((controls_x + 100, controls_y + 25), "+",
                           on_click=lambda: setattr(self, '_stirling_temp_cold',
                                                    min(500, self._stirling_temp_cold + 25)),
                           width=20, height=20, world_space=True)
        Gizmos.draw_button((controls_x + 125, controls_y + 25), "-",
                           on_click=lambda: setattr(self, '_stirling_temp_cold',
                                                    max(200, self._stirling_temp_cold - 25)),
                           width=20, height=20, world_space=True)

        Gizmos.draw_text((controls_x, controls_y + 50), f"Частота: {self._stirling_frequency:.2f} Гц",
                         font_size=12, color=(200, 255, 200), world_space=True)
        Gizmos.draw_button((controls_x + 100, controls_y + 50), "+",
                           on_click=lambda: setattr(self, '_stirling_frequency',
                                                    min(10.0, self._stirling_frequency + 0.1)),
                           width=20, height=20, world_space=True)
        Gizmos.draw_button((controls_x + 125, controls_y + 50), "-",
                           on_click=lambda: setattr(self, '_stirling_frequency',
                                                    max(0.1, self._stirling_frequency - 0.1)),
                           width=20, height=20, world_space=True)

        Gizmos.draw_text((controls_x, controls_y + 75), f"Масса газа: {self._stirling_gas_mass * 1000:.2f} г",
                         font_size=12, color=(255, 200, 255), world_space=True)
        Gizmos.draw_button((controls_x + 100, controls_y + 75), "+",
                           on_click=lambda: setattr(self, '_stirling_gas_mass',
                                                    min(0.01, self._stirling_gas_mass + 0.0005)),
                           width=20, height=20, world_space=True)
        Gizmos.draw_button((controls_x + 125, controls_y + 75), "-",
                           on_click=lambda: setattr(self, '_stirling_gas_mass',
                                                    max(0.0001, self._stirling_gas_mass - 0.0005)),
                           width=20, height=20, world_space=True)

        # --- P-V диаграмма (история) ---
        if len(self._stirling_pressure_history) > 50:
            graph_x = cx - 400
            graph_y = cy - 300
            graph_w = 200
            graph_h = 150

            Gizmos.draw_rect((graph_x, graph_y), graph_w, graph_h,
                             color=(40, 40, 40), filled=True, world_space=True)
            Gizmos.draw_rect((graph_x, graph_y), graph_w, graph_h,
                             color=(100, 100, 100), filled=False, thickness=2, world_space=True)

            p_min = min(self._stirling_pressure_history)
            p_max = max(self._stirling_pressure_history)
            v_min = min(self._stirling_volume_history)
            v_max = max(self._stirling_volume_history)

            if p_max > p_min and v_max > v_min:
                for i in range(len(self._stirling_pressure_history) - 1):
                    p1 = self._stirling_pressure_history[i]
                    p2 = self._stirling_pressure_history[i + 1]
                    v1 = self._stirling_volume_history[i]
                    v2 = self._stirling_volume_history[i + 1]

                    x1 = graph_x - graph_w / 2 + (v1 - v_min) / (v_max - v_min) * graph_w
                    y1 = graph_y - graph_h / 2 + (p1 - p_min) / (p_max - p_min) * graph_h
                    x2 = graph_x - graph_w / 2 + (v2 - v_min) / (v_max - v_min) * graph_w
                    y2 = graph_y - graph_h / 2 + (p2 - p_min) / (p_max - p_min) * graph_h

                    color_intensity = int(255 * i / len(self._stirling_pressure_history))
                    Gizmos.draw_line((x1, y1), (x2, y2),
                                     color=(color_intensity, 255 - color_intensity, 100),
                                     thickness=2, world_space=True)

            Gizmos.draw_text((graph_x, graph_y - graph_h / 2 - 20), "P-V диаграмма",
                             font_size=12, color=(255, 255, 255), world_space=True)

        # теоретический КПД Карно
        theoretical_efficiency = (1.0 - self._stirling_temp_cold / self._stirling_temp_hot) * 100.0
        Gizmos.draw_text((info_x, info_y + 220), f"Теоретический КПД Карно: {theoretical_efficiency:.2f}%",
                         font_size=12, color=(255, 255, 0), world_space=True)

        # конец функции
        return

        # Gizmos.draw_text((cx, cy - 350), "ДВИГАТЕЛЬ СТИРЛИНГА",
        #                  font_size=20, color=(255, 255, 255), world_space=True)
        # Gizmos.draw_text((cx, cy - 320), "Численная термодинамическая модель",
        #                  font_size=14, color=(200, 200, 200), world_space=True)

    def draw_demo_ui(self, position=(0, 0)):
        cx, cy = position
        demo_keys = list(self._demos.keys())
        current_demo_key = demo_keys[self._demo_index]
        demo = self._demos[current_demo_key]

        demo["function"](position)

        Gizmos.draw_text((cx, cy + 650), f"[{self._demo_index + 1}/{len(demo_keys)}] {demo['title']}",
                         font_size=18, color=(255, 255, 255), world_space=True, font_world_space=True)
        Gizmos.draw_text((cx, cy + 680), demo["description"],
                         font_size=14, color=(200, 200, 200), world_space=True, font_world_space=True)

        Gizmos.draw_button((cx - 200, cy + 650), "< Назад",
                           width=80, height=30, world_space=True, font_world_space=True,
                           on_click=lambda: setattr(self, "_demo_index", (self._demo_index - 1) % len(demo_keys)))
        Gizmos.draw_button((cx + 200, cy + 650), "Вперед >",
                           width=80, height=30, world_space=True, font_world_space=True,
                           on_click=lambda: setattr(self, "_demo_index", (self._demo_index + 1) % len(demo_keys)))

    @profile("demo_turing_machine", "demo")
    def demo_turing_machine(self, position=(0, 0)):
        cx, cy = position

        if not hasattr(self, '_turing_init'):
            self._turing_init = True
            self._turing_tape = ['_'] * 50
            self._turing_head_pos = 25
            self._turing_state = 'q0'
            self._turing_step = 0
            self._turing_running = False
            self._turing_speed = 1.0
            self._turing_last_step_time = 0
            self._turing_halt = False
            self._turing_program = {
                ('q0', '0'): ('q1', '1', 'R'),
                ('q0', '1'): ('q2', '0', 'L'),
                ('q0', '_'): ('q_halt', '_', 'N'),
                ('q1', '0'): ('q0', '0', 'R'),
                ('q1', '1'): ('q1', '1', 'R'),
                ('q1', '_'): ('q2', '0', 'L'),
                ('q2', '0'): ('q2', '0', 'L'),
                ('q2', '1'): ('q0', '1', 'R'),
                ('q2', '_'): ('q_halt', '_', 'N')
            }
            self._turing_program_name = "Двоичный счетчик"
            self._turing_history = []
            self._turing_max_steps = 1000
            self._turing_tape[22] = '1'
            self._turing_tape[23] = '0'
            self._turing_tape[24] = '1'
            self._turing_tape[25] = '1'
            self._turing_tape[26] = '0'

        current_time = self._turing_step * 0.016

        if self._turing_running and not self._turing_halt:
            if current_time - self._turing_last_step_time > 1.0 / self._turing_speed:
                self._turing_last_step_time = current_time

                current_symbol = self._turing_tape[self._turing_head_pos]
                key = (self._turing_state, current_symbol)

                if key in self._turing_program:
                    new_state, new_symbol, direction = self._turing_program[key]

                    self._turing_history.append({
                        'step': self._turing_step,
                        'state': self._turing_state,
                        'symbol': current_symbol,
                        'head_pos': self._turing_head_pos,
                        'tape': self._turing_tape.copy()
                    })

                    self._turing_tape[self._turing_head_pos] = new_symbol
                    self._turing_state = new_state

                    if direction == 'R':
                        self._turing_head_pos = min(len(self._turing_tape) - 1, self._turing_head_pos + 1)
                    elif direction == 'L':
                        self._turing_head_pos = max(0, self._turing_head_pos - 1)

                    self._turing_step += 1

                    if new_state == 'q_halt' or self._turing_step >= self._turing_max_steps:
                        self._turing_halt = True
                        self._turing_running = False
                else:
                    self._turing_halt = True
                    self._turing_running = False

        tape_start_x = cx - 400
        tape_y = cy - 100
        cell_width = 40
        cell_height = 40
        visible_cells = 20

        start_cell = max(0, min(len(self._turing_tape) - visible_cells, self._turing_head_pos - visible_cells // 2))

        for i in range(visible_cells):
            cell_index = start_cell + i
            if cell_index >= len(self._turing_tape):
                break

            cell_x = tape_start_x + i * cell_width

            if cell_index == self._turing_head_pos:
                Gizmos.draw_rect((cell_x, tape_y), cell_width, cell_height,
                                 color=(255, 255, 0), filled=True, world_space=True)
            else:
                Gizmos.draw_rect((cell_x, tape_y), cell_width, cell_height,
                                 color=(200, 200, 200), filled=True, world_space=True)

            Gizmos.draw_rect((cell_x, tape_y), cell_width, cell_height,
                             color=(0, 0, 0), filled=False, thickness=2, world_space=True)

            symbol = self._turing_tape[cell_index]
            Gizmos.draw_text((cell_x, tape_y), symbol,
                             font_size=18, color=(0, 0, 0), world_space=True)

        head_x = tape_start_x + (self._turing_head_pos - start_cell) * cell_width
        head_y = tape_y - 60

        Gizmos.draw_rect((head_x, head_y), 30, 20,
                         color=(255, 0, 0), filled=True, world_space=True)
        Gizmos.draw_text((head_x, head_y), "HEAD",
                         font_size=10, color=(255, 255, 255), world_space=True)

        Gizmos.draw_line((head_x, head_y + 10), (head_x, tape_y - cell_height / 2),
                         color=(255, 0, 0), thickness=3, world_space=True)

        state_x = cx - 200
        state_y = cy + 100

        state_color = (0, 255, 0) if not self._turing_halt else (255, 0, 0)
        if self._turing_state == 'q_halt':
            state_color = (255, 100, 100)

        Gizmos.draw_circle((state_x, state_y), 40,
                           color=state_color, filled=True, world_space=True)
        Gizmos.draw_circle((state_x, state_y), 40,
                           color=(0, 0, 0), filled=False, thickness=3, world_space=True)

        Gizmos.draw_text((state_x, state_y), self._turing_state,
                         font_size=14, color=(0, 0, 0), world_space=True)

        info_x = cx - 400
        info_y = cy + 200

        Gizmos.draw_text((info_x, info_y), f"Программа: {self._turing_program_name}",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 25), f"Шаг: {self._turing_step}",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 50), f"Позиция головки: {self._turing_head_pos}",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 75), f"Текущий символ: {self._turing_tape[self._turing_head_pos]}",
                         font_size=14, color=(255, 255, 255), world_space=True)
        Gizmos.draw_text((info_x, info_y + 100), f"Состояние: {'Остановлен' if self._turing_halt else 'Активен'}",
                         font_size=14, color=(255, 255, 255), world_space=True)

        controls_x = cx + 100
        controls_y = cy + 200

        Gizmos.draw_button((controls_x, controls_y), "Старт" if not self._turing_running else "Стоп",
                           width=60, height=30, world_space=True,
                           on_click=lambda: setattr(self, '_turing_running', not self._turing_running))

        Gizmos.draw_button((controls_x + 80, controls_y), "Шаг",
                           width=60, height=30, world_space=True,
                           on_click=lambda: self._turing_step_once())

        Gizmos.draw_button((controls_x + 160, controls_y), "Сброс",
                           width=60, height=30, world_space=True,
                           on_click=lambda: self._turing_reset())

        Gizmos.draw_text((controls_x, controls_y + 40), f"Скорость: {self._turing_speed:.1f}",
                         font_size=12, color=(200, 255, 200), world_space=True)
        Gizmos.draw_button((controls_x + 80, controls_y + 40), "+",
                           width=20, height=20, world_space=True,
                           on_click=lambda: setattr(self, '_turing_speed', min(10.0, self._turing_speed + 0.5)))
        Gizmos.draw_button((controls_x + 105, controls_y + 40), "-",
                           width=20, height=20, world_space=True,
                           on_click=lambda: setattr(self, '_turing_speed', max(0.1, self._turing_speed - 0.5)))

        rules_x = cx + 100
        rules_y = cy - 200

        Gizmos.draw_text((rules_x, rules_y), "Правила программы:",
                         font_size=12, color=(255, 255, 0), world_space=True)

        rule_y = rules_y + 25
        for i, (key, value) in enumerate(list(self._turing_program.items())[:6]):
            state, symbol = key
            new_state, new_symbol, direction = value
            rule_text = f"{state},{symbol} → {new_state},{new_symbol},{direction}"
            color = (255, 255, 255) if key != (self._turing_state, self._turing_tape[self._turing_head_pos]) else (
            255, 255, 0)
            Gizmos.draw_text((rules_x, rule_y + i * 20), rule_text,
                             font_size=10, color=color, world_space=True)

        if len(self._turing_history) > 0:
            history_x = cx - 200
            history_y = cy - 300

            Gizmos.draw_text((history_x, history_y), "История (последние 5 шагов):",
                             font_size=12, color=(200, 200, 255), world_space=True)

            for i, entry in enumerate(self._turing_history[-5:]):
                y_pos = history_y + 25 + i * 20
                history_text = f"Шаг {entry['step']}: {entry['state']}, '{entry['symbol']}' → поз.{entry['head_pos']}"
                Gizmos.draw_text((history_x, y_pos), history_text,
                                 font_size=10, color=(180, 180, 180), world_space=True)

    def _turing_step_once(self):
        if not self._turing_halt:
            current_symbol = self._turing_tape[self._turing_head_pos]
            key = (self._turing_state, current_symbol)

            if key in self._turing_program:
                new_state, new_symbol, direction = self._turing_program[key]

                self._turing_history.append({
                    'step': self._turing_step,
                    'state': self._turing_state,
                    'symbol': current_symbol,
                    'head_pos': self._turing_head_pos,
                    'tape': self._turing_tape.copy()
                })

                self._turing_tape[self._turing_head_pos] = new_symbol
                self._turing_state = new_state

                if direction == 'R':
                    self._turing_head_pos = min(len(self._turing_tape) - 1, self._turing_head_pos + 1)
                elif direction == 'L':
                    self._turing_head_pos = max(0, self._turing_head_pos - 1)

                self._turing_step += 1

                if new_state == 'q_halt' or self._turing_step >= self._turing_max_steps:
                    self._turing_halt = True
            else:
                self._turing_halt = True

    def _turing_reset(self):
        self._turing_tape = ['_'] * 50
        self._turing_head_pos = 25
        self._turing_state = 'q0'
        self._turing_step = 0
        self._turing_running = False
        self._turing_last_step_time = 0
        self._turing_halt = False
        self._turing_history = []
        self._turing_tape[22] = '1'
        self._turing_tape[23] = '0'
        self._turing_tape[24] = '1'
        self._turing_tape[25] = '1'
        self._turing_tape[26] = '0'
    def draw_extra_gizmos(self):
        self.draw_demo_ui(position=(0, 0))
        # self.demo_stirling_engine()
        # self.demo_fluid_dynamics()
        # self.demo_quantum_field()
        # self.demo_raycast_game()
        # self.demo_galaxy_simulation()
        # self.demo_cellular_life_simulation(center=(0, 0))
        # self.demo_supermodel()
        # self.demo_quantum_fractal()
        # self.demo_quantum_swarm()
        # self.quantum_mandala()
        # self.demo_wavy_circle()
        # self.draw_oscilloscope(origin=(-500, -800), width=1000, height=200)
        # self.demo_piano()
        # self.demo_graphing_calculator()
        # self.demo_pulsing_text()
        # self.demo_particle_swarm()
        # self.demo_spiral()
        # self.demo_dynamic_arrow()
        # self.demo_audio_bars()
        # self.demo_fractal_tree()
        # self.demo_rotating_arrows()
        # self.demo_planet_orbits()
        # self.demo_spring()
        # self.demo_wave_grid()
        # self.demo_rose_curve()
        # self.demo_am_signal()
        # self.demo_lorenz_attractor()
        # self.demo_double_pendulum()
        # self.demo_boids()
        # self.demo_cube_wireframe()
        # self.demo_bubble_sort()
        # self.demo_vector_field()
        # self.demo_game_of_life()
        # self.demo_barnsley_fern()
        # self.demo_torus_knot()
        # self.demo_axes()
        # self.demo_rotating_circle_arrow()
        # self.demo_trail()
        # self.demo_basic_shapes()
        # self.demo_langton_ant((0,800))
        # self.demo_hypercube()
    def _update_logic(self, delta_time: float):
        self.phase += delta_time * self.time_scale
        if self.auto_cycle:
            self.cycle_timer += delta_time
            if self.cycle_timer >= self.cycle_interval:
                self.cycle_timer = 0.0
                self.signal_index = (self.signal_index + 1) % len(self.signal_types)
    def draw(self, delta_time: float):
        self._update_logic(delta_time)
        self.draw_extra_gizmos()
        for i, fourier in enumerate(self.fourier_data_list):
            self._draw_fourier_epicycles(self.mandelbrot_contours[i][0], fourier, self.drawing_points_list[i], self.phase)



@profile("calculate_forces", "demo")
@njit(nopython=True, cache=True)
def calculate_forces(positions, masses, forces, G=0.1, softening=5.0):
    n = len(positions)
    forces.fill(0.0)
    for i in range(n):
        for j in range(i + 1, n):
            dx = positions[j][0] - positions[i][0]
            dy = positions[j][1] - positions[i][1]
            dist_sq = dx * dx + dy * dy + softening * softening
            dist = math.sqrt(dist_sq)
            if dist > 0:
                force = G * masses[i] * masses[j] / dist_sq
                fx = force * dx / dist
                fy = force * dy / dist
                forces[i][0] += fx
                forces[i][1] += fy
                forces[j][0] -= fx
                forces[j][1] -= fy

@profile("update_particles", "demo")
@njit(nopython=True, cache=True)
def update_particles(positions, velocities, masses, forces, dt=0.016, damping=0.999):
    n = len(positions)
    for i in range(n):
        ax = forces[i][0] / masses[i]
        ay = forces[i][1] / masses[i]
        velocities[i][0] += ax * dt
        velocities[i][1] += ay * dt
        velocities[i][0] *= damping
        velocities[i][1] *= damping
        positions[i][0] += velocities[i][0] * dt
        positions[i][1] += velocities[i][1] * dt