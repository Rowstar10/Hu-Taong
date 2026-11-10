"""Hits off a paddle's top or bottom end (1.4 fix): they sent the ball off far too fast.

In 1.3 a paddle sweeping down onto the ball with its end sent it off at 3 times serve speed, and
a ball pinned between a paddle's end and the floor came out along the wall at nearly 4 times.
"""
import math
import unittest

from tests import harness

app = harness.app()

from config import BASE_H                      # noqa: E402  (after the harness has set things up)
from game.hu_taong import Hu_Taong             # noqa: E402
from game.physics import Physics               # noqa: E402


class PaddleEndHits(unittest.TestCase):
    def setUp(self):
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown = None
        self.p1, self.ball = self.game.p1, self.game.ball
        self.p1.ai_enabled = self.game.p2.ai_enabled = False
        self.serve = self.ball.speed

    def tearDown(self):
        app.keys_down.clear()
        self.game.stop()

    def place(self, paddle_y0, ball_y0, ball_vy = 0.0, key = None):
        """The left paddle at paddle_y0, and the ball at ball_y0 overlapping it sideways, drifting
        slowly towards its own goal.  `key` is held down (the paddle's up or down)."""
        p1, ball = self.p1, self.ball
        bx = p1.x0 + p1.width / 2 - ball.width / 2
        for obj, x0, y0 in ((p1, p1.x0, paddle_y0), (ball, bx, ball_y0)):
            obj.x0, obj.y0, obj.x1, obj.y1 = x0, y0, x0 + obj.width, y0 + obj.height
        ball.vx, ball.vy, ball.last_paddle = -40.0, ball_vy, None
        p1.vx = 0.0
        p1.vy = p1.speed if key == p1.down else -p1.speed if key == p1.up else 0.0
        app.keys_down.clear()
        if key is not None:
            app.keys_down.add(key)

    def play(self, seconds = 1.0, dt = 1 / 120):
        """Step the physics.  Answers the ball's top speed, and whether it got clear of the paddle."""
        top, clear = 0.0, False
        for _ in range(int(seconds / dt)):
            Physics.step(self.game, dt)
            top = max(top, math.hypot(self.ball.vx, self.ball.vy))
            if self.ball.x0 > self.p1.x1 + 40:
                clear = True
                break
        return top, clear

    def assert_calm(self, top, clear):
        self.assertTrue(clear, "the ball never got clear of the paddle")
        self.assertLessEqual(top, 1.1 * self.serve, f"the ball left at {top:.0f} px/s (serve {self.serve})")

    def test_paddle_sweeping_down_onto_the_ball(self):
        p1 = self.p1
        self.place(300, 300 + p1.height + 2, key = p1.down)
        self.assert_calm(*self.play())

    def test_paddle_sweeping_up_onto_the_ball(self):
        p1, ball = self.p1, self.ball
        self.place(400, 400 - ball.height - 2, key = p1.up)
        self.assert_calm(*self.play())

    def test_ball_pinned_against_the_floor(self):
        p1, ball = self.p1, self.ball
        self.place(BASE_H - p1.height - ball.height - 25, BASE_H - ball.height - 20, key = p1.down)
        self.assert_calm(*self.play())

    def test_ball_pinned_against_the_ceiling(self):
        p1, ball = self.p1, self.ball
        self.place(ball.height + 25, 20, key = p1.up)
        self.assert_calm(*self.play())

    def test_ball_bouncing_between_the_paddle_end_and_the_floor(self):
        # room for the ball to bounce off the floor and back into the paddle's end a few times
        p1, ball = self.p1, self.ball
        self.place(BASE_H - p1.height - ball.height * 3, BASE_H - ball.height * 3 + 2, key = p1.down)
        self.assert_calm(*self.play())

    def test_the_paddle_moves_freely_again_once_the_ball_is_clear(self):
        p1 = self.p1
        self.place(300, 300 + p1.height + 2, key = p1.down)
        self.play()
        for _ in range(30):
            Physics.step(self.game, 1 / 120)
        self.assertIsNone(p1.held)
        # held back it would trail the ball (about 300 px/s); free, it is near full speed again
        # (a paddle settles a little under its speed, against its drag)
        self.assertGreater(p1.vy, 0.8 * p1.speed)

    def test_a_still_paddle_end_returns_the_ball_at_its_own_speed(self):
        p1 = self.p1
        self.place(300, 300 + p1.height + 2, ball_vy = -self.serve)
        top, clear = self.play()
        self.assertTrue(clear)
        self.assertAlmostEqual(top, math.hypot(40, self.serve), delta = 0.1 * self.serve)

    def test_a_hard_hit_with_the_face_still_speeds_the_ball_up(self):
        # unchanged from 1.3: swinging the paddle's face forward into the ball is a smash
        p1, ball = self.p1, self.ball
        for obj, x0, y0 in ((p1, 60, BASE_H / 2 - p1.height / 2), (ball, 64 + p1.width, BASE_H / 2 - ball.height / 2)):
            obj.x0, obj.y0, obj.x1, obj.y1 = x0, y0, x0 + obj.width, y0 + obj.height
        ball.vx, ball.vy = -self.serve, 0.0
        p1.vx, p1.vy = p1.speed, 0.0
        app.keys_down.clear()
        app.keys_down.add(p1.right)
        top, _ = self.play()
        self.assertGreater(top, 2.5 * math.sqrt(2) * self.serve)


if __name__ == "__main__":
    unittest.main()
