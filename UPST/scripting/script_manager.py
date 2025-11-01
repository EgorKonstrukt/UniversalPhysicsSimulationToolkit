import pickle
from typing import List, Any, Optional
from UPST.debug.debug_manager import Debug
from UPST.scripting.script_instance import ScriptInstance

class ScriptManager:
    def __init__(self):
        self.scripts: List[ScriptInstance] = []
        self.world_scripts: List[ScriptInstance] = []

    def add_script_to(self, owner: Any, code: str, name: str = "Script", threaded: bool = False):
        script = ScriptInstance(code, owner, name, threaded)
        if owner is None:
            self.world_scripts.append(script)
        else:
            if not hasattr(owner, "_scripts"):
                owner._scripts = []
            owner._scripts.append(script)
            self.scripts.append(script)
        script.start()
        Debug.log_info(f"Added script '{name}' to {type(owner).__name__ if owner else 'world'}.", "Scripting")

    def remove_script(self, script: ScriptInstance):
        script.stop()
        if script in self.scripts:
            self.scripts.remove(script)
        if script in self.world_scripts:
            self.world_scripts.remove(script)
        if hasattr(script.owner, "_scripts") and script in script.owner._scripts:
            script.owner._scripts.remove(script)

    def update_all(self, dt: float):
        for s in self.scripts:
            if s.running and not s.threaded:
                s.update(dt)
        for s in self.world_scripts:
            if s.running and not s.threaded:
                s.update(dt)

    def stop_all(self):
        for s in list(self.scripts + self.world_scripts):
            self.remove_script(s)

    def get_all_scripts(self) -> List[ScriptInstance]:
        return self.scripts + self.world_scripts

    def serialize_for_save(self) -> dict:
        def serialize_script_list(lst):
            return [
                {
                    "code": s.code,
                    "name": s.name,
                    "threaded": s.threaded,
                    "owner_id": id(s.owner) if s.owner and hasattr(s.owner, "_id") else None,
                    "running": s.running,
                }
                for s in lst
            ]
        return {
            "object_scripts": serialize_script_list(self.scripts),
            "world_scripts": serialize_script_list(self.world_scripts)
        }

    def deserialize_from_save(self, data: dict, body_id_map: dict):
        self.stop_all()
        self.scripts.clear()
        self.world_scripts.clear()

        def load_script_list(lst, is_world=False):
            for item in lst:
                owner = None
                if not is_world and item["owner_id"] is not None:
                    owner = body_id_map.get(item["owner_id"])
                if is_world or owner is not None:
                    self.add_script_to(owner, item["code"], item["name"], item["threaded"])
                    if item.get("running", True):
                        item.start()

        load_script_list(data.get("object_scripts", []), is_world=False)
        load_script_list(data.get("world_scripts", []), is_world=True)

    def take_snapshot(self) -> bytes:
        snapshot = self.serialize_for_save()
        return pickle.dumps(snapshot)

    def restore_snapshot(self, snapshot_bytes: bytes, body_id_map: dict):
        data = pickle.loads(snapshot_bytes)
        self.deserialize_from_save(data, body_id_map)