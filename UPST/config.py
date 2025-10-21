import os
import pygame

class Config:
    """
    Configuration and constants for the application.
    """
    SCREEN_WIDTH, SCREEN_HEIGHT = 2560, 1400
    FULLSCREEN = False
    USE_SYSTEM_DPI = False
    VERSION = "Universal Physics Simulation Toolkit"
    CREATE_BASE_WORLD = True

    DEBUG_GIZMOS = True

    ##--------------PHYSICS--------------------
    PHYSICS_COLLISION_TYPE_DEFAULT = 1
    PHYSICS_SIMULATION_FREQUENCY = 100
    PHYSICS_ITERATIONS = 512
    PHYSICS_SLEEP_TIME_TRESHOLD = 0.5
    PHYSICS_PYMUNK_THREADED = True
    PHYSICS_PYMUNK_THREADS = 2
    ##------------------------------------------

    KEY_HOLD_TIME = 1000

    KEY_SPAWN = pygame.K_f
    KEY_UNDO = pygame.K_z
    KEY_ESCAPE = pygame.K_ESCAPE
    KEY_TOGGLE_PAUSE = pygame.K_SPACE
    KEY_GUIDE = pygame.K_l
    KEY_STATIC_LINE = pygame.K_b
    KEY_FORCE_FIELD = pygame.K_n
    KEY_SCREENSHOT = pygame.K_p
    KEY_DELETE = pygame.K_DELETE

    CLOCK_TICKRATE = 100
    BACKGROUND_COLOR = (30, 30, 30)

    ##---------------CAMERA---------------------
    CAMERA_SMOOTHING = True
    CAMERA_SMOOTHNESS = 1
    CAMERA_SHIFT_SPEED = 2
    CAMERA_ACCELERATION_FACTOR = 2
    CAMERA_FRICTION = 0.9
    CAMERA_ZOOM_SPEED = 0.01
    CAMERA_PAN_TO_CURSOR_SPEED = 0.1
    CAMERA_MOUSE_FRICTION = 0.75
    ##------------------------------------------

    ##---------------IN-GAME-PROFILER---------------------
    PROFILER_UPDATE_DELAY = 0.016 #ms
    PROFILER_MAX_SAMPLES = 200
    PROFILER_NORMAL_SIZE = (800, 400)
    PROFILER_PAUSED = False
    ##------------------------------------------

    ##---------------SYNTHESIZER---------------------
    SYNTHESIZER_SAMPLE_RATE = 44100
    SYNTHESIZER_BUFFER_SIZE = 4096
    SYNTHESIZER_VOLUME = 0.5
    ##------------------------------------------

    DEBUG_DRAW_COLLISION_POINTS = True
    DEBUG_DRAW_CONSTRAINTS = True
    DEBUG_DRAW_BODY_OUTLINES = True
    DEBUG_DRAW_CENTER_OF_MASS = True

    GRID_ENABLED_BY_DEFAULT = True

    GRID_BASE_SIZE = 100  # Base grid size in world units (1 meter = 100 units)
    GRID_MAJOR_MULTIPLIER = 10  # Every Nth line is major
    GRID_MIN_PIXEL_SPACING = 20  # Minimum pixels between grid lines
    GRID_MAX_PIXEL_SPACING = 200  # Maximum pixels between grid lines

    GRID_MINOR_LINE_THICKNESS = 1
    GRID_MAJOR_LINE_THICKNESS = 2
    GRID_ORIGIN_LINE_THICKNESS = 3

    GRID_DEFAULT_COLORS = {
        'major': (100, 100, 100, 255),  # Major grid lines
        'minor': (60, 60, 60, 255),  # Minor grid lines
        'origin': (120, 120, 120, 255),  # Origin lines (x=0, y=0)
    }

    GRID_THEME_COLORS = {
        'light': {
            'major': (100, 100, 100, 255),
            'minor': (60, 60, 60, 255),
            'origin': (140, 140, 140, 255),
        },
        'dark': {
            'major': (80, 80, 80, 255),
            'minor': (40, 40, 40, 255),
            'origin': (120, 120, 120, 255),
        },
        'blue': {
            'major': (100, 120, 140, 255),
            'minor': (60, 80, 100, 255),
            'origin': (140, 160, 180, 255),
        },
        'green': {
            'major': (80, 120, 80, 255),
            'minor': (40, 80, 40, 255),
            'origin': (120, 160, 120, 255),
        }
    }

    GRID_SUBDIVISION_LEVELS = [
        0.1,  # Very zoomed in
        1,  # Normal
        10,  # Zoomed out
        100,  # Very zoomed out
        1000,  # Extremely zoomed out
    ]

    # Alpha transparency for grid lines at different zoom levels
    GRID_ALPHA_FADE_ENABLED = True
    GRID_MIN_ALPHA = 30  # Minimum alpha when fading
    GRID_MAX_ALPHA = 255  # Maximum alpha

    # Grid snapping settings
    GRID_SNAP_TO_GRID_ENABLED = False  # Can be toggled by user
    GRID_SNAP_TOLERANCE = 5  # Pixels tolerance for snapping

    # Performance settings
    GRID_MAX_LINES = 1000  # Maximum number of grid lines to draw
    GRID_SKIP_OFFSCREEN_LINES = True  # Skip drawing lines that are off-screen

    @classmethod
    def get_theme_colors(cls, theme_name):
        """Get grid colors for a specific theme"""
        if theme_name in cls.GRID_THEME_COLORS:
            return cls.GRID_THEME_COLORS[theme_name]
        else:
            # Fallback to default colors
            return cls.GRID_DEFAULT_COLORS

    @classmethod
    def get_optimal_subdivision(cls, pixel_spacing):
        """Get optimal subdivision level based on pixel spacing"""
        if pixel_spacing < cls.GRID_MIN_PIXEL_SPACING:
            return 10  # Make grid less dense
        elif pixel_spacing > cls.GRID_MAX_PIXEL_SPACING:
            return 0.1  # Make grid more dense
        else:
            return 1  # Use base subdivision

    CURRENT_THEME = "Classic"

    WORLD_THEMES = {
        "Classic": {
            "background_color": (30, 30, 30),
            "shape_color_range": ((50, 255), (50, 255), (50, 255)),
            "platform_color": (100, 100, 100, 255),
        },
        "Desert": {
            "background_color": (80, 60, 20),
            "shape_color_range": ((200, 255), (150, 200), (50, 100)),
            "platform_color": (210, 180, 140, 255),
        },
        "Ice": {
            "background_color": (120, 120, 155),
            "shape_color_range": ((150, 200), (180, 230), (230, 255)),
            "platform_color": (100, 170, 220, 255),
        },
        "Night": {
            "background_color": (10, 10, 30),
            "shape_color_range": ((20, 80), (20, 80), (60, 150)),
            "platform_color": (40, 40, 60, 255),
        },
        "Forest": {
            "background_color": (34, 45, 28),
            "shape_color_range": ((30, 100), (100, 200), (30, 100)),
            "platform_color": (60, 120, 60, 255),
        },
        "Lava": {
            "background_color": (40, 0, 0),
            "shape_color_range": ((100, 255), (0, 40), (0, 10)),
            "platform_color": (120, 30, 0, 255),
        },
        "Ocean": {
            "background_color": (0, 40, 80),
            "shape_color_range": ((0, 100), (100, 200), (150, 255)),
            "platform_color": (0, 90, 150, 255),
        },
        "SciFi": {
            "background_color": (10, 10, 10),
            "shape_color_range": ((50, 100), (200, 255), (200, 255)),
            "platform_color": (60, 255, 180, 255),
        },
        "Candy": {
            "background_color": (255, 230, 255),
            "shape_color_range": ((200, 255), (100, 200), (200, 255)),
            "platform_color": (255, 180, 220, 255),
        },
        "Void": {
            "background_color": (0, 0, 0),
            "shape_color_range": ((0, 20), (0, 20), (0, 20)),
            "platform_color": (20, 20, 20, 255),
        },
        "Black&White": {
            "background_color": (255, 255, 255),
            "shape_color_range": ((0, 0), (0, 0), (0, 0)),
            "platform_color": (0, 0, 0, 255),
        },
    }

    GUIDE_TEXT = (
        "F: Spawn object"
        "\nclamped F: Auto spawn objects"
        "\nB: Make border"
        "\nN: Enable gravity field"
        "\nSPACE: Pause physic"
        "\nArrow keys: camera position"
        "\nA/Z: Camera zoom"
        "\nS/X: Camera roll"
        "\nP: Screenshot"
        "\nShift: Move faster"
    )

    HELP_CONSOLE_TEXT = (
        "help: display this"
        "\nexec: execute the Python commands contained in the string."
        "\neval: executes the expression string and returns the result."
        "\npython: open a new interactive python thread"
        "\nclear: clears the output console"
    )

    FRICTION_DICT = [
        ("Aluminium", 0.61), ("Steel", 0.53), ("Brass", 0.51),
        ("Cast iron", 1.05), ("Cast iron", 0.85), ("Concrete (wet)", 0.30),
        ("Concrete (dry)", 1.0), ("Concrete", 0.62), ("Copper", 0.68),
        ("Glass", 0.94), ("Metal", 0.5), ("Polyethene", 0.2),
        ("Steel", 0.80), ("Steel", 0.04), ("Teflon (PTFE)", 0.04),
        ("Wood", 0.4),
    ]