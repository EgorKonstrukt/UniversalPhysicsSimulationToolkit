
import pygame, math, pymunk
from UPST.tools.tool_manager import BaseTool
import pygame_gui
from pygame_gui.elements import UICheckBox

from UPST.config import config

class LaserEmitter:
    def __init__(self, pos, angle, length=3000, color=(255,40,40), width=2, tex_path="sprites/effects/laser_emitter.png"):
        self.pos = pos; self.angle = angle; self.length = length
        self.color = color; self.width = width
        self.ray = None
        self.attached_body = None; self.local_off = None; self.angle_off = 0
        try:
            base = pygame.image.load(tex_path).convert_alpha()
            self.tex_surf = base
        except Exception:
            self.tex_surf = None

class LaserTool(BaseTool):
    name = "Laser"; icon_path = "sprites/gui/tools/laserpen.png"
    def __init__(self, pm, laser_processor):
        super().__init__(pm)
        self.lp = laser_processor
        self.phase = 0
        self.tmp_pos = None; self.tmp_angle = 0
        self.preview = None
        # настройки (по-умолчанию)
        self.length = 30000; self.color = (255,40,40); self.attach_on_create = True
        self.tex_path = "sprites/app/laserpen.png"
        self.width = 2
        self.samples = config.optics.N_SAMPLES
        self.transparency = config.optics.TRANSPARENCY
        self.use_texture = True
        self.spectrum = None
        self._ui_refs = {}
    def create_settings_window(self):
        win = pygame_gui.elements.UIWindow(pygame.Rect(200, config.app.screen_height-360, 300, 30),
                                           manager=self.ui_manager.manager,
                                           window_display_title="Laser Settings")
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(320, 10, 64, 64),
                                    image_surface=pygame.image.load(self.icon_path),
                                    container=win, manager=self.ui_manager.manager)
        labels = [("Length:",10,10,80,20),("Width:",10,40,80,20),
                  ("R:",10,70,30,20),("G:",90,70,30,20),("B:",170,70,30,20),
                  ("Samples:",10,100,80,20),("Transparency:",10,130,100,20),
                  ("Texture:",10,160,80,20),("Spectrum (wl:int,...):",10,190,200,20)]
        for txt,x,y,w,h in labels:
            pygame_gui.elements.UILabel(relative_rect=pygame.Rect(x,y,w,h), text=txt, container=win, manager=self.ui_manager.manager)
        self._ui_refs['len_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.length), relative_rect=pygame.Rect(90,10,200,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['width_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.width), relative_rect=pygame.Rect(90,40,80,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['r_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.color[0]), relative_rect=pygame.Rect(40,70,40,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['g_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.color[1]), relative_rect=pygame.Rect(120,70,40,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['b_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.color[2]), relative_rect=pygame.Rect(200,70,40,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['samples_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.samples), relative_rect=pygame.Rect(100,100,80,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['trans_e'] = pygame_gui.elements.UITextEntryLine(initial_text=str(self.transparency), relative_rect=pygame.Rect(120,130,80,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['tex_e'] = pygame_gui.elements.UITextEntryLine(initial_text=self.tex_path, relative_rect=pygame.Rect(10,230,380,20), container=win, manager=self.ui_manager.manager)
        self._ui_refs['spectrum_e'] = pygame_gui.elements.UITextEntryLine(initial_text="", relative_rect=pygame.Rect(10,210,380,18), container=win, manager=self.ui_manager.manager)
        self._ui_refs['attach_cb'] = pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(10,260,200,20), text="Attach to body on create", manager=self.ui_manager.manager, container=win, initial_state=self.attach_on_create)
        self._ui_refs['use_tex_cb'] = pygame_gui.elements.UICheckBox(relative_rect=pygame.Rect(220,260,150,20), text="Use texture", manager=self.ui_manager.manager, container=win, initial_state=self.use_texture)
        self._ui_refs['apply_btn'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(10,290,120,30), text="Apply", container=win, manager=self.ui_manager.manager)
        self._ui_refs['close_btn'] = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(140,290,120,30), text="Close", container=win, manager=self.ui_manager.manager)
        self.settings_window = win
    def handle_event(self, event, world_pos):
        if event.type == pygame.USEREVENT:
            ui = getattr(event, 'ui_element', None)
            if ui == self._ui_refs.get('apply_btn'):
                try:
                    self.length = float(self._ui_refs['len_e'].get_text())
                    self.width = max(1, int(float(self._ui_refs['width_e'].get_text())))
                    r = int(self._ui_refs['r_e'].get_text()); g = int(self._ui_refs['g_e'].get_text()); b = int(self._ui_refs['b_e'].get_text())
                    self.color = (max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))
                    self.tex_path = self._ui_refs['tex_e'].get_text()
                    self.samples = max(1,int(float(self._ui_refs['samples_e'].get_text())))
                    tval = float(self._ui_refs['trans_e'].get_text()); self.transparency = max(0.0, min(1.0, tval))
                    globals()['TRANSPARENCY'] = self.transparency
                    self.attach_on_create = getattr(self._ui_refs['attach_cb'], 'checked', self.attach_on_create)
                    self.use_texture = getattr(self._ui_refs['use_tex_cb'], 'checked', self.use_texture)
                    spec_txt = self._ui_refs['spectrum_e'].get_text().strip()
                    if spec_txt:
                        pairs = [p.strip() for p in spec_txt.split(',') if p.strip()]
                        spec_list = []
                        for p in pairs:
                            if ':' in p:
                                wls,iv = p.split(':',1)
                                spec_list.append((float(wls), float(iv)))
                        self.spectrum = spec_list if spec_list else None
                    else:
                        self.spectrum = None
                except Exception:
                    pass
            # if ui == self._ui_refs.get('close_btn'):
            #     try: self.settings_window.kill()
            #     except Exception: pass
            if ui == self._ui_refs.get('attach_cb'):
                self.attach_on_create = getattr(self._ui_refs['attach_cb'], 'checked', self.attach_on_create)
            if ui == self._ui_refs.get('use_tex_cb'):
                self.use_texture = getattr(self._ui_refs['use_tex_cb'], 'checked', self.use_texture)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.phase == 0:
                self.tmp_pos = world_pos; self.phase = 1; self.preview = None
            elif self.phase == 1:
                em = LaserEmitter(self.tmp_pos, self.tmp_angle, length=self.length, color=self.color, width=self.width, tex_path=self.tex_path)
                em.samples = getattr(self, 'samples', config.optics.N_SAMPLES)
                if getattr(self, 'spectrum', None):
                    em.spectrum = list(self.spectrum)
                em.use_texture = getattr(self, 'use_texture', True)
                if self.attach_on_create:
                    info = self.pm.space.point_query_nearest(self.tmp_pos, 0, pymunk.ShapeFilter())
                    body = info.shape.body if info and info.shape and info.shape.body != self.pm.static_body else None
                    if body:
                        em.attached_body = body
                        em.local_off = body.world_to_local(self.tmp_pos)
                        em.angle_off = em.angle - body.angle
                if em.use_texture:
                    if em.tex_surf:
                        try:
                            surf = pygame.image.load(em.tex_surf.get_abs_path()) if hasattr(em.tex_surf, 'get_abs_path') else em.tex_surf
                        except Exception:
                            try:
                                surf = pygame.image.load(self.tex_path).convert_alpha()
                            except Exception:
                                surf = None
                        if surf:
                            copy = surf.copy()
                            tint = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
                            tint.fill((*em.color, 0))
                            copy.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
                            em.tex_surf = copy
                    else:
                        try:
                            surf = pygame.image.load(self.tex_path).convert_alpha()
                            copy = surf.copy()
                            tint = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
                            tint.fill((*em.color, 0))
                            copy.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
                            em.tex_surf = copy
                        except Exception:
                            em.tex_surf = None
                else:
                    em.tex_surf = None
                self.lp.add_emitter(em)
                self.phase = 0; self.preview = None
            self.undo_redo.take_snapshot()

        if event.type == pygame.MOUSEMOTION and self.phase == 1:
            dx = world_pos[0] - self.tmp_pos[0]; dy = world_pos[1] - self.tmp_pos[1]
            self.tmp_angle = math.atan2(dy, dx)
            self.preview = {"pos": self.tmp_pos, "angle": self.tmp_angle}
    def _draw_custom_preview(self, screen, camera):
        if not self.preview: return
        p = camera.world_to_screen(self.preview["pos"]); ang = self.preview["angle"]
        end = (p[0] + math.cos(ang) * 90, p[1] + math.sin(ang) * 90)
        pygame.draw.line(screen, self.color, p, end, max(1,self.width))
        pygame.draw.circle(screen, self.color, p, 5, 1)
    def deactivate(self):
        super().deactivate(); self.phase = 0; self.preview = None
