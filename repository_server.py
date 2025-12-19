from fastapi import FastAPI, UploadFile
from fastapi.responses import Response
import uuid
import os
import json

app = FastAPI()
ROOT = "repository_data"
SCENES = os.path.join(ROOT,"scenes")
META = os.path.join(ROOT,"meta.json")

os.makedirs(SCENES,exist_ok=True)
if not os.path.isfile(META):
    with open(META,"w") as f: json.dump([],f)

def load_meta():
    with open(META,"r") as f: return json.load(f)

def save_meta(m):
    with open(META,"w") as f: json.dump(m,f,indent=2)

@app.get("/list")
def list_scenes():
    return load_meta()

@app.get("/download/{scene_id}")
def download(scene_id:str):
    fp = os.path.join(SCENES,f"{scene_id}.bin")
    if not os.path.isfile(fp):
        return Response(status_code=404)
    return Response(open(fp,"rb").read(),media_type="application/octet-stream")

@app.post("/upload")
async def upload(file:UploadFile):
    data = await file.read()
    scene_id = str(uuid.uuid4())
    with open(os.path.join(SCENES,f"{scene_id}.bin"),"wb") as f:
        f.write(data)
    meta = load_meta()
    meta.append({
        "id":scene_id,
        "title":"Untitled Scene",
        "author":"Anonymous"
    })
    save_meta(meta)
    return {"status":"ok","id":scene_id}
