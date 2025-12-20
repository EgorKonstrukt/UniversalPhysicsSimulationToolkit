import os
import pickle
import requests
from UPST.config import config

class RepositoryManager:
    def __init__(self):
        self.cfg = config.repository
        self.base_url = self.cfg.server_url.rstrip("/")
        self.timeout = self.cfg.timeout_sec
        self.local_dir = os.path.join(os.getcwd(),"repository_scenes")
        os.makedirs(self.local_dir,exist_ok=True)

    def is_enabled(self):
        return bool(self.cfg.enabled)

    def fetch_list(self):
        if not self.is_enabled(): return []
        try:
            r = requests.get(f"{self.base_url}/list",timeout=self.timeout)
            return r.json()
        except:
            return []

    def download(self, item_id, title, progress_cb=None):
        r = requests.get(f"{self.base_url}/download/{item_id}", stream=True, timeout=self.timeout)
        total = int(r.headers.get("content-length", 0))
        fp = os.path.join(self.local_dir, f"{item_id}.space")
        size = 0
        with open(fp, "wb") as f:
            for chunk in r.iter_content(8192):
                if not chunk: continue
                f.write(chunk)
                size += len(chunk)
                if progress_cb and total:
                    progress_cb(size / total)
        return fp

    def publish(self, data, progress_cb=None):
        buf = pickle.dumps(data)
        if progress_cb: progress_cb(1.0)
        requests.post(
            f"{self.base_url}/upload",
            data=buf,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(buf))
            },
            timeout=self.timeout
        )

