import os
import sys
import importlib.util
import traceback
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from contextlib import redirect_stdout, redirect_stderr
import io

class GlobalScriptManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.script_executor = ScriptExecutor()
        self.running_scripts = {}
        self.script_queue = []
        self.context_provider = None

    def set_context_provider(self, provider):
        self.context_provider = provider
        self.script_executor.context_provider = provider

    def add_script(self, name, code, auto_start=False):
        self.script_executor.add_script(name, code)
        if auto_start:
            self.start_script(name)

    def start_script(self, name):
        if name not in self.running_scripts:
            self.running_scripts[name] = True
            self.script_queue.append(name)

    def stop_script(self, name):
        self.running_scripts[name] = False
        if name in self.script_queue:
            self.script_queue.remove(name)

    def execute_script(self, name):
        if name in self.script_executor.scripts:
            return self.script_executor.execute_script(name, self.context_provider)
        return None

    def execute_code(self, code, name="inline", context_provider=None):
        if context_provider:
            self.script_executor.context_provider = context_provider
        return self.script_executor.execute_code(code, name)

    def update(self):
        for name in list(self.script_queue):
            if self.running_scripts.get(name, False):
                self.execute_script(name)

    def clear_all(self):
        self.script_queue.clear()
        self.running_scripts.clear()

@dataclass
class ScriptResult:
    success: bool
    output: str
    error: Optional[str]
    execution_time: float


class ScriptExecutor:
    def __init__(self, context_provider: Optional[Callable] = None):
        self.context_provider = context_provider
        self.execution_context = {}
        self.scripts: Dict[str, str] = {}
        self.script_dir = "scripts"
        self._ensure_script_directory()

    def _ensure_script_directory(self):
        os.makedirs(self.script_dir, exist_ok=True)

    def add_script(self, name: str, code: str):
        self.scripts[name] = code
        file_path = os.path.join(self.script_dir, f"{name}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)

    def remove_script(self, name: str):
        if name in self.scripts:
            del self.scripts[name]
        file_path = os.path.join(self.script_dir, f"{name}.py")
        if os.path.exists(file_path):
            os.remove(file_path)

    def load_scripts_from_directory(self):
        self.scripts.clear()
        for filename in os.listdir(self.script_dir):
            if filename.endswith('.py'):
                name = filename[:-3]
                file_path = os.path.join(self.script_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.scripts[name] = f.read()

    def execute_script(self, name: str, context_provider: Optional[Callable] = None) -> ScriptResult:
        if name not in self.scripts:
            return ScriptResult(False, "", f"Script '{name}' not found", 0.0)

        if context_provider:
            self.context_provider = context_provider

        return self.execute_code(self.scripts[name], name)

    def execute_code(self, code: str, script_name: str = "inline_script") -> ScriptResult:
        start_time = __import__('time').time()
        output_buffer = io.StringIO()
        error_msg = None
        success = False

        try:
            if self.context_provider:
                self.execution_context = self.context_provider()

            exec_globals = {
                '__name__': f'__{script_name}__',
                '__file__': f'<{script_name}>',
                **self.execution_context
            }

            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                exec(compile(code, f'<{script_name}>', 'exec'), exec_globals)

            success = True
        except Exception as e:
            error_msg = traceback.format_exc()
            output_buffer.write(f"\nError: {str(e)}\n{error_msg}")

        execution_time = __import__('time').time() - start_time
        return ScriptResult(
            success=success,
            output=output_buffer.getvalue(),
            error=error_msg,
            execution_time=execution_time
        )

    def execute_file(self, file_path: str, context_provider: Optional[Callable] = None) -> ScriptResult:
        if not os.path.exists(file_path):
            return ScriptResult(False, "", f"File '{file_path}' not found", 0.0)

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        if context_provider:
            self.context_provider = context_provider

        return self.execute_code(code, os.path.basename(file_path))