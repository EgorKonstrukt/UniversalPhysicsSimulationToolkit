import pygame
import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UILabel, UIButton, UITextEntryBox, UICheckBox, UITextEntryLine
from pygame_gui.windows import UIMessageWindow
from pygame_gui.core import ObjectID
import tkinter as tk
from tkinter import filedialog
import os
import keyword
import re
import tokenize
import io
from UPST.modules.undo_redo_manager import get_undo_redo
from UPST.utils import safe_filedialog

class ScriptEditorWindow:
    def __init__(self, rect, manager, physics_manager, physics_debug_manager=None, owner=None, script=None, app=None):
        self.app = app
        self.manager = manager
        self.physics_manager = physics_manager
        self.physics_debug_manager = physics_debug_manager
        self.owner = owner
        self.script = script
        self.file_path = None
        self.window = pygame_gui.elements.UIWindow(rect=rect, manager=self.manager, window_display_title=self._get_title(), object_id=ObjectID(class_id='@script_editor_window'), resizable=True, draggable=True)
        self._create_ui()
        self._load_initial_data()
        self.undo_redo = get_undo_redo()
        self._setup_shortcuts()
        self._last_valid_code = self.code_box.get_text()
        self._syntax_colors = {'keyword': (255, 100, 100), 'string': (100, 255, 100), 'comment': (150, 150, 150), 'number': (100, 100, 255), 'default': (220, 220, 220)}
        self._highlight_timer = 0
        self._highlight_delay = 500

    def _get_title(self):
        return "Edit Script" if self.script else f"New Script ({'World' if self.owner is None else 'Object'})"

    def _setup_shortcuts(self):
        self.manager.set_visual_debug_mode(False)

    def _create_ui(self):
        self.layout = {'label_w': 80, 'input_x_offset': 90, 'row_h': 30, 'start_y': 10, 'btn_h': 28, 'code_min_h': 200, 'btn_row_h': 35, 'status_h': 20, 'margin': 10, 'checkbox_h': 20, 'checkbox_label_offset': 25}
        self._update_layout_for_window()
        self._create_elements()

    def _update_layout_for_window(self):
        win_w = self.window.get_container().get_size()[0]
        win_h = self.window.get_container().get_size()[1]
        self.layout['input_w'] = win_w - self.layout['input_x_offset'] - self.layout['margin']
        self.layout['code_h'] = max(self.layout['code_min_h'], win_h - 200)
        self.layout['btn_row_y'] = self.layout['start_y'] + 2 * self.layout['row_h'] + 5 + self.layout['code_h'] + self.layout['checkbox_h'] + 10

    def _create_elements(self):
        self._clear_elements()
        y = self.layout['start_y']
        UILabel(relative_rect=pygame.Rect(self.layout['margin'], y, self.layout['label_w'], 25), text="Target:", manager=self.manager, container=self.window, object_id=ObjectID(class_id='@label'))
        options = ["World"]
        if self.owner is not None: options.append(str(self.owner))
        elif self.physics_debug_manager and self.physics_debug_manager.selected_body: options.append(str(self.physics_debug_manager.selected_body))
        self.target_dropdown = UIDropDownMenu(options_list=options, starting_option=options[0], relative_rect=pygame.Rect(self.layout['input_x_offset'], y, self.layout['input_w'], 25), manager=self.manager, container=self.window, object_id=ObjectID(class_id='@dropdown'))
        y += self.layout['row_h']
        UILabel(relative_rect=pygame.Rect(self.layout['margin'], y, self.layout['label_w'], 25), text="Name:", manager=self.manager, container=self.window, object_id=ObjectID(class_id='@label'))
        self.name_input = UITextEntryLine(relative_rect=pygame.Rect(self.layout['input_x_offset'], y, self.layout['input_w'], 25), manager=self.manager, container=self.window, object_id=ObjectID(class_id='@name_input'))
        y += self.layout['row_h'] + 5
        UILabel(relative_rect=pygame.Rect(self.layout['margin'], y, self.layout['label_w'], 25), text="Code:", manager=self.manager, container=self.window, object_id=ObjectID(class_id='@label'))
        y += 25
        self.code_box = UITextEntryBox(relative_rect=pygame.Rect(self.layout['margin'], y, self.layout['input_w'] + self.layout['input_x_offset'] - self.layout['margin'], self.layout['code_h']), manager=self.manager, container=self.window, object_id=ObjectID(class_id='@script_code_box'))
        y += self.layout['code_h'] + 10
        self.threaded_checkbox = UICheckBox(relative_rect=pygame.Rect(self.layout['margin'], y, self.layout['checkbox_h'], self.layout['checkbox_h']), text="", manager=self.manager, container=self.window, object_id=ObjectID(class_id='@checkbox'))
        UILabel(relative_rect=pygame.Rect(self.layout['margin'] + self.layout['checkbox_label_offset'], y, 200, self.layout['checkbox_h']), text="Run in background thread", manager=self.manager, container=self.window, object_id=ObjectID(class_id='@label'))
        y += self.layout['checkbox_h'] + 5
        btn_defs = [("Load from File", self.load_btn_cb, 0.02, "#load_btn", 0.18), ("Insert Stub", self.insert_stub_cb, 0.22, "#stub_btn", 0.14), ("Save to File", self.save_btn_cb, 0.38, "#save_btn", 0.14), ("Cancel", self.cancel_btn_cb, 0.54, "#cancel_btn", 0.14), ("Apply & Run", self.apply_btn_cb, 0.70, "#apply_script_btn", 0.18)]
        for i, (text, cb, x_norm, obj_id, width_norm) in enumerate(btn_defs):
            x = int(x_norm * (self.layout['input_w'] + self.layout['input_x_offset']))
            width = int(width_norm * (self.layout['input_w'] + self.layout['input_x_offset']))
            btn = UIButton(relative_rect=pygame.Rect(x, y, width, self.layout['btn_h']), text=text, manager=self.manager, container=self.window, object_id=ObjectID(object_id=obj_id))
            setattr(self, f'btn_{i}', btn)
        self.status_label = UILabel(relative_rect=pygame.Rect(self.layout['margin'], y + self.layout['btn_h'] + 5, self.layout['input_w'], self.layout['status_h']), text="Ready", manager=self.manager, container=self.window, object_id=ObjectID(class_id='@status_label'))
        self.code_box.on_text_changed = self._on_text_changed

    def _on_text_changed(self):
        self._highlight_timer = pygame.time.get_ticks()

    def _clear_elements(self):
        elements = ['target_dropdown', 'name_input', 'code_box', 'threaded_checkbox', 'status_label']
        for i in range(5): elements.append(f'btn_{i}')
        for attr in elements:
            if hasattr(self, attr):
                try: getattr(self, attr).kill()
                except: pass

    def _on_resize(self):
        if not self.window:
            return
        container = self.window.get_container()
        new_width, new_height = container.get_size()
        self._update_layout_for_window()
        self._create_elements()

    def on_window_resize(self):
        self._on_resize()

    def load_btn_cb(self):
        self.load_script_from_file()

    def save_btn_cb(self):
        self.save_script_to_file()

    def insert_stub_cb(self):
        current = self.code_box.get_text()
        stub = "\ndef start():\n    # Called when script starts\n    pass\n"
        stub += "def update(dt):\n    # Called every frame with delta time\n    pass\n"
        stub += "def stop():\n    # Called when script stops\n    pass\n"
        if current.strip(): stub = "\n" + stub
        self.code_box.set_text(current + stub)
        self.update_status("Stub inserted")

    def apply_btn_cb(self):
        self.apply_script()

    def cancel_btn_cb(self):
        self.window.kill()

    def _load_initial_data(self):
        if self.script:
            self.name_input.set_text(self.script.name)
            self.code_box.set_text(self.script.code)
            self.threaded_checkbox.set_state(self.script.threaded)
            self.file_path = getattr(self.script, 'file_path', None)
        else:
            self.name_input.set_text("MyScript")
            self.insert_stub_cb()

    def load_script_from_file(self):
        root = tk.Tk()
        root.withdraw()
        path = safe_filedialog(filedialog.askopenfilename(title="Select Python Script",
                                                          filetypes=[("Python files", "*.py"),
                                                                     ("All files", "*.*")]),
                             freeze_watcher=self.app.freeze_watcher)
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f: code = f.read()
            name = os.path.splitext(os.path.basename(path))[0]
            self.name_input.set_text(name)
            self.code_box.set_text(code)
            self.file_path = path
            self.update_status(f"Loaded: {os.path.basename(path)}")
        except Exception as e: self.show_error("Load Error", f"Failed to load script:<br>{str(e)}")

    def save_script_to_file(self):
        init_dir = os.path.dirname(self.file_path) if self.file_path else os.getcwd()
        root = tk.Tk()
        root.withdraw()
        path = filedialog.asksaveasfilename(title="Save Python Script", initialdir=init_dir, initialfile=self.name_input.get_text() or "script.py", defaultextension=".py", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f: f.write(self.code_box.get_text())
            self.file_path = path
            self.update_status(f"Saved: {os.path.basename(path)}")
        except Exception as e: self.show_error("Save Error", f"Failed to save script:<br>{str(e)}")

    def show_error(self, title, msg):
        UIMessageWindow(rect=pygame.Rect(200, 200, 350, 180), manager=self.manager, window_title=title, html_message=msg, object_id=ObjectID(class_id='@error_message'))

    def update_status(self, msg):
        self.status_label.set_text(msg)

    def apply_script(self):
        name = self.name_input.get_text().strip() or "Unnamed"
        code = self.code_box.get_text()
        threaded = self.threaded_checkbox.get_state()
        try: compile(code, f"<script:{name}>", "exec")
        except SyntaxError as se: self.show_error("Syntax Error", f"Line {se.lineno}: {se.msg}"); return
        except Exception as e: self.show_error("Compile Error", f"Compile failed:<br>{str(e)}"); return
        try:
            target = self.target_dropdown.selected_option
            owner = None
            if target != "World": owner = self.owner if self.owner is not None else (self.physics_debug_manager.selected_body if self.physics_debug_manager else None)
            script_manager = self.physics_manager.script_manager
            if self.script:
                was_running = self.script.running
                if was_running: self.script.stop()
                self.script.code = code
                self.script.name = name
                self.script.threaded = threaded
                self.script._recompile(code)
                if was_running: self.script.start()
                self.update_status("Script updated and running")
            else:
                script_manager.add_script_to(owner, code, name, threaded, start_immediately=True)
                self.undo_redo.take_snapshot()
                self.update_status("New script applied and running")
        except Exception as e: self.show_error("Runtime Error", f"Failed to apply script:<br>{str(e)}")

    def _highlight_syntax(self):
        raw_text = self.code_box.get_text()
        if raw_text == self._last_valid_code: return
        try:
            tokens = []
            f = io.StringIO(raw_text)
            for tok in tokenize.generate_tokens(f.readline): tokens.append((tok.type, tok.string, tok.start, tok.end))
            self._last_valid_code = raw_text
        except (tokenize.TokenError, IndentationError, SyntaxError): return
        color_ranges = []
        lines = raw_text.split('\n')
        for tok_type, tok_str, (srow, scol), (erow, ecol) in tokens:
            if srow < 1 or srow > len(lines): continue
            start = sum(len(lines[i]) + 1 for i in range(srow - 1)) + scol
            end = start + len(tok_str)
            color_type = None
            if tok_type == tokenize.NAME and keyword.iskeyword(tok_str): color_type = 'keyword'
            elif tok_type == tokenize.STRING: color_type = 'string'
            elif tok_type == tokenize.NUMBER: color_type = 'number'
            elif tok_type == tokenize.COMMENT: color_type = 'comment'
            if color_type: color_ranges.append((start, end, color_type))
        for start, end, color_type in color_ranges:
            self.code_box.set_text_colour(self._syntax_colors[color_type], (start, end))
        self._last_valid_code = raw_text

    def update(self, time_delta):
        current_time = pygame.time.get_ticks()
        if current_time - self._highlight_timer > self._highlight_delay:
            self._highlight_syntax()
            self._highlight_timer = current_time

    def process_event(self, event):
        handled = False
        if event.type == pygame.WINDOWRESIZED: self._on_resize(); handled = True
        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if event.key == pygame.K_s and mods & pygame.KMOD_CTRL: self.apply_script(); handled = True
            elif event.key == pygame.K_o and mods & pygame.KMOD_CTRL: self.load_btn_cb(); handled = True
            elif event.key == pygame.K_e and mods & pygame.KMOD_CTRL: self.save_btn_cb(); handled = True
            elif event.key == pygame.K_z and mods & pygame.KMOD_CTRL:
                if mods & pygame.KMOD_SHIFT: self.undo_redo.redo()
                else: self.undo_redo.undo()
                handled = True
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            btn_map = {self.btn_0: self.load_btn_cb, self.btn_1: self.insert_stub_cb, self.btn_2: self.save_btn_cb, self.btn_3: self.cancel_btn_cb, self.btn_4: self.apply_btn_cb}
            if event.ui_element in btn_map: btn_map[event.ui_element](); handled = True
        return handled

    def is_alive(self):
        return self.window.alive()