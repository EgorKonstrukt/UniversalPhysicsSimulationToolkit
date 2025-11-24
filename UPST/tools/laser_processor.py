import math,pygame,pymunk,pygame.gfxdraw
from UPST.modules.profiler import profile
from UPST.debug.debug_manager import Debug
from UPST.config import config
opt=config.optics
opt.TRANSPARENCY=0.75
opt.MIN_WL=380;opt.MAX_WL=750;opt.N_SAMPLES=10
C_A=opt.C_A;C_B=opt.C_B
opt.EPS=1e-6;opt.ABSORB_THR=1e-3;opt.ALPHA_EPS=1e-6

try:
    import numpy as _np
    from numba import njit as _njit
    JIT_AVAILABLE=True
except:
    _njit=lambda f:f;_np=None;JIT_AVAILABLE=False

if JIT_AVAILABLE:
    @_njit(cache=True,fastmath=True)
    def _refr_index_nm(w):
        l=w/1000.0
        return C_A+C_B/(l*l)
    @_njit(cache=True,fastmath=True)
    def _reflect_dir(ix,iy,nx,ny):
        d=ix*nx+iy*ny
        rx=ix-2*d*nx;ry=iy-2*d*ny
        L=_np.hypot(rx,ry)
        return (rx/L,ry/L) if L>0 else (0.0,0.0)
    @_njit(cache=True,fastmath=True)
    def _refract_vec(ix,iy,nx,ny,n1,n2):
        d=-(ix*nx+iy*ny);r=n1/n2;k=1-r*r*(1-d*d)
        if k<0:return 0.0,0.0,0
        s=_np.sqrt(k)
        tx=r*ix+(r*d-s)*nx;ty=r*iy+(r*d-s)*ny
        L=_np.hypot(tx,ty)
        return (tx/L,ty/L,1) if L>0 else (0.0,0.0,1)
    @_njit(cache=True,fastmath=True)
    def _ang_from_vec(x,y):return _np.arctan2(y,x)
    @_njit(cache=True,fastmath=True)
    def _wl_to_rgb_f(w):
        r=g=b=0.0
        if 380<=w<440:r=-(w-440)/60;b=1
        elif 440<=w<490:g=(w-440)/50;b=1
        elif 490<=w<510:g=1;b=-(w-510)/20
        elif 510<=w<580:r=(w-510)/70;g=1
        elif 580<=w<645:r=1;g=-(w-645)/65
        elif 645<=w<=750:r=1
        if 380<=w<420:f=0.3+0.7*(w-380)/40
        elif 420<=w<=700:f=1
        else:f=0.3+0.7*(750-w)/50
        return r*f,g*f,b*f
else:
    def _refr_index_nm(w):return C_A+C_B/((w/1000.0)**2)
    def _reflect_dir(ix,iy,nx,ny):
        d=ix*nx+iy*ny;rx=ix-2*d*nx;ry=iy-2*d*ny
        L=math.hypot(rx,ry);return (rx/L,ry/L) if L>0 else (0.0,0.0)
    def _refract_vec(ix,iy,nx,ny,n1,n2):
        d=-(ix*nx+iy*ny);r=n1/n2;k=1-r*r*(1-d*d)
        if k<0:return 0.0,0.0,False
        s=math.sqrt(k);tx=r*ix+(r*d-s)*nx;ty=r*iy+(r*d-s)*ny
        L=math.hypot(tx,ty);return (tx/L,ty/L,True) if L>0 else (0.0,0.0,True)
    def _ang_from_vec(x,y):return math.atan2(y,x)
    def _wl_to_rgb_f(w):
        r=g=b=0.0
        if 380<=w<440:r=-(w-440)/60;b=1
        elif 440<=w<490:g=(w-440)/50;b=1
        elif 490<=w<510:g=1;b=-(w-510)/20
        elif 510<=w<580:r=(w-510)/70;g=1
        elif 580<=w<645:r=1;g=-(w-645)/65
        elif 645<=w<=750:r=1
        if 380<=w<420:f=0.3+0.7*(w-380)/40
        elif 420<=w<=700:f=1
        else:f=0.3+0.7*(750-w)/50
        return r*f,g*f,b*f

Debug.log_warning("JIT_AVAILABLE="+str(JIT_AVAILABLE))

def wl_to_rgb(w):
    r,g,b=_wl_to_rgb_f(w)
    clp=lambda x:int(max(0,min(x,1))*255)
    return clp(r),clp(g),clp(b)

def refr_index_nm(w):return _refr_index_nm(w)
def vec_from_ang(a):return math.cos(a),math.sin(a)
def ang_from_vec(x,y):return _ang_from_vec(x,y)
def reflect_dir(ix,iy,nx,ny):return _reflect_dir(ix,iy,nx,ny)
def refract_vec(ix,iy,nx,ny,n1,n2):
    tx,ty,ok=_refract_vec(ix,iy,nx,ny,n1,n2)
    return tx,ty,bool(ok)

