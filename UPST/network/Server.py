import time
import random
import math
from typing import Dict, Any
from Network import NetworkServer

WORLD_WIDTH = 800
WORLD_HEIGHT = 600
TICK_RATE = 20.0

objects: Dict[int, Dict[str, Any]] = {}
next_id = 1


def run_custom_script(obj: Dict[str, Any], dt: float) -> None:
    script = obj.get("script") or ""
    script = script.strip()
    if not script:
        return
    params = obj.setdefault("params", {})
    x = float(obj.get("x", 0.0))
    y = float(obj.get("y", 0.0))
    size = float(obj.get("size", 40.0))
    vx = float(params.get("vx", 0.0))
    vy = float(params.get("vy", 0.0))
    env = {
        "__builtins__": {},
        "x": x,
        "y": y,
        "vx": vx,
        "vy": vy,
        "size": size,
        "dt": dt,
        "params": params,
        "WORLD_WIDTH": WORLD_WIDTH,
        "WORLD_HEIGHT": WORLD_HEIGHT,
        "math": math,
        "min": min,
        "max": max,
        "abs": abs,
    }
    try:
        exec(script, env, env)
    except Exception as e:
        obj["script_error"] = str(e)
        return
    obj["x"] = float(env.get("x", x))
    obj["y"] = float(env.get("y", y))
    params["vx"] = float(env.get("vx", vx))
    params["vy"] = float(env.get("vy", vy))


def update_object(obj: Dict[str, Any], dt: float) -> None:
    script = obj.get("script") or ""
    if script.strip():
        run_custom_script(obj, dt)
        return
    behavior = obj.get("behavior", "none")
    params = obj.setdefault("params", {})
    if behavior == "none":
        return
    y = float(obj.get("y", 0.0))
    size = float(obj.get("size", 40.0))
    vy = float(params.get("vy", 100.0))
    gravity = float(params.get("gravity", 0.0))
    vy += gravity * dt
    y += vy * dt
    if behavior == "fall":
        if y > WORLD_HEIGHT:
            y = -size
    elif behavior == "bounce":
        if y + size > WORLD_HEIGHT:
            y = WORLD_HEIGHT - size
            vy = -abs(vy)
    obj["y"] = y
    params["vy"] = vy
    params["gravity"] = gravity


def main() -> None:
    global next_id
    server = NetworkServer(host="0.0.0.0", port=9999)
    server.start()
    last_time = time.monotonic()
    while True:
        events = server.poll()
        for etype, cid, payload in events:
            if etype == "connect":
                server.send(cid, {"type": "init_state", "objects": list(objects.values())})
            elif etype == "message":
                msg = payload
                mtype = msg.get("type")
                if mtype == "create_cube":
                    obj_id = next_id
                    next_id += 1
                    x = float(msg.get("x", random.randint(50, WORLD_WIDTH - 50)))
                    y = float(msg.get("y", random.randint(50, WORLD_HEIGHT - 50)))
                    size = float(msg.get("size", 50.0))
                    color = msg.get("color")
                    if color is None:
                        color = [random.randint(80, 255) for _ in range(3)]
                    else:
                        color = list(color)
                    behavior = msg.get("behavior", "none")
                    params = msg.get("params") or {}
                    script = msg.get("script") or ""
                    obj = {
                        "id": obj_id,
                        "x": x,
                        "y": y,
                        "size": size,
                        "color": color,
                        "behavior": behavior,
                        "params": params,
                        "script": script,
                    }
                    objects[obj_id] = obj
                    server.broadcast({"type": "create", "object": obj})
                elif mtype == "move_cube":
                    obj_id = msg.get("id")
                    if obj_id in objects:
                        obj = objects[obj_id]
                        if "x" in msg:
                            obj["x"] = float(msg["x"])
                        if "y" in msg:
                            obj["y"] = float(msg["y"])
                        server.broadcast({"type": "update", "object": obj})
                elif mtype == "edit_cube":
                    obj_id = msg.get("id")
                    if obj_id in objects:
                        obj = objects[obj_id]
                        if "x" in msg:
                            obj["x"] = float(msg["x"])
                        if "y" in msg:
                            obj["y"] = float(msg["y"])
                        if "size" in msg:
                            obj["size"] = float(msg["size"])
                        if "color" in msg:
                            obj["color"] = list(msg["color"])
                        if "behavior" in msg:
                            obj["behavior"] = str(msg["behavior"])
                        if "params" in msg:
                            params = obj.setdefault("params", {})
                            for k, v in msg["params"].items():
                                params[k] = float(v)
                        if "script" in msg:
                            obj["script"] = str(msg["script"] or "")
                            obj.pop("script_error", None)
                        server.broadcast({"type": "update", "object": obj})
        now = time.monotonic()
        dt = now - last_time
        if dt < 0:
            dt = 0.0
        last_time = now
        for obj in list(objects.values()):
            update_object(obj, dt)
        server.broadcast({"type": "state", "objects": list(objects.values())})
        frame_time = time.monotonic() - now
        sleep_time = 1.0 / TICK_RATE - frame_time
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    main()
