import pygame
import pygame_gui
import json
import os
import tkinter as tk
from tkinter import filedialog
from UPST.tools.base_tool import BaseTool
from pygame_gui.windows import UIColourPickerDialog
from UPST.modules.undo_redo_manager import get_undo_redo

class GraphTool(BaseTool):
    name = "graph"
    category = "Visualization"
    icon_path = "sprites/gui/plot.png"
    tooltip = "Create multiple mathematical graphs: cartesian, parametric, polar, implicit, scatter, and vector fields"

    def __init__(self, app):
        super().__init__(app)
        self.undo_redo_manager = get_undo_redo()
        self.graph_manager = app.console_handler.graph_manager
        self.graphs = [{
            'expression': "y=sin(x)",
            'plot_type': "cartesian",
            'color': (0, 200, 255),
            'width': 2,
            'style': "solid",
            'x_range': (-10.0, 10.0),
            'y_range': (-5.0, 5.0)
        }]
        self.active_graph_index = 0
        self.color_picker = None
        self._ui_elements = {}
        self._graph_buttons = []
        self._graph_color_previews = []
        self.list_panel = None
        self.scroll_bar = None
        self.list_height = 120
        self.item_height = 30
        self.scroll_position = 0.0
        self.color = (0, 200, 255)

    def create_settings_window(self):
        if self.settings_window and self.settings_window.alive():
            self.settings_window.show()
            return
        screen_w, screen_h = self.ui_manager.manager.window_resolution
        win_size = (480, 620)
        pos = self.tool_system._find_non_overlapping_position(win_size, pygame.Rect(0, 0, screen_w, screen_h))
        rect = pygame.Rect(*pos, *win_size)
        self.settings_window = pygame_gui.elements.UIWindow(
            rect=rect,
            manager=self.ui_manager.manager,
            window_display_title=f"{self.name} Settings",
            resizable=True
        )
        self._build_ui()

    def _build_ui(self):
        container = self.settings_window.get_container()
        y = 10
        self.list_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(10, y, 200, self.list_height),
            manager=self.ui_manager.manager,
            container=container
        )
        self._rebuild_graph_list()
        y += self.list_height + 10
        self.add_btn = pygame_gui.elements.UIButton(pygame.Rect(10, y, 80, 30), "Add", self.ui_manager.manager, container=container)
        self.remove_btn = pygame_gui.elements.UIButton(pygame.Rect(100, y, 80, 30), "Remove", self.ui_manager.manager, container=container)
        y += 40
        self.type_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['cartesian', 'parametric', 'polar', 'implicit', 'scatter', 'field'],
            self.graphs[0]['plot_type'], pygame.Rect(10, y, 180, 30),
            self.ui_manager.manager, container=container
        )
        self.expr_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(10, y + 40, 400, 30), self.ui_manager.manager, container=container)
        y += 85
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 80, 25), "Color:", self.ui_manager.manager, container=container)
        self.color_btn = pygame_gui.elements.UIButton(pygame.Rect(90, y, 60, 25), "", self.ui_manager.manager, container=container)
        pygame_gui.elements.UILabel(pygame.Rect(160, y, 60, 25), "Width:", self.ui_manager.manager, container=container)
        self.width_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(220, y, 40, 25), self.ui_manager.manager, container=container)
        pygame_gui.elements.UILabel(pygame.Rect(270, y, 50, 25), "Style:", self.ui_manager.manager, container=container)
        self.style_dropdown = pygame_gui.elements.UIDropDownMenu(
            ['solid', 'dashed', 'dotted'], self.graphs[0]['style'], pygame.Rect(320, y, 60, 25),
            self.ui_manager.manager, container=container
        )
        y += 40
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 60, 25), "X range:", self.ui_manager.manager, container=container)
        self.xmin_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(75, y, 80, 25), self.ui_manager.manager, container=container)
        pygame_gui.elements.UILabel(pygame.Rect(165, y, 20, 25), "..", self.ui_manager.manager, container=container)
        self.xmax_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(190, y, 80, 25), self.ui_manager.manager, container=container)
        y += 35
        pygame_gui.elements.UILabel(pygame.Rect(10, y, 60, 25), "Y range:", self.ui_manager.manager, container=container)
        self.ymin_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(75, y, 80, 25), self.ui_manager.manager, container=container)
        pygame_gui.elements.UILabel(pygame.Rect(165, y, 20, 25), "..", self.ui_manager.manager, container=container)
        self.ymax_entry = pygame_gui.elements.UITextEntryLine(pygame.Rect(190, y, 80, 25), self.ui_manager.manager, container=container)
        y += 45
        self.save_btn = pygame_gui.elements.UIButton(pygame.Rect(10, y, 100, 30), "Save JSON", self.ui_manager.manager, container=container)
        self.load_btn = pygame_gui.elements.UIButton(pygame.Rect(120, y, 100, 30), "Load JSON", self.ui_manager.manager, container=container)
        y += 40
        self.apply_all_btn = pygame_gui.elements.UIButton(pygame.Rect(10, y, 100, 30), "Apply All", self.ui_manager.manager, container=container)
        self.clear_btn = pygame_gui.elements.UIButton(pygame.Rect(120, y, 100, 30), "Clear", self.ui_manager.manager, container=container)
        self._ui_elements.update({
            'type': self.type_dropdown,
            'expr': self.expr_entry,
            'color_btn': self.color_btn,
            'width': self.width_entry,
            'style': self.style_dropdown,
            'xmin': self.xmin_entry,
            'xmax': self.xmax_entry,
            'ymin': self.ymin_entry,
            'ymax': self.ymax_entry
        })
        self._load_graph_to_ui(0)
        self._update_y_range_visibility()

    def _rebuild_graph_list(self):
        for btn in self._graph_buttons:
            btn.kill()
        for img in self._graph_color_previews:
            img.kill()
        self._graph_buttons.clear()
        self._graph_color_previews.clear()
        total_items = len(self.graphs)
        visible_count = self.list_height // self.item_height
        scroll_max = max(0, total_items - visible_count)
        start = int(self.scroll_position * scroll_max) if scroll_max > 0 else 0
        end = min(start + visible_count, total_items)
        for i in range(start, end):
            g = self.graphs[i]
            expr_short = (g['expression'][:17] + '...') if len(g['expression']) > 20 else g['expression']
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(5, (i - start) * self.item_height + 5, 160, 25),
                text=expr_short,
                manager=self.ui_manager.manager,
                container=self.list_panel,
                object_id=f"graph_btn_{i}"
            )
            color_surf = pygame.Surface((15, 15))
            color_surf.fill(g['color'])
            img = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(170, (i - start) * self.item_height + 10, 15, 15),
                image_surface=color_surf,
                manager=self.ui_manager.manager,
                container=self.list_panel
            )
            self._graph_buttons.append(btn)
            self._graph_color_previews.append(img)
        if self.scroll_bar:
            self.scroll_bar.kill()
        if total_items > visible_count:
            self.scroll_bar = pygame_gui.elements.UIVerticalScrollBar(
                relative_rect=pygame.Rect(210, 10, 20, self.list_height),
                visible_percentage=visible_count / total_items,
                manager=self.ui_manager.manager,
                container=self.settings_window.get_container()
            )
            self.scroll_bar.set_scroll_from_start_percentage(self.scroll_position)
        else:
            self.scroll_bar = None

    def _load_graph_to_ui(self, idx):
        g = self.graphs[idx]
        self.type_dropdown.selected_option = g['plot_type']
        self.expr_entry.set_text(g['expression'])
        self.color = g['color']
        self._update_color_btn()
        self.width_entry.set_text(str(g['width']))
        self.style_dropdown.selected_option = g['style']
        self.xmin_entry.set_text(str(g['x_range'][0]))
        self.xmax_entry.set_text(str(g['x_range'][1]))
        self.ymin_entry.set_text(str(g['y_range'][0]))
        self.ymax_entry.set_text(str(g['y_range'][1]))

    def _save_ui_to_graph(self, idx):
        g = self.graphs[idx]
        g['plot_type'] = self.type_dropdown.selected_option
        g['expression'] = self.expr_entry.get_text().strip() or "y=sin(x)"
        g['color'] = self.color
        try:
            g['width'] = max(1, min(5, int(self.width_entry.get_text())))
        except ValueError:
            pass
        g['style'] = self.style_dropdown.selected_option
        try:
            g['x_range'] = (float(self.xmin_entry.get_text()), float(self.xmax_entry.get_text()))
        except ValueError:
            pass
        if g['plot_type'] in ('cartesian', 'implicit', 'field'):
            try:
                g['y_range'] = (float(self.ymin_entry.get_text()), float(self.ymax_entry.get_text()))
            except ValueError:
                pass

    def _update_color_btn(self):
        surf = pygame.Surface((56, 21))
        surf.fill(self.color)
        self.color_btn.drawable_shape.states['normal'].surface = surf
        self.color_btn.drawable_shape.redraw_all_states()

    def _update_y_range_visibility(self):
        has_y = self.type_dropdown.selected_option in ('cartesian', 'implicit', 'field')
        self.ymin_entry.visible = has_y
        self.ymax_entry.visible = has_y

    def serialize_for_save(self):
        return {
            "graphs": [
                {
                    "expression": g["expression"],
                    "plot_type": g["plot_type"],
                    "color": list(g["color"]),
                    "width": g["width"],
                    "style": g["style"],
                    "x_range": list(g["x_range"]),
                    "y_range": list(g["y_range"])
                }
                for g in self.graphs
            ],
            "active_graph_index": self.active_graph_index
        }

    def deserialize_from_save(self, data):
        if not isinstance(data, dict):
            return
        graphs = []
        for g in data.get("graphs", []):
            graphs.append({
                "expression": g["expression"],
                "plot_type": g["plot_type"],
                "color": tuple(g["color"]),
                "width": g["width"],
                "style": g["style"],
                "x_range": tuple(g["x_range"]),
                "y_range": tuple(g["y_range"])
            })
        if not graphs:
            graphs = [{
                'expression': "y=sin(x)",
                'plot_type': "cartesian",
                'color': (0, 200, 255),
                'width': 2,
                'style': "solid",
                'x_range': (-10.0, 10.0),
                'y_range': (-5.0, 5.0)
            }]
        self.graphs = graphs
        self.active_graph_index = max(0, min(data.get("active_graph_index", 0), len(graphs) - 1))
        if self.settings_window and self.settings_window.alive():
            self._rebuild_graph_list()
            self._load_graph_to_ui(self.active_graph_index)

    def handle_event(self, event, world_pos):
        super().handle_event(event, world_pos)
        if not self.settings_window or not self.settings_window.alive():
            return
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for i, btn in enumerate(self._graph_buttons):
                if event.ui_element == btn:
                    real_index = int(btn.object_ids[-1].split('_')[-1])
                    self._save_ui_to_graph(self.active_graph_index)
                    self.active_graph_index = real_index
                    self._load_graph_to_ui(real_index)
                    break
            if event.ui_element == self.color_btn:
                self.color_picker = UIColourPickerDialog(
                    rect=pygame.Rect(0, 0, 390, 390),
                    manager=self.ui_manager.manager,
                    initial_colour=pygame.Color(*self.color),
                    window_title="Pick Color"
                )
            elif event.ui_element == self.add_btn:
                self.graphs.append({
                    'expression': "y=cos(x)",
                    'plot_type': "cartesian",
                    'color': (255, 100, 100),
                    'width': 2,
                    'style': "solid",
                    'x_range': (-10.0, 10.0),
                    'y_range': (-5.0, 5.0)
                })
                self._rebuild_graph_list()
            elif event.ui_element == self.remove_btn:
                if len(self.graphs) > 1:
                    del self.graphs[self.active_graph_index]
                    self.active_graph_index = max(0, min(self.active_graph_index, len(self.graphs) - 1))
                    self._rebuild_graph_list()
                    self._load_graph_to_ui(self.active_graph_index)
            elif event.ui_element == self.save_btn:
                self._save_ui_to_graph(self.active_graph_index)
                root = tk.Tk(); root.withdraw()
                path = filedialog.asksaveasfilename(title="Save Graphs", defaultextension=".json", initialfile="graphs.json", filetypes=[("JSON files", "*.json")])
                if path:
                    self.save_graphs_to_json(path)
            elif event.ui_element == self.load_btn:
                root = tk.Tk(); root.withdraw()
                path = filedialog.askopenfilename(title="Load Graphs", filetypes=[("JSON files", "*.json")])
                if path:
                    self.load_graphs_from_json(path)
            elif event.ui_element == self.apply_all_btn:
                self._save_ui_to_graph(self.active_graph_index)
                self._apply_all_graphs()
            elif event.ui_element == self.clear_btn:
                self.graph_manager.handle_graph_command('clear')
        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.type_dropdown:
                self._update_y_range_visibility()
        elif event.type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
            if event.ui_element == self.color_picker:
                self.color = (event.colour.r, event.colour.g, event.colour.b)
                self.graphs[self.active_graph_index]['color'] = self.color
                self._update_color_btn()
                self._rebuild_graph_list()
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.scroll_bar:
                self.scroll_position = event.value
                self._rebuild_graph_list()
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.expr_entry:
                self._save_ui_to_graph(self.active_graph_index)
                self._rebuild_graph_list()

    def save_graphs_to_json(self, filepath):
        data = []
        for g in self.graphs:
            item = g.copy()
            item['color'] = list(g['color'])
            data.append(item)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_graphs_from_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.graphs = []
        for item in data:
            item['color'] = tuple(item['color'])
            if 'x_range' not in item:
                item['x_range'] = (-10.0, 10.0)
            if 'y_range' not in item:
                item['y_range'] = (-5.0, 5.0)
            self.graphs.append(item)
        if not self.graphs:
            self.graphs = [{'expression': "y=sin(x)", 'plot_type': "cartesian", 'color': (0, 200, 255), 'width': 2, 'style': "solid", 'x_range': (-10.0, 10.0), 'y_range': (-5.0, 5.0)}]
        self.active_graph_index = 0
        if self.settings_window and self.settings_window.alive():
            self._rebuild_graph_list()
            self._load_graph_to_ui(0)

    def _apply_all_graphs(self):
        full_commands = []
        for g in self.graphs:
            cmd_parts = [g['expression']]
            cmd_parts.append(f"color:{g['color'][0]},{g['color'][1]},{g['color'][2]}")
            cmd_parts.append(f"width:{g['width']}")
            cmd_parts.append(f"style:{g['style']}")
            if g['plot_type'] in ('cartesian', 'implicit', 'field'):
                xr = g['x_range']
                yr = g['y_range']
                cmd_parts.append(f"x={xr[0]}..{xr[1]}")
                cmd_parts.append(f"y={yr[0]}..{yr[1]}")
            full_commands.append("; ".join(cmd_parts))
        full_cmd = "; clear; " + "; ".join(full_commands)
        self.graph_manager.handle_graph_command(full_cmd)
        self.undo_redo_manager.take_snapshot()

    def activate(self):
        super().activate()
        if not self.settings_window or not self.settings_window.alive():
            self.create_settings_window()

    def deactivate(self):
        super().deactivate()
        if self.settings_window and self.settings_window.alive():
            self.settings_window.hide()