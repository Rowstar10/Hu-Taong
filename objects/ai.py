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
# Balanced (2026-11-09, second pass) against a human-like player in simulated matches: a decent
# attacking player wins about 92%, 85%, 63%, 40% and 20% of points against Balanced, and the AI's
# returns are never quicker than Rowan's original AI's at the same level (its strike is capped, so
# a person can keep up).  The other styles land at about 88/72/41/17/8 (Guardian), 86/81/69/25/10
# (Striker, whose returns are much quicker) and 90/78/58/38/16 (Trickster).
SKILL = {
    "reaction":  (0.28, 0.23, 0.15, 0.115, 0.075),   # seconds behind what is really happening
    "misread":   (270, 205, 120, 82, 42),            # px of guessing error per second the ball is still away
    "wobble":    (80, 68, 52, 47, 40),               # px of error that never goes away, however close the ball
    "foresight": (0, 1, 1, 1, 2),                    # wall bounces it can follow in its head
    "pace":      (0.55, 0.64, 0.78, 0.87, 0.95),     # share of the paddle's top speed it uses
    "aim":       (0.00, 0.15, 0.38, 0.56, 0.80),     # how much it tries to place its returns
    "lapse":     (0.19, 0.13, 0.06, 0.04, 0.015),    # chance of a moment's hesitation on each shot
    "press":     (0.10, 0.19, 0.33, 0.43, 0.55),     # how far it steps in to meet the ball
    "strike":    (0.25, 0.30, 0.40, 0.45, 0.52),     # share of its top speed it drives into the ball with
    "chase":     (0.00, 0.12, 0.30, 0.45, 0.65),     # chance it chases a ball that has got past, not give up
}

# What each style does to the numbers above (one factor, or one per difficulty), plus habits of its own:
#   bank      how much it likes returns that bounce off the walls on the way
#   nerve     how close to the paddle's edge it dares meet the ball (1 = sensible)
#   disguise  it lines up as if to aim one way and switches at the last moment
#   guard     between shots it keeps to the middle of its goal, ready for anything (0-1)
#   charge    with the Middle Wall down it storms past halfway and hits harder still (0-1)
#   mix       chance each shot is a change of pace: a soft drop (often after a fake lunge) or a drive
#   juke      how much it feints about between shots, to be hard to read (0-1)
# Each leans into one thing: the Guardian defends (it reads the ball best and rarely lapses, but
# isn't any quicker), the Striker attacks (it steps in and drives through the ball, leaving gaps
# behind it), and the Trickster deceives (disguised angles, bank shots, changes of pace, feints).
STYLES = {
    "Balanced":  {"bank": 0.3},
    "Guardian":  {"press": 0.15, "aim": 0.5, "strike": 0.8, "misread": (0.6, 0.6, 0.7, 0.8, 0.85),
                  "wobble": (0.7, 0.7, 0.78, 0.82, 0.9), "lapse": 0.4, "chase": 1.6, "foresight": (1, 1, 1, 1, 1.5),
                  "bank": 0.2, "nerve": 0.6, "guard": 1.0},
    "Striker":   {"press": 2.0, "aim": 1.35, "lapse": 1.2, "strike": 1.9, "wobble": (1, 1, 1, 1, 0.9),
                  "bank": 0.2, "nerve": 1.15, "charge": 1.0},
    "Trickster": {"aim": 1.8, "misread": (0.6, 0.6, 0.6, 0.55, 0.5), "wobble": (0.9, 0.82, 0.76, 0.66, 0.62), "lapse": 0.4,
                  "press": 1.3, "bank": 1.8, "nerve": 1.2, "disguise": 1.0, "mix": 0.75, "juke": 1.0,
                  "wrongfoot": 1.0},
}
HABITS = {"bank": 0.0, "nerve": 1.0, "disguise": 0.0, "guard": 0.0, "charge": 0.0, "mix": 0.0, "juke": 0.0,
          "wrongfoot": 0.0}
