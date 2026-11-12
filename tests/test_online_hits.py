"""Ball-paddle hits online feeling wacky (1.5 fixes, second round).

From the November 2026 playtest of 1.5: "sometimes the ball bounced off the wrong side of the paddle
as if it phased through, but a collision was detected and the bounce sound did happen".  Each test
below checks one cause stays fixed.
  - On the host's screen, a save whose word came late showed the ball going into the friend's
    paddle and back out through it.
  - The friend's screen worked out its own returns with simpler maths than the host, so the host
    replaced about 4 in 10 of them and the ball slipped a moment after the hit.
  - The friend's screen only looked at where the ball was each frame, so a quick ball (at a low
    frame rate) or any ball after a hitch could pass straight through their paddle.
  - A goal into the friend's end was given before word of their save could arrive on a shaky link.
  - A save the host turned down left its ball moved back in time; one pinched against a wall by
    the paddle's end was always turned down.
  - After a stall the friend's ball ran ahead of the host's, and saves were turned down as early.
These fixes need both players on the fixed 1.5; with a 1.5 from before them (on a PC or a phone),
the game plays as it did, which the tests marked "earlier 1.5" check.
Nothing goes over the internet: the host's checks are called directly, with a stand-in for the link.
"""
import math
import random
import struct
import time
import unittest
from collections import deque
from types import SimpleNamespace
from unittest import mock

from tests import harness

app = harness.app()

import core.net as netcode                                    # noqa: E402
from config import BASE_H, BASE_W                             # noqa: E402
from core.net import GuestSession, HostSession, pack_json     # noqa: E402
from core.states.guest_state import GuestMatchState           # noqa: E402
from game.hu_taong import Hu_Taong                            # noqa: E402
from game.physics import Physics as netcode_physics           # noqa: E402  (the host's physics)
from game.powerups import PowerUps                            # noqa: E402


class FakeLink:
    """The host's side of the line, as the match sees it."""
    role = "host"
    friend_left = notice = None
    guest_menu = 0
    guest_keys = 0

    def __init__(self):
        self.ping, self.claims, self.acks, self.game, self.over = None, [], {}, None, None
        self.guest_clear_tau = None

    def update(self, dt):
        pass

    def request(self, name):
        return False

    def request_seen(self, name):
        return False

    def connected(self):
        return True

    def keys_for(self, paddle):
        return 0, 0

    def send_due(self):
        pass

    def take_claims(self):
        claims, self.claims = self.claims, []
        return claims


