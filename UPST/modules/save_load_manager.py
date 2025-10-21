import tkinter as tk
from tkinter import filedialog
from UPST.config import config
import pymunk
import pickle
import traceback

from UPST.debug.debug_manager import Debug

class SaveLoadManager:
    def __init__(self, physics_manager, camera, ui_manager, sound_manager):
        self.physics_manager = physics_manager
        self.camera = camera
        self.ui_manager = ui_manager
        self.sound_manager = sound_manager

    def save_world(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(defaultextension=".ngsv", filetypes=[("Newgodoo Save File", "*.ngsv")])
        if not file_path:
            self.sound_manager.play('load_error')
            Debug.log_warning(message="Canceled..." + str(file_path), category="SaveLoadManager")

            return

        data_to_save = {
            'version': config.app.version,
            'iterations': self.physics_manager.space.iterations,
            'sim_freq': self.physics_manager.simulation_frequency,
            'camera_translation': self.camera.translation,
            'camera_scaling': self.camera.scaling,
            'camera_rotation': self.camera.rotation,
            'bodies': [],
            'constraints': [],
            'static_lines': []
        }

        body_map = {body: i for i, body in enumerate(self.physics_manager.space.bodies)}

        for body in self.physics_manager.space.bodies:
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
                    shape_data['vertices'] = shape.get_vertices()
                shapes_data.append(shape_data)

            body_data = {
                'position': body.position, 'angle': body.angle,
                'velocity': body.velocity, 'angular_velocity': body.angular_velocity,
                'mass': body.mass, 'moment': body.moment,
                'shapes': shapes_data
            }
            data_to_save['bodies'].append(body_data)

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

                data_to_save['constraints'].append(const_data)

        try:
            with open(file_path, "wb") as f:
                pickle.dump(data_to_save, f)
            self.ui_manager.console_window.add_output_line_to_log("Save successful!")
            Debug.log_succes(message="Saving! file name: " + str(file_path), category="SaveLoadManager")
            self.sound_manager.play('save_done')
        except Exception as e:
            self.ui_manager.console_window.add_output_line_to_log(f"Save error: {e}")
            self.sound_manager.play('error')
            Debug.log_exception(message="Error! file name: " + str(file_path), category="SaveLoadManager")

    def load_world(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("Newgodoo Save File", "*.ngsv")])
        if not file_path:
            Debug.log_warning(message="Canceled..." + str(file_path), category="SaveLoadManager")

            self.sound_manager.play('load_error')
            return

        try:
            with open(file_path, "rb") as f:
                data = pickle.load(f)

            self.physics_manager.delete_all()

            self.physics_manager.space.iterations = data.get('iterations', config.physics.iterations)
            self.physics_manager.simulation_frequency = data.get('sim_freq', config.physics.simulation_frequency)
            self.camera.translation = data.get('camera_translation', pymunk.Transform())
            self.camera.scaling = data.get('camera_scaling', 1.0)
            self.camera.target_scaling = self.camera.scaling
            self.camera.rotation = data.get('camera_rotation', 0)

            loaded_bodies = []
            for body_data in data['bodies']:
                # Create and add body + shapes together
                body = pymunk.Body(body_data['mass'], body_data['moment'])
                body.position = body_data['position']
                body.angle = body_data['angle']
                body.velocity = body_data['velocity']
                body.angular_velocity = body_data['angular_velocity']

                shapes = []
                for shape_data in body_data['shapes']:
                    shape_type = shape_data['type']
                    if shape_type == 'Circle':
                        shape = pymunk.Circle(body, shape_data['radius'])
                    elif shape_type == 'Poly':
                        shape = pymunk.Poly(body, shape_data['vertices'])
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
                                                     const_data['anchor_a'], const_data['anchor_b'],
                                                     const_data['rest_length'], const_data['stiffness'],
                                                     const_data['damping'])
                elif const_type == 'PinJoint':
                    constraint = pymunk.PinJoint(body_a, body_b, const_data['anchor_a'], const_data['anchor_b'])
                elif const_type == 'PivotJoint':
                    constraint = pymunk.PivotJoint(body_a, body_b, const_data['anchor_a'], const_data['anchor_b'])

                if constraint:
                    self.physics_manager.add_constraint(constraint)

            self.ui_manager.console_window.add_output_line_to_log("Load successful!")
            Debug.log_succes(message="Loaded! file name: " + str(file_path), category="SaveLoadManager")

            self.sound_manager.play('save_done')
        except Exception as e:
            self.ui_manager.console_window.add_output_line_to_log(f"Load error: {e}")
            self.sound_manager.play('error')
            traceback.print_exc()
            Debug.log_exception(message="Error while loading! file name: " + str(file_path), category="SaveLoadManager")
