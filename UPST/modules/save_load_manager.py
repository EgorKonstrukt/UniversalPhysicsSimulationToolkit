import tkinter as tk
import uuid
from tkinter import filedialog
import pickle
import traceback
import pymunk
import gzip
import lzma
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os
import pygame_gui

from UPST.config import config
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import get_gizmos, GizmoType, GizmoData
from UPST.utils.utils import surface_to_bytes, bytes_to_surface, safe_filedialog
from UPST.modules.undo_redo_manager import get_undo_redo
import pygame


class SaveLoadManager:
    def __init__(self, physics_manager, camera, ui_manager, sound_manager, app):
        self.app = app
        self.physics_manager = physics_manager
        self.camera = camera
        self.ui_manager = ui_manager
        self.sound_manager = sound_manager
        self.undo_redo = get_undo_redo()
        self.enable_compression = config.save_load.enable_compression
        self.compression_method = config.save_load.compression_method

        self._executor = ThreadPoolExecutor(max_workers=1)
        self._autosave_lock = threading.Lock()

        self._autosave_load_pending = False
        if os.path.isfile(config.app.autosave_path):
            self._autosave_load_pending = True

    def try_load_deferred_autosave(self):
        if not self._autosave_load_pending:
            return
        self._autosave_load_pending = False
        self._try_load_autosave()
    def render_preview(self, data, size=(256, 256)):
        w, h = size
        assert w == h, "Preview must be square"
        preview_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        preview_surf.fill((30, 30, 30, 255))
        try:
            if hasattr(self.app, 'screen'):
                screen = self.app.screen
                screen_w, screen_h = screen.get_size()
                if screen_w == 0 or screen_h == 0:
                    raise ValueError("Screen surface is invalid")
                min_dim = min(screen_w, screen_h)
                crop_x = (screen_w - min_dim) // 2
                crop_y = (screen_h - min_dim) // 2
                cropped = screen.subsurface((crop_x, crop_y, min_dim, min_dim))
                scaled = pygame.transform.smoothscale(cropped, (w, h))
                preview_surf.blit(scaled, (0, 0))
            else:
                raise AttributeError("Application has no screen attribute")
        except Exception as e:
            Debug.log(f"Failed to render preview: {e}")
            pygame.draw.line(preview_surf, (80, 80, 80), (0, 0), (w, w), 2)
            pygame.draw.line(preview_surf, (80, 80, 80), (w, 0), (0, w), 2)
        return preview_surf

    def _preview_scale(self, points, size):
        if not points: return 1.0
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        w = max(xs) - min(xs) or 1.0
        h = max(ys) - min(ys) or 1.0
        scale_x = size[0] / w
        scale_y = size[1] / h
        return min(scale_x, scale_y) * 0.9

    def _world_to_preview(self, world_pt, all_points, size):
        if not all_points: return (size[0] // 2, size[1] // 2)
        xs = [p.x for p in all_points]
        ys = [p.y for p in all_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max_x - min_x or 1.0
        h = max_y - min_y or 1.0
        sx = size[0] / w
        sy = size[1] / h
        scale = min(sx, sy) * 0.9
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        x = (world_pt.x - cx) * scale + size[0] // 2
        y = (world_pt.y - cy) * scale + size[1] // 2
        return (int(x), int(y))

    def _try_load_autosave(self):
        if not os.path.isfile(config.app.autosave_path):
            return
        future = self._executor.submit(self._load_autosave_task)
        try:
            success, error_msg = future.result(timeout=5.0)
            if success:
                self.physics_manager.set_simulation_paused(paused=False)
                Debug.log_success("Autosave loaded from root directory.", category="SaveLoadManager")
            else:
                self._handle_autosave_error(error_msg)
        except TimeoutError:
            self._handle_autosave_error("Autosave load timed out (took longer than 5 seconds). File may be corrupted.")
        except Exception as e:
            self._handle_autosave_error(f"Unexpected error during autosave load: {e}")

    def _load_autosave_task(self):
        try:
            with open(config.app.autosave_path, "rb") as f:
                data = f.read()
            self._apply_loaded_data(pickle.loads(data))
            return True, None
        except Exception as e:
            return False, str(e)

    def _handle_autosave_error(self, message):
        Debug.log_error(f"Autosave failed: {message}", category="SaveLoadManager")
        if hasattr(self.app, 'screen') and self.app.screen is not None and pygame.display.get_surface() is not None:
            try:
                pygame_gui.windows.UIMessageWindow(
                    rect=pygame.Rect(100, 100, 400, 200),
                    window_title="Autosave Load Failed",
                    html_message=f"<b>Failed to load autosave:</b><br>{message}<br><br>The simulation will start empty.",
                    manager=self.ui_manager
                )
            except Exception as gui_err:
                Debug.log_error(f"Failed to show autosave error dialog: {gui_err}", category="SaveLoadManager")
        else:
            # Too early to show GUI; just log
            Debug.log_warning("Autosave error occurred before UI was ready. Message: " + message, category="SaveLoadManager")

    def _write_autosave_background(self, data):
        if not self._autosave_lock.acquire(blocking=False):
            return
        try:
            snapshot_bytes = pickle.dumps(data)
            with open(config.app.autosave_path, "wb") as f:
                f.write(snapshot_bytes)
            Debug.log_success("Autosave written to root directory.", category="SaveLoadManager")
        except Exception as e:
            Debug.log_error(f"Autosave write failed: {e}", category="SaveLoadManager")
        finally:
            self._autosave_lock.release()

    def save_autosave_background(self, data):
        self._executor.submit(self._write_autosave_background, data)

    def capture_snapshot_data(self) -> dict:
        return self._prepare_save_data()

    def create_snapshot(self) -> bytes:
        data = self.capture_snapshot_data()
        self.save_autosave_background(data)
        return pickle.dumps(data)

    def save_world(self):
        root = tk.Tk(); root.withdraw()
        fp = safe_filedialog(filedialog.asksaveasfilename, defaultextension=".ngsv",
                                                          filetypes=[("UPST Save File","*.space")],
                             freeze_watcher=self.app.freeze_watcher)
        if not fp: Debug.log_warning("Canceled...", "SaveLoadManager"); return
        try:
            data = self._prepare_save_data()
            if self.enable_compression:
                if self.compression_method == "lzma": lzma.open(fp,"wb").__enter__().write(pickle.dumps(data))
                else: gzip.open(fp,"wb").__enter__().write(pickle.dumps(data))
            else: open(fp,"wb").write(pickle.dumps(data))
            Debug.log_success(f"Saved to {fp}", "SaveLoadManager")
        except Exception as e:
            Debug.log_exception(f"Save failed for {fp}: {traceback.format_exc()}", "SaveLoadManager")

    def _prepare_save_data(self):
        data = {"iterations": int(self.physics_manager.space.iterations),
                "air_friction_linear": float(self.physics_manager.air_friction_linear),
                "air_friction_quadratic": float(self.physics_manager.air_friction_quadratic),
                "air_friction_multiplier": float(self.physics_manager.air_friction_multiplier),
                "air_density": float(self.physics_manager.air_density),
                "sim_freq": int(self.physics_manager.simulation_frequency),
                "gravity": tuple(self.physics_manager.space.gravity),
                "damping_linear": float(self.physics_manager.space.damping),
                "damping_angular": float(getattr(self.physics_manager, "_angular_damping", 0.0)),
                "sleep_time_threshold": float(self.physics_manager.space.sleep_time_threshold),
                "collision_slop": float(self.physics_manager.space.collision_slop),
                "collision_bias": float(self.physics_manager.space.collision_bias),
                "camera_translation": (getattr(getattr(self.camera, "translation", None), "tx", 0.0),
                                       getattr(getattr(self.camera, "translation", None), "ty", 0.0)),
                "camera_scaling": float(getattr(self.camera, "scaling", 1.0)),
                "bodies": [],
                "constraints": [],
                "static_lines": [],
                "scripts": self.physics_manager.script_manager.serialize_for_save()}
        if hasattr(self.physics_manager.app, 'console_handler') and hasattr(self.physics_manager.app.console_handler,
                                                                            'graph_manager'):
            graph_mgr = self.physics_manager.app.console_handler.graph_manager
            data["graphs"] = graph_mgr.serialize()
        if hasattr(self.app, 'tool_system'):
            graph_tool = self.app.tool_system.get_tool_by_name('graph')
            if graph_tool and hasattr(graph_tool, 'serialize_for_save'):
                data['graph_tool_state'] = graph_tool.serialize_for_save()
        sim_bodies = [b for b in self.physics_manager.space.bodies if b is not self.physics_manager.static_body]
        body_map = {b: i for i, b in enumerate(sim_bodies)}
        for body in sim_bodies:
            if not hasattr(body, '_script_uuid'):
                body._script_uuid = uuid.uuid4()
            shapes_data = []
            for shape in body.shapes:
                shape_data = {"type": shape.__class__.__name__, "friction": float(getattr(shape, "friction", 0.5)),
                              "elasticity": float(getattr(shape, "elasticity", 0.0)),
                              "color": getattr(shape, "color", (200, 200, 200, 255))}
                if isinstance(shape, pymunk.Circle):
                    shape_data.update(
                        {"radius": float(shape.radius), "offset": tuple(getattr(shape, "offset", (0.0, 0.0)))})
                elif isinstance(shape, pymunk.Poly):
                    shape_data["vertices"] = [tuple(v) for v in shape.get_vertices()]
                elif isinstance(shape, pymunk.Segment):
                    shape_data.update({"a": tuple(shape.a), "b": tuple(shape.b), "radius": float(shape.radius)})
                shapes_data.append(shape_data)
            tex_surface = None
            if hasattr(self.physics_manager.app,
                       'renderer'): tex_surface = self.physics_manager.app.renderer._get_texture(
                getattr(body, 'texture_path', None))
            texture_path = getattr(body, 'texture_path', None)
            tex_bytes = surface_to_bytes(tex_surface) if tex_surface else None
            tex_size = tex_surface.get_size() if tex_surface else None
            body_data = {
                "_script_uuid": str(body._script_uuid),
                "color": tuple(getattr(body, "color", (200, 200, 200, 255))),
                "name": str(getattr(body, "name", "Body"),),
                "position": tuple(body.position), "angle": float(body.angle), "velocity": tuple(body.velocity),
                "angular_velocity": float(body.angular_velocity), "mass": float(getattr(body, "mass", 1.0)),
                "moment": float(getattr(body, "moment", 1.0)), "body_type": int(body.body_type), "shapes": shapes_data,
                "texture_path": texture_path, "texture_bytes": tex_bytes, "texture_size": tex_size,
                "texture_scale": float(getattr(body, "texture_scale", 1.0)),
                "stretch_texture": bool(getattr(body, "stretch_texture", True)),
                "center_of_gravity": tuple(body.center_of_gravity),

            }
            data["bodies"].append(body_data)

        for c in list(self.physics_manager.space.constraints):
            if c.a not in body_map or c.b not in body_map: continue
            cd = {"type":c.__class__.__name__,"a":body_map[c.a],"b":body_map[c.b]}
            if isinstance(c,pymunk.PinJoint): cd.update({"anchor_a":c.anchor_a,"anchor_b":c.anchor_b})
            elif isinstance(c,pymunk.PivotJoint): cd["anchor"] = c.anchor_a
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
            elif isinstance(c,pymunk.SimpleMotor): cd["rate"] = float(c.rate)
            elif isinstance(c,pymunk.GearJoint): cd.update({"phase":float(c.phase),"ratio":float(c.ratio)})
            elif isinstance(c,pymunk.SlideJoint): cd.update({"anchor_a":c.anchor_a,"anchor_b":c.anchor_b,"min":float(c.min),"max":float(c.max)})
            elif isinstance(c,pymunk.RotaryLimitJoint): cd.update({"min":float(c.min),"max":float(c.max)})
            data["constraints"].append(cd)
        for line in list(self.physics_manager.static_lines):
            ld = {"friction":float(getattr(line,"friction",0.5)),"elasticity":float(getattr(line,"elasticity",0.0)),"color":getattr(line,"color",(200,200,200,255))}
            if isinstance(line,pymunk.Poly): ld.update({"type":"Poly","vertices":[tuple(v) for v in line.get_vertices()]})
            elif isinstance(line,pymunk.Segment): ld.update({"type":"Segment","a":tuple(line.a),"b":tuple(line.b),"radius":float(line.radius)})
            else: continue
            data["static_lines"].append(ld)
        script_data = self.physics_manager.script_manager.serialize_for_save()
        data["scripts"] = script_data
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
        if hasattr(self.app, 'plugin_manager'):
            plugin_meta = {}
            plugin_configs = {}
            for name, plugin in self.app.plugin_manager.plugins.items():
                plugin_meta[name] = {
                    "version": plugin.version,
                    "author": plugin.author,
                }
                cfg = getattr(self.app.config, name, None)
                if cfg:
                    from dataclasses import asdict
                    cfg_dict = asdict(cfg)
                    if hasattr(cfg, '_to_dict_custom'):
                        cfg_dict = cfg._to_dict_custom(cfg_dict)
                    plugin_configs[name] = cfg_dict
            data["plugins"] = plugin_meta
            data["plugin_configs"] = plugin_configs

        return data

    def load_world(self):
        root = tk.Tk(); root.withdraw()
        fp = safe_filedialog(filedialog.askopenfilename,filetypes=[("UPST Save File","*.space")],
                             freeze_watcher=self.app.freeze_watcher)
        if not fp: Debug.log_warning(f"Load canceled: {fp}", "SaveLoadManager"); return
        try:
            data = self._load_data_with_fallback(fp)
            self._apply_loaded_data(data)
            self.physics_manager.set_simulation_paused(paused=False)
            Debug.log_success(f"Loaded from {fp}", "SaveLoadManager")
        except Exception as e:
            Debug.log_exception(f"Load failed for {fp}: {traceback.format_exc()}", "SaveLoadManager")

    def _load_data_with_fallback(self, fp):
        methods = [("lzma",lambda:lzma.open(fp,"rb")),("gzip",lambda:gzip.open(fp,"rb")),("none",lambda:open(fp,"rb"))]
        for name,opener in methods:
            try:
                with opener() as f: return pickle.load(f)
            except (lzma.LZMAError,gzip.BadGzipFile,UnicodeDecodeError,EOFError,ValueError): continue
        raise Exception("Unable to load file with any compression method")

    def apply_meta(self, meta):
        self.app.current_scene_meta = meta or {}
        if hasattr(self.app, "set_window_title"):
            self.app.set_window_title(meta.get("title", "Untitled Scene"))

    def _apply_loaded_data(self, data):
        self.physics_manager.delete_all()
        self.physics_manager.set_iterations(int(data.get("iterations",config.physics.iterations)))
        self.physics_manager.set_simulation_frequency(int(data.get("sim_freq",config.physics.simulation_frequency)))
        self.physics_manager.space.gravity = tuple(data.get("gravity",(0.0,900.0)))
        self.physics_manager.set_damping(float(data.get("damping_linear",1.0)),float(data.get("damping_angular",0.0)))
        self.physics_manager.set_sleep_time_threshold(float(data.get("sleep_time_threshold",config.physics.sleep_time_threshold)))
        self.physics_manager.set_collision_slop(float(data.get("collision_slop",0.5)))
        self.physics_manager.set_collision_bias(float(data.get("collision_bias",pow(1.0-0.1,60.0))))

        self.physics_manager.set_air_friction_linear(int(data.get("air_friction_linear",config.physics.air_friction_linear)))
        self.physics_manager.set_air_friction_quadratic(int(data.get("air_friction_quadratic",config.physics.air_friction_quadratic)))
        self.physics_manager.set_air_friction_multiplier(int(data.get("air_friction_multiplier",config.physics.air_friction_multiplier)))
        self.physics_manager.set_air_density(int(data.get("air_density",config.physics.air_density)))

        if "graphs" in data and hasattr(self.physics_manager.app, 'console_handler'):
            graph_mgr = self.physics_manager.app.console_handler.graph_manager
            graph_mgr.deserialize(data["graphs"])
        if "graph_tool_state" in data and hasattr(self.app, 'tool_system'):
            graph_tool = self.app.tool_system.get_tool_by_name('graph')
            if graph_tool and hasattr(graph_tool, 'deserialize_from_save'):
                graph_tool.deserialize_from_save(data["graph_tool_state"])

        cam_tr = data.get("camera_translation")
        if cam_tr and isinstance(cam_tr,(list,tuple)) and len(cam_tr)==2: self.camera.translation = pymunk.Transform(1,0,0,1,float(cam_tr[0]),float(cam_tr[1]))
        cam_scale = float(data.get("camera_scaling",getattr(self.camera,"scaling",1.0)))
        self.camera.scaling = cam_scale
        if hasattr(self.camera,"target_scaling"): self.camera.target_scaling = cam_scale
        loaded_bodies = []
        body_uuid_map = {}
        for bd in data.get("bodies", []):
            body_type = int(bd.get("body_type", int(pymunk.Body.DYNAMIC)))
            bt = pymunk.Body(body_type=body_type)
            if '_script_uuid' in bd and bd['_script_uuid']:
                try:
                    bt._script_uuid = uuid.UUID(bd['_script_uuid'])
                except:
                    bt._script_uuid = uuid.uuid4()
            else:
                bt._script_uuid = uuid.uuid4()
            body_uuid_map[bt._script_uuid] = bt
            if bt.body_type == pymunk.Body.DYNAMIC:
                bt.mass = float(bd.get("mass",1.0))
                bt.moment = float(bd.get("moment",1.0))
            bt.name = bd.get("name",None)
            bt.color = bd.get("color",(255,255,255,255))
            bt.position = pymunk.Vec2d(*bd.get("position",(0.0,0.0)))
            bt.angle = float(bd.get("angle",0.0))
            bt.velocity = pymunk.Vec2d(*bd.get("velocity",(0.0,0.0)))
            bt.angular_velocity = float(bd.get("angular_velocity",0.0))
            bt.texture_path = bd.get("texture_path")
            bt.texture_bytes = bd.get("texture_bytes")
            bt.texture_size = bd.get("texture_size")
            bt.texture_scale = float(bd.get("texture_scale",1.0))
            bt.stretch_texture = bool(bd.get("stretch_texture",True))
            shapes = []
            for sd in bd.get("shapes",[]):
                st = sd.get("type","")
                shp = None
                if st == "Circle": shp = pymunk.Circle(bt,float(sd["radius"]),tuple(sd.get("offset",(0.0,0.0))))
                elif st == "Poly": shp = pymunk.Poly(bt,[pymunk.Vec2d(*v) for v in sd["vertices"]])
                elif st == "Segment": shp = pymunk.Segment(bt,pymunk.Vec2d(*sd["a"]),pymunk.Vec2d(*sd["b"]),float(sd["radius"]))
                if shp:
                    shp.friction = float(sd.get("friction",0.5))
                    shp.elasticity = float(sd.get("elasticity",0.0))
                    shp.color = tuple(sd.get("color",(200,200,200,255)))
                    shapes.append(shp)
            if shapes: self.physics_manager.space.add(bt,*shapes)
            else: self.physics_manager.space.add(bt)
            loaded_bodies.append(bt)
        script_data = data.get("scripts", {})
        self.physics_manager.script_manager.deserialize_from_save(script_data, body_uuid_map)
        for cd in data.get("constraints",[]):
            a = loaded_bodies[cd["a"]]; b = loaded_bodies[cd["b"]]; ctype = cd["type"]; c = None
            if ctype == "PinJoint": c = pymunk.PinJoint(a,b,cd["anchor_a"],cd["anchor_b"])
            elif ctype == "PivotJoint": c = pymunk.PivotJoint(a,b,cd["anchor"])
            elif ctype == "DampedSpring":
                c = pymunk.DampedSpring(a, b, cd["anchor_a"], cd["anchor_b"], float(cd["rest_length"]),
                                        float(cd["stiffness"]), float(cd["damping"]))
                if "size" in cd:
                    c.size = float(cd["size"])
                if "color" in cd:
                    c.color = tuple(cd["color"])
            elif ctype == "SimpleMotor": c = pymunk.SimpleMotor(a,b,float(cd["rate"]))
            elif ctype == "GearJoint": c = pymunk.GearJoint(a,b,float(cd["phase"]),float(cd["ratio"]))
            elif ctype == "SlideJoint": c = pymunk.SlideJoint(a,b,cd["anchor_a"],cd["anchor_b"],float(cd["min"]),float(cd["max"]))
            elif ctype == "RotaryLimitJoint": c = pymunk.RotaryLimitJoint(a,b,float(cd["min"]),float(cd["max"]))
            if c: self.physics_manager.add_constraint(c)
        for ld in data.get("static_lines",[]):
            line = None
            if ld.get("type") == "Poly": line = pymunk.Poly(self.physics_manager.static_body,[pymunk.Vec2d(*v) for v in ld["vertices"]])
            elif ld.get("type") == "Segment": line = pymunk.Segment(self.physics_manager.static_body,pymunk.Vec2d(*ld["a"]),pymunk.Vec2d(*ld["b"]),float(ld["radius"]))
            if line:
                line.friction = float(ld.get("friction",0.5))
                line.elasticity = float(ld.get("elasticity",0.0))
                line.color = tuple(ld.get("color",(200,200,200,255)))
                self.physics_manager.static_lines.append(line)
                self.physics_manager.space.add(line)
        if hasattr(self.physics_manager.app,'renderer') and "bodies" in data:
            renderer = self.physics_manager.app.renderer
            unique_textures = {}
            for bd in data["bodies"]:
                tex_bytes = bd.get("texture_bytes"); tex_size = bd.get("texture_size")
                if tex_bytes and tex_size and tex_bytes not in unique_textures:
                    surf = bytes_to_surface(tex_bytes,tex_size)
                    if surf: unique_textures[tex_bytes] = surf
            renderer.texture_cache.clear()
            for tex_bytes,surf in unique_textures.items(): renderer.texture_cache[tex_bytes] = surf

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
        if hasattr(self.app, 'plugin_manager') and plugin_meta:
            pm = self.app.plugin_manager
            for name, meta in plugin_meta.items():
                if name not in pm.plugins:
                    Debug.log_warning(f"Plugin '{name}' was saved but is not loaded.", "SaveLoadManager")
                    continue
                current = pm.plugins[name]
                if current.version != meta["version"]:
                    Debug.log_warning(
                        f"Plugin '{name}' version mismatch: saved {meta['version']}, current {current.version}",
                        "SaveLoadManager")
            for name, cfg_dict in plugin_configs.items():
                if not hasattr(self.app.config, name):
                    continue
                current_cfg = getattr(self.app.config, name)
                if hasattr(current_cfg.__class__, '_from_dict_custom'):
                    new_cfg = current_cfg.__class__._from_dict_custom(cfg_dict)
                else:
                    new_cfg = current_cfg.__class__(**cfg_dict)
                setattr(self.app.config, name, new_cfg)
            for name, instance in pm.plugin_instances.items():
                plugin_def = pm.plugins[name]
                if plugin_def.on_load:
                    try:
                        plugin_def.on_load(pm, instance)
                    except Exception as e:
                        Debug.log_error(f"Plugin '{name}' on_load failed during load: {e}", "SaveLoadManager")
        self.undo_redo.take_snapshot()

    def set_compression_enabled(self, enabled): self.enable_compression = bool(enabled)
    def set_compression_method(self, method):
        if method in ["gzip","lzma","none"]: self.compression_method = method
    def is_compression_enabled(self): return self.enable_compression
    def get_compression_method(self): return self.compression_method