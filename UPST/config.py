import os
import pygame
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Tuple, List, Type, Optional, get_type_hints
import json

@dataclass
class MultithreadingConfig:
    gizmos_threaded: bool = True
    gizmos_max_workers: int = 1
    grid_threaded: bool = True
    grid_max_workers: int = 1
    pymunk_threaded: bool = True
    pymunk_threads: int = 1

@dataclass
class PhysicsConfig:
    collision_type_default: int = 1
    simulation_frequency: int = 100
    iterations: int = 512
    sleep_time_threshold: float = 0.5

@dataclass
class PhysicsDebugConfig:
    show_velocity_vectors: bool = True
    show_acceleration_vectors: bool = True
    show_forces: bool = True
    show_center_of_mass: bool = False
    show_angular_velocity: bool = True
    show_energy_meters: bool = False
    show_colliders: bool = False
    show_sleep_state: bool = False
    show_object_info: bool = False
    show_trails: bool = False
    show_momentum_vectors: bool = False
    show_angular_momentum: bool = True
    show_impulse_vectors: bool = False
    show_contact_forces: bool = False
    show_friction_forces: bool = True
    show_normal_forces: bool = True
    show_stress_visualization: bool = False
    show_deformation_energy: bool = False
    show_rotation_axes: bool = True
    show_velocity_profiles: bool = False
    show_phase_space: bool = False
    show_lagrangian_mechanics: bool = False
    show_hamiltonian_mechanics: bool = False
    show_conservation_laws: bool = False
    show_stability_analysis: bool = False
    show_resonance_analysis: bool = False
    vector_scale: float = 0.025
    text_scale: float = 1.0
    energy_bar_height: float = 20.0
    trail_length: int = 50
    phase_space_samples: int = 100
    show_constraints: bool = True
    constraint_color: Tuple[int, int, int] = (255, 200, 0)
    show_constraint_info: bool = True
    velocity_color: Tuple[int, int, int] = (0, 255, 0)
    acceleration_color: Tuple[int, int, int] = (255, 0, 0)
    force_color: Tuple[int, int, int] = (255, 255, 0)
    com_color: Tuple[int, int, int] = (255, 255, 255)
    angular_color: Tuple[int, int, int] = (255, 0, 255)
    kinetic_color: Tuple[int, int, int] = (0, 255, 255)
    potential_color: Tuple[int, int, int] = (0, 0, 255)
    momentum_color: Tuple[int, int, int] = (255, 128, 0)
    angular_momentum_color: Tuple[int, int, int] = (128, 255, 0)
    impulse_color: Tuple[int, int, int] = (255, 0, 128)
    contact_color: Tuple[int, int, int] = (255, 255, 255)
    friction_color: Tuple[int, int, int] = (128, 128, 255)
    normal_color: Tuple[int, int, int] = (255, 128, 128)
    stress_color: Tuple[int, int, int] = (255, 200, 200)
    collider_color: Tuple[int, int, int] = (128, 128, 128)
    sleep_color: Tuple[int, int, int] = (64, 64, 64)
    show_vector_labels: bool = True
    show_energy_values: bool = True
    show_coordinate_system: bool = True
    show_scientific_notation: bool = False
    precision_digits: int = 3
    info_panel_visible: bool = True
    info_panel_position: Tuple[int, int] = (10, 100)

@dataclass
class CameraConfig:
    smoothing: bool = True
    smoothness: float = 1.0
    shift_speed: float = 3.0
    acceleration_factor: float = 2.0
    friction: float = 0.9
    zoom_speed: float = 0.02
    pan_to_cursor_speed: float = 0.2
    mouse_friction: float = 0.80
    min_zoom_scale: float = 0.000001
    max_zoom_scale: float = 1000.0

@dataclass
class ProfilerConfig:
    update_delay: float = 0.016
    max_samples: int = 200
    normal_size: Tuple[int, int] = (800, 400)
    paused: bool = False
    auto_remove_threshold: float = 1.0

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
    is_visible:bool = True
    base_size: int = 100
    major_multiplier: int = 20
    min_pixel_spacing: int = 40
    max_pixel_spacing: int = 400
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
    snap_tolerance: int = 100
    snap_radius_pixels:int = 100
    snap_strength: float = 1.0
    max_lines: int = 1000
    skip_offscreen_lines: bool = True
    ruler_skip_factor = 2

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
class SnapshotConfig:
    save_object_positions: bool = True
    save_camera_position: bool = False
    max_snapshots: int = 50

@dataclass
class SaveLoadConfig:
    enable_compression = True
    compression_method = "lzma"  # "gzip", "lzma", or "none"

@dataclass
class TextureEditorConfig:
    max_undo_steps: int = 10
    bg_color: Tuple[int, int, int] = (30, 30, 30)
    filter_mode: int = 1
    tiling_mode: str = 'clamp'
    blend_mode: str = 'normal'
    preview_quality: float = 1.0
    auto_save_interval: float = 5.0

