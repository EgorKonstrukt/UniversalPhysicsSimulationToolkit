from dataclasses import dataclass
from typing import Tuple

@dataclass
class FractalConfig:
    default_depth: int = 64
    color_palette: Tuple[int, int, int] = (0, 128, 255)

PLUGIN = Plugin(
    name="fractal_renderer",
    version="2.0.1",
    description="High-performance fractal rendering using core_math",
    dependency_specs={"core_math": ">=1.1.0"},
    config_class=FractalConfig
)

class PluginImpl:
    def __init__(self, app):
        self.app = app
        # Используем функционал из core_math
        self.math_plugin = app.plugin_manager.plugin_instances["core_math"]

    def render_mandelbrot(self, x: float, y: float) -> int:
        depth = self.app.config.fractal_renderer.default_depth
        return self.math_plugin.mandelbrot_iter(f"{x},{y},{depth}")