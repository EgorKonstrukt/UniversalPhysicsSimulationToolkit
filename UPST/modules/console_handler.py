import math
import pygame
import subprocess
import sys
from types import SimpleNamespace

from UPST.config import config
from UPST.modules.graph_manager import GraphManager


class ConsoleHandler:
    def __init__(self, ui_manager, physics_manager):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.python_process = None
        self.graph_manager = GraphManager(ui_manager)
        self._sandbox = self._build_sandbox()

    def _build_sandbox(self):
        env = {name: getattr(math, name) for name in dir(math) if not name.startswith('_')}
        env.update({
            '__builtins__': {
                'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter', 'float',
                'int', 'len', 'list', 'map', 'max', 'min', 'print', 'range', 'round',
                'set', 'sorted', 'str', 'sum', 'tuple', 'zip'
            }
        })
        return env

    def process_command(self, cmd):
        if cmd == 'help':
            self.ui_manager.console_ui.console_window.add_output_line_to_log(config.app.help_console_text)
        elif cmd == 'clear':
            self.ui_manager.console_ui.console_window.clear_log()
        elif cmd == 'exit':
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif cmd.startswith('exec '):
            self.execute_code(cmd[5:])
        elif cmd.startswith('eval '):
            self.evaluate_code(cmd[5:])
        elif cmd == 'python':
            self.start_python_interpreter()
        elif cmd.startswith('graph '):
            self.graph_manager.handle_graph_command(cmd[6:])
        else:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Unknown command: {cmd}")

    def draw_graph(self):
        self.graph_manager.draw_graph()

    def execute_code(self, code):
        try:
            exec(code, self._sandbox)
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Exec error: {e}")

    def evaluate_code(self, code):
        try:
            res = eval(code, self._sandbox)
            self.ui_manager.console_ui.console_window.add_output_line_to_log(str(res))
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Eval error: {e}")

    def start_python_interpreter(self):
        self.ui_manager.console_ui.console_window.add_output_line_to_log("Starting interactive Python shell...")
        try:
            self.python_process = subprocess.Popen(
                [sys.executable, '-i'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.ui_manager.console_ui.console_window.add_output_line_to_log(
                "Python interpreter started (external process)."
            )
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Failed to start Python interpreter: {e}")