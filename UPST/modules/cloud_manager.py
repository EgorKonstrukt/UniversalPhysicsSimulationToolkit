import os, random, time, math, pygame
from pymunk import Vec2d
from collections import deque
from UPST.modules.profiler import profile

class CloudManager:
    def __init__(self, folder="clouds", cell_size=2048, clouds_per_cell=6, seed=12345,
                 scale_quant=0.05, scaled_cache_limit=400, max_px=512):
        self.folder = folder
        self.cell_size = cell_size
        self.per_cell = clouds_per_cell
        self.seed = seed
        self.textures = []
        self.cells = {}
        self.start_t = time.time()
        self.scaled_tex_cache = {}
        self.scaled_order = deque()
        self.scale_quant = scale_quant
        self.cache_limit = scaled_cache_limit
        self.max_px = max_px
        self._load_textures(folder)

    def _load_textures(self, folder):
        self.textures = []
        if not folder or not os.path.isdir(folder): return
        for fn in os.listdir(folder):
            p = os.path.join(folder, fn)
            try:
                tx = pygame.image.load(p).convert_alpha()
                self.textures.append(tx)
            except Exception:
                continue

    def set_folder(self, folder):
        if folder == self.folder: return
        self.folder = folder
        self._load_textures(folder)
        self.cells.clear()
        self.scaled_tex_cache.clear()
        self.scaled_order.clear()

    def _make_cell(self, cx, cy):
        seed_val = (cx * 73856093) ^ (cy * 19349663) ^ self.seed
        rnd = random.Random(seed_val)
        cs = self.cell_size
        base_x0 = cx * cs
        lst = []
        for _ in range(self.per_cell):
            tx = rnd.choice(self.textures) if self.textures else None
            rx = rnd.random() * cs
            ry = (rnd.random() - 0.5) * cs
            depth = rnd.uniform(0.25, 1.0)
            scale = rnd.uniform(0.6, 1.6)
            speed = rnd.uniform(15.0, 100.0)
            angle = 0.0
            phase = rnd.random() * 1000.0
            lst.append((tx, base_x0 + rx, cy * cs + ry, depth, scale, speed, angle, phase))
        self.cells[(cx, cy)] = lst
        return lst

    def _visible_cell_bounds(self, cam, sw, sh, margin=2):
        tl = cam.screen_to_world((0, 0))
        br = cam.screen_to_world((sw, sh))
        cs = self.cell_size
        cx0 = int(math.floor(min(tl[0], br[0]) / cs)) - margin
        cy0 = int(math.floor(min(tl[1], br[1]) / cs)) - margin
        cx1 = int(math.floor(max(tl[0], br[0]) / cs)) + margin
        cy1 = int(math.floor(max(tl[1], br[1]) / cs)) + margin
        return cx0, cy0, cx1, cy1

    def iter_visible_clouds(self, cam, sw, sh):
        cx0, cy0, cx1, cy1 = self._visible_cell_bounds(cam, sw, sh)
        t = time.time() - self.start_t
        cs = self.cell_size
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                key = (cx, cy)
                if key not in self.cells: self._make_cell(cx, cy)
                for tup in self.cells[key]:
                    tx, bx, by, depth, scale, speed, angle, phase = tup
                    wx = (bx + speed * t) % cs + cx * cs
                    wy = by
                    yield tx, wx, wy, depth, scale, angle

    def _evict_if_needed(self):
        while len(self.scaled_order) > self.cache_limit:
            old = self.scaled_order.popleft()
            if old in self.scaled_tex_cache:
                try:
                    del self.scaled_tex_cache[old]
                except KeyError:
                    pass

    def get_scaled_texture(self, tex, scale, angle=0.0, max_px=None):
        if not tex: return None
        if max_px is None: max_px = self.max_px
        q = max(self.scale_quant, self.scale_quant)
        scale_q = round(scale / q) * q
        if scale_q <= 0: return None
        a = 0.0 if abs(angle) < 0.01 else round(angle, 1)
        key = (id(tex), round(scale_q, 3), a)
        st = self.scaled_tex_cache.get(key)
        if st is not None:
            try:
                self.scaled_order.remove(key)
            except ValueError:
                pass
            self.scaled_order.append(key)
            return st
        w, h = tex.get_size()
        w_new = min(int(w * scale_q), max_px)
        h_new = min(int(h * scale_q), max_px)
        if w_new <= 0 or h_new <= 0: return None
        if a != 0.0:
            s = pygame.transform.rotozoom(tex, a, scale_q)
        else:
            if (w_new, h_new) == (w, h):
                s = tex
            else:
                s = pygame.transform.smoothscale(tex, (w_new, h_new))
        self.scaled_tex_cache[key] = s
        self.scaled_order.append(key)
        if len(self.scaled_order) > self.cache_limit:
            self._evict_if_needed()
        return s

class CloudRenderer:
    def __init__(self, screen, camera, clouds: CloudManager, min_px=32):
        self.screen = screen
        self.camera = camera
        self.clouds = clouds
        self.min_px = min_px

    @profile("Cloud Renderer", "Renderer")
    def draw(self):
        sw, sh = self.screen.get_size()
        cx_screen, cy_screen = sw * 0.5, sh * 0.5
        cam_scale = max(0.01, self.camera.scaling)
        t0 = time.time()
        get_tex = self.clouds.get_scaled_texture
        cam_w2s = self.camera.world_to_screen
        for tx, wx, wy, depth, scale, angle in self.clouds.iter_visible_clouds(self.camera, sw, sh):
            if not tx: continue
            final_scale = scale * cam_scale
            w, h = tx.get_size()
            if w * final_scale < self.min_px or h * final_scale < self.min_px: continue
            s = get_tex(tx, final_scale, angle, max_px=self.clouds.max_px)
            if not s: continue
            scr = cam_w2s((wx, wy))
            screen_x = cx_screen + (scr[0] - cx_screen) * depth
            screen_y = cy_screen + (scr[1] - cy_screen) * depth
            sx, sy = s.get_size()
            self.screen.blit(s, (screen_x - sx * 0.5, screen_y - sy * 0.5))
