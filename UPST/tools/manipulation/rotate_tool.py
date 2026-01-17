import pygame
import pymunk
import math
from UPST.config import config
from UPST.tools.base_tool import BaseTool
import pygame_gui

class RotateTool(BaseTool):
    name = "Rotate"
    icon_path = "sprites/gui/tools/rotate.png"

    def __init__(self, pm, app):
        super().__init__(pm, app)
        self.tgt = None
        self.drag = False
        self.start_angle = 0.0
        self.initial_vec = None
        self.cb_center = None
        self.max_snap_radius = 120
        self.saved_body_type = None
        self.saved_mass = None
        self.saved_moment = None
        self.rotation_center = None
        self.current_angle = 0.0
        self.font = pygame.font.SysFont("Consolas", 14)

    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(200, config.app.screen_height - 200, 300, 120),
            manager=self.ui_manager.manager,
            window_display_title="Rotate Settings"
        )
        self.cb_center = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(1, 10, 200, 20),
            text="Use center of mass",
            manager=self.ui_manager.manager,
            container=win,
            object_id="#rotate_use_com"
        )
        self.settings_window = win

    def handle_event(self, event, wpos):
        if self.ui_manager.manager.get_focus_set():
            return
        if isinstance(wpos, (tuple, list)):
            mx, my = float(wpos[0]), float(wpos[1])
        else:
            mx, my = float(wpos.x), float(wpos.y)
        mouse_pos = pymunk.Vec2d(mx, my)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            info = self.pm.space.point_query_nearest(mouse_pos, 0, pymunk.ShapeFilter())
            body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
            if body and body.body_type == pymunk.Body.DYNAMIC:
                self.tgt = body
                use_com = self.cb_center and self.cb_center.get_state()
                if use_com:
                    cx, cy = self.tgt.position.x, self.tgt.position.y
                else:
                    cx, cy = mx, my
                self.rotation_center = pymunk.Vec2d(cx, cy)
                self.start_angle = self.tgt.angle
                self.initial_vec = mouse_pos - self.rotation_center
                self.saved_body_type = self.tgt.body_type
                self.saved_mass = self.tgt.mass
                self.saved_moment = self.tgt.moment
                self.tgt.body_type = pymunk.Body.KINEMATIC
                self.drag = True
                self.current_angle = 0.0
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag:
                self._stop_rotate()
        elif event.type == pygame.MOUSEMOTION and self.drag and self.tgt:
            self._rotate_to(mouse_pos)

    def _rotate_to(self, wpos):
        if not self.initial_vec or self.initial_vec.length == 0:
            return
        current_vec = wpos - self.rotation_center
        if current_vec.length == 0:
            return
        da = current_vec.angle - self.initial_vec.angle
        target_angle = self.start_angle + da
        self.current_angle = da
        if (wpos - self.rotation_center).length <= self.max_snap_radius:
            snap_step = math.radians(15)
            target_angle = round(target_angle / snap_step) * snap_step
            self.current_angle = target_angle - self.start_angle
        self.tgt.angle = target_angle

    def _stop_rotate(self):
        if self.tgt and self.saved_body_type is not None:
            self.tgt.body_type = self.saved_body_type
            if self.saved_body_type == pymunk.Body.DYNAMIC:
                self.tgt.mass = self.saved_mass
                self.tgt.moment = self.saved_moment
        self.drag = False
        self.tgt = None
        self.initial_vec = None
        self.rotation_center = None
        self.saved_body_type = None
        self.saved_mass = None
        self.saved_moment = None
        if hasattr(self, 'undo_redo'):
            self.undo_redo.take_snapshot()

    def deactivate(self):
        if self.drag:
            self._stop_rotate()

    def draw_preview(self, screen, camera):
        if not self.drag or self.rotation_center is None:
            return

        cx, cy = camera.world_to_screen((self.rotation_center.x, self.rotation_center.y))
        radius_px = self.max_snap_radius

        arc_color = (180, 80, 255, 180)
        text_color = (255, 255, 255)
        outline_color = (255, 255, 255, 200)

        surf = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        start_angle = math.radians(-90)
        end_angle = start_angle + self.current_angle
        points = [(cx, cy)]
        for i in range(36):
            angle = start_angle + (end_angle - start_angle) * i / 35
            x = cx + math.cos(angle) * radius_px
            y = cy + math.sin(angle) * radius_px
            points.append((x, y))
        points.append((cx, cy))
        pygame.draw.polygon(surf, arc_color, [(p[0] - cx + radius_px, p[1] - cy + radius_px) for p in points])
        pygame.draw.lines(surf, outline_color, True, [(p[0] - cx + radius_px, p[1] - cy + radius_px) for p in points[:-1]], 2)
        screen.blit(surf, (cx - radius_px, cy - radius_px))

        world_angle_deg = math.degrees(self.tgt.angle)
        world_text = f"World: {world_angle_deg:+.1f}°"
        world_surf = self.font.render(world_text, True, text_color)
        world_rect = world_surf.get_rect(center=(cx, cy - radius_px - 45))
        screen.blit(world_surf, world_rect)

        rel_angle_deg = math.degrees(self.current_angle)
        rel_text = f"{rel_angle_deg:+.1f}°"
        rel_surf = self.font.render(rel_text, True, text_color)
        rel_rect = rel_surf.get_rect(center=(cx, cy - radius_px - 25))
        screen.blit(rel_surf, rel_rect)

        pygame.draw.circle(screen, outline_color, (int(cx), int(cy)), 4, 2)

        small_radius = 10
        start_rad = math.radians(-90)
        end_rad = start_rad + self.current_angle
        pygame.draw.arc(screen, outline_color, (cx - small_radius, cy - small_radius, small_radius*2, small_radius*2), start_rad, end_rad, 2)