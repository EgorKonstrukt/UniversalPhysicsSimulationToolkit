import pygame
import pygame_gui
from UPST.config import config

class ForceFieldUI:
    def __init__(self, manager, screen_width, screen_height, parent_ui):
        self.manager = manager
        self.parent_ui = parent_ui
        self.force_field_buttons = []
        self.force_field_icons = []
        self.strength_slider = None
        self.radius_slider = None
        self.text_label_strength = None
        self.text_label_radius = None
        self._create_force_field_buttons(screen_width, screen_height)
        self._create_force_field_settings()

    def _create_force_field_buttons(self, screen_width, screen_height):
        paths = ["attraction.png", "repulsion.png", "ring.png", "spiral.png", "laydigital.png"]
        texts = ["attraction", "repulsion", "ring", "spiral", "freeze"]
        for i, (path, text) in enumerate(zip(paths, texts)):
            pos = (screen_width-135, screen_height-500+51*i)
            button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(pos,(110,50)), text=text, manager=self.manager)
            icon = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(pos[0]-50,pos[1]+1,47,47), image_surface=pygame.image.load(f"sprites/gui/force_field/{path}"), manager=self.manager)
            self.force_field_buttons.append(button)
            self.force_field_icons.append(icon)

    def _create_force_field_settings(self):
        self.strength_slider = pygame_gui.elements.UIHorizontalSlider(relative_rect=pygame.Rect(400,10,200,20), start_value=500, value_range=(0,5000), manager=self.manager)
        self.radius_slider = pygame_gui.elements.UIHorizontalSlider(relative_rect=pygame.Rect(400,40,200,20), start_value=500, value_range=(0,10000), manager=self.manager)
        self.text_label_strength = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(380,10,250,50), text=f"Force Field Strength: {500}", manager=self.manager)
        self.text_label_radius = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(400,40,200,50), text=f"Force Field Radius: {500}", manager=self.manager)
        self.hide_settings()

    def handle_button_press(self, button, game_app):
        self.parent_ui.selected_force_field_button_text = button.text
        self.show_settings()

    def handle_slider_move(self, event, game_app):
        if event.ui_element == self.strength_slider:
            game_app.force_field_manager.strength = int(event.value)
            self.text_label_strength.set_text(f"Force Field Strength: {game_app.force_field_manager.strength}")
        elif event.ui_element == self.radius_slider:
            game_app.force_field_manager.radius = int(event.value)
            self.text_label_radius.set_text(f"Force Field Radius: {game_app.force_field_manager.radius}")

    def show_settings(self):
        self.strength_slider.show()
        self.radius_slider.show()
        self.text_label_radius.show()
        self.text_label_strength.show()

    def hide_settings(self):
        self.strength_slider.hide()
        self.radius_slider.hide()
        self.text_label_radius.hide()
        self.text_label_strength.hide()

    def resize(self, screen_width, screen_height):
        for i, (button, icon) in enumerate(zip(self.force_field_buttons, self.force_field_icons)):
            pos = (screen_width-135, screen_height-500+51*i)
            button.set_position(pos)
            icon.set_position((pos[0]-50, pos[1]+1))