class HostedMatch(unittest.TestCase):
    """A match hosted here, power-ups off, the friend's link faked."""
    def setUp(self):
        self.powerups = app.settings.gameplay.powerups
        app.settings.gameplay.powerups = False
        self.net = app.net = FakeLink()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.net.guest_tells_tau = True                # the friend's game is the fixed 1.5 (see EarlierGuest)
        self.friend = self.game.guest_paddle()
        host = self.game.p1 if self.friend is self.game.p2 else self.game.p2
        host.ai_enabled = False

    def tearDown(self):
        app.net = None
        app.settings.gameplay.powerups = self.powerups

    def frame(self, dt = 0.01):
        """One frame of the host's match, in the order GameState.update runs it."""
        game = self.game
        game.update(dt)
        game.recorder.capture(dt)
        game.note_history()
        game.net_tick()

    def send_ball_at_friend(self, speed = 900.0):
        """The ball flying straight at the middle of the friend's paddle, from mid-court."""
        ball, friend = self.game.ball, self.friend
        r = ball.width / 2
        way = 1 if friend is self.game.p2 else -1
        friend.y0, friend.y1 = 440, 440 + friend.height
        ball.x0, ball.y0 = BASE_W / 2 - r, 540 - r
        ball.x1, ball.y1 = ball.x0 + ball.width, ball.y0 + ball.height
        ball.vx, ball.vy = way * speed, 0.0
        face = (friend.x0 - r - 0.5) if way > 0 else (friend.x1 + r + 0.5)
        return way, face

    def score(self):
        return self.game.p1.score + self.game.p2.score

    def save(self, t, face, speed):
        way = 1 if self.friend is self.game.p2 else -1
        self.net.claims.append({"id": 1, "t": t, "bx": face, "by": 540.0, "px": self.friend.x0,
                                "py": self.friend.y0, "pvx": 0, "pvy": 0, "normal": [way, 0],
                                "vx": -way * speed, "vy": 0.0, "rule": 2})

    def play_a_save(self, lag, speed = 900.0):
        """The friend saves the ball on their screen; word gets here `lag` seconds after.  Answers
        where the host drew the ball each frame, and how far past the paddle's face it went."""
        way, face = self.send_ball_at_friend(speed)
        game, ball, r = self.game, self.game.ball, self.game.ball.width / 2
        hit, sent, drawn = None, False, []
        for _ in range(300):
            self.frame()
            x = (ball.x0 + ball.x1) / 2
            if hit is None and way * (x - face) >= 0:
                hit = game.recorder.clock - way * (x - face) / speed     # when the ball met the paddle
            if hit is not None and not sent and game.recorder.clock >= hit + lag:
                sent = True
                self.save(hit, face, speed)
            shown = game.shown_ball(0.01)
            drawn.append((shown[0] + r) if shown else x)
            if sent and self.net.acks:
                break
        return max(way * (x - face) for x in drawn)


class LateWordOfASave(HostedMatch):
    def test_ball_waits_at_the_friends_paddle_while_word_is_late(self):
        self.game.claim_lag = 0.06                     # word usually takes 60 ms
        deepest = self.play_a_save(lag = 0.18)          # this time it took 180 ms
        self.assertGreaterEqual(self.net.acks[1], 0)
        self.assertLess(deepest, 1.0)                   # 1.5 as first released drew it 75 px into the paddle

    def test_on_time_word_changes_nothing(self):
        self.game.claim_lag = 0.06
        self.assertLess(self.play_a_save(lag = 0.04), 1.0)
        self.assertGreaterEqual(self.net.acks[1], 0)


class GoalHold(HostedMatch):
    def ball_in(self, speed = 1500.0):
        way, face = self.send_ball_at_friend(speed)
        before = self.score()
        hit = None
        for _ in range(300):
            self.frame()
            x = (self.game.ball.x0 + self.game.ball.x1) / 2
            if hit is None and way * (x - face) >= 0:
                hit = self.game.recorder.clock - way * (x - face) / speed
            if self.game.pending_goal is not None:
                return before, hit, face
        self.fail("the ball never reached the friend's goal")

    def test_a_save_after_a_stall_still_stands(self):
        before, hit, face = self.ball_in()
        for _ in range(40):                            # 0.4 s with no word (1.5 gave the goal after 0.2 s or less)
            self.frame()
        self.save(hit, face, 1500.0)
        self.frame()
        self.assertGreaterEqual(self.net.acks[1], 0)
        self.assertEqual(self.score(), before)

    def test_a_miss_is_given_as_soon_as_the_friend_has_seen_it(self):
        before, _, _ = self.ball_in()
        goal_clock = self.game.pending_goal["clock"]
        self.frame()
        self.assertEqual(self.score(), before)          # held...
        self.net.guest_clear_tau = goal_clock + 0.01   # ...until their screen shows the ball past with no save
        self.frame()
        self.assertEqual(self.score(), before + 1)

    def test_a_silent_friend_cannot_hold_a_goal_for_long(self):
        before, _, _ = self.ball_in()
        for _ in range(85):
            self.frame()
        self.assertEqual(self.score(), before + 1)


