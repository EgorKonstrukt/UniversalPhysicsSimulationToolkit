from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer
from UPST.scripting.script_manager import ScriptManager

class ScriptWindow(QWidget):
    def __init__(self, script_manager: ScriptManager):
        super().__init__()
        self.script_manager = script_manager
        self.setWindowTitle("Running Scripts")
        self.resize(400, 300)
        layout = QVBoxLayout()
        self.label = QLabel("Active Scripts:")
        self.list_widget = QListWidget()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_list)
        layout.addWidget(self.label)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.refresh_btn)
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_list)
        self.timer.start(1000)
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for s in self.script_manager.get_all_scripts():
            if s.running:
                owner_desc = "World" if s.owner is None else f"Body@{id(s.owner)}"
                self.list_widget.addItem(f"{s.name} ({'Threaded' if s.threaded else 'Main'}) - {owner_desc}")