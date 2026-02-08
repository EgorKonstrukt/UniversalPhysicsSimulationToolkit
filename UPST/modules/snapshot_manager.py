import pickle
import uuid
import pymunk
from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.utils.utils import surface_to_bytes, bytes_to_surface
from UPST.gizmos.gizmos_manager import get_gizmos, GizmoType, GizmoData

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
        if hasattr(self.physics_manager.app, 'console_handler') and hasattr(self.physics_manager.app.console_handler,
                                                                            'graph_manager'):
            graph_mgr = self.physics_manager.app.console_handler.graph_manager
            data["graphs"] = graph_mgr.serialize()
        if hasattr(self.physics_manager.app, 'tool_system'):
            graph_tool = self.physics_manager.app.tool_system.get_tool_by_name('graph')
            if graph_tool and hasattr(graph_tool, 'serialize_for_save'):
                data['graph_tool_state'] = graph_tool.serialize_for_save()

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
                    "name": str(getattr(body, "name", "Body"),),
                    "color": tuple(getattr(body, "color", (200, 200, 200, 255))),
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
                    "center_of_gravity": tuple(body.center_of_gravity),
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
                    cd.update({
                        "anchor_a": tuple(c.anchor_a),
                        "anchor_b": tuple(c.anchor_b),
                        "rest_length": float(c.rest_length),
                        "stiffness": float(c.stiffness),
                        "damping": float(c.damping),
                        "size": float(getattr(c, 'size', 10.0)),
                        "color": getattr(c, 'color', (200, 200, 200, 255))
                    })
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
                    ld["type"] = "Poly"
                    ld["vertices"] = [tuple(v) for v in line.get_vertices()]
                elif isinstance(line, pymunk.Segment):
                    ld["type"] = "Segment"
                    ld["a"] = tuple(line.a)
                    ld["b"] = tuple(line.b)
                    ld["radius"] = float(line.radius)
                else:
                    Debug.log_warning(f"Unknown static line type: {type(line)}, skipped during snapshot.",
                                      "SnapshotManager")
                    continue
                static_lines_data.append(ld)

            data.update({
                "bodies": bodies_data,
                "constraints": constraints_data,
                "static_lines": static_lines_data,
            })
        gizmos_mgr = get_gizmos()
        if gizmos_mgr:
            text_gizmos = []
            all_gizmos_with_persistence = [(g, False) for g in gizmos_mgr.gizmos] + [(g, True) for g in gizmos_mgr.persistent_gizmos]
            for g, is_persistent in all_gizmos_with_persistence:
                if g.gizmo_type == GizmoType.TEXT:
                    owner_id = str(getattr(g.owner, '_script_uuid', None)) if g.owner else None
                    text_gizmos.append({
                        'position': tuple(g.position),
                        'text': g.text,
                        'color': g.color,
                        'background_color': g.background_color,
                        'collision': g.collision,
                        'font_name': g.font_name,
                        'font_size': g.font_size,
                        'font_world_space': g.font_world_space,
                        'world_space': g.world_space,
                        'duration': g.duration,
                        'owner_id': owner_id,
                        'persistent': is_persistent
                    })
            data['text_gizmos'] = text_gizmos
        if hasattr(self.physics_manager.app, 'plugin_manager'):
            plugin_meta = {}
            plugin_configs = {}
            pm = self.physics_manager.app.plugin_manager
            for name, plugin in pm.plugins.items():
                plugin_meta[name] = {"version": plugin.version}
                cfg = getattr(self.physics_manager.app.config, name, None)
                if cfg:
                    from dataclasses import asdict
                    cfg_dict = asdict(cfg)
                    if hasattr(cfg, '_to_dict_custom'):
                        cfg_dict = cfg._to_dict_custom(cfg_dict)
                    plugin_configs[name] = cfg_dict
            data["plugins"] = plugin_meta
            data["plugin_configs"] = plugin_configs
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
        if "graphs" in data and hasattr(self.physics_manager.app, 'console_handler'):
            graph_mgr = self.physics_manager.app.console_handler.graph_manager
            graph_mgr.deserialize(data["graphs"])
        if "graph_tool_state" in data and hasattr(self.physics_manager.app, 'tool_system'):
            graph_tool = self.physics_manager.app.tool_system.get_tool_by_name('graph')
            if graph_tool and hasattr(graph_tool, 'deserialize_from_save'):
                graph_tool.deserialize_from_save(data["graph_tool_state"])
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
                bt.color = bd.get("color",(255,255,255,255))
                bt.position = pymunk.Vec2d(*bd.get("position", (0.0, 0.0)))
                bt.angle = float(bd.get("angle", 0.0))
                bt.velocity = pymunk.Vec2d(*bd.get("velocity", (0.0, 0.0)))
                bt.angular_velocity = float(bd.get("angular_velocity", 0.0))
                bt.texture_path = bd.get("texture_path")
                bt.texture_bytes = bd.get("texture_bytes")
                bt.texture_size = bd.get("texture_size")
                bt.texture_scale = float(bd.get("texture_scale", 1.0))
                bt.stretch_texture = bool(bd.get("stretch_texture", True))
                if bt.body_type == pymunk.Body.DYNAMIC:
                    cog = bd.get("center_of_gravity")
                    if cog:
                        bt.center_of_gravity = pymunk.Vec2d(*cog)

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
                    if "size" in cd:
                        c.size = float(cd["size"])
                    if "color" in cd:
                        c.color = tuple(cd["color"])
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
                if "type" not in ld:
                    Debug.log_warning("Static line entry missing 'type', skipping.", "SnapshotManager")
                    continue
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

        gizmos_mgr = get_gizmos()
        if gizmos_mgr and "text_gizmos" in data:
            gizmos_mgr.clear()
            gizmos_mgr.clear_persistent()

            uuid_map = {str(b._script_uuid): b for b in loaded_bodies if hasattr(b, '_script_uuid')}
            for tg in data['text_gizmos']:
                owner = uuid_map.get(tg['owner_id'], None)
                g = GizmoData(
                    gizmo_type=GizmoType.TEXT,
                    position=pymunk.Vec2d(*tg['position']),
                    text=tg['text'],
                    color=tg['color'],
                    background_color=tg['background_color'],
                    collision=tg['collision'],
                    font_name=tg['font_name'],
                    font_size=tg['font_size'],
                    font_world_space=tg['font_world_space'],
                    world_space=tg['world_space'],
                    duration=tg['duration'],
                    owner=owner
                )
                if tg.get('persistent', True):
                    gizmos_mgr.persistent_gizmos.append(g)
                else:
                    gizmos_mgr.gizmos.append(g)
        plugin_meta = data.get("plugins", {})
        plugin_configs = data.get("plugin_configs", {})
        if hasattr(self.physics_manager.app, 'plugin_manager') and plugin_meta:
            pm = self.physics_manager.app.plugin_manager
            for name, cfg_dict in plugin_configs.items():
                if not hasattr(self.physics_manager.app.config, name):
                    continue
                current_cfg = getattr(self.physics_manager.app.config, name)
                if hasattr(current_cfg.__class__, '_from_dict_custom'):
                    new_cfg = current_cfg.__class__._from_dict_custom(cfg_dict)
                else:
                    new_cfg = current_cfg.__class__(**cfg_dict)
                setattr(self.physics_manager.app.config, name, new_cfg)
            for name, instance in pm.plugin_instances.items():
                plugin_def = pm.plugins[name]
                if plugin_def.on_load:
                    try:
                        plugin_def.on_load(pm, instance)
                    except Exception as e:
                        Debug.log_error(f"Plugin '{name}' on_load failed during snapshot restore: {e}",
                                        "SnapshotManager")
        str_body_map = {str(uid): body for uid, body in body_uuid_map.items()}
        self.physics_manager.script_manager.deserialize_from_save(data.get("scripts", {}), str_body_map)
        Debug.log_success("Snapshot restored.", category="SnapshotManager")