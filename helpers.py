import pygame, math

from config import SOUND_DIR

# ------------------ Math helpers ------------------

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def reflect_in_range(y, lo, hi):
    i = 0
    while y < lo or y > hi:
        if y < lo:
            y = lo + (lo - y)
        else:
            y = hi - (y - hi)
        i += 1
    return y, i

def lerp(a, b, t):
    return a + (b - a) * t

def fit_text(text, max_width, start_size, bold=False):
    size = start_size

    while size > 10:
        font = pygame.font.SysFont("Helvetica", size, bold=bold)
        surf = font.render(text, True, (255,255,255))

        if surf.get_width() <= max_width:
            return font

        size -= 2

    return pygame.font.SysFont("Helvetica", 10, bold=bold)
