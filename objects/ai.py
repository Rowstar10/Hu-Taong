"""How the computer plays a paddle.

Every frame the AI goes through the same steps a person does:

  perceive  the ball as it was a moment ago (its reaction time), and extrapolate
  predict   where it will cross the paddle's line; the guess starts rough and
            sharpens as the ball gets closer, and only a skilled AI can follow
            the ball through several wall bounces
  decide    where to meet it and which part of the paddle to hit it with, so the
            return goes where the opponent isn't, without cutting it so fine
            that its own misjudgement would make it miss
  move      there, easing in rather than snapping, with the odd hesitation

Difficulty sets how well each step is done.  The style sets what the AI tries to do.
"""
import math, random
from collections import deque

from config import BASE_W, BASE_H, MAX_BOUNCE_ANGLE
from helpers import clamp, lerp, reflect_in_range

# One column per difficulty: Baby, Easy, Normal, Hard, Insane.  Adaptive AI slides between them.
SKILL = {
    "reaction":  (0.30, 0.21, 0.14, 0.09, 0.05),   # seconds behind what is really happening
    "misread":   (300,  190,  110,  55,   20),     # px of guessing error per second the ball is still away
    "wobble":    (85,   66,   56,   50,   38),      # px of error that never goes away, however close the ball
    "foresight": (0,    1,    1,    2,    3),      # wall bounces it can follow in its head
    "pace":      (0.55, 0.70, 0.85, 0.95, 1.00),   # share of the paddle's top speed it uses
    "aim":       (0.00, 0.25, 0.50, 0.80, 1.00),   # how much it tries to place its returns
    "lapse":     (0.22, 0.12, 0.06, 0.02, 0.00),   # chance of a moment's hesitation on each shot
    "press":     (0.10, 0.25, 0.40, 0.55, 0.70),   # how far it steps in to meet the ball
    "strike":    (0.35, 0.50, 0.70, 0.85, 1.00),   # how hard it drives into the ball on contact
}

# What each style does to the numbers above (one factor, or one per difficulty), plus three habits of its own:
#   bank      how much it likes returns that bounce off the walls on the way
#   nerve     how close to the paddle's edge it dares meet the ball (1 = sensible)
#   disguise  it lines up as if to aim one way and switches at the last moment
STYLES = {
    "Balanced":  {"bank": 0.3},
    "Guardian":  {"press": 0.2, "aim": 0.6, "strike": 0.7, "wobble": (0.9, 0.9, 0.95, 0.95, 1.05),
                  "bank": 0.2, "nerve": 0.7},
    "Striker":   {"press": 1.7, "aim": 1.2, "lapse": 1.3, "strike": 1.25, "wobble": (1, 1, 1, 1, 0.85),
                  "bank": 0.2, "nerve": 1.1},
    "Trickster": {"aim": 1.35, "wobble": (1, 1, 1, 1, 0.92), "bank": 1.0, "nerve": 1.15, "disguise": 1.0},
}
HABITS = {"bank": 0.0, "nerve": 1.0, "disguise": 0.0}

CONTACT_OFFSETS = (-0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75)


def falling(y, vy, t, g, lo, hi, step=1 / 120):
    """Where a ball under Gravity will be after `t` seconds, bouncing off the floor and ceiling."""
    for _ in range(min(int(t / step), 480)):
        vy += g * step
        y += vy * step
        if y < lo:
            y, vy = 2 * lo - y, -vy
        elif y > hi:
            y, vy = 2 * hi - y, -vy
    return y


