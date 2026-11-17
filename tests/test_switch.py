"""Switch and Soul Swap reworked, 1.7 (Rowan's 1.7 plan, 2026-11-17).

A Switch now always works one way: the players take over each other's paddle, and the goal it
defends.  Each keeps their own keys and their own score; the paddles stay where they are.  Switch
mode does it after every point, mid-rally at random moments (after the 2-second warning), or both;
Soul Swap does it mid-rally until the point ends.  The old place-swapping (and the ball slowing to
half speed at each swap) is gone, so nothing needs the Middle Wall down any more.
"""
import math
import unittest
from array import array
from types import SimpleNamespace

from tests import harness

app = harness.app()

from core.states.guest_state import GuestMatchState             # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY                                # noqa: E402
from game.replay import ReplayView                              # noqa: E402

m = app.settings.match
DT = 1 / 120


def centre(o):
    return (o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2


class SwitchMatch(unittest.TestCase):
    TIMING = None

    def setUp(self):
        m.reset()
        if self.TIMING is not None:
            m.mode_switch, m.switch_timing = True, self.TIMING
        app.keys_down.clear()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.p1, self.p2, self.ball = self.game.p1, self.game.p2, self.game.ball
        self.p1.ai_enabled, self.p2.ai_enabled = False, True       # you on Red, the AI on Blue
        self.game.powerups.wait = 999.0
        self.your_keys = self.p1.up

    def tearDown(self):
        self.game.stop()
        m.reset()

    def yours(self):
        """The paddle your keys move now."""
        return self.p1 if self.p1.up == self.your_keys else self.p2

    def score_for(self, paddle):
        g = self.game
        g.on_score(g.ball, {"normal": (-1, 0) if paddle.is_left else (1, 0)})
        g.message_timer = 0.001
        g.update(0.01)

    def run_until_switch(self, seconds = 20):
        g = self.game
        g.ball.x0, g.ball.x1 = 940, 940 + g.ball.width        # (a ball that stays in play)
        before = g.switches
        for _ in range(int(seconds / DT)):
            g.ball.vx = g.ball.vy = 0.0
            g.update(DT)
            if g.switches > before:
                return True
        return False


class EveryPoint(SwitchMatch):
    TIMING = 0

    def test_you_take_over_the_other_paddle_and_keep_your_score(self):
        self.score_for(self.p1)                      # you (Red) go 1-0 up
        self.assertIs(self.yours(), self.p2, "your keys now play Blue")
        self.assertEqual(self.p2.score, 1, "and your score went with you")
        self.assertEqual(self.p1.score, 0)
        self.assertTrue(self.p1.ai_enabled, "the AI took over Red")
        self.assertFalse(self.p2.ai_enabled)

    def test_no_mid_rally_switches(self):
        self.assertFalse(self.run_until_switch(seconds = 25))


class MidRally(SwitchMatch):
    TIMING = 1

    def test_after_a_warning_the_paddles_change_hands_where_they_are(self):
        g = self.game
        self.assertTrue(g.wall_up, "the Middle Wall stays up")
        self.p1.score = 2
        g.next_switch = 0.5
        warned, jump = False, None
        g.ball.x0, g.ball.x1 = 940, 940 + g.ball.width        # (a ball that stays in play)
        for _ in range(int(4 / DT)):
            g.ball.vx = g.ball.vy = 0.0
            before = {id(p): centre(p) for p in (self.p1, self.p2)}
            g.update(DT)
            warned = warned or g.switch_warning is not None
            if g.switches:
                # across the frame it happened, neither paddle went anywhere it couldn't go in a frame
                jump = max(math.hypot(centre(p)[0] - before[id(p)][0], centre(p)[1] - before[id(p)][1])
                           for p in (self.p1, self.p2))
                break
        self.assertTrue(warned, "no warning first")
        self.assertEqual(g.switches, 1)
        self.assertIs(self.yours(), self.p2)
        self.assertEqual(self.p2.score, 2, "your score is still yours")
        self.assertLess(jump, max(self.p1.speed, self.p2.speed) * DT * 1.5, "the paddles stay where they are")

    def test_the_warning_lasts_two_seconds(self):
        g = self.game
        g.next_switch = 0.0
        g.update(DT)
        self.assertAlmostEqual(g.switch_warning, g.SWITCH_WARNING, delta = 2 * DT)

    def test_the_ball_keeps_its_speed(self):
        g, ball = self.game, self.game.ball
        ball.x0, ball.x1 = 900, 900 + ball.width
        ball.vx, ball.vy = 300.0, 120.0
        g.switch_warning = DT / 2
        g.update(DT)
        self.assertEqual(g.switches, 1)
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), math.hypot(300, 120), delta = 5)

    def test_no_switch_after_a_point(self):
        self.score_for(self.p1)
        self.assertIs(self.yours(), self.p1)

    def test_no_soul_swap_talisman(self):
        self.assertFalse(self.game.powerups.spawnable(BY_KEY["swap"]))


