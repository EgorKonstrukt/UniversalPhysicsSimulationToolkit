import pygame
from collections import deque
import math
import pymunk
import threading
import queue
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from UPST.config import config
from UPST.gizmos.gizmos_manager import Gizmos
from UPST.debug.debug_manager import Debug
from UPST.modules.profiler import profile




class PhysicsDebugManager:
    def __init__(self, physics_manager, camera, plotter):
        self.physics_manager = physics_manager
        self.camera = camera
        self.plotter = plotter
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
        self.selected_body: Optional[pymunk.Body] = None
        self.simulation_start_time = pygame.time.get_ticks() / 1000.0
        self.total_system_momentum = (0.0, 0.0)
        self.total_system_angular_momentum = 0.0
        self.total_system_energy = 0.0
        self.system_center_of_mass = (0.0, 0.0)
        self.plot_parameters: Dict[pymunk.Body, List[str]] = {}
        self.history_buffer = {}

        self._task_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()


    def _get_smoothed(self, body, key, value):
        if body not in self.history_buffer:
            self.history_buffer[body] = {}
        if key not in self.history_buffer[body]:
            self.history_buffer[body][key] = deque([value] * config.physics_debug.smoothing_window,
                                                   maxlen=config.physics_debug.smoothing_window)
        self.history_buffer[body][key].append(value)
        return sum(self.history_buffer[body][key]) / len(self.history_buffer[body][key])

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

        if config.physics_debug.show_constraints:
            for constraint in self.physics_manager.space.constraints:
                self._draw_constraint(constraint)

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
                               max(0, (config.app.screen_height - b.position.y) * 0.001) for b in bodies)

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
        potential_energy = body_mass * gravity_magnitude * max(0, (config.app.screen_height - body_position_y) * 0.001)
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


        if config.physics_debug.show_trails:
            self._update_trail(body, pos)
        if config.physics_debug.show_center_of_mass:
            self._draw_center_of_mass(body, pos)
        if config.physics_debug.show_colliders:
            self._draw_colliders(body)
        if config.physics_debug.show_sleep_state and body.is_sleeping:
            self._draw_sleep_state(body, pos)
        if config.physics_debug.show_velocity_vectors:
            self._draw_velocity_vector(body, pos)
        if config.physics_debug.show_acceleration_vectors:
            self._draw_acceleration_vector(body, pos, dt)
        if config.physics_debug.show_forces:
            self._draw_forces(body, pos)
        if config.physics_debug.show_angular_velocity:
            self._draw_angular_velocity(body, pos, t)
        if config.physics_debug.show_angular_momentum:
            self._draw_angular_momentum(body, pos)
        if config.physics_debug.show_energy_meters:
            self._draw_energy_meters(body, pos)
        if config.physics_debug.show_rotation_axes:
            self._draw_rotation_axes(body, pos)

    def _update_trail(self, body, pos):
        if body not in self.trails:
            self.trails[body] = []
        trail = self.trails[body]
        trail.append((pos.x, pos.y))
        if len(trail) > config.physics_debug.trail_length:
            trail.pop(0)
        for i in range(1, len(trail)):
            alpha = i / len(trail)
            color = (*config.physics_debug.velocity_color, int(255 * alpha))
            thickness = max(1, int(3 * alpha))
            Gizmos.draw_line(trail[i - 1], trail[i], color, thickness, duration=0.1)

    def _update_velocity_history(self, body):
        if body not in self.velocity_history:
            self.velocity_history[body] = []
        history = self.velocity_history[body]
        history.append((body.velocity.x, body.velocity.y))
        if len(history) > 200:
            history.pop(0)


    @profile("_draw_center_of_mass", "physics_debug_manager")
    def _draw_center_of_mass(self, body, pos):
        Gizmos.draw_circle((pos.x, pos.y), 4, config.physics_debug.com_color, thickness=2, duration=0.1)
        Gizmos.draw_cross((pos.x, pos.y), 8, config.physics_debug.com_color, 2, duration=0.1)

    @profile("_draw_colliders", "physics_debug_manager")
    def _draw_colliders(self, body):
        for shape in body.shapes:
            if isinstance(shape, pymunk.Circle):
                center = body.local_to_world(shape.offset)
                Gizmos.draw_circle((center.x, center.y), shape.radius,
                                   config.physics_debug.collider_color, thickness=2, duration=0.1)
                area = math.pi * shape.radius ** 2
                if config.physics_debug.show_vector_labels:
                    Gizmos.draw_text((center.x, center.y - shape.radius - 15),
                                     f"A={area:.2f}m²", config.physics_debug.collider_color,
                                     duration=0.1, font_size=14)
            elif isinstance(shape, pymunk.Poly):
                vertices = [body.local_to_world(v) for v in shape.get_vertices()]
                for i in range(len(vertices)):
                    next_i = (i + 1) % len(vertices)
                    Gizmos.draw_line(vertices[i], vertices[next_i],
                                     config.physics_debug.collider_color, 2, duration=0.1)
                area = abs(sum((vertices[i].x * vertices[(i + 1) % len(vertices)].y -
                                vertices[(i + 1) % len(vertices)].x * vertices[i].y)
                               for i in range(len(vertices)))) / 2
                if config.physics_debug.show_vector_labels:
                    centroid_x = sum(v.x for v in vertices) / len(vertices)
                    centroid_y = sum(v.y for v in vertices) / len(vertices)
                    Gizmos.draw_text((centroid_x, centroid_y - 20),
                                     f"A={area:.2f}m²", config.physics_debug.collider_color,
                                     duration=0.1, font_size=14 * int(config.physics_debug.text_scale))

    @profile("_draw_sleep_state", "physics_debug_manager")
    def _draw_sleep_state(self, body, pos):
        fade_factor = math.sin(pygame.time.get_ticks() * 0.003) * 0.5 + 0.5
        radius = 15 + fade_factor * 5
        Gizmos.draw_circle((pos.x, pos.y), radius, config.physics_debug.sleep_color,
                           thickness=2, duration=0.1)
        Gizmos.draw_text((pos.x - 10, pos.y - 20), "SLEEP", config.physics_debug.sleep_color,
                         duration=0.1, font_size=14 * int(config.physics_debug.text_scale), background_color=(0, 0, 0, 128))

    @profile("_draw_velocity_vector", "physics_debug_manager")
    def _draw_velocity_vector(self, body, pos):
        velocity = body.velocity
        if velocity.length <= 0.01: return
        speed = self._get_smoothed(body, 'speed',
                                   velocity.length) if config.physics_debug.smoothing else velocity.length
        vx = self._get_smoothed(body, 'vx', velocity.x) if config.physics_debug.smoothing else velocity.x
        vy = self._get_smoothed(body, 'vy', velocity.y) if config.physics_debug.smoothing else velocity.y
        scale = config.physics_debug.vector_scale * 20
        origin = (pos.x, pos.y)
        vx_end = (pos.x + vx * scale, pos.y)
        vy_end = (pos.x, pos.y + vy * scale)
        main_end = (pos.x + vx * scale, pos.y + vy * scale)
        thickness = max(1, min(4, int(speed * 0.1)))
        col = config.physics_debug.velocity_color
        arrows = [(origin, vx_end), (origin, vy_end), (origin, main_end)]
        for start, end in arrows:
            Gizmos.draw_arrow(start, end, col, thickness, duration=0.1)
        lines = [(vx_end, main_end), (vy_end, main_end)]
        for start, end in lines:
            Gizmos.draw_line(start, end, (200, 200, 200, 180), max(1, thickness // 2), duration=0.1)
        if config.physics_debug.show_vector_labels:
            pm = config.physics_debug.precision_digits
            angle_deg = math.degrees(math.atan2(vy, vx))
            label_main = (pos.x + vx * scale * 0.6, pos.y + vy * scale * 0.6 - 15)
            Gizmos.draw_text(label_main, f"v={speed:.{pm}f}m/s ∠{angle_deg:+.{pm}f}°", col,
                             duration=0.1, font_size=16 * int(config.physics_debug.text_scale),
                             background_color=(0, 0, 0, 128))
            label_vx = (pos.x + vx * scale * 0.5, pos.y - 25)
            label_vy = (pos.x - 35, pos.y + vy * scale * 0.5)
            # Gizmos.draw_text(label_vx, f"vx={vx:+.{pm}f}", col, duration=0.1, font_size=12,
            #                  background_color=(0, 0, 0, 128))
            # Gizmos.draw_text(label_vy, f"vy={vy:+.{pm}f}", col, duration=0.1, font_size=12,
            #                  background_color=(0, 0, 0, 128))

    @profile("_draw_acceleration_vector", "physics_debug_manager")
    def _draw_acceleration_vector(self, body, pos, dt):
        current_velocity = (body.velocity.x, body.velocity.y)
        if body not in self.previous_velocities or dt <= 0:
            self.previous_velocities[body] = current_velocity
            return
        prev_vx, prev_vy = self.previous_velocities[body]
        acc_x = (current_velocity[0] - prev_vx) / dt
        acc_y = (current_velocity[1] - prev_vy) / dt
        acc_mag = math.hypot(acc_x, acc_y)
        if acc_mag <= 1.0:
            self.previous_velocities[body] = current_velocity
            return
        acc_x = self._get_smoothed(body, 'acc_x', acc_x) if config.physics_debug.smoothing else acc_x
        acc_y = self._get_smoothed(body, 'acc_y', acc_y) if config.physics_debug.smoothing else acc_y
        acc_mag = self._get_smoothed(body, 'acc_mag', acc_mag) if config.physics_debug.smoothing else acc_mag
        scale = config.physics_debug.vector_scale * 5
        end = (pos.x + acc_x * scale, pos.y + acc_y * scale)
        thickness = max(2, min(6, int(acc_mag * 0.05)))
        col = config.physics_debug.acceleration_color
        Gizmos.draw_arrow((pos.x, pos.y), end, col, thickness, duration=0.1)
        if config.physics_debug.show_vector_labels:
            pm = config.physics_debug.precision_digits
            angle_deg = math.degrees(math.atan2(acc_y, acc_x))
            label_pos = (pos.x + acc_x * scale * 0.6, pos.y + acc_y * scale * 0.6 + 15)
            Gizmos.draw_text(label_pos, f"a={acc_mag:.{pm}f}m/s² ∠{angle_deg:+.{pm}f}°", col, duration=0.1,
                             font_size=16 * int(config.physics_debug.text_scale), background_color=(0, 0, 0, 128))
        self.previous_velocities[body] = current_velocity

    @profile("_draw_forces", "physics_debug_manager")
    def _draw_forces(self, body, pos):
        gravity = self.physics_manager.space.gravity
        if abs(gravity[0]) > 0.1 or abs(gravity[1]) > 0.1:
            gravitational_force = (body.mass * gravity[0], body.mass * gravity[1])
            force_magnitude = math.hypot(*gravitational_force)
            if force_magnitude > 0.1:
                scale = config.physics_debug.vector_scale * 0.1
                end_x = pos.x + gravitational_force[0] * scale
                end_y = pos.y + gravitational_force[1] * scale
                Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                                  config.physics_debug.force_color, 3, duration=0.1)
                if config.physics_debug.show_vector_labels:
                    label_x = pos.x + gravitational_force[0] * scale * 0.6 + 20
                    label_y = pos.y + gravitational_force[1] * scale * 0.6
                    Gizmos.draw_text((label_x, label_y),
                                     f"F_g={force_magnitude:.{config.physics_debug.precision_digits}f}N",
                                     config.physics_debug.force_color, duration=0.1, font_size=16 * int(config.physics_debug.text_scale),
                                     background_color=(0, 0, 0, 128))
        net_force = body.force
        if abs(net_force.x) > 0.1 or abs(net_force.y) > 0.1:
            net_force_magnitude = math.hypot(net_force.x, net_force.y)
            scale = config.physics_debug.vector_scale * 0.2
            end_x = pos.x + net_force.x * scale
            end_y = pos.y + net_force.y * scale
            Gizmos.draw_arrow((pos.x, pos.y), (end_x, end_y),
                              (255, 255, 255), 4, duration=0.1)
            if config.physics_debug.show_vector_labels:
                label_x = pos.x + net_force.x * scale * 0.6 + 30
                label_y = pos.y + net_force.y * scale * 0.6
                Gizmos.draw_text((label_x, label_y),
                                 f"F_net={net_force_magnitude:.{config.physics_debug.precision_digits}f}N",
                                 (255, 255, 255), duration=0.1, font_size=16 * int(config.physics_debug.text_scale),
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_momentum_vector", "physics_debug_manager")
    def _draw_momentum_vector(self, body, pos):
        px = body.mass * body.velocity.x
        py = body.mass * body.velocity.y
        p_mag = math.hypot(px, py)
        if p_mag <= 0.01: return
        px = self._get_smoothed(body, 'px', px) if config.physics_debug.smoothing else px
        py = self._get_smoothed(body, 'py', py) if config.physics_debug.smoothing else py
        p_mag = self._get_smoothed(body, 'p_mag', p_mag) if config.physics_debug.smoothing else p_mag
        scale = config.physics_debug.vector_scale * 5
        end = (pos.x + px * scale, pos.y + py * scale)
        thickness = max(2, min(6, int(p_mag * 0.01)))
        col = config.physics_debug.momentum_color
        Gizmos.draw_arrow((pos.x, pos.y), end, col, thickness, duration=0.1)
        if config.physics_debug.show_vector_labels:
            pm = config.physics_debug.precision_digits
            angle_deg = math.degrees(math.atan2(py, px))
            label_pos = (pos.x + px * scale * 0.6, pos.y + py * scale * 0.6 + 25)
            Gizmos.draw_text(label_pos, f"p={p_mag:.{pm}f}kg⋅m/s ∠{angle_deg:+.{pm}f}°", col, duration=0.1,
                             font_size=16 * int(config.physics_debug.text_scale), background_color=(0, 0, 0, 128))

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
                # Gizmos.draw_line((x1, y1), (x2, y2), config.physics_debug.angular_color,
                #                  thickness, duration=0.1)
            final_angle = arc_angle + offset
            arrow_start = (pos.x + radius * math.cos(final_angle),
                           pos.y + radius * math.sin(final_angle))
            direction_angle = final_angle + math.pi / 2 * (1 if angular_velocity > 0 else -1)
            arrow_end = (arrow_start[0] + 10 * math.cos(direction_angle),
                         arrow_start[1] + 10 * math.sin(direction_angle))
            # Gizmos.draw_line(arrow_start, arrow_end, config.physics_debug.angular_color,
            #                  5, duration=0.1)
            if config.physics_debug.show_vector_labels:
                Gizmos.draw_text((pos.x + 40, pos.y - 10),
                                 f"ω={angular_velocity:.{config.physics_debug.precision_digits}f}rad/s",
                                 config.physics_debug.angular_color, duration=0.1, font_size=16 * int(config.physics_debug.text_scale),
                                 background_color=(0, 0, 0, 128))

    @profile("_draw_angular_momentum", "physics_debug_manager")
    def _draw_angular_momentum(self, body, pos):
        angular_momentum = body.moment * body.angular_velocity
        if abs(angular_momentum) > 0.01:
            radius = 25
            Gizmos.draw_circle((pos.x, pos.y), radius, config.physics_debug.angular_momentum_color,
                               thickness=3, duration=0.1)
            if config.physics_debug.show_vector_labels:
                Gizmos.draw_text((pos.x + 30, pos.y + 15),
                                 f"L={angular_momentum:.{config.physics_debug.precision_digits}f}kg⋅m²/s",
                                 config.physics_debug.angular_momentum_color, duration=0.1,
                                 font_size=14 * int(config.physics_debug.text_scale),
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
    @profile("_draw_energy_meters", "physics_debug_manager")
    def _draw_energy_meters(self, body, pos):
        kinetic_energy = 0.5 * body.mass * (body.velocity.length ** 2)
        rotational_energy = 0.5 * body.moment * (body.angular_velocity ** 2)
        gravity_magnitude = math.hypot(*self.physics_manager.space.gravity)
        height = max(0, (config.app.screen_height - pos.y) * 0.001)
        potential_energy = body.mass * gravity_magnitude * height
        total_energy = kinetic_energy + rotational_energy + potential_energy
        max_energy = max(total_energy, 1)
        bar_width = 8
        bar_spacing = 12
        bar_height = config.physics_debug.energy_bar_height
        ke_height = kinetic_energy / max_energy * bar_height
        re_height = rotational_energy / max_energy * bar_height
        pe_height = potential_energy / max_energy * bar_height
        bar_x = pos.x - 45
        Gizmos.draw_line((bar_x, pos.y), (bar_x, pos.y - ke_height),
                         config.physics_debug.kinetic_color, bar_width, duration=0.1)
        Gizmos.draw_line((bar_x + bar_spacing, pos.y), (bar_x + bar_spacing, pos.y - re_height),
                         config.physics_debug.angular_color, bar_width, duration=0.1)
        Gizmos.draw_line((bar_x + 2 * bar_spacing, pos.y), (bar_x + 2 * bar_spacing, pos.y - pe_height),
                         config.physics_debug.potential_color, bar_width, duration=0.1)
        if config.physics_debug.show_energy_values:
            Gizmos.draw_text((bar_x - 20, pos.y - bar_height - 35),
                             f"KE: {kinetic_energy:.{config.physics_debug.precision_digits}f}J",
                             config.physics_debug.kinetic_color, duration=0.1,
                             font_size=12 * int(config.physics_debug.text_scale),
                             background_color=(0, 0, 0, 128), collision=True)
            Gizmos.draw_text((bar_x - 20, pos.y - bar_height - 25),
                             f"RE: {rotational_energy:.{config.physics_debug.precision_digits}f}J",
                             config.physics_debug.angular_color, duration=0.1,
                             font_size=12 * int(config.physics_debug.text_scale),
                             background_color=(0, 0, 0, 128), collision=True)
            Gizmos.draw_text((bar_x - 20, pos.y - bar_height - 15),
                             f"PE: {potential_energy:.{config.physics_debug.precision_digits}f}J",
                             config.physics_debug.potential_color, duration=0.1,
                             font_size=12 * int(config.physics_debug.text_scale),
                             background_color=(0, 0, 0, 128), collision=True)


    @profile("_draw_constraint", "physics_debug_manager")
    def _draw_constraint(self, constraint):
        a, b = constraint.a, constraint.b
        pa = a.position + constraint.anchor_a.rotated(a.angle) if hasattr(constraint, 'anchor_a') else a.position
        pb = b.position + constraint.anchor_b.rotated(b.angle) if hasattr(constraint, 'anchor_b') else b.position
        if config.physics_debug.show_constraint_info:
            midpoint = ((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)
            constraint_type = constraint.__class__.__name__
            info_lines = [constraint_type]
            if hasattr(constraint, 'rest_length'):
                current_length = math.hypot(pb.x - pa.x, pb.y - pa.y)
                info_lines.append(f"L₀: {constraint.rest_length:.{config.physics_debug.precision_digits}f}m")
                info_lines.append(f"L: {current_length:.{config.physics_debug.precision_digits}f}m")
                info_lines.append(f"ΔL: {current_length - constraint.rest_length:.{config.physics_debug.precision_digits}f}m")
            if hasattr(constraint, 'stiffness'):
                info_lines.append(f"k: {constraint.stiffness:.{config.physics_debug.precision_digits}f}N/m")
            if hasattr(constraint, 'damping'):
                info_lines.append(f"c: {constraint.damping:.{config.physics_debug.precision_digits}f}N⋅s/m")
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
                    scale = config.physics_debug.vector_scale * 0.3
                    force_end_x = midpoint[0] + total_force_magnitude * unit_x * scale
                    force_end_y = midpoint[1] + total_force_magnitude * unit_y * scale
                    Gizmos.draw_arrow(midpoint, (force_end_x, force_end_y), (0, 255, 255), 3, duration=0.1)
                    if config.physics_debug.show_vector_labels:
                        Gizmos.draw_text((force_end_x + 10, force_end_y - 10),
                                         f"F_spring={total_force_magnitude:.{config.physics_debug.precision_digits}f}N",
                                         (0, 255, 255), duration=0.1,
                                         font_size=12 * int(config.physics_debug.text_scale),
                                         background_color=(0, 0, 0, 128))
                    spring_potential_energy = 0.5 * constraint.stiffness * (length - constraint.rest_length) ** 2
                    info_lines.append(f"PE_spring: {spring_potential_energy:.{config.physics_debug.precision_digits}f}J")
            for i, line in enumerate(info_lines):
                Gizmos.draw_text((midpoint[0], midpoint[1] + i * 15), line,
                                 config.physics_debug.constraint_color, duration=0.1,
                                 font_size=12 * int(config.physics_debug.text_scale),
                                 background_color=(0, 0, 0, 128))

    def clear_trails(self):
        self.trails.clear()
        self.velocity_history.clear()
        self.phase_space_data.clear()
        Debug.log("All debug history cleared", "PhysicsDebug")

    def set_vector_scale(self, scale: float):
        config.physics_debug.vector_scale = max(0.01, min(10.0, scale))
        Debug.log(f"Vector scale: {config.physics_debug.vector_scale}", "PhysicsDebug")

    def set_precision(self, digits: int):
        config.physics_debug.precision_digits = max(1, min(6, digits))
        Debug.log(f"Precision: {config.physics_debug.precision_digits} digits", "PhysicsDebug")


    def set_selected_bodies(self, bodies):
        self.selected_bodies = list(set(bodies))