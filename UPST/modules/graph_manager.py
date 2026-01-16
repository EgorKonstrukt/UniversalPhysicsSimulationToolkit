import taichi as ti
import numpy as np
import math
import pygame
import ast
import re

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
        return np.array([
            [0.5, 0.0, 0.0, 0.5, 0.0, 0.0],
            [0.5, 0.0, 0.0, 0.5, 0.5, 0.0],
            [0.5, 0.0, 0.0, 0.5, 0.25, 0.5]
        ], dtype=np.float64)
    elif name == 'sierpinski_carpet':
        s = 1 / 3
        offsets = [(i * s, j * s) for i in range(3) for j in range(3) if not (i == 1 and j == 1)]
        rules = []
        for ox, oy in offsets:
            rules.append([s, 0.0, 0.0, s, ox, oy])
        return np.array(rules, dtype=np.float64)
    elif name == 'koch_snowflake':
        angle = np.pi / 3
        c, s = np.cos(angle), np.sin(angle)
        scale = 1 / 3
        return np.array([
            [scale, 0, 0, scale, 0, 0],
            [scale * c, -scale * s, scale * s, scale * c, scale, 0],
            [scale * c, scale * s, -scale * s, scale * c, 0.5, scale * np.sqrt(3) / 2],
            [scale, 0, 0, scale, 2 * scale, 0]
        ], dtype=np.float64)
    else:
        raise ValueError(f"Unknown preset: {name}")

def _parse_palette(palette_str):
    if not palette_str:
        return None
    colors = [c.strip() for c in palette_str.split(',')]
    rgb_list = []
    for col in colors:
        if col.startswith('#') and len(col) == 7:
            r, g, b = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
            rgb_list.append((r, g, b))
        else:
            try:
                rgb = tuple(int(c.strip()) for c in col.split(','))
                if len(rgb) == 3: rgb_list.append(rgb)
            except Exception:
                continue
    if not rgb_list:
        return None
    return rgb_list

