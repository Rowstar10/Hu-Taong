"""A match's sounds, 1.9 (Rowan's 1.9 plan, phase 1, steps 3-5).

"Ball hits differ by surface: paddle, wall, Middle Wall, tombstone, ferry gate, goal...  Each
talisman gets its own pickup sound, plus a main-moment sound where it fits ...  All sounds respect
volume and mute ...  Sounds play correctly online (each event once per player) and in replays."

Till 1.9 a bounce off a wall or a stone had no sound, every talisman's pickup made the same one,
and a stone breaking said "euugh", as a point does.  Now each surface and each talisman has its
own (core/match_sounds.py), and each is recorded as an event, so the friend online and a replay
play the same sound, once.
"""
import hashlib
import math
import os
import random
import unittest
import wave
from types import SimpleNamespace

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from config import BASE_W, SOUND_DIR                            # noqa: E402
from core import match_sounds                                   # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from core.states.replay_state import play_event                 # noqa: E402
from game import courts                                         # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, KINDS                         # noqa: E402
from game.replay import KIND_KEYS, Clip                         # noqa: E402

m = app.settings.match
sound = app.sound_manager
DATA = os.path.join(os.path.dirname(__file__), "data")


class Heard:
    """Every effect played while it's on: the names, in order."""
    def __enter__(self):
        self.names, self.play = [], sound.play
        sound.play = lambda name, *a, **k: (self.names.append(name), self.play(name, *a, **k))[1]
        match_sounds.heard.clear()
        return self.names

    def __exit__(self, *exc):
        sound.play = self.play


def match(court = 0, **rules):
    m.reset()
    m.powerups, m.court = False, court
    for name, value in rules.items():
        setattr(m, name, value)
    g = Hu_Taong(app)
    g.start()
    g.countdown, g.paused = None, False
    g.p1.ai_enabled = g.p2.ai_enabled = False
    return g


def aim(g, x, y, vx, vy):
    b, r = g.ball, g.ball.width / 2
    b.x0, b.x1, b.y0, b.y1 = x - r, x + r, y - r, y + r
    b.vx, b.vy = vx, vy


def run_until(g, done, seconds = 2.0):
    for _ in range(int(seconds * 120)):
        g.update(1 / 120)
        if done():
            return True
    return False


class Files(unittest.TestCase):
    def test_every_sound_is_there(self):
        for name in match_sounds.files():
            with self.subTest(name = name):
                with wave.open(str(SOUND_DIR / name)) as w:
                    self.assertEqual((w.getnchannels(), w.getframerate(), w.getsampwidth()), (1, 44100, 2))
                    self.assertGreater(w.getnframes(), 0.05 * 44100)

    def test_each_talisman_its_own(self):
        tunes = set()
        for kind in KINDS:
            data = (SOUND_DIR / match_sounds.talisman_file(kind.key)).read_bytes()
            tunes.add(hashlib.sha1(data).hexdigest())
        self.assertEqual(len(tunes), len(KINDS))

    def test_loaded_up_front(self):
        from core.sound_manager import SOUND_CACHE
        for name in match_sounds.files():
            self.assertIn(name, SOUND_CACHE, "(so the first bounce doesn't stall on the disk)")


