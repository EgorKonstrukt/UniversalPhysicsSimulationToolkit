# server/main.py (minimal version without fastapi-limiter)

import os
import uuid
import time
import json
import pickle
from typing import List, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = "repository_data"
SCENES = os.path.join(ROOT, "scenes")
META_INDEX = os.path.join(ROOT, "meta")
os.makedirs(SCENES, exist_ok=True)
os.makedirs(META_INDEX, exist_ok=True)

app = FastAPI(title="UPST Repository API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/list")
def list_scenes(page: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> Dict[str, Any]:
    meta_files = sorted(f for f in os.listdir(META_INDEX) if f.endswith(".json"))
    start = page * limit
    end = start + limit
    items = []
    for fname in meta_files[start:end]:
        with open(os.path.join(META_INDEX, fname), "r") as f:
            items.append(json.load(f))
    return {
        "page": page,
        "limit": limit,
        "total": len(meta_files),
        "items": items
    }

@app.get("/download/{scene_id}")
def download(scene_id: str) -> StreamingResponse:
    if not scene_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid ID")
    scene_path = os.path.join(SCENES, f"{scene_id}.bin")
    meta_path = os.path.join(META_INDEX, f"{scene_id}.json")
    if not os.path.isfile(scene_path) or not os.path.isfile(meta_path):
        raise HTTPException(status_code=404, detail="Not found")
    def iterfile():
        with open(scene_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk
    return StreamingResponse(iterfile(), media_type="application/octet-stream")

@app.post("/upload")
async def upload(request: Request) -> JSONResponse:
    raw = await request.body()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        data = pickle.loads(raw)
        meta_in = data.get("_repo_meta", {})
        title = str(meta_in.get("title", "Untitled"))[:128] or "Untitled"
        author = str(meta_in.get("author", "Anonymous"))[:64]
        desc = str(meta_in.get("description", ""))[:512]
        scene_id = str(uuid.uuid4())
        with open(os.path.join(SCENES, f"{scene_id}.bin"), "wb") as f:
            f.write(raw)
        meta_entry = {
            "id": scene_id,
            "title": title,
            "author": author,
            "description": desc,
            "uploaded_at": int(time.time())
        }
        with open(os.path.join(META_INDEX, f"{scene_id}.json"), "w") as f:
            json.dump(meta_entry, f, ensure_ascii=False)
        return JSONResponse({"status": "ok", "id": scene_id}, status_code=201)
    except Exception as e:
        import logging
        logging.exception("Upload failed")
        raise HTTPException(status_code=500, detail="Serialization error")