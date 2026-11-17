"""Make tests/data/v09_hits.json: how Hu Taong 0.9 played a ball off a paddle (1.8, Rowan's v0.9
physics option).

Runs 0.9's own Physics.resolve_collision and Paddle.on_contact over a grid of hits (both paddles,
off the face and both ends, at several contact points, ball speeds and directions, and paddle
movements) and keeps how the ball left.  tests/test_physics_engines.py checks the v0.9 engine
against it.  Only reads the 0.9 source (writes no bytecode there):

    python -B tests/data/make_v09_hits.py "<path to HuTaong_v0.9>"
"""
import sys

sys.dont_write_bytecode = True
import json                                                     # noqa: E402
import math                                                     # noqa: E402
import os                                                       # noqa: E402
from types import SimpleNamespace                               # noqa: E402

V09 = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, V09)

from config import DYNAMIC, KINEMATIC                           # noqa: E402  (0.9's)
from game.physics import Physics                                # noqa: E402
from objects.paddle import Paddle                               # noqa: E402

# The shared layout of every hit (the test rebuilds it the same way)
PADDLE_W, PADDLE_H, BALL = 40, 200, 60
CENTRES = (300.0, 1620.0)                                       # left and right paddles' centres
CY = 540.0
FACE_AT = (-1.2, -0.7, -0.3, 0.0, 0.45)                         # ball centre, in paddle half-heights
END_AT = (-2.0, -0.9, -0.3, 0.0, 0.5, 1.4)                      # ball centre, in paddle half-widths
SPEEDS = (150.0, 700.0, 2400.0)
HEADINGS = [math.radians(10 + 45 * i) for i in range(8)]
PADDLE_V = ((0.0, 0.0), (1500.0, 0.0), (-1500.0, 0.0), (0.0, 1500.0), (0.0, -1500.0), (1100.0, 1100.0))


def layout(side, kind, at):
    """The paddle and ball rectangles, and the normal 0.9's swept test gives the paddle-first pair."""
    cx = CENTRES[side]
    px0, py0 = cx - PADDLE_W / 2, CY - PADDLE_H / 2
    paddle = (px0, py0, px0 + PADDLE_W, py0 + PADDLE_H)
    if kind == "face":
        by = CY + at * PADDLE_H / 2
        bx0 = paddle[2] if side == 0 else paddle[0] - BALL
        return paddle, (bx0, by - BALL / 2, bx0 + BALL, by + BALL / 2), ((-1, 0) if side == 0 else (1, 0))
    bx = cx + at * PADDLE_W / 2
    if kind == "above":
        by0 = paddle[1] - BALL
        return paddle, (bx - BALL / 2, by0, bx + BALL / 2, by0 + BALL), (0, 1)
    by0 = paddle[3]
    return paddle, (bx - BALL / 2, by0, bx + BALL / 2, by0 + BALL), (0, -1)


def body(rect, vx, vy, **kw):
    x0, y0, x1, y1 = rect
    return SimpleNamespace(x0=x0, y0=y0, x1=x1, y1=y1, width=x1 - x0, height=y1 - y0, vx=vx, vy=vy, **kw)


def play(side, kind, at, bvx, bvy, pvx, pvy):
    paddle_rect, ball_rect, normal = layout(side, kind, at)
    paddle = body(paddle_rect, pvx, pvy, body_type=KINEMATIC, inv_mass=0.05, restitution=0.6,
                  is_paddle=True, is_ball=False)
    ball = body(ball_rect, bvx, bvy, body_type=DYNAMIC, inv_mass=1.0, restitution=0.4,
                is_paddle=False, is_ball=True, on_contact=lambda other, data: None)
    paddle.on_contact = lambda other, data: Paddle.on_contact(paddle, other, data)
    rvn = (pvx - bvx) * normal[0] + (pvy - bvy) * normal[1]
    if rvn > 0:
        return None                                             # moving apart: no hit
    Physics.resolve_collision(paddle, ball, {"t": 0.0, "normal": normal})
    return ball.vx, ball.vy


def main():
    hits = []
    for side in (0, 1):
        for kind, places in (("face", FACE_AT), ("above", END_AT), ("below", END_AT)):
            for at in places:
                for speed in SPEEDS:
                    for heading in HEADINGS:
                        bvx, bvy = speed * math.cos(heading), speed * math.sin(heading)
                        for pvx, pvy in PADDLE_V:
                            out = play(side, kind, at, bvx, bvy, pvx, pvy)
                            if out:
                                hits.append([side, kind, at, round(bvx, 3), round(bvy, 3), pvx, pvy,
                                             round(out[0], 3), round(out[1], 3)])
    data = {"about": "How Hu Taong 0.9 played a ball off a paddle: [side (0 left, 1 right), where (face, "
                     "above or below the paddle), contact point, ball vx, vy, paddle vx, vy, ball vx, vy after]",
            "paddle": [PADDLE_W, PADDLE_H], "ball": BALL, "centres": CENTRES, "cy": CY, "hits": hits}
    with open(os.path.join(HERE, "v09_hits.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, separators=(",", ":"))
        f.write("\n")
    print(len(hits), "hits")


if __name__ == "__main__":
    main()
