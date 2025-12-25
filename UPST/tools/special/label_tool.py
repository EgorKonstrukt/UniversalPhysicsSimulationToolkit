import pygame
import pygame_gui
import pymunk
from pygame_gui.elements import UITextEntryBox
from UPST.tools.base_tool import BaseTool
from UPST.modules.undo_redo_manager import get_undo_redo
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos, get_gizmos

class LabelTool(BaseTool):
    name = "Label"
    icon_path = "sprites/gui/label.png"
    tooltip = "Create world-space text labels"

    def __init__(self, pm):
        super().__init__(pm)
        self.settings = {
            "text": "New Label",
            "color": pygame.Color(255, 255, 255),
            "background_color": pygame.Color(0, 0, 0, 128),
            "collision": False,
            "font_name": "Consolas",
            "font_size": 18,
            "world_space_font": True,
            "attach_to_body": True,
            "max_attach_distance": 30.0
        }
        self.settings_window = None
        self._color_picker = None
        self._bg_color_picker = None
        self._world_mouse_pos = (0, 0)

    def create_settings_window(self):
        rect = pygame.Rect(100, 100, 300, 440)
        self.settings_window = pygame_gui.elements.UIWindow(
            rect, self.ui_manager.manager, window_display_title="Label Settings"
        )
        container = self.settings_window.get_container()
        y = 10
        self.text_entry = UITextEntryBox(
            pygame.Rect(10, y, 260, 100), initial_text=self.settings["text"], manager=self.ui_manager.manager,
            container=container
        )
        y += 110
        self.color_button = pygame_gui.elements.UIButton(
            pygame.Rect(10, y, 120, 30), "Text Color", manager=self.ui_manager.manager, container=container
        )
        self.bg_color_button = pygame_gui.elements.UIButton(
            pygame.Rect(140, y, 130, 30), "Background", manager=self.ui_manager.manager, container=container
        )
        y += 40
        self.collision_checkbox = pygame_gui.elements.UICheckBox(
            pygame.Rect(10, y, 20, 20), manager=self.ui_manager.manager, container=container, text="Collision"
        )
        self.collision_checkbox.set_state(self.settings["collision"])
        y += 30
        self.attach_checkbox = pygame_gui.elements.UICheckBox(
            pygame.Rect(10, y, 20, 20), manager=self.ui_manager.manager, container=container, text="Attach to body"
        )
        self.attach_checkbox.set_state(self.settings["attach_to_body"])
        y += 30
        self.font_name_entry = pygame_gui.elements.UITextEntryLine(
            pygame.Rect(10, y, 260, 30), manager=self.ui_manager.manager, container=container
        )
        self.font_name_entry.set_text(self.settings["font_name"])
        y += 40
        self.font_size_slider = pygame_gui.elements.UIHorizontalSlider(
            pygame.Rect(10, y, 200, 25), start_value=self.settings["font_size"], value_range=(8, 48),
            manager=self.ui_manager.manager, container=container
        )
        self.font_size_label = pygame_gui.elements.UILabel(
            pygame.Rect(220, y, 60, 25), str(self.settings["font_size"]), manager=self.ui_manager.manager,
            container=container
        )
        y += 35
        self.world_font_checkbox = pygame_gui.elements.UICheckBox(
            pygame.Rect(10, y, 20, 20), manager=self.ui_manager.manager, container=container, text="World-Space Font"
        )
        self.world_font_checkbox.set_state(self.settings["world_space_font"])

    def handle_event(self, event, world_pos):
        self._world_mouse_pos = world_pos
        if not (self.settings_window and self.settings_window.alive()):
            return

        text_color = pygame.Color(
            self.settings["color"].r,
            self.settings["color"].g,
            self.settings["color"].b,
            255
        )
        bg_color = pygame.Color(
            self.settings["background_color"].r,
            self.settings["background_color"].g,
            self.settings["background_color"].b,
            255
        ) if self.settings["background_color"].a > 0 else None

        Gizmos.draw_text(
            position=self._world_mouse_pos,
            text=self.settings["text"],
            color=text_color,
            background_color=bg_color,
            collision=False,
            font_name=self.settings["font_name"],
            font_size=self.settings["font_size"],
            font_world_space=self.settings["world_space_font"],
            world_space=True,
            duration=0.02,
            owner=None
        )
        if self.settings_window and self.settings_window.alive():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.ui_manager.manager.get_focus_set():
                    self.spawn_label(world_pos)
                    self.undo_redo.take_snapshot()

        if not (self.settings_window and self.settings_window.alive()):
            return

        if event.type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
            if event.ui_element == self._color_picker:
                self.settings["color"] = pygame.Color(event.colour)
                self._color_picker = None
            elif event.ui_element == self._bg_color_picker:
                c = event.colour
                self.settings["background_color"] = pygame.Color(c.r, c.g, c.b, 128)
                self._bg_color_picker = None

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.color_button:
                if not self._color_picker or not self._color_picker.alive():
                    self._color_picker = pygame_gui.windows.UIColourPickerDialog(
                        pygame.Rect(0, 0, 400, 400), self.ui_manager.manager,
                        initial_colour=self.settings["color"]
                    )
            elif event.ui_element == self.bg_color_button:
                if not self._bg_color_picker or not self._bg_color_picker.alive():
                    self._bg_color_picker = pygame_gui.windows.UIColourPickerDialog(
                        pygame.Rect(0, 0, 400, 400), self.ui_manager.manager,
                        initial_colour=self.settings["background_color"]
                    )

        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.font_size_slider:
                self.settings["font_size"] = int(event.value)
                self.font_size_label.set_text(str(self.settings["font_size"]))

        elif event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED:
            if event.ui_element == self.text_entry:
                self.settings["text"] = event.text
            elif event.ui_element == self.font_name_entry:
                self.settings["font_name"] = event.text

        elif event.type == pygame_gui.UI_CHECK_BOX_CHECKED or event.type == pygame_gui.UI_CHECK_BOX_UNCHECKED:
            if event.ui_element == self.collision_checkbox:
                self.settings["collision"] = event.ui_element.get_state()
            elif event.ui_element == self.attach_checkbox:
                self.settings["attach_to_body"] = event.ui_element.get_state()
            elif event.ui_element == self.world_font_checkbox:
                self.settings["world_space_font"] = event.ui_element.get_state()

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.settings_window:
                self.settings_window = None
    def spawn_label(self, position):
        try:
            owner = None
            if self.settings["attach_to_body"]:
                body = self.pm.get_body_at_position(position)
                if body:
                    dist = (body.position - pymunk.Vec2d(*position)).length
                    if dist <= self.settings["max_attach_distance"]:
                        owner = body
                        position = tuple(body.position)
            bg = self.settings["background_color"] if self.settings["background_color"].a > 0 else None
            Gizmos.draw_text(
                position=position,
                text=self.settings["text"],
                color=self.settings["color"],
                background_color=bg,
                collision=self.settings["collision"],
                font_name=self.settings["font_name"],
                font_size=self.settings["font_size"],
                font_world_space=self.settings["world_space_font"],
                world_space=True,
                duration=0,
                owner=owner
            )
        except Exception as e:
            Debug.log_error(f"Failed to spawn label: {e}", "LabelTool")

    def activate(self):
        super().activate()
        if not self.settings_window or not self.settings_window.alive():
            self.create_settings_window()