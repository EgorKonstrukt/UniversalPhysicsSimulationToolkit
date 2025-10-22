import os
import pygame
from dataclasses import dataclass, field, asdict
from typing import Tuple, Dict, List, Literal, Optional, Any
import json

@dataclass
class PhysicsConfig:
    collision_type_default: int = 1
    simulation_frequency: int = 100
    iterations: int = 512
    sleep_time_threshold: float = 0.5
    pymunk_threaded: bool = True
    pymunk_threads: int = 2

@dataclass
class CameraConfig:
    smoothing: bool = True
    smoothness: float = 1.0
    shift_speed: float = 2.0
    acceleration_factor: float = 2.0
    friction: float = 0.9
    zoom_speed: float = 0.01
    pan_to_cursor_speed: float = 0.1
    mouse_friction: float = 0.75
    min_zoom_scale: float = 0.000001
    max_zoom_scale: float = 1000.0

@dataclass
class ProfilerConfig:
    update_delay: float = 0.016
    max_samples: int = 200
    normal_size: Tuple[int, int] = (800, 400)
    paused: bool = False

@dataclass
class SynthesizerConfig:
    sample_rate: int = 44100
    buffer_size: int = 4096
    volume: float = 0.5

@dataclass
class GridColorScheme:
    major: Tuple[int, int, int, int] = (100, 100, 100, 255)
    minor: Tuple[int, int, int, int] = (60, 60, 60, 255)
    origin: Tuple[int, int, int, int] = (120, 120, 120, 255)

@dataclass
class GridConfig:
    enabled_by_default: bool = True
    base_size: int = 100
    major_multiplier: int = 10
    min_pixel_spacing: int = 20
    max_pixel_spacing: int = 200
    minor_line_thickness: int = 1
    major_line_thickness: int = 2
    origin_line_thickness: int = 3
    default_colors: GridColorScheme = field(default_factory=lambda: GridColorScheme())
    theme_colors: Dict[str, GridColorScheme] = field(default_factory=lambda: {
        "light": GridColorScheme((100,100,100,255), (60,60,60,255), (140,140,140,255)),
        "dark": GridColorScheme((80,80,80,255), (40,40,40,255), (120,120,120,255)),
        "blue": GridColorScheme((100,120,140,255), (60,80,100,255), (140,160,180,255)),
        "green": GridColorScheme((80,120,80,255), (40,80,40,255), (120,160,120,255)),
    })
    subdivision_levels: List[float] = field(default_factory=lambda: [0.1, 1.0, 10.0, 100.0, 1000.0])
    alpha_fade_enabled: bool = True
    min_alpha: int = 30
    max_alpha: int = 255
    snap_to_grid_enabled: bool = False
    snap_tolerance: int = 5
    max_lines: int = 1000
    skip_offscreen_lines: bool = True

@dataclass
class WorldTheme:
    background_color: Tuple[int, int, int]
    shape_color_range: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]
    platform_color: Tuple[int, int, int, int]

@dataclass
class WorldConfig:
    themes: Dict[str, WorldTheme] = field(default_factory=lambda: {
        "Classic": WorldTheme((30,30,30), ((50,255),(50,255),(50,255)), (100,100,100,255)),
        "Desert": WorldTheme((80,60,20), ((200,255),(150,200),(50,100)), (210,180,140,255)),
        "Ice": WorldTheme((120,120,155), ((150,200),(180,230),(230,255)), (100,170,220,255)),
        "Night": WorldTheme((10,10,30), ((20,80),(20,80),(60,150)), (40,40,60,255)),
        "Forest": WorldTheme((34,45,28), ((30,100),(100,200),(30,100)), (60,120,60,255)),
        "Lava": WorldTheme((40,0,0), ((100,255),(0,40),(0,10)), (120,30,0,255)),
        "Ocean": WorldTheme((0,40,80), ((0,100),(100,200),(150,255)), (0,90,150,255)),
        "SciFi": WorldTheme((10,10,10), ((50,100),(200,255),(200,255)), (60,255,180,255)),
        "Candy": WorldTheme((255,230,255), ((200,255),(100,200),(200,255)), (255,180,220,255)),
        "Void": WorldTheme((0,0,0), ((0,20),(0,20),(0,20)), (20,20,20,255)),
        "Black&White": WorldTheme((255,255,255), ((0,0),(0,0),(0,0)), (0,0,0,255)),
    })
    current_theme: str = "Classic"

@dataclass
class InputConfig:
    hold_time_ms: int = 1000
    spawn: int = pygame.K_f
    undo: int = pygame.K_z
    escape: int = pygame.K_ESCAPE
    toggle_pause: int = pygame.K_SPACE
    guide: int = pygame.K_l
    static_line: int = pygame.K_b
    force_field: int = pygame.K_n
    screenshot: int = pygame.K_p
    delete: int = pygame.K_DELETE

@dataclass
class DebugConfig:
    gizmos: bool = True
    draw_collision_points: bool = True
    draw_constraints: bool = True
    draw_body_outlines: bool = True
    draw_center_of_mass: bool = True
    show_performance: bool = True
    show_physics_debug: bool = True
    show_camera_debug: bool = True
    show_snapshots_debug: bool = True
    show_console: bool = False