class LaserRay:
    def __init__(self,p,a,L=30000):
        self.start=p;self.angle=a;self.length=L;self.segments=[]

class LaserProcessor:
    def __init__(self,pm,max_bounce=100):
        self.pm=pm;self.max_bounce=max_bounce;self.emitters=[];self._wl_cache={}
    def add_emitter(self,e):self.emitters.append(e)
    def remove_emitter(self,e):
        if e in self.emitters:self.emitters.remove(e)
    def update(self):
        for e in self.emitters:
            b=getattr(e,"attached_body",None)
            if b:
                try:e.pos=b.local_to_world(e.local_off);e.angle=b.angle+e.angle_off
                except:pass
            e.ray=self._compute_ray(e)
    @profile("Laser_compute_ray","LaserProcessor")
    def _compute_ray(self,e):
        pos=e.pos;ang0=e.angle;tot=e.length;sf=pymunk.ShapeFilter()
        sp=getattr(e,"spectrum",None)
        if sp:spec=sp
        else:
            n=getattr(e,"samples",opt.N_SAMPLES)
            mn=opt.MIN_WL;mx=opt.MAX_WL;d=(mx-mn)/(n-1)
            spec=[(mn+i*d,1.0) for i in range(n)]
        px,py=pos;segs=[];space=self.pm.space
        try:pqs=space.point_query((px,py),0,sf);inside0={id(q.shape) for q in pqs}
        except:inside0=set()
        stack=[];thr=opt.ABSORB_THR
        for w,i in spec:
            if i>thr:stack.append((px,py,ang0,tot,w,i,inside0))
        it=0;lim=self.max_bounce*len(spec)
        cos=math.cos;sin=math.sin;hyp=math.hypot;AL=opt.ALPHA_EPS;TR=opt.TRANSPARENCY;EPS=opt.EPS
        while stack and it<lim:
            it+=1;sx,sy,a,rem,wl,intn,ins=stack.pop()
            if rem<=0 or intn<=thr:continue
            ca,sa=cos(a),sin(a);ex=sx+ca*rem;ey=sy+sa*rem
            try:hits=space.segment_query((sx,sy),(ex,ey),0,sf)
            except:hits=[]
            h=None
            for q in hits:
                if q.alpha>AL:h=q;break
            if h is None:
                segs.append(((sx,sy),(ex,ey),wl,intn));continue
            hx=sx+(ex-sx)*h.alpha;hy=sy+(ey-sy)*h.alpha
            segs.append(((sx,sy),(hx,hy),wl,intn))
            nx,ny=h.normal.x,h.normal.y;d=hyp(hx-sx,hy-sy);rem2=rem-d;sid=id(h.shape)
            ent=sid not in ins;n_mat=refr_index_nm(wl)
            n1=1.0 if ent else n_mat;n2=n_mat if ent else 1.0
            tx,ty,ok=refract_vec(ca,sa,nx,ny,n1,n2)
            refl=intn*(1-TR);trans=intn*TR
            if refl>thr and rem2>0:
                rx,ry=reflect_dir(ca,sa,nx,ny);ax=rx*EPS;ay=ry*EPS
                stack.append((hx+ax,hy+ay,ang_from_vec(rx,ry),rem2,wl,refl,ins))
            if ok and trans>thr and rem2>0:
                new_ins=ins.copy()
                if ent:new_ins.add(sid)
                else:new_ins.discard(sid)
                ax=tx*EPS;ay=ty*EPS
                stack.append((hx+ax,hy+ay,ang_from_vec(tx,ty),rem2,wl,trans,new_ins))
        r=LaserRay(pos,ang0,tot);r.segments=segs;return r
    @profile("Laser_draw","LaserProcessor")
    def draw(self,scr,cam):
        to_scr=cam.world_to_screen;w,h=scr.get_size();ln=pygame.draw.line;wl_cache=self._wl_cache
        for e in self.emitters:
            r=getattr(e,"ray",None)
            if not r:continue
            lw=max(1,int(getattr(e,"width",2)))
            for s,e2,wl,i in r.segments:
                if i<=opt.ABSORB_THR:continue
                col=wl_cache.get(wl)
                if col is None:col=wl_to_rgb(wl);wl_cache[wl]=col
                sx,sy=to_scr(s);ex,ey=to_scr(e2)
                if (sx<0 and ex<0)or(sx>=w and ex>=w)or(sy<0 and ey<0)or(sy>=h and ey>=h):continue
                ln(scr,col,(int(sx),int(sy)),(int(ex),int(ey)),lw)
            ts=getattr(e,"tex_surf",None)
            if ts:
                p=to_scr(e.pos);ang=-math.degrees(e.angle);tc=getattr(e,"tex_cache",None)
                if tc is None:tc={};e.tex_cache=tc
                k=int(round(ang));img=tc.get(k)
                if img is None:img=pygame.transform.rotate(ts,ang);tc[k]=img
                rc=img.get_rect(center=(int(p[0]),int(p[1])))
                if rc.right>0 and rc.left<w and rc.bottom>0 and rc.top<h:scr.blit(img,rc)
