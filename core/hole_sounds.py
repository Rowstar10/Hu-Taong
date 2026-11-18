"""Black holes are heard (1.8, Rowan's third playtest): a low hum while any is on the court, louder as
the Black Hole grows (a mini one hums softly); a deep "whoomp" each time one swallows a ball; and a roar
spinning up as the Black Hole collapses, ending in a boom as it bursts.  (The sounds were synthesised
for Hu Taong: see CREDITS.md.)

It's all worked out from the holes as they're shown, frame by frame, so a match, the friend's screen
online and a replay sound alike.  Whatever is showing them calls hear() each frame it plays on; when
nothing has for a moment (the match paused, a menu, the match over), the hum fades away.
"""
import time

import pygame

from game.powerups import PowerUps

HUM, SWALLOW, COLLAPSE = "black_hole_hum.wav", "black_hole_swallow.wav", "black_hole_collapse.wav"


class HoleSounds:
    HUM_OPEN = 0.3              # the hum's volume (a share of the effects slider) for a Black Hole just opened...
    HUM_GROWN = 0.65            # ...and full-grown...
    HUM_MINI = 0.12             # ...and for each mini one
    HUM_EASE = 3.0              # how quickly the hum follows them (per second)
    SWALLOW, SWALLOW_MINI = 0.7, 0.35
    COLLAPSE_LEVEL = 0.6        # (the loudest of them: it's the big moment)
    STALE = 0.15                # seconds without hear() before the hum fades away
    FADE_MS = 400
    SAME = 30                   # px: a hole this near where one was last frame is the same hole

    def __init__(self, sound):
        self.sound = sound      # the SoundManager
        self.hum = None         # the hum's channel, while it plays
        self.level = 0.0        # its volume now, easing towards what the holes call for
        self.heard = None       # when hear() was last called (time.perf_counter)
        self.seen = []          # last frame's holes: (kind, x, y, flash, collapse)

    def hear(self, holes):
        """The holes on the court this frame."""
        now = time.perf_counter()
        dt = min(0.1, now - self.heard) if self.heard is not None else 0.0
        self.heard = now
        want, seen = 0.0, []
        for hole in holes:
            if hole.get("dying") is not None:
                continue
            kind, x, y = hole["kind"], hole["x"], hole["y"]
            flash, collapse = hole.get("flash", 0.0), hole.get("collapse")
            mini = kind == PowerUps.HOLE_MINI
            if mini:
                want += self.HUM_MINI * hole.get("power", 1.0)
            elif collapse is None:
                most = PowerUps.HOLE_GROW * PowerUps.HOLE_GROWTHS
                grown = min(1.0, (hole.get("size", 1.0) - 1) / most) if most else 1.0
                want += (self.HUM_OPEN + (self.HUM_GROWN - self.HUM_OPEN) * grown) * hole.get("power", 1.0)
            before = self.last(kind, x, y)
            if before is not None and flash > before[3] + 0.3:
                self.play(SWALLOW, self.SWALLOW_MINI if mini else self.SWALLOW)    # its heart began to pulse
            if collapse is not None and (before[4] is None if before is not None else collapse < 0.1):
                self.play(COLLAPSE, self.COLLAPSE_LEVEL)
            seen.append((kind, x, y, flash, collapse))
        self.seen = seen
        self.level += (want - self.level) * min(1.0, dt * self.HUM_EASE)
        if want <= 0 and self.level < 0.01:
            self.quiet()
        elif self.level > 0.002 or want > 0:
            self.keep_humming()

    def last(self, kind, x, y):
        best, near = None, self.SAME
        for was in self.seen:
            gap = abs(was[1] - x) + abs(was[2] - y)
            if was[0] == kind and gap < near:
                best, near = was, gap
        return best

    def play(self, name, level):
        self.sound.play(name, multiplier = level)

    def keep_humming(self):
        if not pygame.mixer.get_init():
            return
        from core.sound_manager import HUM_CHANNEL, set_channel_volume
        snd = self.sound.sound(HUM)
        gain = self.sound.gain(self.sound.level("sfx"), self.level)
        if self.hum is None:
            if gain <= 0:
                return
            self.hum = pygame.mixer.Channel(HUM_CHANNEL)          # (its own: effects can't crowd it out)
            self.hum.play(snd, loops = -1)
        set_channel_volume(snd, self.hum, gain)

    def quiet(self):
        """The hum fades away."""
        if self.hum is not None:
            self.hum.fadeout(self.FADE_MS)
        self.hum, self.level = None, 0.0

    def tick(self):
        """Once a frame (SoundManager.update): if nothing has played the holes on lately, quiet."""
        if self.heard is not None and time.perf_counter() - self.heard > self.STALE:
            self.quiet()
            self.seen, self.heard = [], None
