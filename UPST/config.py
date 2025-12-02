import os
import random

import pygame
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Tuple, List, Type, Optional, get_type_hints
import json

@dataclass
class OpticsConfig:
    TRANSPARENCY = 0.75
    N_SAMPLES = 30
    MAX_WL = 750
    MIN_WL = 380
    C_A = 1.514
    C_B = 0.0042
    EPS = 1e-6
    ABSORB_THR = 1e-3
    ALPHA_EPS = 1e-6

@dataclass
class ContextMenuConfig:
    button_height = 30
    button_spacing = -4
    hover_delay = 0.25

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
    PTM_RATIO: float = 30.0
    collision_type_default: int = 1
    simulation_frequency: int = 100
    iterations: int = 512
    sleep_time_threshold: float = 0.5
    air_friction_linear = 0.0100
    air_friction_quadratic = 0.00100
    air_friction_multiplier = 1.0
    air_density = 1.225

@dataclass
class PhysicsDebugConfig:
    smoothing = True
    smoothing_window = 5  # Глубина буфера (рекомендуется 3–5)
    show_velocity_vectors: bool = True
    show_acceleration_vectors: bool = True
    show_forces: bool = True
    show_center_of_mass: bool = False
    show_angular_velocity: bool = True
    show_energy_meters: bool = False
    show_colliders: bool = False
    show_sleep_state: bool = False
    show_trails: bool = False
    show_angular_momentum: bool = True
    show_rotation_axes: bool = True
    vector_scale: float = 0.025
    text_scale: float = 1.0
    energy_bar_height: float = 20.0
    trail_length: int = 50
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
    collider_color: Tuple[int, int, int] = (128, 128, 128)
    sleep_color: Tuple[int, int, int] = (64, 64, 64)
    show_vector_labels: bool = True
    show_energy_values: bool = True
    precision_digits: int = 3
    info_panel_position: Tuple[int, int] = (10, 100)

@dataclass
class CameraConfig:
    smoothing: bool = True
    smoothness: float = 1.0
    shift_speed: float = 3.0
    acceleration_factor: float = 2.0
    friction: float = 0.5
    zoom_speed: float = 0.035
    pan_to_cursor_speed: float = 0.2
    mouse_friction: float = 0.90
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
    autosave_path: str = "autosave.space"
    screen_width: int = 1920
    screen_height: int = 1080
    fullscreen: bool = False
    use_system_dpi: bool = False
    version: str = "Universal Physics Simulation Toolkit"
    create_base_world: bool = True
    clock_tickrate: int = 1000
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

# ---- palette utilities ----
def _rand_in_range(r):
    return random.randint(int(r[0]), int(r[1]))

def sample_color_from_def(pdef: Dict[str, Any]) -> Tuple[int,int,int,int]:
    mode = pdef.get("mode","range")
    if mode == "preset":
        cols = pdef.get("colors",[])
        if not cols: return (200,200,200,255)
        c = random.choice(cols)
        return tuple(int(x) for x in (*c, 255)) if len(c)==3 else tuple(int(x) for x in c)
    # range mode: expects {"r":(min,max),"g":(...),"b":(...),"mix_with_white":float optional}
    r = _rand_in_range(pdef.get("r",(0,255)))
    g = _rand_in_range(pdef.get("g",(0,255)))
    b = _rand_in_range(pdef.get("b",(0,255)))
    a = int(pdef.get("a",255))
    if pdef.get("mix_with_white"):
        mix = float(pdef["mix_with_white"])
        r = int(r + (255 - r) * mix)
        g = int(g + (255 - g) * mix)
        b = int(b + (255 - b) * mix)
    return (r,g,b,a)

@dataclass
class WorldTheme:
    background_color: Tuple[int,int,int]
    shape_color_range: Tuple[Tuple[int,int], Tuple[int,int], Tuple[int,int]]
    platform_color: Tuple[int,int,int,int]
    palettes: Dict[str, Dict[str,Any]] = field(default_factory=dict)
    default_palette: str = "Default"

    def get_palette_def(self, name: Optional[str] = None) -> Dict[str,Any]:
        nm = name or self.default_palette
        if nm in self.palettes: return self.palettes[nm]
        r_rng, g_rng, b_rng = self.shape_color_range
        return {"mode":"range","r":tuple(r_rng),"g":tuple(g_rng),"b":tuple(b_rng),"a":255}

