import taichi as ti
import numpy as np
import math
import pygame
import ast
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
from UPST.modules.fast_math import _apply_transforms
from UPST.modules.profiler import profile, start_profiling, stop_profiling
import numba as nb
from UPST.config import config
from UPST.modules.taichi_kernels import _taichi_compute_fractal

if config.app.use_f64:
    ti_f = ti.f64
    np_f = np.float64
else:
    ti_f = ti.f32
    np_f = np.float32

def _get_preset_rules(name):
    if name == 'sierpinski_triangle':
        return np.array([[0.5,0.0,0.0,0.5,0.0,0.0],[0.5,0.0,0.0,0.5,0.5,0.0],[0.5,0.0,0.0,0.5,0.25,0.5]],dtype=np.float64)
    elif name == 'sierpinski_carpet':
        s=1/3
        offsets=[(i*s,j*s) for i in range(3) for j in range(3) if not (i==1 and j==1)]
        rules=[]
        for ox,oy in offsets: rules.append([s,0.0,0.0,s,ox,oy])
        return np.array(rules,dtype=np.float64)
    elif name == 'koch_snowflake':
        angle=np.pi/3
        c,s=np.cos(angle),np.sin(angle)
        scale=1/3
        return np.array([[scale,0,0,scale,0,0],[scale*c,-scale*s,scale*s,scale*c,scale,0],[scale*c,scale*s,-scale*s,scale*c,0.5,scale*np.sqrt(3)/2],[scale,0,0,scale,2*scale,0]],dtype=np.float64)
    else: raise ValueError(f"Unknown preset: {name}")

def _parse_palette(palette_str):
    if not palette_str: return None
    colors=[c.strip() for c in palette_str.split(',')]
    rgb_list=[]
    for col in colors:
        if col.startswith('#') and len(col)==7:
            r,g,b=int(col[1:3],16),int(col[3:5],16),int(col[5:7],16)
            rgb_list.append((r,g,b))
        else:
            try:
                rgb=tuple(int(c.strip()) for c in col.split(','))
                if len(rgb)==3: rgb_list.append(rgb)
            except Exception: continue
    if not rgb_list: return None
    return rgb_list

class GraphPlugin(ABC):
    name: str = ""
    def __init__(self, manager: 'GraphManager'): self.manager = manager
    @abstractmethod
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple: pass
    @abstractmethod
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]: pass
    def draw_cursor_interaction(self, world_pt: Tuple[float,float], screen_pt: Tuple[int,int], tangent_vec: Optional[Tuple[float,float]], color: Tuple[int,int,int], cam: Any, mx: int, my: int): pass

class CartesianPlugin(GraphPlugin):
    name = "cartesian"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        clean_expr = expr[2:].strip() if expr.startswith('y=') else expr
        code = compile(clean_expr, '<graph>', 'eval')
        return ('cartesian', code, params.get('x_range'))
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code, x_range = compiled[1], compiled[2]
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        vp_w, vp_h = cam.get_viewport_size()
        x_min_def, x_max_def = cam_tx - vp_w/2, cam_tx + vp_w/2
        x_min, x_max = x_range if x_range else (x_min_def, x_max_def)
        steps = max(200, min(5000, int(vp_w * cam.scaling * 2)))
        dx = (x_max - x_min) / steps if steps > 0 else 0
        world_pts, screen_pts = [], []
        for i in range(steps+1):
            x = x_min + i * dx
            try:
                y = eval(code, safe_env, {"x": x})
                if isinstance(y,(int,float)) and math.isfinite(y):
                    world_pts.append((x,y))
                    screen_pts.append(cam.world_to_screen((x,y)))
            except Exception: continue
        return [('line', seg, item['color'], item['width']) for seg in self.manager._apply_line_style(screen_pts, item['style'])], world_pts, screen_pts

class ParametricPlugin(GraphPlugin):
    name = "parametric"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        parts = [p.strip() for p in expr.split(',',1)]
        if len(parts)!=2: raise ValueError("Parametric form must have two components")
        expr_x = parts[0][2:].strip() if parts[0].startswith('x=') else parts[0]
        expr_y = parts[1][2:].strip() if parts[1].startswith('y=') else parts[1]
        if parts[0].startswith('y=') and parts[1].startswith('x='): expr_y, expr_x = expr_x, expr_y
        code_x = compile(expr_x, '<graph>', 'eval')
        code_y = compile(expr_y, '<graph>', 'eval')
        return ('parametric', code_x, code_y, params.get('t_range'))
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code_x, code_y, t_range = compiled[1], compiled[2], compiled[3]
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        vp_w, vp_h = cam.get_viewport_size()
        t_min_def, t_max_def = cam_tx - vp_w/2, cam_tx + vp_w/2
        t_min, t_max = t_range if t_range else (t_min_def, t_max_def)
        steps = max(200, min(5000, int(vp_w * cam.scaling * 2)))
        dt = (t_max - t_min) / steps
        world_pts, screen_pts = [], []
        for i in range(steps+1):
            t_val = t_min + i * dt
            try:
                x_val = eval(code_x, safe_env, {"t": t_val})
                y_val = eval(code_y, safe_env, {"t": t_val})
                if isinstance(x_val,(int,float)) and isinstance(y_val,(int,float)) and math.isfinite(x_val) and math.isfinite(y_val):
                    pt = (x_val, y_val)
                    world_pts.append(pt)
                    screen_pts.append(cam.world_to_screen(pt))
            except Exception: continue
        return [('line', seg, item['color'], item['width']) for seg in self.manager._apply_line_style(screen_pts, item['style'])], world_pts, screen_pts

