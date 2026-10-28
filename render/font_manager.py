import pygame


class FontManager:

    def __init__(self):
        self.cache = {}

    def get(self, name="helvetica", size=24, bold=False, italic=False):

        key = (name, size, bold, italic)

        if key not in self.cache:
            font = pygame.font.SysFont(name, size, bold=bold, italic=italic)
            self.cache[key] = font

        return self.cache[key]
        
    def clear(self):
        self.cache.clear()
