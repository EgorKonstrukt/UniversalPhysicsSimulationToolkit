import collections, math, pygame, time
from typing import Dict, List, Optional, Tuple
from UPST.config import config

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
                 smoothing_factor: float = config.plotter.smoothing_factor,
                 font_size: int = config.plotter.font_size,
                 sort_by_value: bool = config.plotter.sort_by_value,
                 x_label: str = "", y_label: str = "",
                 grid_density: float = config.plotter.grid_density,
                 min_peaks_for_osc: int = config.plotter.min_peaks_for_osc,
                 min_crossings_for_osc: int = config.plotter.min_crossings_for_osc,
                 min_extrema_for_osc: int = config.plotter.min_extrema_for_osc,
                 osc_cache_ttl: int = config.plotter.osc_cache_ttl,
                 enable_osc_analysis: bool = config.plotter.enable_osc_analysis,
                 show_extrema_labels: bool = config.plotter.show_extrema_labels,
                 show_extrema: bool = config.plotter.show_extrema):
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
        self.show_extrema_labels = show_extrema_labels
        self.show_extrema = show_extrema

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
        self._extrema_labels = []

        self._mouse_pos: Optional[Tuple[int, int]] = None
        self._hovered_key: Optional[str] = None
        self._hovered_slope: float = 0.0

        self.noise_floor: float = getattr(config.plotter, 'noise_floor', 1e-6)

        self._hovered_x: Optional[float] = None
        self._hovered_y: Optional[float] = None
        self._hovered_idx: Optional[int] = None
        self._hovered_area: float = 0.0
        self._hovered_key: Optional[str] = None
        self._hovered_info: Optional[Dict] = None

    def _rect_overlap(self, r1, r2):
        return not (r1.right < r2.left or r1.left > r2.right or r1.bottom < r2.top or r1.top > r2.bottom)

    def _render_extrema_labels(self):
        if not self.show_extrema_labels: return
        if not self._extrema_labels: return
        keep = []
        self._extrema_labels.sort(key=lambda x: abs(x["value"]), reverse=True)
        for cur in self._extrema_labels:
            ok = True
            for k in keep:
                if self._rect_overlap(cur["rect"], k["rect"]):
                    ok = False
                    break
            if ok: keep.append(cur)
        for item in keep:
            txtsurf = item["txt"]
            bg = pygame.Surface((txtsurf.get_width() + 8, txtsurf.get_height() + 4), pygame.SRCALPHA)
            pygame.draw.rect(bg, (30, 30, 40, 220), bg.get_rect(), border_radius=5)
            pygame.draw.rect(bg, (200, 200, 255, 100), bg.get_rect(), 1, border_radius=5)
            self.surface.blit(bg, (item["x"], item["y"]))
            self.surface.blit(txtsurf, (item["x"] + 4, item["y"] + 2))

    def _compute_integral(self, xs: List[float], ys: List[float], start_idx: int, end_idx: int) -> float:
        if end_idx <= start_idx or len(xs) < 2: return 0.0
        total = 0.0
        for i in range(start_idx, end_idx):
            dx = xs[i + 1] - xs[i]
            avg_y = (ys[i] + ys[i + 1]) / 2
            total += dx * avg_y
        return total

    def _compute_local_stats(self, xs, ys, idx):
        n = len(xs)
        if n < 3: return {"mean": ys[idx], "std": 0.0, "slope": 0.0, "second": 0.0, "curv": 0.0, "convex": None,
                          "dtheta": 0.0, "local_ext": None, "dx": 0.0, "dy": 0.0}
        L = max(0, idx - 3)
        R = min(n - 1, idx + 3)
        win_x = xs[L:R + 1]
        win_y = ys[L:R + 1]
        m = sum(win_y) / len(win_y)
        v = sum((y - m) ** 2 for y in win_y) / len(win_y)
        dy1 = ys[idx + 1] - ys[idx - 1] if 0 < idx < n - 1 else 0.0
        dx1 = xs[idx + 1] - xs[idx - 1] if 0 < idx < n - 1 else 1.0
        slope = dy1 / dx1 if dx1 != 0 else 0.0
        d2y = ys[idx + 1] - 2 * ys[idx] + ys[idx - 1] if 0 < idx < n - 1 else 0.0
        d2x = (xs[idx + 1] - xs[idx]) - (xs[idx] - xs[idx - 1]) if 0 < idx < n - 1 else 0.0
        second = (d2y - d2x) / ((dx1 / 2) ** 2) if dx1 != 0 else 0.0
        curv = abs(second) / ((1 + slope * slope) ** 1.5) if (1 + slope * slope) != 0 else 0.0
        convex = "up" if second > 0 else ("down" if second < 0 else None)
        dtheta = (slope - (ys[idx] - ys[idx - 1]) / (
            xs[idx] - xs[idx - 1] if xs[idx] - xs[idx - 1] != 0 else 1)) if idx > 0 else 0.0
        dy = ys[idx] - ys[idx - 1] if idx > 0 else 0.0
        dx = xs[idx] - xs[idx - 1] if idx > 0 else 0.0
        ext = None
        if 0 < idx < n - 1:
            if ys[idx] > ys[idx - 1] and ys[idx] > ys[idx + 1]:
                ext = "local_max"
            elif ys[idx] < ys[idx - 1] and ys[idx] < ys[idx + 1]:
                ext = "local_min"
        mn = min(win_y)
        mx = max(win_y)
        win_sorted = sorted(win_y)
        med = win_sorted[len(win_sorted) // 2]
        return {"mean": m, "std": v ** 0.5, "slope": slope, "second": second, "curv": curv, "convex": convex,
                "dtheta": dtheta, "local_ext": ext, "dx": dx, "dy": dy, "win_min": mn, "win_max": mx, "median": med}

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

    def _detect_frequency_components(self, ys, xs):
        N = len(ys)
        if N < 16 or not self.enable_osc_analysis: return []
        t0 = xs[0]
        tN = xs[-1]
        diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)] if len(xs) > 1 else [1.0]
        dt_med = self._median([abs(d) for d in diffs]) if diffs else 1.0
        scale = 1.0
        if dt_med > 1.0: scale = 0.001
        total_t = (xs[-1] - xs[0]) * scale
        if total_t <= 1e-9: return []
        Fs = N / total_t
        mean_y = sum(ys) / N
        ys_d = [v - mean_y for v in ys]
        w = self._hann_win(N)
        ys_w = [ys_d[i] * w[i] for i in range(N)]
        max_k = min(N // 2, 32)
        comps = []
        for k in range(1, max_k):
            re = im = 0.0
            for n in range(N):
                ang = 2 * math.pi * k * n / N
                re += ys_w[n] * math.cos(ang)
                im -= ys_w[n] * math.sin(ang)
            mag = math.hypot(re, im) / N
            freq = k * Fs / N
            if mag > 1e-9: comps.append((mag, freq, k))
        if not comps: return []
        mags = [m for m, f, _ in comps]
        maxm = max(mags)
        medm = self._median(mags) if mags else 0.0
        res = []
        for m, f, k in comps[:5]:
            if m > 1e-6 and (m > 0.2 * maxm or m > medm * 2):
                res.append((m, f))
        return res[:2]

    def _estimate_period_from_crossings(self, crossings: List[float]) -> float:
        if len(crossings) < 2: return float('inf')
        intervals = [crossings[i] - crossings[i - 1] for i in range(1, len(crossings))]
        return sum(intervals) / len(intervals) * 2 if intervals else float('inf')

    def _hann_win(self, n):
        return [0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)] if n > 1 else [1.0]

    def _median(self, arr):
        a = sorted(arr)
        m = len(a) // 2
        return (a[m] if len(a) % 2 == 1 else 0.5 * (a[m - 1] + a[m])) if a else 0.0

    def _autocorr_period(self, xs, ys):
        n = len(ys)
        if n < 16 or not self.enable_osc_analysis: return float('inf'), 0.0
        mean_y = sum(ys) / n
        y = [v - mean_y for v in ys]
        max_lag = min(n // 4, 64)
        ac = [0.0] * (max_lag + 1)
        den = sum(v * v for v in y) + 1e-12
        for lag in range(1, max_lag + 1):
            num = sum(y[i] * y[i + lag] for i in range(n - lag))
            ac[lag] = num / den
        if not ac[1:]: return float('inf'), 0.0
        mx = max(ac[1:])
        if mx <= 0.05: return float('inf'), mx
        peak_lag = None
        for i in range(2, len(ac) - 1):
            if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.3 * mx:
                peak_lag = i
                break
        if peak_lag is None:
            peak_lag = 1 + ac[1:].index(mx)
        diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)] if len(xs) > 1 else [1.0]
        dt_med = self._median([abs(d) for d in diffs]) if diffs else 1.0
        scale = 1.0
        if dt_med > 1.0: scale = 0.001
        period = peak_lag * dt_med * scale
        return period, mx

    def _estimate_amplitude_and_decay(self, ys, xs):
        if len(ys) < 8 or not self.enable_osc_analysis: return 0.0, 0.0
        pks, tr = self._find_extrema([y - sum(ys) / len(ys) for y in ys])
        ext = [(i, abs(ys[i]), xs[i]) for i, _ in pks + tr]
        if len(ext) < 2:
            mean_amp = sum(abs(v) for v in ys) / len(ys)
            return mean_amp, 0.0
        ext.sort()
        diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)] if len(xs) > 1 else [1.0]
        dt_med = self._median([abs(d) for d in diffs]) if diffs else 1.0
        scale = 1.0
        if dt_med > 1.0: scale = 0.001
        tvals = [t * scale for _, _, t in ext]
        amps = [a for _, a, _ in ext if a > 1e-9]
        if len(amps) < 2: return sum(amps) / len(amps) if amps else 0.0, 0.0
        lnamps = [math.log(a) for a in amps if a > 1e-9]
        if len(lnamps) < 2: return sum(amps) / len(amps), 0.0
        n = len(lnamps)
        xs_lr = tvals[:n]
        sumx = sum(xs_lr)
        sumy = sum(lnamps)
        sumxy = sum(x * y for x, y in zip(xs_lr, lnamps))
        sumx2 = sum(x * x for x in xs_lr)
        denom = n * sumx2 - sumx * sumx
        if abs(denom) < 1e-12: return sum(amps) / len(amps), 0.0
        b = (n * sumxy - sumx * sumy) / denom
        decay = -b if b < 0 else 0.0
        mean_amp = sum(amps) / len(amps)
        return mean_amp, decay

    def get_oscillation_stats(self, key):
        if not self.enable_osc_analysis or key not in self.data or len(self.data[key]) < 16:
            return {"valid": False}
        ys = list(self.data[key])
        xs = list(self.x_data[key])
        if len(xs) != len(ys) or len(xs) < 16: return {"valid": False}
        diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)] if len(xs) > 1 else [1.0]
        dt_med = self._median([abs(d) for d in diffs]) if diffs else 1.0
        scale = 1.0
        if dt_med > 1.0: scale = 0.001
        xs_s = [x * scale for x in xs]
        base = sum(ys) / len(ys)
        ys_c = [y - base for y in ys]
        crossings = self._detect_zero_crossings(ys_c, xs) if self.enable_osc_analysis else []
        pks, tr = self._find_extrema(ys_c)
        peak_count = len(pks)
        trough_count = len(tr)
        if peak_count + trough_count < self.min_extrema_for_osc: return {"valid": False}
        per_cross = self._estimate_period_from_crossings(crossings) if crossings else float('inf')
        per_auto, acf_conf = self._autocorr_period(xs, ys_c)
        freqs = self._detect_frequency_components(ys_c, xs)
        mean_amp, decay = self._estimate_amplitude_and_decay(ys_c, xs)
        period = per_auto if per_auto != float('inf') else (per_cross if per_cross != float('inf') else float('inf'))
        period_s = period * (0.001 if dt_med > 1.0 else 1.0)
        dominant_freq = freqs[0][1] if freqs else (1.0 / period_s if period_s > 1e-9 else 0.0)
        mags = [m for m, _ in freqs] if freqs else []
        snr = (max(mags) / (self._median(mags) + 1e-12)) if mags else 0.0
        omega = 2 * math.pi / period_s if period_s > 1e-9 else 0.0
        damping = min(decay / omega, 1.0) if omega > 1e-12 else 0.0
        half_life = math.log(2) / decay if decay > 1e-12 else float('inf')
        conf = 0.0
        if peak_count + trough_count >= self.min_extrema_for_osc: conf += 0.3
        if len(crossings) >= self.min_crossings_for_osc: conf += 0.3
        if freqs and mags and mags[0] > 0: conf += 0.3
        conf += min(0.1, acf_conf)
        valid = conf >= 0.6 and mean_amp > 1e-6 and period_s > 1e-9 and period_s != float('inf')
        weak = (conf >= 0.4 and mean_amp > 1e-6)
        return {
            "period": period_s, "mean_amplitude": mean_amp, "decay_rate": decay, "damping_ratio": damping,
            "dominant_freq": dominant_freq, "spectrum": freqs[:2], "valid": valid, "weak": weak, "snr": snr,
            "peak_count": peak_count, "trough_count": trough_count, "half_life": half_life, "confidence": conf
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

    def _render_extrema_markers(self, pts, key, peaks, troughs):
        if not self.show_extrema:
            return
        col_peak = (255, 70, 70)
        col_trough = (70, 255, 70)
        self._extrema_labels = []
        for idx, prom in peaks:
            x, y = pts[idx]
            sz = max(6, min(14, int(6 + prom * 40)))
            pygame.draw.polygon(self.surface, col_peak,
                                [(x, y - sz), (x - sz * 0.6, y + sz * 0.4), (x + sz * 0.6, y + sz * 0.4)])
            lbl = self.font.render(f"{pts[idx][1]:.3f}", True, (240, 240, 240))
            rect = lbl.get_rect()
            fx = int(x - rect.width / 2)
            fy = int(y - sz - rect.height - 6)
            rect.move_ip(fx, fy)
            self._extrema_labels.append({"value": pts[idx][1], "x": fx, "y": fy, "rect": rect, "txt": lbl})
        for idx, prom in troughs:
            x, y = pts[idx]
            sz = max(6, min(14, int(6 + prom * 40)))
            pygame.draw.polygon(self.surface, col_trough,
                                [(x, y + sz), (x - sz * 0.6, y - sz * 0.4), (x + sz * 0.6, y - sz * 0.4)])
            lbl = self.font.render(f"{pts[idx][1]:.3f}", True, (240, 240, 240))
            rect = lbl.get_rect()
            fx = int(x - rect.width / 2)
            fy = int(y + sz + 4)
            rect.move_ip(fx, fy)
            self._extrema_labels.append({"value": pts[idx][1], "x": fx, "y": fy, "rect": rect, "txt": lbl})

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
        bar_w = 24
        bar_gap = 45
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
        base_line_y = self.MARGIN_TOP + (new_max - 0.0) / draw_range * h if draw_range else self.MARGIN_TOP
        pygame.draw.line(self.surface, self.ZERO_COLOR, (self.MARGIN_LEFT, base_line_y),
                         (self.surface_size[0], base_line_y), width=1)
        for key in keys:
            ys = list(self.data[key])
            xs = list(self.x_data[key])
            if not ys or not xs: continue
            col = self._get_color(key)
            pts = [(self.MARGIN_LEFT + (xs[i] - x_min) / x_range * w,
                    self.MARGIN_TOP + (draw_max - ys[i]) / draw_range * h) for i in range(len(ys))]
            if len(pts) > 1:
                pygame.draw.aalines(self.surface, col, False, pts)
            if pts:
                pygame.draw.circle(self.surface, col, (int(pts[-1][0]), int(pts[-1][1])), 3)
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
        self._render_extrema_labels()

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
                    y0 + (draw_max - ys[j]) / draw_range * scale_h) for j in range(len(ys))]
            if len(pts) > 1:
                pygame.draw.aalines(self.surface, col, False, pts)
            if pts:
                pygame.draw.circle(self.surface, col, (int(pts[-1][0]), int(pts[-1][1])), 3)
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
                base_line_y = y0 + (draw_max - 0.0) / (draw_max - draw_min or 1) * scale_h
                self._render_zero_crossings(ys_centered, xs, x_min, x_max, base_line_y)
                self._render_decay_envelope(pts, ys_centered, xs, stats["decay_rate"], stats["mean_amplitude"])
                self._render_spectrum(stats, int(y0 + bar_h - 25))
            self._draw_label_split(key, ys, col, y0)
        for i in range(len(keys) + 1):
            y = self.MARGIN_TOP + i * bar_h
            pygame.draw.line(self.surface, self.DIVIDER_COLOR, (0, y), (self.surface_size[0], y), width=2)
        self._render_extrema_labels()

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
            t = (max_y - y_val) / y_range
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
        mx, my = pos[0], pos[1]
        w = self.surface_size[0] - self.MARGIN_LEFT
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        if mx < self.MARGIN_LEFT or mx >= self.surface_size[0] or my < self.MARGIN_TOP or my >= self.surface_size[1] - self.MARGIN_BOTTOM:
            self._hovered_key = None
            return

    def _point_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.hypot(p1[0] - p2[0] - 17, p1[1] - p2[1] -50)

    def _render_hover_tooltip(self):
        if not self._hovered_key or not self._hovered_info or not self._mouse_pos: return
        mx, my = self._mouse_pos
        info = self._hovered_info
        ls = [
            f"x={info['x']:.6g}",
            f"y={info['value']:.6g}",
            f"dx={info['dx']:.6g}, dy={info['dy']:.6g}",
            f"slope={info['slope']:.6g}",
            f"second={info['second']:.6g}",
            f"curv={info['curv']:.6g}",
            f"convex={info['convex']}",
            f"dθ={info['dtheta']:.6g}",
            f"window: mean={info['mean']:.6g}, std={info['std']:.6g}",
            f"min={info['win_min']:.6g}, max={info['win_max']:.6g}, median={info['median']:.6g}",
        ]
        if info.get("osc_stats"):
            o = info["osc_stats"]
            ls.extend([
                f"T: {o['period']:.3f}",
                f"A: {o['mean_amplitude']:.3f}",
                f"γ: {o['decay_rate']:.4f}",
                f"ζ: {o['damping_ratio']:.3f}"
            ])
        ls = ls[:self.MAX_HOVER_LINES]
        rend = [self.font.render(t, True, (255, 255, 255)) for t in ls]
        w = max(r.get_width() for r in rend) + 14
        h = len(rend) * self.LABEL_LINE_SPACING + 10
        x = mx + 18
        y = my + 18
        if x + w > self.surface_size[0] - 10: x = mx - w - 18
        if y + h > self.surface_size[1] - 10: y = my - h - 18
        pygame.draw.rect(self.surface, (25, 25, 35, 220), (x, y, w, h), border_radius=6)
        pygame.draw.rect(self.surface, (180, 180, 255), (x, y, w, h), 1, border_radius=6)
        off = 5
        for r in rend:
            self.surface.blit(r, (x + 7, y + off))
            off += self.LABEL_LINE_SPACING

    def _draw_tangent_and_area_overlay(self, key: str, xs: List[float], ys: List[float],
                                       x_min: float, x_max: float, draw_min: float, draw_max: float,
                                       px: float, py: float, idxf: float, slope: float, intercept: float,
                                       area: float) -> None:
        w = self.surface_size[0] - self.MARGIN_LEFT
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        x_range = x_max - x_min or 1.0
        draw_range = draw_max - draw_min or 1.0
        x0 = xs[int(math.floor(idxf))] + (
                    xs[min(len(xs) - 1, int(math.floor(idxf)) + 1)] - xs[int(math.floor(idxf))]) * (
                         idxf - math.floor(idxf)) if len(xs) > 1 else xs[0]
        y0 = ys[int(math.floor(idxf))] + (
                    ys[min(len(ys) - 1, int(math.floor(idxf)) + 1)] - ys[int(math.floor(idxf))]) * (
                         idxf - math.floor(idxf)) if len(xs) > 1 else ys[0]
        intercept_data = y0 - slope * x0
        sx = self.MARGIN_LEFT
        ex = self.MARGIN_LEFT + w
        data_x_s = x_min
        data_x_e = x_max
        y_s_data = slope * data_x_s + intercept_data
        y_e_data = slope * data_x_e + intercept_data
        y_s_screen = self.MARGIN_TOP + (draw_max - y_s_data) / draw_range * h
        y_e_screen = self.MARGIN_TOP + (draw_max - y_e_data) / draw_range * h
        col = self._get_color(key)
        pygame.draw.line(self.surface, (*col, 220), (sx, y_s_screen), (ex, y_e_screen), 2)
        screen_slope = -slope * (h / draw_range) / (w / x_range)
        angle = math.atan(screen_slope)
        arr_len = 18
        ax = px + math.cos(angle) * arr_len
        ay = py + math.sin(angle) * arr_len
        pygame.draw.line(self.surface, col, (px, py), (ax, ay), 2)
        pygame.draw.circle(self.surface, (*col, 230), (int(px), int(py)), 4)
        half_win = 10
        xL = x0 - (xs[1] - xs[0]) * half_win if len(xs) > 1 else x0 - half_win
        xR = x0 + (xs[1] - xs[0]) * half_win if len(xs) > 1 else x0 + half_win
        seg = self._sample_segment(xs, ys, xL, xR)
        if seg:
            surf = pygame.Surface(self.surface_size, pygame.SRCALPHA)
            poly = []
            for xd, yd in seg:
                sxp = self.MARGIN_LEFT + (xd - x_min) / x_range * w
                syp = self.MARGIN_TOP + (draw_max - yd) / draw_range * h
                poly.append((sxp, syp))
            bottom = self.surface_size[1] - self.MARGIN_BOTTOM
            if poly:
                poly_full = poly + [(poly[-1][0], bottom), (poly[0][0], bottom)]
                pygame.draw.polygon(surf, (*col, 60), poly_full)
                pygame.draw.lines(surf, (*col, 120), False, poly, 2)
            self.surface.blit(surf, (0, 0))

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

    def _sample_segment(self, xs: List[float], ys: List[float], xL: float, xR: float) -> List[Tuple[float, float]]:
        if not xs or xR <= xs[0] or xL >= xs[-1]: return []
        xL = max(xL, xs[0])
        xR = min(xR, xs[-1])
        n = len(xs)
        seg_x, seg_y = [], []
        i = 0
        while i + 1 < n and xs[i + 1] < xL: i += 1
        if i + 1 < n:
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[i], ys[i + 1]
            t = (xL - x0) / (x1 - x0) if x1 != x0 else 0.0
            seg_x.append(xL)
            seg_y.append(y0 + (y1 - y0) * t)
        else:
            seg_x.append(xs[-1])
            seg_y.append(ys[-1])
        j = i + 1
        while j < n and xs[j] <= xR:
            seg_x.append(xs[j])
            seg_y.append(ys[j])
            j += 1
        if seg_x and seg_x[-1] < xR and j < n:
            x0, x1 = xs[j - 1], xs[j]
            y0, y1 = ys[j - 1], ys[j]
            t = (xR - x0) / (x1 - x0) if x1 != x0 else 0.0
            seg_x.append(xR)
            seg_y.append(y0 + (y1 - y0) * t)
        return list(zip(seg_x, seg_y))

    def _handle_hover_overlay(self, keys: List[str]) -> None:
        if not self._mouse_pos or not self.enable_osc_analysis:
            self._hovered_key = None
            self._hovered_info = None
            return
        mx, my = self._mouse_pos
        w = self.surface_size[0] - self.MARGIN_LEFT
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        if mx < self.MARGIN_LEFT or mx >= self.surface_size[0] or my < self.MARGIN_TOP or my >= self.surface_size[
            1] - self.MARGIN_BOTTOM:
            self._hovered_key = None
            return
        all_vals = [v for k in keys for v in self.data[k]]
        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_vals or not all_x or len(all_vals) < 16: return
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
            if len(ys) < 16 or len(xs) < 16: continue
            pts = [(self.MARGIN_LEFT + (xs[i] - x_min) / x_range * w,
                    self.MARGIN_TOP + (ys[i] - draw_min) / draw_range * h) for i in range(len(ys))]
            for i, (px, py) in enumerate(pts):
                dist = math.hypot(mx - px, my - py)
                if dist < 12 and dist < best_dist:
                    best_dist = dist
                    best_key = key
                    best_x = xs[i]
                    best_y = ys[i]
                    best_idx = i
                    info = self._compute_local_stats(xs, ys, i)
                    osc = self._get_cached_osc_stats(key) if self.enable_osc_analysis else {}
                    info["osc_stats"] = osc if osc.get("valid") else None
                    info["value"] = ys[i]
                    info["x"] = xs[i]
                    info["index"] = i
                    best_info = info
        self._hovered_key = best_key
        self._hovered_info = best_info
        self._hovered_x = best_x
        self._hovered_y = best_y
        self._hovered_idx = best_idx
        self._hovered_area = 0.0
        if best_key and best_idx is not None:
            col = self._get_color(best_key)
            xs = list(self.x_data[best_key])
            ys = list(self.data[best_key])
            if len(xs) < 2 or len(ys) < 2: return
            x = xs[best_idx]
            y = ys[best_idx]
            xx = self.MARGIN_LEFT + (x - x_min) / x_range * w
            yy = self.MARGIN_TOP + (draw_max - y) / draw_range * h
            for r, a in [(16, 40), (10, 80), (6, 160)]:
                pygame.draw.circle(self.surface, (*col, a), (xx, yy), r)
            local = self._compute_local_stats(xs, ys, best_idx)
            slope_data = local.get("slope", 0.0)
            x0 = xs[best_idx]
            y0 = ys[best_idx]
            intercept = y0 - slope_data * x0
            half_win = 5
            dx = (xs[1] - xs[0]) if len(xs) > 1 else 1.0
            xL = x0 - dx * half_win
            xR = x0 + dx * half_win
            seg = self._sample_segment(xs, ys, xL, xR)
            area = 0.0
            if seg and len(seg) > 1:
                sxs = [p[0] for p in seg]
                sys = [p[1] for p in seg]
                area = self._compute_integral(sxs, sys, 0, len(sxs) - 1)
            self._hovered_area = area
            self._draw_tangent_and_area_overlay(best_key, xs, ys, x_min, x_max, draw_min, draw_max,
                                                xx, yy, float(best_idx), slope_data, intercept, area)

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
                    y0 + (draw_max - ys[j]) / draw_range * scale_h) for j in range(len(ys))]
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