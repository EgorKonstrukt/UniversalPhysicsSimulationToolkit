import pygame_gui
from pygame_gui.elements import UIDropDownMenu, UIHorizontalSlider, UILabel, UITextEntryLine, UIWindow
import pygame
import pymunk
import math


class PropertiesWindow:
    def __init__(self, manager, body, on_close_callback=None):
        self.manager = manager
        self.body = body
        self.on_close_callback = on_close_callback
        self.window = None
        self.elements = {}
        self.create_window()

    def create_window(self):
        self.window = UIWindow(
            pygame.Rect(100, 100, 420, 560),
            manager=self.manager,
            window_display_title="Object Properties",
            object_id=pygame_gui.core.ObjectID(class_id='@properties_window')
        )
        y = 10
        self._add_row("Mass (kg)", 'mass', str(round(self.body.mass, 3)), y); y += 40
        if self.body.shapes:
            s = next(iter(self.body.shapes))
            self._add_slider_row("Friction", 'friction', s.friction, 0.0, 1.0, y); y += 50
            self._add_slider_row("Elasticity", 'elasticity', s.elasticity, 0.0, 1.0, y); y += 50
        self._add_dropdown_row("Body Type", 'body_type',
                               options=['Dynamic', 'Kinematic', 'Static'],
                               initial=self._body_type_to_str(self.body.body_type), y=y); y += 40
        self._add_row("Velocity X", 'vel_x', str(round(self.body.velocity.x, 3)), y); y += 40
        self._add_row("Velocity Y", 'vel_y', str(round(self.body.velocity.y, 3)), y); y += 40
        self._add_row("Angular Velocity", 'ang_vel', str(round(self.body.angular_velocity, 3)), y); y += 40
        self._add_row("Position X", 'pos_x', str(round(self.body.position.x, 3)), y); y += 40
        self._add_row("Position Y", 'pos_y', str(round(self.body.position.y, 3)), y); y += 40

    def _add_row(self, label_text, key, initial_text, y):
        UILabel(relative_rect=pygame.Rect(10, y, 130, 25), text=label_text, manager=self.manager, container=self.window)
        entry = UITextEntryLine(relative_rect=pygame.Rect(150, y, 200, 30), manager=self.manager, container=self.window)
        entry.set_text(initial_text)
        self.elements[key] = entry

    def _add_slider_row(self, label_text, key, value, minv, maxv, y):
        UILabel(relative_rect=pygame.Rect(10, y, 130, 25), text=label_text, manager=self.manager, container=self.window)
        slider = UIHorizontalSlider(relative_rect=pygame.Rect(150, y + 5, 200, 25), start_value=value, value_range=(minv, maxv), manager=self.manager, container=self.window)
        self.elements[key] = slider

    def _add_dropdown_row(self, label_text, key, options, initial, y):
        UILabel(relative_rect=pygame.Rect(10, y, 130, 25), text=label_text, manager=self.manager, container=self.window)
        dd = UIDropDownMenu(options_list=options, starting_option=initial, relative_rect=pygame.Rect(150, y, 200, 30), manager=self.manager, container=self.window)
        self.elements[key] = dd

    def _body_type_to_str(self, bt):
        return {pymunk.Body.DYNAMIC: 'Dynamic', pymunk.Body.KINEMATIC: 'Kinematic', pymunk.Body.STATIC: 'Static'}.get(bt, 'Dynamic')

    def _str_to_body_type(self, s):
        return {'Dynamic': pymunk.Body.DYNAMIC, 'Kinematic': pymunk.Body.KINEMATIC, 'Static': pymunk.Body.STATIC}[s]

    def _safe_float(self, s, default=0.0):
        try:
            return float(s)
        except (ValueError, TypeError):
            return default

    def process_event(self, event):
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            eid = event.ui_element
            if eid == self.elements.get('mass'):
                val = max(self._safe_float(eid.get_text()), 0.001)
                if self.body.body_type == pymunk.Body.DYNAMIC and self.body.shapes:
                    s = next(iter(self.body.shapes))
                    if isinstance(s, pymunk.Circle):
                        moment = pymunk.moment_for_circle(val, 0, s.radius, (0, 0))
                    elif isinstance(s, pymunk.Poly):
                        vertices = [v - s.body.position for v in s.get_vertices()]
                        moment = pymunk.moment_for_poly(val, vertices, (0, 0))
                    else:
                        return
                    self.body.mass = val
                    self.body.moment = moment
                    self.body.activate()
            elif eid == self.elements.get('vel_x'):
                self.body.velocity = (self._safe_float(eid.get_text()), self.body.velocity.y)
                self.body.activate()
            elif eid == self.elements.get('vel_y'):
                self.body.velocity = (self.body.velocity.x, self._safe_float(eid.get_text()))
                self.body.activate()
            elif eid == self.elements.get('ang_vel'):
                self.body.angular_velocity = self._safe_float(eid.get_text())
                self.body.activate()
            elif eid == self.elements.get('pos_x'):
                self.body.position = (self._safe_float(eid.get_text()), self.body.position.y)
                self.body.activate()
            elif eid == self.elements.get('pos_y'):
                self.body.position = (self.body.position.x, self._safe_float(eid.get_text()))
                self.body.activate()

        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if self.body.shapes:
                if event.ui_element == self.elements.get('friction'):
                    for s in self.body.shapes: s.friction = event.value
                elif event.ui_element == self.elements.get('elasticity'):
                    for s in self.body.shapes: s.elasticity = event.value

        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.elements.get('body_type'):
                new_type = self._str_to_body_type(event.text)
                if new_type != self.body.body_type:
                    self._change_body_type(new_type)

    def _change_body_type(self, new_type):
        old_type = self.body.body_type
        pos, angle = self.body.position, self.body.angle
        vel, ang_vel = self.body.velocity, self.body.angular_velocity
        shapes = list(self.body.shapes)
        space = self.body.space
        if space:
            space.remove(self.body, *shapes)
        self.body.body_type = new_type
        self.body.position = pos
        self.body.angle = angle
        if new_type == pymunk.Body.DYNAMIC:
            self.body.velocity = vel
            self.body.angular_velocity = ang_vel
        else:
            self.body.velocity = (0, 0)
            self.body.angular_velocity = 0
        if space:
            space.add(self.body, *shapes)

    def kill(self):
        if self.window.alive():
            self.window.kill()
        if self.on_close_callback:
            self.on_close_callback()