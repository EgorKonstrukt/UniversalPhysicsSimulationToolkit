import pygame
import time
import traceback
from typing import Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque
import json
from UPST.config import config

_debug_instance = None

class LogLevel(int, Enum):
    """Уровни логирования"""
    DEBUG = 0
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


@dataclass
class LogEntry:
    """Запись лога"""
    timestamp: float
    level: LogLevel
    message: str
    category: str
    frame_count: int
    stack_trace: Optional[str] = None


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

        self.performance_history = defaultdict(lambda: deque(maxlen=60))
        self.performance_counters = defaultdict(float)

        self.stats = defaultdict(int)

        self.log_colors = {
            LogLevel.DEBUG: (200, 200, 200),
            LogLevel.INFO: (255, 55, 255),
            LogLevel.SUCCESS: (55, 255, 55),
            LogLevel.WARNING: (255, 255, 0),
            LogLevel.ERROR: (255, 100, 100),
            LogLevel.CRITICAL: (255, 0, 0)
        }

        self.font_small = pygame.font.SysFont("Consolas", 16)
        self.font_medium = pygame.font.SysFont("Consolas", 18)
        self.font_large = pygame.font.SysFont("Consolas", 22)

        self.console_height = 200
        self.console_alpha = 200
        self.console_scroll = 0
        self.max_console_lines = 50

        self.log_file = "debug_log.txt"

        self.auto_save_logs = True

        self.log(LogLevel.INFO, "Debug Manager initialized", "Debug")

    def update(self, delta_time: float):
        """Обновление менеджера отладки"""
        self.frame_count += 1

        self.performance_history['fps'].append(1.0 / delta_time if delta_time > 0 else 0)
        self.performance_history['frame_time'].append(delta_time * 1000)  # в миллисекундах

    def log(self, level: LogLevel, message: str, category: str = "General",
            include_stack: bool = False):
        """Логирование сообщения"""
        if not self.enabled or not self.categories[category]:
            return

        stack_trace = None
        if include_stack or level >= LogLevel.ERROR:
            stack_trace = traceback.format_stack()

        entry = LogEntry(
            timestamp=time.time() - self.start_time,
            level=level,
            message=message,
            category=category,
            frame_count=self.frame_count,
            stack_trace=stack_trace
        )

        self.log_entries.append(entry)

        if self.auto_save_logs and level >= LogLevel.ERROR:
            self._save_log_entry(entry)

        print(f"[{level.name}] {category}: {message}")

    def _save_log_entry(self, entry: LogEntry):
        """Сохранение записи лога в файл"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp_str = time.strftime("%H:%M:%S", time.gmtime(entry.timestamp))
                f.write(f"[{timestamp_str}] [{entry.level.name}] {entry.category}: {entry.message}\n")
                if entry.stack_trace:
                    f.write("Stack trace:\n")
                    for line in entry.stack_trace:
                        f.write(f"  {line}")
                    f.write("\n")
        except Exception as e:
            print(f"Failed to save log entry: {e}")

    def draw_console(self, screen: pygame.Surface):
        if not config.debug.show_console:
            return

        screen_width = screen.get_width()
        header_height = 20
        total_console_height = self.console_height + header_height
        console_rect = pygame.Rect(0, screen.get_height() - total_console_height,
                                   screen_width, total_console_height)
        console_surface = pygame.Surface((console_rect.width, console_rect.height), pygame.SRCALPHA)
        console_surface.fill((0, 0, 0, self.console_alpha))

        header_text = f"Debug Console (Frame: {self.frame_count}) - Press F1 to toggle"
        header_surface = self.font_large.render(header_text, True, (255, 255, 255))
        console_surface.blit(header_surface, (5, 0))

        y_offset = console_rect.height - 15
        lines_drawn = 0
        for entry in reversed(list(self.log_entries)):
            if lines_drawn >= self.max_console_lines or y_offset <= header_height:
                break
            timestamp_str = f"{entry.timestamp:.2f}s"
            text = f"[{timestamp_str}] [{entry.category}] {entry.message}"
            color = self.log_colors.get(entry.level, (255, 255, 255))
            text_surface = self.font_small.render(text, True, color)
            console_surface.blit(text_surface, (5, y_offset))
            y_offset -= 12
            lines_drawn += 1

        screen.blit(console_surface, console_rect)

    def draw_performance_overlay(self, screen: pygame.Surface):
        if not self.show_performance:
            return
        fps_history = list(self.performance_history['fps'])
        frame_time_history = list(self.performance_history['frame_time'])
        if not fps_history:
            return
        current_fps = fps_history[-1] if fps_history else 0
        avg_fps = sum(fps_history) / len(fps_history) if fps_history else 0
        min_fps = min(fps_history) if fps_history else 0
        max_fps = max(fps_history) if fps_history else 0
        current_frame_time = frame_time_history[-1] if frame_time_history else 0
        avg_frame_time = sum(frame_time_history) / len(frame_time_history) if frame_time_history else 0
        overlay_x = 10
        overlay_y = 10
        line_height = 18
        bg_width = 300
        bg_height = 150
        bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        screen.blit(bg_surface, (overlay_x, overlay_y))
        stats_text = [
            f"FPS: {current_fps:.1f} (Avg: {avg_fps:.1f})",
            f"Frame Time: {current_frame_time:.2f}ms (Avg: {avg_frame_time:.2f}ms)",
            f"Min/Max FPS: {min_fps:.1f}/{max_fps:.1f}",
            f"Frame: {self.frame_count}",
            f"Runtime: {time.time() - self.start_time:.1f}s",
            ""
        ]
        for name, value in self.performance_counters.items():
            stats_text.append(f"{name}: {value:.2f}")
        for i, text in enumerate(stats_text):
            if text:
                color = (255, 255, 255)
                if "FPS:" in text and current_fps < 30:
                    color = (255, 100, 100)
                elif "FPS:" in text and current_fps > 60:
                    color = (100, 255, 100)

                text_surface = self.font_small.render(text, True, color)
                screen.blit(text_surface, (overlay_x + 5, overlay_y + 5 + i * line_height))

    def draw_physics_debug(self, screen: pygame.Surface, physics_manager):
        if not self.show_physics_debug:
            return
        space = physics_manager.space
        body_count = len(space.bodies)
        shape_count = len(space.shapes)
        constraint_count = len(space.constraints)
        x = screen.get_width() - 250
        y = 10
        bg_surface = pygame.Surface((240, 100), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        screen.blit(bg_surface, (x, y))
        physics_text = [
            "Physics Debug:",
            f"Bodies: {body_count}",
            f"Shapes: {shape_count}",
            f"Constraints: {constraint_count}",
            f"Gravity: {space.gravity}",
            f"Damping: {space.damping:.3f}"
        ]
        for i, text in enumerate(physics_text):
            text_surface = self.font_small.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (x + 5, y + 5 + i * 16))

    def draw_camera_debug(self, screen: pygame.Surface, camera):
        if not self.show_camera_debug:
            return
        x = screen.get_width() - 250
        y = 120
        bg_surface = pygame.Surface((240, 120), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        screen.blit(bg_surface, (x, y))
        pos = camera.position
        camera_text = [
            "Camera Debug:",
            f"Position: ({pos[0]:.1f}, {pos[1]:.1f})",
            f"Zoom: {camera.scaling:.2f}",
            f"Target Zoom: {camera.target_scaling:.2f}",
            f"Rotation: {camera.rotation:.1f}°",
            # f"Target Rotation: {camera.target_rotation:.1f}°",
            f"Scaling: {camera.target_scaling:.2f}"
        ]
        for i, text in enumerate(camera_text):
            text_surface = self.font_small.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (x + 5, y + 5 + i * 16))

    def draw_all_debug_info(self, screen: pygame.Surface, physics_manager=None, camera=None):
        if not self.enabled:
            return
        self.draw_performance_overlay(screen)
        if physics_manager:
            self.draw_physics_debug(screen, physics_manager)
        if camera:
            self.draw_camera_debug(screen, camera)
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
        self.show_performance = not self.show_performance
        self.log(LogLevel.INFO, f"Performance overlay {'enabled' if self.show_performance else 'disabled'}", "Debug")

    def toggle_physics_debug(self):
        self.show_physics_debug = not self.show_physics_debug
        self.log(LogLevel.INFO, f"Physics debug {'enabled' if self.show_physics_debug else 'disabled'}", "Debug")

    def toggle_camera_debug(self):
        self.show_camera_debug = not self.show_camera_debug
        self.log(LogLevel.INFO, f"Camera debug {'enabled' if self.show_camera_debug else 'disabled'}", "Debug")

    def toggle_snapshots_debug(self):
        self.show_snapshots_debug = not self.show_snapshots_debug
        self.log(LogLevel.INFO,
                 f"Snapshots debug {'enabled' if self.show_snapshots_debug else 'disabled'}",
                 "Snapshot")

    def clear_logs(self):
        self.log_entries.clear()
        self.log(LogLevel.INFO, "Logs cleared", "Debug")

    def save_debug_info(self):
        try:
            debug_info = {
                "timestamp": time.time(),
                "frame_count": self.frame_count,
                "performance_counters": dict(self.performance_counters),
                "stats": dict(self.stats),
                "recent_logs": [
                    {
                        "timestamp": entry.timestamp,
                        "level": entry.level.name,
                        "message": entry.message,
                        "category": entry.category,
                        "frame_count": entry.frame_count
                    }
                    for entry in list(self.log_entries)[-100:]  # Последние 100 записей
                ]
            }
            filename = f"debug_info_{int(time.time())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)

            self.log(LogLevel.INFO, f"Debug info saved to {filename}", "Debug")
        except Exception as e:
            self.log(LogLevel.ERROR, f"Failed to save debug info: {e}", "Debug")

    def set_performance_counter(self, name: str, value: float):
        """Установка счетчика производительности"""
        self.performance_counters[name] = value

    def increment_stat(self, name: str, amount: int = 1):
        """Увеличение статистики"""
        self.stats[name] += amount

    def set_stat(self, name: str, value: int):
        """Установка статистики"""
        self.stats[name] = value

    def get_stat(self, name: str) -> int:
        """Получение статистики"""
        return self.stats.get(name, 0)

    def enable_category(self, category: str):
        """Включение категории логирования"""
        self.categories[category] = True

    def disable_category(self, category: str):
        """Отключение категории логирования"""
        self.categories[category] = False

    def is_category_enabled(self, category: str) -> bool:
        """Проверка включена ли категория"""
        return self.categories.get(category, True)


def get_debug():
    """Получает глобальный экземпляр DebugManager"""
    global _debug_instance
    if _debug_instance is None:
        from pygame import init
        init()
        _debug_instance = DebugManager()
    return _debug_instance


def set_debug(debug_manager):
    """Устанавливает глобальный экземпляр DebugManager"""
    global _debug_instance
    _debug_instance = debug_manager
class Debug:
    """Статический класс для удобного доступа к отладке (аналог Unity Debug)"""

    @staticmethod
    def log(message: str, category: str = "General"):
        """Логирование отладочного сообщения"""
        get_debug().log(LogLevel.DEBUG, message, category)

    @staticmethod
    def log_info(message: str, category: str = "General"):
        """Логирование информационного сообщения"""
        get_debug().log(LogLevel.INFO, message, category)

    @staticmethod
    def log_succes(message: str, category: str = "General"):
        """Логирование информационного сообщения"""
        get_debug().log(LogLevel.SUCCESS, message, category)

    @staticmethod
    def log_warning(message: str, category: str = "General"):
        """Логирование предупреждения"""
        get_debug().log(LogLevel.WARNING, message, category)

    @staticmethod
    def log_error(message: str, category: str = "General"):
        """Логирование ошибки"""
        get_debug().log(LogLevel.ERROR, message, category)

    @staticmethod
    def log_exception(message: str, category: str = "General"):
        """Логирование критической ошибки с трассировкой стека"""
        get_debug().log(LogLevel.CRITICAL, message, category, include_stack=True)

    @staticmethod
    def assert_condition(condition: bool, message: str = "Assertion failed", category: str = "Assert"):
        """Проверка условия (аналог Unity Debug.Assert)"""
        if not condition and _debug_instance:
            get_debug().log(LogLevel.ERROR, f"ASSERTION FAILED: {message}", category, include_stack=True)

    @staticmethod
    def draw_line(start: Tuple[float, float], end: Tuple[float, float],
                  color='white', duration=0.0):
        """Отрисовка линии для отладки"""
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_line(start, end, color, duration=duration)

    @staticmethod
    def draw_ray(origin: Tuple[float, float], direction: Tuple[float, float],
                 length: float = 1.0, color='red', duration=0.0):
        """Отрисовка луча для отладки"""
        from UPST.gizmos.gizmos_manager import Gizmos
        end = (origin[0] + direction[0] * length, origin[1] + direction[1] * length)
        Gizmos.draw_arrow(origin, end, color, duration=duration)

    @staticmethod
    def draw_circle(center: Tuple[float, float], radius: float,
                    color='white', duration=0.0):
        """Отрисовка окружности для отладки"""
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_circle(center, radius, color, duration=duration)

    @staticmethod
    def draw_rect(center: Tuple[float, float], width: float, height: float,
                  color='white', duration=0.0):
        """Отрисовка прямоугольника для отладки"""
        from UPST.gizmos.gizmos_manager import Gizmos
        Gizmos.draw_rect(center, width, height, color, duration=duration)

    @staticmethod
    def set_performance_counter(name: str, value: float):
        """Установка счетчика производительности"""
        if _debug_instance:
            _debug_instance.set_performance_counter(name, value)

    @staticmethod
    def increment_stat(name: str, amount: int = 1):
        """Увеличение статистики"""
        if _debug_instance:
            _debug_instance.increment_stat(name, amount)

    @staticmethod
    def get_stat(name: str) -> int:
        """Получение статистики"""
        if _debug_instance:
            return _debug_instance.get_stat(name)
        return 0