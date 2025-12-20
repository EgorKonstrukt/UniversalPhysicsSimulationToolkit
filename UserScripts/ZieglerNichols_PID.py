import time
import pymunk
from typing import Callable, Tuple, List, Optional
from collections import deque

class AdjustablePIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.last_output = 0.0
        self.auto_tune = False
        self.tune_stage = 0
        self.oscillations: List[Tuple[float, float]] = []
        self.last_crossing_time: Optional[float] = None
        self.critical_gain = 0.0
        self.critical_period = 0.0
        self.tuning_start_time = 0.0
        self.backup_kp = kp
        self.backup_ki = ki
        self.backup_kd = kd
        self.max_tuning_duration = 12.0
        self.oscillation_threshold = 0.03
        self.peak_buffer = deque(maxlen=8)
        self.error_buffer = deque(maxlen=20)
        self.max_critical_gain = 10.0
        self.min_oscillation_count = 4
        self.amplitude_history = deque(maxlen=6)

    def save(self):
        return {
            "kp": self.kp, "ki": self.ki, "kd": self.kd,
            "integral": self.integral, "prev_error": self.prev_error, "last_output": self.last_output,
            "auto_tune": self.auto_tune, "critical_gain": self.critical_gain,
            "critical_period": self.critical_period, "backup_kp": self.backup_kp,
            "backup_ki": self.backup_ki, "backup_kd": self.backup_kd
        }

    def load(self, data):
        self.kp = data.get("kp", 1.0)
        self.ki = data.get("ki", 0.0)
        self.kd = data.get("kd", 0.0)
        self.integral = data.get("integral", 0.0)
        self.prev_error = data.get("prev_error", 0.0)
        self.last_output = data.get("last_output", 0.0)
        self.auto_tune = data.get("auto_tune", False)
        self.critical_gain = data.get("critical_gain", 0.0)
        self.critical_period = data.get("critical_period", 0.0)
        self.backup_kp = data.get("backup_kp", self.kp)
        self.backup_ki = data.get("backup_ki", self.ki)
        self.backup_kd = data.get("backup_kd", self.kd)

    def compute(self, setpoint: float, feedback: float, dt: float) -> float:
        error = setpoint - feedback
        if self.auto_tune:
            return self._tuning_compute(error, dt)
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

    def _tuning_compute(self, error: float, dt: float) -> float:
        now = time.perf_counter()
        self.error_buffer.append(error)
        smoothed_error = sum(self.error_buffer) / len(self.error_buffer)
        output = self.kp * smoothed_error
        self.prev_error = smoothed_error

        if self.tune_stage == 0:
            if self.kp < self.max_critical_gain:
                self.kp *= 1.08
            if len(self.error_buffer) >= 20 and self._has_sustained_oscillation():
                self.tune_stage = 1
                self.tuning_start_time = now
                self.oscillations.clear()
                self.amplitude_history.clear()
                self.last_crossing_time = None
        elif self.tune_stage == 1:
            if now - self.tuning_start_time > self.max_tuning_duration:
                self._finalize_tuning(success=False)
            else:
                self._track_peaks_and_zero_crossings(smoothed_error)
        return output

    def _has_sustained_oscillation(self) -> bool:
        if len(self.error_buffer) < 50: return False
        recent = list(self.error_buffer)[-30:]
        mean = sum(recent) / len(recent)
        centered = [e - mean for e in recent]
        var = sum(e * e for e in centered) / len(centered)
        return var > self.oscillation_threshold ** 2

    def _track_peaks_and_zero_crossings(self, error: float):
        self.peak_buffer.append(error)
        if len(self.peak_buffer) < 4: return
        prev3, prev2, prev1, curr = list(self.peak_buffer)[-4:]
        if prev2 > prev3 and prev2 > prev1 and prev2 > curr and prev2 > self.oscillation_threshold:
            self.amplitude_history.append(prev2)
        if len(self.amplitude_history) >= 3:
            amps = list(self.amplitude_history)
            if not (amps[-1] > amps[0] * 0.7):
                return
        if self.prev_error * error < 0:
            now = time.perf_counter()
            if self.last_crossing_time is not None:
                half_period = now - self.last_crossing_time
                period = half_period * 2
                self.oscillations.append((now, period))
                if len(self.oscillations) >= self.min_oscillation_count:
                    recent_periods = [p for _, p in self.oscillations[-self.min_oscillation_count:]]
                    if max(recent_periods) / min(recent_periods) < 1.5:
                        self.critical_period = sum(recent_periods) / len(recent_periods)
                        self._finalize_tuning(success=True)
            self.last_crossing_time = now

    def _finalize_tuning(self, success: bool):
        if success and self.critical_period > 0.01 and 0.1 < self.kp <= self.max_critical_gain:
            Ku = self.kp
            Tu = self.critical_period
            self.kp = 0.6 * Ku
            self.ki = 1.2 * Ku / Tu
            self.kd = 0.075 * Ku * Tu
        else:
            self.kp, self.ki, self.kd = self.backup_kp, self.backup_ki, self.backup_kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.auto_tune = False
        self.tune_stage = 0

    def start_auto_tune(self):
        self.backup_kp, self.backup_ki, self.backup_kd = self.kp, self.ki, self.kd
        self.auto_tune = True
        self.tune_stage = 0
        self.kp = max(0.05, self.backup_kp * 0.2)
        self.ki = 0.0
        self.kd = 0.0
        self.error_buffer.clear()
        self.peak_buffer.clear()
        self.oscillations.clear()
        self.amplitude_history.clear()

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
                position=(offset_x, offset_y), text=f"{sign}",
                on_click=self._make_adjuster(param, delta), width=50, height=50,
                font_size=32, font_world_space=True, world_space=True
            )
        auto_text = "Stop Auto-Tune" if self.auto_tune else "Start Auto-Tune"
        Gizmos.draw_button(
            position=(x, y + 210), text=auto_text,
            on_click=self._toggle_auto_tune, width=110, height=50,
            font_size=18, font_world_space=True, world_space=True
        )
        Gizmos.draw_text(position=(x, y - 40),
                         text=f"{label} P: {self.kp:.3f} I: {self.ki:.3f} D: {self.kd:.3f}",
                         color=(255, 255, 255), world_space=True)

    def _toggle_auto_tune(self):
        if not self.auto_tune:
            self.start_auto_tune()
        else:
            self.auto_tune = False
            self.kp, self.ki, self.kd = self.backup_kp, self.backup_ki, self.backup_kd
            self.integral = 0.0
            self.prev_error = 0.0


