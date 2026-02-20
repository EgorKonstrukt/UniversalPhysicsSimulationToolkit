import pygame
import time
import traceback
from typing import Dict, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque
import json
from UPST.config import config

import colorama

colorama.init()

_debug_instance = None


class LogLevel(int, Enum):
    DEBUG = 0
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


@dataclass
class LogEntry:
    timestamp: float
    level: LogLevel
    message: str
    category: str
    frame_count: int
    stack_trace: Optional[str] = None
    color: Optional[Tuple[int, int, int]] = None


class DebugManager:
    def __init__(self, max_log_entries=1000):
        self.enabled = True
        self.log_entries: deque = deque(maxlen=max_log_entries)
        self.categories: Dict[str, bool] = defaultdict(lambda: True)
        self.frame_count = 0
        self.start_time = time.time()
        self.show_console = True
        self.show_performance = True
        self.show_physics_debug = True
        self.show_camera_debug = True
        self.show_snapshots_debug = True
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.smoothed_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.performance_counters = defaultdict(float)
        self.stats = defaultdict(int)
        self.log_colors = {
            LogLevel.DEBUG: (200, 200, 200), LogLevel.INFO: (255, 55, 255),
            LogLevel.SUCCESS: (55, 255, 55), LogLevel.WARNING: (255, 255, 0),
            LogLevel.ERROR: (255, 100, 100), LogLevel.CRITICAL: (255, 0, 0)
        }
        self.font_small = pygame.font.SysFont("Consolas", 14)
        self.font_medium = pygame.font.SysFont("Consolas", 16)
        self.font_large = pygame.font.SysFont("Consolas", 20)
        self.console_height = 200
        self.console_alpha = 200
        self.max_console_lines = 50
        self.log_file = "debug_log.txt"
        self.auto_save_logs = True
        self._axis_limits = {'fps': [0.0, 144.0], 'frame_time': [0.0, 20.0]}
        self._axis_smooth_factor = 0.92
        self._data_smooth_factor = 0.25
        self._target_fps = 60.0
        self._target_frame_time = 16.67

        self._text_cache: Dict[str, Tuple[pygame.Surface, float]] = {}
        self._last_cache_clear = 0

        self.log(LogLevel.INFO, "Debug Manager initialized", "Debug")

    def update(self, delta_time: float):
        self.frame_count += 1
        fps = 1.0 / delta_time if delta_time > 0 else 0
        ft = delta_time * 1000
        self.performance_history['fps'].append(fps)
        self.performance_history['frame_time'].append(ft)

        now = time.time()
        if now - self._last_cache_clear > 1.0:
            self._text_cache.clear()
            self._last_cache_clear = now

        for key in ['fps', 'frame_time']:
            hist = self.performance_history[key]
            smooth = self.smoothed_history[key]
            if len(hist) == 0: return
            current_val = hist[-1]
            prev_smooth = smooth[-1] if len(smooth) > 0 else current_val
            weight = self._data_smooth_factor if abs(current_val - prev_smooth) < 10 else 0.6
            new_smooth = prev_smooth * (1 - weight) + current_val * weight
            smooth.append(new_smooth)

            limit_min = min(smooth)
            limit_max = max(smooth)
            margin = (limit_max - limit_min) * 0.15 if limit_max != limit_min else 10.0
            target_min = max(0, limit_min - margin)
            target_max = limit_max + margin
            if key == 'fps': target_max = max(target_max, self._target_fps * 1.2)
            if key == 'frame_time': target_max = max(target_max, self._target_frame_time * 1.5)

            curr_min, curr_max = self._axis_limits[key]
            self._axis_limits[key][0] = curr_min * self._axis_smooth_factor + target_min * (
                        1 - self._axis_smooth_factor)
            self._axis_limits[key][1] = curr_max * self._axis_smooth_factor + target_max * (
                        1 - self._axis_smooth_factor)

    def _get_text_surface(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int]):
        key = f"{text}_{color}"
        if key in self._text_cache:
            surf, created_at = self._text_cache[key]
            if time.time() - created_at < 0.5:
                return surf
        surf = font.render(text, True, color)
        self._text_cache[key] = (surf, time.time())
        return surf

    def log(self, level: LogLevel, message: str, category: str = "General",
            include_stack: bool = False, color_override: Optional[Tuple[int, int, int]] = None):
        if not self.enabled or not self.categories[category]: return
        stack_trace = None
        if include_stack or level >= LogLevel.ERROR:
            stack_trace = traceback.format_stack()
        reset = "\033[0m"
        if color_override is not None:
            r, g, b = color_override
            ansi_color = f"\033[38;2;{r};{g};{b}m"
        else:
            ansi_colors = {
                LogLevel.DEBUG: "\033[38;5;245m", LogLevel.INFO: "\033[38;5;207m",
                LogLevel.SUCCESS: "\033[38;5;46m", LogLevel.WARNING: "\033[38;5;226m",
                LogLevel.ERROR: "\033[38;5;203m", LogLevel.CRITICAL: "\033[38;5;196m"
            }
            ansi_color = ansi_colors.get(level, "")
        for line in message.split('\n'):
            display_color = color_override or self.log_colors.get(level, (255, 255, 255))
            entry = LogEntry(timestamp=time.time() - self.start_time, level=level, message=line,
                             category=category, frame_count=self.frame_count, stack_trace=stack_trace,
                             color=display_color)
            self.log_entries.append(entry)
            if self.auto_save_logs and level >= LogLevel.ERROR:
                self._save_log_entry(entry)
            print(f"{ansi_color}[{level.name}] {category}: {line}{reset}")

    def _save_log_entry(self, entry: LogEntry):
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp_str = time.strftime("%H:%M:%S", time.gmtime(entry.timestamp))
                f.write(f"[{timestamp_str}] [{entry.level.name}] {entry.category}: {entry.message}\n")
                if entry.stack_trace:
                    f.write("Stack trace:\n")
                    for line in entry.stack_trace: f.write(f"  {line}")
                    f.write("\n")
        except Exception as e:
            print(f"Failed to save log entry: {e}")

    def draw_console(self, screen: pygame.Surface):
        if not config.debug.show_console: return
        screen_width = screen.get_width()
        header_height = 20
        total_console_height = self.console_height + header_height
        console_rect = pygame.Rect(0, screen.get_height() - total_console_height, screen_width, total_console_height)

        console_surface = pygame.Surface((console_rect.width, console_rect.height), pygame.SRCALPHA)
        console_surface.fill((0, 0, 0, self.console_alpha))

        header_text = f"Debug Console (Frame: {self.frame_count}) - Press F1 to toggle"
        header_surface = self.font_large.render(header_text, True, (255, 255, 255))
        console_surface.blit(header_surface, (5, 0))

        y_offset = console_rect.height - 15
        lines_drawn = 0
        last_category = None
        for entry in reversed(list(self.log_entries)):
            if lines_drawn >= self.max_console_lines or y_offset <= header_height: break
            show_category = entry.category != last_category
            last_category = entry.category
            timestamp_str = f"{entry.timestamp:.2f}s"
            text = f"[{timestamp_str}] [{entry.category}] {entry.message}" if show_category else f"[{timestamp_str}]           {entry.message}"
            color = entry.color or self.log_colors.get(entry.level, (255, 255, 255))
            text_surface = self.font_small.render(text, True, color)
            console_surface.blit(text_surface, (5, y_offset))
            y_offset -= 12
            lines_drawn += 1
        screen.blit(console_surface, console_rect)

    def _draw_graph(self, screen: pygame.Surface, rect: pygame.Rect, data_key: str, color: Tuple[int, int, int],
                    label: str, ref_val: float = None):
        hist = list(self.smoothed_history[data_key])
        if len(hist) < 2: return

        min_y, max_y = self._axis_limits[data_key]
        range_y = max_y - min_y if max_y > min_y else 1.0

        w = rect.width
        h = rect.height
        step = max(1, len(hist) // w)
        pts = []
        for i in range(0, len(hist), step):
            v = hist[i]
            x = rect.left + int((i / (len(hist) - 1)) * w)
            norm_v = (v - min_y) / range_y
            y = rect.bottom - int(norm_v * h)
            pts.append((x, max(rect.top, min(rect.bottom, y))))

        if len(pts) > 1:
            pygame.draw.lines(screen, color, False, pts, 2)
            fill_pts = pts + [(pts[-1][0], rect.bottom), (pts[0][0], rect.bottom)]
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            if len(fill_pts) > 2:
                pygame.draw.polygon(s, (*color, 40), fill_pts)
                screen.blit(s, (rect.left, rect.top))

        if ref_val is not None:
            ry = rect.bottom - int((ref_val - min_y) / range_y * h)
            if rect.top <= ry <= rect.bottom:
                pygame.draw.line(screen, (200, 200, 200), (rect.left, ry), (rect.right, ry), 1)
                lbl_ref = self._get_text_surface(f"{ref_val:.1f}", self.font_small, (200, 200, 200))
                screen.blit(lbl_ref, (rect.right - lbl_ref.get_width() - 2, ry - lbl_ref.get_height()))

        for i in range(1, 4):
            gy = rect.bottom - int((min_y + range_y * i / 4 - min_y) / range_y * h)
            if rect.top <= gy <= rect.bottom:
                pygame.draw.line(screen, (40, 40, 40), (rect.left, gy), (rect.right, gy), 1)
                val = min_y + range_y * i / 4
                lbl_grid = self._get_text_surface(f"{val:.0f}", self.font_small, (100, 100, 100))
                screen.blit(lbl_grid, (rect.left + 2, gy - lbl_grid.get_height()))

        lbl = self._get_text_surface(label, self.font_medium, color)
        bg_lbl = pygame.Surface((lbl.get_width() + 4, lbl.get_height() + 2), pygame.SRCALPHA)
        bg_lbl.fill((0, 0, 0, 150))
        screen.blit(bg_lbl, (rect.right - lbl.get_width() - 6, rect.top + 2))
        screen.blit(lbl, (rect.right - lbl.get_width() - 4, rect.top + 3))

    def draw_performance_overlay(self, screen: pygame.Surface):
        if not config.debug.show_performance: return
        fps_hist = list(self.performance_history['fps'])
        ft_hist = list(self.performance_history['frame_time'])
        if not fps_hist: return

        cur_fps = fps_hist[-1]
        avg_fps = sum(fps_hist) / len(fps_hist)
        min_fps = min(fps_hist)
        max_fps = max(fps_hist)
        cur_ft = ft_hist[-1]
        avg_ft = sum(ft_hist) / len(ft_hist)

        ox, oy = 10, 10
        lh = 18
        w = 380
        stats_h = 110
        plot_h = 110
        gap = 15
        total_h = stats_h + plot_h * 2 + gap + 20

        bg = pygame.Surface((w, total_h), pygame.SRCALPHA)
        bg.fill((15, 15, 20, 210))
        pygame.draw.rect(bg, (60, 60, 70), bg.get_rect(), 1)
        screen.blit(bg, (ox, oy))

        c_fps = (100, 255, 100) if cur_fps > 55 else (255, 200, 0) if cur_fps > 30 else (255, 100, 100)

        left_col = [
            (f"FPS: {cur_fps:.1f}", c_fps),
            (f"Avg: {avg_fps:.1f}", (200, 200, 200)),
            (f"Min/Max: {min_fps:.0f}/{max_fps:.0f}", (200, 200, 200)),
            (f"Frame: {self.frame_count}", (255, 255, 255)),
        ]
        right_col = [
            (f"Time: {cur_ft:.2f}ms", (255, 150, 100)),
            (f"Avg: {avg_ft:.2f}ms", (200, 200, 200)),
            (f"Runtime: {time.time() - self.start_time:.1f}s", (255, 255, 255)),
        ]
        for k, v in self.performance_counters.items():
            right_col.append((f"{k}: {v:.2f}", (200, 200, 255)))

        start_y = oy + 8
        col_w = (w - 40) // 2

        for i, (t, c) in enumerate(left_col):
            txt = self._get_text_surface(t, self.font_small, c)
            screen.blit(txt, (ox + 10, start_y + i * lh))

        for i, (t, c) in enumerate(right_col):
            txt = self._get_text_surface(t, self.font_small, c)
            screen.blit(txt, (ox + 10 + col_w + 10, start_y + i * lh))

        py1 = oy + stats_h + 10
        py2 = py1 + plot_h + gap
        pw = w - 20
        pr1 = pygame.Rect(ox + 10, py1, pw, plot_h)
        pr2 = pygame.Rect(ox + 10, py2, pw, plot_h)

        pygame.draw.rect(screen, (50, 50, 60), pr1, 1)
        pygame.draw.rect(screen, (50, 50, 60), pr2, 1)

        self._draw_graph(screen, pr1, 'fps', (100, 255, 100), "FPS", self._target_fps)
        self._draw_graph(screen, pr2, 'frame_time', (255, 150, 100), "Frame Time (ms)", self._target_frame_time)

    def draw_physics_debug(self, screen: pygame.Surface, physics_manager):
        if not config.debug.show_physics_debug: return
        space = physics_manager.space
        x = screen.get_width() - 260
        y = 10
        bg_surface = pygame.Surface((250, 110), pygame.SRCALPHA)
        bg_surface.fill((15, 15, 20, 200))
        pygame.draw.rect(bg_surface, (60, 60, 70), bg_surface.get_rect(), 1)
        screen.blit(bg_surface, (x, y))
        physics_text = ["Physics Debug:", f"Bodies: {len(space.bodies)}", f"Shapes: {len(space.shapes)}",
                        f"Constraints: {len(space.constraints)}", f"Gravity: {space.gravity}",
                        f"Damping: {space.damping:.3f}"]
        for i, text in enumerate(physics_text):
            text_surface = self.font_small.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (x + 8, y + 5 + i * 18))

    def draw_camera_debug(self, screen: pygame.Surface, camera):
        if not config.debug.show_camera_debug: return
        x = screen.get_width() - 260
        y = 130
        bg_surface = pygame.Surface((250, 130), pygame.SRCALPHA)
        bg_surface.fill((15, 15, 20, 200))
        pygame.draw.rect(bg_surface, (60, 60, 70), bg_surface.get_rect(), 1)
        screen.blit(bg_surface, (x, y))
        pos = camera.position
        camera_text = ["Camera Debug:", f"Pos: ({pos[0]:.1f}, {pos[1]:.1f})", f"Zoom: {camera.scaling:.4f}",
                       f"Target: {camera.target_scaling:.4f}", f"Rot: {camera.rotation:.2f}°"]
        for i, text in enumerate(camera_text):
            text_surface = self.font_small.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (x + 8, y + 5 + i * 18))

    def draw_all_debug_info(self, screen: pygame.Surface, physics_manager=None, camera=None):
        if not self.enabled: return
        self.draw_performance_overlay(screen)
        if physics_manager: self.draw_physics_debug(screen, physics_manager)
        if camera: self.draw_camera_debug(screen, camera)
        self.draw_console(screen)

    def handle_input(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.toggle_console()
            elif event.key == pygame.K_F2:
                self.toggle_performance()
            elif event.key == pygame.K_F3:
                self.toggle_physics_debug()
            elif event.key == pygame.K_F4:
                self.toggle_camera_debug()
            elif event.key == pygame.K_F5 and (event.mod & pygame.KMOD_CTRL):
                self.toggle_snapshots_debug()
            elif event.key == pygame.K_F5:
                self.save_debug_info()
            elif event.key == pygame.K_F6:
                self.clear_logs()

    def toggle_console(self):
        config.debug.show_console = not config.debug.show_console
        config.save()
        self.log(LogLevel.INFO, f"Console {'enabled' if config.debug.show_console else 'disabled'}", "Debug")

    def toggle_performance(self):
        config.debug.show_performance = not config.debug.show_performance
        self.log(LogLevel.INFO, f"Performance overlay {'enabled' if self.show_performance else 'disabled'}", "Debug")

    def toggle_physics_debug(self):
        config.debug.show_physics_debug = not config.debug.show_physics_debug
        self.log(LogLevel.INFO, f"Physics debug {'enabled' if self.show_physics_debug else 'disabled'}", "Debug")

    def toggle_camera_debug(self):
        config.debug.show_camera_debug = not config.debug.show_camera_debug
        self.log(LogLevel.INFO, f"Camera debug {'enabled' if self.show_camera_debug else 'disabled'}", "Debug")

    def toggle_snapshots_debug(self):
        config.debug.show_snapshots_debug = not config.debug.show_snapshots_debug
        self.log(LogLevel.INFO, f"Snapshots debug {'enabled' if self.show_snapshots_debug else 'disabled'}", "Snapshot")

    def clear_logs(self):
        self.log_entries.clear()
        self.log(LogLevel.INFO, "Logs cleared", "Debug")

    def save_debug_info(self):
        try:
            debug_info = {"timestamp": time.time(), "frame_count": self.frame_count,
                          "performance_counters": dict(self.performance_counters), "stats": dict(self.stats),
                          "recent_logs": [{"timestamp": e.timestamp, "level": e.level.name, "message": e.message,
                                           "category": e.category, "frame_count": e.frame_count}
                                          for e in list(self.log_entries)[-100:]]}
            filename = f"debug_info_{int(time.time())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            self.log(LogLevel.INFO, f"Debug info saved to {filename}", "Debug")
        except Exception as e:
            self.log(LogLevel.ERROR, f"Failed to save debug info: {e}", "Debug")

    def set_performance_counter(self, name: str, value: float):
        self.performance_counters[name] = value

    def increment_stat(self, name: str, amount: int = 1):
        self.stats[name] += amount

    def set_stat(self, name: str, value: int):
        self.stats[name] = value

    def get_stat(self, name: str) -> int:
        return self.stats.get(name, 0)

    def enable_category(self, category: str):
        self.categories[category] = True

    def disable_category(self, category: str):
        self.categories[category] = False

    def is_category_enabled(self, category: str) -> bool:
        return self.categories.get(category, True)


def get_debug():
    global _debug_instance
    if _debug_instance is None:
        from pygame import init
        init()
        _debug_instance = DebugManager()
    return _debug_instance


def set_debug(debug_manager):
    global _debug_instance
    _debug_instance = debug_manager


class Debug:
    @staticmethod
    def log(message: str, category: str = "General"):
        get_debug().log(LogLevel.DEBUG, message, category)

    @staticmethod
    def log_colored(message: str, color: Tuple[int, int, int], category: str = "General"):
        get_debug().log(LogLevel.DEBUG, message, category, color_override=color)

    @staticmethod
    def log_info(message: str, category: str = "General"):
        get_debug().log(LogLevel.INFO, message, category)

    @staticmethod
    def log_success(message: str, category: str = "General"):
        get_debug().log(LogLevel.SUCCESS, message, category)

    @staticmethod
    def log_warning(message: str, category: str = "General"):
        get_debug().log(LogLevel.WARNING, message, category)

    @staticmethod
    def log_error(message: str, category: str = "General"):
        get_debug().log(LogLevel.ERROR, message, category)

    @staticmethod
    def log_exception(message: str, category: str = "General"):
        get_debug().log(LogLevel.CRITICAL, message, category, include_stack=True)

    @staticmethod
    def assert_condition(condition: bool, message: str = "Assertion failed", category: str = "Assert"):
        if not condition and _debug_instance:
            get_debug().log(LogLevel.ERROR, f"ASSERTION FAILED: {message}", category, include_stack=True)

    @staticmethod
    def draw_line(start: Tuple[float, float], end: Tuple[float, float], color='white', duration=0.0):
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_line(start, end, color, duration=duration)

    @staticmethod
    def draw_ray(origin: Tuple[float, float], direction: Tuple[float, float], length: float = 1.0, color='red',
                 duration=0.0):
        from UPST.gizmos.gizmos_manager import Gizmos
        end = (origin[0] + direction[0] * length, origin[1] + direction[1] * length)
        Gizmos.draw_arrow(origin, end, color, duration=duration)

    @staticmethod
    def draw_circle(center: Tuple[float, float], radius: float, color='white', duration=0.0):
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_circle(center, radius, color, duration=duration)

    @staticmethod
    def draw_rect(center: Tuple[float, float], width: float, height: float, color='white', duration=0.0):
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_rect(center, width, height, color, duration=duration)

    @staticmethod
    def set_performance_counter(name: str, value: float):
        if _debug_instance: _debug_instance.set_performance_counter(name, value)

    @staticmethod
    def increment_stat(name: str, amount: int = 1):
        if _debug_instance: _debug_instance.increment_stat(name, amount)

    @staticmethod
    def get_stat(name: str) -> int:
        if _debug_instance: return _debug_instance.get_stat(name)
        return 0