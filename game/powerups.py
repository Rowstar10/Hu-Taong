"""Power-ups: talismans that drift onto the court during a match.

Whoever reaches one, with their paddle or with a ball they hit last, takes it.  Boons help the
one who took it, curses hinder their opponent, and the wild ones shake up the court for everyone.
Everything here runs on game time, so it follows the Game Pace setting.
"""
import math, random
from dataclasses import dataclass

from config import BASE_W, BASE_H, MAX_BOUNCE_ANGLE, MAX_BALL_SPEEDUP
from game.physics import Physics
from helpers import clamp, reflect_in_range


@dataclass(frozen=True)
class Kind:
    key: str
    name: str
    glyph: str
    family: str          # "Boon", "Curse" or "Wild"
    seconds: float       # how long it lasts; 0 for a charge that waits to be used, or for one
                         # that lasts until the point ends (shown with UNTIL_POINT seconds left)
    blurb: str           # one line, for the Power-Ups list
    about: str           # the tooltip: a short line on what it does, then the details


UNTIL_POINT = math.inf   # "seconds left" of something that lasts until the point ends

KINDS = (
    Kind("teleport", "Safety Teleport", "遁", "Boon", 0,
         "One save this point: your paddle blinks in front of a ball about to slip past.",
         "Saves you once.\n"
         "When the ball is about to get past you, your paddle teleports in front of it.\n"
         "• Waits until it's needed\n"
         "• An unused save is lost when the point ends\n"
         "• You can hold one at a time"),
    Kind("giant", "Giant Paddle", "巨", "Boon", 10,
         "Your paddle grows half as tall again for 10 seconds.",
         "Your paddle grows half as tall again.\n"
         "• Lasts 10 s"),
    Kind("swift", "Swift Step", "疾", "Boon", 10,
         "Your paddle moves half as fast again for 10 seconds.",
         "Your paddle moves half as fast again.\n"
         "• It doesn't make your hits any harder\n"
         "• Lasts 10 s"),
    Kind("fire", "Spirit Fire", "火", "Boon", 10,
         "For 10 seconds every hit you make is a blazing shot, 40% faster.",
         "Every hit you make leaves as a blazing shot.\n"
         "• 40% faster, even a little past the usual top speed\n"
         "• Blazing shots chip stones: tombstones break in 2 hits, ferry gates in 3, walls in 4\n"
         "• Lasts 10 s"),
    Kind("frost", "Frostbite", "冰", "Curse", 10,
         "Your next hit frosts the ball; whoever hits it back is frozen at half speed for 5 seconds.",
         "Your next hit frosts the ball. Whoever hits it back is frozen: half speed for 5 s.\n"
         "• The frost never comes back to you\n"
         "• Unused, it wears off 10 s after it was taken"),
    Kind("shrink", "Shrink Curse", "缩", "Curse", 10,
         "Your opponent's paddle shrinks by a third for 10 seconds.",
         "Your opponent's paddle shrinks by a third.\n"
         "• Lasts 10 s"),
    Kind("ghost", "Ghost Ball", "鬼", "Wild", 10,
         "For 10 seconds the ball keeps vanishing and reappearing, at random.",
         "The ball turns into a ghost: it fades out of sight and back again at random moments.\n"
         "• Out of sight for a moment at a time, but always in sight as it nears a paddle\n"
         "• It drifts straight through tombstones and pillars\n"
         "• An AI misjudges it a little as it comes in\n"
         "• Lasts 10 s"),
    Kind("sticky", "Sticky Goo", "粘", "Wild", 10,
         "Both paddles are coated in goo: catch the ball, then sling it where you like.",
         "Both paddles are coated in sticky goo: the ball sticks for a moment, then you sling it.\n"
         "• The way your paddle is moving as it peels off aims it (up slings it up)\n"
         "• A quick flick of the paddle throws it faster\n"
         "• An arrow on the ball shows where it will go\n"
         "• Lasts 10 s"),
    Kind("gravity", "Gravity", "重", "Wild", 10,
         "Both paddles and the ball fall for 10 s; run along the floor, jump with Up.",
         "Gravity takes both paddles and the ball.\n"
         "• The paddles drop to the floor: run with Left and Right, jump with Up\n"
         "• The ball arcs and bounces\n"
         "• Lasts 10 s"),
    Kind("wall", "Open Court", "破", "Wild", 0,
         "The Middle Wall comes down until the point ends; both paddles can roam.",
         "The Middle Wall comes down and both paddles can cross the court.\n"
         "• Lasts until the point ends\n"
         "• Only turns up while the wall is up"),
    Kind("swap", "Soul Swap", "换", "Wild", 0,
         "Chaos Switch + until the point ends: the wall comes down and the paddles keep swapping places.",
         "Chaos Switch + is on until the point ends.\n"
         "• The Middle Wall comes down\n"
         "• Every so often, after a warning, the paddles swap places and every ball slows to half speed\n"
         "• Keys, scores and goals stay put\n"
         "• Doesn't turn up if Chaos Switch + is already on"),
    Kind("blink", "Blink Ball", "闪", "Wild", 10,
         "For 10 seconds the ball blinks to a nearby spot every so often, swerving a little each time.",
         "The ball blinks to a random spot close by, every 0.1 to 0.5 seconds.\n"
         "• Each blink turns it a little off its course\n"
         "• Never through a paddle or a stone\n"
         "• Never close to a paddle it's heading for\n"
         "• Lasts 10 s"),
    Kind("tomb", "Tombstone", "碑", "Wild", 0,
         "A tombstone rises on the court until the point ends; up to two at once.",
         "A tombstone rises somewhere on the court and the ball bounces off it.\n"
         "• Some stand still, some drift up and down\n"
         "• Paddles pass through it\n"
         "• Lasts until the point ends; up to two can stand at once"),
    Kind("snowball", "Snowball", "雪", "Wild", 0,
         "The ball becomes a heavy snowball that grows as it rolls and shoves paddles back.",
         "The ball turns into a heavy snowball until the point ends.\n"
         "• It grows as it travels, and gets heavier as it grows\n"
         "• Every hit shoves the paddle back towards its own goal, even one driving into it\n"
         "• Meet it well out from your goal, so there's room to be shoved\n"
         "• A paddle shoved into its own goal gives away the point (touching it yourself doesn't count)\n"
         "• It smashes stones: tombstones break in 2 hits, ferry gates in 3, walls in 4"),
    Kind("twin", "Twin Balls", "双", "Wild", 0,
         "Until the point ends there are two balls, Red's and Blue's; each only scores in the other's goal.",
         "The ball splits in two until the point ends: a red ball and a blue ball.\n"
         "• They fly apart at half the speed the ball had (never slower than half a serve)\n"
         "• Hits don't change their colours\n"
         "• Red scores only by getting the red ball into Blue's goal, and Blue the blue ball into Red's\n"
         "• A ball that reaches its own colour's goal just bounces off it"),
    Kind("chaos", "Chaos Mode +", "狂", "Wild", 0,
         "Chaos Mode + until the point ends: both paddles and the ball drift through sizes and speeds.",
         "Chaos Mode + is on until the point ends.\n"
         "• Both paddles and the ball keep drifting bigger and smaller, faster and slower, each on its own\n"
         "• Everything goes back to normal for the next serve\n"
         "• Doesn't turn up if Chaos Mode + is already on"),
    Kind("curve", "Curveball", "旋", "Wild", 0,
         "Until the point ends, every hit curves the way the paddle was moving as it hit.",
         "Curveball is on until the point ends.\n"
         "• Move your paddle up or down as you hit, and the ball bends that way as it flies\n"
         "• The faster you sweep, the harder it bends; a still paddle hits it straight\n"
         "• The spin fades as it goes, and flips when it bounces off the top or bottom\n"
         "• Doesn't turn up if Curveball is on for the whole match (in Settings)"),
    Kind("double", "Double or Nothing", "倍", "Wild", 0,
         "This point is worth 2, whoever wins it.",
         "This point is worth 2.\n"
         "• Whoever wins it, Red or Blue\n"
         "• It can win the match outright"),
    Kind("wind", "Wind Gust", "风", "Wild", 10,
         "For 10 seconds a gusting wind blows up or down the court, bending the ball's path.",
         "A wind blows across the court for 10 seconds.\n"
         "• It bends the ball's path up or down, in gusts\n"
         "• Leaves blowing across the court show which way\n"
         "• It doesn't push the paddles"),
    Kind("cracker", "Firecracker", "爆", "Wild", 0,
         "A firecracker is strapped to the ball: after 3 hits it bangs and the ball shoots off.",
         "A firecracker is strapped to the ball.\n"
         "• After 3 more hits its fuse runs out and it bangs\n"
         "• The ball shoots off at double speed at a new angle, away from whoever lit it\n"
         "• The blast flattens any stone close by\n"
         "• Lasts until it bangs, or the point ends"),
    Kind("lantern", "Lantern Night", "灯", "Wild", 0,
         "Until the point ends the court goes dark, lit only by lanterns round the paddles and the ball's glow.",
         "Night falls on the court until the point ends.\n"
         "• Only lantern light round each paddle and the ball's own glow light it up\n"
         "• Power-up talismans still glow in the dark\n"
         "• Doesn't turn up if Lantern Night is on for the whole match (in Settings)"),
    Kind("portal", "Portal Pair", "门", "Wild", 0,
         "Two linked portals open on the court until the point ends: in one, out the other.",
         "Two linked portals open somewhere on the court, each facing its own way.\n"
         "• A ball that goes into one comes out of the other at the same speed\n"
         "• It leaves the way that portal is facing (shown by its arrows)\n"
         "• Paddles pass straight through them\n"
         "• Lasts until the point ends"),
)
BY_KEY = {kind.key: kind for kind in KINDS}

