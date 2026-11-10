import json, pygame, random, time
from concurrent.futures import ThreadPoolExecutor

from config import SOUND_DIR, MUSIC_DIR
from helpers import split_volume

SOUND_CACHE = {}
DEFAULT_VOLUME = 0.5

# Effects that belong to the menus rather than the match; the Menu Sounds setting mutes these
MENU_SOUNDS = {"click.wav", "cancel.wav", "enter_state.wav", "exit_state.wav",
               "startup.wav", "startup2.wav", "shutdown.wav"}

# Even Out Volume brings tracks louder than this (gated RMS, dB) down to it.  Quieter
# tracks are left alone, since the mixer can't turn anything up past full volume.
TARGET_LOUDNESS = -19.0
AMBIENCE = (("Ambience Fire.wav", 1.0), ("Ambience Crickets.wav", 0.55))
MUSIC_CHANNELS = 2          # reserved for the jukebox: one fades out while the other fades in


def set_balance(channel, pan):
    """The channel's share of a split volume (see split_volume).  The mixer forgets it when the
    channel starts a new sound, so it is set after every play."""
    if channel is not None:
        level = (pan + 0.5) / 255          # the mixer truncates; this lands on `pan` exactly
        channel.set_volume(level, level)


def set_channel_volume(sound, channel, gain):
    """Hand a 0-1 gain to the mixer in full.  SDL_mixer keeps a volume in 128 steps, so a quiet
    setting used to snap to the quietest step (or to silence).  The sound's own volume and the
    channel's balance multiply, which gives about 32,000 steps instead."""
    chunk, pan = split_volume(gain)
    sound.set_volume(chunk)
    set_balance(channel, pan)


