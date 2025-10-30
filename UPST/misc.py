import io
import pygame

def surface_to_bytes(surface):
    if not surface:
        return None
    return pygame.image.tobytes(surface, "RGBA")

def bytes_to_surface(data, size, alpha=True):
    if not data or not size or size[0] <= 0 or size[1] <= 0:
        return None
    expected_len = size[0] * size[1] * (4 if alpha else 3)
    if len(data) != expected_len:
        print(f"Warning: byte length {len(data)} != expected {expected_len} for size {size}")
        return None
    fmt = "RGBA" if alpha else "RGB"
    return pygame.image.frombytes(data, size, fmt)