class PolarPlugin(GraphPlugin):
    name = "polar"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        clean_expr = expr[2:].strip() if expr.startswith(('r=','θ=','theta=')) else expr
        code_r = compile(clean_expr, '<graph>', 'eval')
        return ('polar', code_r, params.get('theta_range'))
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code_r, theta_range = compiled[1], compiled[2]
        theta_min, theta_max = theta_range if theta_range else (0, 2*math.pi)
        steps = max(200, min(5000, int(cam.get_viewport_size()[0] * cam.scaling * 2)))
        dtheta = (theta_max - theta_min) / steps
        world_pts, screen_pts = [], []
        for i in range(steps+1):
            theta = theta_min + i * dtheta
            try:
                r_val = eval(code_r, safe_env, {"theta": theta, "θ": theta})
                if isinstance(r_val,(int,float)) and math.isfinite(r_val):
                    x_val = r_val * math.cos(theta)
                    y_val = r_val * math.sin(theta)
                    pt = (x_val, y_val)
                    world_pts.append(pt)
                    screen_pts.append(cam.world_to_screen(pt))
            except Exception: continue
        return [('line', seg, item['color'], item['width']) for seg in self.manager._apply_line_style(screen_pts, item['style'])], world_pts, screen_pts

class ScatterPlugin(GraphPlugin):
    name = "scatter"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        parts = [p.strip() for p in expr.split(',',1)]
        if len(parts)!=2: raise ValueError("Scatter requires two sequences: xs, ys")
        return ('scatter', parts[0], parts[1])
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code_xs, code_ys = compiled[1], compiled[2]
        world_pts, screen_pts, drawables = [], [], []
        try:
            xs_str = eval(code_xs, {"__builtins__": {}}, {})
            ys_str = eval(code_ys, {"__builtins__": {}}, {})
            if not (isinstance(xs_str,str) and isinstance(ys_str,str)): raise ValueError
            xs = ast.literal_eval(xs_str)
            ys = ast.literal_eval(ys_str)
            if not (isinstance(xs,(list,tuple)) and isinstance(ys,(list,tuple))) or len(xs)!=len(ys): raise ValueError
            for x,y in zip(xs,ys):
                if isinstance(x,(int,float)) and isinstance(y,(int,float)) and math.isfinite(x) and math.isfinite(y):
                    pt = (x,y)
                    world_pts.append(pt)
                    scr = cam.world_to_screen(pt)
                    screen_pts.append(scr)
                    drawables.append(('point', scr, item['color'], max(2, item['width'])))
        except Exception: pass
        return drawables, world_pts, screen_pts

class FieldPlugin(GraphPlugin):
    name = "field"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        parts = [p.strip() for p in expr.split(',',1)]
        if len(parts)!=2: raise ValueError("Field requires Fx(x,y), Fy(x,y)")
        code_fx = compile(parts[0], '<graph>', 'eval')
        code_fy = compile(parts[1], '<graph>', 'eval')
        xr = params.get('x_range') or (-5.0,5.0)
        yr = params.get('y_range') or (-5.0,5.0)
        return ('field', code_fx, code_fy, xr, yr)
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code_fx, code_fy, xr, yr = compiled[1], compiled[2], compiled[3], compiled[4]
        density = max(3, min(10, int(20 * cam.scaling)))
        x_step = (xr[1]-xr[0])/density
        y_step = (yr[1]-yr[0])/density
        drawables = []
        for i in range(density+1):
            for j in range(density+1):
                x = xr[0] + i * x_step
                y = yr[0] + j * y_step
                try:
                    fx = eval(code_fx, safe_env, {"x":x,"y":y,"t":t_now})
                    fy = eval(code_fy, safe_env, {"x":x,"y":y,"t":t_now})
                    if isinstance(fx,(int,float)) and isinstance(fy,(int,float)) and math.isfinite(fx) and math.isfinite(fy):
                        start = cam.world_to_screen((x,y))
                        end = cam.world_to_screen((x + fx*0.2, y + fy*0.2))
                        drawables.append(('arrow', start, end, item['color'], item['width']))
                except Exception: pass
        return drawables, [], []

class ImplicitPlugin(GraphPlugin):
    name = "implicit"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        code_f = compile(expr, '<graph>', 'eval')
        xr = params.get('x_range') or (-5.0,5.0)
        yr = params.get('y_range') or (-5.0,5.0)
        return ('implicit', code_f, xr, yr)
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code_f, xr, yr = compiled[1], compiled[2], compiled[3]
        def f_eval(x,y):
            try:
                val = eval(code_f, safe_env, {"x":x,"y":y,"t":t_now})
                return float(val) if isinstance(val,(int,float)) else float('nan')
            except Exception: return float('nan')
        segments_list = []
        try: segments_list = self.manager._adaptive_implicit_renderer(f_eval, xr[0], xr[1], yr[0], yr[1], max_depth=9)
        except RecursionError:
            try: segments_list = self.manager._marching_squares(f_eval, xr[0], xr[1], yr[0], yr[1], threshold=0.0, resolution=200)
            except Exception: pass
        drawables = []
        for seg in segments_list:
            if len(seg)==2:
                p1 = cam.world_to_screen(seg[0])
                p2 = cam.world_to_screen(seg[1])
                drawables.append(('line', [p1,p2], item['color'], item['width']))
        return drawables, [], []

