import pygame
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict


class FilterMode(Enum):
    NEAREST = 0
    BILINEAR = 1
    TRILINEAR = 2


@dataclass
class TextureState:
    rotation: float = 0.0
    scale: float = 1.0
    mirror_x: bool = False
    mirror_y: bool = False
    filter_mode: FilterMode = FilterMode.BILINEAR
    tiling_mode: str = 'clamp'
    blend_mode: str = 'normal'
    crop_rect: Tuple[int, int, int, int] = (0, 0, 128, 128)
    bg_color: Tuple[int, int, int] = (30, 30, 30)


class TextureCache:
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, pygame.Surface] = {}
        self.access_order: List[str] = []
        self.max_size = max_size

    def get(self, path: str) -> Optional[pygame.Surface]:
        if path in self.cache:
            self.access_order.remove(path)
            self.access_order.append(path)
            return self.cache[path]
        return None

    def set(self, path: str, surface: pygame.Surface):
        if path in self.cache:
            self.access_order.remove(path)
        elif len(self.cache) >= self.max_size:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        self.cache[path] = surface
        self.access_order.append(path)


class TextureProcessor:
    def __init__(self):
        self.cache = TextureCache()

    def _apply_transforms(self, surface: pygame.Surface, state: TextureState) -> pygame.Surface:
        processed = surface
        if state.rotation != 0:
            processed = pygame.transform.rotate(processed, state.rotation)
        if state.scale != 1.0:
            w, h = processed.get_size()
            new_w = max(1, int(w * state.scale))
            new_h = max(1, int(h * state.scale))
            if state.filter_mode == FilterMode.NEAREST:
                processed = pygame.transform.scale(processed, (new_w, new_h))
            else:
                processed = pygame.transform.smoothscale(processed, (new_w, new_h))
        if state.mirror_x:
            processed = pygame.transform.flip(processed, True, False)
        if state.mirror_y:
            processed = pygame.transform.flip(processed, False, True)
        return processed

    def _apply_tiling(self, surface: pygame.Surface, target_size: Tuple[int, int], mode: str) -> pygame.Surface:
        if mode == 'repeat':
            result = pygame.Surface(target_size, pygame.SRCALPHA)
            for x in range(0, target_size[0], surface.get_width()):
                for y in range(0, target_size[1], surface.get_height()):
                    result.blit(surface, (x, y))
            return result
        elif mode == 'mirror':
            result = pygame.Surface(target_size, pygame.SRCALPHA)
            w, h = surface.get_size()
            for x in range(0, target_size[0], w):
                for y in range(0, target_size[1], h):
                    tile = surface
                    if (x // w) % 2:
                        tile = pygame.transform.flip(tile, True, False)
                    if (y // h) % 2:
                        tile = pygame.transform.flip(tile, False, True)
                    result.blit(tile, (x, y))
            return result
        else:
            result = pygame.Surface(target_size, pygame.SRCALPHA)
            result.blit(surface, (0, 0))
            return result

    def process_texture(self, path: str, state: TextureState, target_size: Tuple[int, int]) -> pygame.Surface:
        cached_key = f"{path}_{hash(str(asdict(state)))}"
        cached = self.cache.get(cached_key)
        if cached:
            return cached

        img = pygame.image.load(path).convert_alpha()
        processed = self._apply_transforms(img, state)
        processed = self._apply_tiling(processed, target_size, state.tiling_mode)

        self.cache.set(cached_key, processed)
        return processed