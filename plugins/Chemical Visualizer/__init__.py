import pygame
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from UPST.config import Config

@dataclass
class Group:
    label: str
    x: float = 0.0
    y: float = 0.0

@dataclass
class Bond:
    g1: int
    g2: int
    style: str = 'solid'

@dataclass
class Molecule:
    groups: List[Group] = field(default_factory=list)
    bonds: List[Bond] = field(default_factory=list)

class RationalFormulaParser:
    def __init__(self, formula: str):
        self.s = formula.replace(' ', '')
        self.i = 0
    def parse(self) -> Molecule:
        mol = Molecule()
        groups = []
        while self.i < len(self.s):
            if self.s.startswith('CH', self.i):
                n = 3 if self.i + 2 < len(self.s) and self.s[self.i + 2].isdigit() else 2
                if n == 3:
                    groups.append(Group('CH'))
                    self.i += 3
                else:
                    groups.append(Group('CH'))
                    self.i += 2
            elif self.s.startswith('OH', self.i):
                groups.append(Group('OH'))
                self.i += 2
            elif self.s.startswith('C', self.i):
                groups.append(Group('C'))
                self.i += 1
            elif self.s.startswith('O', self.i):
                groups.append(Group('O'))
                self.i += 1
            else:
                self.i += 1
        mol.groups = groups
        for i in range(len(groups) - 1):
            mol.bonds.append(Bond(i, i + 1))
        return mol

@dataclass
class ChemicalVisualizerConfig:
    group_radius: float = 0.35
    bond_width: float = 0.1
    spacing: float = 2.0
    show_grid: bool = False
    color_scheme: dict = field(default_factory=lambda: {
        'CH': (128, 128, 128), 'OH': (160, 160, 160),
        'C': (100, 100, 100), 'O': (200, 100, 100),
        'default': (150, 150, 150)
    })

class ChemicalVisualizer:
    def __init__(self, app, cfg: ChemicalVisualizerConfig):
        self.app = app
        self.cfg = cfg
        self.font = pygame.font.SysFont(None, 20)
        self.current_mol: Optional[Molecule] = None
        self.active = False
    def set_molecule(self, mol: Molecule):
        self.current_mol = mol
        self.active = True
        self._layout_groups()
    def _layout_groups(self):
        if not self.current_mol: return
        for i, g in enumerate(self.current_mol.groups):
            g.x = i * self.cfg.spacing
            g.y = 0.0
    def draw(self):
        if not self.active or not self.current_mol or not (cam := self.app.camera): return
        mol = self.current_mol
        if self.cfg.show_grid:
            self._draw_grid(cam)
        for bond in mol.bonds:
            g1, g2 = mol.groups[bond.g1], mol.groups[bond.g2]
            p1 = cam.world_to_screen((g1.x, g1.y))
            p2 = cam.world_to_screen((g2.x, g2.y))
            width = max(1, int(self.cfg.bond_width * cam.scaling))
            pygame.draw.line(self.app.screen, (180, 180, 180), p1, p2, width)
        r_px = max(10, int(self.cfg.group_radius * cam.scaling))
        for group in mol.groups:
            pos = cam.world_to_screen((group.x, group.y))
            color = self.cfg.color_scheme.get(group.label, self.cfg.color_scheme['default'])
            pygame.draw.circle(self.app.screen, color, (int(pos[0]), int(pos[1])), r_px)
            txt = self.font.render(group.label, True, (255, 255, 255))
            self.app.screen.blit(txt, (int(pos[0]) - txt.get_width() // 2, int(pos[1]) - txt.get_height() // 2))
    def _draw_grid(self, cam):
        w, h = self.app.screen.get_size()
        step = 1.0
        for x in range(int(-w/2/cam.scaling), int(w/2/cam.scaling)+1):
            px = cam.world_to_screen((x * step, 0))[0]
            if 0 <= px <= w:
                pygame.draw.line(self.app.screen, (60,60,60), (px, 0), (px, h), 1)
        for y in range(int(-h/2/cam.scaling), int(h/2/cam.scaling)+1):
            py = cam.world_to_screen((0, y * step))[1]
            if 0 <= py <= h:
                pygame.draw.line(self.app.screen, (60,60,60), (0, py), (w, py), 1)

class PluginImpl:
    def __init__(self, app):
        self.app = app
        self.cfg = getattr(app.config, 'chemical_visualizer', ChemicalVisualizerConfig())
        self.vis = ChemicalVisualizer(app, self.cfg)
    def handle_chemical_formula(self, formula: str):
        try:
            mol = RationalFormulaParser(formula.strip()).parse()
            self.vis.set_molecule(mol)
        except Exception as e:
            print(f"Chemical parsing error: {e}")
            self.vis.active = False
    def on_event(self, ev):
        return False
    def on_draw(self):
        self.vis.draw()

PLUGIN = Plugin(
    name="chemical_visualizer",
    version="1.2",
    description="Simplified rational formula visualizer (semi-expanded form)",
    author="Zarrakun",
    icon_path="chem.png",
    dependency_specs={},
    config_class=ChemicalVisualizerConfig,
    on_load=lambda mgr, inst: setattr(mgr.app, 'chemical_plugin', inst),
    on_unload=lambda mgr, inst: delattr(mgr.app, 'chemical_plugin') if hasattr(mgr.app, 'chemical_plugin') else None,
    on_draw=lambda mgr, inst: inst.on_draw(),
    on_event=lambda mgr, inst, ev: inst.on_event(ev),
    console_commands={'chem': lambda inst, expr: inst.handle_chemical_formula(expr)}
)

Config.register_plugin_config("chemical_visualizer", ChemicalVisualizerConfig)