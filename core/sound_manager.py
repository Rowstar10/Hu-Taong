import pygame, random
from config import SOUND_DIR, MUSIC_DIR
from helpers import to_mixer_volume

SOUND_CACHE = {}
DEFAULT_VOLUME = 0.5

class SoundManager:
    def __init__(self, app):
        self.app = app

        self.multiplier = 1          # temporary music ducking (e.g. pause menu)
        self.reset()

        # Jukebox
        self.fade_out_ms = 1000
        self.fade_in_ms = 1000
        self.mood = "menu"           # which group of tracks the jukebox is drawing from
        self.now_playing = None      # file name of the track that is (or is about to be) playing
        self._pending = None         # track waiting for the current one to finish fading out

        self.preload_sounds()

    def reset(self):
        # Volume sliders (0-1).  Everything audible goes through volume() so the
        # mixer's 1/128 resolution is handled in exactly one place.
        self.master_volume = DEFAULT_VOLUME
        self.sfx_volume = DEFAULT_VOLUME
        self.music_volume = DEFAULT_VOLUME

        self.paddle_hit_sound = True
        self.score_sound = True
        self.update_music_volume()

    # ---------------- Volume ----------------

    def volume(self, slider, multiplier = 1):
        """Slider (0-1) -> the volume actually handed to the mixer."""
        return to_mixer_volume(slider * self.master_volume * multiplier)

    # ---------------- Sound effects ----------------

    def preload_sounds(self):
        """Load every effect up front so the first paddle hit doesn't stall on disk."""
        if not pygame.mixer.get_init():
            return
        for path in SOUND_DIR.glob("*.wav"):
            SOUND_CACHE[path.name] = pygame.mixer.Sound(str(path))

    def play(self, name: str, loops = 0, multiplier = 1):
        if not pygame.mixer.get_init():
            return

        snd = SOUND_CACHE.get(name)
        if snd is None:
            snd = pygame.mixer.Sound(str(SOUND_DIR / name))
            SOUND_CACHE[name] = snd

        snd.set_volume(self.volume(self.sfx_volume, multiplier))
        snd.play(loops)

    def stop(self, name: str):
        snd = SOUND_CACHE.get(name)
        if snd:
            snd.stop()

    # ---------------- Music volume ----------------

    def update_music_volume(self):
        if not pygame.mixer.get_init():
            return
        pygame.mixer.music.set_volume(self.volume(self.music_volume, self.multiplier))

    # ---------------- Jukebox ----------------
    # One jukebox, whatever state the game is in.  `mood` says which group of tracks
    # suits the moment (see AudioSettings.pools); the arrows, Randomise, Shuffle and
    # the automatic next track all stay inside the current mood.  Changing track
    # fades the old one out and starts the new one without blocking the game loop.

    @property
    def pool(self):
        return self.app.settings.audio.pools[self.mood]

    @property
    def display_track(self):
        return self.now_playing or self.pool[0]

    def play_music(self, music: str):
        """Fade out whatever is playing, then start `music`."""
        if not pygame.mixer.get_init():
            return
        self.now_playing = music
        self._pending = music
        self.app.renderer.show_toast("Now playing: " + self.app.settings.audio.track_name(music))
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(self.fade_out_ms)
        else:
            self._start_pending()

    def set_mood(self, mood):
        """Move the jukebox to `mood` (menu / game / victory / defeat) and play
        something from it that isn't what's already on."""
        self.mood = mood
        self.random_track()

    def step_track(self, step):
        """Previous (-1) / next (+1) track within the current mood."""
        pool = self.pool
        here = pool.index(self.now_playing) if self.now_playing in pool else (-1 if step > 0 else 0)
        self.play_music(pool[(here + step) % len(pool)])

    def random_track(self):
        """A random track from the current mood, other than the current one."""
        pool = self.pool
        self.play_music(random.choice([t for t in pool if t != self.now_playing] or pool))

    def _start_pending(self):
        music, self._pending = self._pending, None
        pygame.mixer.music.load(str(MUSIC_DIR / music))
        self.update_music_volume()
        pygame.mixer.music.play(fade_ms = self.fade_in_ms)

    def update(self):
        """Once per frame: finish a queued track change, or move on when a track ends."""
        if not pygame.mixer.get_init() or pygame.mixer.music.get_busy():
            return
        if self._pending is not None:
            self._start_pending()
        elif self.now_playing is not None:
            self.track_finished()

    def track_finished(self):
        if self.app.settings.audio.loop_music:
            self.play_music(self.now_playing)
        else:
            self.random_track()
