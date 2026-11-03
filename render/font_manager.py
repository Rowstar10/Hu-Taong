import pygame

from config import FONT_DIR


class FontManager:
    FILES = {"brush": "MaShanZheng-Regular.ttf",
             "ui": "Philosopher-Regular.ttf",
             "ui_bold": "Philosopher-Bold.ttf"}

    def __init__(self):
        self.cache = {}

    def get(self, name="ui", size=24, bold=False, italic=False):

        if name not in self.FILES:
            name = "ui"

        if name == "ui" and bold:
            name = "ui_bold"

        key = (name, size, italic)

        if key not in self.cache:
            font = pygame.font.Font(str(FONT_DIR / self.FILES[name]), size)
            font.set_italic(italic)
            self.cache[key] = font

        return self.cache[key]

    def clear(self):
        self.cache.clear()
