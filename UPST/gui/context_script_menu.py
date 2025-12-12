import pygame
from pygame_gui.elements import UIWindow, UIButton

from UPST.scripting.script_instance import ScriptInstance


class ContextScriptMenu(UIWindow):
    _active_instance = None

    def __init__(self, rect, manager, script: ScriptInstance, parent_window):
        if ContextScriptMenu._active_instance:
            ContextScriptMenu._active_instance.kill()
        ContextScriptMenu._active_instance = self
        safe_rect = manager.get_root_container().rect
        rect = pygame.Rect(rect.topleft, (200, 180))
        rect.clamp_ip(safe_rect)
        super().__init__(rect, manager, window_display_title="", object_id="#context_script_menu", always_on_top=True)
        self.script = script
        self.parent = parent_window
        self.manager = manager
        y, h, gap = 10, 30, 5
        actions = [("Edit", self.edit), ("Delete", self.delete), ("Duplicate", self.duplicate),
                   ("Pause/Resume", self.toggle), ("Reload", self.reload)]
        for i, (lbl, fn) in enumerate(actions):
            btn = UIButton(pygame.Rect(5, y + (h + gap) * i, 190, h), lbl, manager, container=self)
            btn.rebuild_from_changed_theme_data = lambda: None
            btn.callback = fn

    def edit(self):
        self._finalize()
        self.parent.show_edit_box(self.script)

    def delete(self):
        self.script.stop()
        self.parent.script_manager.remove_script(self.script)
        self._finalize()
        self.parent.refresh_list()

    def duplicate(self):
        sm = self.parent.script_manager
        new_name = f"{self.script.name}_copy"
        s = sm.add_script_to(self.script.owner, self.script.code, new_name, self.script.threaded, False)
        s.start()
        self._finalize()
        self.parent.refresh_list()

    def toggle(self):
        self.script.pause() if self.script.running else self.script.start()
        self._finalize()
        self.parent.refresh_list()

    def reload(self):
        if getattr(self.script, 'filepath', None):
            self.script.reload_from_file()
        else:
            self.script.recompile()
        self._finalize()
        self.parent.refresh_list()

    def _finalize(self):
        ContextScriptMenu._active_instance = None
        self.kill()

    def check_clicked_inside(self, pos):
        return self.rect.collidepoint(pos) or any(child.rect.collidepoint(pos) for child in self.get_container().elements)

    def process_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.check_clicked_inside(event.pos):
                self._finalize()
                return None
        return super().process_event(event)