class ComplexPlugin(GraphPlugin):
    name = "complex"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        clean_expr = re.sub(r'\^', '**', expr)
        xr = params.get('x_range') or (-3.0,3.0)
        yr = params.get('y_range') or (-3.0,3.0)
        mode = params.get('complex_mode','plane')
        code_obj = compile(clean_expr, '<complex>', 'eval')
        return ('complex', code_obj, xr, yr, mode)
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        code_f, xr, yr, mode = compiled[1], compiled[2], compiled[3], compiled[4]
        if mode == 'color':
            surf, offset = self.manager._render_complex_color(code_f, xr[0], xr[1], yr[0], yr[1], screen_w, screen_h, cam)
            return [('complex_surface', surf, offset)], [], []
        else:
            density = max(5, min(15, int(25 * cam.scaling)))
            return self.manager._render_complex_plane(code_f, xr, yr, density, item['color'], item['width'], cam), [], []

class FractalPlugin(GraphPlugin):
    name = "fractal"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        if expr not in ('mandelbrot','julia'): raise ValueError("Supported fractals: mandelbrot, julia")
        c_val = params.get('c')
        c_expr = params.get('c_expr')
        if expr == 'julia' and c_val is None and c_expr is None: raise ValueError("Julia set requires 'c=<complex>' or 'c_t=...' parameter")
        return ('fractal', expr, params.get('max_iter',100), params.get('escape_radius',2.0), c_val, params.get('scale',1.0), params.get('palette'), params.get('scale_expr'), params.get('c_expr'), params.get('escape_radius_expr'))
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        fractal_name, max_iter, escape_radius, c_param, scale_static, palette_str, scale_expr, c_expr, escape_radius_expr = compiled[1:10]
        scale = scale_static
        if scale_expr:
            try: scale = max(1e-6, float(eval(scale_expr, safe_env, {})))
            except: pass
        er = escape_radius
        if escape_radius_expr:
            try: er = max(1.0, float(eval(escape_radius_expr, safe_env, {})))
            except: pass
        c_use = c_param
        if c_expr:
            try:
                c_complex = complex(eval(c_expr, safe_env, {}).replace('i','j'))
                c_use = c_complex
            except: pass
        base_w, base_h = cam.get_viewport_size()
        scaled_w = base_w * scale
        scaled_h = base_h * scale
        x_min, x_max = cam.translation.tx - scaled_w/2, cam.translation.tx + scaled_w/2
        y_min, y_max = cam.translation.ty - scaled_h/2, cam.translation.ty + scaled_h/2
        palette_obj = _parse_palette(palette_str)
        surf, offset = self.manager._render_fractal(fractal_name, x_min, x_max, y_min, y_max, screen_w, screen_h, max_iter, er, c_use, palette_obj)
        return [('fractal_surface', surf, offset)], [], []

