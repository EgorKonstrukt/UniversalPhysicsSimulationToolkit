import time
import threading
import collections
import pygame
import pygame_gui
import pygame.gfxdraw
from UPST.gui.plotter import Plotter
from contextlib import contextmanager
# from UPST.gizmos_manager import Gizmos
from UPST.config import config

_global_profiler = None


def get_profiler():
    """Получить глобальный экземпляр профайлера"""
    global _global_profiler
    return _global_profiler


def set_profiler(profiler):
    """Установить глобальный экземпляр профайлера"""
    global _global_profiler
    _global_profiler = profiler


def profile(key, group=None):
    """Декоратор для профилирования функций"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            if profiler:
                profiler.start(key, group)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    profiler.stop(key)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def profile_context(key, group=None):
    profiler = get_profiler()
    if profiler:
        profiler.start(key, group)
        try:
            yield
        finally:
            profiler.stop(key)
    else:
        yield


class Profiler:
    def __init__(self, manager, max_samples=config.profiler.max_samples, refresh_rate=config.profiler.max_samples, smoothing_factor=0.15):
        self.manager = manager
        self.data = collections.defaultdict(lambda: collections.deque(maxlen=max_samples))
        self.current = {}
        self.lock = threading.Lock()
        self.visible = False
        self.running = True
        self.paused = config.profiler.paused
        self.refresh_rate = refresh_rate
        self.max_samples = max_samples
        self.smoothing_factor = smoothing_factor
        self.surface_size = config.profiler.normal_size
        self.plotter = Plotter(self.surface_size, max_samples, smoothing_factor, sort_by_value=False)
        self.window = None
        self.tooltip_label = None

        self.group_buttons = {}
        self.group_dropdown = None
        self.group_controls_panel = None

        self.needs_update = False
        self.last_update_time = 0

        set_profiler(self)

        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def _get_color(self, key):
        return self.plotter._get_color(key)

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.show_window()
        elif self.window:
            self.window.kill()
            self.window = None

    def show_window(self):
        if self.window:
            return

        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((config.app.screen_width / 2 - 400, 10),
                             (self.surface_size[0] + 40, self.surface_size[1] + 150)),
            manager=self.manager,
            window_display_title='SysProfiler',
            object_id="#profiler_window",
            resizable=True
        )

        self.image_element = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect((10, 10), self.surface_size),
            image_surface=self.plotter.get_surface(),
            manager=self.manager,
            container=self.window
        )

        button_y = self.surface_size[1] + 20
        self.reset_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, button_y), (80, 30)),
            text='Reset',
            manager=self.manager,
            container=self.window
        )

        self.pause_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((100, button_y), (80, 30)),
            text='Pause',
            manager=self.manager,
            container=self.window
        )

        self.toggle_mode_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((190, button_y), (150, 30)),
            text='Overlay Mode: ON',
            manager=self.manager,
            container=self.window
        )

        self.group_dropdown = pygame_gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect((550, button_y), (150, 30)),
            expansion_height_limit = 1000,
            options_list=self.plotter.get_available_groups(),
            starting_option="All",
            manager=self.manager,
            container=self.window
        )

        self.group_controls_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((10, button_y + 40), (self.surface_size[0], 60)),
            manager=self.manager,
            container=self.window
        )

        self._update_group_controls()

        self.tooltip_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((0, 0), (250, 60)),
            text='',
            manager=self.manager,
            visible=False,
            container=self.window
        )

    def _update_group_controls(self):
        if not self.group_controls_panel:
            return

        for button in self.group_buttons.values():
            button.kill()
        self.group_buttons.clear()

        groups = self.plotter.get_available_groups()
        if len(groups) <= 1:  # Только "All"
            return

        x_offset = 3
        y_offset = 3
        button_width = 150
        button_height = 25
        buttons_per_row = 6

        for i, group in enumerate(groups):
            if group == "All":
                continue

            row = i // buttons_per_row
            col = i % buttons_per_row

            x = x_offset + col * (button_width + 10)
            y = y_offset + row * (button_height + 5)

            is_visible = self.plotter.is_group_visible(group)
            button_text = f"- {group}" if is_visible else f"+ {group}"
            button_color = "#4CAF50" if is_visible else "#F44336"

            button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((x, y), (button_width, button_height)),
                text=button_text,
                manager=self.manager,
                container=self.group_controls_panel,
                object_id=f"#{button_color}_button"
            )

            self.group_buttons[group] = button

    def process_event(self, event):
        if not self.visible:
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.reset_button:
                self.plotter.clear_data()
                self._update_group_controls()
                self._update_dropdown()
                self.needs_update = True
            elif event.ui_element == self.pause_button:
                self.paused = not self.paused
                self.pause_button.set_text('Resume' if self.paused else 'Pause')
            elif event.ui_element == self.toggle_mode_button:
                self.plotter.set_overlay_mode(not self.plotter.overlay_mode)
                self.toggle_mode_button.set_text(f"Overlay Mode: {'ON' if self.plotter.overlay_mode else 'OFF'}")
                self.needs_update = True
            else:
                for group, button in self.group_buttons.items():
                    if event.ui_element == button:
                        current_visibility = self.plotter.is_group_visible(group)
                        self.plotter.set_group_visibility(group, not current_visibility)
                        self._update_group_controls()
                        self.needs_update = True
                        break

        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.group_dropdown:
                selected_group = event.text
                self.plotter.set_group_filter(selected_group)
                self.needs_update = True

        elif event.type == pygame_gui.UI_WINDOW_RESIZED:
            if event.ui_element == self.window:
                self._on_resize()

    def _update_dropdown(self):
        if self.group_dropdown:
            options = self.plotter.get_available_groups()
            current_selection = self.group_dropdown.selected_option
            self.group_dropdown.kill()

            button_y = self.surface_size[1] + 20
            self.group_dropdown = pygame_gui.elements.UIDropDownMenu(
                relative_rect=pygame.Rect((350, button_y), (150, 30)),
                options_list=options,
                starting_option=current_selection if current_selection in options else "All",
                manager=self.manager,
                container=self.window
            )

    def start(self, key, group=None):
        if self.paused:
            return
        self.current[key] = {"time": time.perf_counter(), "group": group}

    def stop(self, key):
        if key in self.current:
            start_data = self.current[key]
            elapsed = (time.perf_counter() - start_data["time"]) * 1000
            group = start_data["group"]

            if self.lock.acquire(blocking=False):
                try:
                    self.plotter.add_data(key, elapsed, group)
                    self.needs_update = True

                    if group and group not in self.group_buttons:
                        self._update_group_controls()
                        self._update_dropdown()

                finally:
                    self.lock.release()
            del self.current[key]

    @profile("profiler_update")
    def run(self):
        """Оптимизированный основной цикл"""

        while self.running:

            if self.visible and not self.paused and self.needs_update:
                current_time = time.perf_counter()
                if current_time - self.last_update_time >= self.refresh_rate:
                    self.update_graph()
                    self.last_update_time = current_time
                    self.needs_update = False

            sleep_time = config.profiler.update_delay if self.visible else 0.5
            time.sleep(sleep_time)

    def update_graph(self):
        """Обновить график только при необходимости"""
        if not self.image_element:
            return

        if self.lock.acquire(blocking=False):
            try:
                self.image_element.set_image(self.plotter.get_surface())
            finally:
                self.lock.release()

    def _on_resize(self):
        if not self.window:
            return
        container = self.window.get_container()
        new_width, new_height = container.get_size()
        graph_width = max(400, new_width - 40)
        graph_height = max(200, new_height - 150)
        self.surface_size = (graph_width, graph_height)
        self.plotter.surface_size = self.surface_size
        self.plotter.surface = pygame.Surface(self.surface_size, pygame.SRCALPHA)
        self.image_element.set_dimensions(self.surface_size)
        self.image_element.set_relative_position((10, 10))
        button_y = self.surface_size[1] + 20
        self.reset_button.set_relative_position((10, button_y))
        self.pause_button.set_relative_position((100, button_y))
        self.toggle_mode_button.set_relative_position((190, button_y))
        self.group_dropdown.set_relative_position((350, button_y))
        self.group_controls_panel.set_dimensions((self.surface_size[0], 60))
        self.group_controls_panel.set_relative_position((10, button_y + 40))
        self._update_group_controls()
        self.needs_update = True

    def stop_thread(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)

        global _global_profiler
        if _global_profiler is self:
            _global_profiler = None


def start_profiling(key, group=None):
    profiler = get_profiler()
    if profiler:
        profiler.start(key, group)


def stop_profiling(key):
    profiler = get_profiler()
    if profiler:
        profiler.stop(key)


# Примеры использования:
"""
# Использование декоратора с группой
@profile("database_query", group="database")
def fetch_user_data():
    pass

@profile("render_ui", group="graphics")
def render_interface():
    pass

# Использование контекстного менеджера
def process_data():
    with profile_context("heavy_computation", group="processing"):
        # тяжелые вычисления
        pass

    with profile_context("network_request", group="network"):
        # сетевые запросы
        pass

# Ручное профилирование
def manual_profiling():
    start_profiling("custom_task", group="custom")
    # код задачи
    stop_profiling("custom_task")
"""