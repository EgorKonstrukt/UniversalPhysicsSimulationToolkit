import sys
import os
import json
import socket
import threading
import time
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QListWidget, 
                             QSplitter, QLabel, QLineEdit, QMessageBox, 
                             QFileDialog, QMenuBar, QAction, QStatusBar,
                             QListWidgetItem, QTabWidget, QPlainTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPalette


class GameCommunicator(QObject):
    message_received = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.connected = False
        self.host = "localhost"
        self.port = 12345
        self.receive_thread = None
        
    def connect_to_game(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.connection_status_changed.emit(True)
            
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"Failed to connect to game: {e}")
            self.connected = False
            self.connection_status_changed.emit(False)
            return False
            
    def disconnect_from_game(self):
        if self.socket:
            self.connected = False
            self.socket.close()
            self.socket = None
            self.connection_status_changed.emit(False)
            
    def send_message(self, message: Dict[str, Any]):
        if not self.connected or not self.socket:
            return False
            
        try:
            json_data = json.dumps(message) + "\n"
            self.socket.send(json_data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Failed to send message: {e}")
            self.disconnect_from_game()
            return False
            
    def _receive_messages(self):
        buffer = ""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            self.message_received.emit(message)
                        except json.JSONDecodeError as e:
                            print(f"Failed to decode message: {e}")
                            
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
                
        self.disconnect_from_game()


class ScriptEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.communicator = GameCommunicator()
        self.current_script_id = None
        self.scripts = {}
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        self.setWindowTitle("External Script Editor")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setup_menu_bar()
        self.setup_central_widget()
        self.setup_status_bar()
        
        self.apply_dark_theme()
        
    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Script', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_script)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open Script', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_script)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save Script', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_script)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        connect_action = QAction('Connect to Game', self)
        connect_action.triggered.connect(self.connect_to_game)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction('Disconnect from Game', self)
        disconnect_action.triggered.connect(self.disconnect_from_game)
        file_menu.addAction(disconnect_action)
        
    def setup_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
        
    def create_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("Scripts:"))
        
        self.script_list = QListWidget()
        self.script_list.itemClicked.connect(self.on_script_selected)
        left_layout.addWidget(self.script_list)
        
        button_layout = QHBoxLayout()
        
        self.new_script_btn = QPushButton("New")
        self.new_script_btn.clicked.connect(self.new_script)
        button_layout.addWidget(self.new_script_btn)
        
        self.delete_script_btn = QPushButton("Delete")
        self.delete_script_btn.clicked.connect(self.delete_script)
        button_layout.addWidget(self.delete_script_btn)
        
        left_layout.addLayout(button_layout)
        
        left_layout.addWidget(QLabel("Connection:"))
        
        connection_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_game)
        connection_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_from_game)
        self.disconnect_btn.setEnabled(False)
        connection_layout.addWidget(self.disconnect_btn)
        
        left_layout.addLayout(connection_layout)
        
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("color: red;")
        left_layout.addWidget(self.connection_status)
        
        return left_widget
        
    def create_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        script_info_layout = QHBoxLayout()
        script_info_layout.addWidget(QLabel("Script Name:"))
        
        self.script_name_edit = QLineEdit()
        self.script_name_edit.textChanged.connect(self.on_script_name_changed)
        script_info_layout.addWidget(self.script_name_edit)
        
        right_layout.addLayout(script_info_layout)
        
        tab_widget = QTabWidget()
        right_layout.addWidget(tab_widget)
        
        editor_tab = QWidget()
        editor_layout = QVBoxLayout(editor_tab)
        
        self.code_editor = QPlainTextEdit()
        self.code_editor.setFont(QFont("Consolas", 12))
        self.code_editor.textChanged.connect(self.on_code_changed)
        editor_layout.addWidget(self.code_editor)
        
        execution_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("Run Script")
        self.run_btn.clicked.connect(self.run_script)
        self.run_btn.setEnabled(False)
        execution_layout.addWidget(self.run_btn)
        
        self.run_async_btn = QPushButton("Run Async")
        self.run_async_btn.clicked.connect(self.run_script_async)
        self.run_async_btn.setEnabled(False)
        execution_layout.addWidget(self.run_async_btn)
        
        self.stop_btn = QPushButton("Stop Script")
        self.stop_btn.clicked.connect(self.stop_script)
        self.stop_btn.setEnabled(False)
        execution_layout.addWidget(self.stop_btn)
        
        editor_layout.addLayout(execution_layout)
        
        tab_widget.addTab(editor_tab, "Editor")
        
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Consolas", 10))
        output_layout.addWidget(self.output_display)
        
        clear_output_btn = QPushButton("Clear Output")
        clear_output_btn.clicked.connect(self.clear_output)
        output_layout.addWidget(clear_output_btn)
        
        tab_widget.addTab(output_tab, "Output")
        
        return right_widget
        
    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def setup_connections(self):
        self.communicator.message_received.connect(self.on_message_received)
        self.communicator.connection_status_changed.connect(self.on_connection_status_changed)
        
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QPlainTextEdit, QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px;
            }
            QLabel {
                color: #ffffff;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QStatusBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
        """)
        
    def new_script(self):
        script_id = f"script_{int(time.time())}"
        script_name = f"New Script {len(self.scripts) + 1}"
        
        self.scripts[script_id] = {
            'id': script_id,
            'name': script_name,
            'code': '# New script\nlog("Hello from external editor!")\n',
            'modified': False
        }
        
        self.update_script_list()
        self.select_script(script_id)
        
    def delete_script(self):
        if not self.current_script_id:
            return
            
        reply = QMessageBox.question(self, 'Delete Script', 
                                   f'Are you sure you want to delete "{self.scripts[self.current_script_id]["name"]}"?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            del self.scripts[self.current_script_id]
            self.current_script_id = None
            self.update_script_list()
            self.clear_editor()
            
    def open_script(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Script", "", "Python Files (*.py);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                    
                script_id = f"script_{int(time.time())}"
                script_name = os.path.basename(file_path)
                
                self.scripts[script_id] = {
                    'id': script_id,
                    'name': script_name,
                    'code': code,
                    'file_path': file_path,
                    'modified': False
                }
                
                self.update_script_list()
                self.select_script(script_id)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
                
    def save_script(self):
        if not self.current_script_id:
            return
            
        script = self.scripts[self.current_script_id]
        
        if 'file_path' in script:
            file_path = script['file_path']
        else:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Script", f"{script['name']}.py", "Python Files (*.py);;All Files (*)")
            if not file_path:
                return
                
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script['code'])
                
            script['file_path'] = file_path
            script['modified'] = False
            self.update_script_list()
            self.status_bar.showMessage(f"Saved: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
            
    def connect_to_game(self):
        if self.communicator.connect_to_game():
            self.status_bar.showMessage("Connected to game")
        else:
            self.status_bar.showMessage("Failed to connect to game")
            
    def disconnect_from_game(self):
        self.communicator.disconnect_from_game()
        self.status_bar.showMessage("Disconnected from game")
        
    def run_script(self):
        if not self.current_script_id or not self.communicator.connected:
            return
            
        script = self.scripts[self.current_script_id]
        message = {
            'type': 'execute_script',
            'script_id': script['id'],
            'code': script['code'],
            'async': False
        }
        
        if self.communicator.send_message(message):
            self.status_bar.showMessage("Script sent for execution")
            self.add_output(f"[SENT] Executing script: {script['name']}")
        else:
            self.status_bar.showMessage("Failed to send script")
            
    def run_script_async(self):
        if not self.current_script_id or not self.communicator.connected:
            return
            
        script = self.scripts[self.current_script_id]
        message = {
            'type': 'execute_script',
            'script_id': script['id'],
            'code': script['code'],
            'async': True
        }
        
        if self.communicator.send_message(message):
            self.status_bar.showMessage("Script sent for async execution")
            self.add_output(f"[SENT] Executing script async: {script['name']}")
        else:
            self.status_bar.showMessage("Failed to send script")
            
    def stop_script(self):
        if not self.current_script_id or not self.communicator.connected:
            return
            
        script = self.scripts[self.current_script_id]
        message = {
            'type': 'stop_script',
            'script_id': script['id']
        }
        
        if self.communicator.send_message(message):
            self.status_bar.showMessage("Stop command sent")
            self.add_output(f"[SENT] Stop script: {script['name']}")
        else:
            self.status_bar.showMessage("Failed to send stop command")
            
    def on_script_selected(self, item):
        script_id = item.data(Qt.UserRole)
        self.select_script(script_id)
        
    def select_script(self, script_id):
        if script_id in self.scripts:
            self.current_script_id = script_id
            script = self.scripts[script_id]
            
            self.script_name_edit.setText(script['name'])
            self.code_editor.setPlainText(script['code'])
            
            self.update_ui_state()
            
    def clear_editor(self):
        self.current_script_id = None
        self.script_name_edit.clear()
        self.code_editor.clear()
        self.update_ui_state()
        
    def update_script_list(self):
        self.script_list.clear()
        
        for script_id, script in self.scripts.items():
            display_name = script['name']
            if script.get('modified', False):
                display_name += " *"
                
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, script_id)
            self.script_list.addItem(item)
            
            if script_id == self.current_script_id:
                self.script_list.setCurrentItem(item)
                
    def update_ui_state(self):
        has_script = self.current_script_id is not None
        is_connected = self.communicator.connected
        
        self.delete_script_btn.setEnabled(has_script)
        self.run_btn.setEnabled(has_script and is_connected)
        self.run_async_btn.setEnabled(has_script and is_connected)
        self.stop_btn.setEnabled(has_script and is_connected)
        
    def on_script_name_changed(self):
        if self.current_script_id:
            new_name = self.script_name_edit.text()
            self.scripts[self.current_script_id]['name'] = new_name
            self.scripts[self.current_script_id]['modified'] = True
            self.update_script_list()
            
    def on_code_changed(self):
        if self.current_script_id:
            new_code = self.code_editor.toPlainText()
            self.scripts[self.current_script_id]['code'] = new_code
            self.scripts[self.current_script_id]['modified'] = True
            self.update_script_list()
            
    def on_connection_status_changed(self, connected):
        if connected:
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("color: green;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
        else:
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("color: red;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            
        self.update_ui_state()
        
    def on_message_received(self, message):
        msg_type = message.get('type', '')
        
        if msg_type == 'script_result':
            self.handle_script_result(message)
        elif msg_type == 'script_output':
            self.handle_script_output(message)
        elif msg_type == 'script_error':
            self.handle_script_error(message)
        elif msg_type == 'debug_log':
            self.handle_debug_log(message)
        else:
            self.add_output(f"[RECEIVED] Unknown message type: {msg_type}")
            
    def handle_script_result(self, message):
        script_id = message.get('script_id', '')
        result = message.get('result', {})
        
        success = result.get('success', False)
        output = result.get('output', '')
        error = result.get('error', '')
        execution_time = result.get('execution_time', 0)
        
        self.add_output(f"[RESULT] Script {script_id}:")
        self.add_output(f"  Success: {success}")
        self.add_output(f"  Execution time: {execution_time:.3f}s")
        
        if output:
            self.add_output(f"  Output: {output}")
            
        if error:
            self.add_output(f"  Error: {error}", color="red")
            
    def handle_script_output(self, message):
        script_id = message.get('script_id', '')
        output = message.get('output', '')
        
        self.add_output(f"[OUTPUT] {script_id}: {output}")
        
    def handle_script_error(self, message):
        script_id = message.get('script_id', '')
        error = message.get('error', '')
        
        self.add_output(f"[ERROR] {script_id}: {error}", color="red")
        
    def handle_debug_log(self, message):
        level = message.get('level', 'INFO')
        category = message.get('category', 'General')
        text = message.get('message', '')
        timestamp = message.get('timestamp', '')
        
        color = "white"
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "yellow"
        elif level == "SUCCESS":
            color = "green"
            
        self.add_output(f"[{timestamp}] [{level}] {category}: {text}", color=color)
        
    def add_output(self, text, color="white"):
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        if color != "white":
            self.output_display.setTextColor(QColor(color))
        else:
            self.output_display.setTextColor(QColor("white"))
            
        cursor.insertText(text + "\n")
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
        
    def clear_output(self):
        self.output_display.clear()
        
    def closeEvent(self, event):
        self.communicator.disconnect_from_game()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    editor = ScriptEditor()
    editor.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