class HostChecks(HostedMatch):
    def test_a_refused_save_leaves_the_ball_as_it_was(self):
        game, ball, friend = self.game, self.game.ball, self.friend
        way, face = self.send_ball_at_friend()
        for _ in range(20):
            self.frame()
        t, hx, hy = game.history[-1][:3]
        was = (ball.x0, ball.y0, ball.vx, ball.vy, ball.last_paddle)
        # a "save" the ball was already leaving: the host turns it down
        answer = game.apply_claim({"id": 9, "t": t, "bx": hx, "by": hy, "px": friend.x0, "py": friend.y0,
                                   "pvx": 0, "pvy": 0, "normal": [-way, 0], "vx": 0.0, "vy": 0.0})
        self.assertEqual(answer, -1)
        self.assertEqual(was, (ball.x0, ball.y0, ball.vx, ball.vy, ball.last_paddle))

    def test_friends_bounce_matches_the_hosts_exactly(self):
        """The friend's screen works out its returns as the host's physics plays them, so the host
        keeps theirs and the ball doesn't slip after the hit (it replaced about 4 in 10 before)."""
        game, ball, g = self.game, self.game.ball, self.game.p2
        g.remote, self.game.p1.remote = True, False
        serve, r = ball.speed, ball.width / 2
        rng = random.Random(5)
        checked = pinched = 0
        base = game.settings.paddle_speed
        for i in range(600):
            power = ("", "fire", "frost", "swift")[i % 4]
            end = rng.random() < 0.25
            speed = rng.choice([300, 600, 1100, 2000, 3100])
            px, py = 1840.0, rng.uniform(0, BASE_H - g.height)
            pvx = rng.choice([0.0, 0.0, -1500.0, -700.0, -2200.0 if power == "swift" else -1100.0])  # negative: a smash
            pvy = rng.choice([0.0, 1500.0, -1500.0, 700.0])
            if not end:
                by = py + g.height / 2 + rng.uniform(-1.15, 1.15) * (g.height / 2 + r)
                bx, normal = px - r, (1, 0)
                a = math.radians(rng.uniform(-60, 60))
                bvx, bvy = speed * math.cos(a), speed * math.sin(a)
            else:
                top = rng.random() < 0.5
                if rng.random() < 0.3:                  # the end pinches the ball against the wall
                    py = (2 * r + rng.uniform(0, 5.9)) if top else (BASE_H - g.height - 2 * r - rng.uniform(0, 5.9))
                bx, by = px + rng.uniform(0, g.width), (py - r) if top else (py + g.height + r)
                normal = (0, 1) if top else (0, -1)
                a = math.radians(rng.uniform(20, 70))
                bvx, bvy = speed * math.cos(a), speed * math.sin(a) * (1 if top else -1)
            if not r <= by <= BASE_H - r or (pvx - bvx) * normal[0] + (pvy - bvy) * normal[1] >= 0:
                continue                                # off the court, or not a save the friend would claim
            g.x0, g.y0, g.x1, g.y1 = px, py, px + g.width, py + g.height
            g.speed = base * (PowerUps.SWIFT if power == "swift" else PowerUps.FROZEN if power == "frost" else 1.0)
            top = g.speed / PowerUps.SWIFT if power == "swift" else math.inf
            gvx, gvy, gbx, gby = GuestMatchState.bounce_off(g, 2, normal, bx, by, r, bvx, bvy, pvx, pvy, serve = serve,
                                                            fire = power == "fire", top = top)
            t = 10.0 + i
            game.recorder.clock = t
            game.last_guest_hit = game.last_goal_clock = -1.0
            game.message_text, game.pending_goal, game.claim_note = "", None, None
            game.history = deque([(t - 0.01, bx - bvx * 0.01, by - bvy * 0.01, bvx, bvy, px, py),
                                  (t, bx, by, bvx, bvy, px, py)], maxlen = 240)
            ball.stuck, ball.last_paddle, ball.rally_value = None, None, 0
            game.p1.effects, g.effects = {}, {}
            game.powerups.frost = None
            if power in ("fire", "swift"):
                g.effects[power] = 5.0
            if power == "frost":
                game.powerups.frost = {"holder": g, "owner": g, "armed": False, "left": 5.0}
            g.vx = g.vy = 0.0
            claim = {"id": i, "t": t, "bx": round(gbx, 1), "by": round(gby, 1), "px": px, "py": py, "pvx": pvx,
                     "pvy": pvy, "normal": list(normal), "vx": round(gvx, 1), "vy": round(gvy, 1), "rule": 2}
            played = {}
            real = netcode_physics.resolve_collision

            def spy(a, b, data):
                answer = real(a, b, data)
                if a is g and b is ball:
                    played["v"] = (ball.vx, ball.vy)
                return answer
            with mock.patch.object(netcode_physics, "resolve_collision", staticmethod(spy)):
                answer = game.apply_claim(claim)
            where = (i, power, normal, speed, pvx, pvy, getattr(game, "claim_note", None))
            self.assertGreaterEqual(answer, 0, where)    # every save the friend saw stands (pinched ones too)
            hvx, hvy = played["v"]
            host_speed, theirs = math.hypot(hvx, hvy), math.hypot(gvx, gvy)
            turn = math.degrees(abs(math.atan2(hvx * gvy - hvy * gvx, hvx * gvx + hvy * gvy)))
            self.assertAlmostEqual(theirs / host_speed, 1.0, delta = 0.01, msg = where)
            self.assertLess(turn, 2.0, where)            # (a dead-centre hit's touch of spin is random on the host)
            self.assertAlmostEqual(ball.vx, round(gvx, 1), delta = 0.2, msg = where)     # theirs was kept
            checked += 1
            pinched += bool(normal[1] and (py if normal[1] > 0 else BASE_H - py - g.height) < ball.height + 6)
        self.assertGreater(checked, 300)
        self.assertGreater(pinched, 3)


