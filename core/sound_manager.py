import json, pygame, random
from config import SOUND_DIR, MUSIC_DIR
from helpers import to_mixer_volume

SOUND_CACHE = {}
DEFAULT_VOLUME = 0.5

# Effects that belong to the menus rather than the match; the Menu Sounds setting mutes these
MENU_SOUNDS = {"click.wav", "cancel.wav", "enter_state.wav", "exit_state.wav",
               "startup.wav", "startup2.wav", "shutdown.wav"}

# Even Out Volume brings tracks louder than this (gated RMS, dB) down to it.  Quieter
# tracks are left alone, since the mixer can't turn anything up past full volume.
TARGET_LOUDNESS = -19.0
AMBIENCE = (("Ambience Fire.wav", 1.0), ("Ambience Crickets.wav", 0.55))

class SoundManager:
    def __init__(self, app):
        self.app = app

        self.multiplier = 1          # temporary music ducking (e.g. pause menu)
        self.track_gain = 1.0        # Even Out Volume's share for the current track
        self.ambience = []           # (channel, sound, level) while the ambience is playing
        self.reset()

        # Jukebox
        self.mood = "menu"           # which group of tracks the jukebox is drawing from
        self.now_playing = None      # file name of the track that is (or is about to be) playing
        self._pending = None         # track waiting for the current one to finish fading out
        self.loudness = self.load_loudness()

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
        if name in MENU_SOUNDS and not self.app.settings.audio.menu_sounds:
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
        gain = self.track_gain if self.app.settings.audio.even_volume else 1.0
        pygame.mixer.music.set_volume(self.volume(self.music_volume, self.multiplier * gain))
        for channel, sound, level in self.ambience:
            channel.set_volume(self.volume(self.sfx_volume, 0.5 * level * self.multiplier))

    @staticmethod
    def load_loudness():
        """How loud each track is, measured once and kept beside the music."""
        try:
            return json.loads((MUSIC_DIR / "loudness.json").read_text())
        except (OSError, ValueError):
            return {}

    def gain_for(self, music):
        loud = self.loudness.get(music)
        if loud is None:
            return 1.0
        return min(1.0, 10 ** ((TARGET_LOUDNESS - loud) / 20))

    # ---------------- Ambience ----------------

    def update_ambience(self):
        setting = self.app.settings.audio.ambience
        wanted = self.app.running and (setting == 2 or (setting == 1 and not self.app.in_match()))
        if wanted and not self.ambience:
            for name, level in AMBIENCE:
                sound = SOUND_CACHE.get(name)
                if sound is None:
                    sound = SOUND_CACHE[name] = pygame.mixer.Sound(str(SOUND_DIR / "Ambience" / name))
                channel = sound.play(loops = -1, fade_ms = 2000)
                if channel:
                    self.ambience.append((channel, sound, level))
            self.update_music_volume()
        elif not wanted and self.ambience:
            for channel, sound, level in self.ambience:
                channel.fadeout(1500)
            self.ambience = []

    def stop_ambience(self):
        for channel, sound, level in self.ambience:
            channel.stop()
        self.ambience = []

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
            pygame.mixer.music.fadeout(self.fade_ms)
        else:
            self._start_pending()

    @property
    def fade_ms(self):
        audio = self.app.settings.audio
        return audio.fade_ms[audio.fade]

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
        self.track_gain = self.gain_for(music)
        self.update_music_volume()
        pygame.mixer.music.play(fade_ms = self.fade_ms)

    def update(self):
        """Once per frame: finish a queued track change, or move on when a track ends."""
        if not pygame.mixer.get_init():
            return
        self.update_ambience()
        if pygame.mixer.music.get_busy():
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
