import math, random
from config import DYNAMIC
from helpers import play_sound, lerp
from objects.game_object import GameObject

class Ball(GameObject):
    body_type = DYNAMIC
    is_ball = True
    can_score = True
    
    def __init__(self, game, diameter, x, y,
                 speed = 500, color = "white"):
        
        super().__init__(game, diameter, diameter, x, y,
                         vx = random.choice([1, -1]) * speed,
                         vy = random.choice([1, -1]) * speed,
                         restitution = 0.4)
        
        self.diameter = diameter
        self.speed = speed
        self.color = color
        self.rally_value = 0
        self.last_paddle = None
        
        self.id = self.canvas.create_oval(self.x0, self.y0, self.x1, self.y1, fill = color)

    def on_contact(self, other, data):
        nx, ny = data["normal"]
        if other.is_paddle:
            paddle = other
            
            if self.last_paddle is not paddle:
                play_sound(paddle.sound)
                self.rally_value +=  1
                self.vx += nx * self.speed * lerp(0.1, 2, self.rally_value/100)
                self.vy += ny * self.speed * lerp(0.1, 2, self.rally_value/100)
                self.game.hud.update()

            self.last_paddle = paddle

        if other.is_wall and other.is_goal:
            self.game.on_score(self, data)
            return

    def reset(self):
        super().reset()        
        self.last_paddle = None
        self.rally_value = 0
