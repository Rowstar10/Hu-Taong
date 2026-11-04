import math
import random

from config import DYNAMIC
from helpers import lerp
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
                powerups = getattr(self.game, "powerups", None)
                if powerups:
                    powerups.on_rally(self.rally_value)
                if sound_manager.paddle_hit_sound:
                    sound_manager.play(paddle.sound)

                impact = theme.EMBER if paddle.is_left else theme.SPIRIT_BLUE
                fx.spark(cx, cy, 22, impact, speed = 520)
                fx.burst(cx, cy, 2, 40, "red" if paddle.is_left else "blue", life = (.7, 1.1))

            self.last_paddle = paddle

            powerups = getattr(self.game, "powerups", None)
            if powerups:
                powerups.on_hit(self, paddle)

        if other.is_wall and other.is_goal:
            self.game.on_score(self, data)
            return

        if other.is_wall:
            fx.spark(cx, cy, 8, theme.FLAME, speed = 300, life = .45)

    def reset(self):
        super().reset()
        self.last_paddle = None
        self.rally_value = 0