target_pos = pymunk.Vec2d(400, 300)
target_angle = 0.0
pid_x = AdjustablePIDController(1.0, 0.1, 0.01)
pid_y = AdjustablePIDController(1.0, 0.1, 0.01)
pid_angle = AdjustablePIDController(5.0, 0.0, 0.5)
last_time = time.perf_counter()


def save_state():
    return {
        "pid_x": pid_x.save(),
        "pid_y": pid_y.save(),
        "pid_angle": pid_angle.save()
    }

def load_state(state):
    pid_x.load(state.get("pid_x", {}))
    pid_y.load(state.get("pid_y", {}))
    pid_angle.load(state.get("pid_angle", {}))

def start():
    global body
    body = owner

def update(dt):
    global last_time
    now = time.perf_counter()
    actual_dt = now - last_time or 1e-6
    last_time = now

    pos = body.position
    fx = pid_x.compute(target_pos.x, pos.x, actual_dt)
    fy = pid_y.compute(target_pos.y, pos.y, actual_dt)
    torque = pid_angle.compute(target_angle, body.angle, actual_dt)
    body.apply_force_at_world_point((fx * 10, fy * 10), pos)
    body.torque += torque * 10

    Gizmos.draw_point(target_pos, color=(0, 255, 0), duration=0.1)
    Gizmos.draw_point(pos, color=(255, 0, 0), duration=0.1)
    Gizmos.draw_line(pos, pos + pymunk.Vec2d(30, 0).rotated(body.angle), color=(255, 255, 0), duration=0.1)

    pid_x.draw_ui(pos=(100, 100), label="X")
    pid_y.draw_ui(pos=(100, 320), label="Y")
    pid_angle.draw_ui(pos=(100, 540), label="Angle")