from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class CoreMathConfig:
    precision: int = 8
    use_numba: bool = False

PLUGIN = Plugin(
    name="core_math",
    version="1.2.0",
    description="Core math utilities with JIT support",
    author="Zarrakun",
    icon_path="icon.png",
    dependency_specs={},
    config_class=CoreMathConfig,
    console_commands={
        "mandelbrot_iter": lambda self, expr: self.mandelbrot_iter(expr)
    }
)

class PluginImpl:
    def __init__(self, app):
        self.app = app
        self.cache = {}

    def mandelbrot_iter(self, expr: str) -> int:
        import math
        x, y, max_iter = map(float, expr.split(','))
        c = complex(x, y)
        z = 0j
        for i in range(int(max_iter)):
            if abs(z) > 2:
                return i
            z = z * z + c
        return int(max_iter)