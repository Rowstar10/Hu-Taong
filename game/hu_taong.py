import pygame, random

from config import BASE_W, BASE_H
from game.game_base import GameBase
from objects.wall import Wall
from objects.ball import Ball
from objects.paddle import Paddle


class Hu_Taong(GameBase):
    def __init__(self, app, width=BASE_W, height=BASE_H):
        super().__init__(app, width, height)
        self.message_text = ""
        self.message_color = (255, 255, 255)
        self.message_timer = 0.0

    def build_world(self):
        # Walls & Separator
        self.top_wall = Wall(self, -100, -100, BASE_W + 100, 0)
        self.bottom_wall = Wall(self, -100, BASE_H, BASE_W + 100, BASE_H + 100)
        self.left_wall = Wall(self, -100, -100, 5, BASE_H + 100, color = "Red", is_goal = True)
        self.right_wall = Wall(self, BASE_W - 5, -100, BASE_W + 100, BASE_H + 100, color = "Blue", is_goal = True)
        self.separator = Wall(self, BASE_W / 2, -100, BASE_W / 2, BASE_H + 100, is_separator = True)

        # Players & Ball
        self.p1 = Paddle(
            self,
            width=30,
            height=180,
            x=30,
            y=(BASE_H - 180) / 2,
            up = pygame.K_w,
            down = pygame.K_s,
            left = pygame.K_a,
            right = pygame.K_d,
            color1 = "Red",
            color2 = "Orange Red",
            sound="Hu.wav",
        )

        self.p2 = Paddle(
            self,
            width=30,
            height=180,
            x=BASE_W - 60,
            y=(BASE_H - 180) / 2,
            up = pygame.K_UP,
            down = pygame.K_DOWN,
            left = pygame.K_LEFT,
            right = pygame.K_RIGHT,
            color1="Blue",
            color2="Royal Blue",
            sound="Tao.wav",
        )

        self.ball = Ball(self, diameter=50, x=(BASE_W - 50) / 2, y=(BASE_H - 50) / 2)

    def on_score(self, obj, data):
        self.pause()
        self.app.sound.play("euugh.wav", category="score")

        nx, _ny = data["normal"]

        if nx == 1:
            self.p2.score += 1
            self.message_text = f"{self.p2.color1} scored!"
            self.message_color = (60, 140, 255)
        elif nx == -1:
            self.p1.score += 1
            self.message_text = f"{self.p1.color1} scored!"
            self.message_color = (255, 80, 80)
        else:
            return

        obj.spawn_vx = nx * obj.speed
        obj.spawn_vy = random.choice([1, -1]) * obj.speed

        self.message_timer = 2

    def reset_round(self):
        for obj in self.objects:
            obj.reset()
        self.start_countdown(3)

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message_timer = 0
                self.message_text = ""
                self.reset_round()

        super().update(dt)
