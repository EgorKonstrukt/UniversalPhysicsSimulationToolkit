import collections
import math
from typing import Dict, List, Optional, Tuple
import pygame
import time



class Plotter:
    BASE_COLORS: List[Tuple[int, int, int]] = [
        (0, 255, 255), (255, 105, 180), (147, 255, 180), (255, 215, 0),
        (130, 130, 255), (255, 165, 0), (255, 99, 71), (128, 0, 128),
        (255, 192, 203), (144, 238, 144), (255, 160, 122), (173, 216, 230)
    ]
    FONT_NAME: str = "Consolas"
    BG_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 255)
    LABEL_BG_COLOR: Tuple[int, int, int] = (40, 40, 40)
    GRID_COLOR: Tuple[int, int, int, int] = (60, 60, 70, 190)
    DIVIDER_COLOR: Tuple[int, int, int] = (160, 160, 170)
    TEXT_COLOR: Tuple[int, int, int] = (180, 180, 180)
    NO_DATA_COLOR: Tuple[int, int, int] = (128, 128, 128)
    FILTER_LABEL_COLOR: Tuple[int, int, int] = (200, 200, 200)
    MARGIN_TOP: int = 20
    MARGIN_BOTTOM: int = 30
    MARGIN_LEFT: int = 60
    LABEL_Y_OFFSET: int = 5
    LABEL_LINE_SPACING: int = 18
    FILTER_LABEL_X_OFFSET: int = 150
    GRID_LABEL_X_OFFSET: int = 60
    AXIS_COLOR: Tuple[int, int, int] = (200, 200, 200)
    BASE_GRID_PIXEL_STEP: int = 50
    PADDING_RATIO: float = 0.1

    def __init__(self, surface_size: Tuple[int, int], max_samples: int = 120,
                 smoothing_factor: float = 0.15, font_size: int = 16, sort_by_value: bool = True,
                 x_label: str = "", y_label: str = "", grid_density: float = 1.0):
        self.surface_size = surface_size
        self.max_samples = max(1, int(max_samples))
        self.smoothing_factor = smoothing_factor
        self.sort_by_value = sort_by_value
        self.x_label = x_label
        self.y_label = y_label
        self.grid_density = max(0.1, float(grid_density))
        self.data: Dict[str, collections.deque] = collections.defaultdict(
            lambda: collections.deque(maxlen=self.max_samples))
        self.x_data: Dict[str, collections.deque] = collections.defaultdict(
            lambda: collections.deque(maxlen=self.max_samples))
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

    @staticmethod
    def _nice_step(range_val: float, pixel_length: int, density: float = 1.0) -> float:
        if range_val <= 0:
            return 1.0

        target_steps = max(2, int(pixel_length / 50))
        step_approx = range_val / target_steps
        exponent = int(math.floor(math.log10(step_approx)))
        mantissa = step_approx / (10 ** exponent)
        if mantissa <= 0.5:
            nice_mantissa = 0.5
        elif mantissa <= 1:
            nice_mantissa = 1.0
        elif mantissa <= 2:
            nice_mantissa = 2.0
        elif mantissa <= 5:
            nice_mantissa = 5.0
        else:
            nice_mantissa = 10.0
        base_step = nice_mantissa * (10 ** exponent)
        return base_step / max(0.1, density)

    def _get_color(self, key: str) -> Tuple[int, int, int]:
        if key not in self.colors:
            self.colors[key] = self.BASE_COLORS[len(self.colors) % len(self.BASE_COLORS)]
        return self.colors[key]

    def add_data(self, key: str, y: float, x: Optional[float] = None, group: Optional[str] = None) -> None:
        self.data[key].append(y)
        if x is None:
            x = time.perf_counter() * 1000
        self.x_data[key].append(x)
        group = group or "ungrouped"
        self.groups[key] = group
        self.available_groups.add(group)
        self.group_visibility.setdefault(group, True)

    def set_overlay_mode(self, mode: bool) -> None: self.overlay_mode = mode
    def set_sort_by_value(self, sort_by_value: bool) -> None: self.sort_by_value = sort_by_value
    def clear_data(self) -> None:
        self.data.clear(); self.x_data.clear(); self.groups.clear(); self.available_groups = {"ungrouped"}; self.group_visibility.clear()
    def hide_key(self, key: str) -> None: self.hidden_keys.add(key)
    def show_key(self, key: str) -> None: self.hidden_keys.discard(key)
    def clear_key(self, key: str) -> None:
        self.data.pop(key, None); self.x_data.pop(key, None)
    def set_group_filter(self, group_name: str) -> None: self.current_group_filter = group_name
    def get_available_groups(self) -> List[str]:
        return ["All"] + sorted(self.available_groups - {"ungrouped"}) if len(self.available_groups) > 1 else ["All"]
    def set_group_visibility(self, group_name: str, visible: bool) -> None: self.group_visibility[group_name] = visible
    def is_group_visible(self, group_name: str) -> bool: return self.group_visibility.get(group_name, True)

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
            dy_prev, dy_next = ys[i] - ys[i-1], ys[i] - ys[i+1]
            if dy_prev > 1e-9 and dy_next > 1e-9:
                prominence = min(dy_prev, dy_next)
                peaks.append((i, prominence))
            elif dy_prev < -1e-9 and dy_next < -1e-9:
                prominence = min(-dy_prev, -dy_next)
                troughs.append((i, prominence))
        return peaks, troughs

    def _render_extrema_markers(self, pts: List[Tuple[float, float]], peaks: List[Tuple[int, float]],
                                troughs: List[Tuple[int, float]]) -> None:
        peak_tri, trough_tri = [], []
        peak_labels, trough_labels = [], []

        for idx, prom in peaks:
            x, y = pts[idx]
            size = max(4, min(10, int(5 + prom * 25)))
            v_y = self.data[[k for k in self.data.keys() if k in self._get_filtered_keys()][0]][
                idx]
            peak_tri.append((x, y, size))
            peak_labels.append((x, y - size - 15, f"{v_y:.2f}"))

        for idx, prom in troughs:
            x, y = pts[idx]
            size = max(4, min(10, int(5 + prom * 25)))
            v_y = self.data[[k for k in self.data.keys() if k in self._get_filtered_keys()][0]][idx]
            trough_tri.append((x, y, size))
            trough_labels.append((x, y + size + 15, f"{v_y:.2f}"))

        for x, y, s in peak_tri:
            pygame.draw.polygon(self.surface, (255, 60, 60),
                                [(x, y - s), (x - s * 0.6, y + s * 0.4), (x + s * 0.6, y + s * 0.4)])
            pygame.draw.polygon(self.surface, (255, 180, 180),
                                [(x, y - s + 1), (x - s * 0.55, y + s * 0.35), (x + s * 0.55, y + s * 0.35)], 1)
        for x, y, txt in peak_labels:
            lbl = self.font.render(txt, True, (255, 220, 220))
            bg = pygame.Surface((lbl.get_width() + 4, lbl.get_height() + 2))
            bg.fill(self.LABEL_BG_COLOR);
            bg.set_alpha(180)
            self.surface.blit(bg, (x - bg.get_width() // 2, y - bg.get_height() // 2))
            self.surface.blit(lbl, (x - lbl.get_width() // 2, y - lbl.get_height() // 2))

        for x, y, s in trough_tri:
            pygame.draw.polygon(self.surface, (60, 255, 60),
                                [(x, y + s), (x - s * 0.6, y - s * 0.4), (x + s * 0.6, y - s * 0.4)])
            pygame.draw.polygon(self.surface, (180, 255, 180),
                                [(x, y + s - 1), (x - s * 0.55, y - s * 0.35), (x + s * 0.55, y - s * 0.35)], 1)
        for x, y, txt in trough_labels:
            lbl = self.font.render(txt, True, (220, 255, 220))
            bg = pygame.Surface((lbl.get_width() + 4, lbl.get_height() + 2))
            bg.fill(self.LABEL_BG_COLOR);
            bg.set_alpha(180)
            self.surface.blit(bg, (x - bg.get_width() // 2, y - bg.get_height() // 2))
            self.surface.blit(lbl, (x - lbl.get_width() // 2, y - lbl.get_height() // 2))


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

        if not all_x:
            x_min, x_max = 0.0, 1.0
        else:
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

        for key in keys:
            ys = list(self.data[key])
            xs = list(self.x_data[key])
            if not ys or not xs: continue
            col = self._get_color(key)
            pts = [(self.MARGIN_LEFT + (xs[i] - x_min) / x_range * w,
                    self.MARGIN_TOP + (ys[i] - draw_min) / draw_range * h) for i in range(len(ys))]
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts, width=2)
            pks, trs = self._find_extrema(ys)
            if pks or trs:
                prom_scale = 1.0 / (y_range or 1.0)
                pks_scaled = [(i, p * prom_scale) for i, p in pks]
                trs_scaled = [(i, t * prom_scale) for i, t in trs]
                self._render_extrema_markers(pts, pks_scaled, trs_scaled)
        self._draw_labels_overlay(keys)
        self._draw_grid_range(draw_min, draw_max)
        self._draw_x_axis_labels(x_min, x_max)

    def _render_split_mode(self, keys: List[str]) -> None:
        w = self.surface_size[0] - self.MARGIN_LEFT
        total_h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        bar_h = total_h / len(keys) if keys else 0
        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_x:
            x_min, x_max = 0.0, 1.0
        else:
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
            pks, trs = self._find_extrema(ys)
            if pks or trs:
                prom_scale = 1.0 / (y_range or 1.0)
                pks_scaled = [(i, p * prom_scale) for i, p in pks]
                trs_scaled = [(i, t * prom_scale) for i, t in trs]
                self._render_extrema_markers(pts, pks_scaled, trs_scaled)
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
        for i, key in enumerate(keys):
            ys = self.data[key]
            avg = sum(ys) / len(ys)
            txt = f"{key} [{self.groups.get(key, 'ungrouped')}]: {ys[-1]:.2f} Avg: {avg:.2f}"
            lbl = self.font.render(txt, True, self._get_color(key))
            bg = pygame.Surface(lbl.get_size())
            bg.fill(self.LABEL_BG_COLOR); bg.set_alpha(200)
            y_pos = self.LABEL_Y_OFFSET + i * self.LABEL_LINE_SPACING
            self.surface.blit(bg, (10, y_pos))
            self.surface.blit(lbl, (10, y_pos))

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

    def get_surface(self) -> pygame.Surface:
        self.surface.fill(self.BG_COLOR)
        keys = self._get_filtered_keys()
        if not keys:
            self._render_no_data()
        elif self.overlay_mode:
            self._render_overlay_mode(keys)
        else:
            self._render_split_mode(keys)
        flt = self.font.render(f"Filter: {self.current_group_filter}", True, self.FILTER_LABEL_COLOR)
        self.surface.blit(flt, (self.surface_size[0] - self.FILTER_LABEL_X_OFFSET, 5))
        self._draw_axis_labels()
        return self.surface