class SoundManager:
    def __init__(self, app):
        self.app = app

        self.multiplier = 1          # temporary music ducking (e.g. pause menu)
        self.track_gain = 1.0        # Even Out Volume's share for the current track
        self.ambience = []           # (channel, sound, level) while the ambience is playing
        self.reset()

        # Jukebox.  Tracks are decoded into memory on a worker thread and played on a channel of
        # their own, which gives the volume its full range, an exact length and seeking.
        self.mood = "menu"           # which group of tracks the jukebox is drawing from
        self.now_playing = None      # file name of the track that is (or is about to be) playing
        self.loudness = self.load_loudness()
        self.decoder = ThreadPoolExecutor(max_workers=1, thread_name_prefix="music")
        self.loading = None          # (track, future) while the next track is decoding
        self.music = None            # the track playing: see _start()
        self.music_paused = False
        self.next_channel = 0

        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(MUSIC_CHANNELS)
        self.preload_sounds()

    def reset(self):
        # Volume sliders (0-1).  Everything audible goes through gain() and set_channel_volume().
        self.master_volume = DEFAULT_VOLUME
        self.sfx_volume = DEFAULT_VOLUME
        self.music_volume = DEFAULT_VOLUME

        self.paddle_hit_sound = True
        self.score_sound = True
        self.update_music_volume()

    def close(self):
        self.decoder.shutdown(wait=True, cancel_futures=True)

    # ---------------- Volume ----------------

    def gain(self, slider, multiplier = 1):
        """A slider (0-1) times the master volume: what the listener should hear."""
        return max(0.0, min(1.0, slider * self.master_volume * multiplier))

    # ---------------- Sound effects ----------------

    def preload_sounds(self):
        """Load every effect up front so the first paddle hit doesn't stall on disk."""
        if not pygame.mixer.get_init():
            return
        for path in SOUND_DIR.glob("*.wav"):
            SOUND_CACHE[path.name] = pygame.mixer.Sound(str(path))

    def sound(self, name, folder = SOUND_DIR):
        snd = SOUND_CACHE.get(name)
        if snd is None:
            snd = SOUND_CACHE[name] = pygame.mixer.Sound(str(folder / name))
        return snd

    def play(self, name: str, loops = 0, multiplier = 1, slider = None, folder = SOUND_DIR):
        """Play an effect; returns its channel (None if it is muted or nothing was free)."""
        if not pygame.mixer.get_init():
            return None
        if name in MENU_SOUNDS and not self.app.settings.audio.menu_sounds:
            return None
        gain = self.gain(self.sfx_volume if slider is None else slider, multiplier)
        if gain <= 0:
            return None
        snd = self.sound(name, folder)
        chunk, pan = split_volume(gain)
        snd.set_volume(chunk)
        channel = snd.play(loops)
        set_balance(channel, pan)
        return channel

    def stop(self, name: str):
        snd = SOUND_CACHE.get(name)
        if snd:
            snd.stop()

    # ---------------- Music volume ----------------

    def update_music_volume(self):
        if not pygame.mixer.get_init():
            return
        music = getattr(self, "music", None)
        if music:
            gain = self.track_gain if self.app.settings.audio.even_volume else 1.0
            set_channel_volume(music["sound"], music["channel"],
                               self.gain(self.music_volume, self.multiplier * gain))
        for channel, sound, level in self.ambience:
            set_channel_volume(sound, channel, self.gain(self.sfx_volume, 0.5 * level * self.multiplier))

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
                sound = self.sound(name, SOUND_DIR / "Ambience")
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

    @property
    def fade_ms(self):
        audio = self.app.settings.audio
        return audio.fade_ms[audio.fade]

    def play_music(self, music: str):
        """Decode `music` on the worker thread; once it's ready the old track fades into it."""
        if not pygame.mixer.get_init():
            return
        self.now_playing = music
        self.app.renderer.show_toast("Now playing: " + self.app.settings.audio.track_name(music))
        self.loading = (music, self.decoder.submit(pygame.mixer.Sound, str(MUSIC_DIR / music)))

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

    def _start(self, music, sound):
        old = self.music
        if old:
            old["channel"].fadeout(self.fade_ms)
        channel = pygame.mixer.Channel(self.next_channel)
        self.next_channel = (self.next_channel + 1) % MUSIC_CHANNELS
        self.music = {"track": music, "sound": sound, "source": sound, "raw": None,
                      "channel": channel, "length": sound.get_length(),
                      "offset": 0.0, "started": time.perf_counter(), "paused_at": None}
        self.music_paused = False
        self.track_gain = self.gain_for(music)
        self.update_music_volume()
        channel.play(sound, fade_ms = self.fade_ms)
        self.update_music_volume()          # the balance is set again once the channel has started

    def stop_music(self):
        if self.music:
            self.music["channel"].stop()
        self.music = None
        self.loading = None

    # ---------------- Progress, pause and seeking ----------------

    def music_length(self):
        return self.music["length"] if self.music and not self.loading else 0.0

    def music_position(self):
        music = self.music
        if not music or self.loading:
            return 0.0
        if music["paused_at"] is not None:
            return music["paused_at"]
        return min(music["length"], music["offset"] + time.perf_counter() - music["started"])

    def toggle_music_pause(self):
        music = self.music
        if not music or self.loading:
            return
        if self.music_paused:
            music["offset"], music["started"] = music["paused_at"], time.perf_counter()
            music["paused_at"] = None
            music["channel"].unpause()
        else:
            music["paused_at"] = self.music_position()
            music["channel"].pause()
        self.music_paused = not self.music_paused

    def seek_music(self, seconds):
        """Jump to `seconds` into the current track, playing or paused as it was."""
        music = self.music
        if not music or self.loading or not pygame.mixer.get_init():
            return
        seconds = max(0.0, min(music["length"] - 0.05, seconds))
        if music["raw"] is None:
            music["raw"] = music["source"].get_raw()
        freq, size, channels = pygame.mixer.get_init()
        frame = abs(size) // 8 * channels
        start = int(seconds * freq) * frame
        music["sound"] = pygame.mixer.Sound(buffer = memoryview(music["raw"])[start:])
        self.update_music_volume()
        music["channel"].play(music["sound"], fade_ms = 30)
        self.update_music_volume()
        music["offset"], music["started"] = seconds, time.perf_counter()
        if self.music_paused:
            music["channel"].pause()
            music["paused_at"] = seconds

    def update(self):
        """Once per frame: start a track that has finished decoding, or move on when one ends."""
        if not pygame.mixer.get_init():
            return
        self.update_ambience()
        if self.loading:
            music, job = self.loading
            if job.done():
                self.loading = None
                try:
                    self._start(music, job.result())
                except Exception as e:          # an unreadable file: skip to another track
                    print(f"[sound_manager] could not play {music}: {e}")
                    if len(self.pool) > 1:
                        self.random_track()
            return
        music = self.music
        if music and not self.music_paused and not music["channel"].get_busy():
            self.track_finished()

    def track_finished(self):
        mode = self.app.settings.audio.play_mode
        if mode == 2 and self.music:
            self.seek_music(0.0)
        elif mode == 0:
            self.step_track(1)
        else:
            self.random_track()
