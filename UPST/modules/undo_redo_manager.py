from typing import Optional, Callable, Dict, Any
from UPST.debug.debug_manager import Debug, get_debug
from UPST.gizmos.gizmos_manager import Gizmos
import pickle
from UPST.config import config
import pygame
import json
from datetime import datetime

debug = get_debug()

_undo_redo_instance: Optional['UndoRedoManager'] = None

def get_undo_redo() -> Optional['UndoRedoManager']:
    return _undo_redo_instance

def set_undo_redo(undo_redo_manager: 'UndoRedoManager'):
    global _undo_redo_instance
    _undo_redo_instance = undo_redo_manager

class SnapshotMetadata:
    def __init__(self, index: int, timestamp: datetime, body_count: int, total_mass: float, script_count: int, custom_data: Dict[str, Any] = None):
        self.index = index
        self.timestamp = timestamp
        self.body_count = body_count
        self.total_mass = total_mass
        self.script_count = script_count
        self.custom_data = custom_data or {}

class UndoRedoManager:
    def __init__(self, snapshot_manager, on_state_change: Optional[Callable] = None):
        self.snapshot_manager = snapshot_manager
        self.history = []
        self.metadata_history = []
        self.current_index = -1
        self.max_snapshots = config.snapshot.max_snapshots
        self.on_state_change = on_state_change
        self._batch_operations = 0
        self._batch_snapshot = None
        set_undo_redo(self)

    def handle_input(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            ctrl_held = event.mod & pygame.KMOD_CTRL
            shift_held = event.mod & pygame.KMOD_SHIFT
            if ctrl_held:
                if event.key == pygame.K_z:
                    if shift_held:
                        self.redo()
                    else:
                        self.undo()
                elif event.key == pygame.K_y:
                    self.redo()
                elif event.key == pygame.K_s:
                    self.take_snapshot()

    def update(self):
        self.draw_snapshots_debug()

    def begin_batch_operation(self):
        self._batch_operations += 1
        if self._batch_operations == 1:
            self._batch_snapshot = self.snapshot_manager.create_snapshot()

    def end_batch_operation(self):
        if self._batch_operations > 0:
            self._batch_operations -= 1
            if self._batch_operations == 0 and self._batch_snapshot:
                self.take_snapshot()
                self._batch_snapshot = None

    def take_snapshot(self, custom_metadata: Dict[str, Any] = None):
        if self._batch_operations > 0:
            return
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
            self.metadata_history = self.metadata_history[:self.current_index + 1]

        snapshot = self.snapshot_manager.create_snapshot()

        snapshot_dict = pickle.loads(snapshot)
        snapshot_meta = self._create_metadata_from_dict(snapshot_dict, len(self.history), custom_metadata)

        self.history.append(snapshot)
        self.metadata_history.append(snapshot_meta)
        self.current_index += 1
        if len(self.history) > self.max_snapshots:
            self.history.pop(0)
            self.metadata_history.pop(0)
            self.current_index -= 1
            for i, meta in enumerate(self.metadata_history):
                meta.index = i
        Debug.log(f"taking snapshot, index: {self.current_index}", category="Snapshot")
        if self.on_state_change:
            self.on_state_change(self.current_index, len(self.history))

    def _create_metadata_from_dict(self, snapshot: dict, index: int, custom_data: Dict[str, Any]) -> SnapshotMetadata:
        body_count = len(snapshot.get('bodies', []))
        total_mass = sum(b.get('mass', 0) for b in snapshot.get('bodies', []))

        script_data = snapshot.get('scripts', {})
        if isinstance(script_data, dict):
            script_count = len(script_data.get('object_scripts', [])) + len(script_data.get('world_scripts', []))
        else:
            script_count = 0

        custom_data = custom_data or {}
        custom_data['script_count'] = script_count

        return SnapshotMetadata(index, datetime.now(), body_count, total_mass, script_count, custom_data)

    def undo(self) -> bool:
        if self.current_index > 0:
            self.current_index -= 1
            snapshot = self.history[self.current_index]
            self.snapshot_manager.load_snapshot(snapshot)
            Debug.log(f"loading snapshot, index: {self.current_index}", category="Snapshot")
            if self.on_state_change:
                self.on_state_change(self.current_index, len(self.history))
            return True
        return False

    def redo(self) -> bool:
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            snapshot = self.history[self.current_index]
            self.snapshot_manager.load_snapshot(snapshot)
            Debug.log(f"loading snapshot, index: {self.current_index}", category="Snapshot")
            if self.on_state_change:
                self.on_state_change(self.current_index, len(self.history))
            return True
        return False

    def clear_history(self):
        self.history.clear()
        self.metadata_history.clear()
        self.current_index = -1
        if self.on_state_change:
            self.on_state_change(self.current_index, 0)

    def get_history_size(self) -> int:
        return len(self.history)

    def get_current_index(self) -> int:
        return self.current_index

    def can_undo(self) -> bool:
        return self.current_index > 0

    def can_redo(self) -> bool:
        return self.current_index < len(self.history) - 1

    def get_snapshot_metadata(self, index: int) -> Optional[SnapshotMetadata]:
        if 0 <= index < len(self.metadata_history):
            return self.metadata_history[index]
        return None

    def export_history(self, filepath: str):
        export_data = {
            'history': [pickle.loads(s) for s in self.history],
            'metadata': [{'index': m.index, 'timestamp': m.timestamp.isoformat(), 'body_count': m.body_count, 'total_mass': m.total_mass, 'custom_data': m.custom_data} for m in self.metadata_history],
            'current_index': self.current_index
        }
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

    def import_history(self, filepath: str):
        with open(filepath, 'r') as f:
            import_data = json.load(f)
        self.history = [pickle.dumps(s) for s in import_data['history']]
        self.metadata_history = [
            SnapshotMetadata(
                m['index'],
                datetime.fromisoformat(m['timestamp']),
                m['body_count'],
                m['total_mass'],
                m.get('custom_data', {})
            ) for m in import_data['metadata']
        ]
        self.current_index = import_data['current_index']
        if self.on_state_change:
            self.on_state_change(self.current_index, len(self.history))

    def draw_snapshots_debug(self):
        if not debug.show_snapshots_debug:
            return
        start_idx = max(0, self.current_index - 10)
        end_idx = min(len(self.history), self.current_index + 11)
        for i in range(start_idx, end_idx):
            snapshot_meta = self.metadata_history[i]
            pos = (config.app.screen_width - 200, 50 + (i - start_idx) * 35)
            color = "green" if i == self.current_index else "white"
            Gizmos.draw_circle(pos, radius=8, color=color, filled=True, duration=0.1, world_space=False)
            Gizmos.draw_text(
                (pos[0] + 15, pos[1] - 8),
                text=f"{i} | {snapshot_meta.body_count}b | {snapshot_meta.total_mass:.1f}m",
                color="yellow",
                font_size=10,
                duration=0.1,
                world_space=False
            )
            time_str = snapshot_meta.timestamp.strftime("%H:%M:%S")
            Gizmos.draw_text(
                (pos[0] + 15, pos[1] + 5),
                text=time_str,
                color="gray",
                font_size=8,
                duration=0.1,
                world_space=False
            )