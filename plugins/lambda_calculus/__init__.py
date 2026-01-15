import pygame
from typing import Any, Set, List, Tuple, Optional
from dataclasses import dataclass, field
from UPST.config import Config

@dataclass(frozen=True)
class Var:
    name: str
    def __repr__(self): return self.name

@dataclass(frozen=True)
class Abs:
    param: str
    body: Any
    def __repr__(self): return f"(λ{self.param}.{self.body})"

@dataclass(frozen=True)
class App:
    func: Any
    arg: Any
    def __repr__(self): return f"({self.func} {self.arg})"

class LambdaParser:
    def __init__(self, s: str):
        self.s = s.replace('λ', '\\').replace(' ', '')
        self.i = 0
    def parse(self) -> Any:
        term = self.parse_term()
        if self.i < len(self.s):
            raise ValueError(f"Unexpected trailing chars at {self.i}: '{self.s[self.i:]}'")
        return term
    def parse_term(self) -> Any:
        term = self.parse_atom()
        while self.i < len(self.s) and (self.peek() in ['(', '\\'] or self.peek().isalpha()):
            term = App(term, self.parse_atom())
        return term
    def parse_atom(self) -> Any:
        if self.peek() == '(': self.consume('('); t = self.parse_term(); self.consume(')'); return t
        elif self.peek() == '\\': self.consume('\\'); v = self.parse_var(); self.consume('.'); return Abs(v.name, self.parse_term())
        elif self.peek().isalpha(): return self.parse_var()
        else: raise ValueError(f"Expected atom, got '{self.peek()}'")
    def parse_var(self) -> Var:
        start = self.i
        while self.i < len(self.s) and self.s[self.i].isalpha(): self.i += 1
        if start == self.i: raise ValueError("Expected variable name")
        return Var(self.s[start:self.i])
    def peek(self) -> str: return self.s[self.i] if self.i < len(self.s) else ''
    def consume(self, c: str):
        if self.peek() != c: raise ValueError(f"Expected '{c}', got '{self.peek()}' at {self.i}")
        self.i += 1

def free_vars(t: Any) -> Set[str]:
    if isinstance(t, Var): return {t.name}
    elif isinstance(t, Abs): return free_vars(t.body) - {t.param}
    elif isinstance(t, App): return free_vars(t.func) | free_vars(t.arg)
    return set()

def fresh_var(avoid: Set[str], base: str = 'x') -> str:
    i = 0
    while True:
        cand = f"{base}{i}" if i > 0 else base
        if cand not in avoid: return cand
        i += 1

def substitute(t: Any, var: str, repl: Any) -> Any:
    if isinstance(t, Var): return repl if t.name == var else t
    elif isinstance(t, Abs):
        if t.param == var: return t
        fv_repl = free_vars(repl)
        if t.param in fv_repl:
            new_p = fresh_var(free_vars(t) | fv_repl, t.param)
            new_b = substitute(t.body, t.param, Var(new_p))
            return Abs(new_p, substitute(new_b, var, repl))
        return Abs(t.param, substitute(t.body, var, repl))
    elif isinstance(t, App): return App(substitute(t.func, var, repl), substitute(t.arg, var, repl))
    return t

def reduce_once(t: Any) -> Optional[Any]:
    if isinstance(t, App):
        if isinstance(t.func, Abs): return substitute(t.func.body, t.func.param, t.arg)
        rf = reduce_once(t.func)
        if rf is not None: return App(rf, t.arg)
        ra = reduce_once(t.arg)
        if ra is not None: return App(t.func, ra)
    elif isinstance(t, Abs):
        rb = reduce_once(t.body)
        if rb is not None: return Abs(t.param, rb)
    return None

def full_reduce(t: Any, max_steps: int = 100) -> List[Any]:
    steps = [t]
    for _ in range(max_steps):
        nxt = reduce_once(steps[-1])
        if nxt is None: break
        steps.append(nxt)
    return steps

@dataclass
class LambdaCalculusConfig:
    max_reduction_steps: int = 50
    node_radius: float = 0.3
    h_spacing: float = 10.2
    v_spacing: float = 0.9
    root_x: float = 0.0
    root_y: float = -3.0