class FractalRulePlugin(GraphPlugin):
    name = "fractal_rule"
    def compile(self, expr: str, params: Dict[str,Any]) -> Tuple:
        rule_str = expr
        depth = params.get('depth',5)
        if rule_str in ('sierpinski_triangle','sierpinski_carpet','koch_snowflake'):
            transforms = _get_preset_rules(rule_str)
            return ('fractal_rule', transforms, depth)
        else:
            try:
                rule_list = ast.literal_eval(rule_str)
                if not isinstance(rule_list,list): raise ValueError
                transforms = np.array(rule_list, dtype=np.float64)
                if transforms.ndim!=2 or transforms.shape[1]!=6: raise ValueError
                return ('fractal_rule', transforms, depth)
            except Exception: raise ValueError("Invalid rule: must be list of [a,b,c,d,e,f] or preset name")
    def render(self, compiled: Tuple, item: Dict[str,Any], cam: Any, screen_w: int, screen_h: int, t_now: float, safe_env: Dict[str,Any]) -> List[Tuple]:
        transforms, depth = compiled[1], compiled[2]
        init_pts = np.array([[0.0,0.0]], dtype=np.float64)
        pts = _apply_transforms(init_pts, transforms, depth)
        drawables = []
        for i in range(pts.shape[0]):
            x,y = pts[i,0], pts[i,1]
            scr = cam.world_to_screen((x,y))
            drawables.append(('point', scr, item['color'], max(1, item['width']//2)))
        return drawables, [], []

class GraphManager:
    def __init__(self, ui_manager):
        self.ui_manager = ui_manager
        self.graph_expression = None
        self._graph_cache = None
        self._fractal_cache = {}
        self.last_command = ""
        self.plugins: Dict[str, GraphPlugin] = {}
        self._register_default_plugins()
    def _register_default_plugins(self):
        plugin_classes = [CartesianPlugin, ParametricPlugin, PolarPlugin, ScatterPlugin, FieldPlugin, ImplicitPlugin, ComplexPlugin, FractalPlugin, FractalRulePlugin]
        for cls in plugin_classes:
            plugin = cls(self)
            self.plugins[plugin.name] = plugin
    def register_plugin(self, plugin: GraphPlugin):
        self.plugins[plugin.name] = plugin
    def unregister_plugin(self, name: str):
        self.plugins.pop(name, None)
    def handle_graph_command(self, subcmd):
        self.last_command = subcmd
        if subcmd == 'clear':
            self.graph_expression = None
            self._graph_cache = None
            self._fractal_cache.clear()
            self.ui_manager.console_ui.console_window.add_output_line_to_log("Graph cleared.")
            return
        try:
            tokens = [t.strip() for t in subcmd.split(';') if t.strip()]
            plots = []
            current = {'expr':'','color':(0,200,255,200),'width':1,'style':'solid','x_range':None,'y_range':None,'t_range':None,'theta_range':None,'plot_type':'auto','max_iter':100,'escape_radius':2.0,'c':None,'scale':1.0,'palette':None,'scale_expr':None,'c_expr':None,'escape_radius_expr':None,'complex_mode':'plane','depth':5}
            def finalize_plot():
                expr = current['expr']
                if not expr: return
                plot_type = current['plot_type']
                if plot_type == 'auto':
                    if expr.startswith('scatter '): plot_type, expr_clean = 'scatter', expr[8:].strip()
                    elif expr.startswith('field '): plot_type, expr_clean = 'field', expr[6:].strip()
                    elif expr.startswith('implicit '): plot_type, expr_clean = 'implicit', expr[9:].strip()
                    elif expr.startswith('fractal '): plot_type, expr_clean = 'fractal', expr[8:].strip()
                    elif expr.startswith('fractal_rule '): plot_type, expr_clean = 'fractal_rule', expr[13:].strip()
                    elif expr.startswith('complex '): plot_type, expr_clean = 'complex', expr[8:].strip()
                    else:
                        if ',' in expr:
                            parts = [p.strip() for p in expr.split(',',1)]
                            if len(parts)==2:
                                if (parts[0].startswith('x=') and parts[1].startswith('y=')) or (parts[0].startswith('y=') and parts[1].startswith('x=')): plot_type = 'parametric'
                                else: plot_type = 'parametric'
                            else: plot_type = 'cartesian'
                        elif any(expr.startswith(p) for p in ('r=','θ=','theta=')): plot_type = 'polar'
                        else: plot_type = 'cartesian'
                        expr_clean = expr
                else: expr_clean = expr
                plugin = self.plugins.get(plot_type)
                if not plugin: raise ValueError(f"Unknown plot type: {plot_type}")
                try:
                    compiled = plugin.compile(expr_clean, current)
                    has_time = any([current['scale_expr'], current['c_expr'], current['escape_radius_expr']])
                    plots.append({'compiled':compiled,'color':current['color'],'width':current['width'],'style':current['style'],'max_iter':current['max_iter'],'escape_radius':current['escape_radius'],'c':current['c'],'scale':current['scale'],'palette':current['palette'],'has_time_dependence':has_time})
                except Exception as inner_e: raise ValueError(f"Expression compilation failed: {inner_e}")
                current.update({'expr':'','x_range':None,'y_range':None,'t_range':None,'theta_range':None,'plot_type':'auto','max_iter':100,'escape_radius':2.0,'c':None,'scale':1.0,'palette':None,'scale_expr':None,'c_expr':None,'escape_radius_expr':None,'complex_mode':'plane','depth':5})
            i=0
            while i<len(tokens):
                tok = tokens[i]
                if tok.startswith('color:'):
                    col_str = tok[6:].strip()
                    try:
                        if col_str.startswith('#') and len(col_str)==7:
                            r,g,b = int(col_str[1:3],16),int(col_str[3:5],16),int(col_str[5:7],16)
                            current['color'] = (r,g,b,200)
                        else:
                            rgb = tuple(int(c.strip()) for c in col_str.split(','))
                            if len(rgb)==3: current['color'] = (*rgb,200)
                    except Exception: pass
                elif tok.startswith('mode:'):
                    mode_val = tok[5:].strip()
                    if mode_val in ('plane','color'): current['complex_mode'] = mode_val
                elif tok.startswith('width:'):
                    try: current['width'] = max(1, min(5, int(tok[6:].strip())))
                    except Exception: pass
                elif tok.startswith('style:'):
                    style = tok[6:].strip()
                    if style in ('solid','dashed','dotted'): current['style'] = style
                elif tok.startswith('max_iter:'):
                    try: current['max_iter'] = max(10, min(1000, int(tok[9:].strip())))
                    except Exception: pass
                elif tok.startswith('escape_radius:'):
                    try: current['escape_radius'] = max(1.0, float(tok[14:].strip()))
                    except Exception: pass
                elif tok.startswith('escape_radius_t:'): current['escape_radius_expr'] = tok[16:].strip()
                elif tok.startswith('c='):
                    try: current['c'] = complex(tok[2:].strip().replace('i','j'))
                    except Exception: pass
                elif tok.startswith('c_t='): current['c_expr'] = tok[4:].strip()
                elif tok.startswith('scale:'):
                    try: current['scale'] = max(1e-6, float(tok[6:].strip()))
                    except Exception: pass
                elif tok.startswith('scale_t:'): current['scale_expr'] = tok[8:].strip()
                elif tok.startswith('palette:'): current['palette'] = tok[8:].strip()
                elif tok.startswith('x=') and '..' in tok:
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a,b = map(self._parse_numeric_expr, rng.split('..'))
                        current['x_range'] = (a,b)
                elif tok.startswith('y=') and '..' in tok:
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a,b = map(self._parse_numeric_expr, rng.split('..'))
                        current['y_range'] = (a,b)
                elif tok.startswith('t=') and '..' in tok:
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a,b = map(self._parse_numeric_expr, rng.split('..'))
                        current['t_range'] = (a,b)
                elif (tok.startswith('θ=') or tok.startswith('theta=')) and '..' in tok:
                    key_len = 2 if tok.startswith('θ=') else 6
                    rng = tok[key_len:].strip()
                    if '..' in rng:
                        a,b = map(self._parse_numeric_expr, rng.split('..'))
                        current['theta_range'] = (a,b)
                elif tok.startswith('depth:'):
                    try: current['depth'] = max(1, min(20, int(tok[6:].strip())))
                    except Exception: pass
                else:
                    if current['expr']: finalize_plot()
                    current['expr'] = tok
                i+=1
            if current['expr']: finalize_plot()
            if not plots: raise ValueError("No valid expression to plot")
            self.graph_expression = plots
            self._graph_cache = None
            self._fractal_cache.clear()
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph set with {len(plots)} plot(s).")
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph syntax error: {e}")
    def _parse_numeric_expr(self, expr_str):
        if not expr_str: raise ValueError("Empty numeric expression")
        s = expr_str.strip().replace('θ','pi').replace('π','pi')
        s = re.sub(r'(\d)([a-zA-Z])',r'\1*\2',s)
        s = re.sub(r'(\d)\(',r'\1*(',s)
        s = re.sub(r'\)(\d)',r')*\1',s)
        s = re.sub(r'\)([a-zA-Z])',r')*\1',s)
        s = re.sub(r'([a-zA-Z])\(',r'\1*(',s)
        math_dict = {k:getattr(math,k) for k in dir(math) if not k.startswith('_')}
        safe_env = {**math_dict,"__builtins__":{}}
        try: return float(eval(s, safe_env, {}))
        except SyntaxError as se: raise ValueError(f"Syntax error in '{expr_str}': invalid expression near '{se.text}' at offset {se.offset}")
        except NameError as ne: raise ValueError(f"Undefined symbol in '{expr_str}': {ne}")
        except ZeroDivisionError: raise ValueError(f"Division by zero in '{expr_str}'")
        except Exception as e: raise ValueError(f"Evaluation failed in '{expr_str}': {type(e).__name__}: {e}")
    def _draw_arrow(self, surface, color, start, end, width=1):
        angle = math.atan2(end[1]-start[1], end[0]-start[0])
        arrow_len, arrow_angle = 8, math.pi/6
        left = (end[0]-arrow_len*math.cos(angle-arrow_angle), end[1]-arrow_len*math.sin(angle-arrow_angle))
        right = (end[0]-arrow_len*math.cos(angle+arrow_angle), end[1]-arrow_len*math.sin(angle+arrow_angle))
        pygame.draw.polygon(surface, color, [end, left, right])
    def _adaptive_implicit_renderer(self, f, x_min, x_max, y_min, y_max, depth=0, max_depth=7):
        def eval_interval(x0,x1,y0,y1):
            try:
                vals = [f(x0,y0),f(x1,y0),f(x1,y1),f(x0,y1),f((x0+x1)/2,(y0+y1)/2)]
                finite_vals = [v for v in vals if math.isfinite(v)]
                if not finite_vals: return None,None
                return min(finite_vals), max(finite_vals)
            except: return None,None
        min_val, max_val = eval_interval(x_min,x_max,y_min,y_max)
        if min_val is None or max_val is None: return []
        if min_val>0 or max_val<0: return []
        if depth>=max_depth:
            mid_x, mid_y = (x_min+x_max)/2, (y_min+y_max)/2
            try:
                center_val = f(mid_x,mid_y)
                if not math.isfinite(center_val): return []
            except: return []
            segments, corners = [], [(x_min,y_min),(x_max,y_min),(x_max,y_max),(x_min,y_max)]
            for i in range(4):
                x_a,y_a = corners[i]
                x_b,y_b = corners[(i+1)%4]
                try:
                    f_a,f_b = f(x_a,y_a),f(x_b,y_b)
                    if math.isfinite(f_a) and math.isfinite(f_b):
                        if f_a*f_b<=0 and abs(f_a-f_b)>1e-12:
                            t = f_a/(f_a-f_b)
                            ix,iy = x_a+t*(x_b-x_a), y_a+t*(y_b-y_a)
                            segments.append((ix,iy))
                except: continue
            return [segments] if len(segments)==2 else []
        else:
            xm,ym = (x_min+x_max)/2,(y_min+y_max)/2
            segs = []
            segs += self._adaptive_implicit_renderer(f,x_min,xm,y_min,ym,depth+1,max_depth)
            segs += self._adaptive_implicit_renderer(f,xm,x_max,y_min,ym,depth+1,max_depth)
            segs += self._adaptive_implicit_renderer(f,x_min,xm,ym,y_max,depth+1,max_depth)
            segs += self._adaptive_implicit_renderer(f,xm,x_max,ym,y_max,depth+1,max_depth)
            return segs
    def _marching_squares(self, f, x_min, x_max, y_min, y_max, threshold=0.0, resolution=10):
        dx,dy = (x_max-x_min)/resolution,(y_max-y_min)/resolution
        grid = []
        for j in range(resolution+1):
            row = []
            y = y_min + j*dy
            for i in range(resolution+1):
                x = x_min + i*dx
                try: val = f(x,y)
                except: val = float('inf')
                row.append(val)
            grid.append(row)
        segments = []
        for j in range(resolution):
            for i in range(resolution):
                case = 0
                if grid[j][i]>threshold: case|=1
                if grid[j][i+1]>threshold: case|=2
                if grid[j+1][i+1]>threshold: case|=4
                if grid[j+1][i]>threshold: case|=8
                if case==0 or case==15: continue
                x0,y0 = x_min+i*dx,y_min+j*dy
                x1,y1 = x0+dx,y0
                x2,y2 = x1,y0+dy
                x3,y3 = x0,y2
                def interpolate(p1,p2,v1,v2):
                    if abs(v1-v2)<1e-9: return p1
                    t = (threshold-v1)/(v2-v1)
                    return (p1[0]+t*(p2[0]-p1[0]), p1[1]+t*(p2[1]-p1[1]))
                mid_x01 = interpolate((x0,y0),(x1,y1),grid[j][i],grid[j][i+1])
                mid_x12 = interpolate((x1,y1),(x2,y2),grid[j][i+1],grid[j+1][i+1])
                mid_x23 = interpolate((x2,y2),(x3,y3),grid[j+1][i+1],grid[j+1][i])
                mid_x30 = interpolate((x3,y3),(x0,y0),grid[j+1][i],grid[j][i])
                edge_table = {1:[(mid_x30,mid_x01)],2:[(mid_x01,mid_x12)],3:[(mid_x30,mid_x12)],4:[(mid_x12,mid_x23)],5:[(mid_x30,mid_x01),(mid_x12,mid_x23)],6:[(mid_x01,mid_x23)],7:[(mid_x30,mid_x23)],8:[(mid_x23,mid_x30)],9:[(mid_x01,mid_x12),(mid_x23,mid_x30)],10:[(mid_x01,mid_x23)],11:[(mid_x12,mid_x23)],12:[(mid_x30,mid_x12)],13:[(mid_x01,mid_x30)],14:[(mid_x30,mid_x01)],15:[]}
                if case in edge_table:
                    for seg in edge_table[case]: segments.append(seg)
        return segments
    def serialize(self): return {"last_command":self.last_command}
    def deserialize(self, data):
        cmd = data.get("last_command","")
        if cmd: self.handle_graph_command(cmd)
        else:
            self.graph_expression = None
            self._graph_cache = None
            self._fractal_cache.clear()
    def draw_graph(self):
        if not self.graph_expression or not hasattr(self.ui_manager.app,'camera'):
            self._graph_cache = None
            self._fractal_cache.clear()
            return
        cam = self.ui_manager.app.camera
        screen_w, screen_h = self.ui_manager.app.screen.get_size()
        vp_w, vp_h = cam.get_viewport_size()
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        cam_scale = cam.scaling
        steps_base = max(200, min(5000, int(vp_w * cam_scale * 2)))
        uses_time = any('t' in str(item['compiled'][1]) for item in self.graph_expression if item['compiled'][0] in ('cartesian','parametric','polar','field','implicit'))
        has_fractal = any(item['compiled'][0]=='fractal' for item in self.graph_expression)
        has_animated_fractal = any(item.get('has_time_dependence',False) for item in self.graph_expression)
        if uses_time or has_fractal or has_animated_fractal:
            all_drawables, graph_metadata = self._render_graphs(steps_base, cam, screen_w, screen_h)
            self._graph_cache = None
        else:
            cache_key = (tuple((item['compiled'],item['color'][:3],item['width'],item['style']) for item in self.graph_expression),round(cam_tx,1),round(cam_ty,1),round(cam_scale,3),screen_w,screen_h)
            if self._graph_cache and self._graph_cache[0]==cache_key:
                all_drawables, graph_metadata = self._graph_cache[1]
            else:
                all_drawables, graph_metadata = self._render_graphs(steps_base, cam, screen_w, screen_h)
                self._graph_cache = (cache_key, (all_drawables, graph_metadata))
        for drawable in all_drawables:
            dtype = drawable[0]
            if dtype == 'line':
                _, pts, color, width = drawable
                if len(pts)<2: continue
                for i in range(1,len(pts)): pygame.draw.line(self.ui_manager.app.screen, color[:3], pts[i-1], pts[i], width)
            elif dtype == 'point':
                _, pos, color, size = drawable
                pygame.draw.circle(self.ui_manager.app.screen, color[:3], pos, size)
            elif dtype == 'arrow':
                _, start, end, color, width = drawable
                self._draw_arrow(self.ui_manager.app.screen, color[:3], start, end, width)
            elif dtype == 'fractal_surface' or dtype == 'complex_surface':
                _, surface, offset = drawable
                self.ui_manager.app.screen.blit(surface, offset)
        self._draw_cursor_interaction(graph_metadata, cam)
    def _draw_cursor_interaction(self, graph_metadata, cam):
        mx,my = pygame.mouse.get_pos()
        nearest = self._find_nearest_point(mx, my, graph_metadata, cam)
        if not nearest: return
        world_pt, screen_pt, tangent_vec, color = nearest
        pygame.draw.circle(self.ui_manager.app.screen, (255,255,0), screen_pt, 5, 2)
        tangent_length = 500
        if tangent_vec and (abs(tangent_vec[0])>1e-6 or abs(tangent_vec[1])>1e-6):
            tangent_norm = math.hypot(tangent_vec[0],tangent_vec[1])
            if tangent_norm>1e-6:
                tx_norm,ty_norm = tangent_vec[0]/tangent_norm,tangent_vec[1]/tangent_norm
                test_pt = (world_pt[0]+tx_norm, world_pt[1]+ty_norm)
                screen_test = cam.world_to_screen(test_pt)
                scale_factor = math.hypot(screen_test[0]-screen_pt[0], screen_test[1]-screen_pt[1])
                if scale_factor>1e-6:
                    world_step = tangent_length / scale_factor
                    pt_start_world = (world_pt[0]-tx_norm*world_step*0.5, world_pt[1]-ty_norm*world_step*0.5)
                    pt_end_world = (world_pt[0]+tx_norm*world_step*0.5, world_pt[1]+ty_norm*world_step*0.5)
                    pt_start_screen = cam.world_to_screen(pt_start_world)
                    pt_end_screen = cam.world_to_screen(pt_end_world)
                    pygame.draw.line(self.ui_manager.app.screen, (255,0,255), pt_start_screen, pt_end_screen, 2)
                    self._draw_arrow(self.ui_manager.app.screen, (255,0,255), pt_start_screen, pt_end_screen, 2)
        font = pygame.font.SysFont('monospace',14)
        coord_text = f"({world_pt[0]:.3f}, {world_pt[1]:.3f})"
        slope = tangent_vec[1]/tangent_vec[0] if tangent_vec and abs(tangent_vec[0])>1e-6 else float('inf')
        slope_text = f"slope: {slope:.2f}" if math.isfinite(slope) else "vertical"
        texts = [coord_text, slope_text]
        y_offset = 10
        for txt in texts:
            surf = font.render(txt, True, (255,255,255))
            bg = pygame.Surface((surf.get_width()+8, surf.get_height()+4))
            bg.fill((30,30,40))
            bg.blit(surf, (4,2))
            self.ui_manager.app.screen.blit(bg, (mx+10, my+y_offset))
            y_offset += surf.get_height()+4
    def _find_nearest_point(self, mx, my, graph_metadata, cam):
        cam_scale = cam.scaling
        min_dist_px = max(10.0, 30.0/cam_scale)
        min_dist = min_dist_px**2
        best = None
        for meta in graph_metadata:
            gtype, world_pts, screen_pts, color = meta
            if not screen_pts: continue
            for i,(sx,sy) in enumerate(screen_pts):
                dist_sq = (sx-mx)**2 + (sy-my)**2
                if dist_sq<min_dist:
                    min_dist = dist_sq
                    wx,wy = world_pts[i]
                    tangent = None
                    if len(world_pts)>1:
                        if i==0: nx,ny=world_pts[1]; tangent=(nx-wx,ny-wy)
                        elif i==len(world_pts)-1: px,py=world_pts[-2]; tangent=(wx-px,wy-py)
                        else: px,py=world_pts[i-1]; nx,ny=world_pts[i+1]; tangent=(nx-px,ny-py)
                    best = ((wx,wy),(int(sx),int(sy)),tangent,color)
        return best
    def _render_graphs(self, steps_base, cam, screen_w, screen_h):
        vp_w, vp_h = cam.get_viewport_size()
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        math_dict = {k:getattr(math,k) for k in dir(math) if not k.startswith('_')}
        t_now = pygame.time.get_ticks()/1000.0
        safe_env = {**math_dict,"t":t_now,"__builtins__":{}}
        all_drawables, graph_metadata = [], []
        for item in self.graph_expression:
            compiled = item['compiled']
            color = item['color']
            width = item['width']
            style = item['style']
            drawables, world_pts_all, screen_pts_all = [], [], []
            try:
                graph_type = compiled[0]
                plugin = self.plugins.get(graph_type)
                if plugin:
                    result = plugin.render(compiled, item, cam, screen_w, screen_h, t_now, safe_env)
                    if len(result)==3:
                        drawables, world_pts_all, screen_pts_all = result
                    else:
                        drawables = result
                        world_pts_all, screen_pts_all = [], []
                else:
                    drawables = self._render_special_graph(compiled, item, cam, screen_w, screen_h, t_now, safe_env)
            except Exception: drawables = []
            all_drawables.extend(drawables)
            if world_pts_all and screen_pts_all:
                graph_metadata.append((graph_type, world_pts_all, screen_pts_all, color[:3]))
        return all_drawables, graph_metadata
    def _render_special_graph(self, compiled, item, cam, screen_w, screen_h, t_now, safe_env):
        return []
    def _render_complex_plane(self, code_obj, xr, yr, density, color, width, cam):
        x_min,x_max = xr
        y_min,y_max = yr
        dx,dy = (x_max-x_min)/density,(y_max-y_min)/density
        t_now = pygame.time.get_ticks()/1000.0
        math_dict = {k:getattr(math,k) for k in dir(math) if not k.startswith('_')}
        base_env = {"t":t_now,"__builtins__":{},**math_dict}
        drawables = []
        for i in range(density+1):
            for j in range(density+1):
                x = x_min + i*dx
                y = y_min + j*dy
                z = complex(x,y)
                try:
                    env = {"z":z,"x":x,"y":y,**base_env}
                    f_val = eval(code_obj, {"__builtins__":{}}, env)
                    if isinstance(f_val,complex): w=f_val
                    elif isinstance(f_val,(int,float)): w=complex(f_val,0)
                    else: continue
                    if not (math.isfinite(w.real) and math.isfinite(w.imag)): continue
                    start = cam.world_to_screen((x,y))
                    end = cam.world_to_screen((w.real,w.imag))
                    drawables.append(('arrow', start, end, color, width))
                except Exception: continue
        return drawables
    def _render_complex_color(self, code_obj, x_min, x_max, y_min, y_max, w, h, cam):
        if w<=0 or h<=0:
            empty_surf = pygame.Surface((1,1))
            return empty_surf, (0,0)
        arr = np.zeros((h,w,3), dtype=np.uint8)
        t_now = pygame.time.get_ticks()/1000.0
        math_dict = {k:getattr(math,k) for k in dir(math) if not k.startswith('_')}
        base_env = {"t":t_now,"__builtins__":{},**math_dict}
        for j in range(h):
            y = y_max - (j/h)*(y_max-y_min)
            for i in range(w):
                x = x_min + (i/w)*(x_max-x_min)
                z = complex(x,y)
                try:
                    env = {"z":z,"x":x,"y":y,**base_env}
                    f_val = eval(code_obj, {"__builtins__":{}}, env)
                    if isinstance(f_val,complex): w_val=f_val
                    elif isinstance(f_val,(int,float)): w_val=complex(f_val,0)
                    else: w_val=complex(0,0)
                    if not (math.isfinite(w_val.real) and math.isfinite(w_val.imag)):
                        hue,val = 0.0,0.0
                    else:
                        arg = math.atan2(w_val.imag,w_val.real)
                        hue = (arg+math.pi)/(2*math.pi)
                        mag = abs(w_val)
                        val = min(1.0, math.log1p(mag)/5.0)
                    r,g,b = self._hsv_to_rgb(hue,1.0,val)
                    arr[j,i] = (int(r*255),int(g*255),int(b*255))
                except Exception: arr[j,i] = (0,0,0)
        surface = pygame.surfarray.make_surface(arr.swapaxes(0,1))
        offset_x = cam.world_to_screen((x_min,0))[0]
        offset_y = cam.world_to_screen((0,y_max))[1]
        return surface, (offset_x,offset_y)
    def _hsv_to_rgb(self, h, s, v):
        if s==0.0: return v,v,v
        i = int(h*6.0)
        f = (h*6.0)-i
        p = v*(1.0-s)
        q = v*(1.0-s*f)
        t = v*(1.0-s*(1.0-f))
        i %= 6
        if i==0: return v,t,p
        if i==1: return q,v,p
        if i==2: return p,v,t
        if i==3: return p,q,v
        if i==4: return t,p,v
        if i==5: return v,p,q
    def _render_fractal(self, name, x_min, x_max, y_min, y_max, w, h, max_iter, escape_radius, c_param, palette_obj):
        if w<=0 or h<=0:
            empty_surf = pygame.Surface((1,1))
            return empty_surf, (0,0)
        arr = np.zeros((h,w,3), dtype=np.uint8, order='C')
        esc_sq = np_f(escape_radius*escape_radius)
        fractal_type = 0 if name=='mandelbrot' else 1
        c_real = np_f(c_param.real) if c_param else np_f(0.0)
        c_imag = np_f(c_param.imag) if c_param else np_f(0.0)
        if palette_obj is None:
            default_len = min(max_iter,256)
            r_vals = np.array([min(255,int(95+160*i/default_len)) for i in range(default_len)], dtype=np.uint8)
            g_vals = np.array([min(255,int(20+100*i/default_len)) for i in range(default_len)], dtype=np.uint8)
            b_vals = np.array([min(255,int(150*(1.0-i/default_len))) for i in range(default_len)], dtype=np.uint8)
        else:
            pal_len = len(palette_obj)
            r_vals = np.array([c[0] for c in palette_obj], dtype=np.uint8)
            g_vals = np.array([c[1] for c in palette_obj], dtype=np.uint8)
            b_vals = np.array([c[2] for c in palette_obj], dtype=np.uint8)
        try:
            _taichi_compute_fractal(arr,np_f(x_min),np_f(x_max),np_f(y_min),np_f(y_max),int(w),int(h),int(max_iter),esc_sq,int(fractal_type),c_real,c_imag,r_vals,g_vals,b_vals,len(r_vals))
        except Exception as e:
            print(f"Taichi fractal error: {e}")
            arr.fill(0)
        surface = pygame.surfarray.make_surface(arr.swapaxes(0,1))
        return surface, (0,0)
    def _apply_line_style(self, points, style):
        if style=='solid' or len(points)<2: return [points]
        step = 4 if style=='dotted' else 8
        segments,current = [],[]
        for i,p in enumerate(points):
            current.append(p)
            if i%step==step-1:
                segments.append(current)
                current = []
        if current: segments.append(current)
        return segments