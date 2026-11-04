"""Power-ups: talismans that drift onto the court during a match.

Whoever reaches one, with their paddle or with a ball they hit last, takes it.  Boons help the
one who took it, curses hinder their opponent, and Gravity is wild.  Everything here runs on
game time, so it follows the Game Pace setting.
"""
import math, random
from dataclasses import dataclass

from config import BASE_W, BASE_H
from game.physics import Physics
from helpers import clamp, reflect_in_range


@dataclass(frozen=True)
class Kind:
    key: str
    name: str
    glyph: str
    family: str          # "Boon", "Curse" or "Wild"
    seconds: float       # how long it lasts; 0 for a charge that waits to be used
    blurb: str           # one line, for the Power-Ups list
    about: str           # the full story, for its tooltip


KINDS = (
    Kind("teleport", "Safety Teleport", "遁", "Boon", 0,
         "One save: your paddle blinks in front of a ball about to slip past.",
         "A charge that waits until it's needed (you can hold two). When the ball is about to get past "
         "you into your goal, your paddle teleports right in front of it. Long rallies can earn both "
         "players one too: see Rally Teleports."),
    Kind("giant", "Giant Paddle", "巨", "Boon", 10,
         "Your paddle grows half as tall again for 10 seconds.",
         "Your paddle grows half as tall again for 10 seconds."),
    Kind("swift", "Swift Step", "疾", "Boon", 10,
         "Your paddle moves half as fast again for 10 seconds.",
         "Your paddle moves half as fast again for 10 seconds."),
    Kind("fire", "Spirit Fire", "火", "Boon", 0,
         "Your next hit is a blazing shot, 40% faster.",
         "Keeps until your next hit, which leaves your paddle as a blazing shot, 40% faster than it "
         "would have been, even past the usual top speed."),
    Kind("frost", "Frostbite", "冰", "Curse", 10,
         "Your next hit frosts the ball; whoever it reaches moves at half speed.",
         "Frost coats your paddle (it doesn't slow you). Your next hit passes it to the ball, which "
         "slows down, and whoever touches the frosted ball takes the frost and moves at half speed "
         "until its 10 seconds are up."),
    Kind("shrink", "Shrink Curse", "缩", "Curse", 10,
         "Your opponent's paddle shrinks by a third for 10 seconds.",
         "Your opponent's paddle shrinks by a third for 10 seconds."),
    Kind("hex", "Jiangshi Hex", "咒", "Curse", 6,
         "Your opponent's controls flip for 6 seconds.",
         "Your opponent's controls flip for 6 seconds: up is down and left is right. "
         "An AI catches on after a moment."),
    Kind("ghost", "Ghost Ball", "鬼", "Curse", 10,
         "For 10 seconds the ball fades from sight on its way to your opponent.",
         "For 10 seconds, whenever the ball is heading for your opponent it fades almost out of "
         "sight in the middle of the court."),
    Kind("gravity", "Gravity", "重", "Wild", 10,
         "Your paddle and the ball fall for 10 s; run along the floor, jump with Up.",
         "For 10 seconds gravity takes your paddle and the ball. Your paddle drops to the floor, "
         "runs along it with Left and Right, and jumps very high with Up; the ball arcs and bounces."),
    Kind("wall", "Open Court", "破", "Wild", 10,
         "The Middle Wall comes down for 10 seconds; both paddles can roam.",
         "For 10 seconds the Middle Wall is down and both paddles can cross the court. When it comes "
         "back, a paddle on the wrong side is sent home. Only turns up while the wall is up."),
    Kind("swap", "Soul Swap", "换", "Wild", 0,
         "Starts a Chaos Switch + countdown: the paddles swap places.",
         "Starts the Chaos Switch + warning, and two seconds later the paddles swap places; keys, scores "
         "and goals stay put. Only turns up while the Middle Wall is down."),
)
BY_KEY = {kind.key: kind for kind in KINDS}

