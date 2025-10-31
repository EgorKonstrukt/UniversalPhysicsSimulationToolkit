from __future__ import annotations

import asyncio,traceback
from typing import Dict,Any,Optional,Callable
from .protocol import read_message,write_message,now_ms,PROTO_VERSION,sig
from UPST.modules.profiler import profile


class Client:
    def __init__(self,host:str="127.0.0.1",port:int=7777,token:str|None=None,compress:bool=True):
        self.host=host
        self.port=port
        self.token=token
        self.compress=compress
        self.reader:Optional[asyncio.StreamReader]=None
        self.writer:Optional[asyncio.StreamWriter]=None
        self.client_id:Optional[int]=None
        self.on_spawn:Optional[Callable[[dict],None]]=None
        self.on_state:Optional[Callable[[dict],None]]=None
        self.on_chat:Optional[Callable[[str],None]]=None
        self.on_disconnect:Optional[Callable[[],None]]=None
        self.on_custom:Optional[Callable[[dict],None]]=None
        self._stop=False
    async def connect(self):
        self.reader,self.writer=await asyncio.open_connection(self.host,self.port)
        await write_message(self.writer,{"type":"hello","proto":PROTO_VERSION,"token":(sig(self.token) if self.token else None)})
    async def disconnect(self):
        self._stop=True
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
        self.reader=None
        self.writer=None
    async def send(self,msg:dict):
        if self.writer:
            await write_message(self.writer,msg,compress=self.compress)

    async def loop(self):
        try:
            while not self._stop:
                msg=await read_message(self.reader,timeout=1)
                if msg is None:
                    continue
                t=msg.get("type")
                if t=="welcome":
                    self.client_id=msg.get("client_id")
                    if self.on_chat:
                        self.on_chat(f"[system] id={self.client_id}")
                elif t=="ping":
                    await self.send({"type":"pong","t":msg.get("t"),"cli":now_ms()})
                elif t=="pong":
                    pass
                elif t=="spawn" and self.on_spawn:
                    self.on_spawn(msg)
                elif t=="state" and self.on_state:
                    self.on_state(msg)
                elif t=="chat" and self.on_chat:
                    self.on_chat(f"[{msg.get('from')}] {msg.get('text','')}")
                elif t=="error":
                    if self.on_chat:
                        self.on_chat(f"[error] {msg.get('reason')}")
                elif t=="custom" and self.on_custom:
                    self.on_custom(msg)
        except Exception:
            traceback.print_exc()
        finally:
            if self.on_disconnect:
                self.on_disconnect()