class Both(SwitchMatch):
    TIMING = 2

    def test_after_a_point_and_mid_rally(self):
        self.score_for(self.p1)
        self.assertIs(self.yours(), self.p2)
        self.assertTrue(self.run_until_switch())
        self.assertIs(self.yours(), self.p1)


class SoulSwap(SwitchMatch):
    def test_mid_rally_switches_until_the_point_ends_wall_and_all(self):
        g = self.game
        g.powerups.collect({"kind": "swap", "x": 900, "y": 500}, self.p1)
        self.assertTrue(g.wall_up, "Soul Swap no longer takes the Middle Wall down")
        self.assertTrue(self.run_until_switch(seconds = 6), "the first comes soon")
        self.score_for(self.p2)
        self.assertFalse(g.powerups.switch_plus, "over with the point")
        self.assertFalse(self.run_until_switch(seconds = 25))

    def test_says_how_it_works_now(self):
        about = BY_KEY["swap"].about
        self.assertIn("take over each other's paddle", about)
        self.assertNotIn("half speed", about)
        self.assertNotIn("Middle Wall", about)


class Shown(SwitchMatch):
    TIMING = 1

    def test_the_warning_says_who_takes_over(self):
        g = self.game
        g.switch_warning = 1.0
        texts = []
        real = app.renderer.text
        app.renderer.text = lambda screen, text, *a, **k: texts.append(text) or real(screen, text, *a, **k)
        try:
            app.renderer.draw_switch_warning(app.virtual, g)
        finally:
            app.renderer.text = real
        self.assertIn("AI takes over", texts)                 # Red's paddle: the AI plays Blue now
        self.assertIn(f"{self.p1.controls_label} takes over", texts)

    def test_replays_say_whose_paddle_is_whose(self):
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        view = ReplayView(self.game.recorder.clip(), app)
        self.assertTrue(view.settings.switching)


class FriendsPaddle(unittest.TestCase):
    """Online: when a Switch hands the friend the other paddle mid-rally, their screen starts
    moving that one at once, from where the host has it (it went on moving the old one's copy)."""

    def test_prediction_moves_to_the_new_paddle(self):
        m.reset()
        game = Hu_Taong(app)
        game.start()
        game.recorder.capture(1 / 60)
        row = game.recorder.frames[-1]
        game.stop()
        a = array("f")
        a.frombytes(row)
        guest = GuestMatchState.__new__(GuestMatchState)
        guest.app = SimpleNamespace(net = SimpleNamespace(seq = 0, last_snap = 0, keys = 0, axis = None))
        guest.pred, guest.history, guest.teleport_hold = None, [], None
        guest.last_seq = guest.last_snap = -1
        guest.clock = 0.0
        info = {"guest": 2, "speed": [1500, 1500], "info": {"pace": 1.0}, "seq": 0}
        a[20] = -1.0                                              # no countdown: in play
        row = a.tobytes()
        guest.predict(1 / 60, row, info)
        guest.predict(1 / 60, row, info)
        self.assertAlmostEqual(guest.pred[0], a[5], delta = 30, msg = "Blue's paddle, while it's yours")
        info["guest"] = 1
        guest.predict(1 / 60, row, info)
        self.assertAlmostEqual(guest.pred[0], a[1], delta = 30, msg = "Red's paddle, straight after the Switch")


if __name__ == "__main__":
    unittest.main()