#   wrongfoot  aims where the opponent is moving away from, not just where it is
# A trickster's plan for each shot (picked when the ball comes at it, `mix` of the time):
#   pounce  tap it back softly, then sprint after its own slow ball and hit it again near halfway,
#           off the paddle's edge: it suddenly speeds up and changes angle
#   drop    lunge as if to drive, then let it die short
#   rush    charge forward to take the ball early, near halfway, cutting the opponent's time
#   drive   a full-blooded drive
TRICKS = (("pounce", 0.45), ("drop", 0.1), ("rush", 0.3), ("drive", 0.15))

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
    POUNCE_FASTEST = 2000   # px/s: a trickster only tries a pounce on a ball slower than this

    def __init__(self, paddle):
        self.paddle = paddle
        self.reset()

    def reset(self):
        """Forget everything; used when the AI takes over a paddle."""
        self.seen = deque()
        self.memories = {}          # Twin Balls: what it has seen of each ball
        self.clock = 0.0
        self.incoming = False
        self.noise = 0.0
        self.aim = None
        self.hesitate = 0.0
        self.sway = random.uniform(0, math.tau)
        self.t_hit = math.inf
        self.jump = False
        self.chase = False
        self.pickup = None          # the power-up it has decided to go for
        self.pickup_cooldown = 0.0
        self.heading = None         # direction of the ball last frame, to notice a sudden change
        self.power, self.fake = 1.0, False      # this shot's change of pace (a trickster's), and its fake lunge
        self.plan, self.pounce = None, None     # a trickster's trick for this shot; a pounce under way
        self.juke_next, self.juke_off = 0.0, (0.0, 0.0)   # a trickster's feints between shots
        self.target =(self.paddle.home_x, self.paddle.home_y)

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

        # Power-ups that throw it, as they would a person
        powerups = getattr(game, "powerups", None)
        if powerups:
            ghost = powerups.ghost
            if ghost and self.towards_goal(game.ball.vx):
                # a Ghost Ball coming its way is harder to judge
                k["misread"] *= 1.5
                k["wobble"] += 30
                k["reaction"] += 0.04
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
            # a Ghost Ball out of sight leaves the AI working from where it last saw it; a ball
            # stuck to a paddle is read as leaving the way it will once it peels off
            vx, vy = (ball.stuck["vx"], ball.stuck["vy"]) if getattr(ball, "stuck", None) else (ball.vx, ball.vy)
            self.seen.append((self.clock, (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, vx, vy))
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
            # No wall: a bold AI may cross halfway, but not so far it has no time to see the ball
            # coming; a charging Striker storms on much further
            limit = BASE_W / 2 + forward * BASE_W * (0.12 + 0.13 * k["charge"])
            most = 0.6 + 0.35 * k["charge"]
        room = (limit - p.home_x) * forward
        x = p.home_x + forward * room * clamp(k["press"] * 0.6, 0, most)
        powerups = getattr(p.game, "powerups", None)
        if powerups and powerups.snowball():
            # Stand well out from its goal, so a shove from the snowball can't carry it in
            hold = min(room, 140 + 110 * powerups.ball_size_factor())
            x = max(x, p.home_x + hold) if forward > 0 else min(x, p.home_x - hold)
        return x

    def new_shot(self, k, speed=0.0):
        self.noise = random.gauss(0, 1)
        self.aim = None
        self.hesitate = random.uniform(0.12, 0.3) if random.random() < k["lapse"] else 0.0
        self.chase = random.random() < k["chase"]
        # A trickster picks a trick for this shot (see TRICKS)
        self.power, self.fake, self.plan, self.pounce = 1.0, False, None, None
        if random.random() < k["mix"]:
            roll = random.random()
            for plan, share in TRICKS:
                roll -= share
                if roll <= 0:
                    break
            if plan == "pounce" and speed > self.POUNCE_FASTEST:
                plan = None                 # too quick to tap softly and chase down: just disguise it
            self.plan = plan
            if plan in ("pounce", "drop"):
                self.power = 0.15
                self.fake = plan == "drop"
            elif plan in ("rush", "drive"):
                self.power = 1.6

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
            if k["disguise"]:
                return random.uniform(-reach, reach)       # a trickster never plays it straight
            return clamp(random.uniform(-0.2, 0.2), -reach, reach)     # just get it back

        opponent = self.opponent()
        opp_x = (opponent.x0 + opponent.x1) / 2
        opp_y = (opponent.y0 + opponent.y1) / 2
        # a trickster aims where they're heading away from: behind them, so they're wrong-footed
        opp_y += opponent.vy * 0.4 * k["wrongfoot"]
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
        if self.plan == "rush":
            # a trickster's rush: charge right up to take the ball early, near halfway
            rush = BASE_W / 2 - forward * (p.width / 2 + 30) if p.game.wall_up else BASE_W / 2 + forward * BASE_W * 0.1
            px = (p.x0 + p.x1) / 2
            ball_time = (bx - (rush + forward * (p.width / 2 + r))) * forward / max(1.0, -forward * vx)
            run_time = abs(rush - px) / max(1.0, p.speed * k["pace"]) + k["reaction"] + 0.12
            if (rush - line) * forward > 0 and run_time < ball_time:
                line = rush                 # (only if it can get there before the ball)
            else:
                self.plan = None
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
        field = powerups.ball_accel() if powerups else 0.0
        if field:
            # Gravity or the wind bends its path: it reads the arc by eye, like a player, and a
            # sharper AI judges the bend a little better
            judged = field * (0.8 + 0.2 * min(1.0, k["foresight"] / 2)) * (1 + 0.06 * self.noise)
            if powerups.gravity(p):
                # On the floor itself: pick where along its half to meet the ball, low in its arc
                # where it can, and only as high as it can jump there in time
                line, t_hit, y = self.gravity_contact(bx, by, vx, vy, r, k, judged, line)
                contact_x = line + forward * (p.width / 2 + r)
                self.t_hit = t_hit
            else:
                y = falling(by, vy, t_hit, judged, r, BASE_H - r)
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
        line = self.line_x(k)
        x, y = self.cut_off(bx, by, r, k, line)
        if x is None:
            goal_side = bx - forward * (p.width / 2 + r + 90)
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

    def cut_off(self, bx, by, r, k, line):
        """Circle round the ball: the first spot between it and the goal that the paddle can reach
        (going round, not through it) with a moment to spare, and where the ball will be there."""
        p = self.paddle
        forward = 1 if p.is_left else -1
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2
        vx, vy = self.seen[-1][3], self.seen[-1][4]
        if not self.towards_goal(vx):
            return None, None
        top = max(1.0, p.speed * k["pace"])
        detour = p.height / 2 + r + 24            # the sidestep needed to get round the ball
        for step in range(1, 14):
            x = bx - forward * step * 70
            if (x - p.width / 2 if forward > 0 else BASE_W - x - p.width / 2) < 0:
                break
            t_ball = abs(bx - x) / abs(vx)
            y, _ = reflect_in_range(by + vy * t_ball, r, BASE_H - r)
            run = math.hypot(x - px, detour) + abs(y - py)
            if run / top + 0.15 + k["reaction"] < t_ball:
                return x, y
        return None, None

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

    def committed_pickup(self, k):
        """Make up its mind about a power-up and stick to it: once it sets off it keeps going
        until it has it, the talisman is gone, or the ball is truly coming back too soon.
        After giving one up it leaves power-ups alone for a moment, so it never dithers."""
        p = self.paddle
        powerups = getattr(p.game, "powerups", None)
        if self.pickup_cooldown > 0:
            return None
        item = self.pickup
        if item is not None:
            if not powerups or item not in powerups.pickups:
                self.pickup = None                      # taken, or faded away
            else:
                ball = p.game.ball
                px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2
                far = BASE_W if p.is_left else 0
                back = (abs(far - (ball.x0 + ball.x1) / 2) + abs(far - px)) / max(abs(ball.vx), 1)
                trip = 2 * math.hypot(item["x"] - px, item["y"] - py) / max(1.0, p.speed * k["pace"])
                if trip > back:                         # can't make it back: drop it for good
                    self.pickup, self.pickup_cooldown = None, 1.0
                    return None
                return item["x"], item["y"]
        target = self.pickup_target(k)
        if target is None:
            return None
        self.pickup = next(i for i in powerups.pickups if (i["x"], i["y"]) == target)
        return target

    def opponent_threat(self, bx, by, r):
        """0 to 1: how likely the other paddle is to touch the ball again before it gets here
        (close to it and moving towards it).  Only matters with the wall down, where it can chase."""
        opp = self.opponent()
        nx, ny = clamp(bx, opp.x0, opp.x1), clamp(by, opp.y0, opp.y1)
        dx, dy = bx - nx, by - ny
        gap = math.hypot(dx, dy) - r
        if gap > 260:
            return 0.0
        closing = (opp.vx * dx + opp.vy * dy) / max(1.0, math.hypot(dx, dy))
        if closing <= 50:
            return 0.0
        return clamp(1 - gap / 260, 0, 1) * clamp(closing / 600, 0, 1)

    # ---------------- Gravity ----------------

    def rise_time(self, rise):
        """Seconds a jump with Up held takes to lift the paddle `rise` px."""
        pw = self.paddle.game.powerups
        v, held_g = pw.JUMP, pw.PADDLE_GRAVITY * pw.HOLD_GRAVITY
        hold_h = v * pw.JUMP_HOLD - 0.5 * held_g * pw.JUMP_HOLD ** 2
        if rise <= hold_h:
            return (v - math.sqrt(max(0.0, v * v - 2 * held_g * rise))) / held_g
        v2, g = v - held_g * pw.JUMP_HOLD, pw.PADDLE_GRAVITY
        disc = v2 * v2 - 2 * g * (rise - hold_h)
        return pw.JUMP_HOLD + ((v2 - math.sqrt(disc)) / g if disc > 0 else v2 / g)

    def gravity_contact(self, bx, by, vx, vy, r, k, judged, line):
        """Under Gravity: where along its half to meet the falling ball.  It weighs each spot by
        how high it would have to jump there, and keeps to spots it can reach (run and jump) in time.
        Answers (line x, seconds till contact, the ball's height there)."""
        p = self.paddle
        forward = 1 if p.is_left else -1
        px = (p.x0 + p.x1) / 2
        floor_y = BASE_H - p.height / 2
        top = max(1.0, p.speed * k["pace"])
        far = BASE_W / 2 - forward * (p.width / 2 + 8) if p.game.wall_up else BASE_W / 2 + forward * BASE_W * 0.12
        best = None
        x = p.home_x
        while (far - x) * forward >= 0:
            contact = x + forward * (p.width / 2 + r)
            t = (bx - contact) * forward / max(1.0, -forward * vx)
            if t > 0.05:
                y = falling(by, vy, t, judged, r, BASE_H - r)
                need = floor_y - y                          # how high it must jump to meet it there
                jump = self.rise_time(need) if need > p.height * 0.3 else 0.0
                run = abs(x - px) / top
                if max(run, jump) + k["reaction"] + 0.08 < t:
                    score = max(0.0, need) + 0.25 * abs(x - line)
                    if best is None or score < best[0]:
                        best = (score, x, t, y)
            x += forward * 50
        if best is None:                                   # nowhere it can get to in time: do its best
            contact = line + forward * (p.width / 2 + r)
            t = max(0.0, (bx - contact) * forward / max(1.0, -forward * vx))
            return line, t, falling(by, vy, t, judged, r, BASE_H - r)
        return best[1], best[2], best[3]

    def jump_now(self, target_y):
        """Under Gravity, whether to hold Up this frame: take off just in time to rise to the ball,
        and keep holding only while it still has to climb (letting go early stops the climb)."""
        p = self.paddle
        powerups = p.game.powerups
        cy = (p.y0 + p.y1) / 2
        if p.y1 >= BASE_H - 1:
            if not self.incoming:
                return False
            rise = cy - target_y
            if rise < p.height * 0.3:
                return False
            return self.t_hit <= self.rise_time(rise) + 0.04
        coast = powerups.JUMP_CUT ** 2 / (2 * powerups.PADDLE_GRAVITY)    # it rises this much more after letting go
        return getattr(p, "jump_held", None) is not None and p.vy < 0 and cy - coast > target_y

    def pounce_target(self, ball, bx, by, vx, vy, r):
        """A trickster's pounce: having tapped the ball back softly, it sprints after it and hits it
        again before halfway, off the paddle's edge, so it suddenly speeds up and swings away from
        where the opponent was heading.  Answers where to run, or None (no pounce, or it's over)."""
        if self.plan != "pounce":
            return None
        p = self.paddle
        forward = 1 if p.is_left else -1
        if ball.last_paddle is not p:
            return None                            # its soft tap hasn't happened yet
        speed = math.hypot(vx, vy)
        if self.pounce is None:
            opp = self.opponent()
            # off the edge that sends it away from the opponent's half of the court
            edge = 0.6 if (opp.y0 + opp.y1) / 2 < BASE_H / 2 else -0.6
            self.pounce = {"start": self.clock, "edge": edge, "speed": speed}
        pounce = self.pounce
        limit = BASE_W / 2 - forward * (p.width / 2 + 8) if p.game.wall_up else BASE_W / 2 + forward * BASE_W * 0.2
        if (self.clock - pounce["start"] > 1.6 or speed > pounce["speed"] + 300   # timed out, or hit it again
                or (bx - limit) * forward > -r or forward * vx <= 0):                # too late, or it's coming back
            self.plan = None
            return None
        ahead = 0.1
        fx = bx + vx * ahead
        fy, _ = reflect_in_range(by + vy * ahead, r, BASE_H - r)
        return fx - forward * (p.width / 2 + r) + forward * 140, fy - pounce["edge"] * p.height / 2 * 0.9

    def ready(self, by, k):
        """Between shots: drift back towards the middle of its goal, keeping half an eye on the ball,
        or go and take a power-up."""
        p = self.paddle
        grab = self.committed_pickup(k)
        if grab:
            return grab
        powerups = getattr(p.game, "powerups", None)
        # A guardian settles right back onto its line, square in the middle of its goal
        # (a trickster stays up near its line too, ready to rush or pounce)
        out = 1.0 if powerups and powerups.snowball() else min(1.0, 0.4 + 0.6 * k["guard"] + 0.4 * k["juke"])
        x = lerp(p.home_x, self.line_x(k), out)
        y = lerp(BASE_H / 2, by, 0.3 - 0.15 * k["guard"]) + math.sin(self.clock * 1.6 + self.sway) * p.height * 0.06
        if k["juke"]:
            # A trickster won't keep still: it darts about (forwards and sideways, never back
            # towards its goal), so you can't tell where it will be
            if self.clock >= self.juke_next:
                self.juke_next = self.clock + random.uniform(0.3, 0.7)
                self.juke_off = (random.uniform(0, 90) * k["juke"], random.uniform(-0.4, 0.4) * p.height * k["juke"])
            x += self.juke_off[0] * (1 if p.is_left else -1)
            y += self.juke_off[1]
        return x, y

    # ---------------- Move ----------------

    def pick_ball(self):
        """Which ball to play.  Normally there's one; under Twin Balls it guards against the ball
        that can score in its goal (the other colour's) first, and plays its own-colour ball (which
        can only score at the other end) when that arrives clearly sooner or nothing threatens."""
        p = self.paddle
        powerups = getattr(p.game, "powerups", None)
        balls = powerups.balls() if powerups else [p.game.ball]
        if len(balls) == 1:
            ball = balls[0]
        else:
            mine = "red" if p.is_left else "blue"
            threat = next((b for b in balls if b.side and b.side != mine), balls[0])
            own = next((b for b in balls if b.side == mine), balls[0])

            def arrives(b):
                toward = b.vx < 0 if p.is_left else b.vx > 0
                if not toward:
                    return math.inf
                gap = (b.x0 - p.x1) if p.is_left else (p.x0 - b.x1)
                return max(0.0, gap) / max(1.0, abs(b.vx))
            t_threat, t_own = arrives(threat), arrives(own)
            ball = threat if t_threat < math.inf and not t_own < t_threat - 0.6 else own if t_own < math.inf else threat
        # a separate memory of each ball's path (forgetting balls that have gone)
        live = {id(b) for b in balls}
        for key in [key for key in self.memories if key not in live]:
            del self.memories[key]
        self.seen = self.memories.setdefault(id(ball), self.seen if len(balls) == 1 else deque())
        return ball

    def decide(self, dt):
        """Desired (vx, vy) for the paddle this frame."""
        p = self.paddle
        ball = self.pick_ball()
        k = self.params()
        bx, by, vx, vy = self.perceive(ball, dt, k["reaction"])
        r = ball.diameter / 2
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2

        behind = bx < p.x0 - r - 10 if p.is_left else bx > p.x1 + r + 10
        incoming = self.towards_goal(vx)
        if incoming and not self.incoming:
            self.new_shot(k, math.hypot(vx, vy))
            self.pickup = None                      # the ball comes first; it re-decides later
        self.incoming = incoming
        self.pickup_cooldown = max(0.0, self.pickup_cooldown - dt)

        # A sudden change of the ball's course (a late flick from the other paddle) is a new shot to
        # read, not the old one: drop the aim and any drive it had committed to
        # (a fresh paddle touch, not a wall bounce, which only softens the ball)
        touches = ball.rally_value
        if self.heading is not None and incoming and touches != self.heading:
            self.aim = None
        self.heading = touches

        drive = None
        stuck = getattr(ball, "stuck", None)
        if stuck and stuck["paddle"] is p:
            # Sticky Goo: it's holding the ball, so it sweeps the paddle to sling it away from the
            # opponent (down if they're high, up if they're low; the other way if it's out of room)
            opp = self.opponent()
            way = 1 if (opp.y0 + opp.y1) / 2 < BASE_H / 2 else -1
            if (way > 0 and p.y1 > BASE_H - 80) or (way < 0 and p.y0 < 80):
                way = -way
            self.target = (px, py + way * 400)
            return self.steer(self.target, k)
        if behind and (self.chase or not p.game.wall_up):
            # The ball got past: keep clear of it so it isn't knocked in, and race back goal-side
            # of it (a touch on the paddle's end still sends it back).  With the wall down every AI
            # does this, as Chaos Switch + can drop it anywhere.
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
            # If the other paddle is still closing on the ball it may yet change its course: don't
            # bet everything on the line it's on, hold a little towards the middle of the reachable court
            threat = self.opponent_threat(bx, by, r)
            if threat > 0:
                target = (target[0], lerp(target[1], lerp(BASE_H / 2, by, 0.5), 0.45 * threat))
            # The paddle's speed goes into the return, so a lined-up shot is driven, not just blocked.
            # A charging Striker (wall down) winds up sooner and hits harder; a Trickster's drop shot
            # gives with the ball instead, often after lunging as if to drive it.
            forward = 1 if p.is_left else -1
            charging = 0.0 if p.game.wall_up else k["charge"]
            strike_time = self.STRIKE_TIME * (1 + 0.5 * charging)
            lined_up = threat < 0.2 and abs(target[1] - py) < p.height * 0.4
            if lined_up and self.fake and strike_time < self.t_hit < strike_time + 0.35:
                target = (target[0] + forward * 260, target[1])          # the fake lunge
            elif lined_up and self.t_hit < strike_time:
                target = (target[0] + forward * (260 if self.power >= 0.5 else -40), target[1])
            # Close to contact it never comes forward faster than its strike allows, so its returns
            # keep a pace a person can answer (the player's own swing isn't limited like this).
            # Against another AI it hits out freely, or two careful AIs would rally for ever.
            if self.t_hit < strike_time + 0.15 and (self.power != 1.0 or not self.opponent().ai_enabled):
                drive = min(1.0, k["strike"] * self.power * (1 + 0.35 * charging))
        else:
            target = self.ready(by, k)
            pounce = self.pounce_target(ball, bx, by, vx, vy, r)
            if pounce:
                target, drive = pounce, 1.0

        if self.hesitate > 0:
            self.hesitate -= dt
            target = self.target

        powerups = getattr(p.game, "powerups", None)
        self.jump = bool(powerups and powerups.gravity(p) and self.jump_now(target[1]))

        self.target = target
        return self.steer(target, k, drive)

    def steer(self, target, k, drive=None):
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
        if drive is not None:
            forward = 1 if p.is_left else -1
            if dvx * forward > 0:
                dvx = forward * min(abs(dvx), top * drive)
        dvy = clamp(ey / self.EASE, -1, 1) * top if abs(ey) > 3 else 0
        powerups = getattr(p.game, "powerups", None)
        if powerups and powerups.gravity(p):
            dvy = -p.speed if self.jump else 0           # under Gravity, Up is a jump
        return dvx, dvy
