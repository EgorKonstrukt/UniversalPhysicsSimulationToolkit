import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UIHorizontalSlider, UILabel, UIButton, UITextEntryLine, UIImage, \
    UIPanel, UITextBox, UISelectionList
from pygame_gui.windows import UIConsoleWindow
import pygame
import pymunk
import math


class ContextMenu:
    def __init__(self, manager, ui_manager):
        self.manager = manager
        self.ui_manager = ui_manager
        self.context_menu = None
        self.context_menu_list = None
        self.clicked_object = None
        self.properties_window = None
        self.create_menu()

    def create_menu(self):
        self.context_menu = UIPanel(
            relative_rect=pygame.Rect(0, 0, 250, 400),
            manager=self.manager,
            visible=False
        )
        menu_items = [
            'Delete Object',
            'Properties',
            'Duplicate',
            'Freeze/Unfreeze',
            'Set Velocity',
            'Set Angular Velocity',
            'Set Mass',
            'Set Friction',
            'Set Elasticity',
            'Add Force',
            'Add Torque',
            'Reset Position',
            'Reset Rotation',
            'Make Static',
            'Make Dynamic',
            'Select for Debug'
        ]

        self.context_menu_list = UISelectionList(
            relative_rect=pygame.Rect(0, 0, 250, 400),
            item_list=menu_items,
            container=self.context_menu,
            manager=self.manager
        )

    def show_menu(self, position, clicked_object):
        self.clicked_object = clicked_object
        self.context_menu.set_position(position)
        self.context_menu.show()

    def hide(self):
        self.context_menu.hide()

    def process_event(self, event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
                if event.ui_element == self.context_menu_list:
                    self.handle_selection(event.text)
                    self.context_menu.hide()

    def handle_selection(self, selection):
        if not self.clicked_object:
            return
        if selection == 'Properties':
            self.open_properties_window()
        elif selection == 'Delete Object':
            self.delete_object()
        elif selection == 'Duplicate':
            self.duplicate_object()
        elif selection == 'Freeze/Unfreeze':
            self.toggle_freeze_object()
        elif selection == 'Set Velocity':
            self.set_velocity_dialog()
        elif selection == 'Set Angular Velocity':
            self.set_angular_velocity_dialog()
        elif selection == 'Set Mass':
            self.set_mass_dialog()
        elif selection == 'Set Friction':
            self.set_friction_dialog()
        elif selection == 'Set Elasticity':
            self.set_elasticity_dialog()
        elif selection == 'Add Force':
            self.add_force_dialog()
        elif selection == 'Add Torque':
            self.add_torque_dialog()
        elif selection == 'Reset Position':
            self.reset_position()
        elif selection == 'Reset Rotation':
            self.reset_rotation()
        elif selection == 'Make Static':
            self.make_static()
        elif selection == 'Make Dynamic':
            self.make_dynamic()
        elif selection == 'Select for Debug':
            self.select_for_debug()

    def open_properties_window(self):
        if self.properties_window:
            self.properties_window.kill()

        self.properties_window = pygame_gui.elements.UIWindow(
            pygame.Rect(100, 100, 400, 500), manager=self.manager,
            window_display_title=f"Object Properties")

        y_offset = 10
        line_height = 25

        body = self.clicked_object

        properties = [
            f"Mass: {body.mass:.3f} kg",
            f"Moment of Inertia: {body.moment:.3f} kg⋅m²",
            f"Position: ({body.position.x:.2f}, {body.position.y:.2f}) m",
            f"Velocity: ({body.velocity.x:.2f}, {body.velocity.y:.2f}) m/s",
            f"Speed: {body.velocity.length:.2f} m/s",
            f"Angular Velocity: {body.angular_velocity:.3f} rad/s",
            f"Angle: {math.degrees(body.angle):.1f}°",
            f"Force: ({body.force.x:.2f}, {body.force.y:.2f}) N",
            f"Torque: {body.torque:.3f} N⋅m",
            f"Body Type: {body.body_type}",
            f"Is Sleeping: {body.is_sleeping}",
        ]

        kinetic_energy = 0.5 * body.mass * (body.velocity.length ** 2)
        rotational_energy = 0.5 * body.moment * (body.angular_velocity ** 2)
        total_energy = kinetic_energy + rotational_energy

        properties.extend([
            f"Kinetic Energy: {kinetic_energy:.3f} J",
            f"Rotational Energy: {rotational_energy:.3f} J",
            f"Total Energy: {total_energy:.3f} J",
        ])

        momentum = body.mass * body.velocity.length
        angular_momentum = body.moment * body.angular_velocity

        properties.extend([
            f"Linear Momentum: {momentum:.3f} kg⋅m/s",
            f"Angular Momentum: {angular_momentum:.3f} kg⋅m²/s",
        ])

        if body.shapes:
            shape = body.shapes[0]
            properties.append(f"Shape Type: {type(shape).__name__}")
            properties.append(f"Friction: {shape.friction:.3f}")
            properties.append(f"Elasticity: {shape.elasticity:.3f}")

            if isinstance(shape, pymunk.Circle):
                properties.append(f"Radius: {shape.radius:.2f} m")
                area = math.pi * shape.radius ** 2
                properties.append(f"Area: {area:.3f} m²")
            elif isinstance(shape, pymunk.Poly):
                vertices = shape.get_vertices()
                area = abs(sum((vertices[i].x * vertices[(i + 1) % len(vertices)].y -
                                vertices[(i + 1) % len(vertices)].x * vertices[i].y)
                               for i in range(len(vertices)))) / 2
                properties.append(f"Area: {area:.3f} m²")
                properties.append(f"Vertices: {len(vertices)}")

        for i, prop in enumerate(properties):
            UILabel(relative_rect=pygame.Rect(10, y_offset + i * line_height, 380, 20),
                    text=prop, container=self.properties_window, manager=self.manager)

    def delete_object(self):
        if self.clicked_object:
            self.ui_manager.physics_manager.remove_body(self.clicked_object)

    def duplicate_object(self):
        if not self.clicked_object:
            return
        body = self.clicked_object
        if not body.shapes:
            return
        shape = body.shapes[0]
        offset = pymunk.Vec2d(50, 50)
        new_position = body.position + offset

        if isinstance(shape, pymunk.Circle):
            new_body = pymunk.Body(body.mass, body.moment)
            new_shape = pymunk.Circle(new_body, shape.radius, shape.offset)
        elif isinstance(shape, pymunk.Poly):
            vertices = shape.get_vertices()
            new_body = pymunk.Body(body.mass, body.moment)
            new_shape = pymunk.Poly(new_body, vertices)
        else:
            return

        new_shape.friction = shape.friction
        new_shape.elasticity = shape.elasticity
        new_body.position = new_position
        new_body.velocity = body.velocity
        new_body.angular_velocity = body.angular_velocity

        self.ui_manager.physics_manager.space.add(new_body, new_shape)

    def toggle_freeze_object(self):
        if not self.clicked_object:
            return

        body = self.clicked_object
        if body.velocity.length < 0.1 and abs(body.angular_velocity) < 0.1:
            body.velocity = (100, 0)
            body.angular_velocity = 1.0
        else:
            body.velocity = (0, 0)
            body.angular_velocity = 0

    def set_velocity_dialog(self):
        # This is a simplified implementation. In a full implementation,
        # you would create input dialogs for these values.
        if self.clicked_object:
            self.clicked_object.velocity = (100, 0)

    def set_angular_velocity_dialog(self):
        if self.clicked_object:
            self.clicked_object.angular_velocity = 2.0

    def set_mass_dialog(self):
        if self.clicked_object:
            self.clicked_object.mass = 10.0

    def set_friction_dialog(self):
        if self.clicked_object and self.clicked_object.shapes:
            for shape in self.clicked_object.shapes:
                shape.friction = 0.8

    def set_elasticity_dialog(self):
        if self.clicked_object and self.clicked_object.shapes:
            for shape in self.clicked_object.shapes:
                shape.elasticity = 0.9

    def add_force_dialog(self):
        if self.clicked_object:
            self.clicked_object.apply_force_at_world_point((1000, 0), self.clicked_object.position)

    def add_torque_dialog(self):
        if self.clicked_object:
            self.clicked_object.torque += 1000

    def reset_position(self):
        if self.clicked_object:
            self.clicked_object.position = (0, 0)
            self.clicked_object.velocity = (0, 0)

    def reset_rotation(self):
        if self.clicked_object:
            self.clicked_object.angle = 0
            self.clicked_object.angular_velocity = 0

    def make_static(self):
        if self.clicked_object:
            self.clicked_object.body_type = pymunk.Body.STATIC

    def make_dynamic(self):
        if self.clicked_object:
            self.clicked_object.body_type = pymunk.Body.DYNAMIC

    def select_for_debug(self):
        if self.clicked_object and self.ui_manager.physics_debug_manager:
            self.ui_manager.physics_debug_manager.selected_body = self.clicked_object
            print(f"Selected body for debug: {self.clicked_object}")