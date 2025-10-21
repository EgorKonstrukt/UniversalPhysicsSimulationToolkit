import pymunk
import pickle
from UPST.debug.debug_manager import Debug
from UPST.config import config

class SnapshotManager:
    def __init__(self, physics_manager, camera):
        self.physics_manager = physics_manager
        self.camera = camera

    def create_snapshot(self):
        bodies_data = []
        body_map = {}
        body_index = 0

        for body in self.physics_manager.space.bodies:
            if body is self.physics_manager.static_body:
                continue
            body_map[body] = body_index
            body_index += 1

            shapes_data = []
            for shape in body.shapes:
                shape_data = {
                    'type': shape.__class__.__name__,
                    'friction': shape.friction,
                    'elasticity': shape.elasticity,
                    'color': shape.color
                }
                if isinstance(shape, pymunk.Circle):
                    shape_data['radius'] = shape.radius
                elif isinstance(shape, pymunk.Poly):
                    shape_data['vertices'] = [v for v in shape.get_vertices()]
                shapes_data.append(shape_data)

            body_data = {
                'position': body.position, 'angle': body.angle,
                'velocity': body.velocity, 'angular_velocity': body.angular_velocity,
                'mass': body.mass, 'moment': body.moment,
                'shapes': shapes_data
            }
            bodies_data.append(body_data)

        constraints_data = []
        for constraint in self.physics_manager.space.constraints:
            if constraint.a in body_map and constraint.b in body_map:
                const_data = {
                    'type': constraint.__class__.__name__,
                    'a': body_map[constraint.a],
                    'b': body_map[constraint.b],
                    'anchor_a': constraint.anchor_a,
                    'anchor_b': constraint.anchor_b,
                }
                if isinstance(constraint, pymunk.DampedSpring):
                    const_data['rest_length'] = constraint.rest_length
                    const_data['stiffness'] = constraint.stiffness
                    const_data['damping'] = constraint.damping
                constraints_data.append(const_data)

        static_lines_data = []
        for line in self.physics_manager.static_lines:
            line_data = {
                "friction": line.friction,
                "elasticity": line.elasticity,
                "color": getattr(line, "color", (200, 200, 200, 255))
            }
            if isinstance(line, pymunk.Poly):
                line_data["type"] = "Poly"
                line_data["vertices"] = [tuple(v) for v in line.get_vertices()]
            elif isinstance(line, pymunk.Segment):
                line_data["type"] = "Segment"
                line_data["a"] = tuple(line.a)
                line_data["b"] = tuple(line.b)
                line_data["radius"] = line.radius
            static_lines_data.append(line_data)

        snapshot = {
            'camera_scaling': self.camera.scaling,
            'camera_rotation': self.camera.rotation,
            'bodies': bodies_data,
            'constraints': constraints_data,
            'static_lines': static_lines_data
        }

        dumped_snapshot = pickle.dumps(snapshot)
        Debug.log_warning(message="Size: " + str(len(dumped_snapshot)), category="Snapshot")
        return dumped_snapshot

    def load_snapshot(self, snapshot_data):
        data = pickle.loads(snapshot_data)

        self.physics_manager.delete_all()

        self.physics_manager.space.iterations = data.get('physics_iterations', 10)
        self.physics_manager.simulation_frequency = data.get('simulation_frequency', 60)
        self.camera.translation = data.get('camera_translation', pymunk.Transform())
        self.camera.scaling = data.get('camera_scaling', 1.0)
        self.camera.target_scaling = self.camera.scaling
        self.camera.rotation = data.get('camera_rotation', 0)

        loaded_bodies = []
        for body_data in data['bodies']:
            body = pymunk.Body(body_data['mass'], body_data['moment'])
            body.position = pymunk.Vec2d(*body_data['position'])
            body.angle = body_data['angle']
            body.velocity = pymunk.Vec2d(*body_data['velocity'])
            body.angular_velocity = body_data['angular_velocity']

            shapes = []
            for shape_data in body_data['shapes']:
                shape_type = shape_data['type']
                if shape_type == 'Circle':
                    shape = pymunk.Circle(body, shape_data['radius'])
                elif shape_type == 'Poly':
                    vertices = [pymunk.Vec2d(*v) for v in shape_data['vertices']]
                    shape = pymunk.Poly(body, vertices)
                else:
                    continue
                shape.friction = shape_data['friction']
                shape.elasticity = shape_data['elasticity']
                shape.color = shape_data.get('color', (200, 200, 200, 255))
                shapes.append(shape)

            self.physics_manager.space.add(body, *shapes)
            loaded_bodies.append(body)

        for const_data in data.get('constraints', []):
            body_a = loaded_bodies[const_data['a']]
            body_b = loaded_bodies[const_data['b']]
            const_type = const_data['type']

            constraint = None
            if const_type == 'DampedSpring':
                constraint = pymunk.DampedSpring(body_a, body_b,
                                                 pymunk.Vec2d(*const_data['anchor_a']), pymunk.Vec2d(*const_data['anchor_b']),
                                                 const_data['rest_length'], const_data['stiffness'],
                                                 const_data['damping'])
            elif const_type == 'PinJoint':
                constraint = pymunk.PinJoint(body_a, body_b, pymunk.Vec2d(*const_data['anchor_a']), pymunk.Vec2d(*const_data['anchor_b']))
            elif const_type == 'PivotJoint':
                constraint = pymunk.PivotJoint(body_a, body_b, pymunk.Vec2d(*const_data['anchor_a']), pymunk.Vec2d(*const_data['anchor_b']))

            if constraint:
                self.physics_manager.add_constraint(constraint)

        for line_data in data.get("static_lines", []):
            if line_data["type"] == "Poly":
                vertices = [pymunk.Vec2d(*v) for v in line_data["vertices"]]
                line = pymunk.Poly(self.physics_manager.static_body, vertices)
            elif line_data["type"] == "Segment":
                a = pymunk.Vec2d(*line_data["a"])
                b = pymunk.Vec2d(*line_data["b"])
                line = pymunk.Segment(self.physics_manager.static_body, a, b, line_data["radius"])
            else:
                continue

            line.friction = line_data["friction"]
            line.elasticity = line_data["elasticity"]
            line.color = line_data.get("color", (200, 200, 200, 255))
            self.physics_manager.static_lines.append(line)
            self.physics_manager.space.add(line)

        # print("loaded snapshot!" + str(snapshot_data))


