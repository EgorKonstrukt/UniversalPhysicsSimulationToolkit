import socket
import json
import select
from typing import Dict, Set, Any, Callable, List, Tuple


class JsonConnection:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.sock.setblocking(False)
        self._recv_buffer = ""

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def send(self, msg: Any) -> None:
        data = (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")
        self.sock.sendall(data)

    def poll(self) -> List[Any]:
        messages: List[Any] = []
        while True:
            try:
                chunk = self.sock.recv(4096)
            except BlockingIOError:
                break
            if not chunk:
                raise ConnectionResetError("Connection closed by peer")
            self._recv_buffer += chunk.decode("utf-8")
            while "\n" in self._recv_buffer:
                line, self._recv_buffer = self._recv_buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    pass
        return messages


class NetworkServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999, listen_backlog: int = 16):
        self.host = host
        self.port = port
        self.listen_backlog = listen_backlog
        self._server_sock: socket.socket = None
        self._next_client_id: int = 1
        self._clients: Dict[int, JsonConnection] = {}
        self._sock_to_id: Dict[socket.socket, int] = {}
        self._rooms: Dict[str, Set[int]] = {}
        self._rpc_handlers: Dict[str, Callable[..., Any]] = {}

    @property
    def is_running(self) -> bool:
        return self._server_sock is not None

    def start(self) -> None:
        if self._server_sock is not None:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(self.listen_backlog)
        s.setblocking(False)
        self._server_sock = s

    def register_rpc(self, name: str, func: Callable[..., Any]) -> None:
        self._rpc_handlers[name] = func

    def unregister_rpc(self, name: str) -> None:
        if name in self._rpc_handlers:
            del self._rpc_handlers[name]

    def add_to_room(self, client_id: int, room: str) -> None:
        r = self._rooms.setdefault(room, set())
        r.add(client_id)

    def remove_from_room(self, client_id: int, room: str) -> None:
        r = self._rooms.get(room)
        if not r:
            return
        r.discard(client_id)
        if not r:
            del self._rooms[room]

    def broadcast_room(self, room: str, msg: Any) -> None:
        r = self._rooms.get(room)
        if not r:
            return
        dead: List[int] = []
        for cid in list(r):
            conn = self._clients.get(cid)
            if conn is None:
                dead.append(cid)
                continue
            try:
                conn.send(msg)
            except OSError:
                dead.append(cid)
        dummy_events: List[Tuple[str, int, Any]] = []
        for cid in dead:
            self._drop_client(cid, dummy_events)

    def _accept_new_clients(self, events: List[Tuple[str, int, Any]]) -> None:
        while True:
            try:
                client_sock, addr = self._server_sock.accept()
            except BlockingIOError:
                break
            client_sock.setblocking(False)
            conn = JsonConnection(client_sock)
            cid = self._next_client_id
            self._next_client_id += 1
            self._clients[cid] = conn
            self._sock_to_id[client_sock] = cid
            events.append(("connect", cid, {"address": addr}))

    def _drop_client(self, client_id: int, events: List[Tuple[str, int, Any]]) -> None:
        conn = self._clients.pop(client_id, None)
        if conn is None:
            return
        s = conn.sock
        self._sock_to_id.pop(s, None)
        conn.close()
        empty_rooms: List[str] = []
        for room, members in self._rooms.items():
            if client_id in members:
                members.discard(client_id)
            if not members:
                empty_rooms.append(room)
        for room in empty_rooms:
            del self._rooms[room]
        events.append(("disconnect", client_id, {}))

    def _handle_rpc(self, client_id: int, msg: Dict[str, Any], events: List[Tuple[str, int, Any]]) -> None:
        name = msg.get("name")
        rpc_id = msg.get("id")
        args = msg.get("args") or []
        kwargs = msg.get("kwargs") or {}
        handler = self._rpc_handlers.get(name)
        if handler is None:
            resp = {"type": "rpc_result", "id": rpc_id, "ok": False, "error": "unknown_rpc", "name": name}
            self.send(client_id, resp)
            events.append(("rpc", client_id, {"name": name, "id": rpc_id, "handled": False}))
            return
        try:
            result = handler(client_id, *args, **kwargs)
            resp = {"type": "rpc_result", "id": rpc_id, "ok": True, "result": result, "name": name}
        except Exception as e:
            resp = {"type": "rpc_result", "id": rpc_id, "ok": False, "error": str(e), "name": name}
        self.send(client_id, resp)
        events.append(("rpc", client_id, {"name": name, "id": rpc_id, "handled": True}))

    def poll(self) -> List[Tuple[str, int, Any]]:
        events: List[Tuple[str, int, Any]] = []
        if self._server_sock is None:
            return events
        self._accept_new_clients(events)
        read_socks = [c.sock for c in self._clients.values()]
        if not read_socks:
            self._accept_new_clients(events)
            return events
        try:
            readable, _, exceptional = select.select(read_socks, [], read_socks, 0)
        except ValueError:
            readable, exceptional = [], []
        for s in readable:
            client_id = self._sock_to_id.get(s)
            if client_id is None:
                continue
            conn = self._clients.get(client_id)
            if conn is None:
                continue
            try:
                msgs = conn.poll()
            except (ConnectionResetError, OSError):
                self._drop_client(client_id, events)
            else:
                for msg in msgs:
                    if isinstance(msg, dict) and msg.get("type") == "rpc":
                        self._handle_rpc(client_id, msg, events)
                    else:
                        events.append(("message", client_id, msg))
        for s in exceptional:
            client_id = self._sock_to_id.get(s)
            if client_id is not None:
                self._drop_client(client_id, events)
        self._accept_new_clients(events)
        return events

    def send(self, client_id: int, msg: Any) -> bool:
        conn = self._clients.get(client_id)
        if conn is None:
            return False
        try:
            conn.send(msg)
            return True
        except OSError:
            dummy_events: List[Tuple[str, int, Any]] = []
            self._drop_client(client_id, dummy_events)
            return False

    def broadcast(self, msg: Any) -> None:
        dead: List[int] = []
        for cid, conn in self._clients.items():
            try:
                conn.send(msg)
            except OSError:
                dead.append(cid)
        dummy_events: List[Tuple[str, int, Any]] = []
        for cid in dead:
            self._drop_client(cid, dummy_events)

    def close_client(self, client_id: int) -> None:
        dummy_events: List[Tuple[str, int, Any]] = []
        self._drop_client(client_id, dummy_events)

    def close(self) -> None:
        for cid in list(self._clients.keys()):
            self.close_client(cid)
        if self._server_sock is not None:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None


