import pygame
import pygame_gui
from pygame_gui.elements import (UIWindow, UIButton, UITextEntryLine, UITextBox,
                                 UILabel, UIDropDownMenu, UISelectionList, UIPanel)
from UPST.debug.debug_manager import Debug


class ScriptEditorWindow:
    def __init__(self, manager, script_object_manager, idle_integration):
        self.manager = manager
        self.script_object_manager = script_object_manager
        self.idle_integration = idle_integration
        
        self.window = UIWindow(
            pygame.Rect(100, 100, 800, 600),
            manager=manager,
            window_display_title="Script Editor"
        )
        self.window.hide()
        
        self.current_script = None
        self._create_elements()
        
    def _create_elements(self):
        self.script_dropdown = UIDropDownMenu(
            options_list=['New Script'],
            starting_option='New Script',
            relative_rect=pygame.Rect(10, 10, 200, 30),
            container=self.window,
            manager=self.manager
        )
        
        # Script name input
        UILabel(
            relative_rect=pygame.Rect(220, 10, 80, 30),
            text='Name:',
            container=self.window,
            manager=self.manager
        )
        
        self.name_input = UITextEntryLine(
            relative_rect=pygame.Rect(300, 10, 200, 30),
            container=self.window,
            manager=self.manager
        )
        
        # Auto-run checkbox
        self.autorun_button = UIButton(
            relative_rect=pygame.Rect(510, 10, 100, 30),
            text='Auto-run: OFF',
            container=self.window,
            manager=self.manager
        )
        
        # Code editor (large text box)
        self.code_editor = UITextBox(
            html_text='# Enter your Python code here\n',
            relative_rect=pygame.Rect(10, 50, 580, 400),
            container=self.window,
            manager=self.manager
        )
        
        # Buttons panel
        button_y = 460
        self.save_button = UIButton(
            relative_rect=pygame.Rect(10, button_y, 80, 30),
            text='Save',
            container=self.window,
            manager=self.manager
        )
        
        self.load_button = UIButton(
            relative_rect=pygame.Rect(100, button_y, 80, 30),
            text='Load',
            container=self.window,
            manager=self.manager
        )
        
        self.run_button = UIButton(
            relative_rect=pygame.Rect(190, button_y, 80, 30),
            text='Run',
            container=self.window,
            manager=self.manager
        )
        
        self.run_async_button = UIButton(
            relative_rect=pygame.Rect(280, button_y, 100, 30),
            text='Run Async',
            container=self.window,
            manager=self.manager
        )
        
        self.stop_button = UIButton(
            relative_rect=pygame.Rect(390, button_y, 80, 30),
            text='Stop',
            container=self.window,
            manager=self.manager
        )
        
        self.idle_button = UIButton(
            relative_rect=pygame.Rect(480, button_y, 100, 30),
            text='Open IDLE',
            container=self.window,
            manager=self.manager
        )
        
        # Output panel
        UILabel(
            relative_rect=pygame.Rect(10, 500, 100, 20),
            text='Output:',
            container=self.window,
            manager=self.manager
        )
        
        self.output_box = UITextBox(
            html_text='',
            relative_rect=pygame.Rect(10, 520, 580, 60),
            container=self.window,
            manager=self.manager
        )
        
        # Right panel for script objects
        self.objects_panel = UIPanel(
            relative_rect=pygame.Rect(600, 10, 180, 570),
            container=self.window,
            manager=self.manager
        )
        
        UILabel(
            relative_rect=pygame.Rect(5, 5, 170, 20),
            text='Script Objects:',
            container=self.objects_panel,
            manager=self.manager
        )
        
        self.objects_list = UISelectionList(
            relative_rect=pygame.Rect(5, 30, 170, 300),
            item_list=[],
            container=self.objects_panel,
            manager=self.manager
        )
        
        self.create_object_button = UIButton(
            relative_rect=pygame.Rect(5, 340, 170, 30),
            text='Create Script Object',
            container=self.objects_panel,
            manager=self.manager
        )
        
        self.delete_object_button = UIButton(
            relative_rect=pygame.Rect(5, 380, 170, 30),
            text='Delete Selected',
            container=self.objects_panel,
            manager=self.manager
        )
        
        self.refresh_button = UIButton(
            relative_rect=pygame.Rect(5, 420, 170, 30),
            text='Refresh List',
            container=self.objects_panel,
            manager=self.manager
        )
        
    def show(self):
        self.window.show()
        self.refresh_script_list()
        
    def hide(self):
        self.window.hide()
        
    def is_visible(self):
        return self.window.visible
        
    def refresh_script_list(self):
        script_objects = self.script_object_manager.get_all_script_objects()
        
        options = ['New Script'] + [f"{obj.name} ({obj.id[:8]})" for obj in script_objects]
        self.script_dropdown.options_list = options
        self.script_dropdown.selected_option = options[0]
        
        object_items = [f"{obj.name} ({'Running' if obj.is_running else 'Stopped'})"
                       for obj in script_objects]
        self.objects_list.set_item_list(object_items)
        
    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.save_button:
                self._save_current_script()
            elif event.ui_element == self.load_button:
                self._load_script()
            elif event.ui_element == self.run_button:
                self._run_script(async_execution=False)
            elif event.ui_element == self.run_async_button:
                self._run_script(async_execution=True)
            elif event.ui_element == self.stop_button:
                self._stop_script()
            elif event.ui_element == self.idle_button:
                self._open_idle()
            elif event.ui_element == self.autorun_button:
                self._toggle_autorun()
            elif event.ui_element == self.create_object_button:
                self._create_script_object()
            elif event.ui_element == self.delete_object_button:
                self._delete_selected_object()
            elif event.ui_element == self.refresh_button:
                self.refresh_script_list()
                
        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.script_dropdown:
                self._load_selected_script()
                
        elif event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.objects_list:
                self._select_script_object()
                
    def _save_current_script(self):
        if not self.current_script:
            return
            
        name = self.name_input.get_text()
        code = self.code_editor
        
        if name:
            self.current_script.name = name
        self.current_script.update_code(code)
        
        self.output_box.set_text(f"Script saved: {self.current_script.name}")
        
    def _load_script(self):
        pass
        
    def _run_script(self, async_execution=False):
        if not self.current_script:
            return
            
        code = self.code_editor
        self.current_script.update_code(code)
        
        result = self.current_script.execute(async_execution)
        
        if result['success']:
            output_text = f"Execution {'started' if async_execution else 'completed'}"
            if result.get('output'):
                output_text += f"\nOutput: {result['output']}"
            if result.get('execution_time'):
                output_text += f"\nTime: {result['execution_time']:.4f}s"
        else:
            output_text = f"Error: {result.get('error', 'Unknown error')}"
            
        self.output_box.set_text(output_text)
        
    def _stop_script(self):
        if self.current_script:
            success = self.current_script.stop_execution()
            self.output_box.set_text(f"Script {'stopped' if success else 'not running'}")
            
    def _open_idle(self):
        if self.idle_integration:
            success = self.idle_integration.launch_idle()
            self.output_box.set_text(f"IDLE {'launched' if success else 'failed to launch'}")
            
    def _toggle_autorun(self):
        if self.current_script:
            self.current_script.auto_run = not self.current_script.auto_run
            self.autorun_button.set_text(f"Auto-run: {'ON' if self.current_script.auto_run else 'OFF'}")
            
    def _create_script_object(self):
        name = self.name_input.get_text() or "New Script"
        code = self.code_editor
        
        # Get mouse position for placement
        mouse_pos = pygame.mouse.get_pos()
        world_pos = (mouse_pos[0] - 400, mouse_pos[1] - 300)  # Rough conversion
        
        script_obj = self.script_object_manager.create_script_object(
            position=world_pos,
            name=name,
            code=code,
            auto_run=False
        )
        
        self.current_script = script_obj
        self.refresh_script_list()
        self.output_box.set_text(f"Created script object: {script_obj.name}")
        
    def _delete_selected_object(self):
        selected_items = self.objects_list.get_single_selection()
        if selected_items:
            script_objects = self.script_object_manager.get_all_script_objects()
            if script_objects:
                selected_index = self.objects_list.item_list.index(selected_items)
                if 0 <= selected_index < len(script_objects):
                    script_obj = script_objects[selected_index]
                    self.script_object_manager.remove_script_object(script_obj.id)
                    self.refresh_script_list()
                    self.output_box.set_text(f"Deleted script object: {script_obj.name}")
                    
    def _load_selected_script(self):
        selected = self.script_dropdown.selected_option
        if selected == 'New Script':
            self.current_script = None
            self.name_input.set_text("")
            self.code_editor.set_text("# Enter your Python code here\n")
            self.autorun_button.set_text("Auto-run: OFF")
        else:
            script_id = selected.split('(')[-1].rstrip(')')
            script_objects = self.script_object_manager.get_all_script_objects()
            
            for obj in script_objects:
                if obj.id.startswith(script_id):
                    self.current_script = obj
                    self.name_input.set_text(obj.name)
                    self.code_editor.set_text(obj.code)
                    self.autorun_button.set_text(f"Auto-run: {'ON' if obj.auto_run else 'OFF'}")
                    break

    def _select_script_object(self):
        selected_items = self.objects_list.get_single_selection()
        if not selected_items:
            return

        script_objects = self.script_object_manager.get_all_script_objects()
        for obj in script_objects:
            label = f"{obj.name} ({'Running' if obj.is_running else 'Stopped'})"
            if label == selected_items:
                self.script_object_manager.selected_object = obj
                obj.selected = True
                for other in script_objects:
                    if other != obj:
                        other.selected = False
                break


