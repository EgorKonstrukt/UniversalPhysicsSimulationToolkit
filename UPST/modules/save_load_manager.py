import tkinter as tk
from tkinter import filedialog
import pickle
import traceback
import pymunk
import gzip
import lzma

from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.misc import surface_to_bytes, bytes_to_surface
from UPST.modules.undo_redo_manager import get_undo_redo


class SaveLoadManager:
    def __init__(self, physics_manager, camera, ui_manager, sound_manager):
        self.physics_manager = physics_manager
        self.camera = camera
        self.ui_manager = ui_manager
        self.sound_manager = sound_manager
        self.undo_redo = get_undo_redo()

    def save_world(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(defaultextension=".ngsv", filetypes=[("Newgodoo Save File", "*.ngsv")])
        if not file_path:
            Debug.log_warning("Canceled...", "SaveLoadManager")
            return
        try:
            data_to_save = self._prepare_save_data()
            if config.save_load.enable_compression:
                if config.save_load.compression_method == "lzma":
                    with lzma.open(file_path, "wb") as f:
                        pickle.dump(data_to_save, f)
                else:
                    with gzip.open(file_path, "wb") as f:
                        pickle.dump(data_to_save, f)
            else:
                with open(file_path, "wb") as f:
                    pickle.dump(data_to_save, f)
            self.ui_manager.console_window.add_output_line_to_log("Save successful!")
            Debug.log_succes(message="Saving! file name: " + str(file_path), category="SaveLoadManager")
        except Exception as e:
            self.ui_manager.console_window.add_output_line_to_log(f"Save error: {e}")
            Debug.log_exception(message="Error! file name: " + str(file_path), category="SaveLoadManager")

    def _prepare_save_data(self):
        data_to_save = {
            "iterations": int(self.physics_manager.space.iterations),
            "sim_freq": int(self.physics_manager.simulation_frequency),
            "gravity": tuple(self.physics_manager.space.gravity),
            "damping_linear": float(self.physics_manager.space.damping),
            "damping_angular": float(getattr(self.physics_manager, "_angular_damping", 0.0)),
            "sleep_time_threshold": float(self.physics_manager.space.sleep_time_threshold),
            "collision_slop": float(self.physics_manager.space.collision_slop),
            "collision_bias": float(self.physics_manager.space.collision_bias),
            "camera_translation": (
                getattr(getattr(self.camera, "translation", None), "tx", 0.0),
                getattr(getattr(self.camera, "translation", None), "ty", 0.0),
            ),
            "camera_scaling": float(getattr(self.camera, "scaling", 1.0)),
            "bodies": [],
            "constraints": [],
            "static_lines": [],
        }

        sim_bodies = [b for b in self.physics_manager.space.bodies if b is not self.physics_manager.static_body]
        body_map = {b: i for i, b in enumerate(sim_bodies)}

        for body in sim_bodies:
            shapes_data = []
            for shape in body.shapes:
                shape_data = {
                    "type": shape.__class__.__name__,
                    "friction": float(getattr(shape, "friction", 0.5)),
                    "elasticity": float(getattr(shape, "elasticity", 0.0)),
                    "color": getattr(shape, "color", (200, 200, 200, 255)),
                }
                if isinstance(shape, pymunk.Circle):
                    shape_data["radius"] = float(shape.radius)
                    shape_data["offset"] = tuple(getattr(shape, "offset", (0.0, 0.0)))
                elif isinstance(shape, pymunk.Poly):
                    shape_data["vertices"] = [tuple(v) for v in shape.get_vertices()]
                elif isinstance(shape, pymunk.Segment):
                    shape_data["a"] = tuple(shape.a)
                    shape_data["b"] = tuple(shape.b)
                    shape_data["radius"] = float(shape.radius)
                shapes_data.append(shape_data)

            tex_surface = None
            if hasattr(self.physics_manager.app, 'renderer'):
                renderer = self.physics_manager.app.renderer
                tex_surface = renderer._get_texture(getattr(body, 'texture_path', None))

            texture_path = getattr(body, 'texture_path', None)
            tex_bytes = surface_to_bytes(tex_surface)
            tex_size = None
            if tex_surface:
                tex_size = tex_surface.get_size()

            body_data = {
                "position": tuple(body.position),
                "angle": float(body.angle),
                "velocity": tuple(body.velocity),
                "angular_velocity": float(body.angular_velocity),
                "mass": float(getattr(body, "mass", 1.0)),
                "moment": float(getattr(body, "moment", 1.0)),
                "body_type": int(body.body_type),
                "shapes": shapes_data,
                "texture_path": texture_path,
                "texture_bytes": tex_bytes,
                "texture_size": tex_size,
                "texture_scale": getattr(body, "texture_scale", 1.0),
                "stretch_texture": getattr(body, "stretch_texture", True),
            }
            data_to_save["bodies"].append(body_data)

        for c in list(self.physics_manager.space.constraints):
            if c.a not in body_map or c.b not in body_map:
                continue
            cd = {"type": c.__class__.__name__, "a": body_map[c.a], "b": body_map[c.b]}
            if isinstance(c, pymunk.PinJoint):
                cd.update({"anchor_a": c.anchor_a, "anchor_b": c.anchor_b})
            elif isinstance(c, pymunk.PivotJoint):
                cd.update({"anchor": c.anchor_a})
            elif isinstance(c, pymunk.DampedSpring):
                cd.update(
                    {
                        "anchor_a": c.anchor_a,
                        "anchor_b": c.anchor_b,
                        "rest_length": float(c.rest_length),
                        "stiffness": float(c.stiffness),
                        "damping": float(c.damping),
                    }
                )
            elif isinstance(c, pymunk.SimpleMotor):
                cd.update({"rate": float(c.rate)})
            elif isinstance(c, pymunk.GearJoint):
                cd.update({"phase": float(c.phase), "ratio": float(c.ratio)})
            elif isinstance(c, pymunk.SlideJoint):
                cd.update({"anchor_a": c.anchor_a, "anchor_b": c.anchor_b, "min": float(c.min), "max": float(c.max)})
            elif isinstance(c, pymunk.RotaryLimitJoint):
                cd.update({"min": float(c.min), "max": float(c.max)})
            data_to_save["constraints"].append(cd)

        for line in list(self.physics_manager.static_lines):
            ld = {"friction": float(getattr(line, "friction", 0.5)),
                  "elasticity": float(getattr(line, "elasticity", 0.0)),
                  "color": getattr(line, "color", (200, 200, 200, 255))}
            if isinstance(line, pymunk.Poly):
                ld["type"] = "Poly"
                ld["vertices"] = [tuple(v) for v in line.get_vertices()]
            elif isinstance(line, pymunk.Segment):
                ld["type"] = "Segment"
                ld["a"] = tuple(line.a)
                ld["b"] = tuple(line.b)
                ld["radius"] = float(line.radius)
            else:
                continue
            data_to_save["static_lines"].append(ld)

        return data_to_save

    def load_world(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("Newgodoo Save File", "*.ngsv")])
        if not file_path:
            Debug.log_warning("Canceled..." + str(file_path), "SaveLoadManager")
            return
        try:
            data = self._load_data_with_fallback(file_path)
            self._apply_loaded_data(data)
            self.ui_manager.console_window.add_output_line_to_log("Load successful!")
            Debug.log_succes(message="Loaded! file name: " + str(file_path), category="SaveLoadManager")
        except Exception as e:
            self.ui_manager.console_window.add_output_line_to_log(f"Load error: {e}")
            traceback.print_exc()
            Debug.log_exception(message="Error while loading! file name: " + str(file_path), category="SaveLoadManager")

    def _load_data_with_fallback(self, file_path):
        methods = [
            ("lzma", lambda fp: lzma.open(fp, "rb")),
            ("gzip", lambda fp: gzip.open(fp, "rb")),
            ("none", lambda fp: open(fp, "rb"))
        ]

        for method_name, opener in methods:
            try:
                with opener(file_path) as f:
                    return pickle.load(f)
            except (lzma.LZMAError, gzip.BadGzipFile, UnicodeDecodeError, EOFError):
                continue
        raise Exception("Unable to load file with any compression method")

    def _apply_loaded_data(self, data):
        self.physics_manager.delete_all()

        self.physics_manager.set_iterations(int(data.get("iterations", config.physics.iterations)))
        self.physics_manager.set_simulation_frequency(int(data.get("sim_freq", config.physics.simulation_frequency)))
        self.physics_manager.space.gravity = tuple(data.get("gravity", (0.0, 900.0)))
        self.physics_manager.set_damping(float(data.get("damping_linear", 1.0)),
                                         float(data.get("damping_angular", 0.0)))
        self.physics_manager.set_sleep_time_threshold(
            float(data.get("sleep_time_threshold", config.physics.sleep_time_threshold)))
        self.physics_manager.set_collision_slop(float(data.get("collision_slop", 0.5)))
        self.physics_manager.set_collision_bias(float(data.get("collision_bias", pow(1.0 - 0.1, 60.0))))

        cam_tr = data.get("camera_translation", None)
        if cam_tr is not None and isinstance(cam_tr, (list, tuple)) and len(cam_tr) == 2:
            self.camera.translation = pymunk.Transform(1, 0, 0, 1, float(cam_tr[0]), float(cam_tr[1]))
        cam_scale = float(data.get("camera_scaling", getattr(self.camera, "scaling", 1.0)))
        self.camera.scaling = cam_scale
        if hasattr(self.camera, "target_scaling"):
            self.camera.target_scaling = cam_scale

        loaded_bodies = []
        for bd in data.get("bodies", []):
            body_type = int(bd.get("body_type", int(pymunk.Body.DYNAMIC)))
            bt = pymunk.Body(body_type=body_type)
            if bt.body_type == pymunk.Body.DYNAMIC:
                bt.mass = float(bd.get("mass", 1.0))
                bt.moment = float(bd.get("moment", 1.0))
            bt.position = pymunk.Vec2d(*bd.get("position", (0.0, 0.0)))
            bt.angle = float(bd.get("angle", 0.0))
            bt.velocity = pymunk.Vec2d(*bd.get("velocity", (0.0, 0.0)))
            bt.angular_velocity = float(bd.get("angular_velocity", 0.0))
            bt.texture_path = bd.get("texture_path")
            bt.texture_bytes = bd.get("texture_bytes")
            bt.texture_size = bd.get("texture_size")
            bt.texture_scale = float(bd.get("texture_scale", 1.0))
            bt.stretch_texture = bool(bd.get("stretch_texture", True))

            shapes = []
            for sd in bd.get("shapes", []):
                st = sd.get("type", "")
                shp = None
                if st == "Circle":
                    shp = pymunk.Circle(bt, float(sd["radius"]), tuple(sd.get("offset", (0.0, 0.0))))
                elif st == "Poly":
                    shp = pymunk.Poly(bt, [pymunk.Vec2d(*v) for v in sd["vertices"]])
                elif st == "Segment":
                    shp = pymunk.Segment(bt, pymunk.Vec2d(*sd["a"]), pymunk.Vec2d(*sd["b"]), float(sd["radius"]))
                if shp is None:
                    continue
                shp.friction = float(sd.get("friction", 0.5))
                shp.elasticity = float(sd.get("elasticity", 0.0))
                shp.color = tuple(sd.get("color", (200, 200, 200, 255)))
                shapes.append(shp)

            if shapes:
                self.physics_manager.space.add(bt, *shapes)
            else:
                self.physics_manager.space.add(bt)
            loaded_bodies.append(bt)

        for cd in data.get("constraints", []):
            a = loaded_bodies[cd["a"]]
            b = loaded_bodies[cd["b"]]
            ctype = cd["type"]
            c = None
            if ctype == "PinJoint":
                c = pymunk.PinJoint(a, b, cd["anchor_a"], cd["anchor_b"])
            elif ctype == "PivotJoint":
                c = pymunk.PivotJoint(a, b, cd["anchor"])
            elif ctype == "DampedSpring":
                c = pymunk.DampedSpring(a, b, cd["anchor_a"], cd["anchor_b"], float(cd["rest_length"]),
                                        float(cd["stiffness"]), float(cd["damping"]))
            elif ctype == "SimpleMotor":
                c = pymunk.SimpleMotor(a, b, float(cd["rate"]))
            elif ctype == "GearJoint":
                c = pymunk.GearJoint(a, b, float(cd["phase"]), float(cd["ratio"]))
            elif ctype == "SlideJoint":
                c = pymunk.SlideJoint(a, b, cd["anchor_a"], cd["anchor_b"], float(cd["min"]), float(cd["max"]))
            elif ctype == "RotaryLimitJoint":
                c = pymunk.RotaryLimitJoint(a, b, float(cd["min"]), float(cd["max"]))
            if c:
                self.physics_manager.add_constraint(c)

        for ld in data.get("static_lines", []):
            line = None
            if ld.get("type") == "Poly":
                line = pymunk.Poly(self.physics_manager.static_body, [pymunk.Vec2d(*v) for v in ld["vertices"]])
            elif ld.get("type") == "Segment":
                line = pymunk.Segment(self.physics_manager.static_body, pymunk.Vec2d(*ld["a"]), pymunk.Vec2d(*ld["b"]),
                                      float(ld["radius"]))
            if line is None:
                continue
            line.friction = float(ld.get("friction", 0.5))
            line.elasticity = float(ld.get("elasticity", 0.0))
            line.color = tuple(ld.get("color", (200, 200, 200, 255)))
            self.physics_manager.static_lines.append(line)
            self.physics_manager.space.add(line)

        if (hasattr(self.physics_manager.app, 'renderer') and
                "bodies" in data):
            renderer = self.physics_manager.app.renderer
            unique_textures = {}
            for bd in data["bodies"]:
                tex_bytes = bd.get("texture_bytes")
                tex_size = bd.get("texture_size")
                if tex_bytes and tex_size:
                    if tex_bytes not in unique_textures:
                        surf = bytes_to_surface(tex_bytes, tex_size)
                        if surf:
                            unique_textures[tex_bytes] = surf
            renderer.texture_cache.clear()
            for tex_bytes, surf in unique_textures.items():
                renderer.texture_cache[tex_bytes] = surf
        self.undo_redo.take_snapshot()

    def set_compression_enabled(self, enabled):
        self.enable_compression = bool(enabled)

    def set_compression_method(self, method):
        if method in ["gzip", "lzma", "none"]:
            self.compression_method = method

    def is_compression_enabled(self):
        return self.enable_compression

    def get_compression_method(self):
        return self.compression_method