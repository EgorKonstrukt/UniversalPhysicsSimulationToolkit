import pygame
import json
from typing import Any, Set, List, Tuple, Optional, Union
from dataclasses import dataclass, field, asdict
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

@dataclass(frozen=True)
class TyVar:
    name: str
    def __repr__(self): return self.name

@dataclass(frozen=True)
class TyArrow:
    left: Any
    right: Any
    def __repr__(self): return f"({self.left}→{self.right})"

@dataclass(frozen=True)
class TyForall:
    var: str
    body: Any
    def __repr__(self): return f"∀{self.var}.{self.body}"

@dataclass(frozen=True)
class TyAbs:
    tparam: str
    body: Any
    def __repr__(self): return f"(Λ{self.tparam}.{self.body})"

@dataclass(frozen=True)
class TyApp:
    term: Any
    ty: Any
    def __repr__(self): return f"({self.term} [{self.ty}])"

class SystemFParser:
    def __init__(self, s: str):
        self.s = (s.replace('λ', '\\').replace('Λ', 'L')
                   .replace('→', '->').replace('∀', 'A')
                   .replace(' ', ''))
        self.i = 0
    def parse(self) -> Any:
        term = self.parse_term()
        if self.i < len(self.s):
            raise ValueError(f"Unexpected trailing chars at {self.i}: '{self.s[self.i:]}'")
        return term
    def parse_term(self) -> Any:
        term = self.parse_atom()
        while self.i < len(self.s) and (self.peek() in ['(', '\\', 'L'] or self.peek().isalpha()):
            if self.peek() == '[':
                self.consume('[')
                ty = self.parse_type()
                self.consume(']')
                term = TyApp(term, ty)
            else:
                term = App(term, self.parse_atom())
        return term
    def parse_atom(self) -> Any:
        if self.peek() == '(': self.consume('('); t = self.parse_term(); self.consume(')'); return t
        elif self.peek() == '\\': self.consume('\\'); v = self.parse_var(); self.consume('.'); return Abs(v.name, self.parse_term())
        elif self.peek() == 'L': self.consume('L'); v = self.parse_var(); self.consume('.'); return TyAbs(v.name, self.parse_term())
        elif self.peek().isalpha(): return self.parse_var()
        else: raise ValueError(f"Expected atom, got '{self.peek()}'")
    def parse_type(self) -> Any:
        ty = self.parse_ty_forall()
        while self.i < len(self.s) and self.peek() == '(':
            ty = TyArrow(ty, self.parse_ty_forall())
        return ty
    def parse_ty_forall(self) -> Any:
        if self.peek() == 'A':
            self.consume('A')
            v = self.parse_var()
            self.consume('.')
            return TyForall(v.name, self.parse_ty_forall())
        return self.parse_ty_arrow()
    def parse_ty_arrow(self) -> Any:
        left = self.parse_ty_atom()
        if self.i < len(self.s) and self.peek() == '-':
            self.consume('-')
            self.consume('>')
            return TyArrow(left, self.parse_ty_arrow())
        return left
    def parse_ty_atom(self) -> Any:
        if self.peek() == '(': self.consume('('); t = self.parse_type(); self.consume(')'); return t
        elif self.peek().isalpha(): return TyVar(self.parse_var().name)
        else: raise ValueError(f"Expected type atom, got '{self.peek()}'")
    def parse_var(self) -> Var:
        start = self.i
        while self.i < len(self.s) and self.s[self.i].isalpha(): self.i += 1
        if start == self.i: raise ValueError("Expected variable name")
        return Var(self.s[start:self.i])
    def peek(self) -> str: return self.s[self.i] if self.i < len(self.s) else ''
    def consume(self, c: str):
        if self.peek() != c: raise ValueError(f"Expected '{c}', got '{self.peek()}' at {self.i}")
        self.i += 1

def free_vars_term(t: Any) -> Set[str]:
    if isinstance(t, Var): return {t.name}
    elif isinstance(t, Abs): return free_vars_term(t.body) - {t.param}
    elif isinstance(t, App): return free_vars_term(t.func) | free_vars_term(t.arg)
    elif isinstance(t, TyAbs): return free_vars_term(t.body) - {t.tparam}
    elif isinstance(t, TyApp): return free_vars_term(t.term)
    return set()

def free_vars_type(ty: Any) -> Set[str]:
    if isinstance(ty, TyVar): return {ty.name}
    elif isinstance(ty, TyArrow): return free_vars_type(ty.left) | free_vars_type(ty.right)
    elif isinstance(ty, TyForall): return free_vars_type(ty.body) - {ty.var}
    return set()

def fresh_var(avoid: Set[str], base: str = 'x') -> str:
    i = 0
    while True:
        cand = f"{base}{i}" if i > 0 else base
        if cand not in avoid: return cand
        i += 1

def substitute_term(t: Any, var: str, repl: Any) -> Any:
    if isinstance(t, Var): return repl if t.name == var else t
    elif isinstance(t, Abs):
        if t.param == var: return t
        fv_repl = free_vars_term(repl)
        if t.param in fv_repl:
            new_p = fresh_var(free_vars_term(t) | fv_repl, t.param)
            new_b = substitute_term(t.body, t.param, Var(new_p))
            return Abs(new_p, substitute_term(new_b, var, repl))
        return Abs(t.param, substitute_term(t.body, var, repl))
    elif isinstance(t, App): return App(substitute_term(t.func, var, repl), substitute_term(t.arg, var, repl))
    elif isinstance(t, TyAbs): return TyAbs(t.tparam, substitute_term(t.body, var, repl))
    elif isinstance(t, TyApp): return TyApp(substitute_term(t.term, var, repl), t.ty)
    return t

