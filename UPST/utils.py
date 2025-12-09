import pygame
from tkinter import filedialog
import sys
import os

def ensure_rgba_surface(surface):
    if not surface:
        return None
    if surface.get_bitsize() != 32:
        rgba = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
        rgba.blit(surface, (0, 0))
        return rgba
    return surface

def surface_to_bytes(surface):
    if not surface:
        return None
    rgba = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
    rgba.blit(surface, (0, 0))
    return pygame.image.tobytes(rgba, "RGBA")

def bytes_to_surface(data, size):
    if not data or not size or size[0] <= 0 or size[1] <= 0:
        return None
    expected = size[0] * size[1] * 4
    actual = len(data)
    if actual != expected:
        w = actual // (4 * size[1]) if size[1] > 0 else -1
        print(f"Size mismatch: declared {size}, but data suggests width ~{w} (len={actual}, expected={expected})")
        return None
    return pygame.image.frombytes(data, size, "RGBA")

def safe_filedialog(func, *args, freeze_watcher=None, **kwargs):
    if freeze_watcher:
        freeze_watcher.pause()
    try:
        return func(*args, **kwargs)
    finally:
        if freeze_watcher:
            freeze_watcher.resume()

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)