@dataclass
class AppConfig:
    config_default_path: str = "config.json"
    screen_width: int = 1920
    screen_height: int = 1080
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
    _subconfigs: Dict[str, Type] = {}

    # === Типовые аннотации для автокомплита ===
    app: "AppConfig"
    physics: "PhysicsConfig"
    physics_debug: "PhysicsDebugConfig"
    camera: "CameraConfig"
    profiler: "ProfilerConfig"
    synthesizer: "SynthesizerConfig"
    grid: "GridConfig"
    world: "WorldConfig"
    input: "InputConfig"
    debug: "DebugConfig"
    multithreading: "MultithreadingConfig"
    snapshot: "SnapshotConfig"
    texture_editor: "TextureEditorConfig"
    save_load: "SaveLoadConfig"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._subconfigs = {}

    @classmethod
    def register(cls, name: str, config_type: Type):
        cls._subconfigs[name] = config_type

    def __init__(self, **kwargs):
        for name, config_type in self._subconfigs.items():
            instance = kwargs.get(name) or config_type()
            setattr(self, name, instance)
        self._app_ref = getattr(self, 'app', None)

    @property
    def _default_path(self) -> str:
        return self.app.config_path if hasattr(self, 'app') and hasattr(self.app, 'config_path') else "config.json"

    @classmethod
    def load_from_file(cls, path: Optional[str] = None) -> "Config":
        effective_path = path or "config.json"
        data = {}
        if os.path.exists(effective_path):
            try:
                with open(effective_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                    else:
                        print(f"Warning: {effective_path} is empty. Using default config.")
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read {effective_path} ({e}). Using default config.")
        else:
            print(f"Info: {effective_path} not found. Creating default config.")
        instance = cls.from_dict(data)
        instance.save_to_file(effective_path)
        return instance

    def save_to_file(self, path: Optional[str] = None) -> None:
        effective_path = path or self._default_path
        dir_path = os.path.dirname(effective_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(effective_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)

    def save(self) -> None:
        self.save_to_file()

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for name in self._subconfigs:
            obj = getattr(self, name)
            d = asdict(obj)
            result[name] = self._custom_to_dict(obj, d)
        return result

    def _custom_to_dict(self, obj: Any, d: Dict) -> Any:
        if hasattr(obj, '_to_dict_custom'):
            return obj._to_dict_custom(d)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        kwargs = {}
        for name, config_type in cls._subconfigs.items():
            subdata = data.get(name, {})
            if hasattr(config_type, '_from_dict_custom'):
                kwargs[name] = config_type._from_dict_custom(subdata)
            else:
                kwargs[name] = config_type(**subdata)
        return cls(**kwargs)

Config.register("app", AppConfig)
Config.register("physics", PhysicsConfig)
Config.register("physics_debug", PhysicsDebugConfig)
Config.register("camera", CameraConfig)
Config.register("profiler", ProfilerConfig)
Config.register("synthesizer", SynthesizerConfig)
Config.register("grid", GridConfig)
Config.register("world", WorldConfig)
Config.register("input", InputConfig)
Config.register("debug", DebugConfig)
Config.register("multithreading", MultithreadingConfig)
Config.register("snapshot", SnapshotConfig)
Config.register("texture_editor", TextureEditorConfig)
Config.register("save_load", SaveLoadConfig)

def grid_to_dict_custom(self, d: Dict) -> Dict:
    d["default_colors"] = asdict(self.default_colors)
    d["theme_colors"] = {k: asdict(v) for k, v in self.theme_colors.items()}
    return d

def grid_from_dict_custom(cls, d: Dict) -> "GridConfig":
    d.setdefault("default_colors", {})
    d.setdefault("theme_colors", {})
    d["default_colors"] = GridColorScheme(**d["default_colors"])
    d["theme_colors"] = {k: GridColorScheme(**v) for k, v in d["theme_colors"].items()}
    return cls(**d)

def world_to_dict_custom(self, d: Dict) -> Dict:
    d["themes"] = {k: asdict(v) for k, v in self.themes.items()}
    return d

def world_from_dict_custom(cls, d: Dict) -> "WorldConfig":
    default_themes = {
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
    }
    loaded_themes = d.get("themes", {})
    merged_themes = {}
    for name, default_theme in default_themes.items():
        if name in loaded_themes:
            theme_data = loaded_themes[name]
            # Recreate tuples from lists (JSON doesn't support tuples)
            bg = tuple(theme_data.get("background_color", default_theme.background_color))
            shape = tuple(tuple(pair) for pair in theme_data.get("shape_color_range", default_theme.shape_color_range))
            plat = tuple(theme_data.get("platform_color", default_theme.platform_color))
            merged_themes[name] = WorldTheme(bg, shape, plat)
        else:
            merged_themes[name] = default_theme
    current_theme = d.get("current_theme", "Classic")
    return cls(themes=merged_themes, current_theme=current_theme)

GridConfig._to_dict_custom = grid_to_dict_custom
GridConfig._from_dict_custom = classmethod(grid_from_dict_custom)
WorldConfig._to_dict_custom = world_to_dict_custom
WorldConfig._from_dict_custom = classmethod(world_from_dict_custom)

@property
def background_color(self) -> Tuple[int, int, int]:
    theme = self.world.themes.get(self.world.current_theme)
    return theme.background_color if theme else self.app.background_color

@property
def app(self): return self._app_ref

def get_grid_colors(self, theme_name: str) -> GridColorScheme:
    return self.grid.theme_colors.get(theme_name, self.grid.default_colors)

def get_optimal_subdivision(self, pixel_spacing: float) -> float:
    if pixel_spacing < self.grid.min_pixel_spacing:
        return 10.0
    elif pixel_spacing > self.grid.max_pixel_spacing:
        return 0.1
    else:
        return 1.0

Config.background_color = background_color
Config.get_grid_colors = get_grid_colors
Config.get_optimal_subdivision = get_optimal_subdivision

config = Config.load_from_file()