class EarlierGuest(GoalHold):
    """The friend plays a 1.5 from before these fixes (a PC copy not reinstalled, or the phone
    version built before them): it still connects, and plays as before."""
    def setUp(self):
        super().setUp()
        self.net.guest_tells_tau = False

    def test_a_save_after_a_stall_still_stands(self):
        pass                                            # (the longer wait needs the fixed 1.5)

    def test_a_miss_is_given_as_soon_as_the_friend_has_seen_it(self):
        pass

    def test_earlier_guest_keeps_the_short_wait(self):
        before, _, _ = self.ball_in()
        self.assertLessEqual(self.game.pending_goal["until"] - self.game.pending_goal["clock"], 0.45 + 1e-9)
        for _ in range(50):
            self.frame()
        self.assertEqual(self.score(), before + 1)

    def keep_theirs(self, rule):
        """A return the friend's screen sent 20% faster than the host plays it: does the host keep it?"""
        game, ball, g = self.game, self.game.ball, self.friend
        way, face = self.send_ball_at_friend(900.0)
        for _ in range(20):
            self.frame()
        t, hx, hy, hvx, hvy = game.history[-1][:5]
        r = ball.width / 2
        side = 2 if g is game.p2 else 1
        mine = GuestMatchState.bounce_off(g, side, (way, 0), face, hy, r, hvx, hvy, 0.0, 0.0, serve = ball.speed)
        claim = {"id": 5, "t": t, "bx": hx, "by": hy, "px": g.x0, "py": g.y0, "pvx": 0, "pvy": 0,
                 "normal": [way, 0], "vx": mine[0] * 1.2, "vy": mine[1] * 1.2}
        if rule:
            claim["rule"] = rule
        self.assertGreaterEqual(game.apply_claim(claim), 0)
        return abs(abs(ball.vx) - abs(claim["vx"])) < 1

    def test_earlier_guests_bounce_is_judged_as_before(self):
        self.assertTrue(self.keep_theirs(rule = None))      # within a third: kept, as in 1.5 before

    def test_fixed_guests_bounce_must_match(self):
        self.assertFalse(self.keep_theirs(rule = 2))        # the same rule both sides: 20% off isn't kept


