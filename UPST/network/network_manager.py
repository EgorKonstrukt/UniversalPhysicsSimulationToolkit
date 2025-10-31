from __future__ import annotations

import asyncio,threading,queue,random,math
from typing import Any,Dict,Optional,List,Tuple,Callable
try:
    import pymunk
except ImportError:
    pymunk=None
from .host import Host
from .client import Client
from .protocol import now_ms
from UPST.modules.profiler import profile
Color=Tuple[int,int,int,int]
Vec2=Tuple[float,float]
class NetworkManager:
    def __init__(self,physics_manager=None,ui_manager=None,spawner=None,gizmos=None,console=None,token:str|None=None):
        self.physics_manager=physics_manager
        self.ui_manager=ui_manager
        self.spawner=spawner
        self.gizmos=gizmos
        self.console=console
        self.token=token
        self.role:Optional[str]=None
        self._loop:Optional[asyncio.AbstractEventLoop]=None
        self._thread:Optional[threading.Thread]=None
        self._host:Optional[Host]=None
        self._client:Optional[Client]=None
        self._objects:Dict[int,Any]={}
        self._next_id:int=1
        self._state_provider:Optional[Callable[[],List[dict]]]=None
        self._main_q:queue.SimpleQueue=queue.SimpleQueue()
        self._handlers:Dict[str,Callable[[dict],None]]={}
    @profile("UPSTNetworkLoop", "Network")
    def _ensure_loop(self):
        if self._loop and self._loop.is_running():
            return
        self._loop=asyncio.new_event_loop()
        self._thread=threading.Thread(target=self._loop.run_forever,name="UPSTNetworkLoop",daemon=True)
        self._thread.start()
    def _call(self,coro):
        asyncio.run_coroutine_threadsafe(coro,self._loop)
    def log(self,msg:str):
        try:
            if self.ui_manager and getattr(self.ui_manager,"console_window",None):
                self.ui_manager.console_window.add_output_line_to_log(msg)
            else:
                print("[Network]",msg)
        except:
            print("[Network]",msg)
    def start_host(self,port:int=7777):
        self._ensure_loop()
        self._host=Host(port=port,token=self.token)
        self._host.state_provider=self._collect_state
        self._host.on_input=self._on_client_input
        self._host.on_client=lambda cid,peer:self.log(f"Client {cid} {peer}")
        self._host.on_disconnect=lambda cid:self.log(f"Client {cid} disconnected")
        self._host.on_custom=lambda cid,msg:self._enqueue(("custom_from_client",cid,msg))
        self._call(self._host.start())
        self.role="host"
        self.log(f"Hosting 0.0.0.0:{port}")
    def stop_host(self):
        if self._host and self._loop:
            self._call(self._host.stop())
            self._host=None
            self.role=None
            self.log("Host stopped")
    def connect(self,host:str="127.0.0.1",port:int=7777):
        self._ensure_loop()
        self._client=Client(host,port,token=self.token)
        self._client.on_spawn=lambda msg:self._enqueue(("spawn",msg))
        self._client.on_state=lambda msg:self._enqueue(("state",msg))
        self._client.on_chat=lambda text:self.log(text)
        self._client.on_disconnect=lambda:self.log("Disconnected")
        self._client.on_custom=lambda msg:self._enqueue(("custom",msg))
        async def _run():
            await self._client.connect()
            await self._client.loop()
        self._call(_run())
        self.role="client"
        self.log(f"Connecting {host}:{port}")
    def disconnect(self):
        if self._client and self._loop:
            self._call(self._client.disconnect())
            self._client=None
            self.role=None
            self.log("Client disconnected")
    def send_chat(self,text:str):
        if self._client and self._loop:
            self._call(self._client.send({"type":"chat","text":text}))
        elif self._host:
            self._call(self._host.broadcast({"type":"chat","from":0,"text":text}))
    def broadcast_spawn(self,shape:str,position:Vec2,params:Optional[Dict[str,Any]]=None,seed:Optional[int]=None):
        if seed is None:
            seed=random.randint(0,1_000_000)
        msg={"type":"spawn","shape":shape,"position":position,"params":params or {},"seed":seed}
        if self.role=="host" and self._host:
            self._enqueue(("spawn_local",msg))
            self._call(self._host.broadcast({"type":"spawn",**msg}))
        elif self.role=="client" and self._client:
            self._call(self._client.send(msg))
        else:
            self._enqueue(("spawn_local",msg))
    def send_input(self,data:Dict[str,Any]):
        if self._client and self._loop:
            self._call(self._client.send({"type":"input","payload":data,"ts":now_ms()}))
    def update(self,dt:float):
        if self._host and self._loop:
            self._call(self._host.tick())
        while True:
            try:
                op=self._main_q.get_nowait()
            except:
                break
            self._process_main(op)
    def set_state_provider(self,fn:Callable[[],List[dict]]):
        self._state_provider=fn
    def register_handler(self,msg_type:str,fn:Callable[[dict],None]):
        self._handlers[msg_type]=fn
    def send_custom(self,payload:dict):
        if self.role=="client" and self._client:
            self._call(self._client.send({"type":"custom",**payload}))
        elif self.role=="host" and self._host:
            self._call(self._host.broadcast({"type":"custom",**payload}))
    def _enqueue(self,item):
        self._main_q.put(item)
    def _collect_state(self)->List[dict]:
        if self._state_provider:
            return self._state_provider()
        out=[]
        for oid,obj in self._objects.items():
            try:
                pos=[obj.position.x,obj.position.y] if hasattr(obj.position,"x") else list(obj.position)
                ang=float(getattr(obj,"angle",0.0))
                out.append({"id":oid,"pos":pos,"angle":ang})
            except:
                pass
        return out
    def _process_main(self,op):
        kind=op[0]
        if kind=="spawn":
            self._apply_spawn(op[1])
        elif kind=="spawn_local":
            self._apply_spawn(op[1])
        elif kind=="state":
            msg=op[1]
            if "state" in self._handlers:
                self._handlers["state"](msg)
        elif kind=="custom":
            msg=op[1]
            t=msg.get("subtype","custom")
            if t in self._handlers:
                self._handlers[t](msg)
        elif kind=="custom_from_client":
            cid,ms=op[1],op[2]
            t=ms.get("subtype","custom")
            if t in self._handlers:
                self._handlers[t]({"client_id":cid,**ms})
    def _apply_spawn(self,msg:Dict[str,Any]):
        shape=str(msg.get("shape",""))
        pos=tuple(msg.get("position",(0.0,0.0)))
        params=msg.get("params",{}) or {}
        seed=msg.get("seed",None)
        if seed is not None:
            random.seed(int(seed))
        try:
            if shape=="rectangle":
                size=tuple(params.get("size",(50.0,30.0)))
                friction=float(params.get("friction",0.5))
                elasticity=float(params.get("elasticity",0.2))
                color=tuple(params.get("color",(200,200,200,255)))
                body=self._spawn_rect(pos,size,friction,elasticity,color)
            elif shape=="circle":
                radius=float(params.get("radius",20.0))
                friction=float(params.get("friction",0.5))
                elasticity=float(params.get("elasticity",0.2))
                color=tuple(params.get("color",(200,200,200,255)))
                body=self._spawn_circle(pos,radius,friction,elasticity,color)
            elif shape=="triangle":
                size=tuple(params.get("size",(40.0,40.0)))
                friction=float(params.get("friction",0.5))
                elasticity=float(params.get("elasticity",0.2))
                color=tuple(params.get("color",(200,200,200,255)))
                body=self._spawn_triangle(pos,size,friction,elasticity,color)
            else:
                self.log(f"Unknown spawn {shape}")
                return
            oid=self._next_id
            self._next_id+=1
            self._objects[oid]=body
        except Exception as e:
            self.log(f"Spawn failed {e}")
    def _spawn_rect(self,position:Vec2,size:Vec2,friction:float,elasticity:float,color:Color):
        if not self.physics_manager or pymunk is None:
            raise RuntimeError("physics_manager/pymunk missing")
        w,h=size
        mass=(w*h)/200 if (w and h) else 10
        moment=pymunk.moment_for_box(mass,(w,h))
        body=pymunk.Body(mass,moment)
        body.position=position
        points=[(-w/2,-h/2),(-w/2,h/2),(w/2,h/2),(w/2,-h/2)]
        shape=pymunk.Poly(body,points)
        shape.friction=friction
        shape.elasticity=elasticity
        shape.color=color
        self.physics_manager.add_body_shape(body,shape)
        return body
    def _spawn_circle(self,position:Vec2,radius:float,friction:float,elasticity:float,color:Color):
        if not self.physics_manager or pymunk is None:
            raise RuntimeError("physics_manager/pymunk missing")
        mass=(math.pi*radius*radius)/200
        moment=pymunk.moment_for_circle(mass,0,radius)
        body=pymunk.Body(mass,moment)
        body.position=position
        shape=pymunk.Circle(body,radius)
        shape.friction=friction
        shape.elasticity=elasticity
        shape.color=color
        self.physics_manager.add_body_shape(body,shape)
        return body
    def _spawn_triangle(self,position:Vec2,size:Vec2,friction:float,elasticity:float,color:Color):
        if not self.physics_manager or pymunk is None:
            raise RuntimeError("physics_manager/pymunk missing")
        sx,sy=size
        pts=[(-sx/2,sy/2),(0,-sy/2),(sx/2,sy/2)]
        area=abs(sum(pts[i][0]*pts[(i+1)%3][1]-pts[(i+1)%3][0]*pts[i][1] for i in range(3)))/2
        mass=(area)/100 if area>0 else 10
        moment=pymunk.moment_for_poly(mass,pts)
        body=pymunk.Body(mass,moment)
        body.position=position
        shape=pymunk.Poly(body,pts)
        shape.friction=friction
        shape.elasticity=elasticity
        shape.color=color
        self.physics_manager.add_body_shape(body,shape)
        return body
    def _on_client_input(self,cid:int,msg:dict):
        if "input" in self._handlers:
            self._handlers["input"]({"client_id":cid,**msg})
