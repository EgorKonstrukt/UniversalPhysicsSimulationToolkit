import pickle
import requests
from UPST.config import config

class RepositoryManager:
    def __init__(self):
        self.cfg = config.repository
        self.base_url = self.cfg.server_url.rstrip("/")
        self.timeout = self.cfg.timeout_sec

    def is_enabled(self):
        return bool(self.cfg.enabled)

    def fetch_list(self):
        if not self.is_enabled(): return []
        try:
            r = requests.get(f"{self.base_url}/list",timeout=self.timeout)
            return r.json()
        except:
            return []

    def download(self, item_id):
        r = requests.get(f"{self.base_url}/download/{item_id}",timeout=self.timeout)
        return pickle.loads(r.content)

    def publish(self, data):
        buf = pickle.dumps(data)
        requests.post(
            f"{self.base_url}/upload",
            files={"file":("scene.space",buf)},
            timeout=self.timeout
        )