class GraphManager:
    def __init__(self, ui_manager):
        self.ui_manager = ui_manager
        self.graph_expression = None
        self._graph_cache = None
        self._fractal_cache = {}

    def handle_graph_command(self, subcmd):
        if subcmd == 'clear':
            self.graph_expression = None
            self._graph_cache = None
            self._fractal_cache.clear()
            self.ui_manager.console_ui.console_window.add_output_line_to_log("Graph cleared.")
            return
        try:
            tokens = [t.strip() for t in subcmd.split(';') if t.strip()]
            plots = []
            current = {
                'expr': '', 'color': (0, 200, 255, 200), 'width': 1, 'style': 'solid',
                'x_range': None, 'y_range': None, 't_range': None, 'theta_range': None,
                'plot_type': 'auto', 'max_iter': 100, 'escape_radius': 2.0, 'c': None,
                'scale': 1.0, 'palette': None,
                'scale_expr': None, 'c_expr': None, 'escape_radius_expr': None
            }

            def finalize_plot():
                expr = current['expr']
                if not expr: return
                plot_type = current['plot_type']
                if plot_type == 'auto':
                    if expr.startswith('scatter '):
                        plot_type = 'scatter'
                        expr_clean = expr[8:].strip()
                    elif expr.startswith('field '):
                        plot_type = 'field'
                        expr_clean = expr[6:].strip()
                    elif expr.startswith('implicit '):
                        plot_type = 'implicit'
                        expr_clean = expr[9:].strip()
                    elif expr.startswith('fractal '):
                        plot_type = 'fractal'
                        expr_clean = expr[8:].strip()
                    elif expr.startswith('fractal_rule '):
                        plot_type = 'fractal_rule'
                        expr_clean = expr[13:].strip()
                    elif expr.startswith('complex '):
                        plot_type = 'complex'
                        expr_clean = expr[8:].strip()
                    else:
                        if ',' in expr:
                            parts = [p.strip() for p in expr.split(',', 1)]
                            if len(parts) == 2:
                                if (parts[0].startswith('x=') and parts[1].startswith('y=')) or \
                                        (parts[0].startswith('y=') and parts[1].startswith('x=')):
                                    plot_type = 'parametric'
                                else:
                                    plot_type = 'parametric'
                            else:
                                plot_type = 'cartesian'
                        elif any(expr.startswith(p) for p in ('r=', 'θ=', 'theta=')):
                            plot_type = 'polar'
                        else:
                            plot_type = 'cartesian'
                        expr_clean = expr
                else:
                    expr_clean = expr

                try:
                    if plot_type == 'cartesian':
                        clean_expr = expr_clean[2:].strip() if expr_clean.startswith('y=') else expr_clean
                        code = compile(clean_expr, '<graph>', 'eval')
                        compiled = ('cartesian', code, current['x_range'])
                    elif plot_type == 'parametric':
                        parts = [p.strip() for p in expr_clean.split(',', 1)]
                        if len(parts) != 2:
                            raise ValueError("Parametric form must have two components separated by comma")
                        expr_x = parts[0][2:].strip() if parts[0].startswith('x=') else parts[0]
                        expr_y = parts[1][2:].strip() if parts[1].startswith('y=') else parts[1]
                        if parts[0].startswith('y=') and parts[1].startswith('x='):
                            expr_y, expr_x = expr_x, expr_y
                        code_x = compile(expr_x, '<graph>', 'eval')
                        code_y = compile(expr_y, '<graph>', 'eval')
                        compiled = ('parametric', code_x, code_y, current['t_range'])
                    elif plot_type == 'polar':
                        clean_expr = expr_clean[2:].strip() if expr_clean.startswith(
                            ('r=', 'θ=', 'theta=')) else expr_clean
                        code_r = compile(clean_expr, '<graph>', 'eval')
                        compiled = ('polar', code_r, current['theta_range'])
                    elif plot_type == 'scatter':
                        parts = [p.strip() for p in expr_clean.split(',', 1)]
                        if len(parts) != 2: raise ValueError("Scatter requires two sequences: xs, ys")
                        compiled = ('scatter', parts[0], parts[1])
                    elif plot_type == 'field':
                        parts = [p.strip() for p in expr_clean.split(',', 1)]
                        if len(parts) != 2: raise ValueError("Field requires Fx(x,y), Fy(x,y)")
                        code_fx = compile(parts[0], '<graph>', 'eval')
                        code_fy = compile(parts[1], '<graph>', 'eval')
                        xr = current['x_range'] or (-5.0, 5.0)
                        yr = current['y_range'] or (-5.0, 5.0)
                        compiled = ('field', code_fx, code_fy, xr, yr)
                    elif plot_type == 'implicit':
                        code_f = compile(expr_clean, '<graph>', 'eval')
                        xr = current['x_range'] or (-5.0, 5.0)
                        yr = current['y_range'] or (-5.0, 5.0)
                        compiled = ('implicit', code_f, xr, yr)
                    elif plot_type == 'complex':
                        clean_expr = re.sub(r'\^', '**', expr_clean)
                        xr = current['x_range'] or (-3.0, 3.0)
                        yr = current['y_range'] or (-3.0, 3.0)
                        mode = current.get('complex_mode', 'plane')
                        code_obj = compile(clean_expr, '<complex>', 'eval')
                        compiled = ('complex', code_obj, xr, yr, mode)
                    elif plot_type == 'fractal':
                        if expr_clean not in ('mandelbrot', 'julia'):
                            raise ValueError("Supported fractals: mandelbrot, julia")
                        c_val = current['c']
                        c_expr = current['c_expr']
                        if expr_clean == 'julia' and c_val is None and c_expr is None:
                            raise ValueError("Julia set requires 'c=<complex>' or 'c_t=...' parameter")
                        compiled = (
                            'fractal', expr_clean, current['max_iter'], current['escape_radius'],
                            c_val, current['scale'], current['palette'],
                            current['scale_expr'], current['c_expr'], current['escape_radius_expr']
                        )
                    elif plot_type == 'fractal_rule':
                        rule_str = expr_clean
                        depth = current.get('depth', 5)
                        if rule_str in ('sierpinski_triangle', 'sierpinski_carpet', 'koch_snowflake'):
                            transforms = _get_preset_rules(rule_str)
                            compiled = ('fractal_rule', transforms, depth)
                        else:
                            try:
                                rule_list = ast.literal_eval(rule_str)
                                if not isinstance(rule_list, list):
                                    raise ValueError
                                transforms = np.array(rule_list, dtype=np.float64)
                                if transforms.ndim != 2 or transforms.shape[1] != 6:
                                    raise ValueError
                                compiled = ('fractal_rule', transforms, depth)
                            except Exception:
                                raise ValueError("Invalid rule: must be list of [a,b,c,d,e,f] or preset name")
                    else:
                        raise ValueError(f"Unknown plot type: {plot_type}")
                except SyntaxError as se:
                    raise ValueError(f"Syntax error in expression '{expr_clean}': {se.msg} at column {se.offset}")
                except Exception as inner_e:
                    raise ValueError(f"Expression compilation failed: {inner_e}")

                plots.append({
                    'compiled': compiled, 'color': current['color'], 'width': current['width'],
                    'style': current['style'], 'max_iter': current['max_iter'],
                    'escape_radius': current['escape_radius'], 'c': current['c'],
                    'scale': current['scale'], 'palette': current['palette'],
                    'has_time_dependence': any([
                        current['scale_expr'], current['c_expr'], current['escape_radius_expr']
                    ])
                })
                current.update({
                    'expr': '', 'x_range': None, 'y_range': None, 't_range': None, 'theta_range': None,
                    'plot_type': 'auto', 'max_iter': 100, 'escape_radius': 2.0, 'c': None,
                    'scale': 1.0, 'palette': None,
                    'scale_expr': None, 'c_expr': None, 'escape_radius_expr': None
                })

            i = 0
            while i < len(tokens):
                tok = tokens[i]
                if tok.startswith('color:'):
                    col_str = tok[6:].strip()
                    try:
                        if col_str.startswith('#') and len(col_str) == 7:
                            r, g, b = int(col_str[1:3], 16), int(col_str[3:5], 16), int(col_str[5:7], 16)
                            current['color'] = (r, g, b, 200)
                        else:
                            rgb = tuple(int(c.strip()) for c in col_str.split(','))
                            if len(rgb) == 3: current['color'] = (*rgb, 200)
                    except Exception:
                        pass
                elif tok.startswith('mode:'):
                    mode_val = tok[5:].strip()
                    if mode_val in ('plane', 'color'): current['complex_mode'] = mode_val
                elif tok.startswith('width:'):
                    try:
                        current['width'] = max(1, min(5, int(tok[6:].strip())))
                    except Exception:
                        pass
                elif tok.startswith('style:'):
                    style = tok[6:].strip()
                    if style in ('solid', 'dashed', 'dotted'): current['style'] = style
                elif tok.startswith('max_iter:'):
                    try:
                        current['max_iter'] = max(10, min(1000, int(tok[9:].strip())))
                    except Exception:
                        pass
                elif tok.startswith('escape_radius:'):
                    try:
                        current['escape_radius'] = max(1.0, float(tok[14:].strip()))
                    except Exception:
                        pass
                elif tok.startswith('escape_radius_t:'):
                    current['escape_radius_expr'] = tok[16:].strip()
                elif tok.startswith('c='):
                    try:
                        c_str = tok[2:].strip()
                        c_complex = complex(c_str.replace('i', 'j'))
                        current['c'] = c_complex
                    except Exception:
                        pass
                elif tok.startswith('c_t='):
                    current['c_expr'] = tok[4:].strip()
                elif tok.startswith('scale:'):
                    try:
                        current['scale'] = max(1e-6, float(tok[6:].strip()))
                    except Exception:
                        pass
                elif tok.startswith('scale_t:'):
                    current['scale_expr'] = tok[8:].strip()
                elif tok.startswith('palette:'):
                    current['palette'] = tok[8:].strip()
                elif tok.startswith('x=') and '..' in tok:
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a, b = map(self._parse_numeric_expr, rng.split('..'))
                        current['x_range'] = (a, b)
                elif tok.startswith('y=') and '..' in tok:
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a, b = map(self._parse_numeric_expr, rng.split('..'))
                        current['y_range'] = (a, b)
                elif tok.startswith('t=') and '..' in tok:
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a, b = map(self._parse_numeric_expr, rng.split('..'))
                        current['t_range'] = (a, b)
                elif (tok.startswith('θ=') or tok.startswith('theta=')) and '..' in tok:
                    key_len = 2 if tok.startswith('θ=') else 6
                    rng = tok[key_len:].strip()
                    if '..' in rng:
                        a, b = map(self._parse_numeric_expr, rng.split('..'))
                        current['theta_range'] = (a, b)
                elif tok.startswith('depth:'):
                    try:
                        current['depth'] = max(1, min(20, int(tok[6:].strip())))
                    except Exception:
                        pass
                else:
                    if current['expr']: finalize_plot()
                    current['expr'] = tok
                i += 1
            if current['expr']: finalize_plot()
            if not plots: raise ValueError("No valid expression to plot")
            self.graph_expression = plots
            self._graph_cache = None
            self._fractal_cache.clear()
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph set with {len(plots)} plot(s).")
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph syntax error: {e}")

    def _parse_numeric_expr(self, expr_str):
        if not expr_str:
            raise ValueError("Empty numeric expression")
        s = expr_str.strip()
        orig = s
        s = s.replace('θ', 'pi').replace('π', 'pi')
        s = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', s)
        s = re.sub(r'(\d)\(', r'\1*(', s)
        s = re.sub(r'\)(\d)', r')*\1', s)
        s = re.sub(r'\)([a-zA-Z])', r')*\1', s)
        s = re.sub(r'([a-zA-Z])\(', r'\1*(', s)
        math_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
        safe_env = {**math_dict, "__builtins__": {}}
        try:
            return float(eval(s, safe_env, {}))
        except SyntaxError as se:
            raise ValueError(f"Syntax error in '{orig}': invalid expression near '{se.text}' at offset {se.offset}")
        except NameError as ne:
            raise ValueError(f"Undefined symbol in '{orig}': {ne}")
        except ZeroDivisionError:
            raise ValueError(f"Division by zero in '{orig}'")
        except Exception as e:
            raise ValueError(f"Evaluation failed in '{orig}': {type(e).__name__}: {e}")

    def _draw_arrow(self, surface, color, start, end, width=1):
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_len = 8
        arrow_angle = math.pi / 6
        left = (end[0] - arrow_len * math.cos(angle - arrow_angle), end[1] - arrow_len * math.sin(angle - arrow_angle))
        right = (end[0] - arrow_len * math.cos(angle + arrow_angle), end[1] - arrow_len * math.sin(angle + arrow_angle))
        pygame.draw.polygon(surface, color, [end, left, right])

    def _adaptive_implicit_renderer(self, f, x_min, x_max, y_min, y_max, depth=0, max_depth=7):
        def eval_interval(x0, x1, y0, y1):
            try:
                vals = [
                    f(x0, y0), f(x1, y0), f(x1, y1), f(x0, y1),
                    f((x0 + x1) / 2, (y0 + y1) / 2)
                ]
                finite_vals = [v for v in vals if math.isfinite(v)]
                if not finite_vals: return None, None
                return min(finite_vals), max(finite_vals)
            except:
                return None, None

        min_val, max_val = eval_interval(x_min, x_max, y_min, y_max)
        if min_val is None or max_val is None: return []
        if min_val > 0 or max_val < 0: return []
        if depth >= max_depth:
            mid_x, mid_y = (x_min + x_max) / 2, (y_min + y_max) / 2
            try:
                center_val = f(mid_x, mid_y)
                if not math.isfinite(center_val): return []
            except:
                return []
            segments = []
            corners = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
            for i in range(4):
                x_a, y_a = corners[i]
                x_b, y_b = corners[(i + 1) % 4]
                try:
                    f_a, f_b = f(x_a, y_a), f(x_b, y_b)
                    if math.isfinite(f_a) and math.isfinite(f_b):
                        if f_a * f_b <= 0 and abs(f_a - f_b) > 1e-12:
                            t = f_a / (f_a - f_b)
                            ix = x_a + t * (x_b - x_a)
                            iy = y_a + t * (y_b - y_a)
                            segments.append((ix, iy))
                except:
                    continue
            if len(segments) == 2:
                return [segments]
            else:
                return []
        else:
            xm = (x_min + x_max) / 2
            ym = (y_min + y_max) / 2
            segs = []
            segs += self._adaptive_implicit_renderer(f, x_min, xm, y_min, ym, depth + 1, max_depth)
            segs += self._adaptive_implicit_renderer(f, xm, x_max, y_min, ym, depth + 1, max_depth)
            segs += self._adaptive_implicit_renderer(f, x_min, xm, ym, y_max, depth + 1, max_depth)
            segs += self._adaptive_implicit_renderer(f, xm, x_max, ym, y_max, depth + 1, max_depth)
            return segs

    def _marching_squares(self, f, x_min, x_max, y_min, y_max, threshold=0.0, resolution=100):
        dx = (x_max - x_min) / resolution
        dy = (y_max - y_min) / resolution
        grid = []
        for j in range(resolution + 1):
            row = []
            y = y_min + j * dy
            for i in range(resolution + 1):
                x = x_min + i * dx
                try:
                    val = f(x, y)
                except:
                    val = float('inf')
                row.append(val)
            grid.append(row)
        segments = []
        for j in range(resolution):
            for i in range(resolution):
                case = 0
                if grid[j][i] > threshold: case |= 1
                if grid[j][i + 1] > threshold: case |= 2
                if grid[j + 1][i + 1] > threshold: case |= 4
                if grid[j + 1][i] > threshold: case |= 8
                if case == 0 or case == 15: continue
                x0, y0 = x_min + i * dx, y_min + j * dy
                x1, y1 = x0 + dx, y0
                x2, y2 = x1, y0 + dy
                x3, y3 = x0, y2

                def interpolate(p1, p2, v1, v2):
                    if abs(v1 - v2) < 1e-9: return p1
                    t = (threshold - v1) / (v2 - v1)
                    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))

                mid_x01 = interpolate((x0, y0), (x1, y1), grid[j][i], grid[j][i + 1])
                mid_x12 = interpolate((x1, y1), (x2, y2), grid[j][i + 1], grid[j + 1][i + 1])
                mid_x23 = interpolate((x2, y2), (x3, y3), grid[j + 1][i + 1], grid[j + 1][i])
                mid_x30 = interpolate((x3, y3), (x0, y0), grid[j + 1][i], grid[j][i])
                edge_table = {
                    1: [(mid_x30, mid_x01)], 2: [(mid_x01, mid_x12)], 3: [(mid_x30, mid_x12)],
                    4: [(mid_x12, mid_x23)], 5: [(mid_x30, mid_x01), (mid_x12, mid_x23)], 6: [(mid_x01, mid_x23)],
                    7: [(mid_x30, mid_x23)], 8: [(mid_x23, mid_x30)], 9: [(mid_x01, mid_x12), (mid_x23, mid_x30)],
                    10: [(mid_x01, mid_x23)], 11: [(mid_x12, mid_x23)], 12: [(mid_x30, mid_x12)],
                    13: [(mid_x01, mid_x30)], 14: [(mid_x30, mid_x01)], 15: []
                }
                if case in edge_table:
                    for seg in edge_table[case]:
                        segments.append(seg)
        return segments

    def draw_graph(self):
        if not self.graph_expression or not hasattr(self.ui_manager.app, 'camera'):
            self._graph_cache = None
            self._fractal_cache.clear()
            return
        cam = self.ui_manager.app.camera
        screen_w, screen_h = self.ui_manager.app.screen.get_size()
        vp_w, vp_h = cam.get_viewport_size()
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        cam_scale = cam.scaling
        steps_base = max(100, min(2000, int(vp_w * cam_scale)))
        uses_time = any('t' in str(item['compiled'][1]) for item in self.graph_expression if
                        item['compiled'][0] in ('cartesian', 'parametric', 'polar', 'field', 'implicit'))
        has_fractal = any(item['compiled'][0] == 'fractal' for item in self.graph_expression)
        has_animated_fractal = any(item.get('has_time_dependence', False) for item in self.graph_expression)
        if uses_time or has_fractal or has_animated_fractal:
            all_drawables = self._render_graphs(steps_base, cam, screen_w, screen_h)
            self._graph_cache = None
        else:
            cache_key = (
                tuple(
                    (item['compiled'], item['color'][:3], item['width'], item['style'])
                    for item in self.graph_expression
                ),
                round(cam_tx, 1), round(cam_ty, 1),
                round(cam_scale, 3),
                screen_w, screen_h
            )
            if self._graph_cache and self._graph_cache[0] == cache_key:
                all_drawables = self._graph_cache[1]
            else:
                all_drawables = self._render_graphs(steps_base, cam, screen_w, screen_h)
                self._graph_cache = (cache_key, all_drawables)
        for drawable in all_drawables:
            dtype = drawable[0]
            if dtype == 'line':
                _, pts, color, width = drawable
                if len(pts) < 2: continue
                for i in range(1, len(pts)):
                    pygame.draw.line(self.ui_manager.app.screen, color[:3], pts[i - 1], pts[i], width)
            elif dtype == 'point':
                _, pos, color, size = drawable
                pygame.draw.circle(self.ui_manager.app.screen, color[:3], pos, size)
            elif dtype == 'arrow':
                _, start, end, color, width = drawable
                self._draw_arrow(self.ui_manager.app.screen, color[:3], start, end, width)
            elif dtype == 'fractal_surface':
                _, surface, offset = drawable
                self.ui_manager.app.screen.blit(surface, offset)

    def _render_graphs(self, steps_base, cam, screen_w, screen_h):
        vp_w, vp_h = cam.get_viewport_size()
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        math_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
        t_now = pygame.time.get_ticks() / 1000.0
        safe_env = {**math_dict, "t": t_now, "__builtins__": {}}
        all_drawables = []
        for item in self.graph_expression:
            compiled = item['compiled']
            color = item['color']
            width = item['width']
            style = item['style']
            drawables = []
            try:
                graph_type = compiled[0]
                if graph_type == 'cartesian':
                    code, x_range = compiled[1], compiled[2]
                    x_min_def = cam_tx - vp_w / 2
                    x_max_def = cam_tx + vp_w / 2
                    x_min, x_max = x_range if x_range else (x_min_def, x_max_def)
                    steps = steps_base
                    dx = (x_max - x_min) / steps if steps > 0 else 0
                    pts = []
                    for i in range(steps + 1):
                        x = x_min + i * dx
                        try:
                            y = eval(code, safe_env, {"x": x})
                            if not isinstance(y, (int, float)) or not math.isfinite(y):
                                continue
                            scr = cam.world_to_screen((x, y))
                            pts.append(scr)
                        except Exception:
                            continue
                    drawables = [('line', seg, color, width) for seg in self._apply_line_style(pts, style)]
                elif graph_type == 'parametric':
                    code_x, code_y, t_range = compiled[1], compiled[2], compiled[3]
                    t_min_def = cam_tx - vp_w / 2
                    t_max_def = cam_tx + vp_w / 2
                    t_min, t_max = t_range if t_range else (t_min_def, t_max_def)
                    steps = steps_base
                    dt = (t_max - t_min) / steps
                    pts = []
                    for i in range(steps + 1):
                        t_val = t_min + i * dt
                        try:
                            x_val = eval(code_x, safe_env, {"t": t_val})
                            y_val = eval(code_y, safe_env, {"t": t_val})
                            if not (isinstance(x_val, (int, float)) and isinstance(y_val, (int, float))):
                                continue
                            if not (math.isfinite(x_val) and math.isfinite(y_val)):
                                continue
                            scr = cam.world_to_screen((x_val, y_val))
                            pts.append(scr)
                        except Exception:
                            continue
                    drawables = [('line', seg, color, width) for seg in self._apply_line_style(pts, style)]
                elif graph_type == 'polar':
                    code_r, theta_range = compiled[1], compiled[2]
                    theta_min, theta_max = theta_range if theta_range else (0, 2 * math.pi)
                    steps = steps_base
                    dtheta = (theta_max - theta_min) / steps
                    pts = []
                    for i in range(steps + 1):
                        theta = theta_min + i * dtheta
                        try:
                            r_val = eval(code_r, safe_env, {"theta": theta, "θ": theta})
                            if not isinstance(r_val, (int, float)) or not math.isfinite(r_val):
                                continue
                            x_val = r_val * math.cos(theta)
                            y_val = r_val * math.sin(theta)
                            scr = cam.world_to_screen((x_val, y_val))
                            pts.append(scr)
                        except Exception:
                            continue
                    drawables = [('line', seg, color, width) for seg in self._apply_line_style(pts, style)]
                elif graph_type == 'scatter':
                    code_xs, code_ys = compiled[1], compiled[2]
                    try:
                        xs_str = eval(code_xs, {"__builtins__": {}}, {})
                        ys_str = eval(code_ys, {"__builtins__": {}}, {})
                        if not (isinstance(xs_str, str) and isinstance(ys_str, str)):
                            raise ValueError("Scatter inputs must be string representations of lists")
                        xs = ast.literal_eval(xs_str)
                        ys = ast.literal_eval(ys_str)
                        if not (isinstance(xs, (list, tuple)) and isinstance(ys, (list, tuple))):
                            raise ValueError("Scatter requires list/tuple literals")
                        if len(xs) != len(ys):
                            raise ValueError("Scatter sequences must have equal length")
                        for x, y in zip(xs, ys):
                            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))): continue
                            if not (math.isfinite(x) and math.isfinite(y)): continue
                            scr = cam.world_to_screen((x, y))
                            drawables.append(('point', scr, color, max(2, width)))
                    except Exception:
                        pass
                elif graph_type == 'complex':
                    code_f, xr, yr, mode = compiled[1], compiled[2], compiled[3], compiled[4]
                    if mode == 'color':
                        drawables = [('complex_surface', *self._render_complex_color(
                            code_f, xr[0], xr[1], yr[0], yr[1], screen_w, screen_h, cam
                        ))]
                    else:  # mode == 'plane'
                        density = max(5, min(15, int(25 * cam.scaling)))
                        drawables = self._render_complex_plane(code_f, xr, yr, density, color, width, cam)
                elif graph_type == 'field':
                    code_fx, code_fy, xr, yr = compiled[1], compiled[2], compiled[3], compiled[4]
                    density = max(3, min(10, int(20 * cam.scaling)))
                    x_step = (xr[1] - xr[0]) / density
                    y_step = (yr[1] - yr[0]) / density
                    for i in range(density + 1):
                        for j in range(density + 1):
                            x = xr[0] + i * x_step
                            y = yr[0] + j * y_step
                            try:
                                fx = eval(code_fx, safe_env, {"x": x, "y": y, "t": t_now})
                                fy = eval(code_fy, safe_env, {"x": x, "y": y, "t": t_now})
                                if not (isinstance(fx, (int, float)) and isinstance(fy, (int, float))): continue
                                if not (math.isfinite(fx) and math.isfinite(fy)): continue
                                start = cam.world_to_screen((x, y))
                                end = cam.world_to_screen((x + fx * 0.2, y + fy * 0.2))
                                drawables.append(('arrow', start, end, color, width))
                            except Exception:
                                pass
                elif graph_type == 'implicit':
                    code_f, xr, yr = compiled[1], compiled[2], compiled[3]
                    def f_eval(x, y):
                        val = eval(code_f, safe_env, {"x": x, "y": y, "t": t_now})
                        return float(val) if isinstance(val, (int, float)) else float('nan')
                    try:
                        segments_list = self._adaptive_implicit_renderer(f_eval, xr[0], xr[1], yr[0], yr[1])
                        if not segments_list:
                            segments_list = self._marching_squares(f_eval, xr[0], xr[1], yr[0], yr[1], resolution=min(200, int(steps_base/2)))
                        world_segments = []
                        for seg in segments_list:
                            if len(seg) == 2:
                                p1 = cam.world_to_screen(seg[0])
                                p2 = cam.world_to_screen(seg[1])
                                world_segments.append([p1, p2])
                        drawables = [('line', s, color, width) for s in world_segments]
                    except Exception:
                        drawables = []
                elif graph_type == 'fractal':
                    (fractal_name, max_iter, escape_radius, c_param, scale_static, palette_str,
                     scale_expr, c_expr, escape_radius_expr) = compiled[1:10]
                    t_val = t_now
                    scale = scale_static
                    if scale_expr:
                        try:
                            scale = max(1e-6, float(eval(scale_expr, safe_env, {})))
                        except:
                            pass
                    er = escape_radius
                    if escape_radius_expr:
                        try:
                            er = max(1.0, float(eval(escape_radius_expr, safe_env, {})))
                        except:
                            pass
                    c_use = c_param
                    if c_expr:
                        try:
                            c_complex = complex(eval(c_expr, safe_env, {}).replace('i', 'j'))
                            c_use = c_complex
                        except:
                            pass
                    base_w, base_h = vp_w, vp_h
                    scaled_w = base_w * scale
                    scaled_h = base_h * scale
                    x_min, x_max = cam_tx - scaled_w / 2, cam_tx + scaled_w / 2
                    y_min, y_max = cam_ty - scaled_h / 2, cam_ty + scaled_h / 2
                    c_key = (float(c_use.real), float(c_use.imag)) if c_use is not None else None
                    palette_obj = _parse_palette(palette_str)
                    drawables = [('fractal_surface', *self._render_fractal(
                        fractal_name, x_min, x_max, y_min, y_max, screen_w, screen_h,
                        max_iter, er, c_use, palette_obj
                    ))]
                elif graph_type == 'fractal_rule':
                    transforms, depth = compiled[1], compiled[2]
                    init_pts = np.array([[0.0, 0.0]], dtype=np.float64)
                    pts = _apply_transforms(init_pts, transforms, depth)
                    drawables = []
                    for i in range(pts.shape[0]):
                        x, y = pts[i, 0], pts[i, 1]
                        scr = cam.world_to_screen((x, y))
                        drawables.append(('point', scr, color, max(1, width // 2)))
            except Exception:
                drawables = []
            all_drawables.extend(drawables)
        return all_drawables

    def _render_complex_plane(self, code_obj, xr, yr, density, color, width, cam):
        x_min, x_max = xr
        y_min, y_max = yr
        dx = (x_max - x_min) / density
        dy = (y_max - y_min) / density
        t_now = pygame.time.get_ticks() / 1000.0
        math_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
        base_env = {"t": t_now, "__builtins__": {}, **math_dict}
        drawables = []
        for i in range(density + 1):
            for j in range(density + 1):
                x = x_min + i * dx
                y = y_min + j * dy
                z = complex(x, y)
                try:
                    env = {"z": z, "x": x, "y": y, **base_env}
                    f_val = eval(code_obj, {"__builtins__": {}}, env)
                    if isinstance(f_val, complex):
                        w = f_val
                    elif isinstance(f_val, (int, float)):
                        w = complex(f_val, 0)
                    else:
                        continue
                    if not (math.isfinite(w.real) and math.isfinite(w.imag)):
                        continue
                    start = cam.world_to_screen((x, y))
                    end = cam.world_to_screen((w.real, w.imag))
                    drawables.append(('arrow', start, end, color, width))
                except Exception:
                    continue
        return drawables

    def _render_complex_color(self, code_obj, x_min, x_max, y_min, y_max, w, h, cam):
        if w <= 0 or h <= 0:
            empty_surf = pygame.Surface((1, 1))
            return empty_surf, (0, 0)
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        t_now = pygame.time.get_ticks() / 1000.0
        math_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
        base_env = {"t": t_now, "__builtins__": {}, **math_dict}
        for j in range(h):
            y = y_max - (j / h) * (y_max - y_min)
            for i in range(w):
                x = x_min + (i / w) * (x_max - x_min)
                z = complex(x, y)
                try:
                    env = {"z": z, "x": x, "y": y, **base_env}
                    f_val = eval(code_obj, {"__builtins__": {}}, env)
                    if isinstance(f_val, complex):
                        w_val = f_val
                    elif isinstance(f_val, (int, float)):
                        w_val = complex(f_val, 0)
                    else:
                        w_val = complex(0, 0)
                    if not (math.isfinite(w_val.real) and math.isfinite(w_val.imag)):
                        hue, val = 0.0, 0.0
                    else:
                        arg = math.atan2(w_val.imag, w_val.real)
                        hue = (arg + math.pi) / (2 * math.pi)
                        mag = abs(w_val)
                        val = min(1.0, math.log1p(mag) / 5.0)
                    r, g, b = self._hsv_to_rgb(hue, 1.0, val)
                    arr[j, i] = (int(r * 255), int(g * 255), int(b * 255))
                except Exception:
                    arr[j, i] = (0, 0, 0)
        surface = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
        offset_x = cam.world_to_screen((x_min, 0))[0]
        offset_y = cam.world_to_screen((0, y_max))[1]
        return surface, (offset_x, offset_y)

    def _hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            return v, v, v
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i %= 6
        if i == 0: return v, t, p
        if i == 1: return q, v, p
        if i == 2: return p, v, t
        if i == 3: return p, q, v
        if i == 4: return t, p, v
        if i == 5: return v, p, q
    def _render_fractal(self, name, x_min, x_max, y_min, y_max, w, h, max_iter, escape_radius, c_param, palette_obj):
        if w <= 0 or h <= 0:
            empty_surf = pygame.Surface((1, 1))
            return empty_surf, (0, 0)
        arr = np.zeros((h, w, 3), dtype=np.uint8, order='C')
        esc_sq = np_f(escape_radius * escape_radius)
        fractal_type = 0 if name == 'mandelbrot' else 1
        c_real = np_f(c_param.real) if c_param else np_f(0.0)
        c_imag = np_f(c_param.imag) if c_param else np_f(0.0)
        if palette_obj is None:
            default_len = min(max_iter, 256)
            r_vals = np.array([min(255, int(95 + 160 * i / default_len)) for i in range(default_len)], dtype=np.uint8)
            g_vals = np.array([min(255, int(20 + 100 * i / default_len)) for i in range(default_len)], dtype=np.uint8)
            b_vals = np.array([min(255, int(150 * (1.0 - i / default_len))) for i in range(default_len)], dtype=np.uint8)
        else:
            pal_len = len(palette_obj)
            r_vals = np.array([c[0] for c in palette_obj], dtype=np.uint8)
            g_vals = np.array([c[1] for c in palette_obj], dtype=np.uint8)
            b_vals = np.array([c[2] for c in palette_obj], dtype=np.uint8)
        try:
            _taichi_compute_fractal(
                arr,
                np_f(x_min), np_f(x_max),
                np_f(y_min), np_f(y_max),
                int(w), int(h),
                int(max_iter), esc_sq,
                int(fractal_type),
                c_real, c_imag,
                r_vals, g_vals, b_vals,
                len(r_vals)
            )
        except Exception as e:
            print(f"Taichi fractal error: {e}")
            arr.fill(0)
        surface = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
        return surface, (0, 0)

    def _apply_line_style(self, points, style):
        if style == 'solid' or len(points) < 2:
            return [points]
        step = 4 if style == 'dotted' else 8
        segments = []
        current = []
        for i, p in enumerate(points):
            current.append(p)
            if i % step == step - 1:
                segments.append(current)
                current = []
        if current:
            segments.append(current)
        return segments