class PaddleAI:
    MEMORY = 0.5        # seconds of the ball's past positions it keeps
    EASE = 110          # px over which it slows down as it arrives
    STRIKE_TIME = 0.3   # seconds before contact that it drives forward into the ball

    def __init__(self, paddle):
        self.paddle = paddle
        self.reset()

    def reset(self):
        """Forget everything; used when the AI takes over a paddle."""
        self.seen = deque()
        self.clock = 0.0
        self.incoming = False
        self.noise = 0.0
        self.aim = None
        self.hesitate = 0.0
        self.sway = random.uniform(0, math.tau)
        self.t_hit = math.inf
        self.jump = False
        self.target = (self.paddle.home_x, self.paddle.home_y)

    # ---------------- Skill ----------------

    def params(self):
        game = self.paddle.game
        settings = game.settings
        opponent = self.opponent()
        skill = settings.ai_skill(self.paddle.score, opponent.score)
        lo = int(skill)
        hi = min(lo + 1, len(SKILL["pace"]) - 1)
        style = STYLES[settings.ai_styles[settings.ai_style]]

        def at_skill(values):
            return lerp(values[lo], values[hi], skill - lo) if isinstance(values, tuple) else values

        k = {name: at_skill(column) * at_skill(style.get(name, 1.0)) for name, column in SKILL.items()}
        k["foresight"] = round(k["foresight"])
        k["aim"] = min(1.0, k["aim"])
        k.update({name: style.get(name, default) for name, default in HABITS.items()})
        return k

    def opponent(self):
        game = self.paddle.game
        return game.p2 if self.paddle is game.p1 else game.p1

    # ---------------- Perceive ----------------

    def perceive(self, ball, dt, reaction):
        """The ball as the AI believes it is now: last seen `reaction` ago, then extrapolated."""
        self.clock += dt
        r = ball.diameter / 2
        powerups = getattr(self.paddle.game, "powerups", None)
        if not (powerups and powerups.hidden_from(self.paddle) and self.seen):
            # a Ghost Ball out of sight leaves the AI working from where it last saw it
            self.seen.append((self.clock, (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, ball.vx, ball.vy))
        while len(self.seen) > 1 and self.seen[0][0] < self.clock - self.MEMORY:
            self.seen.popleft()

        past = self.seen[0]
        for record in self.seen:
            if record[0] > self.clock - reaction:
                break
            past = record

        t, x, y, vx, vy = past
        lag = self.clock - t
        y, bounces = reflect_in_range(y + vy * lag, r, BASE_H - r)
        return x + vx * lag, y, vx, vy if bounces % 2 == 0 else -vy

    # ---------------- Decide ----------------

    def towards_goal(self, vx):
        return vx < 0 if self.paddle.is_left else vx > 0

    def line_x(self, k):
        """Where the paddle's centre waits for the ball: at home, or stepped in towards the middle."""
        p = self.paddle
        forward = 1 if p.is_left else -1
        if p.game.wall_up:
            limit, most = BASE_W / 2 - forward * (p.width / 2 + 8), 1.0
        else:
            # No wall: a bold AI may cross halfway, but not so far it has no time to see the ball coming
            limit, most = BASE_W / 2 + forward * BASE_W * 0.12, 0.6
        room = (limit - p.home_x) * forward
        return p.home_x + forward * room * clamp(k["press"] * 0.6, 0, most)

    def new_shot(self, k):
        self.noise = random.gauss(0, 1)
        self.aim = None
        self.hesitate = random.uniform(0.12, 0.3) if random.random() < k["lapse"] else 0.0

    def reach(self, r, k):
        """How far off-centre it dares meet the ball: a sure hand cuts it fine, a shaky one plays safe."""
        p = self.paddle
        half = p.height / 2
        doubt = k["wobble"] + k["misread"] * 0.12          # its likely misjudgement at contact
        margin = 10 + 2.6 * doubt / k["nerve"]
        safe = (half + r - margin) / (half * 0.9)
        return clamp(min(safe, 0.3 + 0.45 * k["aim"]), 0, 0.75)

    def choose_aim(self, contact_x, contact_y, speed, r, k):
        """Which part of the paddle to hit with: -1 is the top edge, 1 the bottom."""
        reach = self.reach(r, k)
        if random.random() > k["aim"]:
            return clamp(random.uniform(-0.2, 0.2), -reach, reach)     # just get it back

        opponent = self.opponent()
        opp_x = (opponent.x0 + opponent.x1) / 2
        opp_y = (opponent.y0 + opponent.y1) / 2
        away = 1 if self.paddle.is_left else -1
        best, best_score = 0.0, -math.inf

        for offset in CONTACT_OFFSETS:
            if abs(offset) > reach + 1e-6:
                continue
            angle = offset * MAX_BOUNCE_ANGLE
            vx, vy = away * speed * math.cos(angle), speed * math.sin(angle)
            t = abs(opp_x - contact_x) / max(abs(vx), 1)
            arrive, bounces = reflect_in_range(contact_y + vy * t, r, BASE_H - r)
            # how far the opponent must travel, against how far it can in the time,
            # and wall bounces on the way make a return harder to read
            score = abs(arrive - opp_y) - opponent.speed * t * 0.35 + k["bank"] * min(bounces, 3) * 90
            if score > best_score:
                best, best_score = offset, score
        return best

    def meet(self, bx, by, vx, vy, r, k):
        p = self.paddle
        forward = 1 if p.is_left else -1
        line = self.line_x(k)
        px = (p.x0 + p.x1) / 2
        if (px - line) * forward > 0 or (bx - line) * forward < p.width / 2 + r:
            line = px                   # driving into the ball, or it's already past the usual spot:
                                        # meet it where the paddle now is
        contact_x = line + forward * (p.width / 2 + r)
        closing = -forward * vx + max(0.0, forward * p.vx)    # the ball's approach plus the paddle's own
        t_hit = (bx - contact_x) * forward / closing if closing > 0 else math.inf
        self.t_hit = t_hit
        if t_hit <= 0:
            # Level with the ball as it slips past: lunge so it catches the paddle's end, which
            # still sends it back
            return px, by

        raw = by + vy * t_hit
        y, bounces = reflect_in_range(raw, r, BASE_H - r)
        powerups = getattr(p.game, "powerups", None)
        if powerups and powerups.ball_gravity():
            y = falling(by, vy, t_hit, powerups.BALL_GRAVITY, r, BASE_H - r)
        elif bounces > k["foresight"]:
            y = clamp(raw, r, BASE_H - r)             # loses track: assumes it sticks to the wall
        y += self.noise * (k["misread"] * min(t_hit, 1.5) + k["wobble"])

        if self.aim is None and t_hit < 0.6:
            self.aim = self.choose_aim(contact_x, y, math.hypot(vx, vy), r, k)
        offset = self.aim or 0.0

        # A trickster lines up for the opposite angle and only switches at the last moment it safely can
        if k["disguise"] and offset and t_hit > self.reveal_time(offset, k):
            offset = -offset * 0.5
        return line, y - offset * p.height / 2 * 0.9

    def reveal_time(self, offset, k):
        """Seconds before contact the paddle needs to slide from its decoy angle to the real one."""
        p = self.paddle
        travel = abs(offset) * 1.5 * p.height / 2 * 0.9
        return 0.16 + k["reaction"] + travel / (p.speed * k["pace"] * 0.5)

    def recover(self, bx, by, r, k):
        """No middle wall, and the ball has got between the paddle and its own goal (after Chaos
        Switch + moved it, or it pushed too far up).  Get out of the ball's row first, so it isn't
        knocked in from behind, then race back to its usual line (or just past the ball, if that's
        nearer the goal) so it arrives with time to line up the save."""
        p = self.paddle
        forward = 1 if p.is_left else -1
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2
        safety = p.height / 2 + r + 24
        goal_side = bx - forward * (p.width / 2 + r + 90)
        line = self.line_x(k)
        x = min(line, goal_side) if forward > 0 else max(line, goal_side)
        y = py
        if abs(by - py) < safety:
            # still in the ball's row: slide out of it while closing in, but stay behind the ball
            room_above, room_below = by - p.height, BASE_H - p.height - by
            away = -1 if room_above > room_below else 1
            y = clamp(by + away * (safety + 10), p.height / 2, BASE_H - p.height / 2)
            trail = bx + forward * (p.width / 2 + r + 30)
            x = max(x, trail) if forward > 0 else min(x, trail)
        return clamp(x, p.width / 2, BASE_W - p.width / 2), y

    def pickup_target(self, k):
        """Between shots, a sharp AI nips over to a power-up it can reach and get back from in time."""
        p = self.paddle
        powerups = getattr(p.game, "powerups", None)
        if not powerups or not powerups.pickups or k["aim"] < 0.2:
            return None
        ball = p.game.ball
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2
        far = BASE_W if p.is_left else 0                  # the ball has to get there and back first
        bx = (ball.x0 + ball.x1) / 2
        back = (abs(far - bx) + abs(far - px)) / max(abs(ball.vx), 1)
        best, best_d = None, math.inf
        for item in powerups.pickups:
            if p.game.wall_up and (item["x"] < BASE_W / 2) != p.is_left:
                continue                                   # on the other side of the wall
            d = math.hypot(item["x"] - px, item["y"] - py)
            trip = 2 * d / max(1.0, p.speed * k["pace"])
            if trip < back * 0.6 * k["aim"] and d < best_d:
                best, best_d = item, d
        return (best["x"], best["y"]) if best else None

    def jump_now(self, target_y):
        """Under Gravity: leave the floor at the moment that brings the paddle up to meet the ball."""
        p = self.paddle
        powerups = p.game.powerups
        if p.y1 < BASE_H - 1 or not self.incoming:
            return False
        rise = (p.y0 + p.y1) / 2 - target_y
        if rise < p.height * 0.3:
            return False
        v, g = powerups.JUMP, powerups.PADDLE_GRAVITY
        disc = v * v - 2 * g * rise
        t = (v - math.sqrt(disc)) / g if disc > 0 else v / g
        return self.t_hit <= t + 0.04

    def ready(self, by, k):
        """Between shots: drift back towards the middle of its goal, keeping half an eye on the ball,
        or go and take a power-up."""
        p = self.paddle
        grab = self.pickup_target(k)
        if grab:
            return grab
        x = lerp(p.home_x, self.line_x(k), 0.4)
        y = lerp(BASE_H / 2, by, 0.3) + math.sin(self.clock * 1.6 + self.sway) * p.height * 0.06
        return x, y

    # ---------------- Move ----------------

    def decide(self, dt):
        """Desired (vx, vy) for the paddle this frame."""
        p = self.paddle
        ball = p.game.ball
        k = self.params()
        bx, by, vx, vy = self.perceive(ball, dt, k["reaction"])
        r = ball.diameter / 2
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2

        behind = bx < p.x0 - r - 10 if p.is_left else bx > p.x1 + r + 10
        incoming = self.towards_goal(vx)
        if incoming and not self.incoming:
            self.new_shot(k)
        self.incoming = incoming

        if behind and not p.game.wall_up:
            target = self.recover(bx, by, r, k)
        elif behind:
            # Too late to play it: step aside rather than knock it into its own goal
            safety = p.height * 0.6 + r + 12
            if abs(by - py) < safety:
                away = 1 if by < BASE_H / 2 else -1
                target = (px, clamp(by + away * safety, p.height / 2, BASE_H - p.height / 2))
            else:
                target = self.target
        elif incoming:
            target = self.meet(bx, by, vx, vy, r, k)
            # The paddle's speed goes into the return, so a lined-up shot is driven, not just blocked
            if self.t_hit < self.STRIKE_TIME and abs(target[1] - py) < p.height * 0.4:
                forward = 1 if p.is_left else -1
                target = (target[0] + forward * 260 * min(1.0, k["strike"]), target[1])
        else:
            target = self.ready(by, k)

        if self.hesitate > 0:
            self.hesitate -= dt
            target = self.target

        powerups = getattr(p.game, "powerups", None)
        self.jump = bool(powerups and powerups.gravity(p) and self.jump_now(target[1]))

        self.target = target
        return self.steer(target, k)

    def steer(self, target, k):
        p = self.paddle
        tx, ty = target
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2

        if p.game.wall_up:
            half = BASE_W / 2 - p.width / 2
            tx = min(tx, half) if p.is_left else max(tx, BASE_W - half)
        ty = clamp(ty, p.height / 2, BASE_H - p.height / 2)

        top = p.speed * k["pace"]
        ex, ey = tx - px, ty - py
        dvx = clamp(ex / self.EASE, -1, 1) * top if abs(ex) > 4 else 0
        dvy = clamp(ey / self.EASE, -1, 1) * top if abs(ey) > 3 else 0
        powerups = getattr(p.game, "powerups", None)
        if powerups and powerups.gravity(p):
            dvy = -p.speed if self.jump else 0           # under Gravity, Up is a jump
        return dvx, dvy
