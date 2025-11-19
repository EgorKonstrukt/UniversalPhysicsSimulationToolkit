import time
import pymunk
from typing import Callable, Tuple


class AdjustablePIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.last_output = 0.0
        self.last_error = 0.0

    def save(self):
        return {
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "integral": self.integral,
            "prev_error": self.prev_error,
            "last_output": self.last_output,
            "last_error": self.last_error
        }

    def load(self, data):
        self.kp = data.get("kp", 1.0)
        self.ki = data.get("ki", 0.0)
        self.kd = data.get("kd", 0.0)
        self.integral = data.get("integral", 0.0)
        self.prev_error = data.get("prev_error", 0.0)
        self.last_output = data.get("last_output", 0.0)
        self.last_error = data.get("last_error", 0.0)

    def compute(self, setpoint: float, feedback: float, dt: float) -> float:
        error = setpoint - feedback
        self.last_error = error
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

    def _make_adjuster(self, attr: str, delta: float) -> Callable[[], None]:
        return lambda: setattr(self, attr, getattr(self, attr) + delta)

    def draw_ui(self, pos: Tuple[float, float], label: str):
        x, y = pos
        for i, (param, sign, delta) in enumerate([
            ("kp", "+", 0.1), ("kp", "-", -0.1),
            ("ki", "+", 0.01), ("ki", "-", -0.01),
            ("kd", "+", 0.1), ("kd", "-", -0.1)
        ]):
            offset_x = x + (i % 2) * 60
            offset_y = y + (i // 2) * 70
            Gizmos.draw_button(
                position=(offset_x, offset_y),
                text=f"{sign}",
                on_click=self._make_adjuster(param, delta),
                width=50,
                height=50,
                font_size=32,
                font_world_space=True,
                world_space=True
            )
        Gizmos.draw_text(position=(x, y - 40),
                         text=f"{label} P:{self.kp:.2f} I:{self.ki:.2f} D:{self.kd:.2f}",
                         color=(255, 255, 255), world_space=True)
        Gizmos.draw_text(position=(x, y + 220),
                         text=f"Err: {self.last_error:+.2f}",
                         color=(255, 255, 0) if abs(self.last_error) < 10 else (255, 64, 64),
                         world_space=True)


target_pos = pymunk.Vec2d(400, 300)
pid_x = AdjustablePIDController(1.0, 0.1, 0.01)
pid_y = AdjustablePIDController(1.0, 0.1, 0.01)
last_time = time.perf_counter()
plotter = None


def save_state():
    return {
        "pid_x": pid_x.save(),
        "pid_y": pid_y.save()
    }


def load_state(state):
    pid_x.load(state.get("pid_x", {}))
    pid_y.load(state.get("pid_y", {}))


def start():
    global body, plotter
    body = owner
    plotter = PlotterWindow(position=(700, 10), size=(600, 400), window_title="PID Error Plotter")
    plotter.show()


def update(dt):
    global last_time
    now = time.perf_counter()
    actual_dt = now - last_time or 1e-6
    last_time = now

    pos = body.position
    fx = pid_x.compute(target_pos.x, pos.x, actual_dt)
    fy = pid_y.compute(target_pos.y, pos.y, actual_dt)
    body.apply_force_at_world_point((fx * 10, fy * 10), pos)

    Gizmos.draw_point(target_pos, color=(0, 255, 0), duration=0.1)
    Gizmos.draw_point(pos, color=(255, 0, 0), duration=0.1)

    pid_x.draw_ui(pos=(100, 100), label="X")
    pid_y.draw_ui(pos=(100, 320), label="Y")

    if plotter:
        plotter.add_data("X Error", abs(pid_x.last_error), "Error")
        plotter.add_data("Y Error", abs(pid_y.last_error), "Error")
        plotter.add_data("X Output", abs(fx), "Output")
        plotter.add_data("Y Output", abs(fy), "Output")


def stop():
    if plotter:
        plotter.hide()