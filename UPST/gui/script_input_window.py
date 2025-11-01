import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UITextBox, UIButton, UILabel
from pygame_gui.windows import UIFileDialog
from UPST.script_system.script_system import GlobalScriptManager
from UPST.script_system.script_context import ScriptContextProvider
import tkinter as tk
from tkinter import filedialog
import os


class ScriptInputWindow:
    def __init__(self, manager, context_provider):
        self.manager = manager
        self.context_provider = context_provider
        self.script_manager = GlobalScriptManager()
        self.window = None
        self.code_textbox = None
        self.execute_button = None
        self.cancel_button = None
        self.file_button = None
        self.status_label = None
        self.result_callback = None
        self.text_entry = None
        self.create_window()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.wm_attributes("-topmost", 1)

    def create_window(self):
        self.window = UIWindow(
            rect=pygame.Rect(100, 100, 600, 500),
            manager=self.manager,
            window_display_title='Python Script Execution',
            object_id=pygame_gui.core.ObjectID(object_id='#script_input_window')
        )

        self.text_entry = pygame_gui.elements.UITextEntryBox(
            relative_rect=pygame.Rect(10, 30, 560, 300),
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(object_id='#script_code_textbox')
        )

        self.execute_button = UIButton(
            relative_rect=pygame.Rect(10, 340, 100, 30),
            text='Execute',
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(object_id='#execute_button')
        )

        self.file_button = UIButton(
            relative_rect=pygame.Rect(120, 340, 120, 30),
            text='Load from File',
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(object_id='#file_button')
        )

        self.cancel_button = UIButton(
            relative_rect=pygame.Rect(250, 340, 100, 30),
            text='Cancel',
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(object_id='#cancel_button')
        )

        self.status_label = UILabel(
            relative_rect=pygame.Rect(10, 380, 560, 80),
            text='Status: Ready',
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(object_id='#status_label')
        )

    def show(self):
        self.window.show()

    def hide(self):
        self.window.hide()

    def process_event(self, event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.execute_button:
                    self._execute_code()
                elif event.ui_element == self.file_button:
                    self._open_file_dialog()
                elif event.ui_element == self.cancel_button:
                    self.hide()
        self.text_entry.process_event(event)

    def _execute_code(self):
        code = self.text_entry.get_text()
        if not code.strip():
            self.status_label.set_text('Status: No code to execute')
            return

        result = self.script_manager.execute_code(
            code,
            context_provider=self.context_provider
        )

        if result.success:
            self.status_label.set_text(f'Status: Execution successful. Time: {result.execution_time:.4f}s')
        else:
            self.status_label.set_text(f'Status: Execution failed. Error: {result.error}')

    def _open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Select Python Script",
            initialdir=".",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            self.text_entry.set_text(code)
            self.status_label.set_text(f'Status: Loaded file: {os.path.basename(file_path)}')
        except Exception as e:
            self.status_label.set_text(f'Status: Error loading file: {str(e)}')