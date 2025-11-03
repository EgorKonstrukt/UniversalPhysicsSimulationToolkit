import json
import pygame
import pygame_gui
from pygame_gui.elements import (
    UILabel, UITextEntryLine, UIHorizontalSlider,
    UIDropDownMenu, UIButton, UIWindow, UIPanel, UISelectionList
)
import pymunk
from math import isfinite


class PropertiesWindow:
    _last_window_pos = (120, 120)

    def __init__(self, manager, body, on_close_callback=None, auto_update=False):
        self.manager = manager
        self.body = body
        self.on_close_callback = on_close_callback
        self.auto_update = auto_update
        self.window = None
        self.elements = {}
        self.update_timer = 0.0
        self.apply_to_all_shapes = False
        self._local_clip = None
        self.create_window()

    def create_window(self):
        if self.window and self.window.alive():
            self.window.kill()

        rect = pygame.Rect(*PropertiesWindow._last_window_pos, 540, 680)
        self.window = UIWindow(
            rect,
            manager=self.manager,
            window_display_title="Object Properties",
            object_id=pygame_gui.core.ObjectID(class_id='@properties_window'),
            resizable=True
        )
        self.window.set_minimum_dimensions((460, 360))

        # Верхняя панель (автообновление, apply-to-all, copy/paste)
        y = 10
        lbl = UILabel(pygame.Rect(10, y, 220, 28), "Controls:", self.manager, container=self.window)
        btn_auto = UIButton(pygame.Rect(230, y, 150, 28), f"Auto Update: {'ON' if self.auto_update else 'OFF'}",
                            manager=self.manager, container=self.window, object_id="#auto_update_btn")
        btn_apply_all = UIButton(pygame.Rect(390, y, 130, 28),
                                 f"Apply to all: {'YES' if self.apply_to_all_shapes else 'NO'}",
                                 manager=self.manager, container=self.window, object_id="#apply_all_btn")
        self.elements['auto_update_btn'] = btn_auto
        self.elements['apply_all_btn'] = btn_apply_all

        y += 36
        btn_copy = UIButton(pygame.Rect(10, y, 120, 30), "Copy", manager=self.manager, container=self.window,
                            object_id="#copy_btn")
        btn_paste = UIButton(pygame.Rect(140, y, 120, 30), "Paste", manager=self.manager, container=self.window,
                             object_id="#paste_btn")
        btn_apply = UIButton(pygame.Rect(270, y, 140, 30), "Apply Changes", manager=self.manager,
                             container=self.window, object_id="#apply_btn")
        btn_reset = UIButton(pygame.Rect(420, y, 100, 30), "Reset", manager=self.manager,
                             container=self.window, object_id="#reset_btn")
        self.elements['copy_btn'] = btn_copy
        self.elements['paste_btn'] = btn_paste
        self.elements['apply_btn'] = btn_apply
        self.elements['reset_btn'] = btn_reset

        # Physics section
        y += 44
        self._add_section_title("Physics", y)
        y += 28

        # Mass (entry + slider)
        self._add_label(pygame.Rect(10, y, 140, 26), "Mass (kg)")
        mass_entry = UITextEntryLine(pygame.Rect(160, y, 130, 28), self.manager, container=self.window)
        mass_entry.set_text(f"{self.body.mass:.4f}")
        mass_slider = UIHorizontalSlider(pygame.Rect(300, y + 4, 220, 24),
                                         start_value=self.body.mass,
                                         value_range=(0.001, max(100.0, self.body.mass * 2 + 1.0)),
                                         manager=self.manager, container=self.window)
        self.elements['mass_entry'] = mass_entry
        self.elements['mass_slider'] = mass_slider
        y += 44

        # Moment of inertia display (readonly label)
        self._add_label(pygame.Rect(10, y, 240, 26), "Moment of Inertia (moment)")
        moment_lbl = UILabel(pygame.Rect(260, y, 260, 26), f"{getattr(self.body, 'moment', 0.0):.4f}",
                             self.manager, container=self.window)
        self.elements['moment_label'] = moment_lbl
        y += 38

        # Body type dropdown
        self._add_label(pygame.Rect(10, y, 140, 26), "Body Type")
        dd = UIDropDownMenu(['Dynamic', 'Kinematic', 'Static'],
                            self._body_type_to_str(self.body.body_type),
                            pygame.Rect(160, y, 200, 30), self.manager, container=self.window)
        self.elements['body_type'] = dd
        y += 42

        # Motion
        self._add_section_title("Motion", y); y += 28
        # Velocity X/Y - each entry + small +/- buttons
        self._add_label(pygame.Rect(10, y, 140, 26), "Velocity X")
        vel_x_entry = UITextEntryLine(pygame.Rect(160, y, 120, 28), self.manager, container=self.window)
        vel_x_entry.set_text(f"{self.body.velocity.x:.4f}")
        btn_vx_minus = UIButton(pygame.Rect(290, y, 32, 28), "-", manager=self.manager, container=self.window)
        btn_vx_plus = UIButton(pygame.Rect(330, y, 32, 28), "+", manager=self.manager, container=self.window)
        self.elements['vel_x'] = vel_x_entry
        self.elements['vel_x_-'] = btn_vx_minus
        self.elements['vel_x_+'] = btn_vx_plus
        y += 36

        self._add_label(pygame.Rect(10, y, 140, 26), "Velocity Y")
        vel_y_entry = UITextEntryLine(pygame.Rect(160, y, 120, 28), self.manager, container=self.window)
        vel_y_entry.set_text(f"{self.body.velocity.y:.4f}")
        btn_vy_minus = UIButton(pygame.Rect(290, y, 32, 28), "-", manager=self.manager, container=self.window)
        btn_vy_plus = UIButton(pygame.Rect(330, y, 32, 28), "+", manager=self.manager, container=self.window)
        self.elements['vel_y'] = vel_y_entry
        self.elements['vel_y_-'] = btn_vy_minus
        self.elements['vel_y_+'] = btn_vy_plus
        y += 36

        # Angular velocity
        self._add_label(pygame.Rect(10, y, 140, 26), "Angular Velocity")
        ang_entry = UITextEntryLine(pygame.Rect(160, y, 120, 28), self.manager, container=self.window)
        ang_entry.set_text(f"{self.body.angular_velocity:.4f}")
        btn_ang_minus = UIButton(pygame.Rect(290, y, 32, 28), "-", manager=self.manager, container=self.window)
        btn_ang_plus = UIButton(pygame.Rect(330, y, 32, 28), "+", manager=self.manager, container=self.window)
        self.elements['ang_vel'] = ang_entry
        self.elements['ang_vel_-'] = btn_ang_minus
        self.elements['ang_vel_+'] = btn_ang_plus
        y += 40

        # Position
        self._add_section_title("Position", y); y += 28
        self._add_label(pygame.Rect(10, y, 140, 26), "Position X")
        pos_x_entry = UITextEntryLine(pygame.Rect(160, y, 120, 28), self.manager, container=self.window)
        pos_x_entry.set_text(f"{self.body.position.x:.4f}")
        self.elements['pos_x'] = pos_x_entry
        y += 36
        self._add_label(pygame.Rect(10, y, 140, 26), "Position Y")
        pos_y_entry = UITextEntryLine(pygame.Rect(160, y, 120, 28), self.manager, container=self.window)
        pos_y_entry.set_text(f"{self.body.position.y:.4f}")
        self.elements['pos_y'] = pos_y_entry
        y += 44

        # Shapes section - create panel per shape
        self._add_section_title("Shapes", y); y += 28
        self.elements['shapes_panels'] = []
        shapes = list(self.body.shapes)
        for idx, shape in enumerate(shapes):
            panel, new_y = self._create_shape_panel(idx, shape, y)
            self.elements['shapes_panels'].append(panel)
            y = new_y + 8

        lbl_help = UILabel(pygame.Rect(10, y, 520, 30),
                           "Подсказка: введите числа, нажмите Apply. Auto Update обновляет значения из симуляции.",
                           self.manager, container=self.window)
        self.elements['help'] = lbl_help

    def _add_section_title(self, text, y):
        UILabel(relative_rect=pygame.Rect(10, y, 520, 24),
                text=f"— {text} —", manager=self.manager, container=self.window)

    def _add_label(self, rect, text):
        UILabel(relative_rect=rect, text=text, manager=self.manager, container=self.window)

    def _create_shape_panel(self, idx, shape, top_y):
        panel = UIPanel(relative_rect=pygame.Rect(10, top_y, 520, 100),
                        manager=self.manager, container=self.window,
                        object_id=pygame_gui.core.ObjectID(class_id='@shape_panel'))
        y = 6
        t = type(shape).__name__
        UILabel(pygame.Rect(6, y, 260, 22), f"Shape {idx}: {t}", self.manager, container=panel)
        y += 24

        UILabel(pygame.Rect(6, y, 100, 22), "Friction", self.manager, container=panel)
        fr_slider = UIHorizontalSlider(pygame.Rect(110, y + 2, 150, 22),
                                       start_value=getattr(shape, 'friction', 0.5),
                                       value_range=(0.0, 1.0),
                                       manager=self.manager, container=panel)
        fr_entry = UITextEntryLine(pygame.Rect(270, y, 80, 24), self.manager, container=panel)
        fr_entry.set_text(f"{getattr(shape, 'friction', 0.0):.3f}")
        self.elements[f"shape_{idx}_friction_slider"] = fr_slider
        self.elements[f"shape_{idx}_friction_entry"] = fr_entry

        el_y = y + 32
        UILabel(pygame.Rect(6, el_y, 100, 22), "Elasticity", self.manager, container=panel)
        el_slider = UIHorizontalSlider(pygame.Rect(110, el_y + 2, 150, 22),
                                       start_value=getattr(shape, 'elasticity', 0.0),
                                       value_range=(0.0, 1.0),
                                       manager=self.manager, container=panel)
        el_entry = UITextEntryLine(pygame.Rect(270, el_y, 80, 24), self.manager, container=panel)
        el_entry.set_text(f"{getattr(shape, 'elasticity', 0.0):.3f}")
        self.elements[f"shape_{idx}_elasticity_slider"] = el_slider
        self.elements[f"shape_{idx}_elasticity_entry"] = el_entry

        cy = el_y + 36
        UILabel(pygame.Rect(6, cy, 100, 22), "Collision Type", self.manager, container=panel)
        coll_entry = UITextEntryLine(pygame.Rect(110, cy, 80, 24), self.manager, container=panel)
        coll_entry.set_text(str(getattr(shape, 'collision_type', 0)))
        sensor_btn = UIButton(pygame.Rect(350, y - 28, 100, 30),
                              "Sensor: YES" if getattr(shape, 'sensor', False) else "Sensor: NO",
                              manager=self.manager, container=panel)
        self.elements[f"shape_{idx}_collision_entry"] = coll_entry
        self.elements[f"shape_{idx}_sensor_btn"] = sensor_btn

        spec_y = cy + 32
        if isinstance(shape, pymunk.Circle):
            UILabel(pygame.Rect(6, spec_y, 100, 22), "Radius", self.manager, container=panel)
            radius_entry = UITextEntryLine(pygame.Rect(110, spec_y, 80, 24), self.manager, container=panel)
            radius_entry.set_text(f"{shape.radius:.4f}")
            UILabel(pygame.Rect(200, spec_y, 60, 22), "Offset", self.manager, container=panel)
            offx = UITextEntryLine(pygame.Rect(260, spec_y, 60, 24), self.manager, container=panel)
            offy = UITextEntryLine(pygame.Rect(330, spec_y, 60, 24), self.manager, container=panel)
            offx.set_text(f"{shape.offset.x:.4f}")
            offy.set_text(f"{shape.offset.y:.4f}")
            self.elements[f"shape_{idx}_radius"] = radius_entry
            self.elements[f"shape_{idx}_offset_x"] = offx
            self.elements[f"shape_{idx}_offset_y"] = offy
        elif isinstance(shape, pymunk.Poly):
            UILabel(pygame.Rect(6, spec_y, 140, 22), f"Vertices: {len(shape.get_vertices())}",
                    self.manager, container=panel)
            recompute_btn = UIButton(pygame.Rect(160, spec_y, 140, 24), "Recompute Moment", manager=self.manager,
                                     container=panel)
            self.elements[f"shape_{idx}_recompute_btn"] = recompute_btn
        else:
            UILabel(pygame.Rect(6, spec_y, 260, 22), "Shape-specific controls not implemented.",
                    self.manager, container=panel)

        bottom_y = top_y + 100
        return panel, bottom_y

    def _body_type_to_str(self, bt):
        return {
            pymunk.Body.DYNAMIC: 'Dynamic',
            pymunk.Body.KINEMATIC: 'Kinematic',
            pymunk.Body.STATIC: 'Static'
        }.get(bt, 'Dynamic')

    def _str_to_body_type(self, s):
        return {
            'Dynamic': pymunk.Body.DYNAMIC,
            'Kinematic': pymunk.Body.KINEMATIC,
            'Static': pymunk.Body.STATIC
        }[s]

    def _safe_float(self, s, default=0.0):
        try:
            v = float(s)
            if not isfinite(v):
                return default
            return v
        except Exception:
            return default

    # ---------------- event handling ----------------
    def process_event(self, event):
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            elem = event.ui_element
            for key, el in self.elements.items():
                if el is elem:
                    self._on_text_finished(key, el)
                    break

        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            elem = event.ui_element
            if elem is self.elements.get('mass_slider'):
                v = event.value
                self.elements['mass_entry'].set_text(f"{v:.4f}")
                self._update_moment_preview(mass=v)
            else:
                for k, el in list(self.elements.items()):
                    if el is elem and k.startswith("shape_") and "_friction_slider" in k:
                        idx = int(k.split('_')[1])
                        v = event.value
                        self.elements[f"shape_{idx}_friction_entry"].set_text(f"{v:.3f}")
                        if self.apply_to_all_shapes:
                            self._apply_shape_property_to_all('friction', v)
                        else:
                            self._set_shape_attr(idx, 'friction', v)
                        break
                    if el is elem and k.startswith("shape_") and "_elasticity_slider" in k:
                        idx = int(k.split('_')[1])
                        v = event.value
                        self.elements[f"shape_{idx}_elasticity_entry"].set_text(f"{v:.3f}")
                        if self.apply_to_all_shapes:
                            self._apply_shape_property_to_all('elasticity', v)
                        else:
                            self._set_shape_attr(idx, 'elasticity', v)
                        break

        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element is self.elements.get('body_type'):
                new_type = self._str_to_body_type(event.text)
                self._change_body_type(new_type)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            btn = event.ui_element
            if btn is self.elements.get('auto_update_btn'):
                self.auto_update = not self.auto_update
                btn.set_text(f"Auto Update: {'ON' if self.auto_update else 'OFF'}")
            elif btn is self.elements.get('apply_all_btn'):
                self.apply_to_all_shapes = not self.apply_to_all_shapes
                btn.set_text(f"Apply to all: {'YES' if self.apply_to_all_shapes else 'NO'}")
            elif btn is self.elements.get('copy_btn'):
                self._copy_properties()
            elif btn is self.elements.get('paste_btn'):
                self._paste_properties()
            elif btn is self.elements.get('apply_btn'):
                self._apply_all()
            elif btn is self.elements.get('reset_btn'):
                self._reset_values()
            # +/- buttons for velocities and angular vel
            elif btn is self.elements.get('vel_x_-'):
                self._increment_velocity('vel_x', -1.0)
            elif btn is self.elements.get('vel_x_+'):
                self._increment_velocity('vel_x', 1.0)
            elif btn is self.elements.get('vel_y_-'):
                self._increment_velocity('vel_y', -1.0)
            elif btn is self.elements.get('vel_y_+'):
                self._increment_velocity('vel_y', 1.0)
            elif btn is self.elements.get('ang_vel_-'):
                self._increment_velocity('ang_vel', -0.5)
            elif btn is self.elements.get('ang_vel_+'):
                self._increment_velocity('ang_vel', 0.5)
            else:
                for k, el in list(self.elements.items()):
                    if el is btn:
                        if k.endswith('_sensor_btn'):
                            idx = int(k.split('_')[1])
                            self._toggle_shape_sensor(idx)
                            break
                        if k.endswith('_recompute_btn'):
                            idx = int(k.split('_')[1])
                            self._recompute_shape_moment(idx)
                            break

    def _on_text_finished(self, key, element):
        text = element.get_text()
        if key == 'mass_entry':
            val = max(self._safe_float(text, 0.001), 0.001)
            slider = self.elements.get('mass_slider')
            if slider:
                low, high = slider.value_range
                if val < low:
                    slider.set_value_range((val * 0.5, high))
                if val > high:
                    slider.set_value_range((low, val * 1.5))
                slider.set_current_value(val)
            self._update_moment_preview(mass=val)
        elif key in ('vel_x', 'vel_y', 'ang_vel', 'pos_x', 'pos_y'):
            self._apply_property_key_to_body(key, text)
        else:
            if key.startswith("shape_") and ("_friction_entry" in key or "_elasticity_entry" in key):
                parts = key.split('_')
                idx = int(parts[1])
                prop = 'friction' if key.endswith('friction_entry') else 'elasticity'
                val = self._safe_float(text)
                slider = self.elements.get(f"shape_{idx}_{prop}_slider")
                if slider:
                    slider.set_current_value(val)
                if self.apply_to_all_shapes:
                    self._apply_shape_property_to_all(prop, val)
                else:
                    self._set_shape_attr(idx, prop, val)
            elif key.startswith("shape_") and key.endswith('_radius'):
                idx = int(key.split('_')[1])
                val = max(self._safe_float(text, 0.001), 0.001)
                shape = self._get_shape_by_index(idx)
                if isinstance(shape, pymunk.Circle):
                    shape.unsafe_set_radius(val)
                    self._update_moment_preview()
            elif key.startswith("shape_") and key.endswith('_offset_x'):
                idx = int(key.split('_')[1])
                ox = self._safe_float(text, 0.0)
                oy = self._safe_float(self.elements.get(f"shape_{idx}_offset_y").get_text(), 0.0)
                shape = self._get_shape_by_index(idx)
                if isinstance(shape, pymunk.Circle):
                    shape.offset = pymunk.Vec2d(ox, oy)
            elif key.startswith("shape_") and key.endswith('_offset_y'):
                idx = int(key.split('_')[1])
                oy = self._safe_float(text, 0.0)
                ox = self._safe_float(self.elements.get(f"shape_{idx}_offset_x").get_text(), 0.0)
                shape = self._get_shape_by_index(idx)
                if isinstance(shape, pymunk.Circle):
                    shape.offset = pymunk.Vec2d(ox, oy)
            elif key.startswith("shape_") and key.endswith('_collision_entry'):
                idx = int(key.split('_')[1])
                ct = int(self._safe_float(text, 0))
                shape = self._get_shape_by_index(idx)
                if shape:
                    shape.collision_type = ct

    def _apply_property_key_to_body(self, key, text):
        v = self._safe_float(text)
        if key == 'vel_x':
            self.body.velocity = (v, self.body.velocity.y)
        elif key == 'vel_y':
            self.body.velocity = (self.body.velocity.x, v)
        elif key == 'ang_vel':
            self.body.angular_velocity = v
        elif key == 'pos_x':
            self.body.position = (v, self.body.position.y)
        elif key == 'pos_y':
            self.body.position = (self.body.position.x, v)
        self.body.activate()

    def _increment_velocity(self, key, delta):
        if key == 'vel_x':
            cur = self._safe_float(self.elements['vel_x'].get_text(), 0.0)
            cur += delta
            self.elements['vel_x'].set_text(f"{cur:.4f}")
            self._apply_property_key_to_body('vel_x', str(cur))
        elif key == 'vel_y':
            cur = self._safe_float(self.elements['vel_y'].get_text(), 0.0)
            cur += delta
            self.elements['vel_y'].set_text(f"{cur:.4f}")
            self._apply_property_key_to_body('vel_y', str(cur))
        elif key == 'ang_vel':
            cur = self._safe_float(self.elements['ang_vel'].get_text(), 0.0)
            cur += delta
            self.elements['ang_vel'].set_text(f"{cur:.4f}")
            self._apply_property_key_to_body('ang_vel', str(cur))

    def _apply_shape_property_to_all(self, prop, value):
        for idx, s in enumerate(list(self.body.shapes)):
            try:
                setattr(s, prop, value)
            except Exception:
                pass
        self.body.activate()

    def _set_shape_attr(self, idx, attr, value):
        shape = self._get_shape_by_index(idx)
        if not shape:
            return
        try:
            setattr(shape, attr, value)
        except Exception:
            pass
        self.body.activate()

    def _toggle_shape_sensor(self, idx):
        shape = self._get_shape_by_index(idx)
        if not shape:
            return
        shape.sensor = not getattr(shape, 'sensor', False)
        btn = self.elements.get(f"shape_{idx}_sensor_btn")
        if btn:
            btn.set_text("Sensor: YES" if shape.sensor else "Sensor: NO")

    def _recompute_shape_moment(self, idx):
        shape = self._get_shape_by_index(idx)
        if not shape:
            return
        self._update_moment_preview()

    def _get_shape_by_index(self, idx):
        shapes = list(self.body.shapes)
        if idx < 0 or idx >= len(shapes):
            return None
        return shapes[idx]

    def _update_moment_preview(self, mass=None):
        m = mass if mass is not None else max(0.001, self._safe_float(self.elements.get('mass_entry').get_text(), self.body.mass))
        total = 0.0
        shapes = list(self.body.shapes)
        if not shapes:
            total = getattr(self.body, 'moment', 0.0)
        else:
            per_shape_mass = m / max(1, len(shapes))
            for s in shapes:
                if isinstance(s, pymunk.Circle):
                    total += pymunk.moment_for_circle(per_shape_mass, 0, s.radius, s.offset)
                elif isinstance(s, pymunk.Poly):
                    verts = s.get_vertices()
                    total += pymunk.moment_for_poly(per_shape_mass, verts)
                else:
                    total += getattr(self.body, 'moment', 0.0) / max(1, len(shapes))
        # update label
        lbl = self.elements.get('moment_label')
        if lbl:
            lbl.set_text(f"{total:.4f}")

    def _apply_all(self):
        mass_val = max(self._safe_float(self.elements.get('mass_entry').get_text(), self.body.mass), 0.001)
        self._set_mass_and_moment(mass_val)

        self._apply_property_key_to_body('vel_x', self.elements['vel_x'].get_text())
        self._apply_property_key_to_body('vel_y', self.elements['vel_y'].get_text())
        self._apply_property_key_to_body('ang_vel', self.elements['ang_vel'].get_text())
        self._apply_property_key_to_body('pos_x', self.elements['pos_x'].get_text())
        self._apply_property_key_to_body('pos_y', self.elements['pos_y'].get_text())

        bt_text = self.elements['body_type'].selected_option
        if isinstance(bt_text, tuple):
            bt_text = bt_text[0]
        self._change_body_type(self._str_to_body_type(bt_text))

        # shapes: friction/elasticity/collision/sensor/radius/offset
        for key, el in list(self.elements.items()):
            if key.startswith('shape_') and key.endswith('_friction_entry'):
                idx = int(key.split('_')[1])
                val = self._safe_float(el.get_text(), getattr(self._get_shape_by_index(idx), 'friction', 0.0))
                if self.apply_to_all_shapes:
                    self._apply_shape_property_to_all('friction', val)
                else:
                    self._set_shape_attr(idx, 'friction', val)
            if key.startswith('shape_') and key.endswith('_elasticity_entry'):
                idx = int(key.split('_')[1])
                val = self._safe_float(el.get_text(), getattr(self._get_shape_by_index(idx), 'elasticity', 0.0))
                if self.apply_to_all_shapes:
                    self._apply_shape_property_to_all('elasticity', val)
                else:
                    self._set_shape_attr(idx, 'elasticity', val)
            if key.endswith('_collision_entry'):
                idx = int(key.split('_')[1])
                ct = int(self._safe_float(el.get_text(), 0))
                shape = self._get_shape_by_index(idx)
                if shape:
                    shape.collision_type = ct
            if key.endswith('_radius'):
                idx = int(key.split('_')[1])
                val = max(self._safe_float(el.get_text(), 0.001), 0.001)
                shape = self._get_shape_by_index(idx)
                if isinstance(shape, pymunk.Circle):
                    shape.unsafe_set_radius(val)
            if key.endswith('_offset_x') or key.endswith('_offset_y'):
                pass

        self.body.activate()
        self.elements['moment_label'].set_text(f"{self.body.moment:.4f}")

    def _set_mass_and_moment(self, mass):
        """Устанавливает массу тела и момент инерции, суммируя моменты shape'ов."""
        shapes = list(self.body.shapes)
        if not shapes:
            self.body.mass = mass
            return
        per_mass = mass / max(1, len(shapes))
        total_moment = 0.0
        for s in shapes:
            if isinstance(s, pymunk.Circle):
                total_moment += pymunk.moment_for_circle(per_mass, 0, s.radius, s.offset)
            elif isinstance(s, pymunk.Poly):
                verts = s.get_vertices()
                total_moment += pymunk.moment_for_poly(per_mass, verts)
            else:
                total_moment += 0.0
        self.body.mass = mass
        self.body.moment = total_moment

    def _change_body_type(self, new_type):
        if new_type == self.body.body_type:
            return
        pos, angle, vel, ang_vel = self.body.position, self.body.angle, self.body.velocity, self.body.angular_velocity
        shapes = list(self.body.shapes)
        space = self.body.space
        if space:
            try:
                space.remove(self.body, *shapes)
            except Exception:
                pass
        self.body.body_type = new_type
        self.body.position, self.body.angle = pos, angle
        if new_type == pymunk.Body.DYNAMIC:
            self.body.velocity, self.body.angular_velocity = vel, ang_vel
        else:
            self.body.velocity, self.body.angular_velocity = (0, 0), 0
        if space:
            try:
                space.add(self.body, *shapes)
            except Exception:
                pass
        self.body.activate()

    def _reset_values(self):
        self.kill()
        self.create_window()

    # ---------------- copy/paste ----------------
    def _copy_properties(self):
        data = {
            'mass': self._safe_float(self.elements['mass_entry'].get_text(), self.body.mass),
            'velocity': (self._safe_float(self.elements['vel_x'].get_text(), 0.0),
                         self._safe_float(self.elements['vel_y'].get_text(), 0.0)),
            'ang_vel': self._safe_float(self.elements['ang_vel'].get_text(), 0.0),
            'position': (self._safe_float(self.elements['pos_x'].get_text(), 0.0),
                         self._safe_float(self.elements['pos_y'].get_text(), 0.0))
        }
        self._local_clip = json.dumps(data)

    def _paste_properties(self):
        if not self._local_clip:
            return
        try:
            data = json.loads(self._local_clip)
        except Exception:
            return
        if 'mass' in data:
            self.elements['mass_entry'].set_text(f"{data['mass']:.4f}")
            self.elements['mass_slider'].set_current_value(data['mass'])
            self._update_moment_preview(mass=data['mass'])
        if 'velocity' in data:
            vx, vy = data['velocity']
            self.elements['vel_x'].set_text(f"{vx:.4f}")
            self.elements['vel_y'].set_text(f"{vy:.4f}")
        if 'ang_vel' in data:
            self.elements['ang_vel'].set_text(f"{data['ang_vel']:.4f}")
        if 'position' in data:
            px, py = data['position']
            self.elements['pos_x'].set_text(f"{px:.4f}")
            self.elements['pos_y'].set_text(f"{py:.4f}")
        # и применим сразу
        self._apply_all()

    # ---------------- periodic update ----------------
    def update(self, time_delta):
        if self.auto_update:
            self.update_timer += time_delta
            if self.update_timer > 0.032:
                self._refresh_display_values()
                self.update_timer = 0.0

    def _refresh_display_values(self):
        """Обновляет значения на экране из текущего тела (позиция, скорость и т.д.)"""
        try:
            self.elements['pos_x'].set_text(f"{self.body.position.x:.4f}")
            self.elements['pos_y'].set_text(f"{self.body.position.y:.4f}")
            self.elements['vel_x'].set_text(f"{self.body.velocity.x:.4f}")
            self.elements['vel_y'].set_text(f"{self.body.velocity.y:.4f}")
            self.elements['ang_vel'].set_text(f"{self.body.angular_velocity:.4f}")
            self.elements['mass_entry'].set_text(f"{self.body.mass:.4f}")
            # sync slider gently
            slider = self.elements.get('mass_slider')
            if slider:
                try:
                    slider.set_current_value(self.body.mass)
                except Exception:
                    pass
            # shapes
            for idx, s in enumerate(list(self.body.shapes)):
                # friction/elasticity
                fe = self.elements.get(f"shape_{idx}_friction_entry")
                if fe:
                    fe.set_text(f"{getattr(s, 'friction', 0.0):.3f}")
                    # sync slider
                    sl = self.elements.get(f"shape_{idx}_friction_slider")
                    if sl:
                        try:
                            sl.set_current_value(getattr(s, 'friction', 0.0))
                        except Exception:
                            pass
                ee = self.elements.get(f"shape_{idx}_elasticity_entry")
                if ee:
                    ee.set_text(f"{getattr(s, 'elasticity', 0.0):.3f}")
                    sl = self.elements.get(f"shape_{idx}_elasticity_slider")
                    if sl:
                        try:
                            sl.set_current_value(getattr(s, 'elasticity', 0.0))
                        except Exception:
                            pass
                # sensor button text
                sb = self.elements.get(f"shape_{idx}_sensor_btn")
                if sb:
                    sb.set_text("Sensor: YES" if getattr(s, 'sensor', False) else "Sensor: NO")
                # radius/offset for circle
                if isinstance(s, pymunk.Circle):
                    re = self.elements.get(f"shape_{idx}_radius")
                    if re:
                        re.set_text(f"{s.radius:.4f}")
                    offx = self.elements.get(f"shape_{idx}_offset_x")
                    offy = self.elements.get(f"shape_{idx}_offset_y")
                    if offx:
                        offx.set_text(f"{s.offset.x:.4f}")
                    if offy:
                        offy.set_text(f"{s.offset.y:.4f}")
            # update moment label
            self.elements['moment_label'].set_text(f"{self.body.moment:.4f}")
        except Exception:
            # любые ошибки — пропускаем, чтобы не ломать цикл
            pass

    def kill(self):
        if self.window and self.window.alive():
            PropertiesWindow._last_window_pos = self.window.rect.topleft
            self.window.kill()
        if self.on_close_callback:
            self.on_close_callback()
