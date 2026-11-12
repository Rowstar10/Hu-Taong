"""Power-ups online, 1.6 (batch 5 of the power-up plan, from the 1.4 reviews).

- Double or Nothing: the friend (and anyone watching a replay) saw the score jump by 2 with no
  "x2" in the scored message.
- Gravity: the friend's own paddle wasn't predicted under Gravity, so every key answered a full
  round trip late.  Their game now runs the same fall-and-jump rules as the host's.
- Safety Teleport: the host judged the friend's save from its late copy of their paddle, so it
  fired on saves they were already making.  Their own screen judges it now, and the save it makes
  tells the host it teleported.
"""
import unittest
from collections import deque
from types import SimpleNamespace

from tests import harness

app = harness.app()

from config import BASE_W                                       # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_online_hits import HostedMatch                  # noqa: E402
from tests.test_powerup_fixes import Match, place               # noqa: E402


class DoubleOnline(Match):
    def message_shown(self, text):
        game = self.game
        game.message_text = text
        for _ in range(3):
            game.recorder.capture(1 / 60)
        clip = game.recorder.clip()
        view = ReplayView(clip, app)
        view.show(clip.length)
        return view.message_text

    def test_x2_reaches_the_friend_and_replays(self):
        self.assertEqual(self.message_shown(f"{self.p1.color1} scored! x2"), "Red scored! x2")

    def test_a_plain_point_still_reads_as_before(self):
        self.assertEqual(self.message_shown(f"{self.p2.color1} scored!"), "Blue scored!")


class GravityPrediction(Match):
    def test_friends_paddle_falls_and_jumps_as_the_hosts_does(self):
        game, p1, ball = self.game, self.p1, self.ball
        p1.effects["gravity"] = 10.0
        place(ball, 1500, 300)
        ball.vx = ball.vy = 0.0
        place(p1, 400, 300)
        p1.vx = p1.vy = 0.0
        game.apply_gameplay_settings()
        dt = 1 / 120
        p, jump = [p1.x0, p1.y0, 0.0, 0.0], None
        # fall to the floor, hold Up into a high jump, run right, tap Up for a hop, run left, jump again
        script = [(0, 0)] * 60 + [(0, -1)] * 30 + [(1, 0)] * 40 + [(0, -1)] * 4 + [(-1, 0)] * 60 + [(0, -1)] * 50
        worst = 0.0
        for dx, dy in script:
            app.keys_down.clear()
            app.keys_down.update(k for k, on in ((p1.right, dx > 0), (p1.left, dx < 0), (p1.up, dy < 0)) if on)
            game.update(dt)
            jump = GuestMatchState.step_paddle(p, dx, dy, p1.speed, p1.width, p1.height, dt * game.settings.pace,
                                               True, jump)
            worst = max(worst, abs(p[0] - p1.x0), abs(p[1] - p1.y0))
        self.assertLess(worst, 3.0)