@dataclass
class WorldConfig:
    themes: Dict[str, WorldTheme] = field(default_factory=lambda: {
        "Default": WorldTheme((30,30,30), ((50,255),(50,255),(50,255)), (100,100,100,255),
            palettes={"Default":{"mode":"range","r":(50,200),"g":(50,200),"b":(50,200)}}, default_palette="Default"),
        "Autumn": WorldTheme((80,60,20), ((200,255),(150,200),(50,100)), (210,180,140,255),
            palettes={"Default":{"mode":"range","r":(180,240),"g":(140,200),"b":(40,120)}}, default_palette="Default"),
        "Black": WorldTheme((0,0,0), ((0,20),(0,20),(0,20)), (20,20,20,255),
            palettes={"Default":{"mode":"range","r":(0,20),"g":(0,20),"b":(0,20)}}, default_palette="Default"),
        "Blueprint": WorldTheme((0,20,80), ((150,255),(150,255),(150,255)), (0,90,150,255),
            palettes={"Default":{"mode":"range","r":(230,230),"g":(230,230),"b":(230,230)}}, default_palette="Default"),
        "Chalkboard": WorldTheme((34,45,28), ((170,200),(170,200),(170,200)), (60,120,60,255),
            palettes={"Default":{"mode":"range","r":(30,100),"g":(80,200),"b":(30,100)}}, default_palette="Default"),
        "Dark": WorldTheme((10,10,30), ((20,80),(20,80),(60,150)), (40,40,60,255),
            palettes={"Default":{"mode":"range","r":(20,80),"g":(20,80),"b":(60,150)}}, default_palette="Default"),
        "Greyscale": WorldTheme((255,255,255), ((0,0),(0,0),(0,0)), (0,0,0,255),
            palettes={"Default":{"mode":"preset","colors":[(0,0,0),(50,50,50),(200,200,200),(255,255,255)]}}, default_palette="Default"),
        "Ice": WorldTheme((120,120,155), ((150,200),(180,230),(230,255)), (100,170,220,255),
            palettes={"Default":{"mode":"range","r":(150,200),"g":(180,230),"b":(230,255)}}, default_palette="Default"),
        "Light grey": WorldTheme((255,255,255), ((0,0),(0,0),(0,0)), (0,0,0,255),
            palettes={"Default":{"mode":"preset","colors":[(0,0,0),(50,50,50),(200,200,200),(255,255,255)]}}, default_palette="Default"),
        "Optics": WorldTheme((10,10,10), ((50,100),(200,255),(200,255)), (60,255,180,255),
            palettes={"Default":{"mode":"range","r":(40,80),"g":(200,255),"b":(180,255)}}, default_palette="Default"),
        "Pastel": WorldTheme((255,230,255), ((200,255),(100,200),(200,255)), (255,180,220,255),
            palettes={"Default":{"mode":"range","r":(200,255),"g":(100,200),"b":(200,255)}}, default_palette="Default"),
        "Sunset": WorldTheme((40,0,0), ((100,255),(0,40),(0,10)), (120,30,0,255),
            palettes={"Default":{"mode":"range","r":(100,255),"g":(0,60),"b":(0,30)}}, default_palette="Default"),
        "Sweet": WorldTheme((30,30,30), ((50,255),(50,255),(50,255)), (100,100,100,255),
            palettes={"Default":{"mode":"range","r":(50,200),"g":(50,200),"b":(50,200)}}, default_palette="Default"),
        "White": WorldTheme((255,255,255), ((0,0),(0,0),(0,0)), (0,0,0,255),
            palettes={"Default":{"mode":"preset","colors":[(0,0,0),(50,50,50),(200,200,200),(255,255,255)]}}, default_palette="Default"),
        "X-ray": WorldTheme((0,0,0), ((0,20),(0,20),(0,20)), (20,20,20,255),
            palettes={"Default":{"mode":"range","r":(0,20),"g":(0,20),"b":(0,20)}}, default_palette="Default"),
    })
    current_theme: str = "Default"
    current_palette: str = "Default"

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
    context_menu: "ContextMenuConfig"
    optics: "OpticsConfig"

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
Config.register("context_menu", ContextMenuConfig)
Config.register("optics", OpticsConfig)

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
    d["themes"] = {}
    for k,v in self.themes.items():
        vd = asdict(v)
        d["themes"][k] = vd
    d["current_theme"] = self.current_theme
    d["current_palette"] = self.current_palette
    return d

def world_from_dict_custom(cls, d: Dict) -> "WorldConfig":
    default = WorldConfig()
    loaded = d.get("themes", {})
    merged = {}
    for name, def_theme in default.themes.items():
        if name in loaded:
            td = loaded[name]
            bg = tuple(td.get("background_color", def_theme.background_color))
            shape = tuple(tuple(pair) for pair in td.get("shape_color_range", def_theme.shape_color_range))
            plat = tuple(td.get("platform_color", def_theme.platform_color))
            pals = td.get("palettes", def_theme.palettes)
            default_pal = td.get("default_palette", def_theme.default_palette)
            merged[name] = WorldTheme(bg, shape, plat, palettes=pals, default_palette=default_pal)
        else:
            merged[name] = def_theme
    cur_t = d.get("current_theme", default.current_theme)
    cur_p = d.get("current_palette", default.current_palette)
    return cls(themes=merged, current_theme=cur_t, current_palette=cur_p)

GridConfig._to_dict_custom = grid_to_dict_custom
GridConfig._from_dict_custom = classmethod(grid_from_dict_custom)

WorldConfig._to_dict_custom = world_to_dict_custom
WorldConfig._from_dict_custom = classmethod(world_from_dict_custom)

def get_theme_and_palette(cfg, theme_name=None, palette_name=None):
    th = cfg.world.themes.get(theme_name or cfg.world.current_theme, None)
    if not th: th = next(iter(cfg.world.themes.values()))
    pal = palette_name or cfg.world.current_palette or th.default_palette
    return th, pal

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
