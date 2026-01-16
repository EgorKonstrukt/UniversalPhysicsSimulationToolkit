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


class ToolSystem:
    def __init__(self, physics_manager, sound_manager):
        self.pm = physics_manager
        self.sm = sound_manager
        self.ui_manager = None
        self.input_handler = None
        self.tools = {}
        self.current_tool = None
        self._pending_tools = []
        self._register_tools()
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

    def _register_tools(self):
        from UPST.tools.special.laser_tool import LaserTool

        self.laser_processor = LaserProcessor(self.pm)
        spawn_tools = [
            CircleTool(self.pm),
            RectangleTool(self.pm),
            TriangleTool(self.pm),
            PolyTool(self.pm),
            PolyhedronTool(self.pm),
            SpamTool(self.pm),
            GearTool(self.pm),
            ChainTool(self.pm),
            PlaneTool(self.pm),
        ]
        constraint_tools = [
            SpringTool(self.pm),
            PivotJointTool(self.pm),
            PinJointTool(self.pm),
            FixateTool(self.pm)
        ]
        special_tools = [
            ExplosionTool(self.pm),
            StaticLineTool(self.pm),
            LaserTool(self.pm, self.laser_processor),
            DragTool(self.pm),
            MoveTool(self.pm),
            RotateTool(self.pm),
            CutTool(self.pm),
            ScriptTool(self.pm),
            LabelTool(self.pm),
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
    def create_tool_buttons(self):
        if not self.ui_manager: return
        bs, pad, x0 = 50, 1, 10
        tip_delay = getattr(config, 'TOOLTIP_DELAY', 0.1)
        items = []
        y = 0

        categories = defaultdict(list)
        for tool in self.tools.values():
            cat = getattr(tool, 'category', 'Tools')
            categories[cat].append(tool)

        known_order = ["Primitives", "Connections", "Tools"]
        sorted_cats = [c for c in known_order if c in categories]
        sorted_cats += sorted([c for c in categories if c not in known_order])

        for cat in sorted_cats:
            items.append(("label", cat, y))
            y += 30
            col = 0
            for tool in categories[cat]:
                x = x0 + col * (bs + pad)
                items.append(("btn", tool.name, tool.icon_path, x, y))
                col += 1
                if col > 1:
                    col = 0
                    y += bs + pad
            if col: y += bs + pad

        panel_width = x0 + 2 * (bs + pad) - pad
        panel_height = y + 70
        panel = UIPanel(relative_rect=pygame.Rect(5, 50, panel_width+15, panel_height), manager=self.ui_manager.manager)
        self.ui_manager.tool_panel = panel
        for it in items:
            if it[0] == "label":
                UILabel(relative_rect=pygame.Rect(0, it[2], panel_width - 10, 25),
                        text=f"-- {it[1]} --", manager=self.ui_manager.manager, container=panel)
            else:
                _, name, icon, x, y = it
                tip = getattr(self.tools[name], 'tooltip', name)
                btn = UIButton(relative_rect=pygame.Rect(x, y, bs, bs), text="",
                               manager=self.ui_manager.manager, container=panel)
                icon_str = str(icon) if icon is not None else None
                if icon_str and os.path.exists(icon_str):
                    img_surface = pygame.image.load(icon_str)
                else:
                    img_surface = pygame.Surface((bs - 4, bs - 4))
                    img_surface.fill((200, 100, 200))
                img = UIImage(relative_rect=pygame.Rect(x + 2, y + 2, bs - 4, bs - 4),
                              image_surface=img_surface,
                              manager=self.ui_manager.manager, container=panel)
                btn.set_tooltip(tip, delay=tip_delay)
                img.set_tooltip(tip, delay=tip_delay)
                btn.tool_name = name
                self.ui_manager.tool_buttons.append(btn)