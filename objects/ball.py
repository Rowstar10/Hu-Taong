import math
import random

from config import DYNAMIC
from helpers import lerp
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
        
        if other.is_paddle:
            paddle = other

            if self.last_paddle is not paddle:
                self.rally_value += 1
                if sound_manager.paddle_hit_sound:
                    sound_manager.play(paddle.sound)

            self.last_paddle = paddle

        if other.is_wall and other.is_goal:
            self.game.on_score(self, data)
            return

    def reset(self):
        super().reset()
        self.last_paddle = None
        self.rally_value = 0
