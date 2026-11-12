"""Power-up bugs found by the 1.4 power-up reviews, fixed in 1.6 (batch 1 of the power-up plan).

- A ball caught between two paddles (Middle Wall down), or between a paddle and a stone, rattled
  on the spot hundreds of times a second and the point could never end.
- Every point restarted the wait for the next talisman, so quick points never got one.
- Gravity, Ghost Ball, Wind Gust and Sticky Goo carried on into the next serve.
- Under Twin Balls, Red's Safety Teleport watched the red ball, which can't score on Red.
- Sticky Goo with the wall down: a paddle could carry the ball to the other goal and sling it
  point-blank.
- Snowball: holding the key towards your own goal made you impossible to shove in.
- Portal Pair: the ball could loop between the two portals for ever.
- Double or Nothing said "the next point", but it doubles the point being played.
"""
import math
import unittest

from tests import harness

app = harness.app()

from config import BASE_W                      # noqa: E402  (after the harness has set things up)
from game.hu_taong import Hu_Taong             # noqa: E402
from game.powerups import BY_KEY, UNTIL_POINT  # noqa: E402
from objects.obstacle import Obstacle          # noqa: E402

DT = 1 / 120


def place(obj, cx, cy):
    obj.x0, obj.x1 = cx - obj.width / 2, cx + obj.width / 2
    obj.y0, obj.y1 = cy - obj.height / 2, cy + obj.height / 2


def centre(obj):
    return (obj.x0 + obj.x1) / 2, (obj.y0 + obj.y1) / 2


class Match(unittest.TestCase):
    def setUp(self):
        app.keys_down.clear()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.p1, self.p2, self.ball = self.game.p1, self.game.p2, self.game.ball
        self.p1.ai_enabled = self.p2.ai_enabled = False
        self.pu = self.game.powerups
        self.pu.wait = 999.0                      # no talismans turning up mid-test
        self.hits = []
        on_hit = self.game.on_hit

        def hit(ball, paddle, data):
            self.hits.append(paddle)
            return on_hit(ball, paddle, data)
        self.game.on_hit = hit

    def tearDown(self):
        app.keys_down.clear()
        self.game.stop()

    def run_for(self, seconds, until = None):
        for _ in range(int(seconds / DT)):
            self.game.update(DT)
            if until and until():
                return True
        return False

    def scores(self):
        return self.p1.score, self.p2.score


class SqueezedBall(Match):
    def test_ball_between_two_paddles_gets_free(self):
        p1, p2, ball = self.p1, self.p2, self.ball
        self.pu.wall_down = UNTIL_POINT                 # Open Court: the paddles can meet mid-court
        place(p2, 1082, 530)
        place(p1, 1183, 530)                            # face to face, Blue left of Red
        place(ball, 1132, 530)
        ball.vx, ball.vy = 700.0, 40.0
        app.keys_down.update({p2.right, p1.left})       # each drives at the other
        self.run_for(1.5)
        self.assertLess(len(self.hits), 20, f"{len(self.hits)} paddle hits in 1.5 s: the ball was stuck")

    def test_ball_between_a_paddle_and_a_tombstone_gets_free(self):
        p2, ball = self.p2, self.ball
        tomb = Obstacle(self.game, 1115, 429, 64, 124, life = UNTIL_POINT, style = "tomb")
        tomb.armed, tomb.age = True, 1.0
        self.pu.tombs.append(tomb)
        place(p2, 1259, 520)
        place(ball, 1209, 500)
        ball.vx, ball.vy = 700.0, 0.0
        app.keys_down.add(p2.left)                      # Blue keeps driving into it
        self.run_for(1.5)
        self.assertLess(len(self.hits), 20, f"{len(self.hits)} paddle hits in 1.5 s: the ball was pinned")


class BetweenPoints(Match):
    def test_talisman_wait_carries_into_the_next_point(self):
        self.pu.wait = 3.0
        self.pu.on_point()
        self.assertAlmostEqual(self.pu.wait, 3.0)

    def test_court_wide_wilds_end_with_the_point(self):
        pu, p1, p2 = self.pu, self.p1, self.p2
        for key in ("ghost", "wind", "gravity", "sticky"):
            pu.collect({"kind": key, "x": 900, "y": 500}, p1)
        pu.collect({"kind": "giant", "x": 900, "y": 500}, p1)
        pu.collect({"kind": "shrink", "x": 900, "y": 500}, p1)
        pu.on_point()
        self.assertIsNone(pu.ghost)
        self.assertIsNone(pu.wind)
        for paddle in (p1, p2):
            self.assertNotIn("gravity", paddle.effects)
            self.assertNotIn("sticky", paddle.effects)
        # your own Boons and Curses carry on
        self.assertIn("giant", p1.effects)
        self.assertIn("shrink", p2.effects)


