import os
from collections import defaultdict

import pygame
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIImage

from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
import pygame_gui

from UPST.tools.shapes.chain_tool import ChainTool
from UPST.tools.special.explosion_tool import ExplosionTool
from UPST.tools.constraints.fixate_tool import FixateTool
from UPST.tools.special.laser_processor import LaserProcessor

from UPST.tools.shapes.circle_tool import CircleTool
from UPST.tools.constraints.pin_joint_tool import PinJointTool
from UPST.tools.constraints.pivot_joint_tool import PivotJointTool
from UPST.tools.shapes.rectanlge_tool import RectangleTool
from UPST.tools.constraints.spring_tool import SpringTool
from UPST.tools.shapes.static_line_tool import StaticLineTool
from UPST.tools.shapes.triangle_tool import TriangleTool
from UPST.tools.shapes.polyhedron_tool import PolyhedronTool
from UPST.tools.special.spam_tool import SpamTool
from UPST.tools.special.gear_tool import GearTool
from UPST.tools.manipulation.move_tool import MoveTool
from UPST.tools.manipulation.rotate_tool import RotateTool
from UPST.tools.manipulation.cut_tool import CutTool
from UPST.tools.special.script_tool import ScriptTool
from UPST.tools.manipulation.drag_tool import DragTool
from UPST.tools.shapes.plane_tool import PlaneTool
from UPST.tools.shapes.poly_tool import PolyTool
from UPST.tools.special.label_tool import LabelTool

from UPST.modules.undo_redo_manager import get_undo_redo

class ResizableToolWindow(pygame_gui.elements.UIWindow):
    CONFIG_KEY = "tool_window_rect"

    def __init__(self, rect, manager, tool_system):
        saved = config.get(self.CONFIG_KEY)
        if saved:
            try:
                rect = pygame.Rect(saved[0]+15, saved[1]+15, saved[2]-30, saved[3]-20)
            except (TypeError, ValueError):
                pass
        super().__init__(rect, manager, window_display_title="Tools", resizable=True)
        self.tool_system = tool_system
        self._last_container_size = self.get_container().get_size()
        self.tool_system._layout_window = self
        self._was_resizing = False

    def update(self, time_delta):
        super().update(time_delta)
        container = self.get_container()
        current_size = container.get_size()
        resizing_now = self.resizing_mode_active
        if current_size != self._last_container_size:
            self._last_container_size = current_size
            self.tool_system._rebuild_tool_layout()
        if self._was_resizing and not resizing_now:
            self._save_window_rect()
        self._was_resizing = resizing_now

    def _save_window_rect(self):
        r = self.rect
        config.set(self.CONFIG_KEY, [r.x, r.y, r.width, r.height])
        config.save()

