import math
import pygame
import ast
import re
import numpy as np
from UPST.modules.profiler import profile, start_profiling, stop_profiling

import numba as nb


@nb.jit(nopython=True, fastmath=True, parallel=False)
def _apply_transforms(points, transforms, depth):
    current = points.copy()
    for _ in range(depth):
        n_pts = current.shape[0]
        n_t = transforms.shape[0]
        total_new = n_pts * n_t
        if total_new == 0:
            break
        new_points = np.empty((total_new, 2), dtype=np.float64)
        idx = 0
        for i in range(n_pts):
            x, y = current[i, 0], current[i, 1]
            for t in range(n_t):
                a, b, c, d, e, f = transforms[t]
                nx = a * x + b * y + e
                ny = c * x + d * y + f
                new_points[idx, 0] = nx
                new_points[idx, 1] = ny
                idx += 1
        current = new_points
    return current

def _get_preset_rules(name):
    if name == 'sierpinski_triangle':
        return np.array([
            [0.5, 0.0, 0.0, 0.5, 0.0, 0.0],
            [0.5, 0.0, 0.0, 0.5, 0.5, 0.0],
            [0.5, 0.0, 0.0, 0.5, 0.25, 0.5]
        ], dtype=np.float64)
    elif name == 'sierpinski_carpet':
        s = 1/3
        offsets = [(i*s, j*s) for i in range(3) for j in range(3) if not (i == 1 and j == 1)]
        rules = []
        for ox, oy in offsets:
            rules.append([s, 0.0, 0.0, s, ox, oy])
        return np.array(rules, dtype=np.float64)
    elif name == 'koch_snowflake':  # IFS approximation
        angle = np.pi / 3
        c, s = np.cos(angle), np.sin(angle)
        scale = 1/3
        return np.array([
            [scale, 0, 0, scale, 0, 0],
            [scale*c, -scale*s, scale*s, scale*c, scale, 0],
            [scale*c, scale*s, -scale*s, scale*c, 0.5, scale*np.sqrt(3)/2],
            [scale, 0, 0, scale, 2*scale, 0]
        ], dtype=np.float64)
    else:
        raise ValueError(f"Unknown preset: {name}")

