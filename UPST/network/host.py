import asyncio,traceback
from typing import Dict,Any,Callable,Optional,Tuple,List
from .protocol import read_message,write_message,now_ms,PROTO_VERSION,sig
from UPST.modules.profiler import profile


class Host:
    def __init__(self,port:int=7777,token:str|None=None,max_clients:int=64,compress:bool=True):
        self.port=port
        self.token=token
        self.max_clients=max_clients
        self.compress=compress
        self.server:Optional[asyncio.base_events.Server]=None
        self.clients:Dict[int,Tuple[asyncio.StreamReader,asyncio.StreamWriter,dict]]={}
        self.next_client_id=1
        self.on_input:Optional[Callable[[int,dict],None]]=None
        self.on_custom:Optional[Callable[[int,dict],None]]=None
        self.on_client:Optional[Callable[[int,Any],None]]=None
        self.on_disconnect:Optional[Callable[[int],None]]=None
        self.state_provider:Optional[Callable[[],List[dict]]]=None
        self.broadcast_hz=10
        self._last_broadcast=0
        self.timeout_ms=15000
        self.ping_interval_ms=3000

    async def start(self):
        self.server=await asyncio.start_server(self._accept,"0.0.0.0",self.port)
    async def stop(self):
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
        finally:
            self.server=None
            for cid,(_,w,_) in list(self.clients.items()):
                try:
                    w.close()
                    await w.wait_closed()
                except:
                    pass
            self.clients.clear()
    async def _accept(self,reader:asyncio.StreamReader,writer:asyncio.StreamWriter):
        peer=writer.get_extra_info("peername")
        if len(self.clients)>=self.max_clients:
            await write_message(writer,{"type":"error","reason":"full"})
            writer.close()
            return
        hello=await read_message(reader,timeout=5)
        if not isinstance(hello,dict) or hello.get("type")!="hello":
            writer.close()
            return
        if hello.get("proto")!=PROTO_VERSION:
            await write_message(writer,{"type":"error","reason":"proto"})
            writer.close()
            return
        if self.token is not None and hello.get("token")!=sig(self.token):
            await write_message(writer,{"type":"error","reason":"auth"})
            writer.close()
            return
        cid=self.next_client_id
        self.next_client_id+=1
        self.clients[cid]=(reader,writer,{"last":now_ms(),"rtt":0})
        await write_message(writer,{"type":"welcome","client_id":cid,"server_time":now_ms(),"proto":PROTO_VERSION})
        if self.on_client:
            self.on_client(cid,peer)
        asyncio.create_task(self._client_loop(cid))

    @profile("net_client_loop", "Network")
    async def _client_loop(self,cid:int):
        try:
            reader,writer,meta=self.clients[cid]
            while True:
                now=now_ms()
                if now-meta["last"]>self.timeout_ms:
                    break
                msg=await read_message(reader,timeout=1)
                if msg is None:
                    continue
                t=msg.get("type")
                meta["last"]=now_ms()
                if t=="ping":
                    await write_message(writer,{"type":"pong","t":msg.get("t"),"srv":now_ms()})
                elif t=="input" and self.on_input:
                    self.on_input(cid,msg)
                elif t=="chat":
                    await self.broadcast({"type":"chat","from":cid,"text":msg.get("text","")})
                elif t=="spawn":
                    await self.broadcast({"type":"spawn",**{k:v for k,v in msg.items() if k!="type"}},exclude=None)
                elif t=="custom" and self.on_custom:
                    self.on_custom(cid,msg)
        except Exception:
            traceback.print_exc()
        finally:
            try:
                _,w,_=self.clients.get(cid,(None,None,None))
                if w:
                    w.close()
                    await w.wait_closed()
            except:
                pass
            self.clients.pop(cid,None)
            if self.on_disconnect:
                self.on_disconnect(cid)
    async def broadcast(self,msg:dict,exclude:Optional[int]=None):
        dead=[]
        for cid,(r,w,_) in self.clients.items():
            if exclude is not None and cid==exclude:
                continue
            try:
                await write_message(w,msg,compress=self.compress)
            except:
                dead.append(cid)
        for cid in dead:
            try:
                _,w,_=self.clients.pop(cid,(None,None,None))
                if w:
                    w.close()
            except:
                pass
    async def tick(self):
        if not self.clients:
            return
        now=now_ms()
        for cid,(r,w,meta) in list(self.clients.items()):
            if now-meta["last"]>self.ping_interval_ms:
                try:
                    await write_message(w,{"type":"ping","t":now})
                except:
                    pass
        if self.state_provider:
            if now-self._last_broadcast>=int(1000/self.broadcast_hz):
                self._last_broadcast=now
                try:
                    data=self.state_provider() or []
                    await self.broadcast({"type":"state","objects":data,"ts":now})
                except:
                    pass
