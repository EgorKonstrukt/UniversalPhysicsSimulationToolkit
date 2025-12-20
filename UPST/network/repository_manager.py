# UPST/repository/manager.py
import os
import pickle
import threading
import time
from typing import List, Dict, Callable, Any, Optional
from urllib.parse import urlencode
import requests
from UPST.config import config
from UPST.debug.debug_manager import Debug

class RepositoryManager:
    def __init__(self):
        self.cfg = config.repository
        self.base_url = self.cfg.server_url.rstrip("/")
        self.timeout = self.cfg.timeout_sec
        self.local_dir = os.path.join(os.getcwd(), "repository_scenes")
        os.makedirs(self.local_dir, exist_ok=True)
        self._list_cache = None
        self._list_cache_ts = 0
        self.CACHE_TTL = 30  # seconds

    def is_enabled(self) -> bool:
        return bool(self.cfg.enabled)

    def fetch_list(self, page: int = 0, limit: int = 50) -> List[Dict[str, str]]:
        if not self.is_enabled():
            return []
        if self._list_cache and time.time() - self._list_cache_ts < self.CACHE_TTL:
            start = page * limit
            return self._list_cache[start:start + limit]
        try:
            params = urlencode({"page": page, "limit": limit})
            r = requests.get(f"{self.base_url}/list?{params}", timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if page == 0:
                self._list_cache = data.get("items", [])
                self._list_cache_ts = time.time()
            return data.get("items", [])
        except Exception as e:
            Debug.log(f"Repo list fetch failed: {e}")
            return []

    def download(self, item_id: str, title: str, progress_cb: Optional[Callable[[float], None]] = None) -> str:
        if not item_id.replace("-", "").isalnum():
            raise ValueError("Invalid item ID")
        fp = os.path.join(self.local_dir, f"{item_id}.space")
        if os.path.exists(fp):
            Debug.log(f"Using cached file: {fp}")
            return fp
        try:
            r = requests.get(f"{self.base_url}/download/{item_id}", stream=True, timeout=self.timeout)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            if total > config.repository.max_scene_size_mb * 1024 * 1024:
                raise ValueError("Scene exceeds max allowed size")
            Debug.log(f"Saving to: {fp}")
            size = 0
            with open(fp, "wb") as f:
                for chunk in r.iter_content(65536):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
                        if progress_cb and total > 0:
                            progress_cb(min(size / total, 1.0))
            Debug.log(f"Download complete: {fp} ({size} bytes)")
            return fp
        except Exception as e:
            if os.path.exists(fp):
                os.remove(fp)
            raise e

    def publish(self, data: Dict[str, Any], progress_cb: Optional[Callable[[float], None]] = None) -> str:
        try:
            buf = pickle.dumps(data)
        except Exception as e:
            raise ValueError(f"Failed to serialize scene: {e}")
        if len(buf) > self.cfg.max_scene_size_mb * 1024 * 1024:
            raise ValueError("Scene too large to publish")
        try:
            r = requests.post(
                f"{self.base_url}/upload",
                data=buf,
                headers={"Content-Type": "application/octet-stream"},
                timeout=self.timeout + 30
            )
            r.raise_for_status()
            resp = r.json()
            if progress_cb:
                progress_cb(1.0)
            return resp["id"]
        except requests.RequestException as e:
            raise RuntimeError(f"Upload request failed: {e}")