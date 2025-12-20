import time
import pymunk
import numpy as np
from typing import Callable, Tuple, List, Optional


class INDIController:
    def __init__(self, dim: int, dt: float = 0.01):
        self.dim = dim
        self.dt = dt
        self.n = dim
        self.m = dim
        self.A = np.zeros((self.n, self.n))
        self.B = np.eye(self.n)
        self.C = np.eye(self.m)
        self.D = np.zeros((self.m, self.n))
        self.x = np.zeros(self.n)
        self.y = np.zeros(self.m)
        self.u = np.zeros(self.n)
        self.r = np.zeros(self.m)
        self.e = np.zeros(self.m)
        self.de = np.zeros(self.m)
        self.d2e = np.zeros(self.m)
        self.y_prev = np.zeros(self.m)
        self.y_prev2 = np.zeros(self.m)
        self.L = np.eye(self.m)
        self.K = np.eye(self.m)
        self.alpha = np.ones(self.m) * 2.0
        self.beta = np.ones(self.m) * 1.0
        self.gamma = np.ones(self.m) * 1.0

    def save(self):
        return {
            "dt": self.dt,
            "A": self.A.tolist(),
            "B": self.B.tolist(),
            "C": self.C.tolist(),
            "D": self.D.tolist(),
            "x": self.x.tolist(),
            "y": self.y.tolist(),
            "u": self.u.tolist(),
            "r": self.r.tolist(),
            "e": self.e.tolist(),
            "de": self.de.tolist(),
            "d2e": self.d2e.tolist(),
            "y_prev": self.y_prev.tolist(),
            "y_prev2": self.y_prev2.tolist(),
            "L": self.L.tolist(),
            "K": self.K.tolist(),
            "alpha": self.alpha.tolist(),
            "beta": self.beta.tolist(),
            "gamma": self.gamma.tolist()
        }

    def load(self, data):
        self.dt = data.get("dt", 0.01)
        self.A = np.array(data.get("A", np.zeros((self.n, self.n))))
        self.B = np.array(data.get("B", np.eye(self.n)))
        self.C = np.array(data.get("C", np.eye(self.m)))
        self.D = np.array(data.get("D", np.zeros((self.m, self.n))))
        self.x = np.array(data.get("x", np.zeros(self.n)))
        self.y = np.array(data.get("y", np.zeros(self.m)))
        self.u = np.array(data.get("u", np.zeros(self.n)))
        self.r = np.array(data.get("r", np.zeros(self.m)))
        self.e = np.array(data.get("e", np.zeros(self.m)))
        self.de = np.array(data.get("de", np.zeros(self.m)))
        self.d2e = np.array(data.get("d2e", np.zeros(self.m)))
        self.y_prev = np.array(data.get("y_prev", np.zeros(self.m)))
        self.y_prev2 = np.array(data.get("y_prev2", np.zeros(self.m)))
        self.L = np.array(data.get("L", np.eye(self.m)))
        self.K = np.array(data.get("K", np.eye(self.m)))
        self.alpha = np.array(data.get("alpha", np.ones(self.m) * 2.0))
        self.beta = np.array(data.get("beta", np.ones(self.m) * 1.0))
        self.gamma = np.array(data.get("gamma", np.ones(self.m) * 1.0))

    def update_model(self, A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray = None):
        self.A = A
        self.B = B
        self.C = C
        self.D = D if D is not None else np.zeros((self.m, self.n))

    def set_reference(self, r: np.ndarray):
        self.r = r

    def compute(self, y: np.ndarray) -> np.ndarray:
        self.y = y.copy()
        self.e = self.r - self.y
        self.de = (self.y - self.y_prev) / self.dt if self.dt > 1e-8 else np.zeros_like(self.y)
        self.d2e = (self.y - 2 * self.y_prev + self.y_prev2) / (self.dt ** 2) if self.dt > 1e-8 else np.zeros_like(
            self.y)

        dy_ref = self.K @ self.e
        d2y_ref = self.L @ dy_ref
        du = np.linalg.pinv(self.C @ self.B) @ (d2y_ref - self.C @ self.A @ self.x - self.D @ self.u)
        self.u += du * self.dt
        self.x += (self.A @ self.x + self.B @ self.u) * self.dt
        self.y_prev2 = self.y_prev.copy()
        self.y_prev = self.y.copy()
        return self.u

    def _make_adjuster(self, attr: str, idx: int, delta: float) -> Callable[[], None]:
        arr = getattr(self, attr)

        def adjust():
            arr[idx] = max(0.0, arr[idx] + delta)
            setattr(self, attr, arr)

        return adjust

    def draw_ui(self, pos: Tuple[float, float], label: str):
        x, y = pos
        for i in range(self.m):
            for j, (param, sign, delta) in enumerate([
                ("alpha", "+", 0.1), ("alpha", "-", -0.1),
                ("beta", "+", 0.1), ("beta", "-", -0.1),
                ("gamma", "+", 0.1), ("gamma", "-", -0.1)
            ]):
                offset_x = x + (j % 2) * 60
                offset_y = y + (j // 2 + i * 3) * 70
                Gizmos.draw_button(
                    position=(offset_x, offset_y),
                    text=f"{sign}{i}",
                    on_click=self._make_adjuster(param, i, delta),
                    width=50,
                    height=50,
                    font_size=24,
                    font_world_space=True,
                    world_space=True
                )
        for i in range(self.m):
            Gizmos.draw_text(position=(x, y - 40 + i * 200),
                             text=f"{label}{i} α:{self.alpha[i]:.2f} β:{self.beta[i]:.2f} γ:{self.gamma[i]:.2f}",
                             color=(255, 255, 255), world_space=True)
            Gizmos.draw_text(position=(x, y + 220 + i * 200),
                             text=f"Err{i}: {self.e[i]:+.2f}",
                             color=(255, 255, 0) if abs(self.e[i]) < 10 else (255, 64, 64),
                             world_space=True)


target_pos = pymunk.Vec2d(400, 300)
indi_ctrl = INDIController(2, 0.01)
last_time = time.perf_counter()


def save_state():
    return {
        "indi_ctrl": indi_ctrl.save()
    }


def load_state(state):
    indi_ctrl.load(state.get("indi_ctrl", {}))


def start():
    global body
    body = owner
    self.preserve_gizmos = True


def update(dt):
    global last_time
    now = time.perf_counter()
    actual_dt = now - last_time or 1e-6
    last_time = now

    pos = np.array([body.position.x, body.position.y])
    indi_ctrl.dt = actual_dt
    ref = np.array([target_pos.x, target_pos.y])
    indi_ctrl.set_reference(ref)
    control_output = indi_ctrl.compute(pos)

    force = pymunk.Vec2d(control_output[0] * 10, control_output[1] * 10)
    body.apply_force_at_world_point(force, body.position)

    Gizmos.draw_point(target_pos, color=(0, 255, 0), duration=0.1)
    Gizmos.draw_point(pymunk.Vec2d(pos[0], pos[1]), color=(255, 0, 0), duration=0.1)

    indi_ctrl.draw_ui(pos=(100, 100), label="INDI")