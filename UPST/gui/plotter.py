import collections
import pygame

class Plotter:
    def __init__(self, surface_size, max_samples=120, smoothing_factor=0.15, font_size=16, sort_by_value=True):
        self.surface_size = surface_size
        self.max_samples = int(max_samples) if max_samples else 120
        self.smoothing_factor = smoothing_factor
        self.sort_by_value = sort_by_value
        self.data = collections.defaultdict(lambda: collections.deque(maxlen=self.max_samples))
        self.colors = {}
        self.hidden_keys = set()
        self.overlay_mode = True
        self.font = pygame.font.SysFont("Consolas", font_size)
        self._smoothed_max = {}
        self.surface = pygame.Surface(surface_size, pygame.SRCALPHA)

        self.groups = {}  # key -> group_name
        self.group_visibility = {}  # group_name -> visible
        self.current_group_filter = "All"
        self.available_groups = set()

    def _get_color(self, key):
        if key not in self.colors:
            base_colors = [
                (0, 255, 255), (255, 105, 180), (147, 255, 180),
                (255, 215, 0), (130, 130, 255), (255, 165, 0),
                (255, 99, 71), (128, 0, 128), (255, 192, 203),
                (144, 238, 144), (255, 160, 122), (173, 216, 230)
            ]
            self.colors[key] = base_colors[len(self.colors) % len(base_colors)]
        return self.colors[key]

    def add_data(self, key, value, group=None):
        self.data[key].append(value)
        if group is None:
            group = "ungrouped"
        self.groups[key] = group
        self.available_groups.add(group)
        if group not in self.group_visibility:
            self.group_visibility[group] = True

    def set_overlay_mode(self, mode):
        self.overlay_mode = mode

    def set_sort_by_value(self, sort_by_value):
        self.sort_by_value = sort_by_value

    def clear_data(self):
        self.data.clear()
        self.groups.clear()
        self.available_groups.clear()
        self.group_visibility.clear()

    def hide_key(self, key):
        self.hidden_keys.add(key)

    def show_key(self, key):
        self.hidden_keys.discard(key)

    def set_group_filter(self, group_name):
        """Установить фильтр по группе"""
        self.current_group_filter = group_name

    def get_available_groups(self):
        """Получить список всех доступных групп"""
        groups = list(self.available_groups)
        if groups:
            return ["All"] + sorted(groups)
        return ["All"]

    def set_group_visibility(self, group_name, visible):
        """Установить видимость группы"""
        self.group_visibility[group_name] = visible

    def is_group_visible(self, group_name):
        """Проверить видимость группы"""
        return self.group_visibility.get(group_name, True)

    def _get_filtered_keys(self):
        """Получить отфильтрованные ключи на основе текущего фильтра группы"""
        all_keys = [k for k in self.data.keys() if k not in self.hidden_keys]

        if self.current_group_filter == "All":
            filtered_keys = []
            for key in all_keys:
                group = self.groups.get(key, "ungrouped")
                if self.is_group_visible(group):
                    filtered_keys.append(key)
            return filtered_keys
        else:
            return [k for k in all_keys if self.groups.get(k, "ungrouped") == self.current_group_filter]

    def get_surface(self):
        self.surface.fill((0, 0, 0, 255))
        keys = self._get_filtered_keys()

        if not keys:
            no_data_text = self.font.render("No data to display", True, (128, 128, 128))
            text_rect = no_data_text.get_rect(center=(self.surface_size[0] // 2, self.surface_size[1] // 2))
            self.surface.blit(no_data_text, text_rect)
            return self.surface

        if self.sort_by_value:
            keys.sort(key=lambda k: self.data[k][-1] if self.data[k] else 0, reverse=True)
        else:
            keys.sort()

        x_step = self.surface_size[0] / self.max_samples
        total_height = self.surface_size[1] - 40

        if not self.overlay_mode:
            bar_height = total_height // len(keys) if len(keys) > 0 else 0
            for idx, key in enumerate(keys):
                values = self.data[key]
                if not values:
                    continue
                color = self._get_color(key)
                y_base = 20 + idx * bar_height
                current_max = max(values)
                if key not in self._smoothed_max:
                    self._smoothed_max[key] = current_max
                self._smoothed_max[key] += (current_max - self._smoothed_max[key]) * self.smoothing_factor
                y_scale = bar_height * 0.8
                points = [(i * x_step, y_base + bar_height - ((val / self._smoothed_max[key]) * y_scale)) for i, val in
                          enumerate(values)]
                if len(points) > 1:
                    pygame.draw.lines(self.surface, color, False, points)
                    shaded_points = [(0, y_base + bar_height)] + points + [(points[-1][0], y_base + bar_height)]
                    pygame.draw.polygon(self.surface, (*color, 100), shaded_points)

                current = values[-1]
                avg = sum(values) / len(values)
                group = self.groups.get(key, "ungrouped")
                label_text = f"{key} [{group}]: {current:.1f}ms Avg: {avg:.1f}ms"
                label = self.font.render(label_text, True, color, (40, 40, 40))
                label.set_colorkey((40, 40, 40))
                text_bg = pygame.Surface(label.get_size())
                text_bg.fill((40, 40, 40))
                text_bg.set_alpha(200)
                self.surface.blit(text_bg, (10, y_base + 5))
                self.surface.blit(label, (10, y_base + 5))

            for idx in range(len(keys) + 1):
                y = 20 + idx * bar_height
                pygame.draw.line(self.surface, (160, 160, 170, 255), (0, y), (self.surface_size[0], y))
        else:
            current_max_y = max([max(vals) for vals in self.data.values() if vals and any(
                self.groups.get(k, "ungrouped") == self.current_group_filter or self.current_group_filter == "All" for k
                in self.data.keys())]) if any(self.data.values()) else 1
            if 'overall' not in self._smoothed_max:
                self._smoothed_max['overall'] = current_max_y
            self._smoothed_max['overall'] += (current_max_y - self._smoothed_max['overall']) * self.smoothing_factor
            y_scale = total_height

            for key in keys:
                values = self.data[key]
                if not values:
                    continue
                color = self._get_color(key)
                points = [(i * x_step, self.surface_size[1] - 20 - (val / self._smoothed_max['overall']) * y_scale) for
                          i, val in enumerate(values)]
                if len(points) > 1:
                    pygame.draw.lines(self.surface, color, False, points)
                    shaded = points + [(points[-1][0], self.surface_size[1] - 20), (0, self.surface_size[1] - 20)]
                    pygame.draw.polygon(self.surface, (*color, 255), shaded, width=2)

            for idx, key in enumerate(keys):
                color = self._get_color(key)
                values = self.data[key]
                current = values[-1]
                avg = sum(values) / len(values)
                group = self.groups.get(key, "ungrouped")
                label_text = f"{key} [{group}]: {current:.2f}ms Avg: {avg:.2f}ms"
                label = self.font.render(label_text, True, color, (40, 40, 40))
                label.set_colorkey((40, 40, 40))
                text_bg = pygame.Surface(label.get_size())
                text_bg.fill((40, 40, 40))
                text_bg.set_alpha(200)
                self.surface.blit(text_bg, (10, 5 + idx * 18))
                self.surface.blit(label, (10, 5 + idx * 18))

            self._draw_grid(self._smoothed_max['overall'])
        filter_text = f"Filter: {self.current_group_filter}"
        filter_label = self.font.render(filter_text, True, (200, 200, 200))
        self.surface.blit(filter_label, (self.surface_size[0] - 150, 5))

        return self.surface

    def _draw_grid(self, max_y):
        grid_color = (60, 60, 70, 190)
        lines_count = 8
        step_y = max_y / lines_count if max_y > 0 else 1
        y_scale = self.surface_size[1] - 40
        for i in range(lines_count + 1):
            value = max_y - i * step_y
            y = (i / lines_count) * y_scale + 20
            pygame.draw.line(self.surface, grid_color, (0, y), (self.surface_size[0], y))
            ms_label = f"{value:.1f}ms"
            label_surface = self.font.render(ms_label, True, (180, 180, 180))
            self.surface.blit(label_surface, (self.surface_size[0] - 60, y - 10))