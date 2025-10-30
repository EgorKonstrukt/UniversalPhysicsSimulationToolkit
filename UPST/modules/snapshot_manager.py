import pickle
import pymunk
from UPST.config import config
from UPST.debug.debug_manager import Debug

from UPST.misc import surface_to_bytes, bytes_to_surface, ensure_rgba_surface


class SnapshotManager:
    def __init__(self, physics_manager, camera):
        self.physics_manager = physics_manager
        self.camera = camera
        self._texture_byte_cache = {}  # path -> bytes

    def create_snapshot(self):
        bodies_data = []
        if config.snapshot.save_object_positions:
            sim_bodies = [b for b in self.physics_manager.space.bodies if b is not self.physics_manager.static_body]
            body_map = {b: i for i, b in enumerate(sim_bodies)}
            for body in sim_bodies:
                shapes_data = []
                for shape in body.shapes:
                    sd = {
                        "type": shape.__class__.__name__,
                        "friction": float(getattr(shape, "friction", 0.5)),
                        "elasticity": float(getattr(shape, "elasticity", 0.0)),
                        "color": getattr(shape, "color", (200, 200, 200, 255)),
                    }
                    if isinstance(shape, pymunk.Circle):
                        sd["radius"] = float(shape.radius)
                        sd["offset"] = tuple(getattr(shape, "offset", (0.0, 0.0)))
                    elif isinstance(shape, pymunk.Poly):
                        sd["vertices"] = [tuple(v) for v in shape.get_vertices()]
                    elif isinstance(shape, pymunk.Segment):
                        sd["a"] = tuple(shape.a)
                        sd["b"] = tuple(shape.b)
                        sd["radius"] = float(shape.radius)
                    shapes_data.append(sd)
                texture_path = getattr(body, 'texture_path', None)
                tex_bytes = None
                tex_size = None
                if texture_path and hasattr(self.physics_manager.app, 'renderer'):
                    renderer = self.physics_manager.app.renderer
                    surf = renderer._get_texture(texture_path)
                    if surf:
                        tex_bytes = surface_to_bytes(surf)
                        tex_size = surf.get_size()
                bd = {
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
                bodies_data.append(bd)

        constraints_data = []
        if config.snapshot.save_object_positions:
            sim_bodies = [b for b in self.physics_manager.space.bodies if b is not self.physics_manager.static_body]
            body_map = {b: i for i, b in enumerate(sim_bodies)}
            for c in list(self.physics_manager.space.constraints):
                if c.a not in body_map or c.b not in body_map:
                    continue
                cd = {"type": c.__class__.__name__, "a": body_map[c.a], "b": body_map[c.b]}
                if isinstance(c, pymunk.PinJoint):
                    cd.update({"anchor_a": c.anchor_a, "anchor_b": c.anchor_b})
                elif isinstance(c, pymunk.PivotJoint):
                    cd.update({"anchor": c.anchor_a})
                elif isinstance(c, pymunk.DampedSpring):
                    cd.update({
                        "anchor_a": c.anchor_a,
                        "anchor_b": c.anchor_b,
                        "rest_length": float(c.rest_length),
                        "stiffness": float(c.stiffness),
                        "damping": float(c.damping),
                    })
                elif isinstance(c, pymunk.SimpleMotor):
                    cd.update({"rate": float(c.rate)})
                elif isinstance(c, pymunk.GearJoint):
                    cd.update({"phase": float(c.phase), "ratio": float(c.ratio)})
                elif isinstance(c, pymunk.SlideJoint):
                    cd.update({"anchor_a": c.anchor_a, "anchor_b": c.anchor_b, "min": float(c.min), "max": float(c.max)})
                elif isinstance(c, pymunk.RotaryLimitJoint):
                    cd.update({"min": float(c.min), "max": float(c.max)})
                constraints_data.append(cd)

        static_lines_data = []
        if config.snapshot.save_object_positions:
            for line in list(self.physics_manager.static_lines):
                ld = {
                    "friction": float(getattr(line, "friction", 0.5)),
                    "elasticity": float(getattr(line, "elasticity", 0.0)),
                    "color": getattr(line, "color", (200, 200, 200, 255))
                }
                if isinstance(line, pymunk.Poly):
                    ld["type"] = "Poly"
                    ld["vertices"] = [tuple(v) for v in line.get_vertices()]
                elif isinstance(line, pymunk.Segment):
                    ld["type"] = "Segment"
                    ld["a"] = tuple(line.a)
                    ld["b"] = tuple(line.b)
                    ld["radius"] = float(line.radius)
                static_lines_data.append(ld)

        snapshot = {
            "iterations": int(self.physics_manager.space.iterations),
            "sim_freq": int(self.physics_manager.simulation_frequency),
            "gravity": tuple(self.physics_manager.space.gravity),
            "damping_linear": float(self.physics_manager.space.damping),
            "damping_angular": float(getattr(self.physics_manager, "_angular_damping", 0.0)),
            "sleep_time_threshold": float(self.physics_manager.space.sleep_time_threshold),
            "collision_slop": float(self.physics_manager.space.collision_slop),
            "collision_bias": float(self.physics_manager.space.collision_bias),
        }

        if config.snapshot.save_object_positions:
            snapshot.update({
                "bodies": bodies_data,
                "constraints": constraints_data,
                "static_lines": static_lines_data,
            })

        if config.snapshot.save_camera_position:
            cam_tr = (
                getattr(getattr(self.camera, "translation", None), "tx", 0.0),
                getattr(getattr(self.camera, "translation", None), "ty", 0.0),
            )
            snapshot.update({
                "camera_scaling": float(getattr(self.camera, "scaling", 1.0)),
                "camera_translation": cam_tr,
            })

        return pickle.dumps(snapshot)

    def load_snapshot(self, snapshot_bytes):
        data = pickle.loads(snapshot_bytes)
        self.physics_manager.delete_all()
        self.physics_manager.set_iterations(int(data.get("iterations", config.physics.iterations)))
        self.physics_manager.set_simulation_frequency(int(data.get("sim_freq", config.physics.simulation_frequency)))
        self.physics_manager.space.gravity = tuple(data.get("gravity", (0.0, 900.0)))
        self.physics_manager.set_damping(
            float(data.get("damping_linear", 1.0)),
            float(data.get("damping_angular", 0.0))
        )
        self.physics_manager.set_sleep_time_threshold(
            float(data.get("sleep_time_threshold", config.physics.sleep_time_threshold))
        )
        self.physics_manager.set_collision_slop(
            float(data.get("collision_slop", 0.5))
        )
        self.physics_manager.set_collision_bias(
            float(data.get("collision_bias", pow(1.0 - 0.1, 60.0)))
        )

        if config.snapshot.save_camera_position and "camera_translation" in data:
            cam_tr = data["camera_translation"]
            self.camera.translation = pymunk.Transform(1, 0, 0, 1, float(cam_tr[0]), float(cam_tr[1]))
            cam_scale = float(data.get("camera_scaling", getattr(self.camera, "scaling", 1.0)))
            self.camera.scaling = cam_scale
            if hasattr(self.camera, "target_scaling"):
                self.camera.target_scaling = cam_scale

        loaded_bodies = []
        if config.snapshot.save_object_positions and "bodies" in data:
            for bd in data["bodies"]:
                body_type = int(bd.get("body_type", int(pymunk.Body.DYNAMIC)))
                bt = pymunk.Body(body_type=body_type)
                if bt.body_type == pymunk.Body.DYNAMIC:
                    bt.mass = float(bd.get("mass", 1.0))
                    bt.moment = float(bd.get("moment", 1.0))
                bt.position = pymunk.Vec2d(*bd.get("position", (0.0, 0.0)))
                bt.angle = float(bd.get("angle", 0.0))
                bt.velocity = pymunk.Vec2d(*bd.get("velocity", (0.0, 0.0)))
                bt.angular_velocity = float(bd.get("angular_velocity", 0.0))

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
                    line = pymunk.Segment(self.physics_manager.static_body, pymunk.Vec2d(*ld["a"]),
                                          pymunk.Vec2d(*ld["b"]), float(ld["radius"]))
                if line is None:
                    continue
                line.friction = float(ld.get("friction", 0.5))
                line.elasticity = float(ld.get("elasticity", 0.0))
                line.color = tuple(ld.get("color", (200, 200, 200, 255)))
                self.physics_manager.static_lines.append(line)
                self.physics_manager.space.add(line)

        if (hasattr(self.physics_manager.app, 'renderer') and
                config.snapshot.save_object_positions and "bodies" in data):
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

        Debug.log_succes(message="Snapshot restored.", category="SnapshotManager")