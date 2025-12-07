import collections
from typing import Dict, List, Optional, Tuple
import pygame

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
    MARGIN_BOTTOM: int = 20
    MARGIN_LEFT: int = 60
    LABEL_Y_OFFSET: int = 5
    LABEL_LINE_SPACING: int = 18
    FILTER_LABEL_X_OFFSET: int = 150
    GRID_LABEL_X_OFFSET: int = 60
    GRID_STEPS: int = 8
    AXIS_COLOR: Tuple[int, int, int] = (200, 200, 200)

    def __init__(self, surface_size: Tuple[int, int], max_samples: int = 120,
                 smoothing_factor: float = 0.15, font_size: int = 16, sort_by_value: bool = True,
                 zero_centered: bool = False, x_label: str = "", y_label: str = ""):
        self.surface_size = surface_size
        self.max_samples = max(1, int(max_samples))
        self.smoothing_factor = smoothing_factor
        self.sort_by_value = sort_by_value
        self.zero_centered = zero_centered
        self.x_label = x_label
        self.y_label = y_label
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

    def _get_color(self, key: str) -> Tuple[int, int, int]:
        if key not in self.colors:
            self.colors[key] = self.BASE_COLORS[len(self.colors) % len(self.BASE_COLORS)]
        return self.colors[key]

    def add_data(self, key: str, y: float, x: Optional[float] = None, group: Optional[str] = None) -> None:
        self.data[key].append(y)
        self.x_data[key].append(x if x is not None else len(self.data[key]))
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

    def _render_overlay_mode(self, keys: List[str]) -> None:
        all_vals = [v for k in keys for v in self.data[k]]
        if not all_vals:
            self._render_no_data()
            return
        global_min = min(all_vals)
        global_max = max(all_vals)
        if self.zero_centered:
            abs_max = max(abs(global_min), abs(global_max))
            y_min, y_max = -abs_max, abs_max
        else:
            y_min, y_max = global_min, global_max
        y_range = y_max - y_min or 1.0
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        w = self.surface_size[0] - self.MARGIN_LEFT
        smoothed_key = 'overlay'
        self._smoothed_range.setdefault(smoothed_key, (y_min, y_max))
        old_min, old_max = self._smoothed_range[smoothed_key]
        new_min = old_min + (y_min - old_min) * self.smoothing_factor
        new_max = old_max + (y_max - old_max) * self.smoothing_factor
        self._smoothed_range[smoothed_key] = (new_min, new_max)
        draw_min, draw_max = new_min, new_max
        draw_range = draw_max - draw_min or 1.0

        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_x:
            x_min, x_max = 0, 1
        else:
            x_min, x_max = min(all_x), max(all_x)
        x_range = x_max - x_min or 1.0

        for key in keys:
            ys = self.data[key]
            xs = self.x_data[key]
            if not ys or not xs: continue
            col = self._get_color(key)
            pts = []
            for i in range(len(ys)):
                x_norm = (xs[i] - x_min) / x_range
                y_norm = (ys[i] - draw_min) / draw_range
                x_screen = self.MARGIN_LEFT + x_norm * w
                y_screen = self.surface_size[1] - self.MARGIN_BOTTOM - y_norm * h
                pts.append((x_screen, y_screen))
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts)
        self._draw_labels_overlay(keys)
        self._draw_grid_range(draw_min, draw_max)
        self._draw_x_axis_labels(x_min, x_max)

    def _draw_x_axis_labels(self, x_min: float, x_max: float) -> None:
        w = self.surface_size[0] - self.MARGIN_LEFT
        x_range = x_max - x_min or 1.0
        for i in range(self.GRID_STEPS + 1):
            t = i / self.GRID_STEPS
            val = x_min + t * x_range
            x = self.MARGIN_LEFT + t * w
            pygame.draw.line(self.surface, self.GRID_COLOR, (x, 0), (x, self.surface_size[1]))
            lbl = self.font.render(f"{val:.1f}", True, self.TEXT_COLOR)
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
        for i in range(self.GRID_STEPS + 1):
            t = i / self.GRID_STEPS
            val = min_y + t * y_range
            y = self.surface_size[1] - self.MARGIN_BOTTOM - t * h
            pygame.draw.line(self.surface, self.GRID_COLOR, (self.MARGIN_LEFT, y), (self.surface_size[0], y))
            lbl = self.font.render(f"{val:.1f}", True, self.TEXT_COLOR)
            self.surface.blit(lbl, (self.surface_size[0] - self.GRID_LABEL_X_OFFSET, y - 10))

    def _render_split_mode(self, keys: List[str]) -> None:
        w = self.surface_size[0] - self.MARGIN_LEFT
        total_h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        bar_h = total_h / len(keys) if keys else 0
        all_x = [x for k in keys for x in self.x_data[k]]
        if not all_x:
            x_min, x_max = 0, 1
        else:
            x_min, x_max = min(all_x), max(all_x)
        x_range = x_max - x_min or 1.0

        for i, key in enumerate(keys):
            ys = self.data[key]
            xs = self.x_data[key]
            if not ys or not xs: continue
            col = self._get_color(key)
            y0 = self.MARGIN_TOP + i * bar_h
            local_min = min(ys)
            local_max = max(ys)
            if self.zero_centered:
                abs_max = max(abs(local_min), abs(local_max))
                y_min, y_max = -abs_max, abs_max
            else:
                y_min, y_max = local_min, local_max
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
            pts = []
            for j in range(len(ys)):
                x_norm = (xs[j] - x_min) / x_range
                y_norm = (ys[j] - draw_min) / draw_range
                x_screen = self.MARGIN_LEFT + x_norm * w
                y_screen = y0 + bar_h - y_norm * scale_h
                pts.append((x_screen, y_screen))
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts)
            self._draw_label_split(key, ys, col, y0)
        for i in range(len(keys) + 1):
            y = self.MARGIN_TOP + i * bar_h
            pygame.draw.line(self.surface, self.DIVIDER_COLOR, (0, y), (self.surface_size[0], y))
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