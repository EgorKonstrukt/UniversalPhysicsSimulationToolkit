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
    LABEL_Y_OFFSET: int = 5
    LABEL_LINE_SPACING: int = 18
    FILTER_LABEL_X_OFFSET: int = 150
    GRID_LABEL_X_OFFSET: int = 60
    GRID_STEPS: int = 8

    def __init__(self, surface_size: Tuple[int, int], max_samples: int = 120,
                 smoothing_factor: float = 0.15, font_size: int = 16, sort_by_value: bool = True):
        self.surface_size = surface_size
        self.max_samples = max(1, int(max_samples))
        self.smoothing_factor = smoothing_factor
        self.sort_by_value = sort_by_value
        self.data: Dict[str, collections.deque] = collections.defaultdict(
            lambda: collections.deque(maxlen=self.max_samples))
        self.colors: Dict[str, Tuple[int, int, int]] = {}
        self.hidden_keys: set = set()
        self.overlay_mode: bool = True
        self.font = pygame.font.SysFont(self.FONT_NAME, font_size)
        self._smoothed_max: Dict[str, float] = {}
        self.surface = pygame.Surface(surface_size, pygame.SRCALPHA)
        self.groups: Dict[str, str] = {}
        self.group_visibility: Dict[str, bool] = {}
        self.current_group_filter: str = "All"
        self.available_groups: set = {"ungrouped"}

    def _get_color(self, key: str) -> Tuple[int, int, int]:
        if key not in self.colors:
            self.colors[key] = self.BASE_COLORS[len(self.colors) % len(self.BASE_COLORS)]
        return self.colors[key]

    def add_data(self, key: str, value: float, group: Optional[str] = None) -> None:
        self.data[key].append(value)
        group = group or "ungrouped"
        self.groups[key] = group
        self.available_groups.add(group)
        self.group_visibility.setdefault(group, True)

    def set_overlay_mode(self, mode: bool) -> None: self.overlay_mode = mode
    def set_sort_by_value(self, sort_by_value: bool) -> None: self.sort_by_value = sort_by_value
    def clear_data(self) -> None:
        self.data.clear(); self.groups.clear(); self.available_groups = {"ungrouped"}; self.group_visibility.clear()
    def hide_key(self, key: str) -> None: self.hidden_keys.add(key)
    def show_key(self, key: str) -> None: self.hidden_keys.discard(key)
    def clear_key(self, key: str) -> None: self.data.pop(key, None)
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
        cur_max = max(all_vals) if all_vals else 1.0
        smoothed_key = 'overlay'
        self._smoothed_max.setdefault(smoothed_key, cur_max)
        self._smoothed_max[smoothed_key] += (cur_max - self._smoothed_max[smoothed_key]) * self.smoothing_factor
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        x_step = self.surface_size[0] / self.max_samples
        for key in keys:
            vals = self.data[key]
            if not vals: continue
            col = self._get_color(key)
            pts = [(j * x_step, self.surface_size[1] - self.MARGIN_BOTTOM - (v / self._smoothed_max[smoothed_key]) * h)
                   for j, v in enumerate(vals)]
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts)
                poly = pts + [(pts[-1][0], self.surface_size[1] - self.MARGIN_BOTTOM), (0, self.surface_size[1] - self.MARGIN_BOTTOM)]
                pygame.draw.polygon(self.surface, (*col, 255), poly, width=2)
        self._draw_labels_overlay(keys)
        self._draw_grid(self._smoothed_max[smoothed_key])

    def _draw_labels_overlay(self, keys: List[str]) -> None:
        for i, key in enumerate(keys):
            vals = self.data[key]
            avg = sum(vals) / len(vals)
            txt = f"{key} [{self.groups.get(key, 'ungrouped')}]: {vals[-1]:.2f} Avg: {avg:.2f}"
            lbl = self.font.render(txt, True, self._get_color(key))
            bg = pygame.Surface(lbl.get_size())
            bg.fill(self.LABEL_BG_COLOR); bg.set_alpha(200)
            y_pos = self.LABEL_Y_OFFSET + i * self.LABEL_LINE_SPACING
            self.surface.blit(bg, (10, y_pos))
            self.surface.blit(lbl, (10, y_pos))

    def _render_split_mode(self, keys: List[str]) -> None:
        x_step = self.surface_size[0] / self.max_samples
        total_h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        bar_h = total_h / len(keys) if keys else 0
        for i, key in enumerate(keys):
            vals = self.data[key]
            if not vals: continue
            col = self._get_color(key)
            y0 = self.MARGIN_TOP + i * bar_h
            cur_max = max(vals)
            sm_key = f"bar_{key}"
            self._smoothed_max.setdefault(sm_key, cur_max)
            self._smoothed_max[sm_key] += (cur_max - self._smoothed_max[sm_key]) * self.smoothing_factor
            scale = bar_h * 0.8
            pts = [(j * x_step, y0 + bar_h - (v / self._smoothed_max[sm_key]) * scale) for j, v in enumerate(vals)]
            if len(pts) > 1:
                pygame.draw.lines(self.surface, col, False, pts)
                poly = [(0, y0 + bar_h)] + pts + [(pts[-1][0], y0 + bar_h)]
                pygame.draw.polygon(self.surface, (*col, 100), poly)
            self._draw_label_split(key, vals, col, y0)
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

    def _draw_grid(self, max_y: float) -> None:
        step_val = max_y / self.GRID_STEPS if max_y > 0 else 1
        h = self.surface_size[1] - self.MARGIN_TOP - self.MARGIN_BOTTOM
        for i in range(self.GRID_STEPS + 1):
            val = max_y - i * step_val
            y = self.MARGIN_TOP + (i / self.GRID_STEPS) * h
            pygame.draw.line(self.surface, self.GRID_COLOR, (0, y), (self.surface_size[0], y))
            lbl = self.font.render(f"{val:.1f}", True, self.TEXT_COLOR)
            self.surface.blit(lbl, (self.surface_size[0] - self.GRID_LABEL_X_OFFSET, y - 10))

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
        return self.surface
