import math, pygame, pymunk
from UPST.modules.profiler import profile
TRANSPARENCY=0.75
MIN_WL=380; MAX_WL=750; N_SAMPLES=10
C_A=1.514; C_B=0.0042
EPS=1e-6; ABSORB_THR=1e-3; ALPHA_EPS=1e-6

def wl_to_rgb(wl):
    w=wl; r=g=b=0.0
    if 380<=w<440: r=-(w-440)/(440-380); b=1.0
    elif 440<=w<490: g=(w-440)/(490-440); b=1.0
    elif 490<=w<510: g=1.0; b=-(w-510)/(510-490)
    elif 510<=w<580: r=(w-510)/(580-510); g=1.0
    elif 580<=w<645: r=1.0; g=-(w-645)/(645-580)
    elif 645<=w<=750: r=1.0
    if 380<=w<420: f=0.3+(0.7*(w-380)/(420-380))
    elif 420<=w<=700: f=1.0
    else: f=0.3+(0.7*(750-w)/(750-700))
    return tuple(int(max(0,min(1,x*f))*255) for x in (r,g,b))

def refr_index_nm(wl_nm):
    lam_um=wl_nm/1000.0
    return C_A + C_B/(lam_um*lam_um)

def vec_from_ang(a): return math.cos(a), math.sin(a)
def ang_from_vec(vx,vy): return math.atan2(vy,vx)
def reflect_dir(ix,iy,nx,ny):
    dot=ix*nx+iy*ny
    rx=ix-2*dot*nx; ry=iy-2*dot*ny
    L=math.hypot(rx,ry)
    return (rx/L,ry/L) if L>0 else (0.0,0.0)

def refract_vec(ix,iy,nx,ny,n1,n2):
    dot=-(ix*nx+iy*ny)
    ratio=n1/n2
    k=1-ratio*ratio*(1-dot*dot)
    if k<0: return (0.0,0.0,False)
    srt=math.sqrt(k)
    tx=ratio*ix + (ratio*dot-srt)*nx
    ty=ratio*iy + (ratio*dot-srt)*ny
    L=math.hypot(tx,ty)
    if L<=0: return (0.0,0.0,True)
    return (tx/L,ty/L,True)

class LaserRay:
    def __init__(self,start,angle,length=30000):
        self.start=start; self.angle=angle; self.length=length; self.segments=[]

class LaserProcessor:
    def __init__(self,pm,max_bounce=100):
        self.pm=pm; self.max_bounce=max_bounce; self.emitters=[]
        self._wl_cache={}
    def add_emitter(self,em): self.emitters.append(em)
    def remove_emitter(self,em):
        if em in self.emitters: self.emitters.remove(em)
    def update(self):
        for em in self.emitters:
            b=getattr(em,"attached_body",None)
            if b:
                try:
                    em.pos=b.local_to_world(em.local_off); em.angle=b.angle+em.angle_off
                except: pass
            em.ray=self._compute_ray(em)
    @profile("Laser_compute_ray","LaserProcessor")
    def _compute_ray(self,em):
        pos=em.pos; ang0=em.angle; total_len=em.length
        samples=getattr(em,"spectrum",None)
        if samples: spec=[(wl,iv) for wl,iv in samples]
        else:
            n=getattr(em,"samples",N_SAMPLES)
            spec=[(MIN_WL + i*(MAX_WL-MIN_WL)/(n-1),1.0) for i in range(n)]
        sx0,sy0=pos; segs=[]
        sf=pymunk.ShapeFilter(); space=self.pm.space
        try:
            pqs=space.point_query((sx0,sy0),0.0,sf)
            init_inside={id(pq.shape) for pq in pqs}
        except Exception:
            init_inside=set()
        stack=[]
        for wl,rel in spec:
            if rel<=ABSORB_THR: continue
            stack.append((sx0,sy0,ang0,total_len,wl,rel,set(init_inside)))
        iters=0; max_iter=self.max_bounce*len(spec)
        cos=math.cos; sin=math.sin; hypot=math.hypot; atan2=math.atan2
        while stack and iters<max_iter:
            iters+=1
            sx,sy,ang,rem,wl,inten,inside = stack.pop()
            if inten<ABSORB_THR or rem<=0: continue
            ca,sa = cos(ang), sin(ang)
            ex=sx+ca*rem; ey=sy+sa*rem
            try:
                hits=space.segment_query((sx,sy),(ex,ey),0.0,sf)
            except Exception:
                hits=[]
            if not hits:
                segs.append(((sx,sy),(ex,ey),wl,inten)); continue
            hit=None
            for h in hits:
                if h.alpha>ALPHA_EPS:
                    hit=h; break
            if hit is None:
                segs.append(((sx,sy),(ex,ey),wl,inten)); continue
            hx = sx + (ex-sx)*hit.alpha; hy = sy + (ey-sy)*hit.alpha
            segs.append(((sx,sy),(hx,hy),wl,inten))
            nx,ny = hit.normal.x, hit.normal.y
            d = hypot(hx-sx,hy-sy); rem2 = rem - d
            sid = id(hit.shape)
            entering = sid not in inside
            n_mat = refr_index_nm(wl)
            n1 = 1.0 if entering else n_mat
            n2 = n_mat if entering else 1.0
            tx,ty,ok = refract_vec(ca,sa,nx,ny,n1,n2)
            refl_int = inten*(1-TRANSPARENCY); trans_int = inten*TRANSPARENCY
            rx,ry = reflect_dir(ca,sa,nx,ny)
            if refl_int>ABSORB_THR and rem2>0:
                sx2,sy2 = hx+rx*EPS, hy+ry*EPS
                stack.append((sx2,sy2,ang_from_vec(rx,ry),rem2,wl,refl_int,set(inside)))
            if ok and trans_int>ABSORB_THR and rem2>0:
                inside_new = set(inside)
                if entering: inside_new.add(sid)
                else: inside_new.discard(sid)
                sx2,sy2 = hx+tx*EPS, hy+ty*EPS
                stack.append((sx2,sy2,ang_from_vec(tx,ty),rem2,wl,trans_int,inside_new))
        res=LaserRay(pos,ang0,total_len); res.segments=segs; return res
    @profile("Laser_draw", "LaserProcessor")
    def draw(self, screen, camera):
        cam_to_screen=camera.world_to_screen; draw_line=pygame.draw.line; wl_cache=self._wl_cache
        for em in self.emitters:
            r = getattr(em, "ray", None)
            if not r: continue
            w = max(1, int(getattr(em, "width", 2)))
            segs = r.segments
            for s,e,wl,inten in segs:
                if inten<=ABSORB_THR: continue
                col = wl_cache.get(wl)
                if col is None:
                    col = wl_to_rgb(wl); wl_cache[wl]=col
                sx,sy = cam_to_screen(s); ex,ey = cam_to_screen(e)
                draw_line(screen, col, (int(sx),int(sy)), (int(ex),int(ey)), w)
            surf = getattr(em, "tex_surf", None)
            if surf:
                pos = cam_to_screen(em.pos)
                angle_deg = -math.degrees(em.angle)
                tex_cache = getattr(em, "tex_cache", None)
                if tex_cache is None:
                    tex_cache = {}; em.tex_cache = tex_cache
                key = int(round(angle_deg))  # discretize to avoid tiny diffs
                img = tex_cache.get(key)
                if img is None:
                    img = pygame.transform.rotate(surf, angle_deg); tex_cache[key]=img
                rect = img.get_rect(center=(int(pos[0]),int(pos[1])))
                screen.blit(img, rect)