def straight_shot(side, speed, fps, rng, hitch = 0.0):
    """The friend's own screen: a ball flying straight at their still paddle, frame by frame, through
    the real GuestMatchState.watch_for_save.  Answers the face the save was claimed on, or None."""
    w, h, r = 40.0, 200.0, 30.0
    x0 = 50.0 if side == 1 else BASE_W - 90.0
    paddle = SimpleNamespace(x0 = x0, x1 = x0 + w, y0 = 440.0, y1 = 640.0, width = w, height = h, flash = 0)
    vx = -speed if side == 1 else speed
    cy = 540 + rng.uniform(-80, 80)
    ball = SimpleNamespace(width = 2 * r, height = 2 * r, vx = vx, vy = 0.0, stuck = None)

    def put(x):
        ball.x0, ball.y0, ball.x1, ball.y1 = x - r, cy - r, x + r, cy + r
    x = BASE_W / 2 + rng.uniform(0, 200) * (-1 if side == 1 else 1)
    put(x)
    claims = []
    me = SimpleNamespace(
        net = SimpleNamespace(claim_id = 0, claims = claims, send_input = lambda: None, last_send = 0.0),
        view = SimpleNamespace(ball = ball, p1 = paddle, p2 = paddle, countdown = None, message_text = "",
                               powerups = SimpleNamespace(effect_list = lambda p: [], fx = [], frosted = lambda p: False)),
        app = SimpleNamespace(sound_manager = SimpleNamespace(paddle_hit_sound = False),
                              fx = SimpleNamespace(spark = lambda *a, **k: None)),
        last_ball = None, bounce = None, claim_rest = 0.0, pred = [x0, 440.0, 0.0, 0.0], tau = 0.0,
        quiet_hit_until = 0.0, bounce_off = GuestMatchState.bounce_off, meet = GuestMatchState.meet,
        simple_bounce = GuestMatchState.simple_bounce)
    face = paddle.x1 if side == 1 else paddle.x0
    hitch_at = abs(face - x) - rng.uniform(0, 400) if hitch else None
    travelled = 0.0
    info = {"serve": 500.0}
    for _ in range(2000):
        GuestMatchState.watch_for_save(me, side, info)
        if claims:
            return tuple(claims[-1]["normal"])
        dt = (1 / fps) * (1 + rng.uniform(-0.25, 0.25))
        if hitch_at is not None and travelled >= hitch_at:
            dt, hitch_at = hitch, None
        travelled += abs(vx * dt)
        x = max(r, min(BASE_W - r, x + vx * dt))       # the drawn ball stops at the goal line
        put(x)
        me.tau += dt
        if x in (r, BASE_W - r):
            GuestMatchState.watch_for_save(me, side, info)
            return tuple(claims[-1]["normal"]) if claims else None
    return None


class FriendsOwnSaves(unittest.TestCase):
    def check(self, speed, fps, hitch = 0.0):
        rng = random.Random(1)
        for side, front in ((1, (-1, 0)), (2, (1, 0))):
            faces = [straight_shot(side, speed, fps, rng, hitch) for _ in range(150)]
            self.assertEqual(faces.count(front), len(faces), (side, speed, fps, hitch))

    def test_quickest_ball_at_30_fps(self):
        self.check(2250, 30)                            # a third went straight through before

    def test_after_a_hitch(self):
        self.check(1000, 60, hitch = 0.1)
        self.check(1000, 60, hitch = 0.3)               # most went through before

    def test_meet_finds_the_face_crossed_first(self):
        # in one frame the ball's centre goes from in front of the paddle to past its middle: that's
        # its front face, not its back
        self.assertEqual(GuestMatchState.meet(30, 40, 200, (-90, 100), (30, 100)), (0.5, (1, 0)))
        self.assertEqual(GuestMatchState.meet(30, 40, 200, (130, 100), (10, 100)), (0.5, (-1, 0)))
        self.assertIsNone(GuestMatchState.meet(30, 40, 200, (-50, -100), (25, -100)))     # passes above it
        self.assertEqual(GuestMatchState.meet(30, 40, 200, (20, -90), (20, 30)), (0.5, (0, 1)))   # onto its top end


