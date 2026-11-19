import math
import random
import time

from config import BASE_W, BASE_H, DYNAMIC
from core import match_sounds
from helpers import clamp, lerp
from render import theme
from objects.game_object import GameObject


class Ball(GameObject):
    body_type = DYNAMIC
    is_ball = True
    can_score = True

    def __init__(self, game, diameter, x, y, speed, color="white"):
        super().__init__(
            game,
            diameter,
            diameter,
            x,
            y,
            vx=random.choice([1, -1]) * speed,
            vy=random.choice([1, -1]) * speed,
            restitution=0.4,
        )

        self.diameter = diameter
        self.speed = speed
        self.color = color
        self.rally_value = 0
        self.last_paddle = None
        self.stuck = None        # Sticky Goo: {"paddle", "dy", "side", "left", "total", "vx", "vy"}
        self.unstick = 0.0       # a moment after peeling off when it can't stick again
        self.side = None         # Twin Balls: "red" or "blue", whose ball this is (it keeps that colour)
        self.curve = 0.0         # Curveball: px/s^2 it bends up (negative) or down as it flies
        self.portal_cool = 0.0   # Portal Pair: a moment after coming out of a portal
        self.transit = None      # Portal Pair: inside one, on the way out of the other (1.8)
        self.hole_cool = 0.0     # Black Hole: a moment after being flung out, when it isn't pulled (1.8)
        self.hole_time = 0.0     # ...and how long it has been in a pull without falling in
        self.press = None        # (what last knocked it sideways, which side of that it was on, when)
        self.press_clock = 0.0   # seconds the ball has moved, to time those knocks
        self.rattled = -1.0      # when a ball rattling between two paddles last made its sound (1.8; real
                                 # time: the physics' own clock barely moves while it rattles)

    PRESS_WINDOW = 0.02          # knocked from both sides within this: it's caught in a squeeze
    RATTLE_FX = 0.05             # rattling between two paddles: its sound and sparks this often at most
    HELD_BY = 4                  # Sticky Goo: px of a held ball that stay beside the paddle's face

    def scores_in(self, nx):
        """Can this ball score in the goal it just reached (nx 1: the left goal, -1: the right)?
        Normally any ball can; under Twin Balls only in the goal of the other colour's player (a
        Switch hands goals and colours over together: the goal is its paddle's player's)."""
        if self.side is None:
            return True
        defender = self.game.p1 if nx == 1 else self.game.p2
        colour = getattr(defender, "colour", "red" if nx == 1 else "blue")
        return colour != self.side

    def commit_position(self, dt):
        self.press_clock += dt
        stuck = self.stuck
        if not stuck:
            super().commit_position(dt)
            return
        # Stuck to a Sticky paddle's face: carried along, slowly peeling away from it
        paddle = stuck["paddle"]
        k = 1 - stuck["left"] / stuck["total"]
        gap = 1 + 14 * k * k
        # It's held where it touched.  A big ball (a Snowball) caught on the paddle's end has its
        # middle out past the end; held no further out than the end, it was dragged onto the paddle,
        # up to 70 px in a frame.  It only has to keep a little of itself beside the face.
        reach = paddle.height / 2 + max(0.0, self.height / 2 - self.HELD_BY)
        cy = (paddle.y0 + paddle.y1) / 2 + clamp(stuck["dy"], -reach, reach)
        x0 = paddle.x1 + gap if stuck["side"] > 0 else paddle.x0 - gap - self.width
        x0 = clamp(x0, 1, BASE_W - self.width - 1)
        y0 = clamp(cy - self.height / 2, 0, BASE_H - self.height)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x0 + self.width, y0 + self.height
        self.vx, self.vy = paddle.vx, paddle.vy

    def can_collide_with(self, other):
        if self.stuck or self.transit:
            return False            # nothing knocks it off while it's stuck, or inside a portal
        if getattr(other, "is_ball", False):
            return False            # Twin Balls pass through each other
        if getattr(other, "is_obstacle", False):
            powerups = getattr(self.game, "powerups", None)
            if powerups and powerups.ghost and self is self.game.ball:
                return False        # a Ghost Ball drifts straight through tombstones and pillars
        return super().can_collide_with(other)

    def on_contact(self, other, data):
        nx, ny = data["normal"]
        sound_manager = self.game.app.sound_manager
        fx = self.game.app.fx
        cx, cy = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

        if other.is_paddle:
            paddle = other
            paddle.flash = 1.0   # the renderer fades this out

            # Caught between two paddles face to face, it rattles between them as long as they
            # press in (1.5's way: 1.6 squirted it out, and Rowan's 1.8 playtest wanted the rattle
            # back).  It goes up and down with them rather than with the angle of each knock: in
            # 1.5 it crept along their faces and slid out past their ends, within a second at 240
            # frames a second (it held at 120).  All that counts is the hit that caught it; the
            # rattle's sound and sparks come RATTLE_FX apart, not hundreds of times a second.
            squeezer = self.pressed_by(paddle) if nx != 0 and not self.stuck else None
            rattle = squeezer is not None and squeezer.is_paddle
            if rattle:
                self.vy = (paddle.vy + squeezer.vy) / 2
            if self.last_paddle is not paddle:
                if not rattle:
                    self.rally_value += 1
                now = time.perf_counter()
                if not rattle or now - self.rattled >= self.RATTLE_FX:
                    if rattle:
                        self.rattled = now
                    if sound_manager.paddle_hit_sound:
                        sound_manager.play(paddle.sound)

                    impact = theme.EMBER if paddle.colour == "red" else theme.SPIRIT_BLUE
                    fx.spark(cx, cy, 22, impact, speed = 520)
                    fx.burst(cx, cy, 2, 40, paddle.colour, life = (.7, 1.1))

            self.last_paddle = paddle

            powerups = getattr(self.game, "powerups", None)
            if powerups:
                powerups.on_hit(self, paddle, data["normal"])
            hook = getattr(self.game, "on_hit", None)
            if hook and not rattle:
                hook(self, paddle, data)

            if squeezer is not None and not rattle:
                self.squeeze_free(paddle, squeezer)         # a paddle drove it into a stone: out it squirts
                return

        if other.is_wall and other.is_goal:
            if not self.scores_in(nx):
                # Twin Balls: its own colour's goal just turns it back, at no less than serve speed
                self.vx = nx * max(abs(self.vx), self.speed)
                fx.spark(cx, cy, 14, theme.EMBER if self.side == "red" else theme.SPIRIT_BLUE, speed = 360, life = .5)
                match_sounds.happen(self.game, "wall", cx, cy, match_sounds.GOAL, match_sounds.force(self))
                self.squeeze_out(nx)
                return
            self.game.on_score(self, data)
            return

        if other.is_wall:
            if ny and self.curve:
                self.curve = -self.curve * 0.5    # Curveball: off the top or bottom its spin turns over
            fx.spark(cx, cy, 8, theme.FLAME, speed = 300, life = .45)
            hook = getattr(self.game, "on_bounce", None)
            if hook:
                hook(self, other)
        if getattr(other, "is_obstacle", False):
            hook = getattr(self.game, "on_bounce", None)
            if hook:
                hook(self, other)
            if nx != 0:
                squeezer = self.pressed_by(other)
                if squeezer is not None and squeezer.is_paddle:
                    self.squeeze_free(other, squeezer)

    def pressed_by(self, other):
        """Note that `other` (a paddle or a stone) just knocked the ball sideways, and answer what
        knocked it from its other side a moment ago, if anything.  A paddle driving it into a stone
        would bounce it between them on the spot hundreds of times a second, and the point could
        never end (see squeeze_free).  Two paddles face to face with the Middle Wall down do that
        too, and it's left to: the players can let it go (see on_contact, 1.8)."""
        side = 1 if self.x0 + self.x1 > other.x0 + other.x1 else -1    # which side of `other` it's on
        last, self.press = self.press, (other, side, self.press_clock)
        if last is None or last[0] is other or last[1] != -side:
            return None
        if self.press_clock - last[2] > self.PRESS_WINDOW or last[0] not in self.game.objects:
            return None
        return last[0]

    def squeeze_free(self, a, b):
        """Caught between `a` and `b` (see pressed_by): it squirts out past their nearer ends, up or
        down, at no less than serve speed, instead of rattling between them."""
        r = self.height / 2
        top, bottom = min(a.y0, b.y0), max(a.y1, b.y1)
        cy = (self.y0 + self.y1) / 2
        room_up, room_down = top >= self.height + 4, BASE_H - bottom >= self.height + 4
        go_up = room_up and (not room_down or cy - top <= bottom - cy)
        if not room_up and not room_down:
            go_up = cy < BASE_H / 2
        y = clamp(top - r - 3 if go_up else bottom + r + 3, r, BASE_H - r)
        self.y0, self.y1 = y - r, y + r
        speed = max(math.hypot(self.vx, self.vy), self.speed)
        self.vy = -speed * 0.9 if go_up else speed * 0.9
        self.vx = math.copysign(speed * 0.44, self.vx or 1.0)
        self.press = None

    def squeeze_out(self, nx):
        """Twin Balls: a ball pressed against its own goal by a paddle would bounce between the two
        on the spot, over and over (and stall the game's physics).  It squirts out past the
        paddle's nearer end instead, along the goal line and back into play."""
        r = self.width / 2
        game = self.game
        for paddle in (game.p1, game.p2):
            if not (paddle.y0 < self.y1 and paddle.y1 > self.y0):
                continue
            # the gap between this paddle's back and the goal the ball is against
            gap = paddle.x0 - game.left_wall.x1 if nx == 1 else game.right_wall.x0 - paddle.x1
            if gap > self.width + 6:
                continue
            up_room, down_room = paddle.y0, BASE_H - paddle.y1
            cy = (self.y0 + self.y1) / 2
            go_up = (up_room >= self.height + 6 and (cy < (paddle.y0 + paddle.y1) / 2 or down_room < self.height + 6))
            y = paddle.y0 - r - 3 if go_up else paddle.y1 + r + 3
            self.y0, self.y1 = y - r, y + r
            speed = max(math.hypot(self.vx, self.vy), self.speed)
            self.vy = -speed * 0.9 if go_up else speed * 0.9
            self.vx = nx * speed * 0.44
            return

    def reset(self):
        super().reset()
        self.last_paddle = None
        self.rally_value = 0
        self.stuck = None
        self.unstick = 0.0
        self.side = None
        self.curve = 0.0
        self.portal_cool = 0.0
        self.transit = None
        self.hole_cool = self.hole_time = 0.0
        self.press = None
        self.rattled = -1.0