class Surfaces(unittest.TestCase):
    """A bounce off each kind of surface: its own sound, heard once, and an event saying what it was."""
    def tearDown(self):
        m.reset()

    def bounce(self, g, x, y, vx, vy, kind):
        with Heard() as names:
            g.recorder.events.clear()
            aim(g, x, y, vx, vy)
            self.assertTrue(run_until(g, lambda: any(e[1] == kind for e in g.recorder.events)), kind)
        event = next(e for e in g.recorder.events if e[1] == kind)
        g.stop()
        return event, [n for n in names if n.startswith("Match/")]

    def test_the_top_and_bottom(self):
        event, names = self.bounce(match(), 700, 60, 300, -900, "wall")
        self.assertEqual(event[4], match_sounds.EDGE)
        self.assertEqual(len(names), 1)
        self.assertTrue(names[0].startswith("Match/edge_"))

    def test_the_middle_wall_has_none(self):
        """It only stops paddles: the ball goes through it, so there's no bounce to hear."""
        g = match(middle_wall = True)
        with Heard() as names:
            aim(g, BASE_W / 2 - 120, 540, 900, 0)
            run_until(g, lambda: g.ball.x0 > BASE_W / 2 + 40, 0.5)
        g.stop()
        self.assertGreater(g.ball.x0, BASE_W / 2, "(it went through)")
        self.assertEqual([n for n in names if n.startswith("Match/")], [])

    def test_tombstones_ferry_gates_and_long_walls(self):
        for index, want, stem in ((1, match_sounds.TOMB, "tomb"), (3, match_sounds.GATE, "gate"),
                                  (4, match_sounds.PILLAR, "pillar")):
            with self.subTest(court = courts.COURTS[index].name):
                g = match(index)
                stone = g.stones[0]
                cx, cy = (stone.x0 + stone.x1) / 2, (stone.y0 + stone.y1) / 2
                event, names = self.bounce(g, cx - 160, cy, 900, 0, "stone")
                self.assertEqual(event[4], want)
                self.assertTrue(names[0].startswith(f"Match/{stem}_"), names)

    def test_twin_balls_own_goal(self):
        g = match()
        g.powerups.split_ball()
        red = g.ball                                        # red's own goal is the left one
        red.side = "red"
        g.p1.y0, g.p1.y1 = 0, g.p1.height                  # (Red's paddle out of its way)
        r = red.width / 2
        red.x0, red.x1, red.y0, red.y1 = 160 - r, 160 + r, 700 - r, 700 + r
        red.vx, red.vy = -900.0, 0.0
        self.assertFalse(red.scores_in(1), "(the left goal is red's own: it turns the red ball back)")
        with Heard() as names:
            self.assertTrue(run_until(g, lambda: red.vx > 0, 1.0))
        g.stop()
        self.assertEqual(sum(n.startswith("Match/goal_") for n in names), 1, names)
        self.assertEqual(g.p2.score, 0)

    def test_harder_is_louder(self):
        ball = SimpleNamespace(speed = 600, vx = 600 * math.sqrt(2), vy = 0.0)
        soft = match_sounds.force(ball)
        ball.vx *= 3
        self.assertLess(soft, match_sounds.force(ball))
        self.assertEqual(soft, 0.0)

    def test_a_rattle_is_heard_once(self):
        with Heard() as names:
            for _ in range(5):
                match_sounds.play(app, "wall", (10, 10, match_sounds.EDGE, 0.5))
        self.assertEqual(len(names), 1)


