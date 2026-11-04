import math
from config import BASE_H, DYNAMIC, KINEMATIC, MAX_BOUNCE_ANGLE, MAX_BALL_SPEEDUP
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

    def apply_inputs(self, dt):
        """Keys or the AI ask for a velocity and the paddle eases towards it.  A Jiangshi Hex
        flips what's asked for; under Gravity the paddle falls, and Up jumps off the floor."""
        if self.ai_enabled:
            dvx, dvy = self.ai_input(dt)
        else:
            keys = self.game.app.keys_down
            dvx = self.speed * ((self.right in keys) - (self.left in keys))
            dvy = self.speed * ((self.down in keys) - (self.up in keys))

        powerups = getattr(self.game, "powerups", None)
        if powerups and powerups.flipped(self):
            dvx, dvy = -dvx, -dvy

        a = 1 - math.exp(-self.soft_control_k * dt)
        self.vx += (dvx - self.vx) * a
        if powerups and powerups.gravity(self):
            # a clean fall and jump: undo the drag the physics step just applied to vy
            self.vy = self.vy / math.exp(-self.linear_drag * dt) + powerups.PADDLE_GRAVITY * dt
            if self.y1 >= BASE_H - 0.5 and dvy < -0.3 * self.speed:
                self.vy = -powerups.JUMP
        else:
            self.vy += (dvy - self.vy) * a

    def can_collide_with(self, other):
        if getattr(other, "is_separator", False):
            return self.game.wall_up
        # Paddles pass through each other, so neither can pin the other away from its goal
        return not other.is_paddle

    def on_contact(self, other, data):
        if other.body_type !=  DYNAMIC:
            return

        nx, ny = data["normal"]
        # A blocked ball loses pace, but never drops below its serve speed, so a rally can't stall
        serve = getattr(other, "speed", 0)
        speed = max(math.hypot(other.vx, other.vy), serve)

        # Hard hits speed it up, but ease off towards a ceiling so it never gets too quick to follow
        cap = MAX_BALL_SPEEDUP * serve * math.sqrt(2)     # serves go diagonally, at `serve` on each axis
        knee = 0.7 * cap
        if serve and speed > knee:
            speed = knee + (cap - knee) * math.tanh((speed - knee) / (cap - knee))

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
            # Caught on the paddle's end: still a return, at the steepest angle, rather than
            # a deflection that drops into the paddle's own goal
            forward = 1 if self.is_left else -1
            other.vx = forward * speed * math.cos(MAX_BOUNCE_ANGLE)
            other.vy = -ny * speed * math.sin(MAX_BOUNCE_ANGLE)

        # A paddle running into the ball faster than it bounces off would catch it again a few
        # frames later and carry it along, so the ball always leaves clearly faster than the paddle.
        # The extra lead stops at the speed ceiling; only a paddle faster than that pushes past it.
        out_x, out_y = -nx, -ny
        chasing = self.vx * out_x + self.vy * out_y
        leaving = other.vx * out_x + other.vy * out_y
        need = max(chasing + 150, min(chasing * 1.3, cap if serve else math.inf))
        if chasing > 0 and leaving < need:
            other.vx += out_x * (need - leaving)
            other.vy += out_y * (need - leaving)

            # ...and its sideways speed gives way, so the push doesn't take it past the ceiling
            limit = max(cap, need) if serve else math.inf
            if math.hypot(other.vx, other.vy) > limit:
                side_x, side_y = other.vx - out_x * need, other.vy - out_y * need
                side = math.hypot(side_x, side_y)
                keep = math.sqrt(max(0.0, limit * limit - need * need)) / side if side else 0.0
                other.vx = out_x * need + side_x * keep
                other.vy = out_y * need + side_y * keep

    # ------------------------ AI Logic ------------------------
    def ai_input(self, dt):
        return self.ai.decide(dt)

    def toggle_ai_state(self):
        self.ai_enabled = not self.ai_enabled
