import random
from config import APP_WIDTH, APP_HEIGHT
from helpers import play_sound
from game.game_base import GameBase
from objects.wall import Wall
from objects.ball import Ball
from objects.paddle import Paddle

class Hu_Taong(GameBase):                        
    def build_world(self):
        # Walls & Separator
        self.top_wall = Wall(self, -100, -100, APP_WIDTH + 100, 0)
        self.bottom_wall = Wall(self, -100, APP_HEIGHT, APP_WIDTH + 100, APP_HEIGHT + 100)
        self.left_wall = Wall(self, -100, -100, 0, APP_HEIGHT + 100, is_goal = True)
        self.right_wall = Wall(self, APP_WIDTH, -100, APP_WIDTH + 100, APP_HEIGHT + 100, is_goal = True)
        self.separator = Wall(self, APP_WIDTH/2, -100, APP_WIDTH/2, APP_HEIGHT + 100, is_separator = True)
        
        # Players & Ball
        self.p1 = Paddle(self, width = 30, height = 180,
                         x = 30, y = (APP_HEIGHT - 180)/2,
                         up = "w", down = "s", left = "a", right = "d",
                         color1 = "Red", color2 = "Orange Red", sound = "Hu.wav")

        self.p2 = Paddle(self, width = 30, height = 180,
                         x = APP_WIDTH - 60, y = (APP_HEIGHT - 180)/2,
                         up = "Up", down = "Down", left = "Left", right = "Right",
                         color1 = "Blue", color2 = "Royal Blue", sound = "Tao.wav")
        
        self.ball = Ball(self, diameter = 50,
                         x = (APP_WIDTH - 50)/2,
                         y = (APP_HEIGHT - 50)/2)

    def on_score(self, obj, data):
        self.pause()
        play_sound("euugh.wav")
        nx, ny = data["normal"]

        if nx  ==  1:
            self.p2.score +=  1
            self.canvas.itemconfigure(self.hud.p1_score_id, text = f"{self.p2.color1}: {self.p2.score}")
            msg = f"{self.p2.color1} scored!"
            msg_color = self.p2.color1
        elif nx  ==  -1:
            self.p1.score +=  1
            self.canvas.itemconfigure(self.hud.p1_score_id, text = f"{self.p1.color1}: {self.p1.score}")
            msg = f"{self.p1.color1} scored!"
            msg_color = self.p1.color1
        else:
            return

        text_id = self.canvas.create_text(APP_WIDTH/2, APP_HEIGHT/2, text = msg,
                                          font = ("Helvetica", 60, "bold"),
                                          fill = msg_color)

        obj.spawn_vx = nx * obj.speed
        obj.spawn_vy = random.choice([1, -1]) * obj.speed

        self.root.after(2000, lambda: (self.canvas.delete(text_id), self.reset_round()))

    def reset_round(self):
        for obj in self.objects:
            obj.reset()
        self.hud.update()
        self.countdown(seconds = 3)
