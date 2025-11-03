import pygame
import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UILabel, UIButton, UITextEntryLine, UITextEntryBox, UICheckBox
from pygame_gui.windows import UIMessageWindow
import tkinter as tk
from tkinter import filedialog
from UPST.modules.undo_redo_manager import get_undo_redo

class ScriptEditorWindow:
    def __init__(self, rect, manager, physics_manager, physics_debug_manager=None, owner=None, script=None):
        self.manager = manager
        self.physics_manager = physics_manager
        self.physics_debug_manager = physics_debug_manager
        self.owner = owner
        self.script = script
        self.window = pygame_gui.elements.UIWindow(
            rect=rect,
            manager=self.manager,
            window_display_title=self._get_title()
        )
        self._create_ui()
        self._load_initial_data()
        self.undo_redo = get_undo_redo()

    def _get_title(self):
        if self.script:
            return "Edit Script"
        owner_desc = "World" if self.owner is None else "Object"
        return f"New Script ({owner_desc})"

    def _create_ui(self):
        # Target dropdown
        UILabel(relative_rect=pygame.Rect(10, 10, 80, 25), text="Target:", manager=self.manager, container=self.window)
        options = ["World"]
        if self.owner is not None:
            options.append(str(self.owner))
        elif self.physics_debug_manager and self.physics_debug_manager.selected_body:
            options.append(str(self.physics_debug_manager.selected_body))
        self.target_dropdown = UIDropDownMenu(
            options_list=options,
            starting_option="World" if self.owner is None else str(self.owner),
            relative_rect=pygame.Rect(90, 10, 180, 25),
            manager=self.manager,
            container=self.window
        )

        # Name field
        UILabel(relative_rect=pygame.Rect(10, 40, 100, 25), text="Name:", manager=self.manager, container=self.window)
        self.name_input = UITextEntryLine(
            relative_rect=pygame.Rect(120, 40, 410, 25),
            manager=self.manager,
            container=self.window
        )

        # Code editor
        UILabel(relative_rect=pygame.Rect(10, 70, 100, 25), text="Code:", manager=self.manager, container=self.window)
        self.code_box = UITextEntryBox(
            relative_rect=pygame.Rect(10, 95, 510, 200),
            manager=self.manager,
            container=self.window
        )

        # Threaded checkbox
        self.threaded_checkbox = UICheckBox(
            relative_rect=pygame.Rect(10, 305, 20, 20),
            text="",
            manager=self.manager,
            container=self.window
        )
        UILabel(relative_rect=pygame.Rect(35, 305, 180, 20), text="Run in background thread", manager=self.manager, container=self.window)

        # Buttons
        self.load_btn = UIButton(relative_rect=pygame.Rect(10, 335, 120, 30), text="Load from File", manager=self.manager, container=self.window)
        self.cancel_btn = UIButton(relative_rect=pygame.Rect(300, 335, 110, 30), text="Cancel", manager=self.manager, container=self.window)
        self.apply_btn = UIButton(relative_rect=pygame.Rect(420, 335, 110, 30), text="Apply & Run", manager=self.manager, container=self.window, object_id="#apply_script_btn")

    def _load_initial_data(self):
        if self.script:
            self.name_input.set_text(self.script.name)
            self.code_box.set_text(self.script.code)
            self.threaded_checkbox.set_state(self.script.threaded)
        else:
            self.name_input.set_text("MyScript")
            stub = ("def start():\n    # Called when script starts\n    pass\n"
                    "def update(dt):\n    # Called every frame with delta time\n    pass\n"
                    "def stop():\n    # Called when script stops\n    pass")
            self.code_box.set_text(stub)

    def load_script_from_file(self):
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Select Python Script", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, 'r') as f:
                code = f.read()
            name = path.split('/')[-1].split('\\')[-1].split('.')[0]
            self.name_input.set_text(name)
            self.code_box.set_text(code)
        except Exception as e:
            print(f"Error loading script: {e}")

    def apply_script(self):
        name = self.name_input.get_text().strip() or "Unnamed"
        code = self.code_box.get_text()
        threaded = self.threaded_checkbox.get_state()
        try:
            target = self.target_dropdown.selected_option
            owner = None
            if target != "World":
                if self.owner is not None:
                    owner = self.owner
                elif self.physics_debug_manager and self.physics_debug_manager.selected_body:
                    owner = self.physics_debug_manager.selected_body

            script_manager = self.physics_manager.script_manager
            if self.script:
                script_manager.remove_script(self.script)
            script_manager.add_script_to(owner, code, name, threaded, start_immediately=True)
            self.window.kill()
            self.undo_redo.take_snapshot()
        except Exception as e:
            print(f"Error applying script: {e}")
            UIMessageWindow(
                rect=pygame.Rect(200, 200, 300, 160),
                manager=self.manager,
                window_title="Script Error",
                html_message=f"Failed to apply script:<br>{str(e)}"
            )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.apply_btn:
                self.apply_script()
            elif event.ui_element == self.cancel_btn:
                self.window.kill()
            elif event.ui_element == self.load_btn:
                self.load_script_from_file()
        return False
    def is_alive(self):
        return self.window.alive()
