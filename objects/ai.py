"""How the computer plays a paddle.

Every frame the AI goes through the same steps a person does:

  perceive  the ball as it was a moment ago (its reaction time), and extrapolate
  predict   where it will cross the paddle's line; the guess starts rough and
            sharpens as the ball gets closer, and only a skilled AI can follow
            the ball through several wall bounces
  decide    where to meet it and which part of the paddle to hit it with, so the
            return goes where the opponent isn't
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
    "wobble":    (85,   55,   35,   15,   5),       # px of error that never goes away, however close the ball
    "foresight": (0,    1,    1,    2,    3),      # wall bounces it can follow in its head
    "pace":      (0.55, 0.70, 0.85, 0.95, 1.00),   # share of the paddle's top speed it uses
    "aim":       (0.00, 0.25, 0.50, 0.80, 1.00),   # how much it tries to place its returns
    "lapse":     (0.22, 0.12, 0.06, 0.02, 0.00),   # chance of a moment's hesitation on each shot
    "press":     (0.10, 0.25, 0.40, 0.55, 0.70),   # how far it steps in to meet the ball
    "strike":    (0.35, 0.50, 0.70, 0.85, 1.00),   # how hard it drives into the ball on contact
}

# What each style does to the numbers above.
STYLES = {
    "Balanced":  {},
    "Guardian":  {"press": 0.2, "aim": 0.6, "misread": 0.8, "wobble": 0.8, "lapse": 0.6, "strike": 0.7},
    "Striker":   {"press": 1.7, "aim": 1.2, "lapse": 1.3, "strike": 1.25},
    "Trickster": {"aim": 1.35, "feint": 1.0},
}

CONTACT_OFFSETS = (-0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75)


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
        self.feint = 0.0
        self.feint_dir = 0
        self.sway = random.uniform(0, math.tau)
        self.t_hit = math.inf
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

        k = {name: lerp(column[lo], column[hi], skill - lo) * style.get(name, 1.0)
             for name, column in SKILL.items()}
        k["foresight"] = round(k["foresight"])
        k["aim"] = min(1.0, k["aim"])
        k["feint"] = style.get("feint", 0.0)
        return k

    def opponent(self):
        game = self.paddle.game
        return game.p2 if self.paddle is game.p1 else game.p1

    # ---------------- Perceive ----------------

    def perceive(self, ball, dt, reaction):
        """The ball as the AI believes it is now: last seen `reaction` ago, then extrapolated."""
        self.clock += dt
        r = ball.diameter / 2
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
        if p.game.settings.middle_wall:
            limit = BASE_W / 2 - forward * (p.width / 2 + 8)
        else:
            limit = BASE_W / 2 + forward * BASE_W * 0.12     # no wall: a bold AI may cross halfway
        room = (limit - p.home_x) * forward
        return p.home_x + forward * room * clamp(k["press"] * 0.6, 0, 1)

    def new_shot(self, k):
        self.noise = random.gauss(0, 1)
        self.aim = None
        self.hesitate = random.uniform(0.12, 0.3) if random.random() < k["lapse"] else 0.0
        if k["feint"] and random.random() < 0.45:
            self.feint, self.feint_dir = random.uniform(0.15, 0.28), random.choice((-1, 1))

    def choose_aim(self, contact_x, contact_y, speed, r, k):
        """Which part of the paddle to hit with: -1 is the top edge, 1 the bottom."""
        reach = 0.3 + 0.45 * k["aim"]
        if random.random() > k["aim"]:
            return random.uniform(-0.2, 0.2)          # just get it back

        opponent = self.opponent()
        opp_x = (opponent.x0 + opponent.x1) / 2
        opp_y = (opponent.y0 + opponent.y1) / 2
        away = 1 if self.paddle.is_left else -1
        best, best_score = 0.0, -math.inf

        for offset in CONTACT_OFFSETS:
            if abs(offset) > reach:
                continue
            angle = offset * MAX_BOUNCE_ANGLE
            vx, vy = away * speed * math.cos(angle), speed * math.sin(angle)
            t = abs(opp_x - contact_x) / max(abs(vx), 1)
            arrive, _ = reflect_in_range(contact_y + vy * t, r, BASE_H - r)
            # how far the opponent must travel, against how far it can in the time
            score = abs(arrive - opp_y) - opponent.speed * t * 0.35
            if k["feint"]:
                score += abs(offset) * 120             # tricksters love an edge
            if score > best_score:
                best, best_score = offset, score
        return best

    def meet(self, bx, by, vx, vy, r, k):
        p = self.paddle
        line = self.line_x(k)
        back = -1 if p.is_left else 1
        contact_x = line - back * (p.width / 2 + r)
        t_hit = (contact_x - bx) / vx if vx else math.inf
        self.t_hit = t_hit
        if t_hit <= 0:
            return self.target

        raw = by + vy * t_hit
        y, bounces = reflect_in_range(raw, r, BASE_H - r)
        if bounces > k["foresight"]:
            y = clamp(raw, r, BASE_H - r)             # loses track: assumes it sticks to the wall
        y += self.noise * (k["misread"] * min(t_hit, 1.5) + k["wobble"])

        if self.aim is None and t_hit < 0.6:
            self.aim = self.choose_aim(contact_x, y, math.hypot(vx, vy), r, k)
        offset = self.aim or 0.0
        return line, y - offset * p.height / 2 * 0.9

    def ready(self, by, k):
        """Between shots: drift back towards the middle of its goal, keeping half an eye on the ball."""
        p = self.paddle
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

        if behind:
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
        elif self.feint > 0:
            self.feint -= dt
            target = (target[0], py + self.feint_dir * p.height)

        self.target = target
        return self.steer(target, k)

    def steer(self, target, k):
        p = self.paddle
        tx, ty = target
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2

        if p.game.settings.middle_wall:
            half = BASE_W / 2 - p.width / 2
            tx = min(tx, half) if p.is_left else max(tx, BASE_W - half)
        ty = clamp(ty, p.height / 2, BASE_H - p.height / 2)

        top = p.speed * k["pace"]
        ex, ey = tx - px, ty - py
        dvx = clamp(ex / self.EASE, -1, 1) * top if abs(ex) > 4 else 0
        dvy = clamp(ey / self.EASE, -1, 1) * top if abs(ey) > 3 else 0
        return dvx, dvy
