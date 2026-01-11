import math
import pygame
from UPST.config import config
import subprocess
import ast

class ConsoleHandler:
    def __init__(self, ui_manager, physics_manager):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.python_process = None
        self.output_str = None
        self.data_lock = None
        self.graph_expression = None
        self._graph_cache = None

    def process_command(self, command):
        if command == 'help':
            self.ui_manager.console_ui.console_window.add_output_line_to_log(config.app.help_console_text)
        elif command == 'clear':
            self.ui_manager.console_ui.console_window.clear_log()
        elif command == 'exit':
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif command.startswith('exec '):
            self.execute_code(command[5:])
        elif command.startswith('eval '):
            self.evaluate_code(command[5:])
        elif command == 'python':
            self.start_python_interpreter()
        elif command.startswith('graph '):
            self.handle_graph_command(command[6:])
        else:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Unknown command: {command}")

    def handle_graph_command(self, subcmd):
        if subcmd == 'clear':
            self.graph_expression = None
            self._graph_cache = None
            self.ui_manager.console_ui.console_window.add_output_line_to_log("Graph cleared.")
            return
        try:
            tokens = [t.strip() for t in subcmd.split(';') if t.strip()]
            plots = []
            current = {'expr': '', 'color': (0, 200, 255, 200), 'width': 1, 'style': 'solid', 'x_range': None,
                       'y_range': None, 't_range': None, 'theta_range': None, 'plot_type': 'auto'}

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
                    else:
                        is_parametric = ',' in expr and not any(
                            expr.startswith(p) for p in ('x=', 'y=', 'r=', 'θ=', 'theta='))
                        is_polar = any(expr.startswith(p) for p in ('r=', 'θ=', 'theta='))
                        plot_type = 'cartesian' if not is_parametric and not is_polar else (
                            'parametric' if is_parametric else 'polar')
                if plot_type == 'cartesian':
                    clean_expr = expr[2:].strip() if expr.startswith('y=') else expr
                    code = compile(clean_expr, '<graph>', 'eval')
                    compiled = ('cartesian', code, current['x_range'])
                elif plot_type == 'parametric':
                    parts = [p.strip() for p in expr.split(',', 1)]
                    if len(parts) != 2: raise ValueError("Parametric form must be: x(t),y(t)")
                    code_x = compile(parts[0], '<graph>', 'eval')
                    code_y = compile(parts[1], '<graph>', 'eval')
                    compiled = ('parametric', code_x, code_y, current['t_range'])
                elif plot_type == 'polar':
                    clean_expr = expr[2:].strip() if expr.startswith(('r=', 'θ=', 'theta=')) else expr
                    code_r = compile(clean_expr, '<graph>', 'eval')
                    compiled = ('polar', code_r, current['theta_range'])
                elif plot_type == 'scatter':
                    parts = [p.strip() for p in expr.split(',', 1)]
                    if len(parts) != 2: raise ValueError("Scatter requires two sequences: xs, ys")
                    # Store raw strings for literal_eval later
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
                else:
                    raise ValueError(f"Unknown plot type: {plot_type}")
                plots.append({'compiled': compiled, 'color': current['color'], 'width': current['width'],
                              'style': current['style']})
                current.update({'expr': '', 'x_range': None, 'y_range': None, 't_range': None, 'theta_range': None,
                                'plot_type': 'auto'})

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
                elif tok.startswith('x='):
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a, b = map(float, rng.split('..'))
                        current['x_range'] = (a, b)
                elif tok.startswith('y='):
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a, b = map(float, rng.split('..'))
                        current['y_range'] = (a, b)
                elif tok.startswith('t='):
                    rng = tok[2:].strip()
                    if '..' in rng:
                        a, b = map(float, rng.split('..'))
                        current['t_range'] = (a, b)
                elif tok.startswith('θ=') or tok.startswith('theta='):
                    key_len = 2 if tok.startswith('θ=') else 6
                    rng = tok[key_len:].strip()
                    if '..' in rng:
                        a, b = map(float, rng.split('..'))
                        current['theta_range'] = (a, b)
                else:
                    if current['expr']: finalize_plot()
                    current['expr'] = tok
                i += 1
            if current['expr']: finalize_plot()
            if not plots: raise ValueError("No valid expression to plot")
            self.graph_expression = plots
            self._graph_cache = None
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph set with {len(plots)} plot(s).")
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph error: {e}")

    def _draw_arrow(self, surface, color, start, end, width=1):
        import math
        pygame.draw.line(surface, color, start, end, width)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_len = 8
        arrow_angle = math.pi / 6
        left = (end[0] - arrow_len * math.cos(angle - arrow_angle), end[1] - arrow_len * math.sin(angle - arrow_angle))
        right = (end[0] - arrow_len * math.cos(angle + arrow_angle), end[1] - arrow_len * math.sin(angle + arrow_angle))
        pygame.draw.polygon(surface, color, [end, left, right])  # [[1]]

    def _marching_squares(self, f, x_min, x_max, y_min, y_max, threshold=0.0, resolution=50):
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
                x0, y0 = x_min + i * dx, y_min + j * dy
                x1, y1 = x0 + dx, y0
                x2, y2 = x1, y0 + dy
                x3, y3 = x0, y2
                mid_x01 = (x0 + x1) / 2, y0
                mid_x12 = x1, (y0 + y2) / 2
                mid_x23 = (x0 + x1) / 2, y2
                mid_x30 = x0, (y0 + y2) / 2
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
        return segments  # [[8], [14]]

    def draw_graph(self):
        if not self.graph_expression or not hasattr(self.ui_manager.app, 'camera'):
            self._graph_cache = None
            return
        cam = self.ui_manager.app.camera
        screen_w, screen_h = self.ui_manager.app.screen.get_size()
        vp_w, vp_h = cam.get_viewport_size()
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        cam_scale = cam.scaling
        steps_base = max(100, min(2000, int(vp_w * cam_scale)))
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
            all_drawables = []
            math_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
            safe_env = {**math_dict, "__builtins__": {}}
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
                            t = t_min + i * dt
                            try:
                                x_val = eval(code_x, safe_env, {"t": t})
                                y_val = eval(code_y, safe_env, {"t": t})
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
                        density = max(3, min(10, int(20 * cam_scale)))
                        x_step = (xr[1] - xr[0]) / density
                        y_step = (yr[1] - yr[0]) / density
                        for i in range(density + 1):
                            for j in range(density + 1):
                                x = xr[0] + i * x_step
                                y = yr[0] + j * y_step
                                try:
                                    fx = eval(code_fx, safe_env, {"x": x, "y": y})
                                    fy = eval(code_fy, safe_env, {"x": x, "y": y})
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
                            return eval(code_f, safe_env, {"x": x, "y": y})

                        segments = self._marching_squares(f_eval, xr[0], xr[1], yr[0], yr[1], threshold=0.0,
                                                          resolution=40)
                        world_segments = []
                        for (x1, y1), (x2, y2) in segments:
                            p1 = cam.world_to_screen((x1, y1))
                            p2 = cam.world_to_screen((x2, y2))
                            world_segments.append([p1, p2])
                        drawables = [('line', seg, color, width) for seg in world_segments]
                except Exception:
                    drawables = []
                all_drawables.extend(drawables)
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

    def execute_code(self, code):
        try:
            exec(code, globals(), locals())
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Error: {e}")

    def evaluate_code(self, code):
        try:
            result = eval(code, globals(), locals())
            self.ui_manager.console_ui.console_window.add_output_line_to_log(str(result))
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Error: {e}")

    def start_python_interpreter(self):
        self.ui_manager.console_ui.console_window.add_output_line_to_log("Starting interactive Python shell...")
        try:
            self.python_process = subprocess.Popen(['python', '-i'],
                                                   stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.STDOUT, shell=True)
            self.ui_manager.console_ui.console_window.add_output_line_to_log(
                "Python interpreter started (limited functionality in refactor).")
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Failed to start Python interpreter: {e}")