class EarlierHost(unittest.TestCase):
    def test_bounce_for_a_host_that_sends_no_serve_speed(self):
        """A host on a 1.5 from before the fixes sends no serve speed: the friend's screen bounces
        the ball as that host expects (keeping its speed), and says so in its claim."""
        rng = random.Random(2)
        saved = GuestMatchState.watch_for_save
        claims = []

        def shot(info):
            claims.clear()
            paddle = SimpleNamespace(x0 = BASE_W - 90.0, x1 = BASE_W - 50.0, y0 = 440.0, y1 = 640.0, width = 40.0,
                                     height = 200.0, flash = 0)
            ball = SimpleNamespace(width = 60.0, height = 60.0, vx = 900.0, vy = 0.0, stuck = None,
                                   x0 = paddle.x0 - 50, y0 = 510.0, x1 = paddle.x0 + 10, y1 = 570.0)
            me = SimpleNamespace(
                net = SimpleNamespace(claim_id = 0, claims = claims, send_input = lambda: None, last_send = 0.0),
                view = SimpleNamespace(ball = ball, p1 = paddle, p2 = paddle, countdown = None, message_text = "",
                                       powerups = SimpleNamespace(effect_list = lambda p: [], fx = [],
                                                                  frosted = lambda p: False)),
                app = SimpleNamespace(sound_manager = SimpleNamespace(paddle_hit_sound = False),
                                      fx = SimpleNamespace(spark = lambda *a, **k: None)),
                last_ball = (paddle.x0 - 70, 540.0, 0.0, paddle.x0, paddle.y0), bounce = None, claim_rest = 0.0,
                pred = [paddle.x0, paddle.y0, 0.0, 0.0], tau = 1 / 30, quiet_hit_until = 0.0,
                bounce_off = GuestMatchState.bounce_off, meet = GuestMatchState.meet,
                simple_bounce = GuestMatchState.simple_bounce)
            saved(me, 2, info)
            return claims[-1]
        old = shot({})
        self.assertEqual(old["rule"], 1)
        self.assertAlmostEqual(math.hypot(old["vx"], old["vy"]), 900.0, delta = 1)
        new = shot({"serve": 500.0})
        self.assertEqual(new["rule"], 2)
        self.assertLess(math.hypot(new["vx"], new["vy"]), 800.0)    # a blocked ball loses pace, as the host plays it


class Lead(unittest.TestCase):
    def test_friends_ball_isnt_sent_ahead_by_a_stall(self):
        guest = GuestSession(app, address = ("127.0.0.1", 9))
        self.addCleanup(guest.close)
        now = time.perf_counter()
        guest.trips.extend([(now - 0.9 + i * 0.01, 0.06) for i in range(60)] + [(now, 0.5)])
        self.assertEqual(guest.quick_trip(), 0.06)

    def test_hosts_ping_is_smoothed(self):
        net = HostSession(app, port = 0, upnp = False)
        self.addCleanup(net.close)
        clock = SimpleNamespace(now = 100.0, perf_counter = lambda: clock.now)
        with mock.patch.object(netcode, "time", clock):
            for seq, trip in enumerate([0.06] * 5 + [0.5], 1):
                net.read_input(struct.pack("<IBd", seq, 0, 1.0) + pack_json({"hecho": 100.0 - trip}))
        self.assertAlmostEqual(net.ping, 0.06 + 0.1 * (0.5 - 0.06), places = 6)


if __name__ == "__main__":
    unittest.main()
