import io
import pygame

def surface_to_bytes(surface):
    if not surface: return None
    with io.BytesIO() as bio:
        pygame.image.save(surface, bio, "png")
        return bio.getvalue()

def bytes_to_surface(data):
    if not data: return None
    with io.BytesIO(data) as bio:
        return pygame.image.load(bio).convert_alpha()