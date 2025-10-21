import pygame
import math
import pymunk
import threading
import queue
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from UPST.config import Config
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.debug.debug_manager import Debug
from UPST.modules.profiler import profile


@dataclass
class PhysicsDebugSettings:
    show_velocity_vectors: bool = True
    show_acceleration_vectors: bool = True
    show_forces: bool = True
    show_center_of_mass: bool = True
    show_angular_velocity: bool = True
    show_energy_meters: bool = True
    show_colliders: bool = False
    show_sleep_state: bool = False
    show_object_info: bool = False
    show_trails: bool = True
    show_momentum_vectors: bool = False
    show_angular_momentum: bool = True
    show_impulse_vectors: bool = False
    show_contact_forces: bool = False
    show_friction_forces: bool = False
    show_normal_forces: bool = False
    show_stress_visualization: bool = False
    show_deformation_energy: bool = False
    show_rotation_axes: bool = True
    show_velocity_profiles: bool = False
    show_phase_space: bool = False
    show_lagrangian_mechanics: bool = False
    show_hamiltonian_mechanics: bool = False
    show_conservation_laws: bool = False
    show_stability_analysis: bool = False
    show_resonance_analysis: bool = False
    vector_scale: float = 0.025
    text_scale: float = 1.0
    energy_bar_height: float = 20.0
    trail_length: int = 50
    phase_space_samples: int = 100
    show_constraints: bool = True
    constraint_color: Tuple[int, int, int] = (255, 200, 0)
    show_constraint_info: bool = True
    velocity_color: Tuple[int, int, int] = (0, 255, 0)
    acceleration_color: Tuple[int, int, int] = (255, 0, 0)
    force_color: Tuple[int, int, int] = (255, 255, 0)
    com_color: Tuple[int, int, int] = (255, 255, 255)
    angular_color: Tuple[int, int, int] = (255, 0, 255)
    kinetic_color: Tuple[int, int, int] = (0, 255, 255)
    potential_color: Tuple[int, int, int] = (0, 0, 255)
    momentum_color: Tuple[int, int, int] = (255, 128, 0)
    angular_momentum_color: Tuple[int, int, int] = (128, 255, 0)
    impulse_color: Tuple[int, int, int] = (255, 0, 128)
    contact_color: Tuple[int, int, int] = (255, 255, 255)
    friction_color: Tuple[int, int, int] = (128, 128, 255)
    normal_color: Tuple[int, int, int] = (255, 128, 128)
    stress_color: Tuple[int, int, int] = (255, 200, 200)
    collider_color: Tuple[int, int, int] = (128, 128, 128)
    sleep_color: Tuple[int, int, int] = (64, 64, 64)
    show_vector_labels: bool = True
    show_energy_values: bool = True
    show_coordinate_system: bool = True
    show_scientific_notation: bool = False
    precision_digits: int = 3
    info_panel_position: Tuple[int, int] = (10, Config.app.screen_height - 350)