@dataclass
class AppConfig:
    screen_width: int = 2560
    screen_height: int = 1400
    fullscreen: bool = False
    use_system_dpi: bool = False
    version: str = "Universal Physics Simulation Toolkit"
    create_base_world: bool = True
    clock_tickrate: int = 100
    background_color: Tuple[int, int, int] = (30, 30, 30)
    guide_text: str = (
        "F: Spawn object\n"
        "clamped F: Auto spawn objects\n"
        "B: Make border\n"
        "N: Enable gravity field\n"
        "SPACE: Pause physic\n"
        "Arrow keys: camera position\n"
        "A/Z: Camera zoom\n"
        "S/X: Camera roll\n"
        "P: Screenshot\n"
        "Shift: Move faster"
    )
    help_console_text: str = (
        "help: display this\n"
        "exec: execute the Python commands contained in the string.\n"
        "eval: executes the expression string and returns the result.\n"
        "python: open a new interactive python thread\n"
        "clear: clears the output console"
    )
    friction_materials: List[Tuple[str, float]] = field(default_factory=lambda: [
        ("Aluminium", 0.61), ("Steel", 0.53), ("Brass", 0.51),
        ("Cast iron", 1.05), ("Cast iron", 0.85), ("Concrete (wet)", 0.30),
        ("Concrete (dry)", 1.0), ("Concrete", 0.62), ("Copper", 0.68),
        ("Glass", 0.94), ("Metal", 0.5), ("Polyethene", 0.2), ("Teflon (PTFE)", 0.04),
        ("Wood", 0.4),
    ])

class Config:
    _default_path = "config.json"

    def __init__(self,
                 app: AppConfig = None,
                 physics: PhysicsConfig = None,
                 camera: CameraConfig = None,
                 profiler: ProfilerConfig = None,
                 synthesizer: SynthesizerConfig = None,
                 grid: GridConfig = None,
                 world: WorldConfig = None,
                 input: InputConfig = None,
                 debug: DebugConfig = None):
        self.app = app or AppConfig()
        self.physics = physics or PhysicsConfig()
        self.camera = camera or CameraConfig()
        self.profiler = profiler or ProfilerConfig()
        self.synthesizer = synthesizer or SynthesizerConfig()
        self.grid = grid or GridConfig()
        self.world = world or WorldConfig()
        self.input = input or InputConfig()
        self.debug = debug or DebugConfig()

    @classmethod
    def load_from_file(cls, path: str = None) -> "Config":
        path = path or cls._default_path
        if not os.path.exists(path):
            default_instance = cls()
            default_instance.save_to_file(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_file(self, path: str = None) -> None:
        path = path or self._default_path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)

    def save(self) -> None:
        self.save_to_file()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app": asdict(self.app),
            "physics": asdict(self.physics),
            "camera": asdict(self.camera),
            "profiler": asdict(self.profiler),
            "synthesizer": asdict(self.synthesizer),
            "grid": self._grid_to_dict(),
            "world": self._world_to_dict(),
            "input": asdict(self.input),
            "debug": asdict(self.debug),
        }

    def _grid_to_dict(self) -> Dict[str, Any]:
        d = asdict(self.grid)
        d["default_colors"] = asdict(self.grid.default_colors)
        d["theme_colors"] = {k: asdict(v) for k, v in self.grid.theme_colors.items()}
        return d

    def _world_to_dict(self) -> Dict[str, Any]:
        d = asdict(self.world)
        d["themes"] = {k: asdict(v) for k, v in self.world.themes.items()}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        def _restore_grid(d: Dict) -> GridConfig:
            d["default_colors"] = GridColorScheme(**d["default_colors"])
            d["theme_colors"] = {k: GridColorScheme(**v) for k, v in d["theme_colors"].items()}
            return GridConfig(**d)
        def _restore_world(d: Dict) -> WorldConfig:
            d["themes"] = {k: WorldTheme(**v) for k, v in d["themes"].items()}
            return WorldConfig(**d)
        return cls(
            app=AppConfig(**data["app"]),
            physics=PhysicsConfig(**data["physics"]),
            camera=CameraConfig(**data["camera"]),
            profiler=ProfilerConfig(**data["profiler"]),
            synthesizer=SynthesizerConfig(**data["synthesizer"]),
            grid=_restore_grid(data["grid"]),
            world=_restore_world(data["world"]),
            input=InputConfig(**data["input"]),
            debug=DebugConfig(**data["debug"]),
        )

    @property
    def background_color(self) -> Tuple[int, int, int]:
        theme = self.world.themes.get(self.world.current_theme)
        return theme.background_color if theme else self.app.background_color

    def get_grid_colors(self, theme_name: str) -> GridColorScheme:
        return self.grid.theme_colors.get(theme_name, self.grid.default_colors)

    def get_optimal_subdivision(self, pixel_spacing: float) -> float:
        if pixel_spacing < self.grid.min_pixel_spacing:
            return 10.0
        elif pixel_spacing > self.grid.max_pixel_spacing:
            return 0.1
        else:
            return 1.0

config = Config()
