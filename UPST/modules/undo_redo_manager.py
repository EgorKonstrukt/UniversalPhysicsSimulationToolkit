import pygame
from UPST.debug.debug_manager import Debug, get_debug
from UPST.gizmos.gizmos_manager import Gizmos
import pickle
from UPST.config import config

debug = get_debug()

class UndoRedoManager:
    def __init__(self, snapshot_manager):
        self.snapshot_manager = snapshot_manager
        # self.ui_manager = ui_manager
        self.history = []
        self.current_index = -1

    # def is_mouse_on_ui(self):
    #     return self.ui_manager.manager.get_focus_set()

    def handle_input(self, event: pygame.event.Event):
        # if self.is_mouse_on_ui():
        #     return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
                self.undo()
            elif event.key == pygame.K_y and (event.mod & pygame.KMOD_CTRL):
                self.redo()

            # elif event.key == pygame.K_t:
            #     self.take_snapshot()
            #     print("take_snapshot!")

    def update(self):
        pass
        # self.draw_snapshots_debug()

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
            pos = (config.app.screen_height-300 , 50+ i * 30)
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