"""Switch and Soul Swap reworked, 1.7 (Rowan's 1.7 plan, 2026-11-17).

A Switch always works one way: the players take over each other's paddle, and the goal it
defends.  Each keeps their own keys and their own score; the paddles stay where they are.  Switch
mode does it after every point, or mid-rally; Soul Swap does it mid-rally until the point ends.
The old place-swapping (and the ball slowing to half speed at each swap) is gone, so nothing needs
the Middle Wall down any more.

Rowan's playtest of 1.7 (same day):
- A mid-rally switch went off two seconds after its warning, so a player could leave a ball they
  could have saved, for it to go in just after the switch, into what was then the other player's
  goal.  Now a mid-rally switch is armed (both paddles glow) and goes off at the next hit, so a
  ball let through is always the letter-through's point lost.
- Mid-rally (Soul Swap, Switch: Mid-rally) each player keeps their colour too.  A switch after a
  point still hands over the paddle as it is, colour and all.
- Switch's "Both" is gone: Every point, or Mid-rally.
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


def place(o, cx, cy):
    o.x0, o.x1 = cx - o.width / 2, cx + o.width / 2
    o.y0, o.y1 = cy - o.height / 2, cy + o.height / 2


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

    def arm(self):
        """Wait (the ball held mid-court) until a mid-rally switch is armed, and past its grace."""
        g = self.game
        place(g.ball, 960, 540)
        for _ in range(int(20 / DT)):
            g.ball.vx = g.ball.vy = 0.0
            g.update(DT)
            if g.switch_warning is not None and g.switch_warning >= g.SWITCH_GRACE:
                return True
        return False

    def hit(self, paddle):
        """A ball meets this paddle's face."""
        g, ball = self.game, self.game.ball
        side = 1 if paddle.is_left else -1
        place(ball, (paddle.x1 + ball.width / 2 + 30) if paddle.is_left else (paddle.x0 - ball.width / 2 - 30),
              centre(paddle)[1])
        ball.vx, ball.vy = -side * 1500.0, 0.0
        before = g.recorder.points[-1]["hits"] if getattr(g.recorder, "points", None) else None
        for _ in range(12):
            g.update(DT)
            if ball.vx * side > 0:
                return
        self.fail("the ball never met the paddle")


class EveryPoint(SwitchMatch):
    TIMING = 0

    def test_you_take_over_the_other_paddle_and_keep_your_score(self):
        self.score_for(self.p1)                      # you (Red) go 1-0 up
        self.assertIs(self.yours(), self.p2, "your keys now play the right paddle")
        self.assertEqual(self.p2.score, 1, "and your score went with you")
        self.assertEqual(self.p1.score, 0)
        self.assertTrue(self.p1.ai_enabled, "the AI took over the left paddle")
        self.assertFalse(self.p2.ai_enabled)

    def test_the_paddle_comes_colour_and_all(self):
        self.score_for(self.p1)
        self.assertEqual((self.p1.colour, self.p2.colour), ("red", "blue"), "as in 1.6")

    def test_no_mid_rally_switches(self):
        self.assertFalse(self.arm())


class MidRally(SwitchMatch):
    TIMING = 1

    def test_armed_then_the_next_hit_switches(self):
        g = self.game
        self.assertTrue(g.wall_up, "the Middle Wall stays up")
        self.p1.score = 2
        self.assertTrue(self.arm(), "never armed")
        self.assertEqual(g.switches, 0, "not on a timer: it waits for a hit")
        where = {id(p): centre(p) for p in (self.p1, self.p2)}
        self.hit(self.p1)
        self.assertEqual(g.switches, 1)
        self.assertIsNone(g.switch_warning)
        self.assertIs(self.yours(), self.p2, "the hitter takes over the far paddle")
        self.assertEqual(self.p2.score, 2, "your score is still yours")
        for p in (self.p1, self.p2):
            self.assertLess(abs(centre(p)[0] - where[id(p)][0]), 60, "the paddles stay where they are")

    def test_your_colour_stays_yours(self):
        self.assertTrue(self.arm())
        self.hit(self.p1)
        self.assertEqual(self.yours().colour, "red", "you stay Red, on the right paddle")
        self.assertEqual((self.p1.colour, self.p2.colour), ("blue", "red"))
        self.assertEqual(self.p2.color1, "Red")

    def test_a_hit_in_the_first_moment_doesnt_count(self):
        g = self.game
        g.next_switch = 0.0
        g.update(DT)
        self.assertIsNotNone(g.switch_warning, "armed")
        self.hit(self.p1)
        self.assertEqual(g.switches, 0, "too soon after it lit up")

    def test_letting_a_ball_through_is_your_point_lost(self):
        """The exploit: armed, you leave a ball that's coming at your goal.  No hit, no switch:
        it's your goal, and your point lost."""
        g, ball = self.game, self.game.ball
        self.assertTrue(self.arm())
        place(self.p1, centre(self.p1)[0], 150)                 # you step out of its way
        place(ball, 400, 800)
        ball.vx, ball.vy = -1500.0, 0.0
        for _ in range(int(1 / DT)):
            g.update(DT)
            if g.message_text:
                break
        self.assertEqual(g.switches, 0)
        self.assertEqual((self.p1.score, self.p2.score), (0, 1), "your point lost, as without the switch")

    def test_the_switch_leaves_the_ball_alone(self):
        """No more slowing every ball to half speed: the switch itself doesn't touch it."""
        ball = self.game.ball
        ball.vx, ball.vy = 900.0, 300.0
        before = (ball.x0, ball.y0)
        self.game.switch_sides(mid_rally = True)
        self.assertEqual((ball.vx, ball.vy, ball.x0, ball.y0), (900.0, 300.0) + before)

    def test_the_point_ending_disarms_it(self):
        self.assertTrue(self.arm())
        self.score_for(self.p2)
        self.assertIsNone(self.game.switch_warning)

    def test_no_switch_after_a_point(self):
        self.score_for(self.p1)
        self.assertIs(self.yours(), self.p1)

    def test_no_soul_swap_talisman(self):
        self.assertFalse(self.game.powerups.spawnable(BY_KEY["swap"]))


