import math
import random

from config import BASE_W, BASE_H, DYNAMIC
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

    def scores_in(self, nx):
        """Can this ball score in the goal it just reached (nx 1: Red's goal on the left, -1: Blue's)?
        Normally any ball can; under Twin Balls only in the other colour's goal."""
        if self.side == "red":
            return nx == -1
        if self.side == "blue":
            return nx == 1
        return True

    def commit_position(self, dt):
        stuck = self.stuck
        if not stuck:
            super().commit_position(dt)
            return
        # Stuck to a Sticky paddle's face: carried along, slowly peeling away from it
        paddle = stuck["paddle"]
        k = 1 - stuck["left"] / stuck["total"]
        gap = 1 + 14 * k * k
        half = paddle.height / 2
        cy = (paddle.y0 + paddle.y1) / 2 + clamp(stuck["dy"], -half, half)
        x0 = paddle.x1 + gap if stuck["side"] > 0 else paddle.x0 - gap - self.width
        x0 = clamp(x0, 1, BASE_W - self.width - 1)
        y0 = clamp(cy - self.height / 2, 0, BASE_H - self.height)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x0 + self.width, y0 + self.height
        self.vx, self.vy = paddle.vx, paddle.vy

    def can_collide_with(self, other):
        if self.stuck:
            return False            # nothing knocks it off while it's stuck
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

            if self.last_paddle is not paddle:
                self.rally_value += 1
                if sound_manager.paddle_hit_sound:
                    sound_manager.play(paddle.sound)

                impact = theme.EMBER if paddle.is_left else theme.SPIRIT_BLUE
                fx.spark(cx, cy, 22, impact, speed = 520)
                fx.burst(cx, cy, 2, 40, "red" if paddle.is_left else "blue", life = (.7, 1.1))

            self.last_paddle = paddle

            powerups = getattr(self.game, "powerups", None)
            if powerups:
                powerups.on_hit(self, paddle, data["normal"])
            hook = getattr(self.game, "on_hit", None)
            if hook:
                hook(self, paddle, data)

        if other.is_wall and other.is_goal:
            if not self.scores_in(nx):
                # Twin Balls: its own colour's goal just turns it back, at no less than serve speed
                self.vx = nx * max(abs(self.vx), self.speed)
                fx.spark(cx, cy, 14, theme.EMBER if self.side == "red" else theme.SPIRIT_BLUE, speed = 360, life = .5)
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