def substitute_type_in_term(t: Any, tvar: str, ty: Any) -> Any:
    if isinstance(t, Var): return t
    elif isinstance(t, Abs): return Abs(t.param, substitute_type_in_term(t.body, tvar, ty))
    elif isinstance(t, App): return App(substitute_type_in_term(t.func, tvar, ty), substitute_type_in_term(t.arg, tvar, ty))
    elif isinstance(t, TyAbs):
        if t.tparam == tvar: return t
        ftv_ty = free_vars_type(ty)
        if t.tparam in ftv_ty:
            new_p = fresh_var(free_vars_type(t) | ftv_ty, t.tparam)
            new_b = substitute_type_in_term(t.body, t.tparam, TyVar(new_p))
            return TyAbs(new_p, substitute_type_in_term(new_b, tvar, ty))
        return TyAbs(t.tparam, substitute_type_in_term(t.body, tvar, ty))
    elif isinstance(t, TyApp): return TyApp(substitute_type_in_term(t.term, tvar, ty), ty if t.ty == TyVar(tvar) else t.ty)
    return t

def reduce_once(t: Any) -> Optional[Any]:
    if isinstance(t, App):
        if isinstance(t.func, Abs): return substitute_term(t.func.body, t.func.param, t.arg)
        rf = reduce_once(t.func)
        if rf is not None: return App(rf, t.arg)
        ra = reduce_once(t.arg)
        if ra is not None: return App(t.func, ra)
    elif isinstance(t, TyApp):
        if isinstance(t.term, TyAbs): return substitute_type_in_term(t.term.body, t.term.tparam, t.ty)
        rt = reduce_once(t.term)
        if rt is not None: return TyApp(rt, t.ty)
    elif isinstance(t, Abs): rb = reduce_once(t.body); return Abs(t.param, rb) if rb else None
    elif isinstance(t, TyAbs): rb = reduce_once(t.body); return TyAbs(t.tparam, rb) if rb else None
    return None

def full_reduce(t: Any, max_steps: int = 100) -> List[Any]:
    steps = [t]
    for _ in range(max_steps):
        nxt = reduce_once(steps[-1])
        if nxt is None: break
        steps.append(nxt)
    return steps

@dataclass
class SystemFConfig:
    max_reduction_steps: int = 50
    node_radius: float = 0.3
    h_spacing: float = 10.2
    v_spacing: float = 0.9
    root_x: float = 0.0
    root_y: float = -3.0

class SystemFVisualizer:
    def __init__(self, app, cfg: SystemFConfig):
        self.app = app
        self.cfg = cfg
        self.font = pygame.font.SysFont(None, 20)
        self.steps = []
        self.step_idx = 0
        self.active = False
        self.colors = {
            'var': (255,255,255), 'abs': (100,200,255), 'app': (255,150,150),
            'tyabs': (180,255,180), 'tyapp': (255,200,100), 'unknown': (200,200,200), 'link': (200,200,200)
        }
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
            elif isinstance(n, TyAbs):
                nodes.append((px, py, f"Λ{n.tparam}", self.colors['tyabs']))
                cx, cy = px, py + self.cfg.v_spacing
                dfs(n.body, cx, cy, depth + 1)
                links.append(((px, py), (cx, cy)))
            elif isinstance(n, TyApp):
                nodes.append((px, py, "[T]", self.colors['tyapp']))
                cx, cy = px, py + self.cfg.v_spacing
                dfs(n.term, cx, cy, depth + 1)
                links.append(((px, py), (cx, cy)))
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
        self.cfg = getattr(app.config, 'system_f', SystemFConfig())
        self.vis = SystemFVisualizer(app, self.cfg)
    def handle_system_f_expr(self, expr: str):
        try:
            term = SystemFParser(expr.strip()).parse()
            self.vis.steps = full_reduce(term, max_steps=self.cfg.max_reduction_steps)
            self.vis.step_idx = 0
            self.vis.active = True
            print(f"Parsed & reduced in {len(self.vis.steps)} steps.")
        except Exception as e:
            print(f"System F error: {e}")
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
    name="system_f",
    version="1.0",
    description="Interactive System F (polymorphic lambda calculus) reduction visualizer",
    author="Zarrakun",
    icon_path="systemf.png",
    dependency_specs={},
    config_class=SystemFConfig,
    on_load=lambda mgr, inst: setattr(mgr.app, 'system_f_plugin', inst),
    on_unload=lambda mgr, inst: delattr(mgr.app, 'system_f_plugin') if hasattr(mgr.app, 'system_f_plugin') else None,
    on_draw=lambda mgr, inst: inst.on_draw(),
    on_event=lambda mgr, inst, ev: inst.on_event(ev),
    console_commands={'systemf': lambda inst, expr: inst.handle_system_f_expr(expr)}
)

Config.register_plugin_config("system_f", SystemFConfig)