import time
import json
from pathlib import Path

class Statistics:
    def __init__(self, save_path="stats.json"):
        self.save_path = Path(save_path)
        self._persistent_keys = {'total_runtime', 'launch_count', 'objects_created',
                                 'paused_times', 'static_created', 'constraints_created',
                                 'objects_cutted', 'scripts_created'}
        self._data = {}
        self.load()
        self._data.setdefault('launch_count', 0)
        self._data.setdefault('total_runtime', 0.0)
        self._data.setdefault('objects_created', 0)
        self._data.setdefault('objects_cutted', 0)
        self._data.setdefault('scripts_created', 0)
        self._data['launch_count'] += 1
        self.save()

    def load(self):
        if self.save_path.exists():
            try:
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                    for k in self._persistent_keys:
                        if k in data:
                            self._data[k] = data[k]
            except (ValueError, OSError):
                pass

    def save(self):
        persistent_data = {k: self._data[k] for k in self._persistent_keys if k in self._data}
        with open(self.save_path, 'w') as f:
            json.dump(persistent_data, f, indent=2)

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'Statistics' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name.startswith('_') or name in ('save_path', '_persistent_keys'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def increment(self, key, delta=1):
        self._data[key] = self._data.get(key, 0) + delta

    def accumulate_session_time(self):
        if hasattr(self, 'session_start'):
            duration = time.time() - self.session_start
            self.total_runtime = self._data.get('total_runtime', 0.0) + duration
            self.save()

# Global instance
stats = Statistics()