class TeleportOnHost(HostedMatch):
    def setUp(self):
        super().setUp()
        self.way = 1 if self.friend is self.game.p2 else -1      # towards the friend's goal

    def test_host_leaves_the_friends_teleport_to_their_screen(self):
        g, ball = self.friend, self.game.ball
        g.charges["teleport"] = 1
        place(g, g.x0 + g.width / 2, g.height / 2 + 2)          # up top, nowhere near the ball
        place(ball, (BASE_W - 100 if self.way > 0 else 100) - self.way * ball.width / 2, 800)
        ball.vx, ball.vy = self.way * 900.0, 0.0
        self.game.powerups.check_teleports()
        self.assertEqual(g.charges.get("teleport"), 1)

    def claim(self, teleport, charge, px_shift = 0.0):
        game, ball, g = self.game, self.game.ball, self.friend
        place(g, g.x0 + g.width / 2, g.height / 2 + 2)
        gx, gy = g.x0, g.y0
        r = ball.width / 2
        # low down, further from their paddle up top than it could move in time (g.speed * 0.45 + 90)
        bx, by, bvx = (BASE_W - 150 if self.way > 0 else 150), 980.0, self.way * 900.0
        px = (bx + r if self.way > 0 else bx - r - g.width) - self.way * px_shift
        py = by - g.height / 2
        g.charges.clear()
        if charge:
            g.charges["teleport"] = 1
        t = 20.0
        game.recorder.clock = t
        game.last_guest_hit = game.last_goal_clock = -1.0
        game.message_text, game.pending_goal = "", None
        game.history = deque([(t - 0.01, bx - bvx * 0.01, by, bvx, 0.0, gx, gy), (t, bx, by, bvx, 0.0, gx, gy)],
                             maxlen = 240)
        claim = {"id": 1, "t": t, "bx": bx, "by": by, "px": px, "py": py, "pvx": 0, "pvy": 0,
                 "normal": [1, 0] if self.way > 0 else [-1, 0], "vx": -bvx, "vy": 0.0, "rule": 2}
        if teleport:
            claim["teleport"] = 1
        return game.apply_claim(claim), px, py

    def test_teleport_save_stands_and_spends_the_charge(self):
        answer, px, py = self.claim(teleport = True, charge = True)
        g = self.friend
        self.assertGreaterEqual(answer, 0, getattr(self.game, "claim_note", None))
        self.assertEqual((round(g.x0), round(g.y0)), (round(px), round(py)))
        self.assertNotIn("teleport", g.charges)

    def test_no_save_to_spend_no_teleport(self):
        answer, _, _ = self.claim(teleport = True, charge = False)
        self.assertEqual(answer, -1)

    def test_a_plain_save_out_of_reach_still_refused(self):
        answer, _, _ = self.claim(teleport = False, charge = True)
        self.assertEqual(answer, -1)
        self.assertEqual(self.friend.charges.get("teleport"), 1)

    def test_teleport_only_in_front_of_their_own_goal(self):
        answer, _, _ = self.claim(teleport = True, charge = True, px_shift = 700)
        self.assertEqual(answer, -1)


class TeleportOnFriendsScreen(unittest.TestCase):
    def friend(self, paddle_y0):
        def place_box(o, x0, y0, w, h):
            o.x0, o.y0, o.x1, o.y1 = x0, y0, x0 + w, y0 + h
        paddle = SimpleNamespace(width = 40.0, height = 200.0, is_left = False, vx = 0.0, vy = 0.0)
        paddle.place = lambda x0, y0, w, h: place_box(paddle, x0, y0, w, h)
        paddle.place(BASE_W - 90.0, paddle_y0, 40.0, 200.0)
        ball = SimpleNamespace(x0 = BASE_W - 160.0, x1 = BASE_W - 120.0, y0 = 780.0, y1 = 820.0, width = 40.0,
                               height = 40.0, diameter = 40.0, vx = 900.0, vy = 0.0, stuck = None, side = None)
        view = SimpleNamespace(ball = ball, p1 = paddle, p2 = paddle, countdown = None, message_text = "",
                               powerups = SimpleNamespace(effect_list = lambda p: [("teleport", None, 1)]))
        me = SimpleNamespace(view = view, pred = [paddle.x0, paddle.y0, 0.0, 0.0], tau = 1.0, bounce = None,
                             teleport_hold = None, teleport_claim = False, quiet_teleport_until = -1.0, history = [1],
                             last_ball = (0, 0, 0, 0, 0), clock = 5.0,
                             app = SimpleNamespace(fx = SimpleNamespace(burst = lambda *a, **k: None),
                                                   sound_manager = SimpleNamespace(play = lambda *a: None)))
        GuestMatchState.watch_for_teleport(me, 2)
        return me, paddle, ball

    def test_blinks_in_front_of_a_ball_about_to_slip_past(self):
        me, paddle, ball = self.friend(0.0)
        self.assertTrue(me.teleport_claim)
        self.assertEqual(me.teleport_hold, 6.0)
        self.assertEqual(paddle.x0, ball.x1 + 6)
        self.assertAlmostEqual((paddle.y0 + paddle.y1) / 2, 800.0)
        self.assertEqual(me.pred[:2], [paddle.x0, paddle.y0])

    def test_not_when_already_covering_it(self):
        me, paddle, _ = self.friend(700.0)
        self.assertFalse(me.teleport_claim)
        self.assertEqual(paddle.y0, 700.0)


if __name__ == "__main__":
    unittest.main()
