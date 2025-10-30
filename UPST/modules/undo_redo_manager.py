from typing import Optional
from UPST.debug.debug_manager import Debug, get_debug
from UPST.gizmos.gizmos_manager import Gizmos
import pickle
from UPST.config import config
import pygame

debug = get_debug()

_undo_redo_instance: Optional['UndoRedoManager'] = None

def get_undo_redo() -> Optional['UndoRedoManager']:
    return _undo_redo_instance

def set_undo_redo(undo_redo_manager: 'UndoRedoManager'):
    global _undo_redo_instance
    _undo_redo_instance = undo_redo_manager

class UndoRedoManager:
    def __init__(self, snapshot_manager):
        self.snapshot_manager = snapshot_manager
        self.history = []
        self.current_index = -1
        set_undo_redo(self)

    def handle_input(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
                self.undo()
            elif event.key == pygame.K_y and (event.mod & pygame.KMOD_CTRL):
                self.redo()

    def update(self):
        self.draw_snapshots_debug()

    def take_snapshot(self):
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        snapshot = self.snapshot_manager.create_snapshot()
        self.history.append(snapshot)
        self.current_index += 1
        if len(self.history) > config.snapshot.max_snapshots:
            self.history.pop(0)
            self.current_index -= 1
        Debug.log("taking snapshot, index: "+str(self.current_index), category="Snapshot")

    def undo(self):
        if self.current_index > 0:
            self.current_index -= 1
            snapshot = self.history[self.current_index]
            self.snapshot_manager.load_snapshot(snapshot)
            Debug.log("loading snapshot, index: " + str(self.current_index), category="Snapshot")
            return True
        return False

    def redo(self):
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            snapshot = self.history[self.current_index]
            self.snapshot_manager.load_snapshot(snapshot)
            Debug.log("loading snapshot, index: " + str(self.current_index), category="Snapshot")
            return True
        return False

    def draw_snapshots_debug(self):
        if debug.show_snapshots_debug:
            return
        for i, snapshot_bytes in enumerate(self.history):
            snapshot = pickle.loads(snapshot_bytes)
            pos = (config.app.screen_height-500 , 50+ i * 30)
            color = "green" if i == self.current_index else "white"
            Gizmos.draw_circle(pos, radius=8, color=color, filled=True, duration=0.1, world_space=False)
            Gizmos.draw_text(
                (pos[0], pos[1] - 15),
                text=f"{i} | bodies={len(snapshot['bodies'])} | mass≈{sum(b['mass'] for b in snapshot['bodies']):.1f}",
                color="yellow",
                font_size=12,
                duration=0.1,
                world_space=False
            )
