from typing import Dict,Any
from UPST.network import NetworkManager
def get_network_api(net:NetworkManager)->Dict[str,Any]:
    return {
        "net_host":lambda port=7777:net.start_host(int(port)),
        "net_stop":lambda:(net.stop_host() if net.role=="host" else net.disconnect()),
        "net_connect":lambda host="127.0.0.1",port=7777:net.connect(str(host),int(port)),
        "net_chat":lambda text="":net.send_chat(str(text)),
        "net_spawn_rect":lambda x=0.0,y=0.0,w=60.0,h=30.0,fr=0.5,el=0.2:net.broadcast_spawn("rectangle",(float(x),float(y)),{"size":(float(w),float(h)),"friction":float(fr),"elasticity":float(el)}),
        "net_spawn_circle":lambda x=0.0,y=0.0,r=20.0,fr=0.5,el=0.2:net.broadcast_spawn("circle",(float(x),float(y)),{"radius":float(r),"friction":float(fr),"elasticity":float(el)}),
        "net_spawn_triangle":lambda x=0.0,y=0.0,sx=40.0,sy=40.0,fr=0.5,el=0.2:net.broadcast_spawn("triangle",(float(x),float(y)),{"size":(float(sx),float(sy)),"friction":float(fr),"elasticity":float(el)}),
        "net_send":lambda payload={}:net.send_custom(dict(payload))
    }
