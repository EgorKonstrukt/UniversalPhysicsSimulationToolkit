import pygame
import pygame_gui
from typing import Dict, Any, Optional, List
import subprocess
import os
import sys


class ScriptUIManager:
    def __init__(self, ui_manager, script_engine, debug_manager):
        self.ui_manager = ui_manager
        self.script_engine = script_engine
        self.debug_manager = debug_manager
        
        self.external_editor_process = None
        self.external_editor_button = None
        
        self.setup_ui()
        
    def setup_ui(self):
        button_rect = pygame.Rect(10, 10, 200, 40)
        self.external_editor_button = pygame_gui.elements.UIButton(
            relative_rect=button_rect,
            text='Open Script Editor',
            manager=self.ui_manager
        )
        
    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.external_editor_button:
                self.launch_external_editor()
                
    def launch_external_editor(self):
        if self.external_editor_process and self.external_editor_process.poll() is None:
            self.debug_manager.log("External script editor is already running", "ScriptUI")
            return
            
        try:
            editor_path = os.path.join(os.path.dirname(__file__), 'external_script_editor.py')
            
            if not os.path.exists(editor_path):
                self.debug_manager.log_error(f"External script editor not found at: {editor_path}", "ScriptUI")
                return
                
            self.external_editor_process = subprocess.Popen([
                sys.executable, editor_path
            ], cwd=os.path.dirname(editor_path))
            
            self.debug_manager.log("External script editor launched successfully", "ScriptUI")
            
        except Exception as e:
            self.debug_manager.log_error(f"Failed to launch external script editor: {e}", "ScriptUI")
            
    def update(self, dt):
        if self.external_editor_process:
            if self.external_editor_process.poll() is not None:
                self.external_editor_process = None
                
    def draw(self, screen):
        pass
        
    def cleanup(self):
        if self.external_editor_process and self.external_editor_process.poll() is None:
            try:
                self.external_editor_process.terminate()
                self.external_editor_process.wait(timeout=5)
            except:
                try:
                    self.external_editor_process.kill()
                except:
                    pass
            self.external_editor_process = None

