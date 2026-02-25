import pygame
from config import SOUND_DIR

SOUND_CACHE = {}

class SoundManager:
    def __init__(self):
        self.master_volume = 0.5
        self.paddle_enabled = True
        self.score_enabled = True

    def play(self, name: str, category: str = "general"):
        if not pygame.mixer.get_init():
            return

        # Category filtering
        if category == "paddle" and not self.paddle_enabled:
            return
        if category == "score" and not self.score_enabled:
            return

        snd = SOUND_CACHE.get(name)
        if snd is None:
            snd = pygame.mixer.Sound(str(SOUND_DIR / name))
            SOUND_CACHE[name] = snd

        snd.set_volume(self.master_volume)
        snd.play()
