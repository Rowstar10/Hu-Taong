"""A ball squeezed between two paddles rattles again, 1.8 (Rowan's fourth 1.8 playtest, 2026-11-18).

"When two paddles sandwich the ball and push towards each other (eg. it's open court), in v1.6 and
onwards it flings the ball out of the sandwich, but in v1.5 it keeps the ball bouncing between the
two rapidly and indefinitely, which feels more fun to play."

So, as in 1.5, it rattles between them for as long as both press in, and the paddles can't pass
through each other while it does.  Unlike 1.5 it holds at any frame rate: in 1.5 it crept along the
paddles' faces and slid out past their ends, within a second at 240 frames a second (it held at 120),
so now it goes up and down with the paddles instead.  Let either paddle go and it comes free.  All of
it counts as the one hit that caught it (no rally of thousands, no replay full of hits), and its
sound and sparks come Ball.RATTLE_FX apart, not hundreds of times a second.  A paddle driving the ball
into a stone still squirts it out (1.6: see test_powerup_fixes).  Under each of 1.8's physics, and
with the Speed Cap (Rowan had the physics rolled back to 1.7's, then asked for 1.8's again).
"""
import unittest
from unittest import mock

from tests import harness

app = harness.app()

import objects.ball as ball_module                              # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from objects.ball import Ball                                   # noqa: E402

m = app.settings.match


class Sandwich(unittest.TestCase):
    def setUp(self):
        m.reset()
        m.middle_wall = False                                   # (the paddles can meet mid-court)
        m.powerups = False
        app.keys_down.clear()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        g = self.game
        self.p1, self.p2, self.ball = g.p1, g.p2, g.ball
        self.p1.ai_enabled = self.p2.ai_enabled = False
        self.hits, real = [], g.on_hit
        g.on_hit = lambda b, p, d: (self.hits.append(p), real(b, p, d))[1]
        self.sounds, play = [], app.sound_manager.play
        app.sound_manager.play = lambda n, *a, **k: (self.sounds.append(n), play(n, *a, **k))[1]
        self.addCleanup(setattr, app.sound_manager, "play", play)

    def tearDown(self):
        app.keys_down.clear()
        self.game.stop()
        m.reset()

    def squeeze(self, y = 540.0):
        p1, p2, ball = self.p1, self.p2, self.ball
        gap = ball.width + 4
        p1.x0, p1.x1 = 900 - p1.width, 900
        p2.x0, p2.x1 = 900 + gap, 900 + gap + p2.width
        for p in (p1, p2):
            p.y0, p.y1 = y - p.height / 2, y + p.height / 2
            p.vx = p.vy = 0.0
        r = ball.width / 2
        ball.x0, ball.x1, ball.y0, ball.y1 = 902, 902 + ball.width, y + 20 - r, y + 20 + r   # (a little off-centre)
        ball.vx, ball.vy = 600.0, 30.0
        app.keys_down.update({p1.right, p2.left})               # each drives at the other

    def between(self):
        cx = (self.ball.x0 + self.ball.x1) / 2
        return self.p1.x1 - 5 <= cx <= self.p2.x0 + 5 and self.p1.x1 <= self.p2.x0 + 2

    def run_for(self, seconds, fps):
        held = 0
        for _ in range(int(seconds * fps)):
            self.game.update(1 / fps)
            held += self.between()
        return held / int(seconds * fps)

    def test_it_rattles_between_them_for_as_long_as_they_press_at_any_frame_rate(self):
        for fps in (60, 144, 240, 360):
            with self.subTest(fps = fps):
                self.squeeze()
                self.assertEqual(self.run_for(6.0, fps), 1.0, "it got out")
                self.assertEqual((self.p1.score, self.p2.score), (0, 0))

    def test_under_each_physics_and_with_the_speed_cap(self):
        for physics in (0, 1, 2):
            for cap in (False, True):
                with self.subTest(physics = m.PHYSICS[physics], cap = cap):
                    self.game.settings.physics, self.game.settings.speed_cap = physics, cap
                    self.squeeze()
                    self.assertEqual(self.run_for(3.0, 240), 1.0, "it got out")

    def test_it_goes_up_and_down_with_them(self):
        self.squeeze()
        self.run_for(0.5, 120)
        app.keys_down.update({self.p1.up, self.p2.up})
        before = self.ball.y0
        self.assertEqual(self.run_for(0.4, 120), 1.0)
        self.assertLess(self.ball.y0, before - 100)

    def test_let_go_and_it_comes_free(self):
        self.squeeze()
        self.run_for(1.0, 120)
        app.keys_down.discard(self.p2.left)
        app.keys_down.add(self.p2.right)                        # Blue backs off
        self.run_for(1.0, 120)
        self.assertFalse(self.between())

    def test_it_counts_as_one_hit(self):
        self.squeeze()
        rally = self.ball.rally_value
        self.run_for(3.0, 120)
        self.assertLessEqual(self.ball.rally_value - rally, 2)
        self.assertLessEqual(len(self.hits), 2, "the replay and highlights saw one hit, not hundreds")

    def test_its_sound_comes_a_little_apart(self):
        clock = [0.0]
        fake = mock.Mock(perf_counter = lambda: clock[0])
        with mock.patch.object(ball_module, "time", fake):
            self.squeeze()
            for _ in range(2 * 120):
                clock[0] += 1 / 120
                self.game.update(1 / 120)
        hits = self.sounds.count(self.p1.sound) + self.sounds.count(self.p2.sound)
        self.assertLessEqual(hits, 2 / Ball.RATTLE_FX + 2)
        self.assertGreater(hits, 2 / Ball.RATTLE_FX * 0.6, "a rattle you can hear")


if __name__ == "__main__":
    unittest.main()
