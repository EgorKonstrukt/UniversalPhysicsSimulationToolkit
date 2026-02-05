import pygame
import pymunk

import pygame_gui
from UPST.debug.debug_manager import Debug
from UPST.gui.windows.properties_window import PropertiesWindow
from UPST.gui.windows.texture_window import TextureWindow
from UPST.gui.windows.script_management_window import ScriptManagementWindow
from UPST.gui.windows.context_plotter_window import ContextPlotterWindow
from UPST.modules.undo_redo_manager import get_undo_redo

class ContextMenuHandlers:
    def delete_selected_objects(self):
        for body in list(self.app.physics_manager.selected_bodies):
            self.ui_manager.physics_manager.remove_body(body)
        get_undo_redo().take_snapshot()
        self.app.physics_manager.clear_selection()

    def toggle_freeze_selected(self):
        for body in self.app.physics_manager.selected_bodies:
            if body.velocity.length < 0.1 and abs(body.angular_velocity) < 0.1:
                body.velocity, body.angular_velocity = (100, 0), 1.0
            else:
                body.velocity, body.angular_velocity = (0, 0), 0
        get_undo_redo().take_snapshot()
        self.app.physics_manager.clear_selection()

    def make_static_selected(self):
        for body in self.app.physics_manager.selected_bodies:
            body.body_type = pymunk.Body.STATIC
        get_undo_redo().take_snapshot()
        self.app.physics_manager.clear_selection()

    def make_dynamic_selected(self):
        for body in self.app.physics_manager.selected_bodies:
            body.body_type = pymunk.Body.DYNAMIC
        get_undo_redo().take_snapshot()
        self.app.physics_manager.clear_selection()

    def reset_positions_selected(self):
        for body in self.app.physics_manager.selected_bodies:
            body.position = (0, 0)
            body.velocity = (0, 0)
            body.angular_velocity = 0.0
        get_undo_redo().take_snapshot()
        self.app.physics_manager.clear_selection()

    def open_rename_dialog(self):
        if not self.clicked_object: return
        if hasattr(self, '_rename_win') and self._rename_win.alive():
            self._rename_win.kill()
        current = getattr(self.clicked_object, 'name', '')
        win_w, win_h = 320, 160
        if self.context_menu and self.context_menu.visible:
            menu_rect = self.context_menu.get_abs_rect()
            x, y = menu_rect.right, menu_rect.top
        else:
            scr_w, scr_h = pygame.display.get_surface().get_size()
            x, y = (scr_w - win_w) // 2, (scr_h - win_h) // 2
        max_x, max_y = pygame.display.get_surface().get_size()
        x = min(x, max_x - win_w); y = min(y, max_y - win_h); x = max(x, 0); y = max(y, 0)
        self._rename_win = pygame_gui.elements.UIWindow(rect=pygame.Rect(x, y, win_w, win_h), manager=self.manager, window_display_title="Set Object Name", object_id=pygame_gui.core.ObjectID('#rename_window', '@floating_window'), resizable=False)
        self._rename_win.set_blocking(True)
        self._rename_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(20, 40, 280, 30), manager=self.manager, container=self._rename_win, initial_text=str(current) if current else "")
        self._rename_entry.focus()
        self._rename_ok = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(60, 90, 80, 30), text="OK", manager=self.manager, container=self._rename_win)
        self._rename_cancel = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(180, 90, 80, 30), text="Cancel", manager=self.manager, container=self._rename_win)

    def open_plotter(self):
        plotter_win = ContextPlotterWindow(manager=self.manager, ui_manager=self.ui_manager, position=(100, 100), size=(700, 500), window_title=f"Plotter: {self.clicked_object.__class__.__name__ if self.clicked_object else 'World'}", x_label="X", y_label="Y", tracked_object=self.clicked_object)
        plotter_win.show()

    def center_to_scene(self):
        Debug.log("center_to_scene called!", "ContextMenu")
        if self.ui_manager.camera:
            Debug.log("Calling camera.center_to_scene", "ContextMenu")
            self.ui_manager.camera.center_to_scene()
        else:
            Debug.log("NO CAMERA!", "ContextMenu")

    def center_to_origin(self):
        Debug.log("center_to_origin called!", "ContextMenu")
        if self.ui_manager.camera:
            Debug.log("Calling camera.center_to_origin", "ContextMenu")
            self.ui_manager.camera.center_to_origin()
        else:
            Debug.log("NO CAMERA!", "ContextMenu")

    def set_camera_target(self):
        cam = self.ui_manager.camera
        pos = self.clicked_object.position if hasattr(self.clicked_object, 'position') else None
        if pos:
            cam.set_tracking_target(pos)
            cam.tracking_target = self.clicked_object
            cam.tracking_enabled = True

    def toggle_camera_rotation(self):
        cam = self.ui_manager.camera
        cam.rotate_with_target = not cam.rotate_with_target

    def open_script_management(self):
        if self.script_window and self.script_window.alive(): self.script_window.kill()
        rect = pygame.Rect(100, 100, 400, 300)
        self.script_window = ScriptManagementWindow(rect, self.manager, self.ui_manager.physics_manager.script_manager)

    def edit_script(self):
        if not self.clicked_object or not hasattr(self.clicked_object, '_scripts'): return
        scripts = self.clicked_object._scripts
        if not scripts: return
        script = scripts[0]
        self.ui_manager.show_inline_script_editor(script=script, owner=self.clicked_object)

    def open_properties_window(self):
        if self.properties_window: self.properties_window.kill()
        self.properties_window = PropertiesWindow(manager=self.manager, body=self.clicked_object, on_close_callback=lambda: setattr(self, 'properties_window', None))

    def delete_object(self):
        if self.clicked_object:
            self.ui_manager.physics_manager.remove_body(self.clicked_object)
            get_undo_redo().take_snapshot()

    def duplicate_object(self):
        if not self.clicked_object or not self.clicked_object.shapes: return
        b = self.clicked_object; s = next(iter(b.shapes)); off = pymunk.Vec2d(50, 50); np = b.position + off
        if isinstance(s, pymunk.Circle):
            nb = pymunk.Body(b.mass, b.moment); ns = pymunk.Circle(nb, s.radius, s.offset)
        elif isinstance(s, pymunk.Poly):
            nb = pymunk.Body(b.mass, b.moment); ns = pymunk.Poly(nb, s.get_vertices())
        else: return
        ns.friction, ns.elasticity = s.friction, s.elasticity
        nb.position, nb.velocity, nb.angular_velocity = np, b.velocity, b.angular_velocity
        self.ui_manager.physics_manager.space.add(nb, ns)

    def toggle_freeze_object(self):
        if not self.clicked_object: return
        b = self.clicked_object
        if b.velocity.length < 0.1 and abs(b.angular_velocity) < 0.1:
            b.velocity, b.angular_velocity = (100, 0), 1.0
        else:
            b.velocity, b.angular_velocity = (0, 0), 0

    def open_texture_window(self):
        if self.properties_window: self.properties_window.close()
        self.properties_window = TextureWindow(manager=self.manager, body=self.clicked_object, on_close_callback=lambda: setattr(self, 'properties_window', None))

    def reset_position(self):
        if self.clicked_object:
            self.clicked_object.position, self.clicked_object.velocity = (0, 0), (0, 0)
            get_undo_redo().take_snapshot()

    def reset_rotation(self):
        if self.clicked_object:
            self.clicked_object.angle, self.clicked_object.angular_velocity = 0, 0
            get_undo_redo().take_snapshot()

    def make_static(self):
        if self.clicked_object:
            self.clicked_object.body_type = pymunk.Body.STATIC
            get_undo_redo().take_snapshot()

    def make_dynamic(self):
        if self.clicked_object:
            self.clicked_object.body_type = pymunk.Body.DYNAMIC
            get_undo_redo().take_snapshot()

    def select_for_debug(self):
        if self.clicked_object and self.ui_manager.physics_debug_manager:
            self.ui_manager.physics_debug_manager.selected_body = self.clicked_object

