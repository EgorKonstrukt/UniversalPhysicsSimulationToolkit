import math
import pygame
from UPST.config import config
import subprocess
import ast
import re

from UPST.modules.graph_manager import GraphManager


class ConsoleHandler:
    def __init__(self, ui_manager, physics_manager):
        self.ui_manager = ui_manager
        self.physics_manager = physics_manager
        self.python_process = None
        self.output_str = None
        self.data_lock = None
        self.graph_manager = GraphManager(ui_manager)

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
            self.graph_manager.handle_graph_command(command[6:])
        else:
            self.ui_manager.console_ui.console_window.add_output_line_to_log(f"Unknown command: {command}")

    def draw_graph(self):
        self.graph_manager.draw_graph()

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