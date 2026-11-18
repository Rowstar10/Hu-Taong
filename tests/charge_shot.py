"""The charge-and-redirect shot (Rowan's 1.8 plan): tap the ball softly, run after it, and hit it
again at full speed by the Middle Wall, off any part of the paddle.  Played in a real match, it
says how long the ball takes to reach the other paddle's line and where, and whether a player
there could have got to it.  Used by tests/test_speed_cap.py.

The defender: in the middle of their goal, reacting REACTION seconds late (a quick person), then
moving at their paddle's top speed, easing up to it as the game's controls do.
"""
import math

from config import BASE_H, BASE_W
from game.hu_taong import Hu_Taong
from game.physics import Physics

REACTION = 0.2
DT = 1 / 120
CONTACTS = (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0)   # where on the face it meets the ball
SLOW_BALLS = ((500.0, 0.0), (360.0, 360.0), (360.0, -360.0))       # the soft tap the attacker chases
RUNS = (0, -1, 1)                                                  # the attacker running straight, or up or down too


def reach(paddle, t):
    """How far the defender gets in `t` seconds from standing, easing up to top speed."""
    if t <= 0:
        return 0.0
    k = paddle.soft_control_k
    return paddle.speed * (t - (1 - math.exp(-k * t)) / k)


def play(app, contact, slow, run):
    """One charge shot; answers (seconds to the defender's line, how far short the defender falls:
    above 0 means they couldn't get there, and the ball's speed off the hit)."""
    game = Hu_Taong(app)
    game.start()
    try:
        game.countdown, game.paused = None, False
        game.powerups.wait = 999.0
        p1, p2, ball = game.p1, game.p2, game.ball
        game.objects.remove(p2)                  # (the defender is worked out, not played)
        r = ball.width / 2
        bx, by = BASE_W / 2 - 60, BASE_H / 2
        ball.x0, ball.y0, ball.x1, ball.y1 = bx - r, by - r, bx + r, by + r
        ball.vx, ball.vy = slow
        cy = by - contact * p1.height / 2       # so the ball meets the face at `contact`
        p1.x1 = ball.x0 - 4
        p1.x0 = p1.x1 - p1.width
        p1.y0, p1.y1 = cy - p1.height / 2, cy + p1.height / 2
        p1.vx, p1.vy = p1.speed, run * p1.speed
        keys = {p1.right} | ({p1.down} if run > 0 else {p1.up} if run < 0 else set())
        app.keys_down = keys
        line = p2.x0                             # the defender's face
        t, fastest = 0.0, 0.0
        while ball.x1 < line and t < 5.0:
            Physics.step(game, DT)
            t += DT
            if ball.last_paddle is p1 or ball.rally_value:
                fastest = max(fastest, math.hypot(ball.vx, ball.vy))
        app.keys_down = set()
        arrive = (ball.y0 + ball.y1) / 2
        need = max(0.0, abs(arrive - BASE_H / 2) - (p2.height / 2 + r))
        return t, need - reach(p2, t - REACTION), fastest
    finally:
        app.keys_down = set()
        game.stop()


def worst(app):
    """The hardest charge shot to reach: (how far short the defender falls, seconds, speed, the shot)."""
    result = None
    for contact in CONTACTS:
        for slow in SLOW_BALLS:
            for run in RUNS:
                t, short, speed = play(app, contact, slow, run)
                if result is None or short > result[0]:
                    result = (short, t, speed, (contact, slow, run))
    return result