class LambdaVisualizer:
    def __init__(self, app, cfg: LambdaCalculusConfig):
        self.app = app
        self.cfg = cfg
        self.font = pygame.font.SysFont(None, 20)
        self.steps = []
        self.step_idx = 0
        self.active = False
        self.colors = {'var': (255,255,255), 'abs': (100,200,255), 'app': (255,150,150), 'unknown': (200,200,200), 'link': (200,200,200)}
    def _layout(self, t: Any, x: float, y: float, d: int = 0) -> Tuple[List, List]:
        nodes, links = [], []
        def dfs(n, px, py, depth):
            if isinstance(n, Var): nodes.append((px, py, str(n), self.colors['var']))
            elif isinstance(n, Abs):
                nodes.append((px, py, f"λ{n.param}", self.colors['abs']))
                cx, cy = px, py + self.cfg.v_spacing
                dfs(n.body, cx, cy, depth + 1)
                links.append(((px, py), (cx, cy)))
            elif isinstance(n, App):
                nodes.append((px, py, "·", self.colors['app']))
                h_off = self.cfg.h_spacing / (2 ** min(depth, 4))
                lx, rx = px - h_off, px + h_off
                cy = py + self.cfg.v_spacing
                dfs(n.func, lx, cy, depth + 1)
                dfs(n.arg, rx, cy, depth + 1)
                links.extend([((px, py), (lx, cy)), ((px, py), (rx, cy))])
            else: nodes.append((px, py, "?", self.colors['unknown']))
        dfs(t, x, y, d)
        return nodes, links
    def draw(self):
        if not self.active or not self.steps or not (cam := self.app.camera): return
        t = self.steps[self.step_idx]
        nodes, links = self._layout(t, self.cfg.root_x, self.cfg.root_y)
        screen_links = [(cam.world_to_screen(a), cam.world_to_screen(b)) for a, b in links]
        screen_nodes = [(cam.world_to_screen((wx, wy)), lbl, col) for wx, wy, lbl, col in nodes]
        for s1, s2 in screen_links: pygame.draw.line(self.app.screen, self.colors['link'], s1, s2, 2)
        r_px = max(8, int(self.cfg.node_radius * cam.scaling))
        for (sx, sy), lbl, col in screen_nodes:
            pygame.draw.circle(self.app.screen, col, (int(sx), int(sy)), r_px)
            txt = self.font.render(lbl, True, (0,0,0))
            self.app.screen.blit(txt, (int(sx) - txt.get_width() // 2, int(sy) - txt.get_height() // 2))
    def next_step(self): self.step_idx = min(self.step_idx + 1, len(self.steps) - 1)
    def prev_step(self): self.step_idx = max(self.step_idx - 1, 0)
    def reset(self): self.steps.clear(); self.step_idx = 0; self.active = False

class PluginImpl:
    def __init__(self, app):
        self.app = app
        self.cfg = getattr(app.config, 'lambda_calculus', LambdaCalculusConfig())
        self.vis = LambdaVisualizer(app, self.cfg)
    def handle_lambda_expr(self, expr: str):
        try:
            term = LambdaParser(expr.strip()).parse()
            self.vis.steps = full_reduce(term, max_steps=self.cfg.max_reduction_steps)
            self.vis.step_idx = 0
            self.vis.active = True
            print(f"Parsed & reduced in {len(self.vis.steps)} steps.")
        except Exception as e:
            print(f"Lambda error: {e}")
            self.vis.active = False
    def on_event(self, ev):
        if not self.vis.active: return False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RIGHT: self.vis.next_step()
            elif ev.key == pygame.K_LEFT: self.vis.prev_step()
            elif ev.key == pygame.K_ESCAPE: self.vis.reset()
            return True
        return False
    def on_draw(self):
        self.vis.draw()

PLUGIN = Plugin(
    name="Lambda Calculus Visualizer",
    version="1.0",
    description="Interactive lambda calculus reduction visualizer",
    dependency_specs={},
    config_class=LambdaCalculusConfig,
    on_load=lambda mgr, inst: setattr(mgr.app, 'lambda_plugin', inst),
    on_unload=lambda mgr, inst: delattr(mgr.app, 'lambda_plugin') if hasattr(mgr.app, 'lambda_plugin') else None,
    on_draw=lambda mgr, inst: inst.on_draw(),
    on_event=lambda mgr, inst, ev: inst.on_event(ev),
    console_commands={'lambda': lambda inst, expr: inst.handle_lambda_expr(expr)}
)