FAMILY_COLOURS = {"Boon": (240, 176, 64), "Curse": (178, 96, 255), "Wild": (90, 220, 150)}


class PowerUps:
    RADIUS = 40          # how close a paddle or ball must come to take one
    LIFETIME = 14.0      # seconds a talisman waits on the court
    MOST = 2             # talismans on the court at once
    WAITS = ((14, 22), (8, 14), (4, 8))     # seconds between talismans: Rare, Normal, Frequent

    GIANT, SHRINK = 1.5, 0.65               # paddle height
    SWIFT, FROZEN = 1.5, 0.5                # paddle speed
    FROST_BALL = 0.7                        # a frosted ball's speed
    FIRE = 1.4                              # a Spirit Fire shot's speed
    BALL_GRAVITY = 1500                     # px/s^2
    PADDLE_GRAVITY = 2600
    JUMP = 1900                             # px/s; carries a paddle about 700 px up
    TELEPORT_WARNING = 0.12                 # seconds before the ball would be in
    TELEPORTS_HELD = 2                      # Safety Teleport charges a player can hold

    def __init__(self, game):
        self.game = game
        self.pickups = []        # {"kind", "x", "y", "age", "phase"}
        self.popups = []         # floating names: [text, x, y, age, colour]
        self.frost = None        # {"holder": a paddle or "ball", "owner": paddle, "left": seconds}
        self.ghost = None        # {"owner": paddle, "left": seconds}
        self.hex_age = {}        # paddle -> seconds since a hex took it (an AI adapts)
        self.wall_down = 0.0     # seconds Open Court keeps the Middle Wall down
        self.wait = self.next_wait()
        self.ball_restitution = game.ball.restitution
        for paddle in (game.p1, game.p2):
            paddle.effects = {}  # key -> seconds left
            paddle.charges = {}  # key -> uses left
        game.ball.blazing = False

    @property
    def settings(self):
        return self.game.settings

    def kinds(self):
        """The power-ups switched on in Settings."""
        s = self.settings
        if not s.powerups:
            return []
        return [kind for kind in KINDS if getattr(s, "pu_" + kind.key)]

    def next_wait(self):
        lo, hi = self.WAITS[self.settings.powerup_rate]
        return random.uniform(lo, hi)

    def opponent(self, paddle):
        game = self.game
        return game.p2 if paddle is game.p1 else game.p1

    # ---------------- Questions the paddles, ball, AI and renderer ask ----------------

    def has(self, paddle, key):
        return paddle.effects.get(key, 0) > 0

    def size_factor(self, paddle):
        factor = 1.0
        if self.has(paddle, "giant"):
            factor *= self.GIANT
        if self.has(paddle, "shrink"):
            factor *= self.SHRINK
        return factor

    def speed_factor(self, paddle):
        factor = 1.0
        if self.has(paddle, "swift"):
            factor *= self.SWIFT
        if self.frozen(paddle):
            factor *= self.FROZEN
        return factor

    def frosted(self, paddle):
        return self.frost is not None and self.frost["holder"] is paddle

    def frozen(self, paddle):
        """Caught the frost from the ball: slowed until it melts.  The one who took it isn't."""
        return self.frosted(paddle) and paddle is not self.frost["owner"]

    def ball_frosted(self):
        return self.frost is not None and self.frost["holder"] == "ball"

    def gravity(self, paddle):
        return self.has(paddle, "gravity")

    def wall_open(self):
        return self.wall_down > 0

    def spawnable(self, kind):
        """Open Court only while the wall is up; Soul Swap only while it's down."""
        game = self.game
        if kind.key == "wall":
            return game.wall_up
        if kind.key == "swap":
            return not game.wall_up and game.switch_warning is None
        return True

    def ball_gravity(self):
        return any(self.has(p, "gravity") for p in (self.game.p1, self.game.p2))

    def flipped(self, paddle):
        """Hexed controls.  An AI works the hex out after a moment, a sharper one sooner."""
        if not self.has(paddle, "hex"):
            return False
        if paddle.ai_enabled:
            skill = self.settings.ai_skill(paddle.score, self.opponent(paddle).score)
            return self.hex_age.get(paddle, 0.0) < 1.4 - 0.2 * skill
        return True

    def ball_alpha(self):
        """How visible the ball is: a Ghost Ball fades mid-court on its way to the owner's opponent."""
        if not self.ghost:
            return 1.0
        ball = self.game.ball
        away = 1 if self.ghost["owner"].is_left else -1          # towards the opponent's goal
        if ball.vx * away <= 0:
            return 1.0
        x = (ball.x0 + ball.x1) / 2 / BASE_W
        k = x if away > 0 else 1 - x                              # 0 at the owner's end, 1 at the far end
        if k < 0.3 or k > 0.82:
            return 1.0
        fade = min(1.0, (k - 0.3) / 0.12, (0.82 - k) / 0.1)
        return 1.0 - 0.9 * fade

    def hidden_from(self, paddle):
        return self.ghost is not None and self.ghost["owner"] is not paddle and self.ball_alpha() < 0.35

    # ---------------- Each frame of play ----------------

    def update(self, dt):
        game, ball = self.game, self.game.ball
        for paddle in (game.p1, game.p2):
            for key in list(paddle.effects):
                paddle.effects[key] -= dt
                if paddle.effects[key] <= 0:
                    del paddle.effects[key]
            if self.has(paddle, "hex"):
                self.hex_age[paddle] = self.hex_age.get(paddle, 0.0) + dt
            else:
                self.hex_age.pop(paddle, None)

        if self.frost:
            self.frost["left"] -= dt
            if self.frost["left"] <= 0:
                if self.ball_frosted():         # the ball thaws back to its own speed
                    ball.vx /= self.FROST_BALL
                    ball.vy /= self.FROST_BALL
                self.frost = None
        if self.ghost:
            self.ghost["left"] -= dt
            if self.ghost["left"] <= 0:
                self.ghost = None
        if self.wall_down > 0:
            self.wall_down -= dt
            if self.wall_down <= 0:
                self.wall_down = 0.0
                self.send_home()

        # Gravity pulls the ball down; its bounces keep their height so it doesn't die on the floor
        if self.ball_gravity():
            ball.vy = clamp(ball.vy + self.BALL_GRAVITY * dt, -2400, 2400)
            ball.restitution = 1.2
        else:
            ball.restitution = self.ball_restitution

        kinds = self.kinds()
        keys = {kind.key for kind in kinds}
        if kinds:
            self.wait -= dt
            if self.wait <= 0:
                self.wait = self.next_wait()
                choices = [kind for kind in kinds if self.spawnable(kind)]
                if choices and len(self.pickups) < self.MOST:
                    self.spawn(random.choice(choices).key)
        for item in self.pickups:
            item["age"] += dt
        self.pickups = [item for item in self.pickups if item["age"] < self.LIFETIME and item["kind"] in keys]

        for item in list(self.pickups):
            owner = self.reached(item)
            if owner:
                self.pickups.remove(item)
                self.collect(item, owner)

        self.check_teleports()

    def update_popups(self, dt):
        for popup in self.popups:
            popup[3] += dt
        self.popups = [p for p in self.popups if p[3] < 1.4]

    def spawn(self, key):
        game = self.game
        movers = (game.p1, game.p2, game.ball)
        for _ in range(40):
            x, y = random.uniform(300, BASE_W - 300), random.uniform(170, BASE_H - 150)
            clear = all(math.hypot(x - (o.x0 + o.x1) / 2, y - (o.y0 + o.y1) / 2) > 220 for o in movers)
            apart = all(math.hypot(x - item["x"], y - item["y"]) > 260 for item in self.pickups)
            if clear and apart:
                self.pickups.append({"kind": key, "x": x, "y": y, "age": 0.0, "phase": random.uniform(0, math.tau)})
                return

    def reached(self, item):
        """Who takes this talisman this frame, if anyone: a paddle over it, or the ball for whoever hit it last."""
        if item["age"] < 0.3:
            return None                          # still fading in
        game, x, y = self.game, item["x"], item["y"]
        for paddle in (game.p1, game.p2):
            nx, ny = clamp(x, paddle.x0, paddle.x1), clamp(y, paddle.y0, paddle.y1)
            if math.hypot(x - nx, y - ny) < self.RADIUS:
                return paddle
        ball = game.ball
        if ball.last_paddle is not None:
            bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
            if math.hypot(x - bx, y - by) < self.RADIUS + ball.diameter / 2:
                return ball.last_paddle
        return None

    def collect(self, item, owner):
        kind = BY_KEY[item["kind"]]
        rival = self.opponent(owner)
        key = kind.key
        if key == "teleport":
            owner.charges["teleport"] = min(self.TELEPORTS_HELD, owner.charges.get("teleport", 0) + 1)
        elif key == "fire":
            owner.charges["fire"] = 1
        elif key in ("giant", "swift", "gravity"):
            owner.effects[key] = kind.seconds
        elif key in ("shrink", "hex"):
            rival.effects[key] = kind.seconds
            self.hex_age.pop(rival, None)
        elif key == "frost":
            self.frost = {"holder": owner, "owner": owner, "left": kind.seconds}
        elif key == "ghost":
            self.ghost = {"owner": owner, "left": kind.seconds}
        elif key == "wall":
            self.wall_down = kind.seconds
        elif key == "swap":
            self.game.start_swap_warning()

        app = self.game.app
        app.fx.burst(item["x"], item["y"], 8, 44, "red" if owner.is_left else "blue", life=(.6, 1.0))
        app.fx.spark(item["x"], item["y"], 18, FAMILY_COLOURS[kind.family], speed=380, life=.6)
        app.sound_manager.play("countdown_go.wav")
        self.popups.append([kind.name, item["x"], item["y"], 0.0, FAMILY_COLOURS[kind.family]])

    # ---------------- Hooks from the ball and the match ----------------

    def on_hit(self, ball, paddle):
        """A paddle touched the ball (called after the paddle has shaped the return)."""
        frost = self.frost
        if frost:
            if frost["holder"] is paddle and paddle is frost["owner"]:
                frost["holder"] = "ball"                # the frost leaves on the ball, slowing it
                ball.vx *= self.FROST_BALL
                ball.vy *= self.FROST_BALL
            elif frost["holder"] == "ball" and paddle is not frost["owner"]:
                frost["holder"] = paddle                # caught it: this paddle is frozen till it melts

        ball.blazing = False
        if paddle.charges.pop("fire", 0):
            ball.vx *= self.FIRE
            ball.vy *= self.FIRE
            ball.blazing = True
            self.game.app.fx.spark((ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, 30,
                                   (255, 150, 60), speed=560, life=.7)

    def on_rally(self, hits):
        """Long rallies pay out: every so many hits (Rally Teleports), both players earn a Safety Teleport."""
        s = self.settings
        every = s.rally_reward_hits[s.rally_reward]
        if not (s.powerups and s.pu_teleport and every) or hits % every:
            return
        game = self.game
        for paddle in (game.p1, game.p2):
            paddle.charges["teleport"] = min(self.TELEPORTS_HELD, paddle.charges.get("teleport", 0) + 1)
        self.popups.append([f"{hits}-hit rally! +1 Safety Teleport each", BASE_W / 2, 340, 0.0,
                            FAMILY_COLOURS["Boon"]])
        game.app.sound_manager.play("countdown_go.wav")

    def send_home(self):
        """Open Court is over and the wall is back: a paddle left on the wrong side goes home."""
        game = self.game
        if not game.wall_up:
            return
        for paddle in (game.p1, game.p2):
            centre = (paddle.x0 + paddle.x1) / 2
            if (centre < BASE_W / 2) == paddle.is_left:
                continue
            x = BASE_W / 2 - paddle.width - 20 if paddle.is_left else BASE_W / 2 + 20
            game.app.fx.burst(centre, (paddle.y0 + paddle.y1) / 2, 8, 44, "red" if paddle.is_left else "blue",
                              life=(.5, .9))
            paddle.x0, paddle.x1 = x, x + paddle.width
            paddle.vx = 0.0
            paddle.ai.reset()

    def on_point(self):
        """A point ends whatever was riding on the ball, and clears the court."""
        self.pickups.clear()
        self.wait = self.next_wait()
        if self.ball_frosted():
            self.frost = None
        self.game.ball.blazing = False

    def swap_owners(self):
        """Chaos Switch: players take each other's paddles, and their power-ups go with them."""
        a, b = self.game.p1, self.game.p2
        a.effects, b.effects = b.effects, a.effects
        a.charges, b.charges = b.charges, a.charges
        swap = {a: b, b: a}
        if self.frost:
            self.frost["owner"] = swap[self.frost["owner"]]
            if self.frost["holder"] != "ball":
                self.frost["holder"] = swap[self.frost["holder"]]
        if self.ghost:
            self.ghost["owner"] = swap[self.ghost["owner"]]
        self.hex_age = {swap[p]: t for p, t in self.hex_age.items()}

    # ---------------- Safety Teleport ----------------

    def check_teleports(self):
        game, ball = self.game, self.game.ball
        for paddle in (game.p1, game.p2):
            if not paddle.charges.get("teleport"):
                continue
            toward = -1 if paddle.is_left else 1
            if ball.vx * toward <= 0:
                continue
            to_goal = ball.x0 if paddle.is_left else BASE_W - ball.x1
            if to_goal > abs(ball.vx) * self.TELEPORT_WARNING + 40 or self.covered(paddle, ball):
                continue
            self.teleport(paddle, ball)

    def covered(self, paddle, ball):
        """Would the paddle stop the ball from where it is now?"""
        r = ball.diameter / 2
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        front = paddle.x1 if paddle.is_left else paddle.x0
        gap = (bx - r - front) if paddle.is_left else (front - bx - r)
        if gap < -r:
            return False                       # the ball is already level with or past the paddle
        t = max(0.0, gap) / max(abs(ball.vx), 1)
        y, _ = reflect_in_range(by + ball.vy * t, r, BASE_H - r)
        return abs(y - (paddle.y0 + paddle.y1) / 2) < paddle.height / 2 + r * 0.6

    def teleport(self, paddle, ball):
        app = self.game.app
        old = ((paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2)
        if paddle.is_left:
            paddle.x1 = ball.x0 - 6
            paddle.x0 = paddle.x1 - paddle.width
        else:
            paddle.x0 = ball.x1 + 6
            paddle.x1 = paddle.x0 + paddle.width
        cy = (ball.y0 + ball.y1) / 2
        paddle.y0, paddle.y1 = cy - paddle.height / 2, cy + paddle.height / 2
        paddle.vx = paddle.vy = 0.0
        Physics.clamp_to_world(paddle)

        paddle.charges["teleport"] -= 1
        if not paddle.charges["teleport"]:
            del paddle.charges["teleport"]
        tint = "red" if paddle.is_left else "blue"
        for x, y in (old, ((paddle.x0 + paddle.x1) / 2, cy)):
            app.fx.burst(x, y, 10, 48, tint, life=(.5, .9))
        app.sound_manager.play("hmyoop!.wav")
        self.popups.append(["Safety Teleport!", (paddle.x0 + paddle.x1) / 2, paddle.y0 - 20, 0.0,
                            FAMILY_COLOURS["Boon"]])