class NoBoth(unittest.TestCase):
    def test_two_versions(self):
        self.assertEqual(m.SWITCH_TIMINGS, ("Every point", "Mid-rally"))


class SoulSwap(SwitchMatch):
    def test_mid_rally_switches_until_the_point_ends_wall_and_all(self):
        g = self.game
        g.powerups.collect({"kind": "swap", "x": 900, "y": 500}, self.p1)
        self.assertTrue(g.wall_up, "Soul Swap no longer takes the Middle Wall down")
        self.assertTrue(self.arm(), "armed soon")
        self.hit(self.p2)
        self.assertEqual(g.switches, 1)
        self.assertEqual(self.yours().colour, "red", "your colour stays yours")
        self.score_for(self.p2)
        self.assertFalse(g.powerups.switch_plus, "over with the point")
        self.assertFalse(self.arm())

    def test_says_how_it_works_now(self):
        about = BY_KEY["swap"].about
        self.assertIn("take over each other's paddle", about)
        self.assertIn("next hit", about)
        self.assertNotIn("half speed", about)
        self.assertNotIn("Middle Wall", about)


class Shown(SwitchMatch):
    TIMING = 1

    def test_while_armed_each_paddle_says_who_takes_over(self):
        g = self.game
        g.switch_warning = 1.0
        texts = []
        real = app.renderer.text
        app.renderer.text = lambda screen, text, *a, **k: texts.append(text) or real(screen, text, *a, **k)
        try:
            app.renderer.draw_switch_warning(app.virtual, g)
        finally:
            app.renderer.text = real
        self.assertIn("AI takes over", texts)                 # the left paddle: the AI plays the right now
        self.assertIn(f"{self.p1.controls_label} takes over", texts)
        self.assertIn("Switch on the next hit", texts)

    def test_colours_drawn_where_the_players_are(self):
        self.assertTrue(self.arm())
        self.hit(self.p1)
        finishes = []
        real = app.renderer.draw_paddle
        app.renderer.draw_paddle = lambda screen, paddle, rect: finishes.append(paddle.colour) or real(screen, paddle, rect)
        glows = []
        real_glow = app.art.paddle_glow
        app.art.paddle_glow = lambda w, h, finish, *a, **k: glows.append(finish) or real_glow(w, h, finish, *a, **k)
        try:
            app.renderer.draw_world(app.virtual, self.game)
        finally:
            app.renderer.draw_paddle = real
            app.art.paddle_glow = real_glow
        self.assertEqual(finishes, ["blue", "red"], "left paddle Blue, right paddle Red")
        self.assertEqual(glows[:1], ["blue"], "and drawn in Blue")

    def test_replays_and_the_friends_screen_know_the_colours(self):
        self.assertTrue(self.arm())
        self.hit(self.p1)
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        view = ReplayView(self.game.recorder.clip(), app)
        view.show(len(view.clip.frames) - 1)
        self.assertEqual((view.p1.colour, view.p2.colour), ("blue", "red"))
        self.assertTrue(view.settings.switching)

    def test_who_scored_says_their_colour(self):
        self.assertTrue(self.arm())
        self.hit(self.p1)
        g = self.game
        g.on_score(g.ball, {"normal": (1, 0)})                   # into the left goal: the right paddle (you, Red) scores
        self.assertTrue(g.message_text.startswith("Red scored"), g.message_text)
        self.assertEqual(g.message_color, g.MESSAGE_COLOURS["red"])


class TwinBallAfterASwitch(SwitchMatch):
    TIMING = 1

    def test_the_red_ball_still_scores_only_in_blues_goal(self):
        self.assertTrue(self.arm())
        self.hit(self.p1)                                        # Blue now on the left
        red = SimpleNamespace(side = "red", game = self.game)
        from objects.ball import Ball
        self.assertTrue(Ball.scores_in(red, 1), "Blue's goal is the left one now")
        self.assertFalse(Ball.scores_in(red, -1))


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