class ToolSystem:
    def __init__(self, physics_manager, sound_manager, app):
        self.pm = physics_manager
        self.app = app
        self.sm = sound_manager
        self.ui_manager = None
        self.input_handler = None
        self.tools = {}
        self.current_tool = None
        self._pending_tools = []
        self.undo_redo = get_undo_redo()
        self.tool_panel = None
        self.tool_buttons = []

    def is_mouse_on_ui(self):
        return bool(self.ui_manager.manager.get_focus_set())

    def set_ui_manager(self, ui_manager):
        self.ui_manager = ui_manager
        self._register_tool_settings()

    def set_input_handler(self, input_handler):
        self.input_handler = input_handler

    def register_tools(self):
        from UPST.tools.special.laser_tool import LaserTool

        self.laser_processor = LaserProcessor(self.pm)
        spawn_tools = [
            CircleTool(self.app),
            RectangleTool(self.app),
            TriangleTool(self.app),
            PolyTool(self.app),
            PolyhedronTool(self.app),
            SpamTool(self.app),
            GearTool(self.app),
            ChainTool(self.app),
            PlaneTool(self.app),
        ]
        constraint_tools = [
            SpringTool(self.app),
            PivotJointTool(self.app),
            PinJointTool(self.app),
            FixateTool(self.app)
        ]
        special_tools = [
            ExplosionTool(self.app),
            StaticLineTool(self.app),
            LaserTool( self.laser_processor, self.app),
            DragTool(self.app),
            MoveTool(self.app),
            RotateTool(self.app),
            CutTool(self.app),
            ScriptTool(self.app),
            LabelTool(self.app),
        ]
        self._pending_tools = spawn_tools + constraint_tools + special_tools

    def _register_tool_settings(self):
        if not self.ui_manager:
            return
        for tool in self._pending_tools:
            tool.set_ui_manager(self.ui_manager)
            self.tools[tool.name] = tool
        self._pending_tools.clear()

    def activate_tool(self, tool_name):
        if self.current_tool:
            self.current_tool.deactivate()
        self.current_tool = self.tools[tool_name]
        if not hasattr(self.current_tool, 'settings_window') or self.current_tool.settings_window is None:
            self.current_tool.create_settings_window()
        self.current_tool.activate()
        synthesizer.play_frequency(1630, duration=0.03, waveform='sine')

    def handle_input(self, world_pos):
        if self.is_mouse_on_ui():
            return
        if self.current_tool and hasattr(self.current_tool, 'handle_input'):
            self.current_tool.handle_input(world_pos)

    def handle_event(self, event, world_pos):
        if event.type == pygame_gui.UI_WINDOW_CLOSE:
            pass
        elif self.is_mouse_on_ui():
            return
        if self.current_tool:
            self.current_tool.handle_event(event, world_pos)

    def draw_preview(self, screen, camera):
        if self.current_tool and hasattr(self.current_tool, 'draw_preview'):
            self.current_tool.draw_preview(screen, camera)

    def register_tool(self, tool):
        print(f">>> Registering tool: {tool.name} (UI ready: {self.ui_manager is not None})")
        if not self.ui_manager:
            self._pending_tools.append(tool)
            print(">>> Added to _pending_tools")
        else:
            tool.set_ui_manager(self.ui_manager)
            self.tools[tool.name] = tool
            print(">>> Added to active tools")
    def clear_tool_buttons(self):
        if hasattr(self.ui_manager, 'tool_panel') and self.ui_manager.tool_panel:
            self.ui_manager.tool_panel.kill()
            self.ui_manager.tool_panel = None
        self.ui_manager.tool_buttons.clear()

    def _rebuild_tool_layout(self):
        if not hasattr(self.ui_manager, 'tool_panel') or not self.ui_manager.tool_panel:
            return
        window = self.ui_manager.tool_panel
        container = window.get_container()
        for child in container.elements:
            child.kill()
        bs, pad, x0 = 50, 1, 0
        tip_delay = getattr(config, 'TOOLTIP_DELAY', 0.1)
        y = 0
        categories = defaultdict(list)
        for tool in self.tools.values():
            cat = getattr(tool, 'category', 'Tools')
            categories[cat].append(tool)
        known_order = ["Primitives", "Connections", "Tools"]
        sorted_cats = [c for c in known_order if c in categories]
        sorted_cats += sorted([c for c in categories if c not in known_order])
        items = []
        for cat in sorted_cats:
            items.append(("label", cat, y))
            y += 0
            col = 0
            max_width = container.rect.width - 0
            for tool in categories[cat]:
                x = x0 + col * (bs + pad)
                if x + bs > max_width:
                    col = 0
                    x = x0
                    y += bs + pad
                items.append(("btn", tool.name, tool.icon_path, x, y))
                col += 1
            y += bs + pad if col else 0
        for it in items:
            if it[0] == "label":
                pass
                # UILabel(relative_rect=pygame.Rect(0, it[2], container.rect.width - 10, 25),
                #         text=f"-- {it[1]} --", manager=self.ui_manager.manager, container=container)
            else:
                _, name, icon, x, y = it
                tip = getattr(self.tools[name], 'tooltip', name)
                btn = UIButton(relative_rect=pygame.Rect(x, y, bs, bs), text="",
                               manager=self.ui_manager.manager, container=container)
                icon_str = str(icon) if icon is not None else None
                if icon_str and os.path.exists(icon_str):
                    img_surface = pygame.image.load(icon_str)
                else:
                    img_surface = pygame.Surface((bs - 4, bs - 4))
                    img_surface.fill((200, 100, 200))
                img = UIImage(relative_rect=pygame.Rect(x + 2, y + 2, bs - 4, bs - 4),
                              image_surface=img_surface,
                              manager=self.ui_manager.manager, container=container)
                btn.set_tooltip(tip, delay=tip_delay)
                img.set_tooltip(tip, delay=tip_delay)
                btn.tool_name = name
                self.ui_manager.tool_buttons.append(btn)

    def create_tool_buttons(self):
        if not self.ui_manager: return
        self.clear_tool_buttons()
        window_rect = pygame.Rect(5, 50, 220, 300)
        window = ResizableToolWindow(window_rect, self.ui_manager.manager, self)
        self.ui_manager.tool_panel = window
        self.ui_manager.tool_buttons = []
        self._rebuild_tool_layout()

    def _find_non_overlapping_position(self, window_size, screen_rect):
        """Find a non-overlapping position for a new window near top-left or bottom-left."""
        candidates = [
            (10, 10),  # top-left
            (10, screen_rect.height - window_size[1] - 10)  # bottom-left
        ]
        existing_rects = []
        for elem in self.ui_manager.manager.get_root_container().elements:
            if isinstance(elem, pygame_gui.elements.UIWindow) and elem.alive() and elem.visible:
                if hasattr(elem, 'rect'):
                    existing_rects.append(elem.rect.copy())
        for x, y in candidates:
            candidate_rect = pygame.Rect(x, y, *window_size)
            if not any(candidate_rect.colliderect(r) for r in existing_rects):
                return (x, y)
        return candidates[1]  # fallback