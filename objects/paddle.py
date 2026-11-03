import math
from config import DYNAMIC, KINEMATIC, MAX_BOUNCE_ANGLE
from objects.ai import PaddleAI
from objects.game_object import GameObject

class Paddle(GameObject):
    body_type = KINEMATIC
    is_paddle = True
    has_inputs = True
    soft_controls = True

    def __init__(self, game, width, height, x, y, speed,
                 up, down, left, right, color1, color2, sound):

        super().__init__(game, width, height, x, y,
                         inv_mass = 0.05,
                         restitution = 0.6,
                         linear_drag = 1)

        self.up = up
        self.down = down
        self.left = left
        self.right = right
        self.speed = speed

        self.is_left = self.home_x < self.game.width / 2

        self.color1 = color1
        self.color2 = color2
        self.sound = sound
        self.score = 0


        # ------------------ AI Settings ------------------
        # The AI itself lives in objects/ai.py
        self.ai_enabled = False
        self.ai = PaddleAI(self)

    def can_collide_with(self, other):
        if getattr(other, "is_separator", False):
            return self.game.settings.middle_wall
        return True

    def on_contact(self, other, data):
        if other.body_type !=  DYNAMIC:
            return

        nx, ny = data["normal"]
        # A blocked ball loses pace, but never drops below its serve speed, so a rally can't stall
        speed = max(math.hypot(other.vx, other.vy), getattr(other, "speed", 0))

        # -------------- Bouncy Center / Flat Edges --------------
        if nx !=  0:
            center = (self.y0 + self.y1) / 2
            other_center = (other.y0 + other.y1) / 2
            offset = (other_center - center) / (self.height / 2)
            offset = max(-1, min(1, offset))

            angle = offset * MAX_BOUNCE_ANGLE
            other.vx = -nx * speed * math.cos(angle)
            other.vy = speed * math.sin(angle)

        if ny !=  0:
            center = (self.x0 + self.x1) / 2
            other_center = (other.x0 + other.x1) / 2
            offset = (other_center - center) / (self.width / 2)
            offset = max(-1, min(1, offset))

            angle = offset * MAX_BOUNCE_ANGLE
            other.vx = speed * math.sin(angle)
            other.vy = -ny * speed * math.cos(angle)

    # ------------------------ AI Logic ------------------------
    def ai_input(self, dt):
        return self.ai.decide(dt)

    def toggle_ai_state(self):
        self.ai_enabled = not self.ai_enabled