class NetworkClient:
    def __init__(self):
        self._conn: JsonConnection = None
        self._connected: bool = False
        self._rpc_id_counter: int = 1
        self._rpc_pending: Dict[int, Dict[str, Any]] = {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, host: str = "127.0.0.1", port: int = 9999, timeout: float = 5.0) -> None:
        if self._connected:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.settimeout(0.0)
        self._conn = JsonConnection(s)
        self._connected = True

    def send(self, msg: Any) -> bool:
        if not self._connected or self._conn is None:
            return False
        try:
            self._conn.send(msg)
            return True
        except OSError:
            self.close()
            return False

    def call_rpc(self, name: str, *args: Any, **kwargs: Any) -> int:
        if not self._connected or self._conn is None:
            return -1
        rpc_id = self._rpc_id_counter
        self._rpc_id_counter += 1
        msg = {"type": "rpc", "id": rpc_id, "name": name, "args": list(args), "kwargs": kwargs}
        ok = self.send(msg)
        if not ok:
            return -1
        self._rpc_pending[rpc_id] = {"done": False, "ok": None, "result": None, "error": None, "name": name}
        return rpc_id

    def get_rpc_result(self, rpc_id: int) -> Any:
        st = self._rpc_pending.get(rpc_id)
        if st is None:
            return None
        if not st["done"]:
            return {"done": False}
        return {"done": True, "ok": st["ok"], "result": st["result"], "error": st["error"], "name": st["name"]}

    def poll(self) -> List[Any]:
        if not self._connected or self._conn is None:
            return []
        try:
            msgs = self._conn.poll()
        except (ConnectionResetError, OSError):
            self.close()
            return []
        normal: List[Any] = []
        for msg in msgs:
            if isinstance(msg, dict) and msg.get("type") == "rpc_result":
                rpc_id = msg.get("id")
                st = self._rpc_pending.get(rpc_id)
                if st is not None:
                    st["done"] = True
                    st["ok"] = bool(msg.get("ok"))
                    st["result"] = msg.get("result")
                    st["error"] = msg.get("error")
            else:
                normal.append(msg)
        return normal

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._connected = False
        self._rpc_pending.clear()
