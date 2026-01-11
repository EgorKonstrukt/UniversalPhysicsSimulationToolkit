import math
import random
from typing import List, Tuple

class DoublePendulums:
    def __init__(self):
        self.g = 9.8
        self.L1 = 1.0
        self.L2 = 1.0
        self.m1 = 1.0
        self.m2 = 1.0
        self.dt = 0.016
        self.trail_len = 100
        self.pendulums: List[List[float]] = []
        self.trajectories: List[List[Tuple[float, float]]] = []
        self.colors = ['red', 'blue', 'green', 'yellow', 'magenta', 'cyan', 'orange', 'purple']

    def save(self):
        return {
            "g": self.g,
            "L1": self.L1,
            "L2": self.L2,
            "m1": self.m1,
            "m2": self.m2,
            "dt": self.dt,
            "trail_len": self.trail_len,
            "pendulums": self.pendulums,
            "trajectories": self.trajectories
        }

    def load(self, data):
        self.g = data.get("g", 9.8)
        self.L1 = data.get("L1", 1.0)
        self.L2 = data.get("L2", 1.0)
        self.m1 = data.get("m1", 1.0)
        self.m2 = data.get("m2", 1.0)
        self.dt = data.get("dt", 0.016)
        self.trail_len = data.get("trail_len", 100)
        self.pendulums = data.get("pendulums", [])
        self.trajectories = data.get("trajectories", [])

    def add_pendulum(self):
        if len(self.pendulums) < 8:
            θ = math.pi / 2 + random.uniform(-0.01, 0.01)
            self.pendulums.append([θ, θ, 0.0, 0.0])
            self.trajectories.append([])

    def clear_all(self):
        self.pendulums.clear()
        self.trajectories.clear()

    def add_chaos_set(self):
        self.clear_all()
        base = math.pi / 2
        for i in range(5):
            δ = i * 0.001
            self.pendulums.append([base + δ, base + δ, 0.0, 0.0])
            self.trajectories.append([])

    def reset_all(self):
        base = math.pi / 2
        for i in range(len(self.pendulums)):
            δ = random.uniform(-0.01, 0.01)
            self.pendulums[i] = [base + δ, base + δ, 0.0, 0.0]
            self.trajectories[i].clear()

    def adjust(self, attr: str, delta: float, min_val: float = 0.0, step: float = 0.1):
        setattr(self, attr, max(min_val, getattr(self, attr) + delta))

    def draw_ui(self, panel_pos: Tuple[float, float]):
        px, py = panel_pos
        w, h, s = 120, 30, 8
        y_off = 0

        def btn(x, y, txt, cb):
            Gizmos.draw_button((x, y), txt, cb, w, h, font_size=14, font_world_space=True, world_space=True)

        btn(px, py + y_off, "Add Pendulum", self.add_pendulum); y_off += h + s
        btn(px, py + y_off, "Clear All", self.clear_all); y_off += h + s
        btn(px, py + y_off, "Chaos Set", self.add_chaos_set); y_off += h + s
        btn(px, py + y_off, "Reset All", self.reset_all); y_off += h + s

        settings = [("g", 0.1), ("L1", 0.05), ("L2", 0.05), ("m1", 0.1), ("m2", 0.1), ("dt", 0.002), ("trail_len", 10)]
        for name, step in settings:
            val = getattr(self, name)
            btn(px, py + y_off, f"{name}: {val:.3f}", lambda n=name, s=step: None)
            btn(px + w + s, py + y_off, "-", lambda n=name, s=step: self.adjust(n, -s, 0.001 if n != "trail_len" else 10, s))
            btn(px + w * 2 + s * 2, py + y_off, "+", lambda n=name, s=step: self.adjust(n, s, 0.001 if n != "trail_len" else 10, s))
            y_off += h + s

        info = f"Pendulums: {len(self.pendulums)}\nJoints: {len(self.pendulums) * 2}"
        Gizmos.draw_text((px, py + y_off), info, 'white', font_size=18, font_world_space=True, world_space=True)

    def update_and_draw(self, origin: Tuple[float, float] = (0, 0), scale: float = 250):
        for i, (state, traj) in enumerate(zip(self.pendulums, self.trajectories)):
            θ1, θ2, ω1, ω2 = state
            Δ = θ2 - θ1
            cosΔ, sinΔ = math.cos(Δ), math.sin(Δ)
            den1 = (self.m1 + self.m2) * self.L1 - self.m2 * self.L1 * cosΔ * cosΔ
            den2 = (self.L2 / self.L1) * den1
            num1 = (-self.m2 * self.L1 * ω1 * ω1 * sinΔ * cosΔ +
                    self.m2 * self.g * math.sin(θ2) * cosΔ +
                    self.m2 * self.L2 * ω2 * ω2 * sinΔ -
                    (self.m1 + self.m2) * self.g * math.sin(θ1))
            num2 = (-self.m2 * self.L2 * ω2 * ω2 * sinΔ * cosΔ +
                    (self.m1 + self.m2) * self.g * math.sin(θ1) * cosΔ -
                    (self.m1 + self.m2) * self.L1 * ω1 * ω1 * sinΔ -
                    (self.m1 + self.m2) * self.g * math.sin(θ2))
            α1 = num1 / den1 if abs(den1) > 1e-9 else 0.0
            α2 = num2 / den2 if abs(den2) > 1e-9 else 0.0
            ω1 += α1 * self.dt
            ω2 += α2 * self.dt
            θ1 += ω1 * self.dt
            θ2 += ω2 * self.dt
            self.pendulums[i] = [θ1, θ2, ω1, ω2]
            p1 = (origin[0] + self.L1 * scale * math.sin(θ1),
                  origin[1] + self.L1 * scale * math.cos(θ1))
            p2 = (p1[0] + self.L2 * scale * math.sin(θ2),
                  p1[1] + self.L2 * scale * math.cos(θ2))
            traj.append(p2)
            if len(traj) > self.trail_len:
                traj.pop(0)
            col = self.colors[i % len(self.colors)]
            if len(traj) > 1:
                for j in range(1, len(traj)):
                    α = j / len(traj) * 0.4
                    Gizmos.draw_line(traj[j - 1], traj[j], col, 1, True, α)
            α_line = 0.6 if len(self.pendulums) > 1 else 0.8
            Gizmos.draw_line(origin, p1, col, 4, True, α_line)
            Gizmos.draw_line(p1, p2, col, 4, True, α_line)
            bob_r = 8 if len(self.pendulums) > 3 else 10
            Gizmos.draw_circle(p1, bob_r, col, True, True, 0.8)
            Gizmos.draw_circle(p2, bob_r, col, True, True, 0.9)
        if self.pendulums:
            Gizmos.draw_circle(origin, 4, 'white', True, True, 0.9)

_double_pendulum_sim = DoublePendulums()

def save_state():
    return _double_pendulum_sim.save()

def load_state(data):
    _double_pendulum_sim.load(data)

def start():
    pass

def update(dt):
    _double_pendulum_sim.draw_ui(panel_pos=(-450, 250))
    _double_pendulum_sim.update_and_draw(origin=(0, 0), scale=250)

def stop():
    pass