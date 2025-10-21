import pygame
import pygame_gui
from typing import List, Callable
from collections import deque
from UPST.debug.debug_manager import DebugManager, LogLevel, LogEntry


class ConsoleGUI:
    def __init__(self, ui_manager: pygame_gui.UIManager, debug_manager: DebugManager, 
                 width: int = 800, height: int = 300):
        self.ui_manager = ui_manager
        self.debug_manager = debug_manager
        self.width = width
        self.height = height
        
        self.visible = False
        self.console_rect = pygame.Rect(0, 0, width, height)
        
        self.command_history: deque = deque(maxlen=100)
        self.history_index = -1
        self.current_command = ""
        
        self.command_handlers: dict = {}
        self.auto_complete_commands: List[str] = []
        
        self.font = pygame.font.SysFont("Consolas", 14)
        self.line_height = 16
        self.max_display_lines = (height - 60) // self.line_height
        
        self.scroll_offset = 0
        self.log_entries_cache: List[LogEntry] = []
        
        self.colors = {
            'background': (0, 0, 0, 200),
            'border': (100, 100, 100),
            'text_normal': (255, 255, 255),
            'text_input': (200, 255, 200),
            'text_error': (255, 100, 100),
            'text_warning': (255, 255, 100),
            'text_success': (100, 255, 100),
            'text_debug': (200, 200, 200),
            'prompt': (100, 200, 255)
        }
        
        self.setup_ui_elements()
        self.setup_default_commands()
        
        # Register as debug listener
        self.debug_manager.add_log_listener(self.on_log_entry)
        
    def setup_ui_elements(self):
        input_rect = pygame.Rect(5, self.height - 30, self.width - 10, 25)
        self.input_line = pygame_gui.elements.UITextEntryLine(
            relative_rect=input_rect,
            manager=self.ui_manager,
            initial_text=""
        )
        self.input_line.hide()
        
    def setup_default_commands(self):
        self.register_command("help", self.cmd_help, "Show available commands")
        self.register_command("clear", self.cmd_clear, "Clear console log")
        self.register_command("debug", self.cmd_debug, "Toggle debug categories")
        self.register_command("filter", self.cmd_filter, "Set log filters")
        self.register_command("save", self.cmd_save, "Save debug info")
        self.register_command("stats", self.cmd_stats, "Show debug statistics")
        self.register_command("exec", self.cmd_exec, "Execute Python code")
        self.register_command("eval", self.cmd_eval, "Evaluate Python expression")
        
    def register_command(self, command: str, handler: Callable, description: str = ""):
        self.command_handlers[command] = {
            'handler': handler,
            'description': description
        }
        self.auto_complete_commands.append(command)
        
    def show(self):
        if not self.visible:
            self.visible = True
            self.input_line.show()
            self.input_line.focus()
            self.refresh_log_cache()
            self.debug_manager.log(LogLevel.INFO, "Console GUI opened", "Console")
            
    def hide(self):
        if self.visible:
            self.visible = False
            self.input_line.hide()
            self.debug_manager.log(LogLevel.INFO, "Console GUI closed", "Console")
            
    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()
            
    def on_log_entry(self, entry: LogEntry):
        if self.visible:
            self.log_entries_cache.append(entry)
            if len(self.log_entries_cache) > self.max_display_lines * 2:
                self.log_entries_cache = self.log_entries_cache[-self.max_display_lines:]
                
    def refresh_log_cache(self):
        self.log_entries_cache = list(self.debug_manager.log_entries)[-self.max_display_lines * 2:]
        
    def handle_event(self, event):
        if not self.visible:
            return False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                self.execute_command()
                return True
            elif event.key == pygame.K_UP:
                self.navigate_history(-1)
                return True
            elif event.key == pygame.K_DOWN:
                self.navigate_history(1)
                return True
            elif event.key == pygame.K_TAB:
                self.auto_complete()
                return True
            elif event.key == pygame.K_PAGEUP:
                self.scroll_up()
                return True
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_down()
                return True
                
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.input_line:
                self.execute_command()
                return True
                
        return False
        
    def navigate_history(self, direction: int):
        if not self.command_history:
            return
            
        if self.history_index == -1:
            self.current_command = self.input_line.get_text()
            
        self.history_index += direction
        self.history_index = max(-1, min(len(self.command_history) - 1, self.history_index))
        
        if self.history_index == -1:
            self.input_line.set_text(self.current_command)
        else:
            command = list(self.command_history)[-(self.history_index + 1)]
            self.input_line.set_text(command)
            
    def auto_complete(self):
        current_text = self.input_line.get_text().strip()
        if not current_text:
            return
            
        matches = [cmd for cmd in self.auto_complete_commands if cmd.startswith(current_text)]
        if len(matches) == 1:
            self.input_line.set_text(matches[0] + " ")
        elif len(matches) > 1:
            self.debug_manager.log(LogLevel.INFO, f"Possible completions: {', '.join(matches)}", "Console")
            
    def scroll_up(self):
        self.scroll_offset = min(self.scroll_offset + 5, len(self.log_entries_cache) - self.max_display_lines)
        
    def scroll_down(self):
        self.scroll_offset = max(0, self.scroll_offset - 5)
        
    def execute_command(self):
        command_text = self.input_line.get_text().strip()
        if not command_text:
            return
            
        self.input_line.set_text("")
        self.command_history.append(command_text)
        self.history_index = -1
        self.current_command = ""
        
        self.debug_manager.log(LogLevel.INFO, f"> {command_text}", "Console")
        
        parts = command_text.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command in self.command_handlers:
            try:
                self.command_handlers[command]['handler'](args)
            except Exception as e:
                self.debug_manager.log(LogLevel.ERROR, f"Command error: {e}", "Console")
        else:
            self.debug_manager.log(LogLevel.WARNING, f"Unknown command: {command}. Type 'help' for available commands.", "Console")
            
    def cmd_help(self, args):
        self.debug_manager.log(LogLevel.INFO, "=== CONSOLE COMMANDS ===", "Console")
        for cmd, info in self.command_handlers.items():
            desc = info.get('description', 'No description')
            self.debug_manager.log(LogLevel.INFO, f"  {cmd:12} - {desc}", "Console")
        self.debug_manager.log(LogLevel.INFO, "=== NAVIGATION ===", "Console")
        self.debug_manager.log(LogLevel.INFO, "  UP/DOWN      - Command history", "Console")
        self.debug_manager.log(LogLevel.INFO, "  TAB          - Auto-complete", "Console")
        self.debug_manager.log(LogLevel.INFO, "  PAGE UP/DOWN - Scroll log", "Console")
        self.debug_manager.log(LogLevel.INFO, "  ESC          - Close console", "Console")
        
    def cmd_clear(self, args):
        self.debug_manager.clear_logs()
        self.log_entries_cache.clear()
        
    def cmd_debug(self, args):
        if not args:
            categories = list(self.debug_manager.categories.keys())
            self.debug_manager.log(LogLevel.INFO, f"Debug categories: {', '.join(categories)}", "Console")
            return
            
        action = args[0].lower()
        if len(args) < 2:
            self.debug_manager.log(LogLevel.WARNING, "Usage: debug <enable|disable> <category>", "Console")
            return
            
        category = args[1]
        if action == "enable":
            self.debug_manager.enable_category(category)
        elif action == "disable":
            self.debug_manager.disable_category(category)
        else:
            self.debug_manager.log(LogLevel.WARNING, "Use 'enable' or 'disable'", "Console")
            
    def cmd_filter(self, args):
        if not args:
            filters = list(self.debug_manager.log_filters)
            if filters:
                self.debug_manager.log(LogLevel.INFO, f"Active filters: {', '.join(filters)}", "Console")
            else:
                self.debug_manager.log(LogLevel.INFO, "No active filters", "Console")
            return
            
        action = args[0].lower()
        if action == "clear":
            self.debug_manager.clear_log_filters()
            self.debug_manager.log(LogLevel.INFO, "All filters cleared", "Console")
        elif action == "add" and len(args) > 1:
            category = args[1]
            self.debug_manager.add_log_filter(category)
            self.debug_manager.log(LogLevel.INFO, f"Added filter: {category}", "Console")
        elif action == "remove" and len(args) > 1:
            category = args[1]
            self.debug_manager.remove_log_filter(category)
            self.debug_manager.log(LogLevel.INFO, f"Removed filter: {category}", "Console")
        else:
            self.debug_manager.log(LogLevel.WARNING, "Usage: filter <clear|add|remove> [category]", "Console")
            
    def cmd_save(self, args):
        self.debug_manager.save_debug_info()
        
    def cmd_stats(self, args):
        summary = self.debug_manager.get_log_summary()
        self.debug_manager.log(LogLevel.INFO, "=== DEBUG STATISTICS ===", "Console")
        self.debug_manager.log(LogLevel.INFO, f"Total entries: {summary['total_entries']}", "Console")
        self.debug_manager.log(LogLevel.INFO, f"Runtime: {summary['runtime']:.1f}s", "Console")
        self.debug_manager.log(LogLevel.INFO, f"Frame count: {summary['frame_count']}", "Console")
        
        self.debug_manager.log(LogLevel.INFO, "Level counts:", "Console")
        for level, count in summary['level_counts'].items():
            self.debug_manager.log(LogLevel.INFO, f"  {level}: {count}", "Console")
            
        self.debug_manager.log(LogLevel.INFO, "Category counts:", "Console")
        for category, count in sorted(summary['category_counts'].items()):
            self.debug_manager.log(LogLevel.INFO, f"  {category}: {count}", "Console")
            
    def cmd_exec(self, args):
        if not args:
            self.debug_manager.log(LogLevel.WARNING, "Usage: exec <python_code>", "Console")
            return
            
        code = " ".join(args)
        try:
            safe_globals = {
                '__builtins__': {
                    'print': lambda *args: self.debug_manager.log(LogLevel.INFO, " ".join(str(arg) for arg in args), "Exec"),
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                }
            }
            exec(code, safe_globals)
            self.debug_manager.log(LogLevel.SUCCESS, "Code executed successfully", "Console")
        except Exception as e:
            self.debug_manager.log(LogLevel.ERROR, f"Execution error: {e}", "Console")
            
    def cmd_eval(self, args):
        if not args:
            self.debug_manager.log(LogLevel.WARNING, "Usage: eval <python_expression>", "Console")
            return
            
        expression = " ".join(args)
        try:
            safe_globals = {
                '__builtins__': {
                    'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'sum': sum, 'min': min, 'max': max, 'abs': abs, 'round': round,
                }
            }
            result = eval(expression, safe_globals)
            self.debug_manager.log(LogLevel.SUCCESS, f"Result: {result}", "Console")
        except Exception as e:
            self.debug_manager.log(LogLevel.ERROR, f"Evaluation error: {e}", "Console")
            
    def update(self, dt):
        if self.visible:
            if not self.input_line.is_focused:
                self.input_line.focus()
                
    def draw(self, screen: pygame.Surface):
        if not self.visible:
            return
        screen_height = screen.get_height()
        self.console_rect.y = screen_height - self.height
        self.console_rect.width = screen.get_width()
        console_surface = pygame.Surface((self.console_rect.width, self.console_rect.height), pygame.SRCALPHA)
        console_surface.fill(self.colors['background'])
        screen.blit(console_surface, self.console_rect)
        pygame.draw.rect(screen, self.colors['border'], self.console_rect, 2)
        header_text = f"Debug Console - {len(self.log_entries_cache)} entries | F1: Toggle | ESC: Close | TAB: Complete"
        header_surface = self.font.render(header_text, True, self.colors['text_normal'])
        screen.blit(header_surface, (self.console_rect.x + 5, self.console_rect.y + 5))
        log_y = self.console_rect.y + 25
        log_height = self.console_rect.height - 65
        start_index = max(0, len(self.log_entries_cache) - self.max_display_lines - self.scroll_offset)
        end_index = min(len(self.log_entries_cache), start_index + self.max_display_lines)
        for i in range(start_index, end_index):
            if i >= len(self.log_entries_cache):
                break
            entry = self.log_entries_cache[i]
            y_pos = log_y + (i - start_index) * self.line_height
            
            if y_pos + self.line_height > log_y + log_height:
                break
            if entry.level == LogLevel.ERROR or entry.level == LogLevel.CRITICAL:
                color = self.colors['text_error']
            elif entry.level == LogLevel.WARNING:
                color = self.colors['text_warning']
            elif entry.level == LogLevel.SUCCESS:
                color = self.colors['text_success']
            elif entry.level == LogLevel.DEBUG:
                color = self.colors['text_debug']
            else:
                color = self.colors['text_normal']
            time_str = entry.formatted_time or f"{entry.timestamp:.2f}s"
            category_str = f"[{entry.category[:10]}]"
            level_str = f"[{entry.level.name[:4]}]"
            text = f"{time_str} {level_str} {category_str}: {entry.message}"
            max_chars = (self.console_rect.width - 10) // 8
            if len(text) > max_chars:
                text = text[:max_chars-3] + "..."
            text_surface = self.font.render(text, True, color)
            screen.blit(text_surface, (self.console_rect.x + 5, y_pos))
        prompt_y = self.console_rect.y + self.console_rect.height - 35
        prompt_text = ">"
        prompt_surface = self.font.render(prompt_text, True, self.colors['prompt'])
        screen.blit(prompt_surface, (self.console_rect.x + 5, prompt_y + 5))
        input_rect = pygame.Rect(25, prompt_y, self.console_rect.width - 35, 25)
        self.input_line.relative_rect = input_rect
        
    def cleanup(self):
        if self.debug_manager:
            self.debug_manager.remove_log_listener(self.on_log_entry)
        if self.input_line:
            self.input_line.kill()