class PhysicsDebugManager:
    def __init__(self, physics_manager, camera, plotter):
        self.physics_manager = physics_manager
        self.camera = camera
        self.plotter = plotter
        self.settings = PhysicsDebugSettings()
        self.font_small = pygame.font.Font(None, 12)
        self.font_medium = pygame.font.Font(None, 16)
        self.font_large = pygame.font.Font(None, 20)
        self.previous_velocities: Dict[pymunk.Body, Tuple[float, float]] = {}
        self.previous_angular_velocities: Dict[pymunk.Body, float] = {}
        self.previous_positions: Dict[pymunk.Body, Tuple[float, float]] = {}
        self.previous_time = 0.0
        self.dt_history: List[float] = []
        self.trails: Dict[pymunk.Body, List[Tuple[float, float]]] = {}
        self.velocity_history: Dict[pymunk.Body, List[Tuple[float, float]]] = {}
        self.energy_history: Dict[pymunk.Body, List[Tuple[float, float, float]]] = {}
        self.phase_space_data: Dict[pymunk.Body, List[Tuple[float, float]]] = {}
        self.collision_impulses: Dict[pymunk.Body, List[Tuple[float, float, float]]] = {}
        self.contact_forces: Dict[pymunk.Body, List[Tuple[float, float, float, float]]] = {}
        self.info_panel_visible = True
        self.selected_body: Optional[pymunk.Body] = None
        self.simulation_start_time = pygame.time.get_ticks() / 1000.0
        self.total_system_momentum = (0.0, 0.0)
        self.total_system_angular_momentum = 0.0
        self.total_system_energy = 0.0
        self.system_center_of_mass = (0.0, 0.0)
        self.plot_parameters: Dict[pymunk.Body, List[str]] = {}

        self._task_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def add_plot_parameter(self, body: pymunk.Body, parameter: str):
        if body not in self.plot_parameters:
            self.plot_parameters[body] = []
        if parameter not in self.plot_parameters[body]:
            self.plot_parameters[body].append(parameter)
            Debug.log(f"Added {parameter} for plotting for body {body.mass:.2f}kg", "PhysicsDebug")

    def clear_plot_data(self):
        self.plotter.clear_data()
        self.plot_parameters.clear()
        Debug.log("Cleared all plot data", "PhysicsDebug")

    def update(self, delta_time: float):
        current_time = pygame.time.get_ticks() / 1000.0
        self.dt_history.append(delta_time)
        if len(self.dt_history) > 100:
            self.dt_history.pop(0)

        self._task_queue.put(("update_system_properties", {}))
        while not self._result_queue.empty():
            task_type, result = self._result_queue.get()
            if task_type == "update_system_properties":
                (self.total_system_momentum,
                 self.total_system_angular_momentum,
                 self.total_system_energy,
                 self.system_center_of_mass) = result

        for body in self.physics_manager.space.bodies:
            if body.body_type == pymunk.Body.DYNAMIC:
                self._update_body_debug(body, delta_time, current_time)

        if self.settings.show_constraints:
            for constraint in self.physics_manager.space.constraints:
                self._draw_constraint(constraint)

        if self.settings.show_conservation_laws:
            self._draw_conservation_laws()

        if self.settings.show_phase_space and self.selected_body:
            self._draw_phase_space_diagram(self.selected_body)

        self.previous_time = current_time

    def _worker_loop(self):
        while True:
            task = self._task_queue.get()
            if task is None:
                break
            task_type, kwargs = task
            if task_type == "update_system_properties":
                bodies = [b for b in self.physics_manager.space.bodies if b.body_type == pymunk.Body.DYNAMIC]
                if not bodies:
                    self._result_queue.put((task_type, ((0.0, 0.0), 0.0, 0.0, (0.0, 0.0))))
                    continue

                total_mass = sum(b.mass for b in bodies)
                total_momentum_x = sum(b.mass * b.velocity.x for b in bodies)
                total_momentum_y = sum(b.mass * b.velocity.y for b in bodies)
                total_momentum = (total_momentum_x, total_momentum_y)

                total_angular_momentum = sum(
                    b.moment * b.angular_velocity +
                    b.mass * (b.position.x * b.velocity.y - b.position.y * b.velocity.x)
                    for b in bodies
                )

                com_x = sum(b.mass * b.position.x for b in bodies) / total_mass
                com_y = sum(b.mass * b.position.y for b in bodies) / total_mass
                system_com = (com_x, com_y)

                total_ke = sum(0.5 * b.mass * (b.velocity.length ** 2) +
                               0.5 * b.moment * (b.angular_velocity ** 2) for b in bodies)
                gravity_magnitude = math.hypot(*self.physics_manager.space.gravity)
                total_pe = sum(b.mass * gravity_magnitude *
                               max(0, (Config.app.screen_height - b.position.y) * 0.001) for b in bodies)

                elastic_pe = 0.0
                for constraint in self.physics_manager.space.constraints:
                    if isinstance(constraint, pymunk.DampedSpring):
                        a, b = constraint.a, constraint.b
                        pa = a.position + constraint.anchor_a.rotated(a.angle) if hasattr(constraint, 'anchor_a') else a.position
                        pb = b.position + constraint.anchor_b.rotated(b.angle) if hasattr(constraint, 'anchor_b') else b.position
                        current_length = math.hypot(pb.x - pa.x, pb.y - pa.y)
                        displacement = current_length - constraint.rest_length
                        elastic_pe += 0.5 * constraint.stiffness * displacement ** 2

                total_energy = total_ke + total_pe + elastic_pe
                self._result_queue.put((task_type, (total_momentum, total_angular_momentum, total_energy, system_com)))

    def _calculate_body_properties(self, body_mass, body_moment, body_velocity_x, body_velocity_y, body_angular_velocity, body_position_y, gravity_magnitude):
        velocity_length = math.sqrt(body_velocity_x**2 + body_velocity_y**2)
        kinetic_energy = 0.5 * body_mass * (velocity_length ** 2)
        rotational_energy = 0.5 * body_moment * (body_angular_velocity ** 2)
        potential_energy = body_mass * gravity_magnitude * max(0, (Config.app.screen_height - body_position_y) * 0.001)
        total_energy = kinetic_energy + rotational_energy + potential_energy
        linear_momentum = body_mass * velocity_length
        angular_momentum = body_moment * body_angular_velocity
        return velocity_length, kinetic_energy, rotational_energy, potential_energy, total_energy, linear_momentum, angular_momentum

    def _update_body_debug(self, body: pymunk.Body, dt: float, t: float):
        pos = body.position
        velocity_length, kinetic_energy, rotational_energy, potential_energy, total_energy, linear_momentum, angular_momentum = \
            self._calculate_body_properties(body.mass, body.moment, body.velocity.x, body.velocity.y, body.angular_velocity, body.position.y, math.hypot(*self.physics_manager.space.gravity))

        if body in self.plot_parameters:
            for param in self.plot_parameters[body]:
                key = f"{body.mass:.1f}kg_{param}"
                group = f"Body {body.mass:.1f}kg"
                value = 0.0
                if param == 'Velocity Length':
                    value = velocity_length
                elif param == 'Angular Velocity':
                    value = body.angular_velocity
                elif param == 'Kinetic Energy':
                    value = kinetic_energy
                elif param == 'Potential Energy':
                    value = potential_energy
                elif param == 'Total Energy':
                    value = total_energy
                elif param == 'Mass':
                    value = body.mass
                elif param == 'Moment of Inertia':
                    value = body.moment
                elif param == 'Linear Momentum':
                    value = linear_momentum
                elif param == 'Angular Momentum':
                    value = angular_momentum
                elif param == 'Force X':
                    value = body.force.x
                elif param == 'Force Y':
                    value = body.force.y
                elif param == 'Torque':
                    value = body.torque
                self.plotter.add_data(key, value, group)

        if self.settings.show_trails:
            self._update_trail(body, pos)
        if self.settings.show_velocity_profiles:
            self._update_velocity_history(body)
        if self.settings.show_phase_space:
            self._update_phase_space_data(body)
        if self.settings.show_center_of_mass:
            self._draw_center_of_mass(body, pos)
        if self.settings.show_colliders:
            self._draw_colliders(body)
        if self.settings.show_sleep_state and body.is_sleeping:
            self._draw_sleep_state(body, pos)
        if self.settings.show_velocity_vectors:
            self._draw_velocity_vector(body, pos)
        if self.settings.show_acceleration_vectors:
            self._draw_acceleration_vector(body, pos, dt)
        if self.settings.show_forces:
            self._draw_forces(body, pos)
        if self.settings.show_momentum_vectors:
            self._draw_momentum_vector(body, pos)
        if self.settings.show_angular_velocity:
            self._draw_angular_velocity(body, pos, t)
        if self.settings.show_angular_momentum:
            self._draw_angular_momentum(body, pos)
        if self.settings.show_energy_meters:
            self._draw_energy_meters(body, pos)
        if self.settings.show_deformation_energy:
            self._draw_deformation_energy(body, pos)
        if self.settings.show_rotation_axes:
            self._draw_rotation_axes(body, pos)
        if self.settings.show_stress_visualization:
            self._draw_stress_visualization(body, pos)
        if self.settings.show_stability_analysis:
            self._draw_stability_analysis(body, pos)
        if self.settings.show_object_info:
            self._draw_object_info(body, pos)
        if self.settings.show_lagrangian_mechanics:
            self._draw_lagrangian_info(body, pos)
        if self.settings.show_hamiltonian_mechanics:
            self._draw_hamiltonian_info(body, pos)

    def _update_trail(self, body, pos):
        if body not in self.trails:
            self.trails[body] = []
        trail = self.trails[body]
        trail.append((pos.x, pos.y))
        if len(trail) > self.settings.trail_length:
            trail.pop(0)
        for i in range(1, len(trail)):
            alpha = i / len(trail)
            color = (*self.settings.velocity_color, int(255 * alpha))
            thickness = max(1, int(3 * alpha))
            Gizmos.draw_line(trail[i - 1], trail[i], color, thickness, duration=0.1)

    def _update_velocity_history(self, body):
        if body not in self.velocity_history:
            self.velocity_history[body] = []
        history = self.velocity_history[body]
        history.append((body.velocity.x, body.velocity.y))
        if len(history) > 200:
            history.pop(0)

    @profile("_update_phase_space_data", "physics_debug_manager")
    def _update_phase_space_data(self, body):
        if body not in self.phase_space_data:
            self.phase_space_data[body] = []
        data = self.phase_space_data[body]
        data.append((body.position.x, body.velocity.x))
        if len(data) > self.settings.phase_space_samples:
            data.pop(0)

    @profile("_draw_center_of_mass", "physics_debug_manager")
    def _draw_center_of_mass(self, body, pos):
        Gizmos.draw_circle((pos.x, pos.y), 4, self.settings.com_color, thickness=2, duration=0.1)
        Gizmos.draw_cross((pos.x, pos.y), 8, self.settings.com_color, 2, duration=0.1)

    @profile("_draw_colliders", "physics_debug_manager")
    def _draw_colliders(self, body):
        for shape in body.shapes:
            if isinstance(shape, pymunk.Circle):
                center = body.local_to_world(shape.offset)
                Gizmos.draw_circle((center.x, center.y), shape.radius,
                                   self.settings.collider_color, thickness=2, duration=0.1)
                area = math.pi * shape.radius ** 2
                if self.settings.show_vector_labels:
                    Gizmos.draw_text((center.x, center.y - shape.radius - 15),
                                     f"A={area:.2f}m²", self.settings.collider_color,
                                     duration=0.1, font_size=14)
            elif isinstance(shape, pymunk.Poly):
                vertices = [body.local_to_world(v) for v in shape.get_vertices()]
                for i in range(len(vertices)):
                    next_i = (i + 1) % len(vertices)
                    Gizmos.draw_line(vertices[i], vertices[next_i],
                                     self.settings.collider_color, 2, duration=0.1)
                area = abs(sum((vertices[i].x * vertices[(i + 1) % len(vertices)].y -
                                vertices[(i + 1) % len(vertices)].x * vertices[i].y)
                               for i in range(len(vertices)))) / 2
                if self.settings.show_vector_labels:
                    centroid_x = sum(v.x for v in vertices) / len(vertices)
                    centroid_y = sum(v.y for v in vertices) / len(vertices)
                    Gizmos.draw_text((centroid_x, centroid_y - 20),
                                     f"A={area:.2f}m²", self.settings.collider_color,
                                     duration=0.1, font_size=14)

    @profile("_draw_sleep_state", "physics_debug_manager")
    def _draw_sleep_state(self, body, pos):
        fade_factor = math.sin(pygame.time.get_ticks() * 0.003) * 0.5 + 0.5
        radius = 15 + fade_factor * 5
        Gizmos.draw_circle((pos.x, pos.y), radius, self.settings.sleep_color,
                           thickness=2, duration=0.1)
        Gizmos.draw_text((pos.x - 10, pos.y - 20), "SLEEP", self.settings.sleep_color,
                         duration=0.1, font_size=14, background_color=(0, 0, 0, 128))

    @profile("_draw_velocity_vector", "physics_debug_manager")
    def _draw_velocity_vector(self, body, pos):
        velocity = body.velocity
        speed = velocity.length
        if speed > 0.01:
            scale = self.settings.vector_scale * 20
            end_x = pos.x + velocity.x * scale
            end_y = pos.y + velocity.y * scale
            thickness = max(2, min(8, int(speed * 0.1)))
            Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                              self.settings.velocity_color, thickness, duration=0.1)
            if self.settings.show_vector_labels:
                label_x = pos.x + velocity.x * scale * 0.6
                label_y = pos.y + velocity.y * scale * 0.6 - 15
                Gizmos.draw_text((label_x, label_y), f"v={speed:.{self.settings.precision_digits}f}m/s",
                                 self.settings.velocity_color, duration=0.1, font_size=14,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_acceleration_vector", "physics_debug_manager")
    def _draw_acceleration_vector(self, body, pos, dt):
        current_velocity = (body.velocity.x, body.velocity.y)
        if body in self.previous_velocities and dt > 0:
            prev_velocity = self.previous_velocities[body]
            acceleration = ((current_velocity[0] - prev_velocity[0]) / dt,
                            (current_velocity[1] - prev_velocity[1]) / dt)
            acceleration_magnitude = math.hypot(*acceleration)
            if acceleration_magnitude > 1.0:
                scale = self.settings.vector_scale * 5
                end_x = pos.x + acceleration[0] * scale
                end_y = pos.y + acceleration[1] * scale
                thickness = max(2, min(6, int(acceleration_magnitude * 0.05)))
                Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                                  self.settings.acceleration_color, thickness, duration=0.1)
                if self.settings.show_vector_labels:
                    label_x = pos.x + acceleration[0] * scale * 0.6
                    label_y = pos.y + acceleration[1] * scale * 0.6 + 15
                    Gizmos.draw_text((label_x, label_y),
                                     f"a={acceleration_magnitude:.{self.settings.precision_digits}f}m/s²",
                                     self.settings.acceleration_color, duration=0.1, font_size=14,
                                     background_color=(0, 0, 0, 128))
        self.previous_velocities[body] = current_velocity

    @profile("_draw_forces", "physics_debug_manager")
    def _draw_forces(self, body, pos):
        gravity = self.physics_manager.space.gravity
        if abs(gravity[0]) > 0.1 or abs(gravity[1]) > 0.1:
            gravitational_force = (body.mass * gravity[0], body.mass * gravity[1])
            force_magnitude = math.hypot(*gravitational_force)
            if force_magnitude > 0.1:
                scale = self.settings.vector_scale * 0.1
                end_x = pos.x + gravitational_force[0] * scale
                end_y = pos.y + gravitational_force[1] * scale
                Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                                  self.settings.force_color, 3, duration=0.1)
                if self.settings.show_vector_labels:
                    label_x = pos.x + gravitational_force[0] * scale * 0.6 + 20
                    label_y = pos.y + gravitational_force[1] * scale * 0.6
                    Gizmos.draw_text((label_x, label_y),
                                     f"F_g={force_magnitude:.{self.settings.precision_digits}f}N",
                                     self.settings.force_color, duration=0.1, font_size=14,
                                     background_color=(0, 0, 0, 128))
        net_force = body.force
        if abs(net_force.x) > 0.1 or abs(net_force.y) > 0.1:
            net_force_magnitude = math.hypot(net_force.x, net_force.y)
            scale = self.settings.vector_scale * 0.2
            end_x = pos.x + net_force.x * scale
            end_y = pos.y + net_force.y * scale
            Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                              (255, 255, 255), 4, duration=0.1)
            if self.settings.show_vector_labels:
                label_x = pos.x + net_force.x * scale * 0.6 + 30
                label_y = pos.y + net_force.y * scale * 0.6
                Gizmos.draw_text((label_x, label_y),
                                 f"F_net={net_force_magnitude:.{self.settings.precision_digits}f}N",
                                 (255, 255, 255), duration=0.1, font_size=14,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_momentum_vector", "physics_debug_manager")
    def _draw_momentum_vector(self, body, pos):
        momentum = (body.mass * body.velocity.x, body.mass * body.velocity.y)
        momentum_magnitude = math.hypot(*momentum)
        if momentum_magnitude > 0.01:
            scale = self.settings.vector_scale * 5
            end_x = pos.x + momentum[0] * scale
            end_y = pos.y + momentum[1] * scale
            thickness = max(2, min(6, int(momentum_magnitude * 0.01)))
            Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                              self.settings.momentum_color, thickness, duration=0.1)
            if self.settings.show_vector_labels:
                label_x = pos.x + momentum[0] * scale * 0.6
                label_y = pos.y + momentum[1] * scale * 0.6 + 25
                Gizmos.draw_text((label_x, label_y),
                                 f"p={momentum_magnitude:.{self.settings.precision_digits}f}kg⋅m/s",
                                 self.settings.momentum_color, duration=0.1, font_size=14,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_angular_velocity", "physics_debug_manager")
    def _draw_angular_velocity(self, body, pos, t):
        angular_velocity = body.angular_velocity
        if abs(angular_velocity) > 0.01:
            radius = 35
            offset = t * angular_velocity
            segments = 16
            arc_angle = 1.5 * math.pi
            for i in range(segments):
                angle1 = i / segments * arc_angle + offset
                angle2 = (i + 1) / segments * arc_angle + offset
                x1 = pos.x + radius * math.cos(angle1)
                y1 = pos.y + radius * math.sin(angle1)
                x2 = pos.x + radius * math.cos(angle2)
                y2 = pos.y + radius * math.sin(angle2)
                thickness = 4 if i == segments - 1 else 2
                Gizmos.draw_line((x1, y1), (x2, y2), self.settings.angular_color,
                                 thickness, duration=0.1)
            final_angle = arc_angle + offset
            arrow_start = (pos.x + radius * math.cos(final_angle),
                           pos.y + radius * math.sin(final_angle))
            direction_angle = final_angle + math.pi / 2 * (1 if angular_velocity > 0 else -1)
            arrow_end = (arrow_start[0] + 10 * math.cos(direction_angle),
                         arrow_start[1] + 10 * math.sin(direction_angle))
            Gizmos.draw_line(arrow_start, arrow_end, self.settings.angular_color,
                             5, duration=0.1)
            if self.settings.show_vector_labels:
                Gizmos.draw_text((pos.x + 40, pos.y - 10),
                                 f"ω={angular_velocity:.{self.settings.precision_digits}f}rad/s",
                                 self.settings.angular_color, duration=0.1, font_size=14,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_angular_momentum", "physics_debug_manager")
    def _draw_angular_momentum(self, body, pos):
        angular_momentum = body.moment * body.angular_velocity
        if abs(angular_momentum) > 0.01:
            radius = 25
            Gizmos.draw_circle((pos.x, pos.y), radius, self.settings.angular_momentum_color,
                               thickness=3, duration=0.1)
            if self.settings.show_vector_labels:
                Gizmos.draw_text((pos.x + 30, pos.y + 15),
                                 f"L={angular_momentum:.{self.settings.precision_digits}f}kg⋅m²/s",
                                 self.settings.angular_momentum_color, duration=0.1, font_size=14,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_energy_meters", "physics_debug_manager")
    def _draw_energy_meters(self, body, pos):
        kinetic_energy = 0.5 * body.mass * (body.velocity.length ** 2)
        rotational_energy = 0.5 * body.moment * (body.angular_velocity ** 2)
        gravity_magnitude = math.hypot(*self.physics_manager.space.gravity)
        height = max(0, (Config.app.screen_height - pos.y) * 0.001)
        potential_energy = body.mass * gravity_magnitude * height
        total_energy = kinetic_energy + rotational_energy + potential_energy
        max_energy = max(total_energy, 1)
        bar_width = 8
        bar_spacing = 12
        bar_height = self.settings.energy_bar_height
        ke_height = kinetic_energy / max_energy * bar_height
        re_height = rotational_energy / max_energy * bar_height
        pe_height = potential_energy / max_energy * bar_height
        bar_x = pos.x - 45
        Gizmos.draw_line((bar_x, pos.y), (bar_x, pos.y - ke_height),
                         self.settings.kinetic_color, bar_width, duration=0.1)
        Gizmos.draw_line((bar_x + bar_spacing, pos.y), (bar_x + bar_spacing, pos.y - re_height),
                         self.settings.angular_color, bar_width, duration=0.1)
        Gizmos.draw_line((bar_x + 2 * bar_spacing, pos.y), (bar_x + 2 * bar_spacing, pos.y - pe_height),
                         self.settings.potential_color, bar_width, duration=0.1)
        if self.settings.show_energy_values:
            Gizmos.draw_text((bar_x - 20, pos.y - bar_height - 35),
                             f"KE: {kinetic_energy:.{self.settings.precision_digits}f}J",
                             self.settings.kinetic_color, duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128), collision=True)
            Gizmos.draw_text((bar_x - 20, pos.y - bar_height - 25),
                             f"RE: {rotational_energy:.{self.settings.precision_digits}f}J",
                             self.settings.angular_color, duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128), collision=True)
            Gizmos.draw_text((bar_x - 20, pos.y - bar_height - 15),
                             f"PE: {potential_energy:.{self.settings.precision_digits}f}J",
                             self.settings.potential_color, duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128), collision=True)

    @profile("_draw_deformation_energy", "physics_debug_manager")
    def _draw_deformation_energy(self, body, pos):
        deformation_energy = 0.0
        for constraint in self.physics_manager.space.constraints:
            if isinstance(constraint, pymunk.DampedSpring):
                if constraint.a == body or constraint.b == body:
                    a_pos = constraint.a.position + constraint.anchor_a.rotated(constraint.a.angle) if hasattr(
                        constraint, 'anchor_a') else constraint.a.position
                    b_pos = constraint.b.position + constraint.anchor_b.rotated(constraint.b.angle) if hasattr(
                        constraint, 'anchor_b') else constraint.b.position
                    current_length = math.hypot(b_pos.x - a_pos.x, b_pos.y - a_pos.y)
                    displacement = current_length - constraint.rest_length
                    spring_energy = 0.5 * constraint.stiffness * displacement ** 2
                    deformation_energy += spring_energy
        if deformation_energy > 0.01:
            if self.settings.show_vector_labels:
                Gizmos.draw_text((pos.x + 50, pos.y + 35),
                                 f"E_def={deformation_energy:.{self.settings.precision_digits}f}J",
                                 self.settings.stress_color, duration=0.1, font_size=14,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_rotation_axes", "physics_debug_manager")
    def _draw_rotation_axes(self, body, pos):
        if abs(body.angular_velocity) > 0.01:
            axis_length = 50
            Gizmos.draw_line((pos.x, pos.y - axis_length), (pos.x, pos.y + axis_length),
                             (100, 100, 100), 2, duration=0.1)
            Gizmos.draw_line((pos.x - axis_length, pos.y), (pos.x + axis_length, pos.y),
                             (100, 100, 100), 2, duration=0.1)
            Gizmos.draw_circle((pos.x, pos.y), 8, (255, 255, 255), thickness=2, duration=0.1)

    @profile("_draw_stress_visualization", "physics_debug_manager")
    def _draw_stress_visualization(self, body, pos):
        acceleration_magnitude = 0.0
        if body in self.previous_velocities:
            dt = self.dt_history[-1] if self.dt_history else 0.016
            if dt > 0:
                prev_vel = self.previous_velocities[body]
                curr_vel = (body.velocity.x, body.velocity.y)
                acceleration = ((curr_vel[0] - prev_vel[0]) / dt, (curr_vel[1] - prev_vel[1]) / dt)
                acceleration_magnitude = math.hypot(*acceleration)
        stress_factor = min(1.0, acceleration_magnitude / 100.0)
        if stress_factor > 0.1:
            stress_radius = 20 + stress_factor * 15
            stress_alpha = int(255 * stress_factor)
            stress_color = (*self.settings.stress_color[:3], stress_alpha)
            Gizmos.draw_circle((pos.x, pos.y), stress_radius, stress_color, thickness=5, duration=0.1)
            if self.settings.show_vector_labels:
                Gizmos.draw_text((pos.x + 25, pos.y + 25),
                                 f"σ={stress_factor:.{self.settings.precision_digits}f}",
                                 self.settings.stress_color, duration=0.1, font_size=12,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_stability_analysis", "physics_debug_manager")
    def _draw_stability_analysis(self, body, pos):
        velocity_magnitude = body.velocity.length
        angular_velocity_magnitude = abs(body.angular_velocity)
        stability_metric = 1.0 / (1.0 + velocity_magnitude + angular_velocity_magnitude)
        if stability_metric < 0.8:
            instability_color = (255, int(255 * stability_metric), 0)
            Gizmos.draw_circle((pos.x, pos.y), 40, instability_color, thickness=2, duration=0.1)
            if self.settings.show_vector_labels:
                Gizmos.draw_text((pos.x + 45, pos.y),
                                 f"S={stability_metric:.{self.settings.precision_digits}f}",
                                 instability_color, duration=0.1, font_size=12,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_lagrangian_info", "physics_debug_manager")
    def _draw_lagrangian_info(self, body, pos):
        if body == self.selected_body:
            kinetic_energy = 0.5 * body.mass * (body.velocity.length ** 2) + 0.5 * body.moment * (
                        body.angular_velocity ** 2)
            gravity_magnitude = math.hypot(*self.physics_manager.space.gravity)
            height = max(0, (Config.app.screen_height - pos.y) * 0.001)
            potential_energy = body.mass * gravity_magnitude * height
            lagrangian = kinetic_energy - potential_energy
            Gizmos.draw_text((pos.x + 60, pos.y - 60),
                             f"L = T - V = {lagrangian:.{self.settings.precision_digits}f}J",
                             (255, 255, 255), duration=0.1, font_size=14,
                             background_color=(0, 0, 0, 128))
            generalized_momentum_x = body.mass * body.velocity.x
            generalized_momentum_y = body.mass * body.velocity.y
            generalized_momentum_angular = body.moment * body.angular_velocity
            Gizmos.draw_text((pos.x + 60, pos.y - 45),
                             f"∂L/∂ẋ = {generalized_momentum_x:.{self.settings.precision_digits}f}kg⋅m/s",
                             (200, 200, 200), duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128))
            Gizmos.draw_text((pos.x + 60, pos.y - 33),
                             f"∂L/∂ẏ = {generalized_momentum_y:.{self.settings.precision_digits}f}kg⋅m/s",
                             (200, 200, 200), duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128))
            Gizmos.draw_text((pos.x + 60, pos.y - 21),
                             f"∂L/∂θ̇ = {generalized_momentum_angular:.{self.settings.precision_digits}f}kg⋅m²/s",
                             (200, 200, 200), duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128))

    @profile("_draw_hamiltonian_info", "physics_debug_manager")
    def _draw_hamiltonian_info(self, body, pos):
        if body == self.selected_body:
            kinetic_energy = 0.5 * body.mass * (body.velocity.length ** 2) + 0.5 * body.moment * (
                        body.angular_velocity ** 2)
            gravity_magnitude = math.hypot(*self.physics_manager.space.gravity)
            height = max(0, (Config.app.screen_height - pos.y) * 0.001)
            potential_energy = body.mass * gravity_magnitude * height
            hamiltonian = kinetic_energy + potential_energy
            Gizmos.draw_text((pos.x + 60, pos.y + 10),
                             f"H = T + V = {hamiltonian:.{self.settings.precision_digits}f}J",
                             (255, 255, 255), duration=0.1, font_size=14,
                             background_color=(0, 0, 0, 128))
            canonical_momentum_x = body.mass * body.velocity.x
            canonical_momentum_y = body.mass * body.velocity.y
            canonical_momentum_angular = body.moment * body.angular_velocity
            Gizmos.draw_text((pos.x + 60, pos.y + 25),
                             f"px = {canonical_momentum_x:.{self.settings.precision_digits}f}kg⋅m/s",
                             (200, 200, 200), duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128))
            Gizmos.draw_text((pos.x + 60, pos.y + 37),
                             f"py = {canonical_momentum_y:.{self.settings.precision_digits}f}kg⋅m/s",
                             (200, 200, 200), duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128))
            Gizmos.draw_text((pos.x + 60, pos.y + 49),
                             f"pθ = {canonical_momentum_angular:.{self.settings.precision_digits}f}kg⋅m²/s",
                             (200, 200, 200), duration=0.1, font_size=12,
                             background_color=(0, 0, 0, 128))

    @profile("_draw_object_info", "physics_debug_manager")
    def _draw_object_info(self, body, pos):
        if body == self.selected_body:
            Gizmos.draw_circle((pos.x, pos.y), 35, (255, 255, 255), thickness=3, duration=0.1)
            info_x = pos.x + 120
            info_y = pos.y - 80
            Gizmos.draw_text((info_x, info_y), f"=== RIGID BODY ANALYSIS ===", (255, 255, 255),
                             duration=0.1, font_size=14, background_color=(0, 0, 0, 180))
            Gizmos.draw_text((info_x, info_y + 20), f"Mass: {body.mass:.{self.settings.precision_digits}f} kg",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 32),
                             f"Moment of Inertia: {body.moment:.{self.settings.precision_digits}f} kg⋅m²",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 44), f"Position: ({pos.x:.1f}, {pos.y:.1f}) m",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 56),
                             f"Velocity: {body.velocity.length:.{self.settings.precision_digits}f} m/s",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 68),
                             f"Angular velocity: {body.angular_velocity:.{self.settings.precision_digits}f} rad/s",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 80), f"Angle: {math.degrees(body.angle):.1f}°",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            torque = body.torque
            Gizmos.draw_text((info_x, info_y + 92), f"Torque: {torque:.{self.settings.precision_digits}f} N⋅m",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            kinetic_energy = 0.5 * body.mass * (body.velocity.length ** 2)
            rotational_energy = 0.5 * body.moment * (body.angular_velocity ** 2)
            Gizmos.draw_text((info_x, info_y + 104),
                             f"Translational KE: {kinetic_energy:.{self.settings.precision_digits}f} J",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 116),
                             f"Rotational KE: {rotational_energy:.{self.settings.precision_digits}f} J",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            angular_momentum = body.moment * body.angular_velocity
            linear_momentum = body.mass * body.velocity.length
            Gizmos.draw_text((info_x, info_y + 128),
                             f"Linear momentum: {linear_momentum:.{self.settings.precision_digits}f} kg⋅m/s",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))
            Gizmos.draw_text((info_x, info_y + 140),
                             f"Angular momentum: {angular_momentum:.{self.settings.precision_digits}f} kg⋅m²/s",
                             (255, 255, 255), duration=0.1, font_size=12, background_color=(0, 0, 0, 128))

    @profile("_draw_constraint", "physics_debug_manager")
    def _draw_constraint(self, constraint):
        a, b = constraint.a, constraint.b
        pa = a.position + constraint.anchor_a.rotated(a.angle) if hasattr(constraint, 'anchor_a') else a.position
        pb = b.position + constraint.anchor_b.rotated(b.angle) if hasattr(constraint, 'anchor_b') else b.position
        if self.settings.show_constraint_info:
            midpoint = ((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)
            constraint_type = constraint.__class__.__name__
            info_lines = [constraint_type]
            if hasattr(constraint, 'rest_length'):
                current_length = math.hypot(pb.x - pa.x, pb.y - pa.y)
                info_lines.append(f"L₀: {constraint.rest_length:.{self.settings.precision_digits}f}m")
                info_lines.append(f"L: {current_length:.{self.settings.precision_digits}f}m")
                info_lines.append(f"ΔL: {current_length - constraint.rest_length:.{self.settings.precision_digits}f}m")
            if hasattr(constraint, 'stiffness'):
                info_lines.append(f"k: {constraint.stiffness:.{self.settings.precision_digits}f}N/m")
            if hasattr(constraint, 'damping'):
                info_lines.append(f"c: {constraint.damping:.{self.settings.precision_digits}f}N⋅s/m")
            if isinstance(constraint, pymunk.DampedSpring):
                dx = pb.x - pa.x
                dy = pb.y - pa.y
                length = math.hypot(dx, dy)
                if length > 0:
                    unit_x, unit_y = dx / length, dy / length
                    spring_force_magnitude = constraint.stiffness * (length - constraint.rest_length)
                    relative_velocity = (b.velocity - a.velocity)
                    relative_velocity_along_spring = relative_velocity.dot((unit_x, unit_y))
                    damping_force_magnitude = constraint.damping * relative_velocity_along_spring
                    total_force_magnitude = spring_force_magnitude + damping_force_magnitude
                    scale = self.settings.vector_scale * 0.3
                    force_end_x = midpoint[0] + total_force_magnitude * unit_x * scale
                    force_end_y = midpoint[1] + total_force_magnitude * unit_y * scale
                    Gizmos.draw_arrow(midpoint, (force_end_x, force_end_y), (0, 255, 255), 3, duration=0.1)
                    if self.settings.show_vector_labels:
                        Gizmos.draw_text((force_end_x + 10, force_end_y - 10),
                                         f"F_spring={total_force_magnitude:.{self.settings.precision_digits}f}N",
                                         (0, 255, 255), duration=0.1, font_size=12,
                                         background_color=(0, 0, 0, 128))
                    spring_potential_energy = 0.5 * constraint.stiffness * (length - constraint.rest_length) ** 2
                    info_lines.append(f"PE_spring: {spring_potential_energy:.{self.settings.precision_digits}f}J")
            for i, line in enumerate(info_lines):
                Gizmos.draw_text((midpoint[0], midpoint[1] + i * 15), line,
                                 self.settings.constraint_color, duration=0.1, font_size=12,
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_conservation_laws", "physics_debug_manager")
    def _draw_conservation_laws(self):
        if not self.info_panel_visible:
            return
        x = self.settings.info_panel_position[0] + 200
        y = self.settings.info_panel_position[1]
        Gizmos.draw_text((x, y), "=== CONSERVATION LAWS ===", (255, 255, 255),
                         duration=0.1, font_size=14, world_space=False,
                         background_color=(0, 0, 0, 180))
        momentum_magnitude = math.hypot(*self.total_system_momentum)
        Gizmos.draw_text((x, y + 20), f"Total momentum: {momentum_magnitude:.{self.settings.precision_digits}f} kg⋅m/s",
                         (200, 200, 200), duration=0.1, font_size=12, world_space=False,
                         background_color=(0, 0, 0, 128))
        Gizmos.draw_text((x, y + 32),
                         f"Total ang. momentum: {self.total_system_angular_momentum:.{self.settings.precision_digits}f} kg⋅m²/s",
                         (200, 200, 200), duration=0.1, font_size=12, world_space=False,
                         background_color=(0, 0, 0, 128))
        Gizmos.draw_text((x, y + 44), f"Total energy: {self.total_system_energy:.{self.settings.precision_digits}f} J",
                         (200, 200, 200), duration=0.1, font_size=12, world_space=False,
                         background_color=(0, 0, 0, 128))
        Gizmos.draw_text((x, y + 56),
                         f"System COM: ({self.system_center_of_mass[0]:.1f}, {self.system_center_of_mass[1]:.1f})",
                         (200, 200, 200), duration=0.1, font_size=12, world_space=False,
                         background_color=(0, 0, 0, 128))
        Gizmos.draw_circle(self.system_center_of_mass, 8, (255, 255, 0), thickness=3, duration=0.1)

    @profile("_draw_phase_space_diagram", "physics_debug_manager")
    def _draw_phase_space_diagram(self, body):
        if body not in self.phase_space_data or len(self.phase_space_data[body]) < 2:
            return
        data = self.phase_space_data[body]
        phase_space_x = Config.app.screen_width - 200
        phase_space_y = 100
        phase_space_size = 150
        Gizmos.draw_line((phase_space_x, phase_space_y), (phase_space_x + phase_space_size, phase_space_y),
                         (100, 100, 100), 2, duration=0.1, world_space=False)
        Gizmos.draw_line((phase_space_x, phase_space_y), (phase_space_x, phase_space_y + phase_space_size),
                         (100, 100, 100), 2, duration=0.1, world_space=False)
        Gizmos.draw_text((phase_space_x + phase_space_size // 2, phase_space_y - 15), "Phase Space (x vs vx)",
                         (255, 255, 255), duration=0.1, font_size=12, world_space=False,
                         background_color=(0, 0, 0, 128))
        if len(data) > 1:
            x_positions = [point[0] for point in data]
            x_velocities = [point[1] for point in data]
            min_x, max_x = min(x_positions), max(x_positions)
            min_vx, max_vx = min(x_velocities), max(x_velocities)
            x_range = max_x - min_x if max_x != min_x else 1
            vx_range = max_vx - min_vx if max_vx != min_vx else 1
            for i in range(1, len(data)):
                prev_point = data[i - 1]
                curr_point = data[i]
                prev_screen_x = phase_space_x + (prev_point[0] - min_x) / x_range * phase_space_size
                prev_screen_y = phase_space_y + (prev_point[1] - min_vx) / vx_range * phase_space_size
                curr_screen_x = phase_space_x + (curr_point[0] - min_x) / x_range * phase_space_size
                curr_screen_y = phase_space_y + (curr_point[1] - min_vx) / vx_range * phase_space_size
                alpha = i / len(data)
                color = (int(255 * alpha), int(255 * (1 - alpha)), 128)
                Gizmos.draw_line((prev_screen_x, prev_screen_y), (curr_screen_x, curr_screen_y),
                                 color, 2, duration=0.1, world_space=False)

    @profile("draw_coordinate_system", "physics_debug_manager")
    def draw_coordinate_system(self):
        if not self.settings.show_coordinate_system:
            return
        width, height = Config.app.screen_width, Config.app.screen_height
        Gizmos.draw_line((0, height // 2), (width, height // 2), (100, 100, 100), 1,
                         duration=0.1, world_space=False)
        Gizmos.draw_line((width // 2, 0), (width // 2, height), (100, 100, 100), 1,
                         duration=0.1, world_space=False)
        Gizmos.draw_text((width - 30, height // 2 - 20), "X", (150, 150, 150),
                         duration=0.1, world_space=False, font_size=16)
        Gizmos.draw_text((width // 2 + 10, 15), "Y", (150, 150, 150),
                         duration=0.1, world_space=False, font_size=16)
        for i in range(0, width, 100):
            if i != width // 2:
                Gizmos.draw_line((i, height // 2 - 5), (i, height // 2 + 5), (80, 80, 80), 1,
                                 duration=0.1, world_space=False)
        for i in range(0, height, 100):
            if i != height // 2:
                Gizmos.draw_line((width // 2 - 5, i), (width // 2 + 5, i), (80, 80, 80), 1,
                                 duration=0.1, world_space=False)

    @profile("draw_physics_info_panel", "physics_debug_manager")
    def draw_physics_info_panel(self):
        if not self.info_panel_visible:
            return
        space = self.physics_manager.space
        dynamic_bodies = [body for body in space.bodies if body.body_type == pymunk.Body.DYNAMIC]
        sleeping_bodies = [body for body in dynamic_bodies if body.is_sleeping]
        total_kinetic_energy = sum(0.5 * body.mass * (body.velocity.length ** 2) +
                                   0.5 * body.moment * (body.angular_velocity ** 2) for body in dynamic_bodies)
        gravity_magnitude = abs(self.physics_manager.space.gravity[1])
        total_potential_energy = sum(body.mass * gravity_magnitude *
                                     max(0, (Config.app.screen_height - body.position.y) * 0.001) for body in
                                     dynamic_bodies)
        total_elastic_energy = 0.0
        for constraint in space.constraints:
            if isinstance(constraint, pymunk.DampedSpring):
                a, b = constraint.a, constraint.b
                pa = a.position + constraint.anchor_a.rotated(a.angle) if hasattr(constraint,
                                                                                  'anchor_a') else a.position
                pb = b.position + constraint.anchor_b.rotated(b.angle) if hasattr(constraint,
                                                                                  'anchor_b') else b.position
                current_length = math.hypot(pb.x - pa.x, pb.y - pa.y)
                displacement = current_length - constraint.rest_length
                total_elastic_energy += 0.5 * constraint.stiffness * displacement ** 2
        simulation_time = pygame.time.get_ticks() / 1000.0 - self.simulation_start_time
        avg_dt = sum(self.dt_history) / len(self.dt_history) if self.dt_history else 0.016
        info_lines = [
            "=== PHYSICS SIMULATION ANALYSIS ===",
            f"Simulation time: {simulation_time:.2f} s",
            f"Average Δt: {avg_dt:.6f} s",
            f"Physics frequency: {1 / avg_dt:.1f} Hz",
            "",
            f"Dynamic bodies: {len(dynamic_bodies)}",
            f"Sleeping bodies: {len(sleeping_bodies)}",
            f"Total shapes: {len(space.shapes)}",
            f"Total constraints: {len(space.constraints)}",
            "",
            f"Gravity: {space.gravity[1]:.{self.settings.precision_digits}f} m/s²",
            f"Total kinetic energy: {total_kinetic_energy:.{self.settings.precision_digits}f} J",
            f"Total potential energy: {total_potential_energy:.{self.settings.precision_digits}f} J",
            f"Total elastic energy: {total_elastic_energy:.{self.settings.precision_digits}f} J",
            f"Total system energy: {total_kinetic_energy + total_potential_energy + total_elastic_energy:.{self.settings.precision_digits}f} J",
            "",
            f"System momentum: {math.hypot(*self.total_system_momentum):.{self.settings.precision_digits}f} kg⋅m/s",
            f"System ang. momentum: {self.total_system_angular_momentum:.{self.settings.precision_digits}f} kg⋅m²/s"
        ]
        x, y = self.settings.info_panel_position
        for i, line in enumerate(info_lines):
            if line == "":
                continue
            color = (255, 255, 255) if "===" in line else (200, 200, 200)
            font_size = 14 if "===" in line else 12
            Gizmos.draw_text((x, y + i * 18), line, color, duration=0.1, world_space=False,
                             font_size=font_size, background_color=(0, 0, 0, 128))

    def select_body_at_position(self, world_pos):
        query_result = self.physics_manager.space.point_query_nearest(world_pos, 0, pymunk.ShapeFilter())
        if query_result.shape and query_result.shape.body.body_type == pymunk.Body.DYNAMIC:
            self.selected_body = query_result.shape.body
            Debug.log(f"Selected body: Mass={self.selected_body.mass:.2f}kg, "
                      f"Moment={self.selected_body.moment:.2f}kg⋅m²", "PhysicsDebug")
        else:
            self.selected_body = None
            Debug.log("No body selected", "PhysicsDebug")

    def toggle_info_panel(self):
        self.info_panel_visible = not self.info_panel_visible
        Debug.log(f"Info panel: {self.info_panel_visible}", "PhysicsDebug")

    def toggle_trails(self):
        self.settings.show_trails = not self.settings.show_trails
        if not self.settings.show_trails:
            self.trails.clear()
        Debug.log(f"Trails: {self.settings.show_trails}", "PhysicsDebug")

    def toggle_constraints(self):
        self.settings.show_constraints = not self.settings.show_constraints
        Debug.log(f"Constraints: {self.settings.show_constraints}", "PhysicsDebug")

    def toggle_phase_space(self):
        self.settings.show_phase_space = not self.settings.show_phase_space
        Debug.log(f"Phase space: {self.settings.show_phase_space}", "PhysicsDebug")

    def clear_trails(self):
        self.trails.clear()
        self.velocity_history.clear()
        self.phase_space_data.clear()
        Debug.log("All debug history cleared", "PhysicsDebug")

    def set_vector_scale(self, scale: float):
        self.settings.vector_scale = max(0.01, min(10.0, scale))
        Debug.log(f"Vector scale: {self.settings.vector_scale}", "PhysicsDebug")

    def set_precision(self, digits: int):
        self.settings.precision_digits = max(1, min(6, digits))
        Debug.log(f"Precision: {self.settings.precision_digits} digits", "PhysicsDebug")

    def get_debug_shortcuts(self) -> Dict[str, str]:
        return {
            'V': 'Toggle velocity vectors',
            'A': 'Toggle acceleration vectors',
            'F': 'Toggle forces',
            'C': 'Toggle center of mass',
            'R': 'Toggle angular velocity',
            'E': 'Toggle energy meters',
            'B': 'Toggle colliders',
            'S': 'Toggle sleep state',
            'T': 'Toggle trails',
            'P': 'Toggle momentum vectors',
            'L': 'Toggle angular momentum',
            'M': 'Toggle Lagrangian mechanics',
            'H': 'Toggle Hamiltonian mechanics',
            'X': 'Toggle phase space',
            'I': 'Toggle info panel',
            'CTRL+T': 'Clear all debug history',
            'CTRL+A': 'Toggle all debug features',
            'CTRL+C': 'Toggle conservation laws',
            'MOUSE': 'Click to select object for detailed analysis',
            '1-6': 'Set precision (1-6 digits)'
        }

    def toggle_velocity_vectors(self):
        self.settings.show_velocity_vectors = not self.settings.show_velocity_vectors
        Debug.log(f"Velocity vectors: {self.settings.show_velocity_vectors}", "PhysicsDebug")

    def toggle_acceleration_vectors(self):
        self.settings.show_acceleration_vectors = not self.settings.show_acceleration_vectors
        Debug.log(f"Acceleration vectors: {self.settings.show_acceleration_vectors}", "PhysicsDebug")

    def toggle_forces(self):
        self.settings.show_forces = not self.settings.show_forces
        Debug.log(f"Forces: {self.settings.show_forces}", "PhysicsDebug")

    def toggle_center_of_mass(self):
        self.settings.show_center_of_mass = not self.settings.show_center_of_mass
        Debug.log(f"Center of mass: {self.settings.show_center_of_mass}", "PhysicsDebug")

    def toggle_angular_velocity(self):
        self.settings.show_angular_velocity = not self.settings.show_angular_velocity
        Debug.log(f"Angular velocity: {self.settings.show_angular_velocity}", "PhysicsDebug")

    def toggle_energy_meters(self):
        self.settings.show_energy_meters = not self.settings.show_energy_meters
        Debug.log(f"Energy meters: {self.settings.show_energy_meters}", "PhysicsDebug")

    def toggle_colliders(self):
        self.settings.show_colliders = not self.settings.show_colliders
        Debug.log(f"Colliders: {self.settings.show_colliders}", "PhysicsDebug")

    def toggle_sleep_state(self):
        self.settings.show_sleep_state = not self.settings.show_sleep_state
        Debug.log(f"Sleep state: {self.settings.show_sleep_state}", "PhysicsDebug")

    def toggle_all_debug(self):
        s = self.settings
        all_on = all([
            s.show_velocity_vectors,
            s.show_acceleration_vectors,
            s.show_forces,
            s.show_center_of_mass,
            s.show_angular_velocity,
            s.show_energy_meters,
            s.show_colliders,
            s.show_sleep_state
        ])
        state = not all_on
        for attr in ['show_velocity_vectors', 'show_acceleration_vectors', 'show_forces', 'show_center_of_mass',
                     'show_angular_velocity', 'show_energy_meters', 'show_colliders', 'show_sleep_state']:
            setattr(s, attr, state)
        Debug.log(f"All debug features: {state}", "PhysicsDebug")

    def set_selected_bodies(self, bodies):
        self.selected_bodies = list(set(bodies))