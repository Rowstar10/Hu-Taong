import pygame, random
from config import SOUND_DIR, MUSIC_DIR

SOUND_CACHE = {}

class SoundManager:
    def __init__(self, app):
        self.app = app
        self.master_volume = 0.5
        self.sfx_volume = 0.5
        self.music_volume = 0.5
        self.multiplier = 1

        self.music_type = "menu"
        self.paddle_hit_sound = True
        self.score_sound = True

    def play(self, name: str, loops = 0, multiplier = 1):
        if not pygame.mixer.get_init():
            return

        snd = SOUND_CACHE.get(name)
        if snd is None:
            snd = pygame.mixer.Sound(str(SOUND_DIR / name))
            SOUND_CACHE[name] = snd

        volume = self.sfx_volume * self.master_volume * multiplier
        volume = max(0, min(volume, 1))
        snd.set_volume(volume)
        snd.play(loops)

    def stop(self, name: str):
        snd = SOUND_CACHE.get(name)
        snd.stop()

    def play_music(self, music: str, fade_out_ms = 1000, fade_in_ms = 1000, **kwargs):
        if not pygame.mixer.get_init():
            return
        
        if "music_type" in kwargs:
            self.music_type = kwargs.get("music_type")

        if pygame.mixer.music.get_busy():
            self.app.ignore_music_end = True
            pygame.mixer.music.fadeout(fade_out_ms)
        pygame.mixer.music.load(str(MUSIC_DIR / music))
        self.update_music_volume()
        pygame.mixer.music.play(fade_ms = fade_in_ms)
            
    def update_music_volume(self):
        if not pygame.mixer.get_init():
            return
        
        volume = self.music_volume * self.master_volume * self.multiplier
        volume = max(0, min(volume, 1))
        pygame.mixer.music.set_volume(volume)

        
