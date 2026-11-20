"""How a ball comes off a paddle under each physics option (Match settings > Ball & Paddles, 1.8).

Current is 1.7's engine (objects/paddle.py on_contact).  Classic is Pong's: the angle comes from
where the ball meets the paddle, every hit of a rally is a step faster up to the usual top speed,
and the paddle's movement adds nothing.  v0.9 is Hu Taong 0.9's: the knock's own speed (drive into
the ball to speed it up, a still paddle slows it) with no top speed, angled by where it met the
paddle, off an end too.  The Speed Cap limits how hard a paddle can knock the ball.

The host's game (objects/paddle.py) and the friend's screen online (core/states/guest_state.py
bounce_off) both play hits by these numbers, so the two agree.
"""
import math

from config import MAX_BALL_SPEEDUP, MAX_BOUNCE_ANGLE, BALL_PACE

CURRENT, CLASSIC, V09 = 0, 1, 2

CLASSIC_STEP = 0.05     # Classic: each hit of a rally adds this share of the serve's speed, up to
                        # the usual top speed (MAX_BALL_SPEEDUP times the serve's)
V09_FLOOR = 0.25        # v0.9: never slower than this share of the serve's speed.  (0.9 had no
                        # floor: two still paddles could slow a point almost to a standstill)
V09_UPRIGHT = 0.15      # v0.9: off an end, never closer to straight up or down than this (the share
                        # of its speed it keeps going sideways).  0.9 could send it straight up and
                        # down, out of reach for ever
CAP_DRIVE = 1.6         # the Speed Cap: a paddle knocks the ball as if it were moving into it no
                        # faster than this share of the serve's speed (1,131 px/s at ball speed
                        # 500).  Measured with tests/charge_shot.py: the worst charge shot stays
                        # within reach, with about 190 px to spare, up to about 1.95


def serve_speed(serve):
    """A serve's speed: serves go diagonally, at `serve` on each axis."""
    return serve * math.sqrt(2)


def classic_speed(serve, hits):
    """Classic: the speed after the rally's `hits`-th hit."""
    start = serve_speed(serve)
    return min(start * (1 + CLASSIC_STEP * hits), MAX_BALL_SPEEDUP * start)


def v09_floor(serve):
    return V09_FLOOR * serve_speed(serve)


def push_pace(capped):
    """How much a paddle's push into the ball counts (1.9): BALL_PACE, so the ball goes a little slower
    than 1.8's while the paddles keep their speed, but in full under the Speed Cap, where the cap limits
    drives already and a paddle follows its own shot: pushed for less, a ball could never outrun the
    paddle pushing it, which was held behind it (1.8's "moves like a turtle")."""
    return 1.0 if capped else BALL_PACE


def cap_drive(serve):
    """The Speed Cap: the fastest a paddle counts as moving into the ball when it knocks it, for a
    ball served at `serve`.  (Since the ball went at BALL_PACE, 1.9, the limit is the one measured for
    the Ball Speed setting, as in 1.8: a capped knock is as fast as it was, so a paddle pushing its
    own shot along isn't held back any more than it was, and every capped shot is still in reach.)"""
    return CAP_DRIVE * serve_speed(serve / BALL_PACE)


def v09_off_the_end(offset, ny, speed, forward):
    """v0.9, off a paddle's end: angled by where along the end it met (`offset`, -1 to 1), mostly up
    or down (`ny`: the paddle-first normal, so -ny is the way out), but never quite straight; with
    no sideways way to keep, it goes `forward`."""
    angle = max(-1.0, min(1.0, offset)) * MAX_BOUNCE_ANGLE
    vx, vy = speed * math.sin(angle), -ny * speed * math.cos(angle)
    if abs(vx) < V09_UPRIGHT * speed:
        vx = math.copysign(V09_UPRIGHT * speed, vx if vx else forward)
        vy = math.copysign(math.sqrt(1 - V09_UPRIGHT ** 2) * speed, vy or -ny)
    return vx, vy
