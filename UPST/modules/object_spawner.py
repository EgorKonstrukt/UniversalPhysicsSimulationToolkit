import traceback
import math
import pymunk
import random
from UPST.config import Config
from UPST.sound.sound_synthesizer import synthesizer


class ObjectSpawner:
    """
    Handles the creation of different physics objects.
    """

    def __init__(self, physics_manager, ui_manager, sound_manager):
        self.physics_manager = physics_manager
        self.ui_manager = ui_manager
        self.sound_manager = sound_manager


    def get_random_color_from_theme(self):
        theme = Config.world.themes.get(Config.world.current_theme, Config.world.themes["Classic"])
        r_range, g_range, b_range = theme.shape_color_range
        r = random.randint(r_range[0], r_range[1])
        g = random.randint(g_range[0], g_range[1])
        b = random.randint(b_range[0], b_range[1])
        return (r, g, b, 255)

    def spawn_dragged(self, shape_type, start_pos, end_pos):
        method_name = f"spawn_{shape_type.lower()}_dragged"
        spawn_method = getattr(self, method_name, None)
        if spawn_method:
            spawn_method(start_pos, end_pos)
            synthesizer.play_frequency(1630, duration=0.03, waveform='sine')

        else:
            self.ui_manager.console_window.add_output_line_to_log(
                f"Error: Drag spawn method for '{shape_type}' not found")



    def spawn_circle_dragged(self, start_pos, end_pos):
        try:
            start = pymunk.Vec2d(*start_pos)
            end = pymunk.Vec2d(*end_pos)
            radius = (start - end).length
        except (TypeError, ValueError) as e:
            print("Error creating Vec2d from positions:", e)
            return

        if radius <= 0:
            return  # Prevent invalid circle

        inputs = self.ui_manager.circle_inputs
        mass = radius * math.pi / 10
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = start_pos
        shape = pymunk.Circle(body, radius)

        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())

        if self.ui_manager.circle_color_random:
            shape.color = self.get_random_color_from_theme()
        else:
            r, g, b = [s.get_current_value() for s in self.ui_manager.circle_color_sliders]
            shape.color = (r, g, b, 255)

        self.physics_manager.add_body_shape(body, shape)

    def spawn_rectangle_dragged(self, start_pos, end_pos):
        try:
            start = pymunk.Vec2d(*start_pos)
            end = pymunk.Vec2d(*end_pos)
            delta = end - start
            size_x = abs(delta.x)/2
            size_y = abs(delta.y)/2
        except (TypeError, ValueError) as e:
            print("Error creating Vec2d from positions:", e)
            return

        if size_x <= 0 or size_y <= 0:
            return

        center = (start + end) / 2

        inputs = self.ui_manager.rect_inputs
        mass = (size_x * size_y) / 200
        moment = pymunk.moment_for_box(mass, (size_x * 2, size_y * 2))
        body = pymunk.Body(mass, moment)
        body.position = center
        points = [(-size_x, -size_y), (-size_x, size_y), (size_x, size_y), (size_x, -size_y)]
        shape = pymunk.Poly(body, points)

        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())

        if self.ui_manager.rectangle_color_random:
            shape.color = self.get_random_color_from_theme()
        else:
            r, g, b = [s.get_current_value() for s in self.ui_manager.rectangle_color_sliders]
            shape.color = (r, g, b, 255)

        self.physics_manager.add_body_shape(body, shape)

    def spawn_triangle_dragged(self, start_pos, end_pos):
        try:
            start = pymunk.Vec2d(*start_pos)
            end = pymunk.Vec2d(*end_pos)
            delta = end - start
            size = delta.length / 2
        except (TypeError, ValueError) as e:
            print("Error creating Vec2d from positions:", e)
            return

        if size <= 0:
            return

        inputs = self.ui_manager.triangle_inputs
        points = []
        for i in range(3):
            angle = i * (2 * math.pi / 3)
            points.append((size * math.cos(angle), size * math.sin(angle)))

        mass = (size ** 2) / 200
        moment = pymunk.moment_for_poly(mass, points)
        body = pymunk.Body(mass, moment)
        body.position = start_pos
        shape = pymunk.Poly(body, points)

        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())

        if self.ui_manager.triangle_color_random:
            shape.color = self.get_random_color_from_theme()
        else:
            r, g, b = [s.get_current_value() for s in self.ui_manager.triangle_color_sliders]
            shape.color = (r, g, b, 255)

        self.physics_manager.add_body_shape(body, shape)

    def spawn_polyhedron_dragged(self, start_pos, end_pos):
        try:
            start = pymunk.Vec2d(*start_pos)
            end = pymunk.Vec2d(*end_pos)
            delta = end - start
            radius = delta.length / 2
        except (TypeError, ValueError) as e:
            print("Error creating Vec2d from positions:", e)
            return

        if radius <= 0:
            return

        inputs = self.ui_manager.poly_inputs
        faces = int(inputs['faces_entry'].get_text())
        points = []
        for i in range(faces):
            angle = i * (2 * math.pi / faces)
            points.append((radius * math.cos(angle), radius * math.sin(angle)))

        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += (x1 * y2 - x2 * y1)
        mass = (abs(area) / 2) / 100

        moment = pymunk.moment_for_poly(mass, points)
        body = pymunk.Body(mass, moment)
        body.position = start_pos
        shape = pymunk.Poly(body, points)

        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())

        if self.ui_manager.poly_color_random:
            shape.color = self.get_random_color_from_theme()
        else:
            r, g, b = [s.get_current_value() for s in self.ui_manager.poly_color_sliders]
            shape.color = (r, g, b, 255)

        self.physics_manager.add_body_shape(body, shape)

    def spawn(self, shape_type, position):
        try:
            spawn_method_name = f"spawn_{shape_type.lower()}"
            spawn_method = getattr(self, spawn_method_name, None)
            if spawn_method:
                spawn_method(position)
                synthesizer.play_frequency(1630, duration=0.03, waveform='sine')

            else:
                self.ui_manager.console_window.add_output_line_to_log(f"Error: Unknown spawn tool '{shape_type}'")
        except Exception as e:
            synthesizer.play_frequency(630, duration=0.1, waveform='sine')
            traceback.print_exc()
            self.ui_manager.console_window.add_output_line_to_log(f"Error spawning object: {e}")

    def spawn_circle(self, position):
        inputs = self.ui_manager.circle_inputs
        radius = float(inputs['radius_entry'].get_text())
        mass = radius * math.pi / 10
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Circle(body, radius)
        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())

        if self.ui_manager.circle_color_random:
            shape.color = self.get_random_color_from_theme()
        else:
            r, g, b = [s.get_current_value() for s in self.ui_manager.circle_color_sliders]
            shape.color = (r, g, b, 255)

        self.physics_manager.add_body_shape(body, shape)

    def spawn_rectangle(self, position, size):
        inputs = self.ui_manager.rect_inputs
        if inputs: size = (float(inputs['size_x_entry'].get_text()), float(inputs['size_y_entry'].get_text()))
        points = [(-size[0], -size[1]), (-size[0], size[1]), (size[0], size[1]), (size[0], -size[1])]
        mass = (size[0] * size[1]) / 200
        moment = pymunk.moment_for_box(mass, (2 * size[0], 2 * size[1]))
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Poly(body, points)
        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())

        if self.ui_manager.rectangle_color_random:
            shape.color = self.get_random_color_from_theme()
        else:
            r, g, b = [s.get_current_value() for s in self.ui_manager.rectangle_color_sliders]
            shape.color = (r, g, b, 255)

        self.physics_manager.add_body_shape(body, shape)

    def spawn_triangle(self, position):
        inputs = self.ui_manager.triangle_inputs
        radius = float(inputs['size_entry'].get_text())
        points = []
        for i in range(3):
            angle = i * (2 * math.pi / 3)
            points.append((radius * math.cos(angle), radius * math.sin(angle)))
        mass = (radius ** 2) / 200
        moment = pymunk.moment_for_poly(mass, points)
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Poly(body, points)
        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())
        shape.color = self.get_random_color_from_theme()
        self.physics_manager.add_body_shape(body, shape)

    def spawn_polyhedron(self, position):
        inputs = self.ui_manager.poly_inputs
        faces = int(inputs['faces_entry'].get_text())
        radius = float(inputs['size_entry'].get_text())
        points = []
        for i in range(faces):
            angle = i * (2 * math.pi / faces)
            points.append((radius * math.cos(angle), radius * math.sin(angle)))

        area = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area += (x1 * y2 - x2 * y1)
        mass = (abs(area) / 2) / 100

        moment = pymunk.moment_for_poly(mass, points)
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Poly(body, points)
        shape.friction = float(inputs['friction_entry'].get_text())
        shape.elasticity = float(inputs['elasticity_entry'].get_text())
        shape.color = self.get_random_color_from_theme()
        self.physics_manager.add_body_shape(body, shape)

    def spawn_spam(self, position):
        for _ in range(50):
            shape_type = random.choice(["circle", "rectangle", "triangle", "polyhedron"])
            offset_pos = (position[0] + random.uniform(-150, 150), position[1] + random.uniform(-150, 150))
            self.spawn(shape_type, offset_pos)

    def spawn_human(self, position):
        parts = []
        # Head
        head_body = pymunk.Body(10, pymunk.moment_for_circle(10, 0, 30))
        head_body.position = position
        head_shape = pymunk.Circle(head_body, 30)
        self.physics_manager.add_body_shape(head_body, head_shape)
        parts.append(head_body)

        # Torso
        torso_body = pymunk.Body(20, pymunk.moment_for_box(20, (20, 80)))
        torso_body.position = position[0], position[1] - 30 - 40
        torso_shape = pymunk.Poly.create_box(torso_body, (20, 80))
        self.physics_manager.add_body_shape(torso_body, torso_shape)
        parts.append(torso_body)

        # Joints
        head_torso_joint = pymunk.PinJoint(head_body, torso_body, (0, -30), (0, 40))
        self.physics_manager.space.add(head_torso_joint)