class TeleportUnderTwinBalls(Match):
    def setUp(self):
        super().setUp()
        self.pu.split_ball()
        self.red, self.blue = self.ball, self.pu.twin["ball"]
        place(self.p1, self.p1.x0 + self.p1.width / 2, self.p1.height / 2 + 2)   # Red's paddle up top
        self.p1.charges["teleport"] = 1

    def coming_at_reds_goal(self, ball):
        place(ball, 100 + ball.width / 2, 800)
        ball.vx, ball.vy = -900.0, 0.0

    def going_away(self, ball):
        place(ball, 1200, 300)
        ball.vx, ball.vy = 900.0, 0.0

    def test_red_ball_cant_score_on_red_so_no_save(self):
        self.coming_at_reds_goal(self.red)
        self.going_away(self.blue)
        self.pu.check_teleports()
        self.assertEqual(self.p1.charges.get("teleport"), 1, "the save was spent on a harmless ball")

    def test_blue_ball_coming_at_reds_goal_is_saved(self):
        self.coming_at_reds_goal(self.blue)
        self.going_away(self.red)
        self.pu.check_teleports()
        self.assertFalse(self.p1.charges.get("teleport"), "no save for the ball that can score")
        self.assertAlmostEqual(centre(self.p1)[1], centre(self.blue)[1], delta = 2)


class StickyCarry(Match):
    def test_stuck_ball_is_slung_at_the_halfway_line(self):
        p1, ball, pu = self.p1, self.ball, self.pu
        pu.wall_down = UNTIL_POINT
        p1.effects["sticky"] = 10.0
        place(p1, 700, 540)
        place(ball, p1.x1 + ball.width / 2 + 2, 540)
        ball.vx, ball.vy = 700.0, 0.0
        pu.stick(ball, p1)
        ball.stuck["left"] = ball.stuck["total"] = 1.0
        app.keys_down.add(p1.right)                      # carry it towards Blue's goal
        furthest = 0.0
        for _ in range(int(1.0 / DT)):
            self.game.update(DT)
            if ball.stuck:
                furthest = max(furthest, centre(ball)[0])
        self.assertLessEqual(furthest, BASE_W / 2 + 40, f"carried to x {furthest:.0f} while stuck")

    def test_with_the_wall_up_it_holds_as_before(self):
        p1, ball, pu, game = self.p1, self.ball, self.pu, self.game
        game.settings.middle_wall, was = True, game.settings.middle_wall
        try:
            p1.effects["sticky"] = 10.0
            place(p1, BASE_W / 2 - 60, 540)                  # right up by the wall
            place(ball, p1.x1 + ball.width / 2 + 2, 540)
            ball.vx, ball.vy = 700.0, 0.0
            pu.stick(ball, p1)
            ball.stuck["left"] = ball.stuck["total"] = 1.0
            self.run_for(0.5)
            self.assertIsNotNone(ball.stuck, "slung early with the wall up")
        finally:
            game.settings.middle_wall = was


class SnowballShove(Match):
    def shoved_at(self, key):
        p1, ball, pu, game = self.p1, self.ball, self.pu, self.game
        pu.snow = {"size": 2.0}
        place(p1, game.left_wall.x1 + 60 + p1.width / 2, 540)
        place(ball, p1.x1 + 120 + ball.width / 2, 540)
        ball.vx, ball.vy = -1400.0, 0.0
        pu.ball_v = (ball.vx, ball.vy)
        if key:
            app.keys_down.add(key)
        before = self.scores()
        self.run_for(1.0, until = lambda: self.scores() != before)
        return self.scores()[1] - before[1]

    def test_holding_towards_your_goal_still_shoved_in(self):
        self.assertEqual(self.shoved_at(self.p1.left), 1, "holding back made the paddle immune")

    def test_pushing_forward_shoved_in(self):
        self.assertEqual(self.shoved_at(self.p1.right), 1)

    def test_walking_into_your_own_goal_unshoved_is_no_point(self):
        p1, game = self.p1, self.game
        self.pu.snow = {"size": 2.0}
        place(p1, game.left_wall.x1 + 60 + p1.width / 2, 540)
        place(self.ball, 1400, 300)
        self.ball.vx, self.ball.vy = 400.0, 0.0
        app.keys_down.add(p1.left)
        before = self.scores()
        self.run_for(0.5)
        self.assertEqual(self.scores(), before)


class PortalLoop(Match):
    def test_a_loop_closes_the_portals(self):
        pu, ball = self.pu, self.ball
        # the exit faces straight back at the other portal: in one, out the other, round and round
        pu.portals = [{"x": 700.0, "y": 540.0, "angle": 0.0}, {"x": 1220.0, "y": 540.0, "angle": math.pi}]
        place(ball, 700, 540)
        ball.vx, ball.vy = -800.0, 0.0
        trips = []
        self.game.on_portal = lambda door, out: trips.append(door)
        self.run_for(4.0)
        self.assertEqual(pu.portals, [], "the portals stayed open")
        self.assertLessEqual(len(trips), 3)

    def test_a_paddle_touch_resets_the_count(self):
        pu = self.pu
        pu.portals = [{"x": 700.0, "y": 540.0, "angle": 0.0}, {"x": 1220.0, "y": 540.0, "angle": math.pi}]
        pu.portal_trips = 2
        pu.on_hit(self.ball, self.p1, (1, 0))
        self.assertEqual(pu.portal_trips, 0)


class DoubleOrNothingWords(unittest.TestCase):
    def test_says_this_point(self):
        kind = BY_KEY["double"]
        for text in (kind.blurb, kind.about):
            self.assertIn("This point is worth 2", text)
            self.assertNotIn("next point", text)


if __name__ == "__main__":
    unittest.main()