@nb.jit(nopython=True, fastmath=True, parallel=True, nogil=True)
def _compute_fractal(arr, x_min, x_max, y_min, y_max, w, h, max_iter, esc_sq, fractal_type, c_real=0.0, c_imag=0.0):
    dx = (x_max - x_min) / w
    dy = (y_max - y_min) / h
    palette = np.empty((max_iter + 1, 3), dtype=np.uint8)
    for i in range(max_iter):
        t = i / max_iter
        palette[i, 0] = np.uint8(95 + 160 * t)
        palette[i, 1] = np.uint8(20 + 100 * t)
        palette[i, 2] = np.uint8(150 * (1 - t))
    palette[max_iter, :] = 0  # inside set

    for py in nb.prange(h):
        y = y_max - py * dy
        for px in range(w):
            x = x_min + px * dx
            zx = zy = 0.0
            cx = x if fractal_type == 0 else c_real
            cy = y if fractal_type == 0 else c_imag
            if fractal_type != 0:
                zx, zy = x, y
            escaped = max_iter
            for i in range(max_iter):
                zx2 = zx * zx
                zy2 = zy * zy
                if zx2 + zy2 > esc_sq:
                    escaped = i
                    break
                zy = 2 * zx * zy + cy
                zx = zx2 - zy2 + cx
            col = palette[escaped]
            arr[py, px, 0] = col[0]
            arr[py, px, 1] = col[1]
            arr[py, px, 2] = col[2]

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
            current = {'expr': '', 'color': (0, 200, 255, 200), 'width': 1, 'style': 'solid', 'x_range': None,
                       'y_range': None, 't_range': None, 'theta_range': None, 'plot_type': 'auto',
                       'max_iter': 100, 'escape_radius': 2.0, 'c': None}

            def finalize_plot():
                expr = current['expr']
                if not expr: return
                plot_type = current['plot_type']
                if plot_type == 'auto':
                    if expr.startswith('scatter '):
                        plot_type = 'scatter'
                        expr = expr[8:].strip()
                    elif expr.startswith('field '):
                        plot_type = 'field'
                        expr = expr[6:].strip()
                    elif expr.startswith('implicit '):
                        plot_type = 'implicit'
                        expr = expr[9:].strip()
                    elif expr.startswith('fractal '):
                        plot_type = 'fractal'
                        expr = expr[8:].strip()
                    elif expr.startswith('fractal_rule '):
                        plot_type = 'fractal_rule'
                        expr = expr[13:].strip()
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
                if plot_type == 'cartesian':
                    clean_expr = expr[2:].strip() if expr.startswith('y=') else expr
                    code = compile(clean_expr, '<graph>', 'eval')
                    compiled = ('cartesian', code, current['x_range'])
                elif plot_type == 'parametric':
                    parts = [p.strip() for p in expr.split(',', 1)]
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
                    clean_expr = expr[2:].strip() if expr.startswith(('r=', 'θ=', 'theta=')) else expr
                    code_r = compile(clean_expr, '<graph>', 'eval')
                    compiled = ('polar', code_r, current['theta_range'])
                elif plot_type == 'scatter':
                    parts = [p.strip() for p in expr.split(',', 1)]
                    if len(parts) != 2: raise ValueError("Scatter requires two sequences: xs, ys")
                    compiled = ('scatter', parts[0], parts[1])
                elif plot_type == 'field':
                    parts = [p.strip() for p in expr.split(',', 1)]
                    if len(parts) != 2: raise ValueError("Field requires Fx(x,y), Fy(x,y)")
                    code_fx = compile(parts[0], '<graph>', 'eval')
                    code_fy = compile(parts[1], '<graph>', 'eval')
                    xr = current['x_range'] or (-5.0, 5.0)
                    yr = current['y_range'] or (-5.0, 5.0)
                    compiled = ('field', code_fx, code_fy, xr, yr)
                elif plot_type == 'implicit':
                    code_f = compile(expr, '<graph>', 'eval')
                    xr = current['x_range'] or (-5.0, 5.0)
                    yr = current['y_range'] or (-5.0, 5.0)
                    compiled = ('implicit', code_f, xr, yr)
                elif plot_type == 'fractal':
                    if expr not in ('mandelbrot', 'julia'):
                        raise ValueError("Supported fractals: mandelbrot, julia")
                    c_val = current['c']
                    if expr == 'julia' and c_val is None:
                        raise ValueError("Julia set requires 'c=<complex>' parameter")
                    compiled = ('fractal', expr, current['max_iter'], current['escape_radius'], c_val)
                elif plot_type == 'fractal_rule':
                    rule_str = expr
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
                plots.append({'compiled': compiled, 'color': current['color'], 'width': current['width'],
                              'style': current['style'], 'max_iter': current['max_iter'],
                              'escape_radius': current['escape_radius'], 'c': current['c']})
                current.update({'expr': '', 'x_range': None, 'y_range': None, 't_range': None, 'theta_range': None,
                                'plot_type': 'auto', 'max_iter': 100, 'escape_radius': 2.0, 'c': None})

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
                elif tok.startswith('c='):
                    try:
                        c_str = tok[2:].strip()
                        c_complex = complex(c_str.replace('i', 'j'))
                        current['c'] = c_complex
                    except Exception:
                        pass
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
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph error: {e}")

    def _parse_numeric_expr(self, expr_str):
        if not expr_str:
            return None
        s = expr_str.strip()
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
        except Exception as e:
            raise ValueError(f"Invalid numeric range expression: {expr_str}")

    def _draw_arrow(self, surface, color, start, end, width=1):
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_len = 8
        arrow_angle = math.pi / 6
        left = (end[0] - arrow_len * math.cos(angle - arrow_angle), end[1] - arrow_len * math.sin(angle - arrow_angle))
        right = (end[0] - arrow_len * math.cos(angle + arrow_angle), end[1] - arrow_len * math.sin(angle + arrow_angle))
        pygame.draw.polygon(surface, color, [end, left, right])

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
        uses_time = any('t' in str(item['compiled'][1]) for item in self.graph_expression if item['compiled'][0] in ('cartesian', 'parametric', 'polar', 'field', 'implicit'))
        has_fractal = any(item['compiled'][0] == 'fractal' for item in self.graph_expression)
        if uses_time or has_fractal:
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
                        return eval(code_f, safe_env, {"x": x, "y": y, "t": t_now})
                    segments = self._marching_squares(f_eval, xr[0], xr[1], yr[0], yr[1], threshold=0.0, resolution=40)
                    world_segments = []
                    for (x1, y1), (x2, y2) in segments:
                        p1 = cam.world_to_screen((x1, y1))
                        p2 = cam.world_to_screen((x2, y2))
                        world_segments.append([p1, p2])
                    drawables = [('line', seg, color, width) for seg in world_segments]
                elif graph_type == 'fractal':
                    fractal_name, max_iter, escape_radius, c_param = compiled[1], compiled[2], compiled[3], compiled[4]
                    x_min, x_max = cam_tx - vp_w / 2, cam_tx + vp_w / 2
                    y_min, y_max = cam_ty - vp_h / 2, cam_ty + vp_h / 2
                    c_key = (float(c_param.real), float(c_param.imag)) if c_param is not None else None
                    cache_key = (fractal_name, round(x_min, 12), round(x_max, 12), round(y_min, 12), round(y_max, 12),
                                 screen_w, screen_h, max_iter, round(escape_radius, 6), c_key)
                    if cache_key in self._fractal_cache:
                        surf, offset = self._fractal_cache[cache_key]
                    else:
                        start_profiling("_render_fractal")
                        surf, offset = self._render_fractal(fractal_name, x_min, x_max, y_min, y_max, screen_w, screen_h, max_iter, escape_radius, c_param)
                        self._fractal_cache[cache_key] = (surf, offset)
                        stop_profiling("_render_fractal")
                    drawables = [('fractal_surface', surf, offset)]
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

    def _render_fractal(self, name, x_min, x_max, y_min, y_max, w, h, max_iter, escape_radius, c_param):
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        esc_sq = escape_radius * escape_radius
        fractal_type = 0 if name == 'mandelbrot' else 1
        c_real = c_param.real if c_param else 0.0
        c_imag = c_param.imag if c_param else 0.0
        _compute_fractal(arr, x_min, x_max, y_min, y_max, w, h, max_iter, esc_sq, fractal_type, c_real, c_imag)
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