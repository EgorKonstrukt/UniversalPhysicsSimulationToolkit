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

    def register_body(self, body):
        """Assign UUID to bodies for persistent referencing"""
        if not hasattr(body, '_script_uuid'):
            body._script_uuid = uuid.uuid4()
        self._body_uuid_map[body._script_uuid] = body

    def add_script_to(self, owner: Any, code: str, name: str = "Script",
                      threaded: bool = False, start_immediately: bool = True) -> ScriptInstance:
        if owner is not None and hasattr(owner, '_script_uuid'):
            self.register_body(owner)

        script = ScriptInstance(code, owner, name, threaded, app=self.app)
        if owner is None:
            self.world_scripts.append(script)
        else:
            if not hasattr(owner, "_scripts"):
                owner._scripts = []
            owner._scripts.append(script)
            self.scripts.append(script)
        if start_immediately:
            script.start()
        Debug.log_info(f"Added script '{name}' to {type(owner).__name__ if owner else 'world'}.", "Scripting")
        return script

    def remove_scripts_by_owner(self, owner):
        if not hasattr(owner, "_scripts"):
            return
        scripts_to_remove = list(owner._scripts)
        for script in scripts_to_remove:
            self.remove_script(script)
        owner._scripts.clear()

    def remove_script(self, script: ScriptInstance):
        script.stop()
        if script in self.scripts:
            self.scripts.remove(script)
        if script in self.world_scripts:
            self.world_scripts.remove(script)
        if hasattr(script.owner, "_scripts") and script in script.owner._scripts:
            script.owner._scripts.remove(script)

    def update_all(self, dt: float):
        for s in self.scripts + self.world_scripts:
            if s.running and not s.threaded:
                s.update(dt)

    def stop_all(self):
        for s in list(self.scripts + self.world_scripts):
            self.remove_script(s)

    def get_all_scripts(self) -> List[ScriptInstance]:
        return self.scripts + self.world_scripts

    def serialize_for_save(self) -> dict:
        def serialize_script(s):
            owner_uuid = None
            if s.owner is not None and hasattr(s.owner, '_script_uuid'):
                owner_uuid = str(s.owner._script_uuid)
            return {
                "code": s.code,
                "name": s.name,
                "threaded": s.threaded,
                "owner_uuid": owner_uuid,
                "running": s.running,
                "state": s.get_serializable_state()
            }

        return {
            "object_scripts": [serialize_script(s) for s in self.scripts],
            "world_scripts": [serialize_script(s) for s in self.world_scripts]
        }
    def start_script(self, script: ScriptInstance):
        if script not in self.scripts and script not in self.world_scripts:
            Debug.log_warning(f"Attempted to start unregistered script '{script.name}'", "Scripting")
            return
        if not script.running:
            script.start()
    def stop_script(self, script: ScriptInstance):
        if script in self.scripts or script in self.world_scripts:
            self.remove_script(script)

    def deserialize_from_save(self, data: dict, body_uuid_map: dict):
        self.stop_all()
        self.scripts.clear()
        self.world_scripts.clear()

        str_body_map = {str(uid): body for uid, body in body_uuid_map.items()}

        def load_script_list(items, is_world=False):
            for item in items:
                owner = None
                owner_uuid_str = item.get("owner_uuid")
                if not is_world and owner_uuid_str:
                    owner = str_body_map.get(owner_uuid_str)
                if is_world or owner is not None:
                    script = self.add_script_to(
                        owner,
                        item["code"],
                        item["name"],
                        item["threaded"],
                        start_immediately=False
                    )
                    script.restore_state(item.get("state", {}))
                    if item.get("running", True):
                        script.start()

        load_script_list(data.get("object_scripts", []), is_world=False)
        load_script_list(data.get("world_scripts", []), is_world=True)

    def take_snapshot(self) -> bytes:
        return pickle.dumps(self.serialize_for_save())

    def restore_snapshot(self, snapshot_bytes: bytes, body_uuid_map: dict):
        self.deserialize_from_save(pickle.loads(snapshot_bytes), body_uuid_map)