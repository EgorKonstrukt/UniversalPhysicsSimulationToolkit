import pygame
import time
import traceback
import sys
import gc
import os
import re
from typing import Dict, Optional, Tuple, List, Any
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque
import json
import psutil
import colorama
import pyperclip

from UPST.config import config

colorama.init()

_debug_instance = None


class LogLevel(int, Enum):
    TRACE = -1
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
    exc_type: Optional[str] = None
    line_no: Optional[int] = None

    def get_full_text(self) -> str:
        ts_str = f"{self.timestamp:.3f}"
        return f"[{ts_str}] [{self.level.name}] [{self.category}] {self.message}"

    def get_message_only(self) -> str:
        return self.message


class DebugManager:
    def __init__(self, max_log_entries=2000):
        self.enabled = True
        self.log_entries: List[LogEntry] = []
        self.max_log_entries = max_log_entries
        self.categories: Dict[str, bool] = defaultdict(lambda: True)
        self.min_log_level = LogLevel.DEBUG
        self.frame_count = 0
        self.start_time = time.time()

        self.show_console = config.debug.show_console
        self.show_performance = config.debug.show_performance
        self.show_physics_debug = config.debug.show_physics_debug
        self.show_camera_debug = config.debug.show_camera_debug
        self.show_snapshots_debug = config.debug.show_snapshots_debug

        self.console_rect: Optional[pygame.Rect] = None
        self.console_dragging = False
        self.console_resizing = False
        self.drag_offset = (0, 0)

        self.selected_index = -1
        self.scroll_offset = 0.0

        self.line_height = 18
        self.padding = 5
        self.header_height = 24
        self.min_console_height = 100
        self.max_console_height = 600

        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.smoothed_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.performance_counters = defaultdict(float)
        self.stats = defaultdict(int)

        self.log_colors = {
            LogLevel.TRACE: (150, 150, 150), LogLevel.DEBUG: (200, 200, 200),
            LogLevel.INFO: (100, 200, 255), LogLevel.SUCCESS: (50, 255, 100),
            LogLevel.WARNING: (255, 200, 50), LogLevel.ERROR: (255, 80, 80),
            LogLevel.CRITICAL: (255, 0, 0)
        }

        self.font_small = pygame.font.SysFont("Consolas", 13)
        self.font_medium = pygame.font.SysFont("Consolas", 15)
        self.font_large = pygame.font.SysFont("Consolas", 18)
        self.font_bold = pygame.font.SysFont("Consolas", 14, bold=True)

        self.console_height = 400
        self.console_alpha = 210
        self.console_bg_color = (10, 10, 15)
        self.log_file = "debug_log.txt"
        self.auto_save_logs = True

        self._axis_limits = {'fps': [0.0, 144.0], 'frame_time': [0.0, 20.0], 'memory': [0.0, 100.0]}
        self._axis_smooth_factor = 0.92
        self._data_smooth_factor = 0.25
        self._target_fps = 60.0
        self._target_frame_time = 16.67

        self._text_cache: Dict[str, Tuple[pygame.Surface, float]] = {}
        self._last_cache_clear = 0

        try:
            self.process = psutil.Process(os.getpid())
        except:
            self.process = None
        self.last_gc_time = time.time()

        self.last_screen_h = 0

    def update(self, delta_time: float):
        self.frame_count += 1
        fps = 1.0 / delta_time if delta_time > 0 else 0
        ft = delta_time * 1000
        mem_mb = 0
        if self.process:
            try:
                mem_mb = self.process.memory_info().rss / 1024 / 1024
            except:
                pass

        self.performance_history['fps'].append(fps)
        self.performance_history['frame_time'].append(ft)
        self.performance_history['memory'].append(mem_mb)

        now = time.time()
        if now - self._last_cache_clear > 2.0:
            self._text_cache.clear()
            self._last_cache_clear = now

        if now - self.last_gc_time > 10.0:
            gc.collect()
            self.last_gc_time = now

        for key in ['fps', 'frame_time', 'memory']:
            hist = self.performance_history[key]
            smooth = self.smoothed_history[key]
            if len(hist) == 0: continue
            current_val = hist[-1]
            prev_smooth = smooth[-1] if len(smooth) > 0 else current_val
            weight = self._data_smooth_factor if abs(current_val - prev_smooth) < (max(10, prev_smooth * 0.1)) else 0.6
            new_smooth = prev_smooth * (1 - weight) + current_val * weight
            smooth.append(new_smooth)

            limit_min = min(smooth)
            limit_max = max(smooth)
            margin = (limit_max - limit_min) * 0.15 if limit_max != limit_min else 10.0
            target_min = max(0, limit_min - margin)
            target_max = limit_max + margin

            if key == 'fps': target_max = max(target_max, self._target_fps * 1.2)
            if key == 'frame_time': target_max = max(target_max, self._target_frame_time * 1.5)
            if key == 'memory': target_max = max(target_max, mem_mb * 1.2)

            curr_min, curr_max = self._axis_limits[key]
            self._axis_limits[key][0] = curr_min * self._axis_smooth_factor + target_min * (
                        1 - self._axis_smooth_factor)
            self._axis_limits[key][1] = curr_max * self._axis_smooth_factor + target_max * (
                        1 - self._axis_smooth_factor)

    def _get_text_surface(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int]):
        key = f"{text}_{color}"
        if key in self._text_cache:
            surf, created_at = self._text_cache[key]
            if time.time() - created_at < 1.0:
                return surf
        surf = font.render(text, True, color)
        self._text_cache[key] = (surf, time.time())
        return surf

    def log(self, level: LogLevel, message: str, category: str = "General",
            include_stack: bool = False, color_override: Optional[Tuple[int, int, int]] = None,
            exc_info: Optional[Any] = None):
        if not self.enabled or not self.categories[category] or level < self.min_log_level:
            return

        stack_trace = None
        exc_type_str = None
        line_no = None

        if exc_info:
            exc_type, exc_value, exc_tb = exc_info
            exc_type_str = exc_type.__name__ if exc_type else "UnknownError"
            if exc_tb:
                line_no = exc_tb.tb_lineno
                filename = os.path.basename(exc_tb.tb_frame.f_code.co_filename)
                message = f"{exc_type_str}: {exc_value} (in {filename}:{line_no})\n{message}"

        if include_stack or level >= LogLevel.ERROR:
            stack_trace = ''.join(traceback.format_stack(limit=5))

        reset = "\033[0m"
        display_color = color_override or self.log_colors.get(level, (255, 255, 255))

        if color_override is not None:
            r, g, b = color_override
            ansi_color = f"\033[38;2;{r};{g};{b}m"
        else:
            ansi_colors = {
                LogLevel.TRACE: "\033[38;5;245m", LogLevel.DEBUG: "\033[38;5;245m",
                LogLevel.INFO: "\033[38;5;39m", LogLevel.SUCCESS: "\033[38;5;46m",
                LogLevel.WARNING: "\033[38;5;226m", LogLevel.ERROR: "\033[38;5;203m",
                LogLevel.CRITICAL: "\033[38;5;196m"
            }
            ansi_color = ansi_colors.get(level, "")

        for line in message.split('\n'):
            entry = LogEntry(
                timestamp=time.time() - self.start_time, level=level, message=line,
                category=category, frame_count=self.frame_count, stack_trace=stack_trace,
                color=display_color, exc_type=exc_type_str, line_no=line_no
            )

            if len(self.log_entries) >= self.max_log_entries:
                self.log_entries.pop(0)
                if self.selected_index > 0:
                    self.selected_index -= 1
            self.log_entries.append(entry)

            if self.selected_index == -1 or self.selected_index == len(self.log_entries) - 2:
                self.selected_index = len(self.log_entries) - 1
                self._ensure_visible()

            if self.auto_save_logs and level >= LogLevel.WARNING:
                self._save_log_entry(entry)

            ts_str = f"{entry.timestamp:.3f}"
            print(f"{ansi_color}[{ts_str}] [{level.name:<8}] [{category}] {line}{reset}")

    def log_exception(self, message: str = "An exception occurred", category: str = "Exception"):
        exc_info = sys.exc_info()
        self.log(LogLevel.CRITICAL, message, category, include_stack=True, exc_info=exc_info)

    def _save_log_entry(self, entry: LogEntry):
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                ts_str = time.strftime("%H:%M:%S", time.gmtime(entry.timestamp + self.start_time))
                f.write(f"[{ts_str}] [{entry.level.name}] [{entry.category}] {entry.message}\n")
                if entry.stack_trace:
                    f.write(f"Stack:\n{entry.stack_trace}\n")
                f.write("-" * 40 + "\n")
        except Exception as e:
            print(f"Failed to save log: {e}")

    def _ensure_visible(self):
        if self.selected_index < 0: return

        content_h = self.console_height - self.header_height - 2 * self.padding
        visible_lines = max(1, int(content_h // self.line_height))
        total_lines = len(self.log_entries)

        start_visible = int(self.scroll_offset // self.line_height)
        end_visible = start_visible + visible_lines

        if self.selected_index < start_visible:
            self.scroll_offset = float(self.selected_index * self.line_height)
        elif self.selected_index >= end_visible:
            self.scroll_offset = float((self.selected_index - visible_lines + 1) * self.line_height)

        self.scroll_offset = max(0.0, self.scroll_offset)

    def _draw_dashed_line(self, screen: pygame.Surface, color: Tuple[int, int, int],
                          start: Tuple[int, int], end: Tuple[int, int], width: int = 1, dash_length: int = 4):
        x1, y1 = start
        x2, y2 = end
        if x1 == x2:
            for y in range(y1, y2, dash_length * 2):
                pygame.draw.line(screen, color, (x1, y), (x1, min(y + dash_length, y2)), width)
        elif y1 == y2:
            for x in range(x1, x2, dash_length * 2):
                pygame.draw.line(screen, color, (x, y1), (min(x + dash_length, x2), y1), width)
        else:
            dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            if dist == 0: return
            dx = (x2 - x1) / dist
            dy = (y2 - y1) / dist
            curr = 0.0
            while curr < dist:
                next_val = min(curr + dash_length, dist)
                sx, sy = x1 + dx * curr, y1 + dy * curr
                ex, ey = x1 + dx * next_val, y1 + dy * next_val
                pygame.draw.line(screen, color, (sx, sy), (ex, ey), width)
                curr += dash_length * 2

    def draw_console(self, screen: pygame.Surface):
        if not config.debug.show_console:
            self.console_rect = None
            return

        sw, sh = screen.get_size()

        if self.last_screen_h != sh:
            if self.console_rect:
                if abs((self.console_rect.bottom) - self.last_screen_h) < 50:
                    self.console_rect.bottom = sh
                self.last_screen_h = sh
            else:
                self.last_screen_h = sh

        w = sw
        h = self.console_height

        if self.console_rect is None:
            self.console_rect = pygame.Rect(0, sh - h, w, h)
        else:
            old_right = self.console_rect.right
            self.console_rect.width = w
            if self.console_rect.right > sw:
                self.console_rect.x = sw - w

            self.console_rect.height = max(self.min_console_height,
                                           min(self.max_console_height, self.console_rect.height))
            self.console_height = self.console_rect.height

            if self.console_rect.top < 0:
                self.console_rect.top = 0
            if self.console_rect.bottom > sh:
                self.console_rect.bottom = sh

        console_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        console_surf.fill((*self.console_bg_color, self.console_alpha))

        header_rect = pygame.Rect(0, 0, w, self.header_height)
        pygame.draw.rect(console_surf, (30, 30, 40, 255), header_rect)
        pygame.draw.line(console_surf, (60, 60, 80), (0, self.header_height), (w, self.header_height), 1)

        count_str = f"{len(self.log_entries)} logs"
        if self.selected_index >= 0:
            count_str += f" | Sel: {self.selected_index + 1}/{len(self.log_entries)}"

        status_txt = f"Debug Console | FPS: {self.performance_history['fps'][-1]:.1f} | Mem: {self.performance_history['memory'][-1]:.1f}MB | {count_str}"
        txt_surf = self.font_medium.render(status_txt, True, (200, 200, 220))
        console_surf.blit(txt_surf, (10, 4))

        hint_txt = "Alt+DragTop:Resize Arrows:Nav Ctrl+C:Copy"
        hint_surf = self.font_small.render(hint_txt, True, (100, 100, 120))
        console_surf.blit(hint_surf, (w - hint_surf.get_width() - 10, 6))

        content_rect = pygame.Rect(self.padding, self.header_height + self.padding,
                                   w - 2 * self.padding, h - self.header_height - 2 * self.padding)
        console_surf.set_clip(content_rect)

        start_idx = max(0, int(self.scroll_offset // self.line_height))
        visible_lines = int(content_rect.height // self.line_height) + 2
        end_idx = min(len(self.log_entries), start_idx + visible_lines)

        for i in range(start_idx, end_idx):
            if i < 0 or i >= len(self.log_entries): continue
            entry = self.log_entries[i]

            y = int(content_rect.top + (i * self.line_height) - self.scroll_offset)

            if y + self.line_height < content_rect.top or y > content_rect.bottom:
                continue

            if i == self.selected_index:
                sel_rect = pygame.Rect(content_rect.left, y, content_rect.width, self.line_height)
                sel_rect.clamp_ip(content_rect)
                pygame.draw.rect(console_surf, (60, 70, 90, 150), sel_rect)
                pygame.draw.rect(console_surf, (100, 150, 255, 100), sel_rect, 1)

            ts_str = f"{entry.timestamp:.2f}"
            prefix = f"[{ts_str}] [{entry.level.name}] "
            color = entry.color or self.log_colors.get(entry.level, (255, 255, 255))

            pre_surf = self.font_small.render(prefix, True, color)
            console_surf.blit(pre_surf, (content_rect.left, y))

            msg_x = content_rect.left + pre_surf.get_width()
            max_w = content_rect.right - msg_x - 5

            msg_text = entry.message
            if self.font_small.size(msg_text)[0] > max_w:
                ratio = max_w / max(1, self.font_small.size(msg_text)[0])
                chars_fit = int(len(msg_text) * ratio)
                msg_text = msg_text[:max(0, chars_fit - 3)] + "..."

            msg_surf = self.font_small.render(msg_text, True, (220, 220, 220))
            console_surf.blit(msg_surf, (msg_x, y))

            if entry.exc_type:
                exc_surf = self.font_bold.render(f"!{entry.exc_type}", True, (255, 50, 50))
                console_surf.blit(exc_surf, (msg_x + msg_surf.get_width() + 5, y))

        console_surf.set_clip(None)

        total_h = len(self.log_entries) * self.line_height
        if total_h > content_rect.height:
            ratio = content_rect.height / total_h
            bar_h = max(20, int(content_rect.height * ratio))
            scroll_pos = (self.scroll_offset / total_h) * (content_rect.height - bar_h)
            bar_rect = pygame.Rect(w - 6, int(content_rect.top + scroll_pos), 4, bar_h)
            pygame.draw.rect(console_surf, (100, 100, 120), bar_rect, border_radius=2)

        screen.blit(console_surf, self.console_rect)

    def _draw_graph(self, screen: pygame.Surface, rect: pygame.Rect, data_key: str, color: Tuple[int, int, int],
                    label: str, ref_val: float = None):
        hist = list(self.smoothed_history[data_key])
        if len(hist) < 2: return

        min_y, max_y = self._axis_limits[data_key]
        range_y = max(0.1, max_y - min_y)

        pts = []
        step = max(1, len(hist) // rect.width)
        for i in range(0, len(hist), step):
            v = hist[i]
            x = rect.left + int((i / (len(hist) - 1)) * rect.width)
            norm_v = (v - min_y) / range_y
            y = rect.bottom - int(norm_v * rect.height)
            pts.append((x, max(rect.top, min(rect.bottom, y))))

        if len(pts) > 1:
            pygame.draw.lines(screen, color, False, pts, 2)
            fill_pts = pts + [(pts[-1][0], rect.bottom), (pts[0][0], rect.bottom)]
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if len(fill_pts) > 2:
                pygame.draw.polygon(s, (*color, 30), fill_pts)
                screen.blit(s, (rect.left, rect.top))

        if ref_val is not None:
            ry = rect.bottom - int((ref_val - min_y) / range_y * rect.height)
            if rect.top <= ry <= rect.bottom:
                self._draw_dashed_line(screen, (150, 150, 150), (rect.left, ry), (rect.right, ry), 1, 4)
                lbl_ref = self._get_text_surface(f"{ref_val:.1f}", self.font_small, (150, 150, 150))
                screen.blit(lbl_ref, (rect.right - lbl_ref.get_width() - 2, ry - lbl_ref.get_height()))

        for i in range(1, 4):
            gy = rect.bottom - int((min_y + range_y * i / 4 - min_y) / range_y * rect.height)
            if rect.top <= gy <= rect.bottom:
                pygame.draw.line(screen, (40, 40, 50), (rect.left, gy), (rect.right, gy), 1)
                val = min_y + range_y * i / 4
                lbl_grid = self._get_text_surface(f"{val:.1f}", self.font_small, (80, 80, 90))
                screen.blit(lbl_grid, (rect.left + 2, gy - lbl_grid.get_height()))

        lbl = self._get_text_surface(label, self.font_medium, color)
        bg_lbl = pygame.Surface((lbl.get_width() + 6, lbl.get_height() + 4), pygame.SRCALPHA)
        bg_lbl.fill((0, 0, 0, 180))
        screen.blit(bg_lbl, (rect.right - lbl.get_width() - 8, rect.top + 4))
        screen.blit(lbl, (rect.right - lbl.get_width() - 5, rect.top + 5))

    def draw_performance_overlay(self, screen: pygame.Surface):
        if not config.debug.show_performance: return
        fps_hist = list(self.performance_history['fps'])
        if not fps_hist: return

        cur_fps = fps_hist[-1]
        avg_fps = sum(fps_hist) / len(fps_hist)
        cur_mem = self.performance_history['memory'][-1] if self.performance_history['memory'] else 0

        ox, oy = 10, 10
        lh = 18
        w = 400
        stats_h = 100
        plot_h = 100
        gap = 10
        total_h = stats_h + plot_h * 2 + gap * 2 + 10

        bg = pygame.Surface((w, total_h), pygame.SRCALPHA)
        bg.fill((12, 12, 18, 220))
        pygame.draw.rect(bg, (50, 50, 60), bg.get_rect(), 1)
        screen.blit(bg, (ox, oy))

        c_fps = (50, 255, 50) if cur_fps >= 55 else (255, 200, 0) if cur_fps >= 30 else (255, 50, 50)

        left_col = [
            (f"FPS: {cur_fps:.1f}", c_fps),
            (f"Avg: {avg_fps:.1f}", (180, 180, 180)),
            (f"Frame: {self.frame_count}", (255, 255, 255)),
            (f"Time: {time.time() - self.start_time:.0f}s", (150, 150, 150)),
        ]
        right_col = [
            (f"RAM: {cur_mem:.1f} MB", (100, 200, 255)),
            (f"GC: {(time.time() - self.last_gc_time):.1f}s ago", (150, 150, 150)),
        ]
        for k, v in self.performance_counters.items():
            right_col.append((f"{k}: {v:.2f}", (200, 150, 255)))

        start_y = oy + 8
        col_w = (w - 30) // 2

        for i, (t, c) in enumerate(left_col):
            txt = self._get_text_surface(t, self.font_small, c)
            screen.blit(txt, (ox + 10, start_y + i * lh))

        for i, (t, c) in enumerate(right_col):
            txt = self._get_text_surface(t, self.font_small, c)
            screen.blit(txt, (ox + 10 + col_w + 10, start_y + i * lh))

        py1 = oy + stats_h + 5
        py2 = py1 + plot_h + gap
        pw = w - 20
        pr1 = pygame.Rect(ox + 10, py1, pw, plot_h)
        pr2 = pygame.Rect(ox + 10, py2, pw, plot_h)

        pygame.draw.rect(screen, (40, 40, 50), pr1, 1)
        pygame.draw.rect(screen, (40, 40, 50), pr2, 1)

        self._draw_graph(screen, pr1, 'fps', (50, 255, 50), "FPS", self._target_fps)
        self._draw_graph(screen, pr2, 'frame_time', (255, 150, 50), "Frame Time (ms)", self._target_frame_time)

    def draw_physics_debug(self, screen: pygame.Surface, physics_manager):
        if not config.debug.show_physics_debug or not physics_manager: return
        space = physics_manager.space
        x = screen.get_width() - 270
        y = 10
        bg_surface = pygame.Surface((260, 130), pygame.SRCALPHA)
        bg_surface.fill((12, 12, 18, 210))
        pygame.draw.rect(bg_surface, (50, 50, 60), bg_surface.get_rect(), 1)
        screen.blit(bg_surface, (x, y))

        title = self.font_medium.render("Physics Debug", True, (255, 200, 50))
        screen.blit(title, (x + 10, y + 5))

        info = [
            f"Bodies: {len(space.bodies)}", f"Shapes: {len(space.shapes)}",
            f"Constraints: {len(space.constraints)}", f"Gravity: ({space.gravity[0]:.1f}, {space.gravity[1]:.1f})",
            f"Damping: {space.damping:.3f}"
        ]
        for i, text in enumerate(info):
            text_surface = self.font_small.render(text, True, (200, 200, 220))
            screen.blit(text_surface, (x + 10, y + 25 + i * 18))

    def draw_camera_debug(self, screen: pygame.Surface, camera):
        if not config.debug.show_camera_debug or not camera: return
        x = screen.get_width() - 270
        y = 150
        bg_surface = pygame.Surface((260, 140), pygame.SRCALPHA)
        bg_surface.fill((12, 12, 18, 210))
        pygame.draw.rect(bg_surface, (50, 50, 60), bg_surface.get_rect(), 1)
        screen.blit(bg_surface, (x, y))

        title = self.font_medium.render("Camera Debug", True, (100, 200, 255))
        screen.blit(title, (x + 10, y + 5))

        pos = camera.position
        info = [
            f"Pos: ({pos[0]:.2f}, {pos[1]:.2f})", f"Zoom: {camera.scaling:.4f}",
            f"Target: {camera.target_scaling:.4f}", f"Rot: {camera.rotation:.2f}°",
            f"Vel: ({camera.velocity[0]:.1f}, {camera.velocity[1]:.1f})" if hasattr(camera, 'velocity') else ""
        ]
        for i, text in enumerate(info):
            if not text: continue
            text_surface = self.font_small.render(text, True, (200, 200, 220))
            screen.blit(text_surface, (x + 10, y + 25 + i * 18))

    def draw_all_debug_info(self, screen: pygame.Surface, physics_manager=None, camera=None):
        if not self.enabled: return
        self.draw_performance_overlay(screen)
        if physics_manager: self.draw_physics_debug(screen, physics_manager)
        if camera: self.draw_camera_debug(screen, camera)
        self.draw_console(screen)

    def handle_input(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            count = len(self.log_entries)

            if event.key == pygame.K_c and (mods & pygame.KMOD_CTRL):
                if not config.debug.show_console: return
                if self.selected_index >= 0 and self.selected_index < count:
                    entry = self.log_entries[self.selected_index]
                    text_to_copy = entry.get_message_only() if (mods & pygame.KMOD_SHIFT) else entry.get_full_text()
                    try:
                        pyperclip.copy(text_to_copy)
                    except:
                        pass

            if event.key == pygame.K_UP:
                if count > 0: self.selected_index = max(0, self.selected_index - 1); self._ensure_visible()
            elif event.key == pygame.K_DOWN:
                if count > 0: self.selected_index = min(count - 1, self.selected_index + 1); self._ensure_visible()
            elif event.key == pygame.K_PAGEUP:
                if count > 0:
                    visible = max(1, int((self.console_height - self.header_height) // self.line_height))
                    self.selected_index = max(0, self.selected_index - visible)
                    self._ensure_visible()
            elif event.key == pygame.K_PAGEDOWN:
                if count > 0:
                    visible = max(1, int((self.console_height - self.header_height) // self.line_height))
                    self.selected_index = min(count - 1, self.selected_index + visible)
                    self._ensure_visible()
            elif event.key == pygame.K_HOME:
                if count > 0: self.selected_index = 0; self._ensure_visible()
            elif event.key == pygame.K_END:
                if count > 0: self.selected_index = count - 1; self._ensure_visible()
            elif event.key == pygame.K_F1:
                config.debug.show_console = not config.debug.show_console
                # self.log(LogLevel.INFO, f"Console {'enabled' if self.show_console else 'disabled'}", "UI")
            elif event.key == pygame.K_F2:
                config.debug.show_performance = not config.debug.show_performance
            elif event.key == pygame.K_F3:
                config.debug.show_physics_debug = not config.debug.show_physics_debug
            elif event.key == pygame.K_F4:
                config.debug.show_camera_debug = not config.debug.show_camera_debug
            elif event.key == pygame.K_F5:
                self.save_debug_info()
            elif event.key == pygame.K_F6:
                self.clear_logs()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and config.debug.show_console and self.console_rect:
                mx, my = event.pos
                resize_zone = pygame.Rect(self.console_rect.x, self.console_rect.y, self.console_rect.width, 5)

                if pygame.key.get_mods() & pygame.KMOD_ALT:
                    if resize_zone.collidepoint(mx, my):
                        self.console_resizing = True
                        self.resize_start_y = my
                        self.start_h = self.console_rect.height
                        return

                header_rect = pygame.Rect(self.console_rect.x, self.console_rect.y, self.console_rect.width,
                                          self.header_height)
                if header_rect.collidepoint(mx, my):
                    self.console_dragging = True
                    self.drag_offset = (mx - self.console_rect.x, my - self.console_rect.y)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.console_dragging = False
                self.console_resizing = False

        elif event.type == pygame.MOUSEMOTION:
            if self.console_resizing:
                _, my = event.pos
                delta = self.resize_start_y - my
                new_h = self.start_h + delta
                self.console_height = max(self.min_console_height, min(self.max_console_height, new_h))
                self.console_rect.height = self.console_height
                self.console_rect.y = (self.console_rect.y + self.start_h) - self.console_height  # Корректировка Y

            if self.console_dragging:
                new_x = event.pos[0] - self.drag_offset[0]
                new_y = event.pos[1] - self.drag_offset[1]
                self.console_rect.x = new_x
                self.console_rect.y = new_y



    def clear_logs(self):
        self.log_entries.clear()
        self.selected_index = -1
        self.scroll_offset = 0.0
        self.log(LogLevel.INFO, "Logs cleared", "System")

    def save_debug_info(self):
        try:
            debug_info = {
                "timestamp": time.time(), "frame_count": self.frame_count,
                "performance_counters": dict(self.performance_counters),
                "stats": dict(self.stats),
                "recent_logs": [{"ts": e.timestamp, "level": e.level.name, "msg": e.message, "cat": e.category} for e in
                                self.log_entries[-200:]]
            }
            filename = f"debug_dump_{int(time.time())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            self.log(LogLevel.SUCCESS, f"Debug info saved to {filename}", "System")
        except Exception as e:
            self.log_exception(f"Failed to save debug info: {e}", "System")

    def set_performance_counter(self, name: str, value: float):
        self.performance_counters[name] = value

    def increment_stat(self, name: str, amount: int = 1):
        self.stats[name] += amount

    def enable_category(self, category: str):
        self.categories[category] = True

    def disable_category(self, category: str):
        self.categories[category] = False


def get_debug():
    global _debug_instance
    if _debug_instance is None:
        pygame.init()
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
    def log_exception(message: str = "Exception", category: str = "Exception"):
        get_debug().log_exception(message, category)

    @staticmethod
    def assert_condition(condition: bool, message: str = "Assertion failed", category: str = "Assert"):
        if not condition:
            get_debug().log(LogLevel.ERROR, f"ASSERT: {message}", category, include_stack=True)

    @staticmethod
    def draw_line(start: Tuple[float, float], end: Tuple[float, float], color='white', duration=0.0):
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_line(start, end, color, duration=duration)

    @staticmethod
    def draw_ray(origin: Tuple[float, float], direction: Tuple[float, float], length: float = 1.0, color='red',
                 duration=0.0):
        from UPST.gizmos.gizmos_manager import Gizmos
        end_pos = (origin[0] + direction[0] * length, origin[1] + direction[1] * length)
        Gizmos.draw_arrow(origin, end_pos, color, duration=duration)

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
        return _debug_instance.get_stat(name) if _debug_instance else 0