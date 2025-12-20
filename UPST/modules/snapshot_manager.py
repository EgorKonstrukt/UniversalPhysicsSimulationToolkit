import os
import pickle
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import pymunk
from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.utils import surface_to_bytes, bytes_to_surface


class SnapshotManager:

    def __init__(self, physics_manager, camera, script_manager):
        self.physics_manager = physics_manager
        self.camera = camera
        self.script_manager = script_manager



    def capture_snapshot_data(self) -> dict:
        return self._collect_snapshot_data()

    def create_snapshot(self) -> bytes:
        data = self.capture_snapshot_data()

        #TODO:сделать запись только последнего снапшота

        return pickle.dumps(data)

    #TODO: Исправить перезапись тяжелых изображений и кода, проверять наличие перед записью
    def _collect_snapshot_data(self):
        data = {
            "iterations": int(self.physics_manager.space.iterations),
            "sim_freq": int(self.physics_manager.simulation_frequency),
            "gravity": tuple(self.physics_manager.space.gravity),
            "damping_linear": float(self.physics_manager.space.damping),
            "damping_angular": float(getattr(self.physics_manager, "_angular_damping", 0.0)),
            "sleep_time_threshold": float(self.physics_manager.space.sleep_time_threshold),
            "collision_slop": float(self.physics_manager.space.collision_slop),
            "collision_bias": float(self.physics_manager.space.collision_bias),
            "scripts": self.script_manager.serialize_for_save(),
        }

        if config.snapshot.save_camera_position:
            tr = self.camera.translation
            data.update({
                "camera_scaling": float(getattr(self.camera, "scaling", 1.0)),
                "camera_translation": (tr.tx if tr else 0.0, tr.ty if tr else 0.0),
            })

        if config.snapshot.save_object_positions:
            sim_bodies = [b for b in self.physics_manager.space.bodies if b is not self.physics_manager.static_body]
            bodies_data = []
            for body in sim_bodies:
                if not hasattr(body, '_script_uuid'):
                    body._script_uuid = uuid.uuid4()
                shapes_data = []
                for shape in body.shapes:
                    sd = {
                        "type": shape.__class__.__name__,
                        "friction": float(getattr(shape, "friction", 0.5)),
                        "elasticity": float(getattr(shape, "elasticity", 0.0)),
                        "color": getattr(shape, "color", (200, 200, 200, 255)),
                    }
                    if isinstance(shape, pymunk.Circle):
                        sd.update({"radius": float(shape.radius), "offset": tuple(getattr(shape, "offset", (0.0, 0.0)))})
                    elif isinstance(shape, pymunk.Poly):
                        sd["vertices"] = [tuple(v) for v in shape.get_vertices()]
                    elif isinstance(shape, pymunk.Segment):
                        sd.update({"a": tuple(shape.a), "b": tuple(shape.b), "radius": float(shape.radius)})
                    shapes_data.append(sd)

                tex_bytes, tex_size = None, None
                if hasattr(self.physics_manager.app, 'renderer'):
                    surf = self.physics_manager.app.renderer._get_texture(getattr(body, 'texture_path', None))
                    if surf:
                        tex_bytes, tex_size = surface_to_bytes(surf), surf.get_size()

                bodies_data.append({
                    "_script_uuid": str(body._script_uuid),
                    "name": str(body.name),
                    "position": tuple(body.position),
                    "angle": float(body.angle),
                    "velocity": tuple(body.velocity),
                    "angular_velocity": float(body.angular_velocity),
                    "mass": float(getattr(body, "mass", 1.0)),
                    "moment": float(getattr(body, "moment", 1.0)),
                    "body_type": int(body.body_type),
                    "shapes": shapes_data,
                    "texture_path": getattr(body, "texture_path", None),
                    "texture_bytes": tex_bytes,
                    "texture_size": tex_size,
                    "texture_scale": float(getattr(body, "texture_scale", 1.0)),
                    "stretch_texture": bool(getattr(body, "stretch_texture", True)),
                })

            constraints_data = []
            body_map = {b: i for i, b in enumerate(sim_bodies)}
            for c in self.physics_manager.space.constraints:
                if c.a not in body_map or c.b not in body_map:
                    continue
                cd = {"type": c.__class__.__name__, "a": body_map[c.a], "b": body_map[c.b]}
                if isinstance(c, pymunk.PinJoint):
                    cd.update({"anchor_a": tuple(c.anchor_a), "anchor_b": tuple(c.anchor_b)})
                elif isinstance(c, pymunk.PivotJoint):
                    cd["anchor"] = tuple(c.anchor_a)
                elif isinstance(c, pymunk.DampedSpring):
                    cd.update({"anchor_a": tuple(c.anchor_a), "anchor_b": tuple(c.anchor_b), "rest_length": float(c.rest_length),
                               "stiffness": float(c.stiffness), "damping": float(c.damping)})
                elif isinstance(c, pymunk.SimpleMotor):
                    cd["rate"] = float(c.rate)
                elif isinstance(c, pymunk.GearJoint):
                    cd.update({"phase": float(c.phase), "ratio": float(c.ratio)})
                elif isinstance(c, pymunk.SlideJoint):
                    cd.update({"anchor_a": tuple(c.anchor_a), "anchor_b": tuple(c.anchor_b), "min": float(c.min), "max": float(c.max)})
                elif isinstance(c, pymunk.RotaryLimitJoint):
                    cd.update({"min": float(c.min), "max": float(c.max)})
                constraints_data.append(cd)

            static_lines_data = []
            for line in self.physics_manager.static_lines:
                ld = {
                    "friction": float(getattr(line, "friction", 0.5)),
                    "elasticity": float(getattr(line, "elasticity", 0.0)),
                    "color": getattr(line, "color", (200, 200, 200, 255)),
                }
                if isinstance(line, pymunk.Poly):
                    ld.update({"type": "Poly", "vertices": [tuple(v) for v in line.get_vertices()]})
                elif isinstance(line, pymunk.Segment):
                    ld.update({"type": "Segment", "a": tuple(line.a), "b": tuple(line.b), "radius": float(line.radius)})
                static_lines_data.append(ld)

            data.update({
                "bodies": bodies_data,
                "constraints": constraints_data,
                "static_lines": static_lines_data,
            })

        return data

    def load_snapshot(self, snapshot_bytes):
        data = pickle.loads(snapshot_bytes)
        self.physics_manager.delete_all()
        pm = self.physics_manager
        pm.set_iterations(int(data.get("iterations", config.physics.iterations)))
        pm.set_simulation_frequency(int(data.get("sim_freq", config.physics.simulation_frequency)))
        pm.space.gravity = tuple(data.get("gravity", (0.0, 900.0)))
        pm.set_damping(float(data.get("damping_linear", 1.0)), float(data.get("damping_angular", 0.0)))
        pm.set_sleep_time_threshold(float(data.get("sleep_time_threshold", config.physics.sleep_time_threshold)))
        pm.set_collision_slop(float(data.get("collision_slop", 0.5)))
        pm.set_collision_bias(float(data.get("collision_bias", pow(1.0 - 0.1, 60.0))))

        if config.snapshot.save_camera_position and "camera_translation" in data:
            tx, ty = data["camera_translation"]
            self.camera.translation = pymunk.Transform(1, 0, 0, 1, float(tx), float(ty))
            scale = float(data.get("camera_scaling", getattr(self.camera, "scaling", 1.0)))
            self.camera.scaling = scale
            if hasattr(self.camera, "target_scaling"):
                self.camera.target_scaling = scale

        body_uuid_map = {}
        loaded_bodies = []
        if config.snapshot.save_object_positions and "bodies" in data:
            for bd in data["bodies"]:
                bt = pymunk.Body(body_type=int(bd.get("body_type", pymunk.Body.DYNAMIC)))
                try:
                    bt._script_uuid = uuid.UUID(bd["_script_uuid"])
                except:
                    bt._script_uuid = uuid.uuid4()
                body_uuid_map[bt._script_uuid] = bt

                if bt.body_type == pymunk.Body.DYNAMIC:
                    bt.mass = float(bd.get("mass", 1.0))
                    bt.moment = float(bd.get("moment", 1.0))
                bt.name = bd.get("name",None)
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
                    st = sd["type"]
                    if st == "Circle":
                        shp = pymunk.Circle(bt, float(sd["radius"]), tuple(sd.get("offset", (0.0, 0.0))))
                    elif st == "Poly":
                        shp = pymunk.Poly(bt, [pymunk.Vec2d(*v) for v in sd["vertices"]])
                    elif st == "Segment":
                        shp = pymunk.Segment(bt, pymunk.Vec2d(*sd["a"]), pymunk.Vec2d(*sd["b"]), float(sd["radius"]))
                    else:
                        continue
                    shp.friction = float(sd.get("friction", 0.5))
                    shp.elasticity = float(sd.get("elasticity", 0.0))
                    shp.color = tuple(sd.get("color", (200, 200, 200, 255)))
                    shapes.append(shp)

                pm.space.add(bt, *shapes) if shapes else pm.space.add(bt)
                loaded_bodies.append(bt)

            body_index_map = {i: b for i, b in enumerate(loaded_bodies)}
            for cd in data.get("constraints", []):
                a, b = body_index_map[cd["a"]], body_index_map[cd["b"]]
                ctype = cd["type"]
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
                else:
                    continue
                pm.add_constraint(c)

            for ld in data.get("static_lines", []):
                if ld["type"] == "Poly":
                    line = pymunk.Poly(pm.static_body, [pymunk.Vec2d(*v) for v in ld["vertices"]])
                elif ld["type"] == "Segment":
                    line = pymunk.Segment(pm.static_body, pymunk.Vec2d(*ld["a"]), pymunk.Vec2d(*ld["b"]),
                                          float(ld["radius"]))
                else:
                    continue
                line.friction = float(ld.get("friction", 0.5))
                line.elasticity = float(ld.get("elasticity", 0.0))
                line.color = tuple(ld.get("color", (200, 200, 200, 255)))
                pm.static_lines.append(line)
                pm.space.add(line)

        if hasattr(pm.app, 'renderer') and config.snapshot.save_object_positions:
            cache = pm.app.renderer.texture_cache
            cache.clear()
            for bd in data.get("bodies", []):
                tex_bytes, tex_size = bd.get("texture_bytes"), bd.get("texture_size")
                if tex_bytes and tex_size and tex_bytes not in cache:
                    surf = bytes_to_surface(tex_bytes, tex_size)
                    if surf:
                        cache[tex_bytes] = surf

        str_body_map = {str(uid): body for uid, body in body_uuid_map.items()}
        self.physics_manager.script_manager.deserialize_from_save(data.get("scripts", {}), str_body_map)
        Debug.log_success("Snapshot restored.", category="SnapshotManager")