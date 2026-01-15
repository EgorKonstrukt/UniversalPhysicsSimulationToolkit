from dataclasses import dataclass

@dataclass
class PlotUIConfig:
    show_grid: bool = True
    line_width: int = 2

PLUGIN = Plugin(
    name="plot_ui",
    version="1.0.0",
    description="Interactive fractal plotter UI",
    dependency_specs={
        "core_math": ">=1.0.0",
        "fractal_renderer": ">=2.0.0"
    },
    config_class=PlotUIConfig,
    console_commands={
        "plot_fractal_at": lambda self, expr: self.plot_at(expr)
    }
)

class PluginImpl:
    def __init__(self, app):
        self.app = app
        self.renderer = app.plugin_manager.plugin_instances["fractal_renderer"]

    def plot_at(self, expr: str) -> str:
        x, y = map(float, expr.split(','))
        iterations = self.renderer.render_mandelbrot(x, y)
        return f"Point ({x:.4f}, {y:.4f}) → {iterations} iterations"