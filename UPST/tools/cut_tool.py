import random
import pygame, math, pymunk
from UPST.config import config
from UPST.sound.sound_synthesizer import synthesizer
from UPST.tools.tool_manager import BaseTool
import pygame_gui

class CutTool(BaseTool):
    name = "Cut"
    icon_path = "sprites/gui/tools/cut.png"
    def __init__(self, pm):
        super().__init__(pm)
        self.start_pos=None
        self.thickness_entry=None
        self.remove_circles_cb=None
        self.keep_small_cb=None
        self._tmp_preview=None
    def create_settings_window(self):
        win=pygame_gui.elements.UIWindow(rect=pygame.Rect(200,10,360,160),manager=self.ui_manager.manager,window_display_title="Cut Settings")
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,120,20),text="Толщина (px):",manager=self.ui_manager.manager,container=win)
        self.thickness_entry=pygame_gui.elements.UITextEntryLine(relative_rect=pygame.Rect(130,10,80,20),initial_text="4",manager=self.ui_manager.manager,container=win)
        self.remove_circles_cb=pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10,40,240,20),text="Удалять круги при пересечении",manager=self.ui_manager.manager,container=win)
        self.keep_small_cb=pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10,65,240,20),text="Оставлять мелкие фрагменты",manager=self.ui_manager.manager,container=win)
        pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,95,320,40),text="Рисуйте линию — объекты, пересёкшиеся линией, будут разрезаны/удалены.",manager=self.ui_manager.manager,container=win)
        self.settings_window=win
    def _seg_seg_intersection(self,a1,a2,b1,b2):
        ax,ay=a1; bx,by=a2; cx,cy=b1; dx,dy=b2
        r=(bx-ax,by-ay); s=(dx-cx,dy-cy)
        denom=r[0]*s[1]-r[1]*s[0]
        if abs(denom)<1e-8: return None
        t=((cx-ax)*s[1]-(cy-ay)*s[0])/denom
        u=((cx-ax)*r[1]-(cy-ay)*r[0])/denom
        if 0<=t<=1 and 0<=u<=1:
            return (ax+t*r[0], ay+t*r[1])
        return None
    def _seg_circle_intersect(self,a,b,center,r):
        ax,ay=a; bx,by=b; cx,cy=center
        vx=bx-ax; vy=by-ay; ux=ax-cx; uy=ay-cy
        a_coef=vx*vx+vy*vy
        if a_coef==0: return (ux*ux+uy*uy)<=r*r
        b_coef=2*(ux*vx+uy*vy); c_coef=ux*ux+uy*uy-r*r
        disc=b_coef*b_coef-4*a_coef*c_coef
        if disc<0: return False
        sq=math.sqrt(disc); denom=2*a_coef
        if denom==0: return False
        t1=(-b_coef-sq)/denom; t2=(-b_coef+sq)/denom
        return (0<=t1<=1) or (0<=t2<=1)
    def _seg_circle_intersection_points(self,a,b,center,r):
        ax,ay=a; bx,by=b; cx,cy=center
        vx=bx-ax; vy=by-ay; ux=ax-cx; uy=ay-cy
        a_coef=vx*vx+vy*vy
        if a_coef==0:
            return []
        b_coef=2*(ux*vx+uy*vy); c_coef=ux*ux+uy*uy-r*r
        disc=b_coef*b_coef-4*a_coef*c_coef
        if disc<0: return []
        sq=math.sqrt(disc); denom=2*a_coef
        if denom==0: return []
        t1=(-b_coef-sq)/denom; t2=(-b_coef+sq)/denom
        pts=[]
        for t in (t1,t2):
            if 0<=t<=1:
                pts.append((ax+t*vx, ay+t*vy))
        return pts
    def _point_line_dist(self,p,a,b):
        ax,ay=a; bx,by=b; px,py=p
        lx=bx-ax; ly=by-ay; l2=lx*lx+ly*ly
        if l2==0: return math.hypot(px-ax,py-ay)
        t=max(0,min(1,((px-ax)*lx+(py-ay)*ly)/l2))
        proj=(ax+t*lx, ay+t*ly)
        return math.hypot(px-proj[0], py-proj[1])
    def _polygon_world_pts(self,poly):
        return [poly.body.local_to_world(v) for v in poly.get_vertices()]
    def _area_centroid(self,pts):
        a=0; cx=0; cy=0
        for i in range(len(pts)):
            x1,y1=pts[i]; x2,y2=pts[(i+1)%len(pts)]
            cross=x1*y2-x2*y1; a+=cross; cx+=(x1+x2)*cross; cy+=(y1+y2)*cross
        a=0.5*a
        if abs(a)<1e-8: return 0,(pts[0][0],pts[0][1])
        cx=cx/(6*a); cy=cy/(6*a)
        return abs(a),(cx,cy)
    def _create_poly_body(self,pts,proto_shape):
        area,cent=self._area_centroid(pts)
        if area<1e-2: return None
        local_pts=[(p[0]-cent[0], p[1]-cent[1]) for p in pts]
        mass=area/100
        if mass<=0: mass=0.001
        body=pymunk.Body(mass, pymunk.moment_for_poly(mass, local_pts))
        body.position=cent
        shape=pymunk.Poly(body, local_pts)
        shape.friction=getattr(proto_shape,"friction",0.7)
        shape.elasticity=getattr(proto_shape,"elasticity",0.5)
        shape.color=getattr(proto_shape,"color",(200,200,200,255))
        return body,shape
    def _remove_shape_and_maybe_body(self,shape):
        b=shape.body
        try:
            if shape in self.pm.space.shapes: self.pm.space.remove(shape)
        except Exception: pass
        try:
            if len(b.shapes)==0 and b in self.pm.space.bodies:
                try: self.pm.space.remove(b)
                except Exception: pass
        except Exception: pass
    def _split_poly_by_segment(self,poly,a,b):
        pts=self._polygon_world_pts(poly)
        inters=[]
        for i in range(len(pts)):
            p1=pts[i]; p2=pts[(i+1)%len(pts)]
            ip=self._seg_seg_intersection(a,b,p1,p2)
            if ip: inters.append((i,ip))
        if len(inters)!=2: return None
        (i1,ip1),(i2,ip2)=inters
        if i2<i1: i1,ip1,i2,ip2=i2,ip2,i1,ip1
        poly1=[]; poly1.extend(pts[i1+1:i2+1]); poly1.insert(0,ip1); poly1.append(ip2)
        poly2=[]; poly2.extend(pts[i2+1:]+pts[:i1+1]); poly2.insert(0,ip2); poly2.append(ip1)
        return poly1,poly2
    def _split_circle_by_segment(self, circle_shape, a, b):
        center = circle_shape.body.position; r = circle_shape.radius
        pts = self._seg_circle_intersection_points(a,b,center,r)
        if len(pts)!=2: return None
        p1,p2 = pts
        cx,cy=center
        ang1=math.atan2(p1[1]-cy, p1[0]-cx); ang2=math.atan2(p2[1]-cy, p2[0]-cx)
        def norm(a): return (a+2*math.pi)%(2*math.pi)
        a1=norm(ang1); a2=norm(ang2)
        delta1=(a2-a1)%(2*math.pi); delta2=(a1-a2)%(2*math.pi)
        def make_arc(start,delta):
            samples=max(20, int(delta/(math.pi/20)))
            pts=[(cx+math.cos(start+i*(delta/samples))*r, cy+math.sin(start+i*(delta/samples))*r) for i in range(1,samples)]
            return pts
        arc1 = make_arc(a1,delta1)
        poly1 = [p1] + arc1 + [p2]
        arc2 = make_arc(a2,delta2)
        poly2 = [p2] + arc2 + [p1]
        return [poly1, poly2]
    def _safe_add_body_shape(self,body,shape):
        try:
            self.pm.space.add(body,shape)
            return True
        except Exception:
            try:
                if body in self.pm.space.bodies:
                    try: self.pm.space.remove(body)
                    except Exception: pass
            except Exception: pass
            try:
                if shape in self.pm.space.shapes:
                    try: self.pm.space.remove(shape)
                    except Exception: pass
            except Exception: pass
            return False
    def _process_cut(self,a,b,thickness):
        to_remove_shapes=[]; to_add=[]
        for shape in list(self.pm.space.shapes):
            if shape.body==self.pm.static_body: continue
            if isinstance(shape,pymunk.Segment):
                p1=shape.a; p2=shape.b
                if self._seg_seg_intersection(a,b,p1,p2): to_remove_shapes.append(shape)
            elif isinstance(shape,pymunk.Circle):
                if self._seg_circle_intersect(a,b,shape.body.position,shape.radius):
                    if self.remove_circles_cb.get_state():
                        to_remove_shapes.append(shape)
                    else:
                        res=self._split_circle_by_segment(shape,a,b)
                        if res:
                            for pts in res:
                                new=self._create_poly_body(pts,shape)
                                if new: to_add.append(new)
                            to_remove_shapes.append(shape)
                        else:
                            to_remove_shapes.append(shape)
            elif isinstance(shape,pymunk.Poly):
                res=self._split_poly_by_segment(shape,a,b)
                if res:
                    p1_pts,p2_pts=res
                    new1=self._create_poly_body(p1_pts,shape)
                    new2=self._create_poly_body(p2_pts,shape)
                    if new1: to_add.append(new1)
                    if new2: to_add.append(new2)
                    to_remove_shapes.append(shape)
                else:
                    mind=min(self._point_line_dist(v,a,b) for v in self._polygon_world_pts(shape))
                    if mind<=thickness: to_remove_shapes.append(shape)
        for c in list(self.pm.space.constraints):
            a1=c.a.local_to_world(getattr(c,"anchor_a",(0,0))); a2=c.b.local_to_world(getattr(c,"anchor_b",(0,0)))
            if self._point_line_dist(a1,a,b)<=thickness or self._point_line_dist(a2,a,b)<=thickness:
                try: self.pm.space.remove(c)
                except: pass
        for sh in to_remove_shapes:
            try:
                self._remove_shape_and_maybe_body(sh)
            except Exception: pass
        for body,shape in to_add:
            added=self._safe_add_body_shape(body,shape)
            if not added and self.keep_small_cb and self.keep_small_cb.get_state():
                try:
                    if body in self.pm.space.bodies:
                        try: self.pm.space.remove(body)
                        except Exception: pass
                except Exception: pass
    def handle_event(self,event,world_pos):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            self.start_pos=world_pos; self._tmp_preview=(world_pos,world_pos)
        elif event.type==pygame.MOUSEMOTION and self.start_pos:
            self._tmp_preview=(self.start_pos,world_pos)
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1 and self.start_pos:
            a=self.start_pos; b=world_pos
            try: thickness=float(self.thickness_entry.get_text()) if self.thickness_entry else 4.0
            except: thickness=4.0
            self._process_cut(a,b,thickness)
            self.start_pos=None; self._tmp_preview=None
            synthesizer.play_frequency(300,duration=0.05,waveform='sine')
    def draw_preview(self,screen,camera):
        seg=self._tmp_preview
        if not seg: return
        a_screen=camera.world_to_screen(seg[0]); b_screen=camera.world_to_screen(seg[1])
        try: w=int(float(self.thickness_entry.get_text()) if self.thickness_entry else 4)
        except: w=4
        pygame.draw.line(screen,(255,100,100),a_screen,b_screen,w)


