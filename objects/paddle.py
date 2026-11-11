import math, random
from config import BASE_H, DYNAMIC, KINEMATIC, MAX_BOUNCE_ANGLE, MAX_BALL_SPEEDUP

FLAT_ANGLE = math.radians(3)    # returns flatter than this get a little spin
SPEED_KNEE = 0.85               # hard hits only start easing off at this share of the speed ceiling
HOLD_GAP = 150                  # px/s: after an end hit, the paddle trails the ball by at least this
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

        self.held = None                     # (ball, out_y) after hitting a ball with an end: see hold_back

    def apply_inputs(self, dt):
        """Keys or the AI ask for a velocity and the paddle eases towards it.  Under Gravity
        the paddle falls, and Up jumps off the floor."""
        net = getattr(self.game, "net", None)
        if self.ai_enabled:
            dvx, dvy = self.ai_input(dt)
        elif net and getattr(self, "remote", False):
            # Online: the friend's keys, as they last sent them
            x, y = net.keys_for(self)
            dvx, dvy = self.speed * x, self.speed * y
        else:
            keys = self.game.app.keys_down
            dvx = self.speed * ((self.right in keys) - (self.left in keys))
            dvy = self.speed * ((self.down in keys) - (self.up in keys))
            if net:                          # online, either set of keys moves your paddle
                other = self.game.app.settings.interface.keys("p2" if self.up == self.game.app.settings.interface.p1_up else "p1")
                dvx = dvx or self.speed * ((other["right"] in keys) - (other["left"] in keys))
                dvy = dvy or self.speed * ((other["down"] in keys) - (other["up"] in keys))
            touch = getattr(self.game.app, "touch", None)     # on a phone, a finger on this paddle (core/touch.py)
            steer = touch.steer_paddle(self) if touch else None
            if steer is not None:
                dvx, dvy = steer

        powerups = getattr(self.game, "powerups", None)

        self.want_vx = dvx                   # what its player asks for (a Snowball point needs a real shove)
        k = self.soft_control_k
        if powerups and getattr(self, "shoved", 0) > powerups.SHOVE_TIME - powerups.SNOW_REELING:
            k *= powerups.SNOW_GRIP          # reeling from a Snowball's hit: it carries the paddle back
        a = 1 - math.exp(-k * dt)
        self.vx += (dvx - self.vx) * a
        if powerups and powerups.gravity(self):
            self.gravity_jump(dt, dvy < -0.3 * self.speed, powerups)
        else:
            self.jump_held = None
            self.vy += (dvy - self.vy) * a
        self.hold_back()

    def hold_back(self):
        """A paddle that hit the ball with its top or bottom end can't run on through it: while the
        ball is still beside that end, the paddle moves towards it no faster than the ball moves
        away (and stops if the ball is coming back, say off the wall).  So the ball needn't be sped
        up to stay ahead of the paddle, and can't be pinned against a wall and pumped faster."""
        held = self.held
        if held is None:
            return
        if getattr(self, "remote", False) and getattr(self.game, "net", None):
            self.held = None                 # online, the friend's paddle goes where their keys say
            return
        ball, out_y = held
        beside = ball.x0 < self.x1 and ball.x1 > self.x0
        past_end = ball.y0 >= self.y1 - 4 if out_y > 0 else ball.y1 <= self.y0 + 4
        if not beside or not past_end or ball not in self.game.objects:
            self.held = None
            return
        limit = max(0.0, ball.vy * out_y - HOLD_GAP)
        if self.vy * out_y > limit:
            self.vy = out_y * limit

    def gravity_jump(self, dt, up, powerups):
        """Under Gravity the paddle falls, and Up jumps: a tap is a small hop, and the longer Up is
        held (up to half a second) the higher it goes, right up to the top of the court."""
        vy = self.vy / math.exp(-self.linear_drag * dt)        # a clean fall: undo the physics' drag
        g = powerups.PADDLE_GRAVITY
        held = getattr(self, "jump_held", None)
        if self.y1 >= BASE_H - 0.5 and up and vy >= -1 and held is None:
            vy, held = -powerups.JUMP, 0.0                      # off the floor
        elif held is not None:
            if up and vy < 0 and held < powerups.JUMP_HOLD:
                held += dt                                      # still holding: climbs on
                g *= powerups.HOLD_GRAVITY
            else:
                if not up and vy < -powerups.JUMP_CUT:
                    vy = -powerups.JUMP_CUT                     # let go early: the climb is cut short
                held = None
        self.jump_held = held
        self.vy = vy + g * dt

    def can_collide_with(self, other):
        if getattr(other, "is_separator", False):
            return self.game.wall_up
        if other.is_ball and getattr(self, "remote", False) and getattr(self.game, "net", None):
            # online, the friend's own screen says when their paddle hits the ball (see
            # Hu_Taong.apply_claim); Twin Balls' blue ball is played here, on the host
            return other is not self.game.ball
        # Paddles pass through each other, and through stones, so nothing can pin one away from its goal
        return not other.is_paddle and not getattr(other, "is_obstacle", False)

    def on_contact(self, other, data):
        if other.body_type !=  DYNAMIC:
            return
        touch = getattr(self.game.app, "touch", None)
        if touch:
            touch.felt_hit(self)                    # a phone buzzes as your paddle hits the ball

        nx, ny = data["normal"]
        # A blocked ball loses pace, but never drops below its serve speed, so a rally can't stall
        serve = getattr(other, "speed", 0)
        speed = max(math.hypot(other.vx, other.vy), serve)
        if ny != 0:
            # Off an end, the ball keeps the speed it came in at: the knock from a paddle sweeping
            # up or down isn't a hard hit towards the other player (it was, and sent the ball off
            # at 3 times serve speed)
            vx, vy = data.get("before", {}).get(other, (other.vx, other.vy))
            speed = max(math.hypot(vx, vy), serve)

        # Hard hits speed it up, but ease off towards a ceiling so it never gets too quick to follow
        cap = MAX_BALL_SPEEDUP * serve * math.sqrt(2)     # serves go diagonally, at `serve` on each axis
        knee = SPEED_KNEE * cap
        if serve and speed > knee:
            speed = knee + (cap - knee) * math.tanh((speed - knee) / (cap - knee))

        # -------------- Bouncy Center / Flat Edges --------------
        if nx !=  0:
            center = (self.y0 + self.y1) / 2
            other_center = (other.y0 + other.y1) / 2
            offset = (other_center - center) / (self.height / 2)
            offset = max(-1, min(1, offset))

            angle = offset * MAX_BOUNCE_ANGLE
            # A dead-centre hit gets a touch of spin, so two paddles can't trade perfectly flat
            # returns forever
            if abs(angle) < FLAT_ANGLE:
                angle = math.copysign(random.uniform(FLAT_ANGLE, 2 * FLAT_ANGLE),
                                      angle if angle else random.choice((-1, 1)))
            other.vx = -nx * speed * math.cos(angle)
            other.vy = speed * math.sin(angle)

        pinched = False
        if ny !=  0:
            # Caught on the paddle's end: still a return, at the steepest angle, rather than
            # a deflection that drops into the paddle's own goal
            forward = 1 if self.is_left else -1
            other.vx = forward * speed * math.cos(MAX_BOUNCE_ANGLE)
            other.vy = -ny * speed * math.sin(MAX_BOUNCE_ANGLE)

            # No room between the paddle's end and the wall: shoot it out forward along the wall
            room = self.y0 if ny > 0 else BASE_H - self.y1
            if room < other.height + 6:
                pinched = True
                other.vx = forward * speed
                other.vy = 0.0
                # and the paddle can't push it through the wall: it stops until the ball is clear,
                # or the two would meet again at once, over and over, and the ball would freeze
                if self.vy * ny < 0:
                    self.vy = 0.0

            # The paddle, not the ball, gives way: it can't chase the ball through its end (see
            # hold_back).  Speeding the ball up to outrun it instead sent end hits off at 3 times
            # serve speed, and a ball pinned against a wall came out at nearly 4 times.
            self.held = (other, -ny)
            self.hold_back()

        # A paddle running into the ball faster than it bounces off would catch it again a few
        # frames later and carry it along, so the ball always leaves clearly faster than the paddle.
        # The extra lead stops at the speed ceiling; only a paddle faster than that pushes past it.
        # (Off the paddle's face only: off an end, the paddle is held back instead.)
        out_x, out_y = -nx, -ny
        chasing = self.vx * out_x + self.vy * out_y
        leaving = other.vx * out_x + other.vy * out_y
        need = chasing + 150                                       # the least it must leave at
        want = max(need, min(chasing * 1.3, cap if serve else math.inf))
        if chasing > 0 and leaving < want and not pinched and ny == 0:
            # Speed the whole return up, keeping its angle; at the ceiling the angle flattens
            # only as far as it must for the ball to get clear
            total = math.hypot(other.vx, other.vy)
            share = leaving / total if total and leaving > 0 else 0.0      # cosine of the angle
            limit = max(cap, need) if serve else math.inf
            new_speed = min(limit, want / share) if share else need
            normal = max(need, new_speed * share)
            new_speed = max(new_speed, normal)
            side_x, side_y = other.vx - out_x * leaving, other.vy - out_y * leaving
            side = math.hypot(side_x, side_y)
            keep = math.sqrt(max(0.0, new_speed * new_speed - normal * normal)) / side if side else 0.0
            other.vx = out_x * normal + side_x * keep
            other.vy = out_y * normal + side_y * keep

        # Never leave it going straight up and down: it would bounce there forever, out of reach
        speed = math.hypot(other.vx, other.vy)
        if speed and abs(other.vx) < speed * 0.3:
            forward = 1 if self.is_left else -1
            other.vx = forward * speed * 0.3
            other.vy = math.copysign(speed * math.sqrt(1 - 0.09), other.vy or -1)

    # ------------------------ AI Logic ------------------------
    def ai_input(self, dt):
        return self.ai.decide(dt)

    def toggle_ai_state(self):
        self.ai_enabled = not self.ai_enabled
