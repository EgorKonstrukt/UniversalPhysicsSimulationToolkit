import math

import pygame
from UPST.config import config
import subprocess


class ConsoleHandler:
    """
    Handles commands entered into the in-game console.
    """

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
            if hasattr(self, 'app') and hasattr(self.app, 'renderer'):
                self._graph_cache = None
            self.ui_manager.console_ui.console_window.add_output_line_to_log("Graph cleared.")
        else:
            try:
                compile(subcmd, '<graph>', 'eval')
                self.graph_expression = subcmd
                if hasattr(self, 'app') and hasattr(self.app, 'renderer'):
                    self._graph_cache = None
                self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph set to: {subcmd}")
            except SyntaxError as e:
                self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Graph syntax error: {e}")

    def execute_code(self, code):
        try:
            exec(code, globals(), locals())
        except Exception as e:
            self.ui_manager.console_window.add_output_line_to_log(f"Error: {e}")

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

    def draw_graph(self):
        if not hasattr(self.ui_manager.app, 'console_handler') or not self.graph_expression:
            self._graph_cache = None
            return
        expr = self.graph_expression
        cam = self.ui_manager.app.camera
        screen_w, screen_h = self.ui_manager.app.screen.get_size()
        vp_w, vp_h = cam.get_viewport_size()
        cam_tx, cam_ty = cam.translation.tx, cam.translation.ty
        cam_scale = cam.scaling

        cache_key = (
            expr,
            int(cam_tx * 10), int(cam_ty * 10),
            int(cam_scale * 1000),
            screen_w, screen_h
        )

        if self._graph_cache and self._graph_cache[0] == cache_key:
            points = self._graph_cache[1]
        else:
            x_min = cam_tx - vp_w / 2
            x_max = cam_tx + vp_w / 2
            y_min = cam_ty - vp_h / 2
            y_max = cam_ty + vp_h / 2
            steps = max(100, min(5000, int(vp_w * cam_scale)))
            dx = (x_max - x_min) / steps if steps > 0 else 0
            points = []
            local_env = {"math": math, "__builtins__": {}}
            try:
                for i in range(steps + 1):
                    x = x_min + i * dx
                    y = eval(expr, local_env, {"x": x})
                    if not isinstance(y, (int, float)) or not math.isfinite(y) or y < y_min or y > y_max:
                        continue
                    scr = cam.world_to_screen((x, y))
                    points.append(scr)  # Храним как float
            except Exception:
                points = []
            self._graph_cache = (cache_key, points)

        if len(points) < 2:
            return
        color = (0, 200, 255, 200)
        for i in range(1, len(points)):
            pygame.draw.aaline(self.ui_manager.app.screen, color, points[i - 1], points[i])