FAMILY_COLOURS = {"Boon": (240, 176, 64), "Curse": (178, 96, 255), "Wild": (90, 220, 150)}
FAMILY_NOTES = {"Boon": "Boon: helps whoever takes it",
                "Curse": "Curse: hinders the other player",
                "Wild": "Wild: shakes up the court"}


class PowerUps:
    RADIUS = 56          # how close a paddle or ball must come to take one (and the talisman's size)
    LIFETIME = 14.0      # seconds a talisman waits on the court
    MOST = 2             # talismans on the court at once
    WAITS = ((14, 22), (8, 14), (4, 8), (1.5, 3))   # seconds between talismans: Rare, Normal, Frequent, Chaotic

    GIANT, SHRINK = 1.5, 0.65               # paddle height
    SWIFT, FROZEN = 1.5, 0.5                # paddle speed (Swift Step's hits are no harder: see Paddle.on_contact)
    FROST_TIME = 5.0                        # seconds whoever hits a frosted ball back stays frozen
    FIRE = 1.4                              # a Spirit Fire shot's speed...
    FIRE_TOP = 1.1                          # ...up to this much past the usual top speed (it reached 1.4 times)
    BALL_GRAVITY = 1500                     # px/s^2
    PADDLE_GRAVITY = 2600
    JUMP = 1900                             # px/s off the floor; a tap is cut to JUMP_CUT at once (a hop)...
    JUMP_HOLD = 0.4                         # ...but holding Up for up to this long keeps it rising...
    HOLD_GRAVITY = 0.15                     # ...under only this share of gravity: right up to the top
    JUMP_CUT = 500                          # px/s: letting go of Up early cuts the climb to this
    TELEPORT_WARNING = 0.12                 # seconds before the ball would be in
    TELEPORTS_HELD = 1                      # Safety Teleport charges a player can hold
    STICK_TIME = (0.6, 1.0)                 # seconds a gooey paddle holds the ball before slinging it
    STICK_SPEED = 0.85                      # the share of its speed it keeps...
    SLING_WHIP = 0.5                        # ...plus this share of the paddle's speed as it flicks
    BLINK_EVERY = (0.1, 0.5)                # seconds between Blink Ball hops
    BLINK_REACH = (45, 120)                 # how far a hop goes, in px
    BLINK_CLEAR = 350                       # px: no hops this close to the paddle the ball is heading for
    TOMBS_MOST = 2                          # Tombstones from power-ups standing at once
    GHOST_SHOWN = (0.5, 1.3)                # seconds a Ghost Ball stays in sight at a time...
    GHOST_HIDDEN = (0.3, 0.7)               # ...and out of sight, each picked at random
    GHOST_FADE = 0.15                       # seconds it takes to fade out, or back in
    GHOST_CLEAR = 300                       # px: always in sight this close to the paddle it's heading for
    CURVE = 2000                            # Curveball: px/s^2 the ball bends at, from a full-speed sweep...
    CURVE_FADE = 1.3                        # ...fading away at this rate as it flies (per second)
    WIND = 500                              # Wind Gust: px/s^2 at the height of a gust (360 was too gentle to notice)
    CRACKER_HITS = 3                        # Firecracker: hits before it bangs...
    CRACKER_FUSE = 0.25                     # ...a moment after the last one...
    CRACKER_TOP = 2600                      # ...and the ball shoots off at double speed, up to this (3600 was unreturnable)
    PORTAL_R = 80                           # Portal Pair: a portal's radius
    PORTAL_COOL = 0.35                      # seconds before a ball can go through a portal again
    PORTAL_TRIPS = 3                        # trips with no paddle touch before they close (a loop)
    LANTERN_FADE = (0.6, 0.9)               # Lantern Night: seconds for night to fall, and to lift
    BLAST_R = 280                           # Firecracker: how far its blast flattens stones
    BLAST_TIME = 0.7                        # seconds its shockwave takes to spread and fade
    SNOW_GROW = 1 / 9000                    # Snowball: size gained per px it rolls...
    SNOW_MOST = 2.4                         # ...up to this many times its own diameter (200 px at most)
    SNOW_SHOVE = 0.12                       # share of its speed that shoves a paddle back, times size squared
    SNOW_HOLD = 0.0                         # share of a paddle's drive into it that takes off the shove
    SNOW_REELING = 0.4                      # seconds a shoved paddle answers its controls only weakly...
    SNOW_GRIP = 0.15                        # ...this share as well as usual
    SHOVE_TIME = 0.6                        # seconds a shove can still carry a paddle into its goal
    SHOVE_CARRY = 150                       # px/s backwards it must still be going for the shove to count

    def __init__(self, game):
        self.game = game
        self.pickups = []        # {"kind", "x", "y", "age", "phase"}
        self.popups = []         # floating names: [text, x, y, age, colour]
        self.frost = None        # {"holder": a paddle or "ball", "owner": who took it, "armed": True while it
                                 #  waits on the taker's paddle for their next hit (they aren't slowed by
                                 #  it), "left": seconds}
        self.ghost = None        # {"left": seconds, "hidden": bool, "next": seconds till it turns, "alpha"}
        self.blink = None        # {"left": seconds, "next": seconds to the next hop}
        self.hops = []           # recent Blink Ball hops for the renderer: [x0, y0, x1, y1, age]
        self.tombs = []          # Tombstones raised by the power-up
        self.wall_down = 0.0     # seconds Open Court keeps the Middle Wall down (UNTIL_POINT)
        self.snow = None         # Snowball: {"size": times the ball's own diameter}
        self.twin = None         # Twin Balls: {"left": seconds, "ball": the blue ball}; the main ball is red
        self.switch_plus = False # Soul Swap: Chaos Switch + is on until the point ends
        self.chaos_plus = False  # Chaos Mode + until the point ends
        self.curve_on = False    # Curveball until the point ends
        self.double = False      # Double or Nothing: the point being played is worth 2
        self.wind = None         # Wind Gust: {"left", "dir" (1 down, -1 up), "t"}
        self.cracker = None      # Firecracker: {"hits": hits left, "fuse": seconds to the bang or None}
        self.lantern = None      # Lantern Night: {"age": seconds, "lifting": seconds left of the dawn, or None}
        self.blasts = []         # Firecracker explosions for the renderer: [x, y, age]
        self.portals = []        # Portal Pair: [{"x", "y", "angle"}, {"x", "y", "angle"}]
        self.portal_trips = 0    # trips through them since a paddle last touched a ball
        self.ball_v = (game.ball.vx, game.ball.vy)   # the ball's velocity last frame, before any hit
        self.wait = self.next_wait()
        self.ball_restitution = game.ball.restitution
        for paddle in (game.p1, game.p2):
            paddle.effects = {}  # key -> seconds left
            paddle.charges = {}  # key -> uses left
            paddle.shoved = 0.0  # seconds a Snowball's shove can still carry it into its goal
        game.ball.blazing = False
        game.ball.curve = 0.0
        game.ball.portal_cool = 0.0
        game.ball.stuck = None
        game.ball.unstick = 0.0

    @property
    def settings(self):
        return self.game.settings

    def kinds(self):
        """The power-ups switched on in Settings."""
        s = self.settings
        if not s.powerups:
            return []
        return [kind for kind in KINDS if getattr(s, "pu_" + kind.key)]

    def most(self):
        """Talismans that may wait on the court at once: three on Chaotic, two otherwise."""
        return 3 if self.settings.powerup_rate >= 3 else self.MOST

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
        """Caught the frost by hitting a frosted ball back: slowed until it melts (FROST_TIME).  The
        one who took the power-up isn't slowed while it waits for their next hit."""
        return self.frosted(paddle) and not self.frost["armed"]

    def ball_frosted(self):
        return self.frost is not None and self.frost["holder"] == "ball"

    def gravity(self, paddle):
        return self.has(paddle, "gravity")

    def wall_open(self):
        """Open Court, or Soul Swap's Chaos Switch +, has the Middle Wall down."""
        return self.wall_down > 0 or self.switch_plus

    def swapping(self):
        """Chaos Switch + is on: from Settings, or from Soul Swap until the point ends."""
        return self.settings.switch_mid_rally or self.switch_plus

    def drifting(self):
        """Chaos Mode + is on: from Settings, or from the power-up until the point ends."""
        return self.settings.chaos_mode == 2 or self.chaos_plus

    def curving(self):
        """Curveball is on: for the whole match (Settings), or from the power-up until the point ends."""
        return getattr(self.settings, "curveball", False) or self.curve_on

    def wind_force(self):
        """Wind Gust: the wind's push on the ball now, px/s^2 (down is positive), gusting."""
        if not self.wind:
            return 0.0
        w = self.wind
        ease = min(1.0, (BY_KEY["wind"].seconds - w["left"]) / 0.8, w["left"] / 0.8)
        return w["dir"] * self.WIND * ease * (0.65 + 0.35 * math.sin(w["t"] * 2.3))

    def ball_accel(self):
        """What pulls the ball up or down as it flies: Gravity and the wind (for the AI's reckoning)."""
        return (self.BALL_GRAVITY if self.ball_gravity() else 0.0) + self.wind_force()

    def lantern_level(self):
        """Lantern Night: 0 (day) to 1 (full night), easing in and out.  Always night if it's on
        for the whole match in Settings."""
        if getattr(self.settings, "lantern_night", False):
            return 1.0
        if not self.lantern:
            return 0.0
        fall, lift = self.LANTERN_FADE
        level = min(1.0, self.lantern["age"] / fall)
        if self.lantern["lifting"] is not None:
            level = min(level, max(0.0, self.lantern["lifting"] / lift))
        return level

    def cracker_hits(self, ball):
        """Firecracker: hits left before it bangs, if it's strapped to this ball (else 0)."""
        return self.cracker["hits"] if self.cracker and ball is self.game.ball else 0

    def point_value(self):
        return 2 if self.double else 1

    def snowball(self):
        return self.snow is not None

    def ball_size_factor(self):
        return self.snow["size"] if self.snow else 1.0

    def spawnable(self, kind):
        """Open Court only while the wall is up; Soul Swap only while it's down; one Snowball at a time."""
        game = self.game
        if kind.key == "wall":
            return game.wall_up
        if kind.key == "swap":
            return not self.swapping()
        if kind.key == "chaos":
            return not self.drifting()
        if kind.key == "curve":
            return not self.curving()
        if kind.key == "double":
            return not self.double
        if kind.key == "wind":
            return self.wind is None
        if kind.key == "cracker":
            return self.cracker is None
        if kind.key == "lantern":
            return self.lantern is None and not getattr(self.settings, "lantern_night", False)
        if kind.key == "portal":
            return not self.portals
        if kind.key == "tomb":
            return len(self.tombs) < self.TOMBS_MOST
        if kind.key == "snowball":
            return self.snow is None
        if kind.key == "twin":
            return self.twin is None
        return True

    # ---------------- Twin Balls ----------------

    def balls(self):
        """Every ball in play: the ball, and while Twin Balls lasts, the blue one too."""
        return [self.game.ball] + ([self.twin["ball"]] if self.twin else [])

    def split_ball(self):
        """Twin Balls: the ball splits in two, red (the ball itself) and blue (a new one), heading off
        on mirrored paths so they part straight away."""
        from objects.ball import Ball
        game, ball = self.game, self.game.ball
        if ball.stuck:
            self.unstick_now(ball)
        r = ball.diameter / 2
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        blue = Ball(game, diameter = ball.diameter, x = ball.x0, y = ball.y0, speed = ball.speed, color = "white")
        blue.drift = getattr(ball, "drift", None)
        # They fly apart at mirrored angles, each at half the speed the ball had (two at full speed
        # at once would be too much to handle)
        before = math.hypot(ball.vx, ball.vy)
        speed = max(before * 0.5, ball.speed * math.sqrt(2) * 0.5)   # never slower than half a serve
                                                                      # (a serve goes at ball.speed on each axis)
        ux, uy = (ball.vx / before, ball.vy / before) if before else (1.0, 0.0)
        if abs(uy) < 0.3:                                   # split them clearly apart
            uy = math.copysign(0.5, uy or 1)
            ux = math.copysign(math.sqrt(0.75), ux or 1)
        ball.vx, ball.vy = speed * ux, speed * uy
        blue.vx, blue.vy = speed * ux, -speed * uy
        # part them a little at once, so each is clear of the other and of the walls
        apart = r + 4
        ball.y0 = clamp(cy - r - apart, 0, BASE_H - 2 * r)
        ball.y1 = ball.y0 + 2 * r
        blue.y0 = clamp(cy - r + apart, 0, BASE_H - 2 * r)
        blue.y1 = blue.y0 + 2 * r
        blue.x0, blue.x1 = cx - r, cx + r
        blue.last_paddle = ball.last_paddle
        ball.side, blue.side = "red", "blue"
        self.twin = {"left": UNTIL_POINT, "ball": blue}            # until the point ends
        game.app.fx.spark(cx, cy, 30, (255, 236, 200), speed = 420, life = .6)

    def end_twin(self):
        """Twin Balls is over (its time, or a point): the blue ball vanishes, the ball plays on."""
        twin, game = self.twin, self.game
        # every ball but the ball itself goes (whatever left one behind), and the ball is plain again
        for extra in [o for o in game.objects if o.is_ball and o is not game.ball]:
            game.objects.remove(extra)
            game.app.fx.spark((extra.x0 + extra.x1) / 2, (extra.y0 + extra.y1) / 2, 18, (120, 170, 255),
                              speed = 300, life = .5)
        game.ball.side = None
        self.twin = None

    def unstick_now(self, ball):
        if ball.stuck:
            ball.vx, ball.vy = ball.stuck["vx"], ball.stuck["vy"]
            ball.stuck = None
            ball.unstick = 0.3

    def ball_gravity(self):
        return any(self.has(p, "gravity") for p in (self.game.p1, self.game.p2))

    def ball_alpha(self, ball=None):
        """How visible the ball is: a Ghost Ball fades out of sight and back at random moments.
        (Twin Balls' blue ball is never a ghost.)"""
        if not self.ghost or (ball is not None and ball is not self.game.ball):
            return 1.0
        return self.ghost["alpha"]

    def ghostly(self):
        """A Ghost Ball is on: the ball itself is haunted (the HUD shows it on the ball, not a player)."""
        return self.ghost is not None

    def hidden_from(self, paddle):
        return self.ghost is not None and self.ball_alpha() < 0.35

    def effect_list(self, paddle):
        """What is on this player right now, for the HUD: [(key, seconds left or None, charges)]."""
        items = [(key, left, 0) for key, left in paddle.effects.items()]
        if self.frosted(paddle):
            ready = self.frost["armed"]
            items.append(("frost", None if ready else self.frost["left"], 1 if ready else 0))
        items += [(key, None, count) for key, count in paddle.charges.items()]
        return items

    def court_list(self):
        """What is on the ball and the court: [(key, seconds left or None, note)]."""
        items = []
        ball = self.game.ball
        if self.ball_frosted():
            items.append(("frost", self.frost["left"], "Frosted: whoever hits it back is frozen"))
        if getattr(ball, "blazing", False):
            items.append(("fire", None, "Blazing shot"))
        if self.ghost:
            items.append(("ghost", self.ghost["left"], "Vanishes and reappears at random"))
        if self.blink:
            items.append(("blink", self.blink["left"], "Blinking about"))
        if getattr(ball, "stuck", None):
            items.append(("sticky", ball.stuck["left"], "Stuck to a paddle"))
        if self.wall_open():
            items.append(("wall", self.wall_down, "Middle Wall down until the point ends"))
        for tomb in self.tombs:
            items.append(("tomb", tomb.life, "Drifting" if tomb.speed else "Standing"))
        if self.snow:
            items.append(("snowball", UNTIL_POINT, f"Snowball, {self.snow['size']:.1f}x as big"))
        if self.twin:
            items.append(("twin", self.twin["left"], "Red and blue balls: each scores only in the other's goal"))
        if self.switch_plus:
            items.append(("swap", UNTIL_POINT, "Chaos Switch +: the paddles keep swapping places"))
        if self.chaos_plus:
            items.append(("chaos", UNTIL_POINT, "Chaos Mode +: sizes and speeds drifting"))
        if self.curve_on:
            items.append(("curve", UNTIL_POINT, "Curveball: hits bend the way the paddle moved"))
        if self.double:
            items.append(("double", UNTIL_POINT, "This point is worth 2"))
        if self.wind:
            items.append(("wind", self.wind["left"], "Wind blowing " + ("down" if self.wind["dir"] > 0 else "up")))
        if self.cracker:
            items.append(("cracker", float(self.cracker["hits"]), "Firecracker: bangs after its last hit"))
        if self.lantern:
            items.append(("lantern", UNTIL_POINT, "Night: lanterns only, until the point ends"))
        if self.portals:
            items.append(("portal", UNTIL_POINT, "Two linked portals"))
        return items

    # ---------------- Each frame of play ----------------

    def update(self, dt):
        game, ball = self.game, self.game.ball
        for paddle in (game.p1, game.p2):
            for key in list(paddle.effects):
                paddle.effects[key] -= dt
                if paddle.effects[key] <= 0:
                    del paddle.effects[key]

        if self.frost:
            self.frost["left"] -= dt
            if self.frost["left"] <= 0:
                self.frost = None
        if self.ghost:
            self.update_ghost(dt)
        if self.wall_down > 0:
            self.wall_down -= dt
            if self.wall_down <= 0:
                self.wall_down = 0.0
                self.send_home()

        self.update_sticky(dt)
        self.update_blink(dt)
        self.update_tombs(dt)
        self.update_flight(dt)
        self.update_cracker(dt)
        if self.lantern:
            self.lantern["age"] += dt
        self.update_portals(dt)
        if self.update_snow(dt):
            return                          # a paddle was shoved into its goal: the point is over

        # Gravity pulls the ball down; its bounces keep their height so it doesn't die on the floor
        if self.ball_gravity():
            if not ball.stuck:
                ball.vy = clamp(ball.vy + self.BALL_GRAVITY * dt, -2400, 2400)
            ball.restitution = 1.2
        else:
            ball.restitution = self.ball_restitution      # (not under Wind Gust: lively bounces sped its rallies up)

        kinds = self.kinds()
        keys = {kind.key for kind in kinds}
        if kinds:
            self.wait -= dt
            if self.wait <= 0:
                self.wait = self.next_wait()
                waiting = {item["kind"] for item in self.pickups}    # never two of a kind on the court
                choices = [kind for kind in kinds if self.spawnable(kind) and kind.key not in waiting]
                if choices and len(self.pickups) < self.most():
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
        self.ball_v = (ball.vx, ball.vy)

    def update_ghost(self, dt):
        """A Ghost Ball turns invisible and back at random moments, fading quickly each way."""
        ghost = self.ghost
        ghost["left"] -= dt
        if ghost["left"] <= 0:
            self.ghost = None
            return
        ghost["next"] -= dt
        if ghost["next"] <= 0:
            ghost["hidden"] = not ghost["hidden"]
            ghost["next"] = random.uniform(*(self.GHOST_HIDDEN if ghost["hidden"] else self.GHOST_SHOWN))
        target = 0.0 if ghost["hidden"] else 1.0
        # it's always in sight for its last GHOST_CLEAR px to a paddle (vanishing just before it
        # reached you was a guess, not a read), fading back in early enough to be whole by then
        ball = self.game.ball
        if self.gap_ahead(ball.x0, ball.x1, ball.vx) <= self.GHOST_CLEAR + abs(ball.vx) * self.GHOST_FADE:
            target = 1.0
        step = dt / self.GHOST_FADE
        ghost["alpha"] = min(target, ghost["alpha"] + step) if target > ghost["alpha"] else max(target, ghost["alpha"] - step)

    def gap_ahead(self, x0, x1, vx):
        """How far across the court (px) a ball spanning x0..x1 and moving at vx is from the
        nearest paddle it's heading for: 0 if level with one, infinity if none is ahead."""
        best = math.inf
        for paddle in (self.game.p1, self.game.p2):
            gap = paddle.x0 - x1 if vx >= 0 else x0 - paddle.x1
            if gap >= -paddle.width:
                best = min(best, max(0.0, gap))
        return best

    def update_popups(self, dt):
        for popup in self.popups:
            popup[3] += dt
        self.popups = [p for p in self.popups if p[3] < 1.4]
        for hop in self.hops:
            hop[4] += dt
        self.hops = [h for h in self.hops if h[4] < 0.35]
        # Lantern Night lifts, and the Firecracker's shockwaves spread and fade, whatever the game's doing
        if self.lantern and self.lantern["lifting"] is not None:
            self.lantern["lifting"] -= dt
            if self.lantern["lifting"] <= 0:
                self.lantern = None
        for blast in self.blasts:
            blast[2] += dt
        self.blasts = [b for b in self.blasts if b[2] < self.BLAST_TIME]
        # Tombstones sink away after a point, while the "scored" message shows
        game = self.game
        if game.paused or game.countdown is not None:
            for tomb in self.tombs:
                if tomb.life != UNTIL_POINT:
                    tomb.life -= dt
            self.update_tombs(dt)

    def spawn(self, key):
        game = self.game
        movers = (game.p1, game.p2, game.ball)
        stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
        for _ in range(40):
            x, y = random.uniform(300, BASE_W - 300), random.uniform(170, BASE_H - 150)
            clear = all(math.hypot(x - (o.x0 + o.x1) / 2, y - (o.y0 + o.y1) / 2) > 220 for o in movers)
            apart = all(math.hypot(x - item["x"], y - item["y"]) > 260 for item in self.pickups)
            off_stones = all(not (o.x0 - 50 < x < o.x1 + 50 and o.y0 - 50 < y < o.y1 + 50) for o in stones)
            if clear and apart and off_stones:
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
        for ball in self.balls():
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
        elif key in ("giant", "swift", "fire"):
            owner.effects[key] = kind.seconds
        elif key in ("gravity", "sticky"):
            owner.effects[key] = rival.effects[key] = kind.seconds      # on both paddles
        elif key == "shrink":
            rival.effects[key] = kind.seconds
        elif key == "frost":
            self.frost = {"holder": owner, "owner": owner, "armed": True, "left": kind.seconds}
        elif key == "ghost":
            self.ghost = {"left": kind.seconds, "hidden": False, "alpha": 1.0,
                          "next": random.uniform(0.3, 0.8)}
        elif key == "wall":
            self.wall_down = UNTIL_POINT
        elif key == "blink":
            self.blink = {"left": kind.seconds, "next": random.uniform(*self.BLINK_EVERY) * 0.5}
        elif key == "tomb":
            self.raise_tomb(UNTIL_POINT)
        elif key == "snowball":
            self.snow = {"size": 1.0}
        elif key == "twin":
            if not self.twin:                       # a second one while split does nothing
                self.split_ball()
        elif key == "swap":
            self.switch_plus = True
            self.game.start_switch_mode()
        elif key == "chaos":
            self.chaos_plus = True
        elif key == "curve":
            self.curve_on = True
        elif key == "double":
            self.double = True
        elif key == "wind":
            self.wind = {"left": kind.seconds, "dir": random.choice((-1, 1)), "t": 0.0}
        elif key == "cracker":
            self.cracker = {"hits": self.CRACKER_HITS, "fuse": None}
        elif key == "lantern":
            self.lantern = {"age": 0.0, "lifting": None}
        elif key == "portal":
            self.open_portals()

        app = self.game.app
        app.fx.burst(item["x"], item["y"], 8, 44, "red" if owner.is_left else "blue", life=(.6, 1.0))
        app.fx.spark(item["x"], item["y"], 18, FAMILY_COLOURS[kind.family], speed=380, life=.6)
        app.sound_manager.play("countdown_go.wav")
        self.popups.append([kind.name, item["x"], item["y"], 0.0, FAMILY_COLOURS[kind.family]])
        self.game.on_powerup(kind, owner)

    # ---------------- Hooks from the ball and the match ----------------

    def on_hit(self, ball, paddle, normal=(1, 0)):
        """A paddle touched the ball (called after the paddle has shaped the return)."""
        # Frostbite goes one way: the taker's next hit frosts the ball, and whoever hits the frosted
        # ball back catches it and is frozen for FROST_TIME, whatever they hit.  It never comes back
        # to the taker, and the ball keeps its speed (slowing it gave the frozen player more time).
        main = ball is self.game.ball          # Twin Balls' blue ball carries no frost, goo or snow
        self.portal_trips = 0                  # a ball looping through the portals has been played
        frost = self.frost
        if frost and main:
            if frost["holder"] is paddle and frost["armed"]:
                frost["holder"] = "ball"
                frost["armed"] = False
            elif frost["holder"] == "ball" and paddle is not frost["owner"]:
                frost["holder"] = paddle
                frost["left"] = self.FROST_TIME

        # Spirit Fire: every hit while it lasts is a blazing shot, 40% faster, but never more than a
        # little past the usual top speed (it reached 1.4 times it, faster than anyone can follow)
        ball.blazing = False
        if self.has(paddle, "fire"):
            ball.vx *= self.FIRE
            ball.vy *= self.FIRE
            serve = getattr(ball, "speed", 0)
            if serve:
                top = self.FIRE_TOP * MAX_BALL_SPEEDUP * serve * math.sqrt(2)
                speed = math.hypot(ball.vx, ball.vy)
                if speed > top:
                    ball.vx, ball.vy = ball.vx * top / speed, ball.vy * top / speed
            ball.blazing = True
            self.game.app.fx.spark((ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, 30,
                                   (255, 150, 60), speed=560, life=.7)

        if self.snow and normal[0] != 0 and main:
            self.shove(paddle)

        # Curveball: the ball bends the way the paddle was sweeping as it hit
        ball.curve = 0.0
        if self.curving() and normal[0] != 0:
            sweep = clamp(paddle.vy / max(1.0, paddle.speed), -1.0, 1.0)
            ball.curve = sweep * self.CURVE if abs(sweep) > 0.08 else 0.0

        # Firecracker: each hit burns the fuse down; the last lights it
        if main and self.cracker and self.cracker["fuse"] is None:
            self.cracker["hits"] -= 1
            if self.cracker["hits"] <= 0:
                self.cracker["fuse"] = self.CRACKER_FUSE
                self.cracker["lit_by"] = paddle

        if main and self.has(paddle, "sticky") and normal[0] != 0 and not ball.stuck and ball.unstick <= 0:
            self.stick(ball, paddle)

    # ---------------- Curveball and Wind Gust ----------------

    def update_flight(self, dt):
        """Curveball's spin and the wind both bend the balls' paths as they fly."""
        if self.wind:
            self.wind["left"] -= dt
            self.wind["t"] += dt
            if self.wind["left"] <= 0:
                self.wind = None
        push = self.wind_force()
        fade = math.exp(-self.CURVE_FADE * dt)
        for b in self.balls():
            if b.stuck:
                continue
            curve = getattr(b, "curve", 0.0)
            if curve:
                b.vy += curve * dt
                b.curve = curve * fade if abs(curve * fade) > 20 else 0.0
            if push:
                # the wind turns the ball's path but doesn't speed it up (any speed it added would
                # come straight back out of the next paddle hit, as a faster shot)
                speed = math.hypot(b.vx, b.vy)
                b.vy += push * dt
                turned = math.hypot(b.vx, b.vy)
                if turned:
                    b.vx, b.vy = b.vx * speed / turned, b.vy * speed / turned

    # ---------------- Firecracker ----------------

    def update_cracker(self, dt):
        """The firecracker's fuse burns after its last hit, then it bangs: the ball shoots off at
        double speed at a new angle, away from whoever lit it (either way, it could shoot straight
        back at them from point-blank, and nearly half its points ended on the bang)."""
        cracker = self.cracker
        if not cracker or cracker["fuse"] is None:
            return
        cracker["fuse"] -= dt
        if cracker["fuse"] > 0:
            return
        self.cracker = None
        ball = self.game.ball
        if ball.stuck:
            self.unstick_now(ball)
        speed = min(self.CRACKER_TOP, max(math.hypot(ball.vx, ball.vy), ball.speed) * 2)
        angle = math.radians(random.uniform(-55, 55))
        lit_by = cracker.get("lit_by")
        way = (1 if lit_by.is_left else -1) if lit_by is not None else random.choice((-1, 1))
        ball.vx, ball.vy = way * speed * math.cos(angle), speed * math.sin(angle)
        ball.blazing = True
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        app = self.game.app
        fx = app.fx
        fx.spark(cx, cy, 110, (255, 214, 100), speed = 980, life = 1.0)
        fx.spark(cx, cy, 80, (255, 90, 40), speed = 700, life = .9)
        fx.spark(cx, cy, 50, (120, 100, 90), speed = 380, life = 1.4)       # smoke and grit
        fx.burst(cx, cy, 18, 80, "red", life = (.6, 1.1))
        self.blasts.append([cx, cy, 0.0])
        app.sound_manager.play("firecracker_bang.wav")
        renderer = getattr(app, "renderer", None)
        if renderer is not None:
            renderer.shake(22, 0.45)
        self.popups.append(["BANG!", cx, cy - 40, 0.0, (255, 200, 80)])
        # any stone the blast reaches is flattened at once
        for stone in self.game.objects:
            if getattr(stone, "is_obstacle", False) and stone.solid:
                nx, ny = clamp(cx, stone.x0, stone.x1), clamp(cy, stone.y0, stone.y1)
                if math.hypot(cx - nx, cy - ny) <= self.BLAST_R:
                    stone.crumble()
        hook = getattr(self.game, "on_bang", None)
        if hook:
            hook(cx, cy)

    # ---------------- Portal Pair ----------------

    def open_portals(self):
        """Two linked portals open somewhere mid-court, well apart, each facing its own way (never
        straight up or down)."""
        game, ball = self.game, self.game.ball
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
        placed = []
        for _ in range(200):
            x = random.uniform(BASE_W * 0.27, BASE_W * 0.73)
            y = random.uniform(190, BASE_H - 190)
            if math.hypot(x - bx, y - by) < 220:
                continue
            if any(math.hypot(x - p["x"], y - p["y"]) < 520 for p in placed):
                continue
            if any(o.x0 - 90 < x < o.x1 + 90 and o.y0 - 90 < y < o.y1 + 90 for o in stones):
                continue
            while True:
                angle = random.uniform(0, math.tau)
                if abs(math.cos(angle)) >= 0.45:
                    break
            placed.append({"x": x, "y": y, "angle": angle})
            if len(placed) == 2:
                break
        if len(placed) == 2:
            self.portals = placed
            self.portal_trips = 0
            for p in placed:
                game.app.fx.spark(p["x"], p["y"], 24, (170, 120, 255), speed = 300, life = .6)

    def update_portals(self, dt):
        """A ball whose centre reaches a portal comes out of the other one, at the same speed, the
        way that portal faces."""
        if not self.portals:
            return
        for b in self.balls():
            b.portal_cool = max(0.0, getattr(b, "portal_cool", 0.0) - dt)
            if b.stuck or b.portal_cool > 0:
                continue
            cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
            for i, door in enumerate(self.portals):
                if math.hypot(cx - door["x"], cy - door["y"]) > self.PORTAL_R * 0.6:
                    continue
                out = self.portals[1 - i]
                r = b.width / 2
                dx, dy = math.cos(out["angle"]), math.sin(out["angle"])
                x = clamp(out["x"] + dx * (self.PORTAL_R * 0.5 + r), r + 2, BASE_W - r - 2)
                y = clamp(out["y"] + dy * (self.PORTAL_R * 0.5 + r), r + 2, BASE_H - r - 2)
                b.x0, b.y0, b.x1, b.y1 = x - r, y - r, x + r, y + r
                speed = math.hypot(b.vx, b.vy)
                b.vx, b.vy = speed * dx, speed * dy
                b.portal_cool = self.PORTAL_COOL
                fx = self.game.app.fx
                fx.spark(door["x"], door["y"], 16, (170, 120, 255), speed = 260, life = .45)
                fx.spark(out["x"], out["y"], 22, (120, 230, 255), speed = 340, life = .5)
                self.game.app.sound_manager.play("countdown_tick.wav", multiplier = 0.5)
                hook = getattr(self.game, "on_portal", None)
                if hook:
                    hook(door, out)
                self.portal_trips += 1
                if self.portal_trips >= self.PORTAL_TRIPS:
                    self.close_portals()        # round and round with nobody touching it: a loop
                    return
                break

    def close_portals(self):
        """The portals snap shut (a ball was looping through them with no paddle near)."""
        for p in self.portals:
            self.game.app.fx.spark(p["x"], p["y"], 24, (170, 120, 255), speed = 300, life = .6)
        self.portals = []
        self.portal_trips = 0

    # ---------------- Snowball ----------------

    def shove(self, paddle):
        """The heavy snowball knocks the paddle that hit it back towards its own goal: the bigger
        and faster the ball, the harder.  (SNOW_HOLD would let driving into it take some of the
        shove off; it's 0, as the tooltip says: even a paddle driving into it is shoved.)"""
        back = -1 if paddle.is_left else 1                  # towards this paddle's goal
        incoming = self.ball_v[0] * back                     # how fast it came at the goal
        if incoming <= 0:
            return
        size = self.snow["size"]
        drive = max(0.0, -paddle.vx * back)                  # the paddle moving into the ball
        push = self.SNOW_SHOVE * incoming * size * size - self.SNOW_HOLD * drive
        if push <= 0:
            return
        paddle.vx = back * push
        paddle.back_speed = push
        paddle.shoved = self.SHOVE_TIME
        game = self.game
        cx, cy = (paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2
        game.app.fx.spark(cx, cy, int(8 + 10 * size), (226, 240, 255), speed = 200 + 120 * size, life = .5)

    def update_snow(self, dt):
        """The snowball grows as it rolls, and a paddle shoved back into its own goal concedes.
        Answers True if that just ended the point."""
        game, ball = self.game, self.game.ball
        if self.snow and not ball.stuck:
            rolled = math.hypot(ball.vx, ball.vy) * dt
            self.snow["size"] = min(self.SNOW_MOST, self.snow["size"] + rolled * self.SNOW_GROW)
        for paddle in (game.p1, game.p2):
            if paddle.shoved <= 0:
                continue
            paddle.shoved -= dt
            # how far it is from its goal line (the goal's wall, a few px in from the screen's edge)
            gap = paddle.x0 - game.left_wall.x1 if paddle.is_left else game.right_wall.x0 - paddle.x1
            back = -1 if paddle.is_left else 1
            # It only counts if the shove carried it in: still going back fast as it got there (the
            # goal's wall stops it dead, so last frame's speed counts too).  While it reels from the
            # hit its player barely steers it, so what key they hold doesn't matter (holding towards
            # their own goal made them impossible to shove in); after that, a paddle its player
            # steered into the goal themself gives nothing away
            going = max(paddle.vx * back, getattr(paddle, "back_speed", 0.0))
            paddle.back_speed = paddle.vx * back
            reeling = paddle.shoved > self.SHOVE_TIME - self.SNOW_REELING
            steered = getattr(paddle, "want_vx", 0.0) * back > 0
            carried = going > self.SHOVE_CARRY and (reeling or not steered)
            if gap <= 2 and not carried:
                paddle.shoved = 0.0
                continue
            if gap <= 2:
                paddle.shoved = 0.0
                self.popups.append(["Shoved into the goal!", (paddle.x0 + paddle.x1) / 2, paddle.y0 - 20, 0.0,
                                    FAMILY_COLOURS["Wild"]])
                game.on_score(ball, {"normal": (1, 0) if paddle.is_left else (-1, 0)})
                return True
        return False

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
        """A point ends whatever was riding on the ball, and clears the court: Open Court's wall
        goes back up, Tombstones sink away and the Snowball melts back into a ball.  What acts on
        both players (Gravity, Sticky Goo, a Ghost Ball, the wind) ends too, so the next serve is a
        plain one; each player's own Boons and Curses carry on.  The wait for the next talisman
        carries on where it was (restarted at every point, quick points never got one)."""
        from objects.obstacle import Obstacle
        self.pickups.clear()
        if self.ball_frosted():
            self.frost = None
        self.ghost = None
        self.wind = None
        for paddle in (self.game.p1, self.game.p2):
            for key in ("gravity", "sticky"):
                paddle.effects.pop(key, None)
            paddle.charges.pop("teleport", None)        # an unused Safety Teleport is lost
        ball = self.game.ball
        ball.blazing = False
        ball.stuck = None
        ball.unstick = 0.0
        self.blink = None
        self.snow = None
        self.end_twin()
        walled = self.switch_plus
        self.switch_plus = False
        if self.chaos_plus:
            self.chaos_plus = False
            self.game.reset_drift()                 # sizes and speeds are back to normal for the serve
        self.curve_on = False
        self.double = False
        self.cracker = None
        if self.lantern and self.lantern["lifting"] is None:
            self.lantern["lifting"] = self.LANTERN_FADE[1]   # dawn comes while the point is announced
        # court stones broken or chipped during the point stand whole again for the next serve
        for stone in self.game.objects:
            if getattr(stone, "is_obstacle", False) and stone not in self.tombs and \
                    (stone.broken or stone.hp < stone.max_hp):
                stone.restore()
        self.portals = []
        self.portal_trips = 0
        for b in self.balls():
            b.curve = 0.0
        if walled:
            self.send_home()
        for paddle in (self.game.p1, self.game.p2):
            paddle.shoved = 0.0
        for tomb in self.tombs:
            tomb.life = min(tomb.life, Obstacle.SINK)
        if self.wall_down > 0:
            self.wall_down = 0.0
            self.send_home()

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

    # ---------------- Sticky Goo ----------------

    def stick(self, ball, paddle):
        """The ball clings to the face it hit, carried along with the paddle, until it's slung off
        (see sling)."""
        hold = random.uniform(*self.STICK_TIME)
        k = self.STICK_SPEED
        serve = getattr(ball, "speed", 0)
        speed = math.hypot(ball.vx, ball.vy)
        if speed * k < serve and speed > 0:
            k = min(1.0, serve / speed)
        side = 1 if ball.vx > 0 else -1
        cy = (ball.y0 + ball.y1) / 2 - (paddle.y0 + paddle.y1) / 2
        ball.stuck = {"paddle": paddle, "dy": cy, "side": side, "left": hold, "total": hold,
                      "vx": ball.vx * k, "vy": ball.vy * k}
        self.game.app.sound_manager.play("countdown_tick.wav", multiplier = 0.5)
        self.game.on_stick(paddle)

    @staticmethod
    def sling_angle(paddle, stuck=None):
        """Sticky Goo: the angle a stuck ball is slung at.  The paddle's movement aims it (moving up
        slings it up, as far as the steepest return angle); held still, it goes as it was returned."""
        move = getattr(paddle, "vy", 0.0) / max(1.0, getattr(paddle, "speed", 1500))
        if abs(move) > 0.1 or not stuck or "vx" not in stuck:
            return clamp(move, -1.0, 1.0) * MAX_BOUNCE_ANGLE
        return math.atan2(stuck["vy"], abs(stuck["vx"]) or 1.0)

    def sling(self, stuck, paddle, serve):
        """How a stuck ball leaves: at the paddle's aim, and a quick flick of the paddle throws it
        faster (up to the usual top speed); always clearly faster than the paddle chasing it."""
        side = stuck["side"]
        base = math.hypot(stuck["vx"], stuck["vy"])
        whip = math.hypot(paddle.vx, paddle.vy) * self.SLING_WHIP
        cap = MAX_BALL_SPEEDUP * serve * math.sqrt(2) if serve else math.inf
        speed = min(max(base + whip, serve), cap)
        angle = self.sling_angle(paddle, stuck)
        vx, vy = side * speed * math.cos(angle), speed * math.sin(angle)
        chasing = paddle.vx * side
        if vx * side < chasing + 150:
            vx = side * (max(0.0, chasing) + 150)
        return vx, vy

    def update_sticky(self, dt):
        ball = self.game.ball
        if ball.unstick > 0:
            ball.unstick -= dt
        stuck = ball.stuck
        if not stuck:
            return
        stuck["left"] -= dt
        # carried into a stone, it's knocked loose there and then
        for stone in self.game.objects:
            if getattr(stone, "is_obstacle", False) and stone.solid and                     min(ball.x1, stone.x1) > max(ball.x0, stone.x0) and min(ball.y1, stone.y1) > max(ball.y0, stone.y0):
                stuck["left"] = 0
        # with the Middle Wall down, a paddle can only hold the ball in its own half: carried over
        # the halfway line, or caught in the other half, it's slung there and then (it could be
        # carried right up to the other goal and slung in point-blank)
        if not self.game.wall_up:
            if ((ball.x0 + ball.x1) / 2 > BASE_W / 2) == stuck["paddle"].is_left:
                stuck["left"] = 0
        if stuck["left"] > 0:
            return
        # Peeled off: slung away where the paddle aims it
        ball.vx, ball.vy = self.sling(stuck, stuck["paddle"], ball.speed)
        ball.stuck = None
        ball.unstick = 0.3
        self.game.app.fx.spark((ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, 12, (214, 196, 90),
                               speed = 260, life = .5)

    # ---------------- Blink Ball ----------------

    def update_blink(self, dt):
        blink = self.blink
        if not blink:
            return
        blink["left"] -= dt
        if blink["left"] <= 0:
            self.blink = None
            return
        blink["next"] -= dt
        if blink["next"] <= 0:
            blink["next"] = random.uniform(*self.BLINK_EVERY)
            self.hop()

    def hop(self):
        """Blink the ball to a random spot close by.  Never into, or across, a paddle or a stone,
        and never right up to a goal, so a blink can't sneak the ball past anyone.  Not close to
        the paddle it's heading for either, before or after: a hop just before your paddle can't
        be answered."""
        game, ball = self.game, self.game.ball
        if ball.stuck or self.gap_ahead(ball.x0, ball.x1, ball.vx) < self.BLINK_CLEAR:
            return
        r = ball.diameter / 2
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        blockers = [o for o in game.objects if o.is_paddle or (getattr(o, "is_obstacle", False) and o.solid)]
        for _ in range(16):
            angle = random.uniform(0, math.tau)
            dist = random.uniform(*self.BLINK_REACH)
            x, y = bx + math.cos(angle) * dist, by + math.sin(angle) * dist
            if not (r + 4 < y < BASE_H - r - 4 and 160 < x < BASE_W - 160):
                continue
            if self.gap_ahead(x - r, x + r, ball.vx) < self.BLINK_CLEAR:
                continue
            if any(self.crosses(o, bx, by, x, y, r + 8) for o in blockers):
                continue
            ball.x0, ball.y0 = x - r, y - r
            ball.x1, ball.y1 = x + r, y + r
            self.swerve(ball)
            self.hops.append([bx, by, x, y, 0.0])
            fx = game.app.fx
            fx.spark(bx, by, 8, (150, 220, 255), speed = 200, life = .35)
            fx.spark(x, y, 10, (210, 240, 255), speed = 260, life = .4)
            game.app.sound_manager.play("countdown_tick.wav", multiplier = 0.35)
            game.on_blink(bx, by, x, y)
            return

    BLINK_TURN = (8, 22)                    # degrees a blink turns the ball off its course

    def swerve(self, ball):
        """Each blink also turns the ball a little off its course, keeping its speed (and never so
        far that it ends up crawling up and down, or heads back the way it came)."""
        speed = math.hypot(ball.vx, ball.vy)
        if not speed:
            return
        turn = math.radians(random.uniform(*self.BLINK_TURN)) * random.choice((-1, 1))
        heading = math.atan2(ball.vy, ball.vx) + turn
        vx, vy = speed * math.cos(heading), speed * math.sin(heading)
        if abs(vx) < speed * 0.35 or vx * ball.vx < 0:
            vx, vy = speed * math.cos(heading - 2 * turn), speed * math.sin(heading - 2 * turn)   # the other way
        if abs(vx) >= speed * 0.35 and vx * ball.vx > 0:
            ball.vx, ball.vy = vx, vy

    @staticmethod
    def crosses(o, x0, y0, x1, y1, pad):
        """Does the line from (x0, y0) to (x1, y1) touch `o`, grown by `pad`?"""
        left, right, top, bottom = o.x0 - pad, o.x1 + pad, o.y0 - pad, o.y1 + pad
        for i in range(9):
            t = i / 8
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if left < x < right and top < y < bottom:
                return True
        return False

    # ---------------- Tombstone ----------------

    def raise_tomb(self, seconds):
        """A tombstone rises somewhere clear of the ball and both paddles."""
        from objects.obstacle import Obstacle
        game = self.game
        moving = random.random() < 0.4
        w, h = (64, 124) if moving else (78, 148)
        ball = game.ball
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
        for _ in range(40):
            x = random.uniform(BASE_W * 0.26, BASE_W * 0.74)
            y = random.uniform(150 + h / 2, BASE_H - 150 - h / 2)
            if math.hypot(x - bx, y - by) < 300 or math.hypot(x - BASE_W / 2, y - BASE_H / 2) < 180:
                continue
            if any(abs(x - (p.x0 + p.x1) / 2) < 220 for p in (game.p1, game.p2)):
                continue
            if any(o.x0 - 120 < x < o.x1 + 120 and o.y0 - 120 < y < o.y1 + 120 for o in stones):
                continue
            speed = random.choice((-1, 1)) * random.uniform(160, 260) if moving else 0.0
            tomb = Obstacle(game, x - w / 2, y - h / 2, w, h, speed = speed,
                            lo = 120 + h / 2, hi = BASE_H - 120 - h / 2, life = seconds, style = "tomb")
            self.tombs.append(tomb)
            game.app.fx.spark(x, y + h / 2, 22, (176, 160, 130), speed = 300, life = .6, arc = (3.4, 6.0))
            return

    def update_tombs(self, dt):
        game = self.game
        for tomb in list(self.tombs):
            if tomb.life <= 0:
                self.tombs.remove(tomb)
                if tomb in game.objects:
                    game.objects.remove(tomb)

    # ---------------- Safety Teleport ----------------

    def check_teleports(self):
        """A held Safety Teleport saves its player from any ball that could score in their goal
        (under Twin Balls, the other colour's ball: their own can't score on them)."""
        game = self.game
        for paddle in (game.p1, game.p2):
            if not paddle.charges.get("teleport"):
                continue
            toward = -1 if paddle.is_left else 1
            goal = 1 if paddle.is_left else -1                  # as Ball.scores_in numbers the goals
            for ball in self.balls():
                if ball.stuck or ball.vx * toward <= 0 or not ball.scores_in(goal):
                    continue
                to_goal = ball.x0 if paddle.is_left else BASE_W - ball.x1
                if to_goal > abs(ball.vx) * self.TELEPORT_WARNING + 40 or self.covered(paddle, ball):
                    continue
                self.teleport(paddle, ball)
                break

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
        self.game.on_teleport(paddle)