class Talismans(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_each_pickup_plays_its_own_once(self):
        for kind in KINDS:
            with self.subTest(talisman = kind.name):
                g = match(powerups = True)
                item = {"kind": kind.key, "x": 900.0, "y": 300.0}
                with Heard() as names:
                    g.powerups.collect(item, g.p1)
                g.stop()
                self.assertEqual(names.count(match_sounds.talisman_file(kind.key)), 1, names)
                self.assertNotIn("countdown_go.wav", names, "(the one sound all 21 made till 1.9)")

    def test_moments_are_recorded_and_heard(self):
        g = match(powerups = True)
        cases = (
            ("portal", lambda: g.powerups.open_portals()),
            ("bang", lambda: g.powerups.collect({"kind": "cracker", "x": 900.0, "y": 300.0}, g.p1)),
        )
        for kind, start in cases:
            with self.subTest(moment = kind):
                g.recorder.events.clear()
                start()
                if kind == "portal":
                    door = g.powerups.portals[0]
                    aim(g, door["x"] - 60, door["y"], 700, 0)
                else:
                    g.powerups.cracker["fuse"] = 0.01
                with Heard() as names:
                    self.assertTrue(run_until(g, lambda: any(e[1] == kind for e in g.recorder.events), 1.5))
                want = "firecracker_bang.wav" if kind == "bang" else match_sounds.file_name(match_sounds.MOMENTS[kind])
                self.assertEqual(names.count(want), 1, names)
        g.stop()

    def test_a_broken_stone_is_no_longer_euugh(self):
        g = match(1)
        stone = g.stones[0]
        with Heard() as names:
            stone.damage(1)
            stone.damage(stone.max_hp)
        g.stop()
        self.assertNotIn("euugh.wav", names)
        self.assertIn("Match/crumble.wav", names)
        self.assertTrue(any(n.startswith("Match/chip_") for n in names))
        kinds = [e[1] for e in g.recorder.events]
        self.assertIn("chip", kinds)
        self.assertIn("crumble", kinds)

    def test_every_moment_has_a_sound(self):
        for kind in list(match_sounds.MOMENTS) + list(match_sounds.OLD_SOUNDS):
            with self.subTest(moment = kind):
                with Heard() as names:
                    match_sounds.play(app, kind, (1, 100.0, 100.0))
                self.assertEqual(len(names), 1)
                self.assertTrue((SOUND_DIR / names[0]).exists(), names)


class VolumeAndMute(unittest.TestCase):
    def tearDown(self):
        sound.reset()

    def test_effects_mute_silences_them(self):
        for muted in ("sfx_muted", "master_muted"):
            with self.subTest(muted = muted):
                sound.reset()
                setattr(sound, muted, True)
                match_sounds.heard.clear()
                self.assertIsNone(match_sounds.play(app, "wall", (10, 10, match_sounds.EDGE, 1.0)))
                self.assertIsNone(match_sounds.talisman(app, "hole"))

    def test_the_effects_slider_sets_their_volume(self):
        gains = []
        real = sound.gain
        sound.gain = lambda slider, multiplier = 1: (gains.append(slider * multiplier), real(slider, multiplier))[1]
        try:
            for level in (0.2, 0.8):
                sound.sfx_volume = level
                match_sounds.heard.clear()
                match_sounds.talisman(app, "giant")
        finally:
            sound.gain = real
        self.assertAlmostEqual(gains[1] / gains[0], 4.0)

    def test_menu_sounds_off_leaves_them_on(self):
        app.settings.audio.menu_sounds = False
        try:
            pygame.mixer.stop()                     # (nothing finishes playing without a sound card)
            match_sounds.heard.clear()
            self.assertIsNotNone(match_sounds.talisman(app, "giant"))
        finally:
            app.settings.audio.menu_sounds = True


class Elsewhere(unittest.TestCase):
    """The friend's screen online, and replays, play the events' sounds."""
    def view(self):
        ball = SimpleNamespace(x0 = 0.0, x1 = 20.0, y0 = 0.0, y1 = 20.0)
        return SimpleNamespace(p1 = SimpleNamespace(flash = 0.0), p2 = SimpleNamespace(flash = 0.0), ball = ball,
                               powerups = SimpleNamespace(popups = []), kind = lambda i: KIND_KEYS[int(i)])

    def test_replays_play_the_same_sounds(self):
        view = self.view()
        cases = ((("wall", (5.0, 5.0, match_sounds.GOAL, 0.5)), "Match/goal_"),
                 (("stone", (5.0, 5.0, match_sounds.GATE, 0.5)), "Match/gate_"),
                 (("pickup", (KIND_KEYS.index("lantern"), 1)), "Match/talisman_lantern.wav"),
                 (("sling", (5.0, 5.0)), "Match/goo_sling.wav"),
                 (("bang", (5.0, 5.0)), "firecracker_bang.wav"))
        for (kind, values), want in cases:
            with self.subTest(event = kind):
                with Heard() as names:
                    play_event(app, view, kind, values)
                self.assertEqual(len(names), 1, names)
                self.assertTrue(names[0].startswith(want), names)

    def test_events_from_before_1_9(self):
        view = self.view()
        for (kind, values), want in ((("wall", (5.0, 5.0)), "Match/edge_"), (("stone", (5.0, 5.0)), "Match/tomb_")):
            with Heard() as names:
                play_event(app, view, kind, values)
            self.assertTrue(names and names[0].startswith(want), (kind, names))

    def test_a_1_6_replay_plays_through(self):
        clip = Clip.load(os.path.join(DATA, "replay_1.6_gravity_frost.htreplay"))
        view = self.view()
        view.kind = clip.kind if hasattr(clip, "kind") else view.kind
        with Heard():
            for event in clip.events:
                play_event(app, view, event[1], event[2:])

    def guest(self, events, side = 2, quiet = -1.0):
        me = SimpleNamespace(app = app, view = self.view(), tau = 10.0, clock = 10.0, quiet_hit_until = quiet,
                             quiet_teleport_until = -1.0, pending = [(9.9, kind, values) for kind, values in events])
        with Heard() as names:
            GuestMatchState.play_due_events(me, side)
            GuestMatchState.play_due_events(me, side)       # (and again: nothing twice)
        return names

    def test_the_friend_hears_each_once(self):
        names = self.guest([("wall", (5.0, 5.0, match_sounds.EDGE, 0.5)), ("chip", (5.0, 5.0)),
                            ("pickup", (KIND_KEYS.index("wind"), 1)), ("blaze", (1,))])
        self.assertEqual(len(names), 4, names)
        self.assertIn("Match/talisman_wind.wav", names)

    def test_your_own_blazing_shot_isnt_heard_twice(self):
        """The friend's own Spirit Fire hit is heard the moment it's made on their screen; the host's
        word of it, a moment later, isn't played again."""
        names = self.guest([("blaze", (2,))], side = 2, quiet = 11.0)
        self.assertEqual(names, [])
        names = self.guest([("blaze", (1,))], side = 2, quiet = 11.0)
        self.assertEqual(names, ["Match/blaze.wav"])


if __name__ == "__main__":
    unittest.main()
