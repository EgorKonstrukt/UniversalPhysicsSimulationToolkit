import pymunk
import pygame
from pygame_gui.elements import UILabel, UIButton, UIImage, UIPanel
from UPST.sound.sound_synthesizer import synthesizer

class ToolManager:
    def __init__(self, physics_manager, ui_manager, input_handler, sound_manager, spawner):
        self.physics_manager = physics_manager
        self.ui_manager = ui_manager
        self.input_handler = input_handler
        self.sound_manager = sound_manager
        self.spawner = spawner
        self.tools = {}
        self._register_tools()
    def create_tool_buttons(self):
        spawn_panel = UIPanel(relative_rect=pygame.Rect(5, 50, 200, 640), manager=self.ui_manager.manager)
        section_y = 0
        def add_section_label(text, y):
            UILabel(relative_rect=pygame.Rect(0, y, 190, 25), text=f"-- {text} --", manager=self.ui_manager.manager, container=spawn_panel)
            return y + 30
        def add_tool_button(y, name, icon_path):
            button = UIButton(relative_rect=pygame.Rect(10, y, 120, 45), text=name, manager=self.ui_manager.manager, container=spawn_panel)
            UIImage(relative_rect=pygame.Rect(135, y + 2, 40, 40), image_surface=pygame.image.load(icon_path), manager=self.ui_manager.manager, container=spawn_panel)
            self.ui_manager.tool_buttons.append(button)
            return y + 45
        section_y = add_section_label("Primitives", section_y)
        for tool_name in ["Circle", "Rectangle", "Triangle", "Polyhedron", "Spam", "Human"]:
            icon = self.tools[tool_name]["icon"]
            section_y = add_tool_button(section_y, tool_name, icon)
        section_y = add_section_label("Connections", section_y)
        for tool_name in ["Spring", "Pivot", "Rigid"]:
            icon = self.tools[tool_name]["icon"]
            section_y = add_tool_button(section_y, tool_name, icon)
        section_y = add_section_label("Fun Stuff", section_y)
        explosion_icon = self.tools["Explosion"]["icon"]
        section_y = add_tool_button(section_y, "Explosion", explosion_icon)
    def _register_tools(self):
        spawn_tools = {
            "Circle": {"type": "spawn", "icon": "sprites/gui/spawn/circle.png", "window": self.ui_manager.window_circle, "spawner": self.spawner.spawn_circle, "drag_spawner": self.spawner.spawn_circle_dragged},
            "Rectangle": {"type": "spawn", "icon": "sprites/gui/spawn/rectangle.png", "window": self.ui_manager.window_rectangle, "spawner": self.spawner.spawn_rectangle, "drag_spawner": self.spawner.spawn_rectangle_dragged},
            "Triangle": {"type": "spawn", "icon": "sprites/gui/spawn/triangle.png", "window": self.ui_manager.window_triangle, "spawner": self.spawner.spawn_triangle, "drag_spawner": self.spawner.spawn_triangle_dragged},
            "Polyhedron": {"type": "spawn", "icon": "sprites/gui/spawn/polyhedron.png", "window": self.ui_manager.window_polyhedron, "spawner": self.spawner.spawn_polyhedron, "drag_spawner": self.spawner.spawn_polyhedron_dragged},
            "Spam": {"type": "spawn", "icon": "sprites/gui/spawn/spam.png", "spawner": self.spawner.spawn_spam, "drag_spawner": None},
            "Human": {"type": "spawn", "icon": "sprites/gui/spawn/human.png", "spawner": self.spawner.spawn_human, "drag_spawner": None}
        }
        constraint_tools = {
            "Spring": {"type": "constraint", "icon": "sprites/gui/tools/spring.png", "handler": self.create_spring},
            "Pivot": {"type": "constraint", "icon": "sprites/gui/tools/pivot.png", "handler": self.create_pivot},
            "Rigid": {"type": "constraint", "icon": "sprites/gui/tools/rigid.png", "handler": self.create_rigid}
        }
        self.tools["Explosion"] = {"type": "tool", "icon": "sprites/gui/tools/explosion.png", "handler": self.trigger_explosion}
        self.tools["Drag"] = {"type": "tool", "icon": "sprites/gui/tools/explosion.png", "handler": self.trigger_explosion}
        self.tools.update(spawn_tools)
        self.tools.update(constraint_tools)
        for tool_name, tool_info in self.tools.items():
            if "icon" in tool_info:
                try:
                    icon_surface = pygame.image.load(tool_info["icon"]).convert_alpha()
                    self.ui_manager.tool_icons[tool_name] = icon_surface
                except Exception as e:
                    print(f"Failed to load icon for {tool_name}: {e}")
    def handle_tool_button_press(self, button, game_app):
        tool_name = button.text
        if tool_name in self.tools:
            synthesizer.play_frequency(1630, duration=0.03, waveform='sine')
            tool_info = self.tools[tool_name]
            self.ui_manager.hide_all_object_windows()
            self.input_handler.first_joint_body = None
            self.input_handler.current_tool = tool_name
            if tool_info["type"] == "spawn" and "window" in tool_info:
                tool_info["window"].show()
    def create_spring(self, start_body, end_body):
        if start_body and end_body:
            spring = pymunk.DampedSpring(start_body, end_body, anchor_a=(0, 0), anchor_b=(0, 0), rest_length=50, stiffness=50, damping=10)
            self.physics_manager.space.add(spring)
    def create_pivot(self, start_body, end_body):
        if start_body and end_body:
            pivot = pymunk.PivotJoint(start_body, end_body, (0, 0))
            self.physics_manager.space.add(pivot)
    def create_rigid(self, start_body, end_body):
        if start_body and end_body:
            self.physics_manager.space.add(pymunk.PinJoint(start_body, end_body, (0, 0), (0, 0)))
    def trigger_explosion(self, position):
        print("boom!")
        for body in self.physics_manager.space.bodies:
            distance = (body.position - position).length
            if distance < 100:
                impulse = (position - body.position) * 1000 / distance
                body.apply_impulse_at_local_point(impulse)