class ScriptManagerWindow:
    def __init__(self, manager, script_object_manager, idle_integration):
        self.manager = manager
        self.script_object_manager = script_object_manager
        self.idle_integration = idle_integration
        
        self.window = UIWindow(
            pygame.Rect(200, 150, 600, 400),
            manager=manager,
            window_display_title="Script Manager"
        )
        self.window.hide()
        
        self._create_elements()
        
    def _create_elements(self):
        # Running scripts list
        UILabel(
            relative_rect=pygame.Rect(10, 10, 150, 20),
            text='Running Scripts:',
            container=self.window,
            manager=self.manager
        )
        
        self.running_list = UISelectionList(
            relative_rect=pygame.Rect(10, 35, 280, 200),
            item_list=[],
            container=self.window,
            manager=self.manager
        )
        
        # All scripts list
        UILabel(
            relative_rect=pygame.Rect(300, 10, 150, 20),
            text='All Scripts:',
            container=self.window,
            manager=self.manager
        )
        
        self.all_scripts_list = UISelectionList(
            relative_rect=pygame.Rect(300, 35, 280, 200),
            item_list=[],
            container=self.window,
            manager=self.manager
        )
        
        # Control buttons
        button_y = 250
        self.stop_selected_button = UIButton(
            relative_rect=pygame.Rect(10, button_y, 100, 30),
            text='Stop Selected',
            container=self.window,
            manager=self.manager
        )
        
        self.stop_all_button = UIButton(
            relative_rect=pygame.Rect(120, button_y, 100, 30),
            text='Stop All',
            container=self.window,
            manager=self.manager
        )
        
        self.run_selected_button = UIButton(
            relative_rect=pygame.Rect(300, button_y, 100, 30),
            text='Run Selected',
            container=self.window,
            manager=self.manager
        )
        
        self.run_all_auto_button = UIButton(
            relative_rect=pygame.Rect(410, button_y, 120, 30),
            text='Run All Auto',
            container=self.window,
            manager=self.manager
        )
        
        # IDLE controls
        idle_y = 290
        self.idle_status_label = UILabel(
            relative_rect=pygame.Rect(10, idle_y, 200, 20),
            text='IDLE Status: Not Running',
            container=self.window,
            manager=self.manager
        )
        
        self.launch_idle_button = UIButton(
            relative_rect=pygame.Rect(220, idle_y, 100, 30),
            text='Launch IDLE',
            container=self.window,
            manager=self.manager
        )
        
        self.close_idle_button = UIButton(
            relative_rect=pygame.Rect(330, idle_y, 100, 30),
            text='Close IDLE',
            container=self.window,
            manager=self.manager
        )
        
        # Refresh button
        self.refresh_button = UIButton(
            relative_rect=pygame.Rect(450, idle_y, 80, 30),
            text='Refresh',
            container=self.window,
            manager=self.manager
        )
        
    def show(self):
        self.window.show()
        self.refresh_lists()
        
    def hide(self):
        self.window.hide()
        
    def is_visible(self):
        return self.window.visible
        
    def refresh_lists(self):
        script_objects = self.script_object_manager.get_all_script_objects()
        
        running_items = [f"{obj.name} ({obj.id[:8]})"
                        for obj in script_objects if obj.is_running]
        self.running_list.set_item_list(running_items)
        
        all_items = [f"{obj.name} ({'Auto' if obj.auto_run else 'Manual'})"
                    for obj in script_objects]
        self.all_scripts_list.set_item_list(all_items)
        
        if self.idle_integration:
            status = "Running" if self.idle_integration.is_idle_running() else "Not Running"
            self.idle_status_label.set_text(f"IDLE Status: {status}")
            
    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.stop_selected_button:
                self._stop_selected_script()
            elif event.ui_element == self.stop_all_button:
                self._stop_all_scripts()
            elif event.ui_element == self.run_selected_button:
                self._run_selected_script()
            elif event.ui_element == self.run_all_auto_button:
                self._run_all_auto_scripts()
            elif event.ui_element == self.launch_idle_button:
                self._launch_idle()
            elif event.ui_element == self.close_idle_button:
                self._close_idle()
            elif event.ui_element == self.refresh_button:
                self.refresh_lists()
                
    def _stop_selected_script(self):
        selected = self.running_list.get_single_selection()
        if selected:
            script_id = selected.split('(')[-1].rstrip(')')
            script_obj = self.script_object_manager.get_script_object(script_id)
            if script_obj:
                script_obj.stop_execution()
                self.refresh_lists()
                
    def _stop_all_scripts(self):
        for obj in self.script_object_manager.get_all_script_objects():
            if obj.is_running:
                obj.stop_execution()
        self.refresh_lists()
        
    def _run_selected_script(self):
        selected = self.all_scripts_list.get_single_selection()
        if selected:
            script_objects = self.script_object_manager.get_all_script_objects()
            selected_index = self.all_scripts_list.item_list.index(selected)
            if 0 <= selected_index < len(script_objects):
                script_obj = script_objects[selected_index]
                script_obj.execute(async_execution=True)
                self.refresh_lists()
                
    def _run_all_auto_scripts(self):
        self.script_object_manager.execute_all_auto_run()
        self.refresh_lists()
        
    def _launch_idle(self):
        if self.idle_integration:
            self.idle_integration.launch_idle()
            self.refresh_lists()
            
    def _close_idle(self):
        if self.idle_integration:
            self.idle_integration.close_idle()
            self.refresh_lists()


