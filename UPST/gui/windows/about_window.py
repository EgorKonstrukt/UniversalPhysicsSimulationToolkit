import pygame
import pygame_gui
from pygame_gui.elements import UIImage, UITextBox, UIWindow
from UPST.modules.statistics import stats
import time

class AboutWindow(UIWindow):
    def __init__(self, rect, manager, app_name="Universal Physics Simulation Toolkit"):
        super().__init__(rect, manager, window_display_title="About", object_id="#about_window")
        self.app_name = app_name
        self.set_blocking(True)

        try:
            logo = pygame.image.load("logo.png").convert_alpha()
        except (pygame.error, FileNotFoundError):
            logo = pygame.Surface((256, 256), pygame.SRCALPHA)
            pygame.draw.rect(logo, (200, 200, 200), logo.get_rect(), 2)

        self.logo_image = UIImage(
            relative_rect=pygame.Rect((rect.width - 256) // 2, 10, 256, 256),
            image_surface=logo,
            container=self,
            manager=manager
        )

        stats_html = self._build_stats_html()
        self.stats_box = UITextBox(
            html_text=stats_html,
            relative_rect=pygame.Rect(20, 280, rect.width - 40, 300),
            manager=manager,
            container=self,
            object_id="#about_stats"
        )

    def _format_time(self, seconds):
        if seconds < 0:
            return "--:--:--"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _build_stats_html(self):
        lines = [f"<b>Universal Physics Simulation Toolkit</b>\n<i>Simulate. Visualize. Understand.</i>", "<br>"]

        lines.append("<b>Engine</b>: Pygame + Pymunk")
        lines.append("<b>Author</b>: Zarrakun")
        lines.append("<br>")

        try:
            session_time = time.time() - stats.session_start
        except AttributeError:
            session_time = 0
        lines.append(f"<b>Total Runtime</b>: {self._format_time(stats.total_runtime)}")
        lines.append(f"<b>Current Session</b>: {self._format_time(session_time)}")
        lines.append(f"<b>Launch Count</b>: {getattr(stats, 'launch_count', 0)}")
        lines.append("<br>")

        dynamic_keys = []
        for key in sorted(vars(stats).get('_data', {}).keys()):
            if key not in ('total_runtime', 'session_start', 'launch_count'):
                value = getattr(stats, key, None)
                if isinstance(value, (int, float)):
                    dynamic_keys.append((key.replace('_', ' ').title(), value))
        for key, value in dynamic_keys:
            if isinstance(value, float) and value > 3:
                lines.append(f"<b>{key}</b>: {self._format_time(value)}")
            else:
                lines.append(f"<b>{key}</b>: {value:,}")

        return "<br>".join(lines)