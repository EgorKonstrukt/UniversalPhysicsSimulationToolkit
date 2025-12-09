import csv

import pygame_gui
from typing import Optional
import pygame
import tkinter as tk
from tkinter import filedialog
import os

from UPST.gui.plotter import Plotter
from UPST.debug.debug_manager import Debug

class ContextPlotterWindow:
    def __init__(self, manager: Optional[object], ui_manager=None, position=(10,10), size=(600,400),
                 window_title="Data Plotter", max_samples=200,
                 x_label: str = "X", y_label: str = "Y", tracked_object=None):
        self.tracked_object = tracked_object
        orig_mgr = manager
        self.ui_manager = ui_manager
        self._wrapper = orig_mgr
        self.manager = manager
        self.position = position
        self.size = size
        self.window_title = window_title
        self.max_samples = max_samples
        self.x_label = x_label
        self.y_label = y_label
        self.window = None
        self.plot_image = None
        self.plotter = None
        self.buttons = {}
        self.axis_controls = {}
        self.slider_controls = {}
        self.checkboxes = {}
        self.current_x_axis = "time"
        self.current_y_axis = "position_x"
        self.time_span = 5.0
        self.smoothing = 0.36
        self.show_axes = True
        self.show_legends = True
        self._create_window()
        self.ui_manager.register_plotter_window(self)
        self._create_buttons()
        self._create_sample_controls()
        self._create_axis_controls()
        self._create_slider_controls()
        self._create_checkboxes()
        self._create_save_buttons()

    def _fetch_value(self, key):
        if not self.tracked_object: return 0.0
        o = self.tracked_object
        if key == "pos_x": return o.position.x
        if key == "pos_y": return o.position.y
        if key == "vel": return o.velocity.x + o.velocity.y
        if key == "vel_x": return o.velocity.x
        if key == "vel_y": return o.velocity.y
        if key == "ang_vel": return o.angular_velocity
        if key == "acc_x": return o.force.x / o.mass if o.mass else 0.0
        if key == "acc_y": return o.force.y / o.mass if o.mass else 0.0
        if key == "acc_mag": return (o.force.x**2 + o.force.y**2)**0.5 / o.mass if o.mass else 0.0
        if key == "force_x": return o.force.x
        if key == "force_y": return o.force.y
        if key == "force_mag": return (o.force.x**2 + o.force.y**2)**0.5
        if key == "mom_x": return o.velocity.x * o.mass
        if key == "mom_y": return o.velocity.y * o.mass
        if key == "ang_mom": return o.angular_velocity * o.moment
        if key == "lin_kin_en": return 0.5 * o.mass * (o.velocity.x**2 + o.velocity.y**2)
        if key == "ang_kin_en": return 0.5 * o.moment * o.angular_velocity**2
        if key == "kin_en_sum": return 0.5 * o.mass * (o.velocity.x**2 + o.velocity.y**2) + 0.5 * o.moment * o.angular_velocity**2
        if key == "pot_grav_en": return -o.mass * 9.81 * o.position.y
        if key == "pot_en_sum": return -o.mass * 9.81 * o.position.y
        if key == "en_sum": return 0.5 * o.mass * (o.velocity.x**2 + o.velocity.y**2) + 0.5 * o.moment * o.angular_velocity**2 - o.mass * 9.81 * o.position.y

        return 0.0

    def fetch_and_add_data(self, elapsed_time):
        if not self.tracked_object or not self.is_open(): return
        x_val = elapsed_time if self.current_x_axis == "time" else self._fetch_value(self.current_x_axis)
        y_val = elapsed_time if self.current_y_axis == "time" else self._fetch_value(self.current_y_axis)
        self.plotter.add_data(str(self.current_y_axis)+" / "+str(self.current_x_axis ), y_val, x=x_val, group="Tracked Object")

    def _create_window(self):
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(self.position, self.size),
            manager=self.manager,
            window_display_title=self.window_title,
            resizable=True
        )
        plot_width = self.size[0] - 205
        plot_height = self.size[1] - 30
        self.plot_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect(200, 0, plot_width, plot_height),
            image_surface=pygame.Surface((plot_width, plot_height)).convert(),
            manager=self.manager,
            container=self.window
        )
        self.plotter = Plotter((plot_width, plot_height),
                               max_samples=self.max_samples,
                               x_label=self.x_label,
                               y_label=self.y_label)

    def _create_buttons(self):
        btn_defs = {
            "toggle_mode": ("Toggle Mode", (10, 10, 100, 30)),
            "clear_data": ("Clear Data", (10, 50, 100, 30)),
        }
        for key, (txt, rect) in btn_defs.items():
            self.buttons[key] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(rect),
                text=txt,
                manager=self.manager,
                container=self.window
            )

    def _create_sample_controls(self):
        pass

    def _create_axis_controls(self):
        axis_options = [
            "Time",
            "Position (x)",
            "Position (y)",
            "Velocity",
            "Velocity (x)",
            "Velocity (y)",
            "Angular Velocity",
            "Acceleration (x)",
            "Acceleration (y)",
            "Acceleration (magnitude)",
            "Force (x)",
            "Force (y)",
            "Force (magnitude)",
            "Momentum (x)",
            "Momentum (y)",
            "Angular momentum",
            "Linear kinetic energy",
            "Angular kinetic energy",
            "Kinetic energy (sum)",
            "Potential gravitational energy",
            "Potential energy (sum)",
            "Energy (sum)"
        ]
        self.axis_controls["x"] = pygame_gui.elements.UIDropDownMenu(
            options_list=axis_options,
            starting_option=axis_options[0],
            relative_rect=pygame.Rect(10, 90, 180, 30),
            manager=self.manager,
            container=self.window
        )
        self.axis_controls["y"] = pygame_gui.elements.UIDropDownMenu(
            options_list=axis_options,
            starting_option=axis_options[1],
            relative_rect=pygame.Rect(10, 130, 180, 30),
            manager=self.manager,
            container=self.window
        )

    def _create_slider_controls(self):
        # Time span slider
        y_offset = 200
        self.slider_controls["time_span"] = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(10, y_offset, 180, 20),
            start_value=self.time_span,
            value_range=(0.1, 10.0),
            manager=self.manager,
            container=self.window
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_offset - 25, 180, 20),
            text="Time span (s)",
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(class_id="@label", object_id="#slider_label")
        )
        self.slider_controls["time_span_entry"] = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(10, y_offset + 25, 180, 25),
            initial_text=f"{self.time_span:.2f}",
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(class_id="@entry_line", object_id="#time_span_entry")
        )

        # Smoothing slider
        y_offset = 260
        self.slider_controls["smoothing"] = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(10, y_offset, 180, 20),
            start_value=self.smoothing,
            value_range=(0.0, 1.0),
            manager=self.manager,
            container=self.window
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_offset - 25, 180, 20),
            text="Smoothing",
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(class_id="@label", object_id="#slider_label")
        )
        self.slider_controls["smoothing_entry"] = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(10, y_offset + 25, 180, 25),
            initial_text=f"{self.smoothing:.2f}",
            manager=self.manager,
            container=self.window,
            object_id=pygame_gui.core.ObjectID(class_id="@entry_line", object_id="#smoothing_entry")
        )

    def _create_checkboxes(self):
        self.checkboxes["show_axes"] = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 300, 20, 20),
            text="Show axes",
            manager=self.manager,
            container=self.window,
            initial_state=self.show_axes
        )
        self.checkboxes["show_legends"] = pygame_gui.elements.UICheckBox(
            relative_rect=pygame.Rect(10, 330, 20, 20),
            text="Show legends",
            manager=self.manager,
            container=self.window,
            initial_state=self.show_legends
        )

    def _create_save_buttons(self):
        self.save_image_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 370, 180, 30),
            text="Save as image file",
            manager=self.manager,
            container=self.window
        )
        self.save_csv_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 400, 180, 30),
            text="Save as CSV file",
            manager=self.manager,
            container=self.window
        )

    def _resize_plot_area(self):
        new_w, new_h = self.window.rect.size[0]-225, self.window.rect.size[1]-60
        self.plotter.surface_size = (new_w, new_h)
        self.plotter.surface = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
        self.plot_image.set_dimensions((new_w, new_h))
        self.plot_image.set_image(self.plotter.get_surface())

    def handle_event(self, event: pygame.event.Event):
        if not self.is_open(): return
        if event.type == pygame_gui.UI_WINDOW_RESIZED and event.ui_element == self.window:
            self._resize_plot_area()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons["toggle_mode"]:
                self.plotter.set_overlay_mode(not self.plotter.overlay_mode)
            elif event.ui_element == self.buttons["clear_data"]:
                self.plotter.clear_data()
            elif event.ui_element == self.save_image_btn:
                self._save_as_image()
            elif event.ui_element == self.save_csv_btn:
                self._save_as_csv()
        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.axis_controls["x"]:
                self.current_x_axis = self._get_axis_key(event.text)
                self.plotter.clear_data()
            elif event.ui_element == self.axis_controls["y"]:
                self.current_y_axis = self._get_axis_key(event.text)
                self.plotter.clear_data()
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.slider_controls["time_span"]:
                self.time_span = event.value
                self.slider_controls["time_span_entry"].set_text(f"{self.time_span:.2f}")
            elif event.ui_element == self.slider_controls["smoothing"]:
                self.smoothing = event.value
                self.slider_controls["smoothing_entry"].set_text(f"{self.smoothing:.2f}")
                self.plotter.smoothing_factor = self.smoothing
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.slider_controls["time_span_entry"]:
                try:
                    val = float(event.text)
                    val = max(0.1, min(10.0, val))
                    self.time_span = val
                    self.slider_controls["time_span"].set_current_value(val)
                except ValueError:
                    self.slider_controls["time_span_entry"].set_text(f"{self.time_span:.2f}")
            elif event.ui_element == self.slider_controls["smoothing_entry"]:
                try:
                    val = float(event.text)
                    val = max(0.0, min(1.0, val))
                    self.smoothing = val
                    self.slider_controls["smoothing"].set_current_value(val)
                    self.plotter.smoothing_factor = self.smoothing
                except ValueError:
                    self.slider_controls["smoothing_entry"].set_text(f"{self.smoothing:.2f}")
        elif event.type == pygame_gui.UI_CHECK_BOX_CHECKED or event.type == pygame_gui.UI_CHECK_BOX_UNCHECKED:
            if event.ui_element == self.checkboxes["show_axes"]:
                self.show_axes = event.ui_element.checked
            elif event.ui_element == self.checkboxes["show_legends"]:
                self.show_legends = event.ui_element.checked

    def _get_axis_key(self, label: str) -> str:
        mapping = {
            "Time": "time",
            "Position (x)": "pos_x",
            "Position (y)": "pos_y",
            "Velocity": "vel",
            "Velocity (x)": "vel_x",
            "Velocity (y)": "vel_y",
            "Angular Velocity": "ang_vel",
            "Acceleration (x)": "acc_x",
            "Acceleration (y)": "acc_y",
            "Acceleration (magnitude)": "acc_mag",
            "Force (x)": "force_x",
            "Force (y)": "force_y",
            "Force (magnitude)": "force_mag",
            "Momentum (x)": "mom_x",
            "Momentum (y)": "mom_y",
            "Angular momentum": "ang_mom",
            "Linear kinetic energy": "lin_kin_en",
            "Angular kinetic energy": "ang_kin_en",
            "Kinetic energy (sum)": "kin_en_sum",
            "Potential gravitational energy": "pot_grav_en",
            "Potential energy (sum)": "pot_en_sum",
            "Energy (sum)": "en_sum"
        }
        return mapping.get(label, "time")

    def _save_as_image(self):
        try:
            root = tk.Tk()
            root.withdraw()
            fp = filedialog.asksaveasfilename(
                title="Save Plot as Image",
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            root.destroy()
            if fp:
                pygame.image.save(self.plotter.surface, fp)
        except Exception as e:
            Debug.log_exception(f"Failed to save plot image: {e}", "Plotter")

    def _save_as_csv(self):
        try:
            root = tk.Tk()
            root.withdraw()
            fp = filedialog.asksaveasfilename(
                title="Save Plot Data as CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            root.destroy()
            if not fp: return
            key = f"{self.current_y_axis} / {self.current_x_axis}"
            xs = self.plotter.x_data.get(key, [])
            ys = self.plotter.data.get(key, [])
            with open(fp, 'w', newline='') as f:
                wr = csv.writer(f)
                wr.writerow([self.current_x_axis, self.current_y_axis])
                wr.writerows(zip(xs, ys))
        except Exception as e:
            Debug.log_exception(f"Failed to save plot CSV: {e}", "Plotter")

    def is_open(self): return self.window and self.window.alive()
    def show(self): self.window.show()
    def hide(self): self.window.hide()
    def close(self):
        try:
            if self._wrapper and hasattr(self._wrapper, "unregister_plotter_window"):
                self._wrapper.unregister_plotter_window(self)
        except Exception:
            Debug.log_exception("Failed to unregister ContextPlotterWindow from UI wrapper.", "GUI")
        if self.window:
            self.window.kill()
    def add_data(self, key, y, x=None, group="General"): self.plotter.add_data(key, y, x, group)
    def clear_data(self): self.plotter.clear_data()

    def update(self, dt: float, sim_time: float):
        if not self.is_open(): return
        if self.tracked_object:
            self.fetch_and_add_data(sim_time)
        self.plot_image.set_image(self.plotter.get_surface())