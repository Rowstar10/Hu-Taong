import math, random
from config import BASE_H, DYNAMIC, KINEMATIC, MAX_BOUNCE_ANGLE, MAX_BALL_SPEEDUP
from game import engines
from game.engines import CLASSIC, V09

FLAT_ANGLE = math.radians(3)    # returns flatter than this get a little spin
SPEED_KNEE = 0.85               # hard hits only start easing off at this share of the speed ceiling
HOLD_GAP = 150                  # px/s: after an end hit, the paddle trails the ball by at least this
GIVE_GAP = 30                   # px: a paddle that mustn't catch its own ball is held back only this close to it
from objects.ai import PaddleAI
from objects.game_object import GameObject

class Paddle(GameObject):
    body_type = KINEMATIC
    is_paddle = True
    has_inputs = True
    soft_controls = True

    @property
    def colour(self):
        """"red" or "blue": whose paddle it is now.  A Switch hands a paddle to the other player,
        and their colour goes with them (color1, swapped in Hu_Taong.switch_sides)."""
        return self.color1.lower()

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
        self.trail = None                    # (ball, out_x) after a face hit it mustn't catch again: see keep_behind

    def apply_inputs(self, dt):
        """Keys or the AI ask for a velocity and the paddle eases towards it."""
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
                other = self.game.app.settings.gameplay.keys("p2" if self.up == self.game.app.settings.gameplay.p1_up else "p1")
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
        self.vy += (dvy - self.vy) * a
        self.hold_back()
        self.keep_behind()

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

    def can_collide_with(self, other):
        if getattr(other, "is_separator", False):
            return self.game.wall_up
        if other.is_ball and getattr(self, "remote", False) and getattr(self.game, "net", None):
            # online, the friend's own screen says when their paddle hits the ball (see
            # Hu_Taong.apply_claim); Twin Balls' blue ball is played here, on the host
            return other is not self.game.ball
        # Paddles pass through each other, and through stones, so nothing can pin one away from its goal
        return not other.is_paddle and not getattr(other, "is_obstacle", False)

    def keep_behind(self, just_hit=False):
        """Classic physics, or the Speed Cap (1.8): a paddle that has hit the ball off its face
        can't run on into it and knock it again, which would hand on its speed after all.  While
        the ball is going away just in front of its face, until someone else plays it, the paddle
        moves forward no faster than the ball moves away (as hold_back does after an end hit).

        Only just in front (1.8 playtest): held back whenever its shot was anywhere ahead, a paddle
        charging forward after a slow or steep shot crawled across the court, for no reason the
        player could see."""
        trail = self.trail
        if trail is None:
            return
        if getattr(self, "remote", False) and getattr(self.game, "net", None):
            self.trail = None                # online, the friend's paddle goes where their keys say
            return
        ball, out_x = trail
        if ball not in self.game.objects or (not just_hit and ball.last_paddle is not self):
            self.trail = None
            return
        if getattr(ball, "stuck", None):
            return                           # Sticky Goo carries it: it moves with the paddle
        ahead = ball.x0 - self.x1 if out_x > 0 else self.x0 - ball.x1
        if ahead < -2 or not (ball.y1 > self.y0 and ball.y0 < self.y1):
            return                           # not in front of the face just now
        if ball.vx * out_x <= 0:
            return                           # coming back: it's there to be played
        closing = (self.vx - ball.vx) * out_x
        if ahead > GIVE_GAP + max(0.0, closing) / 30:
            return                           # not about to catch it (a frame of up to 1/30 s ahead)
        limit = max(0.0, ball.vx * out_x - HOLD_GAP)
        if self.vx * out_x > limit:
            self.vx = out_x * limit

    def give_way(self, ball, out_x):
        self.trail = (ball, out_x)
        self.keep_behind(just_hit=True)

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
        # The match's physics (Ball & Paddles, 1.8): how the ball comes off, and the Speed Cap
        rules = getattr(self.game, "settings", None)
        physics = getattr(rules, "physics", engines.CURRENT)
        capped = bool(getattr(rules, "speed_cap", False)) and physics != CLASSIC

        # Swift Step makes the paddle quicker, not its hits harder: off its face, a knock from a
        # paddle going faster than its normal top speed is played as if at that speed (the extra
        # power was most of Swift Step's edge: its taker won 74% of points against the Hard AI).
        # The Speed Cap does the same with a lower limit.
        top = self.top_speed()
        if capped:
            top = min(top, engines.cap_drive(getattr(other, "speed", 0)))
        before = data.get("before", {})
        if nx != 0 and top < math.inf and self in before and other in before:
            pvx, pvy = before[self]
            drive = -(pvx * nx + pvy * ny)                 # towards the ball's way out
            if drive > top:
                other.vx, other.vy = self.knock(other, data, pvx + nx * (drive - top), pvy + ny * (drive - top))

        if physics == CLASSIC:
            self.classic_return(other, nx, ny)
            return
        if physics == V09:
            self.v09_return(other, nx, ny, capped)
            return

        # ---- Current physics (1.7's) from here ----
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
            angle = self.face_angle(other)
            other.vx = -nx * speed * math.cos(angle)
            other.vy = speed * math.sin(angle)

        pinched = False
        if ny !=  0:
            pinched = self.off_the_end(other, ny, speed)

        # A paddle running into the ball faster than it bounces off would catch it again a few
        # frames later and carry it along, so the ball always leaves clearly faster than the paddle.
        # The extra lead stops at the speed ceiling; only a paddle faster than that pushes past it.
        # (Off the paddle's face only: off an end, the paddle is held back instead.  With the
        # Speed Cap, the paddle gives way instead, or the lead would hand on its speed after all.)
        out_x, out_y = -nx, -ny
        chasing = self.vx * out_x + self.vy * out_y
        leaving = other.vx * out_x + other.vy * out_y
        need = chasing + 150                                       # the least it must leave at
        want = max(need, min(min(chasing, top) * 1.3, cap if serve else math.inf))
        if chasing > 0 and leaving < want and not pinched and ny == 0 and not capped:
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
        if capped and nx != 0:
            self.give_way(other, out_x)

        self.never_upright(other)

    def face_angle(self, other, spin=True):
        """The angle the ball leaves the face at: by where it met the paddle, straight back from
        the middle, up to MAX_BOUNCE_ANGLE at the ends.  A dead-centre hit gets a touch of spin, so
        two paddles can't trade perfectly flat returns forever (not under v0.9's physics)."""
        center = (self.y0 + self.y1) / 2
        other_center = (other.y0 + other.y1) / 2
        offset = (other_center - center) / (self.height / 2)
        offset = max(-1, min(1, offset))

        angle = offset * MAX_BOUNCE_ANGLE
        if spin and abs(angle) < FLAT_ANGLE:
            angle = math.copysign(random.uniform(FLAT_ANGLE, 2 * FLAT_ANGLE),
                                  angle if angle else random.choice((-1, 1)))
        return angle

    def off_the_end(self, other, ny, speed):
        """Caught on the paddle's end: still a return, at the steepest angle, rather than a
        deflection that drops into the paddle's own goal.  Answers whether it was pinned."""
        forward = 1 if self.is_left else -1
        other.vx = forward * speed * math.cos(MAX_BOUNCE_ANGLE)
        other.vy = -ny * speed * math.sin(MAX_BOUNCE_ANGLE)
        pinched = self.free_if_pinned(other, ny, speed)

        # The paddle, not the ball, gives way: it can't chase the ball through its end (see
        # hold_back).  Speeding the ball up to outrun it instead sent end hits off at 3 times
        # serve speed, and a ball pinned against a wall came out at nearly 4 times.
        self.held = (other, -ny)
        self.hold_back()
        return pinched

    def free_if_pinned(self, other, ny, speed):
        """No room between the paddle's end and the wall: shoot it out forward along the wall."""
        room = self.y0 if ny > 0 else BASE_H - self.y1
        if room >= other.height + 6:
            return False
        other.vx = (1 if self.is_left else -1) * speed
        other.vy = 0.0
        # and the paddle can't push it through the wall: it stops until the ball is clear, or the
        # two would meet again at once, over and over, and the ball would freeze
        if self.vy * ny < 0:
            self.vy = 0.0
        return True

    def never_upright(self, other):
        """Never leave it going straight up and down: it would bounce there forever, out of reach."""
        speed = math.hypot(other.vx, other.vy)
        if speed and abs(other.vx) < speed * 0.3:
            forward = 1 if self.is_left else -1
            other.vx = forward * speed * 0.3
            other.vy = math.copysign(speed * math.sqrt(1 - 0.09), other.vy or -1)

    def classic_return(self, other, nx, ny):
        """Classic physics (1.8): the ball leaves at the rally's speed, a step faster every hit up
        to the usual top speed, angled by where it met the paddle.  The paddle's movement adds
        nothing, and the paddle gives way rather than catching its own ball again."""
        hits = getattr(other, "rally_value", 0) + (getattr(other, "last_paddle", None) is not self)
        serve = getattr(other, "speed", 0)
        speed = engines.classic_speed(serve, hits) if serve else math.hypot(other.vx, other.vy)
        if nx != 0:
            angle = self.face_angle(other)
            other.vx = -nx * speed * math.cos(angle)
            other.vy = speed * math.sin(angle)
            self.give_way(other, -nx)
        else:
            self.off_the_end(other, ny, speed)
        self.never_upright(other)

    def v09_return(self, other, nx, ny, capped):
        """Hu Taong 0.9's physics (1.8): the ball leaves at the knock's own speed (drive into it to
        speed it up; a still paddle slows it), with no top speed, angled by where it met the paddle,
        off an end as well (mostly up or down).  Only what kept 0.9's points from ever ending is
        added: a little speed at the least, never quite straight up or down, and a ball pinned
        against the wall shoots out along it.  With the Speed Cap, the paddle gives way too.
        (tests/test_physics_engines.py checks it against 0.9's own code.)"""
        speed = max(math.hypot(other.vx, other.vy), engines.v09_floor(getattr(other, "speed", 0)))
        if nx != 0:
            angle = self.face_angle(other, spin=False)
            other.vx = -nx * speed * math.cos(angle)
            other.vy = speed * math.sin(angle)
            if capped:
                self.give_way(other, -nx)
            return
        offset = ((other.x0 + other.x1) / 2 - (self.x0 + self.x1) / 2) / (self.width / 2)
        other.vx, other.vy = engines.v09_off_the_end(offset, ny, speed, 1 if self.is_left else -1)
        self.free_if_pinned(other, ny, speed)
        if capped:
            self.held = (other, -ny)
            self.hold_back()

    def top_speed(self):
        """This paddle's normal top speed, when Swift Step has it going faster (else infinity)."""
        powerups = getattr(self.game, "powerups", None)
        factor = powerups.speed_factor(self) if powerups else 1.0
        return self.speed / factor if factor > 1 else math.inf

    def knock(self, ball, data, pvx, pvy):
        """The ball's velocity after a knock from this paddle moving at (pvx, pvy), as
        Physics.resolve_collision plays it (the paddle is its first body)."""
        bvx, bvy = data["before"][ball]
        nx, ny = data["normal"]
        rvn = (pvx - bvx) * nx + (pvy - bvy) * ny
        if rvn > 0:
            return bvx, bvy
        res = (self.restitution + ball.restitution) / 2
        imp = -(1 + res) * rvn / (self.inv_mass + ball.inv_mass) * ball.inv_mass
        return bvx - imp * nx, bvy - imp * ny

    # ------------------------ AI Logic ------------------------
    def ai_input(self, dt):
        return self.ai.decide(dt)

    def toggle_ai_state(self):
        self.ai_enabled = not self.ai_enabled
