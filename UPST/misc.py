import pygame

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