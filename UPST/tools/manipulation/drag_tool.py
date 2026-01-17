import random
import pygame, math, pymunk
from UPST.config import config
from UPST.tools.base_tool import BaseTool
import pygame_gui
from UPST.config import config

class DragTool(BaseTool):
    name = "Drag"
    icon_path = "sprites/gui/tools/drag.png"
    def __init__(self, pm, app):
        super().__init__(pm, app)
        self.mb = None
        self.tgt = None
        self.pj = None
        self.ds = None
        self.dragging = False
        self.stiff_entry = None
        self.damp_entry = None
        self.rest_entry = None
        self.cb_no_rot = None
        self.cb_center = None
        self.cb_show_force = None
        self.cb_stabilizer = True
        self.last_force = 0.0
        self.saved_moi = None
        self.font = pygame.font.SysFont("Arial", 16)

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, config.app.screen_height-245, 300, 245),
            manager=self.ui_manager.manager,
            window_display_title="Drag Settings"
        )
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 10, 80, 20), text="Stiff:", manager=self.ui_manager.manager, container=win)
        self.stiff_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(95, 10, 80, 20), initial_text="8000", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 40, 80, 20), text="Damp:", manager=self.ui_manager.manager, container=win)
        self.damp_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(95, 40, 80, 20), initial_text="200", manager=self.ui_manager.manager, container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10, 70, 80, 20), text="Rest:", manager=self.ui_manager.manager, container=win)
        self.rest_entry = pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(95, 70, 80, 20), initial_text="0", manager=self.ui_manager.manager, container=win)
        self.cb_no_rot = pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10, 100, 25, 25), text="Отключить вращение", manager=self.ui_manager.manager, container=win)
        self.cb_center = pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10, 125, 25, 25), text="Брать за центр массы", manager=self.ui_manager.manager, container=win)
        self.cb_show_force = pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10, 150, 25, 25), text="Отображать силу", manager=self.ui_manager.manager, container=win)
        self.cb_stabilizer = pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10, 175, 25, 25), text="Стабилизация", manager=self.ui_manager.manager, container=win, initial_state=True)
        self.settings_window = win

    def _make_mouse_body(self, pos):
        b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        b.position = pos
        self.pm.space.add(b)
        return b

    def _start_drag(self, wpos, info):
        self.tgt = info.shape.body
        self.mb = self._make_mouse_body(wpos)
        if self.cb_center.get_state():
            local_anchor = (0, 0)
        else:
            local_anchor = self.tgt.world_to_local(wpos)
        k = float(self.stiff_entry.get_text()) if self.stiff_entry else 8000
        d = float(self.damp_entry.get_text()) if self.damp_entry else 200
        rest = float(self.rest_entry.get_text()) if self.rest_entry else 0
        self.pj = pymunk.PivotJoint(self.mb, self.tgt, (0, 0), local_anchor)
        self.ds = pymunk.DampedSpring(self.mb, self.tgt, (0, 0), local_anchor, rest, k, d)
        if self.cb_stabilizer.get_state():
            self.pm.space.add(self.pj, self.ds)
        else:
            self.pm.space.add(self.ds)
        if self.cb_no_rot.get_state():
            self.saved_moi = self.tgt.moment
            self.tgt.moment = float("inf")
            self.tgt.angular_velocity = 0
        self.dragging = True

    def _stop_drag(self):
        for j in (self.pj, self.ds):
            if j:
                try: self.pm.space.remove(j)
                except: pass
        self.pj = None
        self.ds = None
        if self.mb:
            try: self.pm.space.remove(self.mb)
            except: pass
        self.mb = None
        if self.cb_no_rot.get_state() and self.saved_moi and self.tgt:
            self.tgt.moment = self.saved_moi
        self.saved_moi = None
        self.tgt = None
        self.dragging = False
        self.undo_redo.take_snapshot()

    def handle_event(self, event, wpos):
        if self.ui_manager.manager.get_focus_set():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            info = self.pm.space.point_query_nearest(wpos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
            if body: self._start_drag(wpos, info)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging: self._stop_drag()
        elif event.type == pygame.MOUSEMOTION and self.dragging and self.mb:
            self.mb.position = wpos

    def _compute_spring_force(self):
        if not self.ds or not self.mb or not self.tgt:
            return 0.0
        a = self.mb.local_to_world(self.ds.anchor_a)
        b = self.tgt.local_to_world(self.ds.anchor_b)
        delta = b - a
        dist = delta.length
        if dist == 0:
            return 0.0
        rest = self.ds.rest_length
        k = self.ds.stiffness
        d = self.ds.damping
        va = self.mb.velocity_at_local_point(self.ds.anchor_a)
        vb = self.tgt.velocity_at_local_point(self.ds.anchor_b)
        v_rel = vb - va
        v_along = v_rel.dot(delta / dist)
        force_raw = -k * (dist - rest) - d * v_along
        return abs(force_raw) / 30.0  # PTM_RATIO = 30

    def draw_preview(self, screen, camera):
        if self.dragging and self.tgt and self.mb:
            a = camera.world_to_screen(self.mb.position)
            b = camera.world_to_screen(self.tgt.local_to_world(self.ds.anchor_b))
            pygame.draw.line(screen, (200, 200, 255), a, b, 2)
            pygame.draw.circle(screen, (180, 180, 255), a, 5)
            if self.cb_show_force.get_state():
                f = self._compute_spring_force()
                self.last_force = f
                t = self.font.render(f"{f:.1f} N", True, (220, 220, 255))
                screen.blit(t, (a[0] + 10, a[1] - 10))

    def deactivate(self):
        if self.dragging: self._stop_drag()