import pygame, random

from config import BASE_W, BASE_H
from render import theme
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

    def stop(self):
        super().stop()
        self.message_timer = 0
        self.message_color = (255, 255, 255)
        self.message_text = ""
        
    def build_world(self):
        # Walls & Separator
        self.top_wall = Wall(self, -10, -10, BASE_W + 10, 0)
        self.bottom_wall = Wall(self, -10, BASE_H, BASE_W + 10, BASE_H + 10)
        self.left_wall = Wall(self, -10, -10, 5, BASE_H + 10, color = theme.RED, is_goal = True)
        self.right_wall = Wall(self, BASE_W - 5, -10, BASE_W + 10, BASE_H + 10, color = theme.BLUE, is_goal = True)
        self.separator = Wall(self, BASE_W / 2, -10, BASE_W / 2, BASE_H + 10, is_separator = True)

        settings = self.app.settings.gameplay

        # Red (left) always uses W A S D, Blue (right) always uses the arrow keys
        p1_keys = dict(up = pygame.K_w,  down = pygame.K_s,    left = pygame.K_a,    right = pygame.K_d)
        p2_keys = dict(up = pygame.K_UP, down = pygame.K_DOWN, left = pygame.K_LEFT, right = pygame.K_RIGHT)
        
        # Players & Ball
        self.p1 = Paddle(self,
                         width = settings.paddle_width,
                         height = settings.paddle_height,
                         x = settings.paddle_width,
                         y = (BASE_H - settings.paddle_height) / 2,
                         speed = settings.paddle_speed,
                         **p1_keys,
                         color1 = "Red",
                         color2 = "Orange Red",
                         sound = "Hu.wav")

        self.p2 = Paddle(self,
                         width = settings.paddle_width,
                         height = settings.paddle_height,
                         x = BASE_W - 2 * settings.paddle_width,
                         y = (BASE_H - settings.paddle_height) / 2,
                         speed = settings.paddle_speed,
                         **p2_keys,
                         color1 = "Blue",
                         color2 = "Royal Blue",
                         sound = "Tao.wav")

        self.p1.controls_label, self.p2.controls_label = "W A S D", "Arrow Keys"

        # vs AI: the AI takes whichever paddle the player didn't pick
        self.p1.ai_enabled = settings.vs_ai and settings.play_as_blue
        self.p2.ai_enabled = settings.vs_ai and not settings.play_as_blue

        self.ball = Ball(self, diameter = settings.ball_diameter, x = (BASE_W - settings.ball_diameter) / 2, y = (BASE_H - settings.ball_diameter) / 2, speed = settings.ball_speed, color = "white")

    def on_score(self, obj, data):
        self.pause()
        nx, _ny = data["normal"]
        settings = self.app.settings.gameplay
        sound_manager = self.app.sound_manager
        win_score = settings.winning_scores[settings.winning_score_index]

        if nx == 1:
            self.p2.score += 1
            self.message_text = f"{self.p2.color1} scored!"
            self.message_color = (60, 140, 255)
            
            if not win_score == "Endless Mode" and self.p2.score >= win_score:
                if not settings.win_by_two or self.p2.score >= self.p1.score + 2:
                    self.app.state_manager.push_state(
                        "win", p1 = self.p1, p2 = self.p2,
                        winner=self.p2, loser=self.p1)
                    return
                    
        elif nx == -1:
            self.p1.score += 1
            self.message_text = f"{self.p1.color1} scored!"
            self.message_color = (255, 80, 80)
            
            if not win_score == "Endless Mode" and self.p1.score >= win_score:
                if not settings.win_by_two or self.p1.score >= self.p2.score + 2:
                    self.app.state_manager.push_state(
                        "win", p1 = self.p1, p2 = self.p2,
                        winner=self.p1, loser=self.p2)
                    return
   
        else:
            return
        
        if sound_manager.score_sound:
            self.app.sound_manager.play("euugh.wav")

        obj.spawn_vx = nx * obj.speed
        obj.spawn_vy = random.choice([1, -1]) * obj.speed

        self.message_timer = 2

    def reset_round(self):
        settings = self.app.settings.gameplay
        if settings.chaos_mode:
            settings.chaos_roll()
            self.apply_gameplay_settings()
            for obj in self.objects:
                if obj.is_ball:   # launch at the new speed, in the same directions
                    obj.spawn_vx = obj.speed * (1 if obj.spawn_vx >= 0 else -1)
                    obj.spawn_vy = obj.speed * (1 if obj.spawn_vy >= 0 else -1)

        for obj in self.objects:
            obj.reset()
            
        self.message_text = ""
        self.message_timer = 0.0
        
        self.start_countdown(3)

    def update(self, dt):
        super().update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.reset_round()

    def apply_gameplay_settings(self):
        super().apply_gameplay_settings()
        s = self.app.settings.gameplay

        for obj in self.objects:
            if obj.is_paddle:
                w_diff = abs(obj.width - s.paddle_width)
                h_diff = abs(obj.height - s.paddle_height)
                
                obj.width = s.paddle_width
                obj.height = s.paddle_height
                obj.speed = s.paddle_speed

                obj.x0 -= w_diff / 2
                obj.y0 -= h_diff / 2
                obj.x1 = obj.x0 + obj.width
                obj.y1 = obj.y0 + obj.height
                
                if obj.is_left:                    
                    obj.spawn_x = obj.width
                    obj.spawn_y = (BASE_H - obj.height) / 2
                    obj.home_x = obj.spawn_x + obj.width / 2
                    obj.home_y = obj.spawn_y + obj.height / 2
                    
                else:
                    obj.spawn_x = BASE_W - 2 * obj.width
                    obj.spawn_y = (BASE_H - obj.height) / 2
                    obj.home_x = obj.spawn_x + obj.width / 2
                    obj.home_y = obj.spawn_y + obj.height / 2    
                    
                
            if obj.is_ball:
                diff = abs(obj.diameter - s.ball_diameter)
                
                obj.width = s.ball_diameter
                obj.height = s.ball_diameter
                obj.diameter = s.ball_diameter
                obj.speed = s.ball_speed
                
                obj.x0 -= diff / 2
                obj.y0 -= diff / 2
                obj.x1 = obj.x0 + obj.width
                obj.y1 = obj.y0 + obj.height
                
                obj.spawn_x = (BASE_W - obj.width) /2
                obj.spawn_y = (BASE_H - obj.height) / 2
                obj.home_x = obj.spawn_x + obj.width / 2
                obj.home_y = obj.spawn_y + obj.height / 2
                
