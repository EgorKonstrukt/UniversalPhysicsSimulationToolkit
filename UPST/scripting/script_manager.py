import pickle
import uuid
from typing import List, Any, Optional, Dict
from UPST.debug.debug_manager import Debug
from UPST.scripting.script_instance import ScriptInstance



class ScriptManager:
    def __init__(self, app=None):
        self.app = app
        self.scripts: List[ScriptInstance] = []
        self.world_scripts: List[ScriptInstance] = []
        self._body_uuid_map: Dict[uuid.UUID, Any] = {}

    def reload_all_scripts(self):
        all_s = self.get_all_scripts()
        r = 0
        for s in all_s:
            if getattr(s, 'filepath', None):
                if s.reload_from_file():
                    r += 1
            else:
                if s.recompile():
                    r += 1
        Debug.log_info(f"Reloaded {r}/{len(all_s)} scripts from files or inline code.", "Scripting")

    def register_body(self, body):
        if not hasattr(body, '_script_uuid'):
            body._script_uuid = uuid.uuid4()
        self._body_uuid_map[body._script_uuid] = body

    def add_script_to(self, owner: Any, code: str, name: str = "Script", threaded: bool = False, start_immediately: bool = True) -> ScriptInstance:
        if owner is not None and hasattr(owner, '_script_uuid'): self.register_body(owner)
        s = ScriptInstance(code, owner, name, threaded, app=self.app)
        if owner is None: self.world_scripts.append(s)
        else:
            if not hasattr(owner, "_scripts"): owner._scripts = []
            owner._scripts.append(s)
            self.scripts.append(s)
        if start_immediately: s.start()
        Debug.log_info(f"Added script '{name}' to {type(owner).__name__ if owner else 'world'}.", "Scripting")
        return s

    def remove_scripts_by_owner(self, owner):
        if not hasattr(owner, "_scripts"): return
        to_rm = list(owner._scripts)
        for sc in to_rm: self.remove_script(sc)
        owner._scripts.clear()

    def remove_script(self, script: ScriptInstance):
        script.stop()
        if script in self.scripts: self.scripts.remove(script)
        if script in self.world_scripts: self.world_scripts.remove(script)
        if hasattr(script.owner, "_scripts") and script in script.owner._scripts: script.owner._scripts.remove(script)

    def update_all(self, dt: float):
        for s in self.scripts + self.world_scripts:
            if s.running and not s.threaded: s.update(dt)

    def stop_all(self):
        for s in list(self.scripts + self.world_scripts): self.remove_script(s)

    def get_all_scripts(self) -> List[ScriptInstance]:
        return self.scripts + self.world_scripts

    def serialize_for_save(self) -> dict:
        def ser(s: ScriptInstance) -> dict:
            ou = None
            if s.owner is not None and hasattr(s.owner, '_script_uuid'): ou = str(s.owner._script_uuid)
            return {"code": s.code, "name": s.name, "threaded": s.threaded, "owner_uuid": ou, "running": s.running, "state": s.get_serializable_state()}
        return {"object_scripts": [ser(s) for s in self.scripts], "world_scripts": [ser(s) for s in self.world_scripts]}

    def start_script(self, script: ScriptInstance):
        if script not in self.scripts and script not in self.world_scripts:
            Debug.log_warning(f"Attempted to start unregistered script '{script.name}'", "Scripting")
            return
        if not script.running: script.start()

    def stop_script(self, script: ScriptInstance):
        if script in self.scripts or script in self.world_scripts: self.remove_script(script)

    def deserialize_from_save(self, data: dict, body_uuid_map: dict):
        self.stop_all()
        self.scripts.clear()
        self.world_scripts.clear()
        str_map = {str(k): v for k, v in body_uuid_map.items()}
        def load_list(items, is_world=False):
            for it in items:
                owner = None
                ou = it.get("owner_uuid")
                if not is_world and ou: owner = str_map.get(ou)
                if is_world or owner is not None:
                    s = self.add_script_to(owner, it["code"], it["name"], it["threaded"], start_immediately=False)
                    s.restore_state(it.get("state", {}))
                    if it.get("running", True): s.start()
        load_list(data.get("object_scripts", []), is_world=False)
        load_list(data.get("world_scripts", []), is_world=True)

    def take_snapshot(self) -> bytes:
        return pickle.dumps(self.serialize_for_save())

    def restore_snapshot(self, snapshot_bytes: bytes, body_uuid_map: dict):
        self.deserialize_from_save(pickle.loads(snapshot_bytes), body_uuid_map)
