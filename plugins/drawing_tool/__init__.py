from __future__ import annotations

from pathlib import Path
import pygame
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING, Dict, Any
from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.modules.undo_redo_manager import UndoRedoManager
from UPST.tools.base_tool import BaseTool

try:
    from plugin_base import Plugin
except ImportError:
    pass

@dataclass
class DrawingToolConfig:
    enabled: bool = True
    brush_size: float = 2.0
    brush_color: tuple[int, int, int] = (255, 255, 255)
    opacity: float = 1.0
    smoothing: bool = True

PLUGIN_DIR = Path(__file__).parent

class DrawingTool(BaseTool):
    name = "drawing"
    category = "Drawing"
    icon_path = None
    tooltip = "Freehand drawing tool"

    def __init__(self, app):
        super().__init__(app)
        self.active = False
        self.brush_size = getattr(config.drawing_tool, "brush_size", 2.0)
        self.brush_color = getattr(config.drawing_tool, "brush_color", (255, 255, 255))
        self.points = []
        self.undo_redo_manager = self.app.undo_redo_manager

    def activate(self):
        self.active = True
        self.points.clear()

    def deactivate(self):
        self.active = False
        self.points.clear()

    def handle_event(self, event, world_pos) -> bool:
        if not self.active:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.points = [world_pos]
            return True
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            self.points.append(world_pos)
            self._render_stroke_segment()
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if len(self.points) > 1:
                self.undo_redo_manager.take_snapshot()
            self.points.clear()
            return True
        return False

    def _render_stroke_segment(self):
        if len(self.points) < 2:
            return
        manager = self.app.plugin_manager.plugin_instances.get("drawing_tool")
        if not manager or not hasattr(manager, "manager") or not manager.manager:
            return
        drawing_manager = manager.manager
        drawing_manager.add_stroke_segment(self.points[-2], self.points[-1])

class DrawingManager:
    def __init__(self, camera):
        self.camera = camera
        self.strokes = []
        self.brush_size = config.drawing_tool.brush_size
        self.brush_color = config.drawing_tool.brush_color
        self.opacity = config.drawing_tool.opacity
        self.smoothing = config.drawing_tool.smoothing

    def add_stroke_segment(self, p1, p2):
        self.strokes.append((p1, p2, self.brush_size, self.brush_color))

    def render(self, screen: pygame.Surface, camera):
        for p1, p2, size, color in self.strokes:
            s1 = camera.world_to_screen(p1)
            s2 = camera.world_to_screen(p2)
            r = max(1, int(size * camera.scaling))
            pygame.draw.line(screen, color, s1, s2, r)

    def clear(self):
        self.strokes.clear()

    def shutdown(self):
        self.clear()

class PluginImpl:
    def __init__(self, app: "App"):
        self.app = app
        self.manager = None
        self.enabled = getattr(config.drawing_tool, "enabled", True)
        self.tool = DrawingTool(app)

    def on_load(self, plugin_manager, instance):
        if self.enabled:
            self.manager = DrawingManager(self.app.camera)
        Debug.log_info("Drawing tool plugin loaded.", "Plugins")

    def on_unload(self, plugin_manager, instance):
        if self.manager:
            self.manager.shutdown()
            self.manager = None
        Debug.log_info("Drawing tool plugin unloaded.", "Plugins")

    def on_draw(self, plugin_manager, instance):
        if self.manager and self.enabled:
            self.manager.render(self.app.screen, self.app.camera)

    def get_tools(self, app):
        return [self.tool]

    def toggle_enabled(self, value: bool):
        self.enabled = value
        if value and not self.manager:
            self.manager = DrawingManager(self.app.camera)
        elif not value and self.manager:
            self.manager.shutdown()
            self.manager = None
        config.drawing_tool.enabled = value
        self.app.config.save()

    def set_brush_size(self, size: float):
        config.drawing_tool.brush_size = max(0.5, size)
        self.app.config.save()

    def set_brush_color(self, r: int, g: int, b: int):
        config.drawing_tool.brush_color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        self.app.config.save()

    def console_toggle(self, expr: str):
        val = expr.strip().lower() in ("1", "true", "on")
        self.toggle_enabled(val)
        return f"Drawing tool {'enabled' if val else 'disabled'}."

    def console_set_brush_size(self, expr: str):
        try:
            s = float(expr.strip())
            self.set_brush_size(s)
            return f"Brush size set to {s}."
        except ValueError:
            return "Invalid number."

    def console_set_color(self, expr: str):
        try:
            parts = list(map(int, expr.strip().split()))
            if len(parts) != 3:
                raise ValueError
            self.set_brush_color(*parts)
            return f"Brush color set to RGB{tuple(parts)}."
        except ValueError:
            return "Usage: draw_color <R> <G> <B> (0-255)"
def serialize_plugin(pm, instance):
    return {
        "brush_size": instance.tool.brush_size,
        "brush_color": instance.tool.brush_color,
        "strokes": instance.manager.strokes if instance.manager else []
    }

def deserialize_plugin(pm, instance, data):
    if instance.manager:
        instance.manager.strokes = data.get("strokes", [])
    if hasattr(instance, 'tool'):
        instance.tool.brush_size = data.get("brush_size", 2.0)
        instance.tool.brush_color = tuple(data.get("brush_color", (255, 255, 255)))
PLUGIN = Plugin(
    name="drawing_tool",
    version="1.0.0",
    description="Freehand drawing tool with configurable brush size and color.",
    author="Zarrakun",
    icon_path=None,
    dependency_specs={},
    config_class=DrawingToolConfig,
    on_load=lambda pm, inst: inst.on_load(pm, inst),
    on_unload=lambda pm, inst: inst.on_unload(pm, inst),
    on_draw=lambda pm, inst: inst.on_draw(pm, inst),
    console_commands={
        "draw_toggle": lambda inst, expr: inst.console_toggle(expr),
        "draw_size": lambda inst, expr: inst.console_set_brush_size(expr),
        "draw_color": lambda inst, expr: inst.console_set_color(expr),
    },
    command_help={
        "draw_toggle": "Enable/disable drawing tool",
        "draw_size": "Set brush size in world units",
        "draw_color": "Set brush color as R G B (0–255)",
    },
    serialize = serialize_plugin,
    deserialize = deserialize_plugin,
)