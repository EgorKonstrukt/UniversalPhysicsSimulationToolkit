import pygame
import os
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass, field, asdict
from UPST.config import Config

@dataclass
class CollisionSoundConfig:
    enabled: bool = True
    volume: float = 0.5
    sound_path: str = "assets/sounds/collision.ogg"
    use_material_based: bool = False
    material_map: Dict[str, str] = field(default_factory=lambda: {
        "metal": "assets/sounds/metal.ogg",
        "wood": "assets/sounds/wood.ogg",
        "default": "assets/sounds/collision.ogg"
    })

    def _to_dict_custom(self, d: Dict) -> Dict:
        return d

    @classmethod
    def _from_dict_custom(cls, d: Dict) -> "CollisionSoundConfig":
        d.setdefault("enabled", True)
        d.setdefault("volume", 0.5)
        d.setdefault("sound_path", "assets/sounds/collision.ogg")
        d.setdefault("use_material_based", False)
        d.setdefault("material_map", {
            "metal": "assets/sounds/metal.ogg",
            "wood": "assets/sounds/wood.ogg",
            "default": "assets/sounds/collision.ogg"
        })
        return cls(**d)

class CollisionSoundHandler:
    def __init__(self, app, cfg: CollisionSoundConfig):
        self.app = app
        self.cfg = cfg
        self.plugin_dir = os.path.dirname(__file__)
        self.sound_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        pygame.mixer.set_num_channels(16)
        self._ensure_default_sound()
        self._load_sound(self.cfg.sound_path)
        if self.cfg.use_material_based:
            for path in self.cfg.material_map.values():
                self._load_sound(path)

    def _abs_path(self, rel_path: str) -> str:
        return os.path.join(self.plugin_dir, rel_path)

    def _generate_default_beep(self, duration=0.05, freq=880, sample_rate=22050) -> pygame.mixer.Sound:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(2 * np.pi * freq * t) * 0.3
        wave = (wave * 32767).astype(np.int16)
        return pygame.mixer.Sound(buffer=wave.tobytes())

    def _ensure_default_sound(self):
        default_rel = self.cfg.material_map.get("default", self.cfg.sound_path)
        default_abs = self._abs_path(default_rel)
        if not os.path.exists(default_abs):
            self.sound_cache[default_rel] = self._generate_default_beep()
            self.sound_cache[default_rel].set_volume(self.cfg.volume)

    def _load_sound(self, rel_path: str):
        if rel_path in self.sound_cache and self.sound_cache[rel_path] is not None:
            return
        abs_path = self._abs_path(rel_path)
        if os.path.exists(abs_path):
            try:
                snd = pygame.mixer.Sound(abs_path)
                snd.set_volume(self.cfg.volume)
                self.sound_cache[rel_path] = snd
                return
            except Exception as e:
                print(f"[CollisionSound] Failed to load {abs_path}: {e}")
        if rel_path == self.cfg.material_map.get("default", self.cfg.sound_path):
            self.sound_cache[rel_path] = self._generate_default_beep()
            self.sound_cache[rel_path].set_volume(self.cfg.volume)
        else:
            self.sound_cache[rel_path] = None

    def get_sound_for_bodies(self, a, b) -> Optional[pygame.mixer.Sound]:
        if not self.cfg.enabled:
            return None
        if not self.cfg.use_material_based:
            snd = self.sound_cache.get(self.cfg.sound_path)
            return snd if snd else self.sound_cache.get(self.cfg.material_map.get("default", self.cfg.sound_path))
        mat_a = getattr(a, 'material', 'default')
        mat_b = getattr(b, 'material', 'default')
        rel_path = self.cfg.material_map.get(mat_a, self.cfg.material_map['default'])
        if rel_path not in self.sound_cache or self.sound_cache[rel_path] is None:
            self._load_sound(rel_path)
        snd = self.sound_cache.get(rel_path)
        return snd if snd else self.sound_cache.get(self.cfg.material_map['default'])

class PluginImpl:
    def __init__(self, app):
        self.app = app
        self.cfg = getattr(app.config, 'collision_sound', CollisionSoundConfig())
        self.handler = CollisionSoundHandler(app, self.cfg)
        self._registered = False

    def register_handler(self):
        if self._registered:
            return
        physics_mgr = self.app.physics_manager
        if not physics_mgr:
            return
        space = getattr(physics_mgr, 'space', None)
        if not space:
            print("[CollisionSound] Error: physics space not available")
            return
        def _on_collision_begin(arbiter, space, data):
            a, b = arbiter.shapes[0].body, arbiter.shapes[1].body
            sound = self.handler.get_sound_for_bodies(a, b)
            if sound:
                sound.play()
            return True
        space.on_collision(0, 0, begin=_on_collision_begin)
        self._registered = True

PLUGIN = Plugin(
    name="collision_sound",
    version="1.0",
    description="Plays sound on physics body collisions",
    dependency_specs={},
    author="Zarrakun",
    icon_path="icon.png",
    config_class=CollisionSoundConfig,
    on_load=lambda mgr, inst: setattr(mgr.app, 'collision_sound_plugin', inst),
    on_unload=lambda mgr, inst: delattr(mgr.app, 'collision_sound_plugin') if hasattr(mgr.app, 'collision_sound_plugin') else None,
    on_update=lambda mgr, inst, dt: inst.register_handler()
)