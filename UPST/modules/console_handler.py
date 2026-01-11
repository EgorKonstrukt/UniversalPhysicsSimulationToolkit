import math
import pygame
from UPST.config import config
import subprocess

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
        else:
            try:
                tokens = [t.strip() for t in subcmd.split(';') if t.strip()]
                plots = []
                current = {
                    'expr': '',
                    'color': (0, 200, 255, 200),
                    'width': 1,
                    'style': 'solid',
                    'x_range': None,
                    't_range': None,
                    'theta_range': None
                }

                def finalize_plot():
                    expr = current['expr']
                    if not expr: return
                    is_parametric = ',' in expr and ('x=' not in expr or 'y=' not in expr)
                    is_polar = any(kw in expr for kw in ('r=', 'θ=', 'theta='))
                    is_cartesian = not is_parametric and not is_polar and ('x' in expr or '=' not in expr)

                    if is_cartesian:
                        if '=' in expr:
                            if not expr.startswith('y='): raise ValueError("Cartesian must be y=...")
                            expr = expr[2:].strip()
                        code = compile(expr, '<graph>', 'eval')
                        compiled = ('cartesian', code, current['x_range'])
                    elif is_parametric:
                        parts = [p.strip() for p in expr.split(',', 1)]
                        if len(parts) != 2: raise ValueError("Parametric: x(t),y(t)")
                        code_x = compile(parts[0], '<graph>', 'eval')
                        code_y = compile(parts[1], '<graph>', 'eval')
                        compiled = ('parametric', code_x, code_y, current['t_range'])
                    elif is_polar:
                        if expr.startswith('r='):
                            expr = expr[2:].strip()
                        code_r = compile(expr, '<graph>', 'eval')
                        compiled = ('polar', code_r, current['theta_range'])
                    else:
                        raise ValueError("Unrecognized graph type")

                    plots.append({
                        'compiled': compiled,
                        'color': current['color'],
                        'width': current['width'],
                        'style': current['style']
                    })
                    current.update({'expr': '', 'x_range': None, 't_range': None, 'theta_range': None})

                i = 0
                while i < len(tokens):
                    tok = tokens[i]
                    if tok.startswith('color:'):
                        col_str = tok[6:].strip()
                        try:
                            if col_str.startswith('#') and len(col_str) == 7:
                                r = int(col_str[1:3], 16)
                                g = int(col_str[3:5], 16)
                                b = int(col_str[5:7], 16)
                                current['color'] = (r, g, b, 200)
                            else:
                                rgb = tuple(int(c.strip()) for c in col_str.split(','))
                                if len(rgb) == 3:
                                    current['color'] = (*rgb, 200)
                        except Exception:
                            pass
                    elif tok.startswith('width:'):
                        try:
                            w = int(tok[6:].strip())
                            current['width'] = max(1, min(5, w))
                        except Exception:
                            pass
                    elif tok.startswith('style:'):
                        style = tok[6:].strip()
                        if style in ('solid', 'dashed', 'dotted'):
                            current['style'] = style
                    elif tok.startswith('x='):
                        rng = tok[2:].strip()
                        if '..' in rng:
                            a, b = map(float, rng.split('..'))
                            current['x_range'] = (a, b)
                    elif tok.startswith('t='):
                        rng = tok[2:].strip()
                        if '..' in rng:
                            a, b = map(float, rng.split('..'))
                            current['t_range'] = (a, b)
                    elif tok.startswith('θ=') or tok.startswith('theta='):
                        key = 'θ' if tok.startswith('θ=') else 'theta'
                        rng = tok[len(key)+1:].strip()
                        if '..' in rng:
                            a, b = map(float, rng.split('..'))
                            current['theta_range'] = (a, b)
                    else:
                        if current['expr']:
                            finalize_plot()
                        current['expr'] = tok
                    i += 1

                if current['expr']:
                    finalize_plot()

                if not plots:
                    raise ValueError("No valid plot")
                self.graph_expression = plots
                self._graph_cache = None
                self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph set: {subcmd}")
            except Exception as e:
                self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph error: {e}")

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
            all_segments = self._graph_cache[1]
        else:
            all_segments = []
            math_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
            safe_env = {**math_dict, "__builtins__": {}}
            for item in self.graph_expression:
                compiled = item['compiled']
                color = item['color']
                width = item['width']
                style = item['style']
                segments = []
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
                        segments = self._apply_line_style(pts, style)
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
                        segments = self._apply_line_style(pts, style)
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
                        segments = self._apply_line_style(pts, style)
                except Exception:
                    segments = []
                all_segments.append((segments, color, width))
            self._graph_cache = (cache_key, all_segments)
        for segments, color, width in all_segments:
            for seg in segments:
                if len(seg) < 2: continue
                for i in range(1, len(seg)):
                    pygame.draw.line(self.ui_manager.app.screen, color[:3], seg[i - 1], seg[i], width)

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