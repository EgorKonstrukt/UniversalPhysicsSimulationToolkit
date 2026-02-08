import json
from UPST.utils.serialization import serialize_body, deserialize_body

class ContraptionSaveLoadManager:
    def __init__(self, physics_manager):
        self.physics_manager = physics_manager

    def save_contraption(self, filepath, bodies):
        data = [serialize_body(body) for body in bodies]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_contraption(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        new_bodies = []
        for body_data in data:
            body = deserialize_body(body_data)
            if body:
                self.physics_manager.space.add(body, *body.shapes)
                new_bodies.append(body)
        return new_bodies