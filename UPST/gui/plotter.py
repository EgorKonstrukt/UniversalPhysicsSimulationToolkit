import collections, math, pygame, time
from typing import Dict, List, Optional, Tuple


class Plotter:
    BASE_COLORS: List[Tuple[int, int, int]] = [(0, 255, 255), (255, 105, 180), (147, 255, 180), (255, 215, 0),
                                               (130, 130, 255), (255, 165, 0), (255, 99, 71), (128, 0, 128),
                                               (255, 192, 203), (144, 238, 144), (255, 160, 122), (173, 216, 230)]
    FONT_NAME: str = "Consolas"
    BG_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 255)
    LABEL_BG_COLOR: Tuple[int, int, int] = (40, 40, 40)
    GRID_COLOR: Tuple[int, int, int, int] = (60, 60, 70, 190)
    DIVIDER_COLOR: Tuple[int, int, int] = (160, 160, 170)
    TEXT_COLOR: Tuple[int, int, int] = (180, 180, 180)
    NO_DATA_COLOR: Tuple[int, int, int] = (128, 128, 128)
    FILTER_LABEL_COLOR: Tuple[int, int, int] = (200, 200, 200)
    AXIS_COLOR: Tuple[int, int, int] = (200, 200, 200)
    ZERO_COLOR: Tuple[int, int, int] = (255, 255, 100)
    ENVELOPE_COLOR: Tuple[int, int, int] = (255, 120, 255)
    SPECTRUM_BG: Tuple[int, int, int] = (30, 30, 40)
    SPECTRUM_BAR_COLOR: Tuple[int, int, int] = (100, 200, 255)
    MARGIN_TOP: int = 20
    MARGIN_BOTTOM: int = 30
    MARGIN_LEFT: int = 60
    LABEL_Y_OFFSET: int = 5
    LABEL_LINE_SPACING: int = 18
    FILTER_LABEL_X_OFFSET: int = 150
    GRID_LABEL_X_OFFSET: int = 60
    BASE_GRID_PIXEL_STEP: int = 50
    PADDING_RATIO: float = 0.1
    MAX_HOVER_LINES: int = 8

    def __init__(self, surface_size: Tuple[int, int], max_samples: int = 120,
                 smoothing_factor: float = 0.15, font_size: int = 16, sort_by_value: bool = True,
                 x_label: str = "", y_label: str = "", grid_density: float = 1.0,
                 min_peaks_for_osc: int = 3, min_crossings_for_osc: int = 2,
                 min_extrema_for_osc: int = 3, osc_cache_ttl: int = 10,
                 enable_osc_analysis: bool = True):
        self.surface_size = surface_size
        self.max_samples = max(1, int(max_samples))
        self.smoothing_factor = smoothing_factor
        self.sort_by_value = sort_by_value
        self.x_label = x_label
        self.y_label = y_label
        self.grid_density = max(0.1, float(grid_density))
        self.min_peaks_for_osc = min_peaks_for_osc
        self.min_crossings_for_osc = min_crossings_for_osc
        self.min_extrema_for_osc = min_extrema_for_osc
        self.osc_cache_ttl = osc_cache_ttl
        self.enable_osc_analysis = enable_osc_analysis
        self.data: Dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=self.max_samples))
        self.x_data: Dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=self.max_samples))
        self.colors: Dict[str, Tuple[int, int, int]] = {}
        self.hidden_keys: set = set()
        self.overlay_mode: bool = True
        self.font = pygame.font.SysFont(self.FONT_NAME, font_size)
        self._smoothed_range: Dict[str, Tuple[float, float]] = {}
        self.surface = pygame.Surface(surface_size, pygame.SRCALPHA)
        self.groups: Dict[str, str] = {}
        self.group_visibility: Dict[str, bool] = {}
        self.current_group_filter: str = "All"
        self.available_groups: set = {"ungrouped"}
        self._osc_cache: Dict[str, Tuple[Dict, int]] = {}
        self._frame_counter: int = 0

        self._mouse_pos: Optional[Tuple[int, int]] = None
        self._hovered_key: Optional[str] = None
        self._hovered_slope: float = 0.0

        self._hovered_x: Optional[float] = None
        self._hovered_y: Optional[float] = None
        self._hovered_idx: Optional[int] = None
        self._hovered_area: float = 0.0
        self._hovered_key: Optional[str] = None
        self._hovered_info: Optional[Dict] = None

    def _compute_integral(self, xs: List[float], ys: List[float], start_idx: int, end_idx: int) -> float:
        if end_idx <= start_idx or len(xs) < 2: return 0.0
        total = 0.0
        for i in range(start_idx, end_idx):
            dx = xs[i + 1] - xs[i]
            avg_y = (ys[i] + ys[i + 1]) / 2
            total += dx * avg_y
        return total
    def _compute_local_stats(self, xs: List[float], ys: List[float], idx: int) -> Dict[str, float]:
        win = max(1, min(3, len(xs) // 4))
        l = max(0, idx - win)
        r = min(len(xs), idx + win + 1)
        window_ys = ys[l:r]
        window_xs = xs[l:r]
        avg = sum(window_ys) / len(window_ys)
        std = math.sqrt(sum((y - avg) ** 2 for y in window_ys) / len(window_ys)) if len(window_ys) > 1 else 0.0
        slope, _ = self._linear_regression(window_xs, window_ys)
        return {"x": xs[idx], "y": ys[idx], "local_avg": avg, "local_std": std, "slope": slope}
    @staticmethod
    def _nice_step(range_val: float, pixel_length: int, density: float = 1.0) -> float:
        if range_val <= 0: return 1.0
        target_steps = max(2, int(pixel_length / 50))
        step_approx = range_val / target_steps
        exponent = int(math.floor(math.log10(step_approx)))
        mantissa = step_approx / (10 ** exponent)
        if mantissa <= 0.5: nice_mantissa = 0.5
        elif mantissa <= 1: nice_mantissa = 1.0
        elif mantissa <= 2: nice_mantissa = 2.0
        elif mantissa <= 5: nice_mantissa = 5.0
        else: nice_mantissa = 10.0
        base_step = nice_mantissa * (10 ** exponent)
        return base_step / max(0.1, density)

    def _get_color(self, key: str) -> Tuple[int, int, int]:
        if key not in self.colors:
            self.colors[key] = self.BASE_COLORS[len(self.colors) % len(self.BASE_COLORS)]
        return self.colors[key]

    def add_data(self, key: str, y: float, x: Optional[float] = None, group: Optional[str] = None) -> None:
        self.data[key].append(y)
        if x is None: x = time.perf_counter() * 1000
        self.x_data[key].append(x)
        group = group or "ungrouped"
        self.groups[key] = group
        self.available_groups.add(group)
        self.group_visibility.setdefault(group, True)

    def set_overlay_mode(self, mode: bool) -> None: self.overlay_mode = mode
    def set_sort_by_value(self, sort_by_value: bool) -> None: self.sort_by_value = sort_by_value
    def clear_data(self) -> None:
        self.data.clear(); self.x_data.clear(); self.groups.clear()
        self.available_groups = {"ungrouped"}; self.group_visibility.clear()
        self._osc_cache.clear()
    def hide_key(self, key: str) -> None: self.hidden_keys.add(key)
    def show_key(self, key: str) -> None: self.hidden_keys.discard(key)
    def clear_key(self, key: str) -> None:
        self.data.pop(key, None); self.x_data.pop(key, None)
        self._osc_cache.pop(key, None)
    def set_group_filter(self, group_name: str) -> None: self.current_group_filter = group_name
    def get_available_groups(self) -> List[str]:
        return ["All"] + sorted(self.available_groups - {"ungrouped"}) if len(self.available_groups) > 1 else ["All"]
    def set_group_visibility(self, group_name: str, visible: bool) -> None: self.group_visibility[group_name] = visible
    def is_group_visible(self, group_name: str) -> bool: return self.group_visibility.get(group_name, True)
    def set_osc_analysis_enabled(self, enable: bool) -> None: self.enable_osc_analysis = enable

    def _get_filtered_keys(self) -> List[str]:
        keys = [k for k in self.data if k not in self.hidden_keys]
        if self.current_group_filter == "All":
            return [k for k in keys if self.is_group_visible(self.groups.get(k, "ungrouped"))]
        return [k for k in keys if self.groups.get(k, "ungrouped") == self.current_group_filter]

    def _render_no_data(self) -> None:
        txt = self.font.render("No data to display", True, self.NO_DATA_COLOR)
        self.surface.blit(txt, txt.get_rect(center=(self.surface_size[0] // 2, self.surface_size[1] // 2)))

    def _get_padded_range(self, val_min: float, val_max: float) -> Tuple[float, float]:
        val_range = val_max - val_min or 1.0
        pad = val_range * self.PADDING_RATIO
        return val_min - pad, val_max + pad

    def _find_extrema(self, ys: List[float]) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        if len(ys) < 3: return [], []
        peaks, troughs = [], []
        for i in range(1, len(ys) - 1):
            window = ys[max(0, i - 2):min(len(ys), i + 3)]
            local_max = max(window); local_min = min(window)
            if ys[i] == local_max and ys[i] > ys[i - 1] and ys[i] > ys[i + 1]:
                prominence = ys[i] - max(ys[i - 1], ys[i + 1])
                peaks.append((i, prominence))
            elif ys[i] == local_min and ys[i] < ys[i - 1] and ys[i] < ys[i + 1]:
                prominence = min(ys[i - 1], ys[i + 1]) - ys[i]
                troughs.append((i, prominence))
        return peaks, troughs

    def _linear_regression(self, xs: List[float], ys: List[float]) -> Tuple[float, float]:
        if len(xs) < 2: return 0.0, float('nan')
        n = len(xs); sum_x = sum(xs); sum_y = sum(ys); sum_xy = sum(x*y for x, y in zip(xs, ys)); sum_x2 = sum(x*x for x in xs)
        denom = n * sum_x2 - sum_x * sum_x
        if abs(denom) < 1e-12: return 0.0, float('nan')
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept

    def _detect_zero_crossings(self, ys: List[float], xs: List[float]) -> List[float]:
        if len(ys) < 2: return []
        crossings = []
        for i in range(1, len(ys)):
            y0, y1 = ys[i - 1], ys[i]
            if y0 * y1 < 0:
                t = abs(y0) / (abs(y0) + abs(y1))
                x_cross = xs[i - 1] + t * (xs[i] - xs[i - 1])
                crossings.append(x_cross)
        return crossings

    def _detect_frequency_components(self, ys: List[float], xs: List[float]) -> List[Tuple[float, float]]:
        if len(ys) < 8: return []
        dt = xs[-1] - xs[0]
        if dt <= 0: return []
        N = len(ys); Fs = N / dt
        fft_vals = []
        for k in range(1, min(N // 2, 20)):
            real = imag = 0.0
            for n in range(N):
                angle = 2 * math.pi * k * n / N
                real += ys[n] * math.cos(angle)
                imag -= ys[n] * math.sin(angle)
            mag = math.sqrt(real*real + imag*imag) / N
            freq = k * Fs / N
            fft_vals.append((mag, freq))
        fft_vals.sort(reverse=True)
        if not fft_vals: return []
        dominant = fft_vals[0][0]
        if dominant < 0.05 * sum(m for m, _ in fft_vals): return []
        return fft_vals[:3]

    def _estimate_period_from_crossings(self, crossings: List[float]) -> float:
        if len(crossings) < 2: return float('inf')
        intervals = [crossings[i] - crossings[i - 1] for i in range(1, len(crossings))]
        return sum(intervals) / len(intervals) * 2 if intervals else float('inf')

    def _estimate_amplitude_and_decay(self, ys: List[float], xs: List[float]) -> Tuple[float, float]:
        if len(ys) < 3: return 0.0, 0.0
        peaks, troughs = self._find_extrema(ys)
        if len(peaks) + len(troughs) < self.min_peaks_for_osc: return 0.0, 0.0
        extrema = [(i, abs(ys[i])) for i, _ in (peaks + troughs)]
        if len(extrema) < 2: return sum(a for _, a in extrema) / len(extrema), 0.0
        extrema.sort()
        x_ext = [xs[i] for i, _ in extrema]
        ln_amps = [math.log(a) for _, a in extrema if a > 1e-9]
        if len(ln_amps) < 2: return sum(a for _, a in extrema) / len(extrema), 0.0
        slope, _ = self._linear_regression(x_ext, ln_amps)
        mean_amp = sum(a for _, a in extrema) / len(extrema)
        return mean_amp, -slope

    def get_oscillation_stats(self, key: str) -> Dict[str, float]:
        if not self.enable_osc_analysis or key not in self.data or len(self.data[key]) < 6:
            return {"period": float('inf'), "mean_amplitude": 0.0, "decay_rate": 0.0, "damping_ratio": 0.0,
                    "valid": False, "weak": False}
        ys = list(self.data[key])
        xs = list(self.x_data[key])
        base = sum(ys) / len(ys)
        ys_centered = [y - base for y in ys]
        crossings = self._detect_zero_crossings(ys_centered, xs)
        peaks, troughs = self._find_extrema(ys_centered)
        enough_extrema = (len(peaks) + len(troughs)) >= self.min_extrema_for_osc
        enough_crossings = len(crossings) >= self.min_crossings_for_osc
        weak_candidate = enough_extrema and enough_crossings and len(ys) >= 8
        if not weak_candidate:
            return {"period": float('inf'), "mean_amplitude": 0.0, "decay_rate": 0.0, "damping_ratio": 0.0,
                    "valid": False, "weak": False}
        period = self._estimate_period_from_crossings(crossings)
        mean_amp, decay = self._estimate_amplitude_and_decay(ys_centered, xs)
        omega = 2 * math.pi / period if period > 0 else 0
        damping_ratio = min(decay / omega, 1.0) if omega > 1e-6 else 0.0
        freqs = self._detect_frequency_components(ys_centered, xs)
        dominant_freq = freqs[0][1] if freqs else (1.0 / period if period > 0 else 0.0)
        strong_valid = (period > 0.01 and mean_amp > 1e-6 and len(crossings) >= 4 and len(freqs) > 0)
        weak_valid = (period > 0.01 and mean_amp > 1e-6 and enough_crossings and enough_extrema)
        valid = strong_valid or weak_valid
        return {
            "period": period if period != float('inf') else 0.0,
            "mean_amplitude": mean_amp,
            "decay_rate": decay,
            "damping_ratio": damping_ratio,
            "dominant_freq": dominant_freq,
            "spectrum": freqs,
            "valid": valid,
            "weak": not strong_valid and weak_valid
        }

    def _get_cached_osc_stats(self, key: str) -> Dict[str, float]:
        if not self.enable_osc_analysis:
            return {"valid": False}
        self._frame_counter += 1
        current_stats = self.get_oscillation_stats(key)
        if current_stats["valid"]:
            self._osc_cache[key] = (current_stats, self._frame_counter)
            return current_stats
        cached = self._osc_cache.get(key)
        if cached:
            cached_stats, cache_time = cached
            if self._frame_counter - cache_time <= self.osc_cache_ttl:
                return cached_stats
        return {"valid": False}

    def _render_extrema_markers(self, pts: List[Tuple[float, float]], data_key: str,
                                peaks: List[Tuple[int, float]], troughs: List[Tuple[int, float]]) -> None:
        for idx, prom in peaks:
            x, y = pts[idx]
            s = max(5, min(14, int(7 + prom * 40)))
            pygame.draw.polygon(self.surface, (255, 50, 50),
                                [(x, y - s), (x - s * 0.6, y + s * 0.4), (x + s * 0.6, y + s * 0.4)])
        for idx, prom in troughs:
            x, y = pts[idx]
            s = max(5, min(14, int(7 + prom * 40)))
            pygame.draw.polygon(self.surface, (50, 255, 50),
                                [(x, y + s), (x - s * 0.6, y - s * 0.4), (x + s * 0.6, y - s * 0.4)])

    def _render_zero_crossings(self, ys_centered: List[float], xs: List[float],
                               x_min: float, x_max: float, y_zero: float) -> None:
        if not self.enable_osc_analysis: return
        crossings = self._detect_zero_crossings(ys_centered, xs)
        x_range = x_max - x_min or 1.0
        w = self.surface_size[0] - self.MARGIN_LEFT
        for xc in crossings:
            t = (xc - x_min) / x_range
            x = self.MARGIN_LEFT + t * w
            pygame.draw.line(self.surface, self.ZERO_COLOR, (x, y_zero - 7), (x, y_zero + 7), width=2)

    def _render_decay_envelope(self, pts: List[Tuple[float, float]], ys_centered: List[float],
                               xs: List[float], decay: float, mean_amp: float) -> None:
        if not self.enable_osc_analysis or decay <= 1e-6 or not pts: return
        y_max_abs = max(abs(y) for y in ys_centered)
        if y_max_abs < 1e-6: return
        color = self.ENVELOPE_COLOR
        t0 = xs[0]
        env_pts = []
        neg_env_pts = []
        for (px, py), x in zip(pts, xs):
            amp_t = mean_amp * math.exp(-decay * (x - t0))
            ratio = amp_t / y_max_abs
            env_y = py - ratio * (py - self.MARGIN_TOP)
            neg_env_y = py + ratio * (py - self.MARGIN_TOP)
            env_pts.append((px, env_y))
            neg_env_pts.append((px, neg_env_y))
        if len(env_pts) > 1:
            pygame.draw.lines(self.surface, color, False, env_pts, width=2)
            pygame.draw.lines(self.surface, color, False, neg_env_pts, width=2)

    def _render_spectrum(self, stats: Dict[str, float], y_pos: int) -> None:
        if not self.enable_osc_analysis or not stats.get("spectrum"): return
        sp = stats["spectrum"]
        bar_w = 14
        bar_gap = 4
        total_width = len(sp) * (bar_w + bar_gap) - bar_gap
        start_x = self.surface_size[0] - total_width - 20
        pygame.draw.rect(self.surface, self.SPECTRUM_BG, (start_x - 5, y_pos - 10, total_width + 10, 40))
        max_mag = max(m for m, _ in sp)
        for i, (mag, freq) in enumerate(sp):
            h = 30 * (mag / max_mag if max_mag > 0 else 0)
            x = start_x + i * (bar_w + bar_gap)
            pygame.draw.rect(self.surface, self.SPECTRUM_BAR_COLOR, (x, y_pos + 20 - h, bar_w, h))
            txt = self.font.render(f"{freq:.1f}Hz", True, self.TEXT_COLOR)
            self.surface.blit(txt, (x - txt.get_width() // 2 + bar_w // 2, y_pos + 22))

    def _render_overlay_mode(self, keys: List[str]) -> None:
        all_vals = [v for k in keys for v in self.data[k]]
        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_vals:
            self._render_no_data()
            return
        global_min = min(all_vals)
        global_max = max(all_vals)
        y_min, y_max = self._get_padded_range(global_min, global_max)
        y_range = y_max - y_min or 1.0
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        w = self.surface_size[0] - self.MARGIN_LEFT
        x_min = x_max = 0.0
        if all_x:
            x_min_raw, x_max_raw = min(all_x), max(all_x)
            x_min, x_max = self._get_padded_range(x_min_raw, x_max_raw)
        x_range = x_max - x_min or 1.0
        smoothed_key = 'overlay'
        self._smoothed_range.setdefault(smoothed_key, (y_min, y_max))
        old_min, old_max = self._smoothed_range[smoothed_key]
        new_min = old_min + (y_min - old_min) * self.smoothing_factor
        new_max = old_max + (y_max - old_max) * self.smoothing_factor
        self._smoothed_range[smoothed_key] = (new_min, new_max)
        draw_min, draw_max = new_min, new_max
        draw_range = draw_max - draw_min or 1.0
        base_line_y = self.MARGIN_TOP + (-new_min) / draw_range * h if draw_range else self.MARGIN_TOP
        pygame.draw.line(self.surface, self.ZERO_COLOR, (self.MARGIN_LEFT, base_line_y),
                         (self.surface_size[0], base_line_y), width=1)
        for key in keys:
            ys = list(self.data[key])
            xs = list(self.x_data[key])
            if not ys or not xs: continue
            col = self._get_color(key)
            pts = [(self.MARGIN_LEFT + (xs[i] - x_min) / x_range * w,
                    self.MARGIN_TOP + (ys[i] - draw_min) / draw_range * h) for i in range(len(ys))]
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts, width=2)
            if not self.enable_osc_analysis:
                continue
            base = sum(ys) / len(ys)
            ys_centered = [y - base for y in ys]
            pks, trs = self._find_extrema(ys_centered)
            if pks or trs:
                self._render_extrema_markers(pts, key, pks, trs)
            stats = self._get_cached_osc_stats(key)
            if stats["valid"]:
                self._render_zero_crossings(ys_centered, xs, x_min, x_max, base_line_y)
                self._render_decay_envelope(pts, ys_centered, xs, stats["decay_rate"], stats["mean_amplitude"])
        self._draw_labels_overlay(keys)
        self._draw_grid_range(draw_min, draw_max)
        self._draw_x_axis_labels(x_min, x_max)

    def _render_split_mode(self, keys: List[str]) -> None:
        w = self.surface_size[0] - self.MARGIN_LEFT
        total_h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        bar_h = total_h / len(keys) if keys else 0
        all_x = [x for k in keys for x in self.x_data[k]]
        x_min = x_max = 0.0
        if all_x:
            x_min_raw, x_max_raw = min(all_x), max(all_x)
            x_min, x_max = self._get_padded_range(x_min_raw, x_max_raw)
        x_range = x_max - x_min or 1.0
        for i, key in enumerate(keys):
            ys = list(self.data[key])
            xs = list(self.x_data[key])
            if not ys or not xs: continue
            col = self._get_color(key)
            y0 = self.MARGIN_TOP + i * bar_h
            local_min = min(ys)
            local_max = max(ys)
            y_min, y_max = self._get_padded_range(local_min, local_max)
            y_range = y_max - y_min or 1.0
            scale_h = bar_h * 0.8
            smoothed_key = f"bar_{key}"
            self._smoothed_range.setdefault(smoothed_key, (y_min, y_max))
            old_min, old_max = self._smoothed_range[smoothed_key]
            new_min = old_min + (y_min - old_min) * self.smoothing_factor
            new_max = old_max + (y_max - old_max) * self.smoothing_factor
            self._smoothed_range[smoothed_key] = (new_min, new_max)
            draw_min, draw_max = new_min, new_max
            draw_range = draw_max - draw_min or 1.0
            pts = [(self.MARGIN_LEFT + (xs[j] - x_min) / x_range * w,
                    y0 + (ys[j] - draw_min) / draw_range * scale_h) for j in range(len(ys))]
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts, width=2)
            if not self.enable_osc_analysis:
                self._draw_label_split(key, ys, col, y0)
                continue
            base = sum(ys) / len(ys)
            ys_centered = [y - base for y in ys]
            pks, trs = self._find_extrema(ys_centered)
            if pks or trs:
                self._render_extrema_markers(pts, key, pks, trs)
            stats = self._get_cached_osc_stats(key)
            if stats["valid"]:
                base_line_y = y0 + (-new_min) / (new_max - new_min or 1) * scale_h
                self._render_zero_crossings(ys_centered, xs, x_min, x_max, base_line_y)
                self._render_decay_envelope(pts, ys_centered, xs, stats["decay_rate"], stats["mean_amplitude"])
                self._render_spectrum(stats, int(y0 + bar_h - 25))
            self._draw_label_split(key, ys, col, y0)
        for i in range(len(keys) + 1):
            y = self.MARGIN_TOP + i * bar_h
            pygame.draw.line(self.surface, self.DIVIDER_COLOR, (0, y), (self.surface_size[0], y), width=2)

    def _compute_grid_steps(self, axis_length: int) -> int:
        step_px = self.BASE_GRID_PIXEL_STEP * self.grid_density
        return max(1, int(axis_length / step_px))

    def _draw_x_axis_labels(self, x_min: float, x_max: float) -> None:
        w = self.surface_size[0] - self.MARGIN_LEFT
        x_range = x_max - x_min or 1.0
        step = self._nice_step(x_range, w, self.grid_density)
        start = math.floor(x_min / step) * step
        end = math.ceil(x_max / step) * step
        x_vals = []
        val = start
        while val <= end + 1e-9:
            x_vals.append(val)
            val += step
        for x_val in x_vals:
            t = (x_val - x_min) / x_range
            x = self.MARGIN_LEFT + t * w
            pygame.draw.line(self.surface, self.GRID_COLOR, (x, 0), (x, self.surface_size[1]))
            if abs(x_val) < 0.01 or abs(x_val) > 1e5:
                txt = f"{x_val:.2e}"
            else:
                txt = f"{x_val:.4f}".rstrip('0').rstrip('.')
                if '.' not in txt and abs(x_val) < 1000:
                    txt = str(int(round(x_val)))
            lbl = self.font.render(txt, True, self.TEXT_COLOR)
            self.surface.blit(lbl, (x - lbl.get_width() // 2, self.surface_size[1] - self.MARGIN_BOTTOM // 2))

    def _draw_labels_overlay(self, keys: List[str]) -> None:
        y_offset = self.LABEL_Y_OFFSET
        for i, key in enumerate(keys):
            ys = self.data[key]
            avg = sum(ys) / len(ys)
            txt = f"{key} [{self.groups.get(key, 'ungrouped')}]: {ys[-1]:.2f} Avg: {avg:.2f}"
            lbl = self.font.render(txt, True, self._get_color(key))
            bg = pygame.Surface(lbl.get_size())
            bg.fill(self.LABEL_BG_COLOR); bg.set_alpha(200)
            self.surface.blit(bg, (10, y_offset))
            self.surface.blit(lbl, (10, y_offset))
            y_offset += self.LABEL_LINE_SPACING
            if self.enable_osc_analysis:
                stats = self._get_cached_osc_stats(key)
                if stats["valid"]:
                    osc_txt = f"_Osc: T={stats['period']:.1f} A={stats['mean_amplitude']:.2f} γ={stats['decay_rate']:.4f} ζ={stats['damping_ratio']:.3f}"
                    osc_lbl = self.font.render(osc_txt, True, (220, 220, 100))
                    bg = pygame.Surface(osc_lbl.get_size())
                    bg.fill(self.LABEL_BG_COLOR); bg.set_alpha(200)
                    self.surface.blit(bg, (10, y_offset))
                    self.surface.blit(osc_lbl, (10, y_offset))
                    y_offset += self.LABEL_LINE_SPACING
                    self._render_spectrum(stats, y_offset)
                    y_offset += 40

    def _draw_grid_range(self, min_y: float, max_y: float) -> None:
        y_range = max_y - min_y or 1.0
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        step = self._nice_step(y_range, h, self.grid_density)
        start = math.floor(min_y / step) * step
        end = math.ceil(max_y / step) * step
        y_vals = []
        val = start
        while val <= end + 1e-9:
            y_vals.append(val)
            val += step
        for y_val in y_vals:
            t = (y_val - min_y) / y_range
            y = self.MARGIN_TOP + t * h
            pygame.draw.line(self.surface, self.GRID_COLOR, (self.MARGIN_LEFT, y), (self.surface_size[0], y))
            if abs(y_val) < 0.01 or abs(y_val) > 1e5:
                txt = f"{y_val:.2e}"
            else:
                txt = f"{y_val:.4f}".rstrip('0').rstrip('.')
                if '.' not in txt and abs(y_val) < 1000:
                    txt = str(int(round(y_val)))
            lbl = self.font.render(txt, True, self.TEXT_COLOR)
            self.surface.blit(lbl, (self.surface_size[0] - self.GRID_LABEL_X_OFFSET, y - 10))

    def _draw_label_split(self, key: str, vals: collections.deque, col: Tuple[int, int, int], y0: float) -> None:
        avg = sum(vals) / len(vals)
        txt = f"{key} [{self.groups.get(key, 'ungrouped')}]: {vals[-1]:.1f} Avg: {avg:.1f}"
        lbl = self.font.render(txt, True, col)
        bg = pygame.Surface(lbl.get_size())
        bg.fill(self.LABEL_BG_COLOR); bg.set_alpha(200)
        self.surface.blit(bg, (10, y0 + self.LABEL_Y_OFFSET))
        self.surface.blit(lbl, (10, y0 + self.LABEL_Y_OFFSET))

    def _draw_axis_labels(self) -> None:
        if self.x_label:
            txt = self.font.render(self.x_label, True, self.TEXT_COLOR)
            self.surface.blit(txt, (self.surface_size[0] // 2 - txt.get_width() // 2,
                                    self.surface_size[1] - self.MARGIN_BOTTOM // 2 + 10))
        if self.y_label:
            txt = self.font.render(self.y_label, True, self.TEXT_COLOR)
            txt = pygame.transform.rotate(txt, 90)
            self.surface.blit(txt, (5, self.surface_size[1] // 2 - txt.get_height() // 2))



    def set_mouse_position(self, pos: Optional[Tuple[int, int]]) -> None:
        self._mouse_pos = pos
        if pos is None:
            self._hovered_key = None
            return
        mx, my = pos
        w = self.surface_size[0] - self.MARGIN_LEFT
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        if mx < self.MARGIN_LEFT or mx >= self.surface_size[0] or my < self.MARGIN_TOP or my >= self.surface_size[1] - self.MARGIN_BOTTOM:
            self._hovered_key = None
            return

    def _point_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _render_hover_tooltip(self) -> None:
        if self._hovered_key is None or self._hovered_info is None or self._mouse_pos is None:
            return
        info = self._hovered_info
        lines = [
            f"x = {info['x']:.3f} s",
            f"y = {info['y']:.4f}",
            f"dy/dx ≈ {info['slope']:.4f}",
            f"∫ ≈ {self._hovered_area:.4f}"
        ]
        if info.get("osc_stats"):
            osc = info["osc_stats"]
            lines.extend([
                f"T = {osc['period']:.2f} s",
                f"A = {osc['mean_amplitude']:.3f}",
                f"γ = {osc['decay_rate']:.4f}",
                f"ζ = {osc['damping_ratio']:.3f}"
            ])
        lines = lines[:self.MAX_HOVER_LINES]
        mx, my = self._mouse_pos
        y_offset = 0
        for line in lines:
            lbl = self.font.render(line, True, (255, 255, 255))
            bg = pygame.Surface(lbl.get_size(), pygame.SRCALPHA)
            bg.fill((40, 40, 50, 220))
            self.surface.blit(bg, (mx + 12, my + 12 + y_offset))
            self.surface.blit(lbl, (mx + 12, my + 12 + y_offset))
            y_offset += self.LABEL_LINE_SPACING

    def get_surface(self) -> pygame.Surface:
        self.surface.fill(self.BG_COLOR)
        keys = self._get_filtered_keys()
        if not keys:
            self._render_no_data()
        elif self.overlay_mode:
            self._render_overlay_mode(keys)
            self._handle_hover_overlay(keys)
        else:
            self._render_split_mode(keys)
            self._handle_hover_split(keys)
        flt = self.font.render(f"Filter: {self.current_group_filter}", True, self.FILTER_LABEL_COLOR)
        self.surface.blit(flt, (self.surface_size[0] - self.FILTER_LABEL_X_OFFSET, 5))

        if self._hovered_key is not None and self._hovered_x is not None:
            w = self.surface_size[0] - self.MARGIN_LEFT
            h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
            all_vals = [v for k in keys for v in self.data[k]]
            all_x = [x for k in keys for x in self.x_data[k]]
            if all_vals and all_x:
                global_min = min(all_vals)
                global_max = max(all_vals)
                y_min, y_max = self._get_padded_range(global_min, global_max)
                draw_min, draw_max = self._smoothed_range.get('overlay', (y_min, y_max))
                draw_range = draw_max - draw_min or 1.0
                x_min_raw, x_max_raw = min(all_x), max(all_x)
                x_min, x_max = self._get_padded_range(x_min_raw, x_max_raw)
                x_range = x_max - x_min or 1.0
                t = (self._hovered_x - x_min) / x_range
                x = self.MARGIN_LEFT + t * w
                pygame.draw.line(self.surface, (255, 255, 255, 180), (x, self.MARGIN_TOP),
                                 (x, self.surface_size[1] - self.MARGIN_BOTTOM), width=1)
                if self._hovered_idx is not None:
                    ys = list(self.data[self._hovered_key])
                    xs = list(self.x_data[self._hovered_key])
                    start_idx = max(0, self._hovered_idx - 5)
                    pts = [(self.MARGIN_LEFT + (xs[i] - x_min) / x_range * w,
                            self.MARGIN_TOP + (ys[i] - draw_min) / draw_range * h) for i in
                           range(start_idx, self._hovered_idx + 1)]
                    if len(pts) > 1:
                        bottom_y = self.surface_size[1] - self.MARGIN_BOTTOM
                        poly = pts + [(pts[-1][0], bottom_y), (pts[0][0], bottom_y)]
                        pygame.draw.polygon(self.surface, (*self._get_color(self._hovered_key), 80), poly)

        self._render_hover_tooltip()
        self._draw_axis_labels()
        return self.surface

    def _handle_hover_overlay(self, keys: List[str]) -> None:
        if not self._mouse_pos:
            self._hovered_key = None
            self._hovered_info = None
            self._hovered_x = None
            self._hovered_y = None
            self._hovered_idx = None
            self._hovered_area = 0.0
            return
        mx, my = self._mouse_pos
        w = self.surface_size[0] - self.MARGIN_LEFT
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        if mx < self.MARGIN_LEFT or mx >= self.surface_size[0] or my < self.MARGIN_TOP or my >= self.surface_size[
            1] - self.MARGIN_BOTTOM:
            self._hovered_key = None
            self._hovered_info = None
            return
        all_vals = [v for k in keys for v in self.data[k]]
        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_vals or not all_x: return
        global_min = min(all_vals)
        global_max = max(all_vals)
        y_min, y_max = self._get_padded_range(global_min, global_max)
        draw_min, draw_max = self._smoothed_range.get('overlay', (y_min, y_max))
        draw_range = draw_max - draw_min or 1.0
        x_min_raw, x_max_raw = min(all_x), max(all_x)
        x_min, x_max = self._get_padded_range(x_min_raw, x_max_raw)
        x_range = x_max - x_min or 1.0
        best_dist = float('inf')
        best_key = best_info = best_x = best_y = None
        best_idx = None
        for key in keys:
            ys = list(self.data[key])
            xs = list(self.x_data[key])
            if not ys or not xs: continue
            pts = [(self.MARGIN_LEFT + (xs[i] - x_min) / x_range * w,
                    self.MARGIN_TOP + (ys[i] - draw_min) / draw_range * h) for i in range(len(ys))]
            for i, (px, py) in enumerate(pts):
                dist = self._point_distance((mx, my), (px, py))
                if dist < 12 and dist < best_dist:
                    best_dist = dist
                    best_key = key
                    best_x = xs[i]
                    best_y = ys[i]
                    best_idx = i
                    best_info = self._compute_local_stats(xs, ys, i)
                    stats = self._get_cached_osc_stats(key)
                    best_info["osc_stats"] = stats if stats.get("valid") else None
        self._hovered_key = best_key
        self._hovered_info = best_info
        self._hovered_x = best_x
        self._hovered_y = best_y
        self._hovered_idx = best_idx
        if best_key and best_idx is not None:
            xs = list(self.x_data[best_key])
            ys = list(self.data[best_key])
            start_idx = max(0, best_idx - 5)
            self._hovered_area = self._compute_integral(xs, ys, start_idx, best_idx + 1)

    def _handle_hover_split(self, keys: List[str]) -> None:
        if not self._mouse_pos:
            self._hovered_key = None
            self._hovered_info = None
            return
        mx, my = self._mouse_pos
        w = self.surface_size[0] - self.MARGIN_LEFT
        total_h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        bar_h = total_h / len(keys) if keys else 0
        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_x: return
        x_min_raw, x_max_raw = min(all_x), max(all_x)
        x_min, x_max = self._get_padded_range(x_min_raw, x_max_raw)
        x_range = x_max - x_min or 1.0
        best_dist = float('inf')
        best_key = best_info = None
        for i, key in enumerate(keys):
            ys = list(self.data[key])
            xs = list(self.x_data[key])
            if not ys or not xs: continue
            y0 = self.MARGIN_TOP + i * bar_h
            local_min = min(ys)
            local_max = max(ys)
            y_min, y_max = self._get_padded_range(local_min, local_max)
            draw_min, draw_max = self._smoothed_range.get(f"bar_{key}", (y_min, y_max))
            draw_range = draw_max - draw_min or 1.0
            scale_h = bar_h * 0.8
            pts = [(self.MARGIN_LEFT + (xs[j] - x_min) / x_range * w,
                    y0 + (ys[j] - draw_min) / draw_range * scale_h) for j in range(len(ys))]
            for j, (px, py) in enumerate(pts):
                dist = self._point_distance((mx, my), (px, py))
                if dist < 12 and dist < best_dist:
                    best_dist = dist
                    best_key = key
                    best_info = self._compute_local_stats(xs, ys, j)
                    stats = self._get_cached_osc_stats(key)
                    best_info["osc_stats"] = stats if stats.get("valid") else None
        self._hovered_key = best_key
        self._hovered_info = best_info