class ScriptUIManager:
    def __init__(self, ui_manager, script_object_manager, idle_integration):
        self.ui_manager = ui_manager
        self.script_object_manager = script_object_manager
        self.idle_integration = idle_integration
        
        self.script_editor = ScriptEditorWindow(
            ui_manager.manager, script_object_manager, idle_integration
        )
        
        self.script_manager = ScriptManagerWindow(
            ui_manager.manager, script_object_manager, idle_integration
        )
        
        self._create_main_buttons()
        
    def _create_main_buttons(self):
        self.script_editor_button = UIButton(
            relative_rect=pygame.Rect(self.ui_manager.screen_width - 135, 210, 125, 40),
            text="Script Editor",
            manager=self.ui_manager.manager
        )
        
        self.script_manager_button = UIButton(
            relative_rect=pygame.Rect(self.ui_manager.screen_width - 135, 260, 125, 40),
            text="Script Manager",
            manager=self.ui_manager.manager
        )
        
    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.script_editor_button:
                if self.script_editor.is_visible():
                    self.script_editor.hide()
                else:
                    self.script_editor.show()
            elif event.ui_element == self.script_manager_button:
                if self.script_manager.is_visible():
                    self.script_manager.hide()
                else:
                    self.script_manager.show()
                    
        self.script_editor.handle_event(event)
        try:
            pass
        except Exception as e:
            print(e)
            Debug.log_exception(f"{e}", category="ScriptSystem")
        self.script_manager.handle_event(event)
        
    def update(self, dt):
        pass
        
    def draw(self, screen):
        pass

