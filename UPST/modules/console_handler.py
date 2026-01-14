import math
import pygame
import subprocess
import sys
from typing import Dict, Callable, Any

from UPST.config import config
from UPST.modules.graph_manager import GraphManager


class ConsoleHandler:
    def __init__(self, ui_manager, physics_manager):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.python_process = None
        self.graph_manager = GraphManager(ui_manager)
        self._sandbox = self._build_base_sandbox()
        self._plugin_commands: Dict[str, Callable] = {}
        self._builtin_commands = {
            'help': self._cmd_help,
            'clear': self._cmd_clear,
            'exit': self._cmd_exit,
            'exec': self._cmd_exec,
            'eval': self._cmd_eval,
            'python': self._cmd_python,
            'graph': self._cmd_graph,
        }

    def _build_base_sandbox(self):
        env = {name: getattr(math, name) for name in dir(math) if not name.startswith('_')}
        env.update({
            '__builtins__': {
                'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter', 'float',
                'int', 'len', 'list', 'map', 'max', 'min', 'print', 'range', 'round',
                'set', 'sorted', 'str', 'sum', 'tuple', 'zip'
            }
        })
        return env

    def register_plugin_command(self, name: str, func: Callable):
        self._plugin_commands[name] = func
        self._sandbox[name] = lambda *args, f=func: f(*args)

    def unregister_plugin_command(self, name: str):
        self._plugin_commands.pop(name, None)
        self._sandbox.pop(name, None)

    def process_command(self, cmd: str):
        parts = cmd.split(maxsplit=1)
        base_cmd = parts[0] if parts else ''
        args = parts[1] if len(parts) > 1 else ''

        if base_cmd in self._plugin_commands:
            try:
                self._plugin_commands[base_cmd](args)
            except Exception as e:
                self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Plugin command error: {e}")
            return

        handler = self._builtin_commands.get(base_cmd)
        if handler:
            handler(args)
        else:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Unknown command: {cmd}")

    def _cmd_help(self, _):
        self.ui_manager.console_ui.console_window.add_output_line_to_log(config.app.help_console_text)

    def _cmd_clear(self, _):
        self.ui_manager.console_ui.console_window.clear_log()

    def _cmd_exit(self, _):
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _cmd_exec(self, code: str):
        self.execute_code(code)

    def _cmd_eval(self, code: str):
        self.evaluate_code(code)

    def _cmd_python(self, _):
        self.start_python_interpreter()

    def _cmd_graph(self, expr: str):
        self.graph_manager.handle_graph_command(expr)

    def draw_graph(self):
        self.graph_manager.draw_graph()

    def execute_code(self, code: str):
        try:
            exec(code, self._sandbox)
        except Exception as e:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Exec error: {e}")

    def evaluate_code(self, code: str):
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