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
         "Your paddle grows half as tall again for 10 seconds of play.",
         "Your paddle grows half as tall again.\n"
         "• Lasts 10 s of play: what's left carries on into the next point"),
    Kind("swift", "Swift Step", "疾", "Boon", 10,
         "Your paddle moves half as fast again for 10 seconds of play.",
         "Your paddle moves half as fast again.\n"
         "• It doesn't make your hits any harder\n"
         "• Lasts 10 s of play: what's left carries on into the next point"),
    Kind("fire", "Spirit Fire", "火", "Boon", 10,
         "For 10 seconds of play every hit you make is a blazing shot, 20% faster.",
         "Every hit you make leaves as a blazing shot.\n"
         "• 20% faster, up to the usual top speed\n"
         "• Blazing shots chip stones: tombstones break in 2 hits, ferry gates in 3, walls in 4\n"
         "• Lasts 10 s of play: what's left carries on into the next point"),
    Kind("shrink", "Shrink Curse", "缩", "Curse", 10,
         "Your opponent's paddle shrinks by a fifth for 10 seconds of play.",
         "Your opponent's paddle shrinks by a fifth.\n"
         "• Lasts 10 s of play: what's left carries on into the next point"),
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
         "• The way your paddle is moving aims it (up slings it up), until the aim locks half a second before it goes\n"
         "• It comes off a little slower than it came in, and a quick flick of the paddle throws it faster\n"
         "• An arrow on the ball shows where it will go, and holds steady once the aim is locked\n"
         "• Lasts 10 s"),
    Kind("wall", "Open Court", "破", "Wild", 0,
         "The Middle Wall comes down until the point ends; both paddles can roam.",
         "The Middle Wall comes down and both paddles can cross the court.\n"
         "• Lasts until the point ends\n"
         "• Only turns up while the wall is up"),
    Kind("swap", "Soul Swap", "换", "Wild", 0,
         "Until the point ends, you and your opponent keep taking over each other's paddle, at a hit.",
         "Until the point ends, every few seconds both paddles glow, and the next hit makes you and "
         "your opponent take over each other's paddle, and the goal it defends.\n"
         "• Your keys, your score and your colour stay yours\n"
         "• The paddles stay where they are\n"
         "• When the point ends, you're back on your own paddles (in a Switch match, the switch goes on from there)\n"
         "• Doesn't turn up in a Switch match with mid-rally switches"),
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
         "• Every hit wears it down: 3 hits break it, or 2 blazing ones, or 1 from the Snowball\n"
         "• Paddles pass through it\n"
         "• Lasts until the point ends; up to two can stand at once"),
    Kind("snowball", "Snowball", "雪", "Wild", 0,
         "The ball becomes a heavy snowball that grows as it rolls and shoves paddles back.",
         "The ball turns into a heavy snowball until the point ends.\n"
         "• It grows as it travels, and gets heavier as it grows\n"
         "• Every hit shoves the paddle back towards its own goal, even one driving into it\n"
         "• Meet it well out from your goal, so there's room to be shoved\n"
         "• A paddle shoved into its own goal gives away the point (touching it yourself doesn't count)\n"
         "• It smashes a Tombstone at once, and once it's grown big it ploughs straight through\n"
         "• It chips the court's stones: its own tombstones break in 2 hits, ferry gates in 3, walls in 4"),
    Kind("twin", "Twin Balls", "双", "Wild", 0,
         "Until the point ends there are two balls, Red's and Blue's; each only scores in the other's goal.",
         "The ball splits in two until the point ends: a red ball and a blue ball.\n"
         "• They fly apart at half the speed the ball had (never slower than half a serve)\n"
         "• Hits don't change their colours\n"
         "• Red scores only by getting the red ball into Blue's goal, and Blue the blue ball into Red's\n"
         "• A ball that reaches its own colour's goal just bounces off it\n"
         "• Doesn't turn up in a Twin Ball match"),
    Kind("shape", "Shape Shift", "变", "Wild", 0,
         "Until the point ends, the paddles grow and shrink together, and the ball on its own.",
         "For the rest of the point, the paddles keep drifting bigger and smaller together, always "
         "the same size as each other, and the ball drifts bigger and smaller on its own.\n"
         "• Speeds stay as they are\n"
         "• Giant Paddle and Shrink Curse still act on top\n"
         "• Everything goes back to normal for the next serve\n"
         "• Doesn't turn up in a Chaos match with Constant drift"),
    Kind("curve", "Curveball", "旋", "Wild", 0,
         "Until the point ends, every hit curves the way the paddle was moving as it hit.",
         "Curveball is on until the point ends.\n"
         "• Move your paddle up or down as you hit, and the ball bends that way as it flies\n"
         "• The faster you sweep, the harder it bends; a still paddle hits it straight\n"
         "• The spin fades as it goes, and flips when it bounces off the top or bottom\n"
         "• Doesn't turn up in a Curveball match"),
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
    Kind("cracker", "Firecracker", "爆", "Wild", 5,
         "A lit firecracker is strapped to the ball: 5 seconds later it bangs and the ball shoots off.",
         "A firecracker is strapped to the ball, its fuse lit.\n"
         "• The fuse burns down for 5 s, then it bangs\n"
         "• The ball shoots off at double speed at a new angle, away from whoever hit it last\n"
         "• The blast flattens any stone close by\n"
         "• If the point ends first, it goes out without a bang"),
    Kind("lantern", "Lantern Night", "灯", "Wild", 20,
         "For 20 seconds of play the court goes dark, lit only by lanterns round the paddles and the ball's glow.",
         "Night falls on the court for 20 seconds of play.\n"
         "• Only lantern light round each paddle and the ball's own glow light it up\n"
         "• It stays dark between points, until its time is up and dawn comes\n"
         "• Power-up talismans still glow in the dark\n"
         "• Doesn't turn up in a Lantern Night match"),
    Kind("portal", "Portal Pair", "门", "Wild", 0,
         "Two linked portals drift about the court until the point ends: in one, out the other.",
         "Two linked portals open on the court, drifting slowly about, each facing its own way.\n"
         "• A ball that goes into one comes out of the other a moment later, a little slower each time\n"
         "  (never slower than a serve)\n"
         "• The way out flashes just before the ball comes out\n"
         "• Each portal is an oval, and the ball comes out of its bright wide side; they slowly turn\n"
         "• They grow a little each time a ball goes through\n"
         "• Once they're full size, the next ball through sets them collapsing into a black hole: a ball it\n"
         "  swallows comes out as Twin Balls, each heading for the goal it can score in\n"
         "• Then mini black holes come and go until the point ends, each pulling the ball in and flinging it\n"
         "  out again, on towards the side it was heading for\n"
         "• Paddles pass straight through them\n"
         "• Lasts until the point ends\n"
         "• Doesn't turn up in a Portal Pair match"),
    Kind("hole", "Black Hole", "渊", "Wild", 0,
         "A black hole opens mid-court until the point ends: it pulls the ball in and flings it out.",
         "A black hole opens in the middle of the court.\n"
         "• Its gravity pulls the ball in, harder the closer it comes: the ball speeds up as it falls\n"
         "  towards it and spirals in, and a near miss is whipped round it; paddles feel nothing\n"
         "• A ball that falls in is flung out a moment later, as fast as it went in, still heading for the same\n"
         "  side but at any angle (never straight up or down)\n"
         "• Its heart pulses as it swallows the ball: no telling which way it will come out until it does\n"
         "• Lasts until the point ends, then it implodes"),
)
BY_KEY = {kind.key: kind for kind in KINDS}

FAMILY_COLOURS = {"Boon": (240, 176, 64), "Curse": (178, 96, 255), "Wild": (90, 220, 150)}
FAMILY_NOTES = {"Boon": "Boon: helps whoever takes it",
                "Curse": "Curse: hinders the other player",
                "Wild": "Wild: shakes up the court"}


class PowerUps:
    RADIUS = 56          # how close a paddle or ball must come to take one (and the talisman's size)
    LIFETIME = 20.0      # seconds of play a talisman waits on the court (it stays through points: 1.8)
    WAITS = ((14, 22), (8, 14), (4, 8), (1.5, 3))   # seconds between talismans: Rare, Normal, Frequent, Chaotic

    GIANT, SHRINK = 1.5, 0.8                # paddle height (Shrink Curse took a third off until 1.8)
    SWIFT = 1.5                             # paddle speed (Swift Step's hits are no harder: see Paddle.on_contact)
    FIRE = 1.2                              # a Spirit Fire shot's speed (1.4 until 1.8)...
    FIRE_TOP = 1.0                          # ...up to this times the usual top speed (1.1 until 1.8; once 1.4)
    TELEPORT_WARNING = 0.12                 # seconds before the ball would be in
    TELEPORTS_HELD = 1                      # Safety Teleport charges a player can hold
    STICK_TIME = (0.6, 1.0)                 # seconds a gooey paddle holds the ball before slinging it
    STICK_SPEED = 0.75                      # the share of its speed it keeps (0.85 until 1.8)...
    SLING_WHIP = 0.5                        # ...plus this share of the paddle's speed as it flicks
    AIM_LOCK = 0.5                          # seconds before it's slung that its aim locks (1.8: no last-moment fakes)
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
    CRACKER_TOP = 2600                      # Firecracker: its bang shoots the ball off at double speed, up to this (3600 was unreturnable)
    PORTAL_R = 120                          # Portal Pair: a portal's radius at its biggest (96 until 1.8)...
    PORTAL_START = 48                       # ...as they open in a Portal Pair match (they grow all match)...
    PORTAL_START_TALISMAN = 72              # ...or from the talisman, for one point: not so small
    PORTAL_GROW = 8                         # every ball through grows both by this much (1.6's were 80 all along)
    PORTAL_DRIFT = (35.0, 60.0)             # px/s a portal drifts about the court...
    PORTAL_TURN = (0.25, 0.45)              # ...and radians/s it turns (its way out: the bright side of its oval)
    PORTAL_AREA = (0.24, 0.76, 170)         # where they keep to: this share of the court's width, and px from top and bottom
    PORTAL_APART = 420                      # centres closer than this and the two drift apart
    PORTAL_STEEPEST = 0.45                  # a ball never leaves steeper than this (the cosine of its angle)
    PORTAL_COOL = 0.35                      # seconds before a ball can go through a portal again
    PORTAL_TRIPS = 3                        # trips with no paddle touch before they close (a loop)
    PORTAL_SLOW = 0.08                      # each trip through takes this share off the ball's speed (1.8)...
    PORTAL_TRANSIT = 0.2                    # ...after this long inside, while the way out flashes
    PORTAL_FLASH = 0.35                     # seconds the way out's flash takes to fade
    PORTAL_SHUT = 0.4                       # seconds closing portals take to shrink away (1.8)
    WIND_DIES = 1.5                         # Wind Gust: seconds it takes to die down at the end (0.8 until 1.8)
    HOLE_REACH = 450                        # Black Hole (1.8): px its gravity reaches...
    HOLE_PULL = 6000                        # ...px/s^2 it pulls a serve-speed ball at, HOLE_NEAR px out (more
    HOLE_NEAR = 100                         #    closer in, easing off to nothing at its reach; faster balls more:
                                            #    2000 before the playtest, which only bent paths and kept speeds)...
    HOLE_SWIRL = 3.0                        # ...how fast a ball's sideways speed bleeds away near it, so it spirals in...
    HOLE_FASTEST = 2.0                      # ...and at most this many times as fast as it came in
    HOLE_CORE = 36                          # ...the radius of its black heart: a ball touching it falls in...
    HOLE_HOLD = 0.35                        # ...seconds the ball is held inside while the way out flares...
    HOLE_COOL = 0.6                         # ...and seconds after it's flung out before the pull takes it again
    HOLE_OPEN = 0.8                         # seconds a black hole takes to open...
    HOLE_IMPLODE = 0.7                      # ...and to implode at the point's end
    HOLE_FLARE = HOLE_HOLD + HOLE_COOL      # seconds the way out flares for, from when a ball falls in
    HOLE_TRAP = 2.5                         # seconds a ball can circle in its pull before it's drawn in
    HOLE_CLEAR = 240                        # px it opens clear of stones, portals and the ball
    HOLE_TALISMAN, HOLE_COLLAPSE, HOLE_MINI = 1, 2, 3      # kinds of black hole (in replay rows too)
    COLLAPSE_TIME = 2.5                     # Portal Pair (1.8): seconds full-size portals take to collapse into a black hole:
    COLLAPSE_FLARE, COLLAPSE_SPIRAL = 0.6, 2.0   # flaring till 0.6 s, spiralling in round each other till 2.0, then merging
    MINI_REACH, MINI_PULL, MINI_CORE = 260, HOLE_PULL * 0.4, 22  # its mini black holes: a weaker pull, not so far...
    MINI_LIFE = (3.0, 5.0)                  # ...each there this long...
    MINI_FADE = 0.5                         # ...fading in and out over this...
    MINI_EVERY = (1.5, 3.0)                 # ...a new one every so often...
    MINI_FIRST = 0.6                        # ...the first this soon after the Twin Balls come out...
    MINI_MOST = 3                           # ...up to this many at once...
    MINI_GOAL_GAP = 350                     # ...this far from either goal...
    MINI_HOLD = 0.2                         # ...holding a ball this long (no black hole shows an arrow: Rowan's playtest)
    LANTERN_FADE = (0.6, 0.9)               # Lantern Night: seconds for night to fall, and to lift
    LANTERN_LIGHT = 300                     # px of lantern light round each paddle
    BLAST_R = 280                           # Firecracker: how far its blast flattens stones
    BLAST_TIME = 0.7                        # seconds its shockwave takes to spread and fade
    PLOUGH_SIZE = 1.8                       # a Snowball this many times its own size ploughs through a Tombstone...
    PLOUGH_KEEP = 0.9                       # ...keeping this share of its speed...
    PLOUGH_TIME = 0.8                       # ...in a burst of snow and stone this long (1.8)
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
        self.ghost = None        # {"left": seconds, "hidden": bool, "next": seconds till it turns, "alpha"}
        self.blink = None        # {"left": seconds, "next": seconds to the next hop}
        self.hops = []           # recent Blink Ball hops for the renderer: [x0, y0, x1, y1, age]
        self.tombs = []          # Tombstones raised by the power-up
        self.wall_down = 0.0     # seconds Open Court keeps the Middle Wall down (UNTIL_POINT)
        self.snow = None         # Snowball: {"size": times the ball's own diameter}
        self.twin = None         # Twin Balls: {"left": seconds, "ball": the blue ball}; the main ball is red
        self.switch_plus = False # Soul Swap: mid-rally switches until the point ends...
        self.soul_swaps = 0      # ...and how many it has made, to undo at the point's end
        self.shape_shift = False # Shape Shift: sizes drift until the point ends
        self.curve_on = False    # Curveball until the point ends
        self.double = False      # Double or Nothing: the point being played is worth 2
        self.wind = None         # Wind Gust: {"left", "dir" (1 down, -1 up), "t"}
        self.cracker = None      # Firecracker: {"fuse": seconds to the bang, "taker": who took it}
        self.lantern = None      # Lantern Night: {"age", "left": seconds of play, "lifting": seconds left of the dawn, or None}
        self.blasts = []         # Firecracker explosions for the renderer: [x, y, age]
        self.ploughs = []        # a big Snowball ploughing through a Tombstone, for the renderer: [x, y, age]
        self.portals = []        # Portal Pair: two {"x", "y", "angle", "r", "vx", "vy", "spin"}
        self.closing = []        # portals shrinking away as they close: the same, with "shut" going 1 to 0 (1.8)
        self.portal_trips = 0    # trips through them since a paddle last touched a ball
        self.holes = []          # Black Hole (1.8): {"x", "y", "kind", "age", "power", "spin", "way", "flash", "dying"}
        self.collapse_due = False  # Portal Pair (1.8): a ball went in at full size; they collapse as it comes out
        self.minis = None        # ...and after the collapse, mini black holes come and go: {"next": seconds}
        self.portal_grown = 0.0  # Portal Pair match: how big they'd grown when a loop shut them
        self.ball_v = (game.ball.vx, game.ball.vy)   # the ball's velocity last frame, before any hit
        self.wait = self.next_wait()
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
        """The power-ups switched on in Settings (Talisman Rush brings them even with Power-Ups off)."""
        s = self.settings
        if not s.talismans_on:
            return []
        return [kind for kind in KINDS if getattr(s, "pu_" + kind.key)]

    NOT_COUNTED = ("teleport", "double", "lantern", "wall")     # (Rowan's call: they don't crowd play)

    def in_play(self):
        """How many talismans are in play (Talismans at once, 1.8): each Boon or Curse on a player
        and each talisman acting on the court.  Safety Teleport, Double or Nothing, Lantern Night
        and Open Court don't count (NOT_COUNTED), nor do game modes."""
        s, game = self.settings, self.game
        n = 0
        for paddle in (game.p1, game.p2):
            n += sum(1 for key in paddle.effects if key != "sticky")
        n += any("sticky" in paddle.effects for paddle in (game.p1, game.p2))     # one Goo coats both
        n += sum(1 for on in (self.ghost, self.wind, self.blink, self.snow, self.cracker,
                              self.switch_plus, self.shape_shift, self.curve_on) if on)
        n += len(self.tombs)
        n += bool(self.twin) and not s.mode_twin_ball
        n += (bool(self.portals) or self.collapsed()) and not s.mode_portal_pair
        n += any(h["kind"] == self.HOLE_TALISMAN and h["dying"] is None for h in self.holes)
        return n

    def room(self):
        """Can another talisman turn up?  Only while those in play and those waiting on the court come
        to fewer than Talismans at once allows (Talisman Rush lifts the limit)."""
        waiting = sum(1 for item in self.pickups if item["kind"] not in self.NOT_COUNTED)
        return self.in_play() + waiting < self.settings.talisman_limit

    def next_wait(self):
        """Seconds to the next talisman, at the Spawn rate; Talisman Rush cuts it to a third."""
        lo, hi = self.WAITS[self.settings.powerup_rate]
        rush = self.settings.RUSH if self.settings.mode_talisman_rush else 1.0
        return random.uniform(lo, hi) / rush

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
        return factor

    def wall_open(self):
        """Open Court has the Middle Wall down."""
        return self.wall_down > 0

    def swapping(self):
        """Mid-rally switches: Switch, mid-rally (Settings), or Soul Swap until the point ends."""
        return self.settings.switch_mid_rally or self.switch_plus

    def sizes_drifting(self):
        """The paddles (together) and the ball drift bigger and smaller: all match in Chaos with
        Constant drift, or from Shape Shift until the point ends.  Speeds never drift."""
        return self.settings.chaos_drift or self.shape_shift

    def curving(self):
        """Curveball is on: for the whole match (Settings), or from the power-up until the point ends."""
        return self.settings.mode_curveball or self.curve_on

    def wind_force(self):
        """Wind Gust: the wind's push on the ball now, px/s^2 (down is positive), gusting."""
        if not self.wind:
            return 0.0
        w = self.wind
        ease = min(1.0, (BY_KEY["wind"].seconds - w["left"]) / 0.8, w["left"] / self.WIND_DIES)
        return w["dir"] * self.WIND * ease * (0.65 + 0.35 * math.sin(w["t"] * 2.3))

    def ball_accel(self):
        """What pulls the ball up or down as it flies: the wind (for the AI's reckoning)."""
        return self.wind_force()

    def lantern_level(self):
        """Lantern Night: 0 (day) to 1 (full night), easing in and out.  Always night if it's on
        for the whole match in Settings."""
        if self.settings.mode_lantern_night:
            return 1.0
        if not self.lantern:
            return 0.0
        fall, lift = self.LANTERN_FADE
        level = min(1.0, self.lantern["age"] / fall)
        if self.lantern["lifting"] is not None:
            level = min(level, max(0.0, self.lantern["lifting"] / lift))
        return level

    def cracker_fuse(self, ball):
        """Firecracker: seconds left on its fuse, if it's strapped to this ball (else 0)."""
        return self.cracker["fuse"] if self.cracker and ball is self.game.ball else 0.0

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
        if kind.key == "shape":
            return not self.sizes_drifting()
        if kind.key == "curve":
            return not self.curving()
        if kind.key == "double":
            return not self.double
        if kind.key == "wind":
            return self.wind is None
        if kind.key == "cracker":
            return self.cracker is None
        if kind.key == "lantern":
            return self.lantern is None and not self.settings.mode_lantern_night
        if kind.key == "portal":
            return not self.portals and not self.collapsed() and not self.settings.mode_portal_pair
        if kind.key == "hole":
            return not any(h["kind"] == self.HOLE_TALISMAN for h in self.holes)
        if kind.key == "tomb":
            return len(self.tombs) < self.TOMBS_MOST
        if kind.key == "snowball":
            return self.snow is None
        if kind.key == "twin":
            return self.twin is None and not self.settings.mode_twin_ball
        return True

    # ---------------- Twin Balls ----------------

    def balls(self):
        """Every ball in play: the ball, and while Twin Balls lasts, the blue one too."""
        return [self.game.ball] + ([self.twin["ball"]] if self.twin else [])

    def split_ball(self):
        """Twin Balls: the ball splits in two, red (the ball itself) and blue (a new one), heading off
        on mirrored paths so they part straight away."""
        game, ball = self.game, self.game.ball
        if ball.stuck:
            self.unstick_now(ball)
        r = ball.diameter / 2
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        blue = self.new_blue(ball)
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
        ball.side, blue.side = "red", "blue"
        self.twin = {"left": UNTIL_POINT, "ball": blue}            # until the point ends
        game.app.fx.spark(cx, cy, 30, (255, 236, 200), speed = 420, life = .6)

    def new_blue(self, ball):
        """Twin Balls' blue ball, made like the ball (it joins the court as it's made)."""
        from objects.ball import Ball
        blue = Ball(self.game, diameter = ball.diameter, x = ball.x0, y = ball.y0, speed = ball.speed, color = "white")
        blue.drift = getattr(ball, "drift", None)
        blue.last_paddle = ball.last_paddle
        return blue

    def twin_serve(self):
        """Twin Ball (a game mode): every point is served with both balls, Red's (the ball itself) and
        Blue's, under the Twin Balls rules.  Each sets off at the usual serve towards the goal it can
        score in (red only scores in Blue's goal), on mirrored paths."""
        from objects.ball import Ball
        game, ball = self.game, self.game.ball
        self.end_twin()
        r = ball.diameter / 2
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        blue = Ball(game, diameter = ball.diameter, x = ball.x0, y = ball.y0, speed = ball.speed, color = "white")
        blue.drift = getattr(ball, "drift", None)
        down = 1 if getattr(ball, "spawn_vy", 1) >= 0 else -1
        way = -1 if game.p1.colour == "blue" else 1                 # where Blue's goal is (a Switch moves it)
        ball.vx, ball.vy = way * ball.speed, down * ball.speed      # red: towards Blue's goal
        blue.vx, blue.vy = -way * ball.speed, -down * ball.speed    # blue: towards Red's goal
        apart = r + 4                                               # each a little clear of the other, moving apart
        ball.y0 = clamp(cy - r + down * apart, 0, BASE_H - 2 * r)
        ball.y1 = ball.y0 + 2 * r
        blue.y0 = clamp(cy - r - down * apart, 0, BASE_H - 2 * r)
        blue.y1 = blue.y0 + 2 * r
        blue.x0, blue.x1 = cx - r, cx + r
        ball.side, blue.side = "red", "blue"
        self.twin = {"left": UNTIL_POINT, "ball": blue}

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

    def ball_alpha(self, ball=None):
        """How visible the ball is: a Ghost Ball fades out of sight and back at random moments.
        (Twin Balls' blue ball is never a ghost.)  A ball inside a portal can't be seen (1.8)."""
        if getattr(ball if ball is not None else self.game.ball, "transit", None):
            return 0.0
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
        items +=[(key, None, count) for key, count in paddle.charges.items()]
        return items

    def court_list(self):
        """What is on the ball and the court: [(key, seconds left or None, note)]."""
        items = []
        ball = self.game.ball
        if getattr(ball, "blazing", False):
            items.append(("fire", None, "Blazing shot"))
        if self.ghost:
            items.append(("ghost", max(0.0, self.ghost["left"]), "Vanishes and reappears at random"))
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
            items.append(("swap", UNTIL_POINT, "Soul Swap: you keep taking over each other's paddle"))
        if self.shape_shift:
            items.append(("shape", UNTIL_POINT, "Shape Shift: sizes drifting"))
        if self.curve_on:
            items.append(("curve", UNTIL_POINT, "Curveball: hits bend the way the paddle moved"))
        if self.double:
            items.append(("double", UNTIL_POINT, "This point is worth 2"))
        if self.wind:
            items.append(("wind", self.wind["left"], "Wind blowing " + ("down" if self.wind["dir"] > 0 else "up")))
        if self.cracker:
            items.append(("cracker", self.cracker["fuse"], "Firecracker: bangs when its fuse burns down"))
        if self.lantern:
            items.append(("lantern", max(0.0, self.lantern.get("left", 0.0)), "Night: lanterns only"))
        if self.portals:
            items.append(("portal", UNTIL_POINT, "Two linked portals"))
        elif self.collapsed():
            items.append(("portal", UNTIL_POINT, "The portals collapsed: black holes"))
        if any(h["kind"] == self.HOLE_TALISMAN and h["dying"] is None for h in self.holes):
            items.append(("hole", UNTIL_POINT, "Black Hole: pulls the ball in and flings it out"))
        return items

    # ---------------- Each frame of play ----------------

    def update(self, dt):
        game, ball = self.game, self.game.ball
        # While a point is announced, what lasts between points waits: Boons and Curses, Lantern
        # Night and the talismans on the court keep the time they have left for the next serve (1.8)
        between = getattr(game, "message_timer", 0) > 0
        for paddle in (game.p1, game.p2):
            for key in list(paddle.effects):
                if not between:
                    paddle.effects[key] -= dt
                if paddle.effects[key] <= 0:
                    del paddle.effects[key]

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
            if not between and self.lantern["lifting"] is None:
                self.lantern["left"] -= dt
                if self.lantern["left"] <= 0:
                    self.lantern["lifting"] = self.LANTERN_FADE[1]     # its time is up: dawn comes
        self.update_portals(dt)
        self.update_holes(dt)
        self.update_minis(dt)
        if self.update_snow(dt):
            return                          # a paddle was shoved into its goal: the point is over

        kinds = self.kinds()
        keys = {kind.key for kind in kinds}
        if kinds and not between:
            self.wait -= dt
            if self.wait <= 0:
                self.wait = self.next_wait()
                waiting = {item["kind"] for item in self.pickups}    # never two of a kind on the court
                choices = [kind for kind in kinds if self.spawnable(kind) and kind.key not in waiting]
                if choices and self.room():
                    self.spawn(random.choice(choices).key)
        for item in self.pickups:
            if not between:
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
            # its time is up: it fades back into sight, then it's a plain ball again (1.8)
            ghost["alpha"] = min(1.0, ghost["alpha"] + dt / self.GHOST_FADE)
            if ghost["alpha"] >= 1.0:
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
        for plough in self.ploughs:
            plough[2] += dt
        self.ploughs = [p for p in self.ploughs if p[2] < self.PLOUGH_TIME]
        for door in self.closing:
            door["shut"] -= dt / self.PORTAL_SHUT
        self.closing = [door for door in self.closing if door["shut"] > 0]
        for hole in self.holes:
            if hole["dying"] is not None:
                hole["dying"] -= dt
        self.holes = [h for h in self.holes if h["dying"] is None or h["dying"] > 0]
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
        elif key == "sticky":
            owner.effects[key] = rival.effects[key] = kind.seconds      # on both paddles
        elif key == "shrink":
            rival.effects[key] = kind.seconds
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
        elif key == "shape":
            self.shape_shift = True
        elif key == "curve":
            self.curve_on = True
        elif key == "double":
            self.double = True
        elif key == "wind":
            self.wind = {"left": kind.seconds, "dir": random.choice((-1, 1)), "t": 0.0}
        elif key == "cracker":
            self.cracker = {"fuse": kind.seconds, "taker": owner}      # lit as it's taken
        elif key == "lantern":
            self.lantern = {"age": 0.0, "lifting": None, "left": kind.seconds}
        elif key == "portal":
            self.open_portals(self.PORTAL_START_TALISMAN)
        elif key == "hole":
            self.open_hole()

        app = self.game.app
        app.fx.burst(item["x"], item["y"], 8, 44, owner.colour, life=(.6, 1.0))
        app.fx.spark(item["x"], item["y"], 18, FAMILY_COLOURS[kind.family], speed=380, life=.6)
        app.sound_manager.play("countdown_go.wav")
        self.popups.append([kind.name, item["x"], item["y"], 0.0, FAMILY_COLOURS[kind.family]])
        self.game.on_powerup(kind, owner)

    # ---------------- Hooks from the ball and the match ----------------

    def on_hit(self, ball, paddle, normal=(1, 0)):
        """A paddle touched the ball (called after the paddle has shaped the return)."""
        main = ball is self.game.ball          # Twin Balls' blue ball carries no goo, snow or firecracker
        self.portal_trips = 0                  # a ball looping through the portals has been played
        ball.hole_speed = None                 # (a black hole's pull counts from the speed of this hit)

        # Spirit Fire: every hit while it lasts is a blazing shot, 20% faster, but never past the
        # usual top speed (nor slower than the hit would have been without it)
        ball.blazing = False
        if self.has(paddle, "fire"):
            plain = math.hypot(ball.vx, ball.vy)
            ball.vx *= self.FIRE
            ball.vy *= self.FIRE
            serve = getattr(ball, "speed", 0)
            if serve:
                top = max(self.FIRE_TOP * MAX_BALL_SPEEDUP * serve * math.sqrt(2), plain)
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
        """The firecracker's fuse burns for 5 s of play from when it was taken, then it bangs: the
        ball shoots off at double speed at a new angle, away from whoever hit it last (or, if no
        one has since, whoever took it).  Either way it could shoot straight back at them from
        point-blank, and nearly half its points ended on the bang.  (It burned down over 3 hits
        before 1.6's playtest; a fuse you can watch is easier to play round.)"""
        cracker = self.cracker
        if not cracker:
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
        last = getattr(ball, "last_paddle", None) or cracker.get("taker")
        way = (1 if last.is_left else -1) if last is not None else random.choice((-1, 1))
        ball.vx, ball.vy = way * speed * math.cos(angle), speed * math.sin(angle)
        ball.hole_speed = None
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

    def open_portals(self, start):
        """Two linked portals open somewhere mid-court, well apart and small, each facing its own way
        (never straight up or down), and set off drifting, slowly turning."""
        game, ball = self.game, self.game.ball
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
        room = self.portal_room(start)              # as far from stones as they keep as they drift
        # Clear spots first, then two of them: (1.7) picking the first portal's spot before the
        # second's could leave nowhere far enough from it on a court with stones, and no portals
        spots = []
        for _ in range(400):
            x = random.uniform(BASE_W * 0.27, BASE_W * 0.73)
            y = random.uniform(190, BASE_H - 190)
            if math.hypot(x - bx, y - by) < 220:
                continue
            if any(o.x0 - room < x < o.x1 + room and o.y0 - room < y < o.y1 + room for o in stones):
                continue
            spots.append((x, y))
            if len(spots) == 40:
                break
        pair, far = None, -1.0                      # two at least 520 px apart, or else the farthest apart
        for i, (ax, ay) in enumerate(spots):
            for cx, cy in spots[i + 1:]:
                gap = math.hypot(ax - cx, ay - cy)
                if gap > far:
                    pair, far = ((ax, ay), (cx, cy)), gap
                if gap >= 520:
                    break
            if far >= 520:
                break
        placed = []
        for x, y in pair or ():
            while True:
                angle = random.uniform(0, math.tau)
                if abs(math.cos(angle)) >= 0.45:
                    break
            heading = random.uniform(0, math.tau)
            drift = random.uniform(*self.PORTAL_DRIFT)
            placed.append({"x": x, "y": y, "angle": angle, "r": float(start),
                           "vx": drift * math.cos(heading), "vy": drift * math.sin(heading),
                           "spin": random.choice((-1, 1)) * random.uniform(*self.PORTAL_TURN)})
        if len(placed) == 2:
            self.portals = placed
            self.portal_trips = 0
            for p in placed:
                game.app.fx.spark(p["x"], p["y"], 24, (170, 120, 255), speed = 300, life = .6)

    @classmethod
    def portal_exit(cls, angle):
        """The way a ball leaves a portal facing `angle`: that way, but never steeper than
        PORTAL_STEEPEST, as it turns through straight up or down.  (The friend's screen
        flies the ball through portals by this too.)"""
        dx, dy = math.cos(angle), math.sin(angle)
        if abs(dx) < cls.PORTAL_STEEPEST:
            dx = math.copysign(cls.PORTAL_STEEPEST, dx or 1.0)
            dy = math.copysign(math.sqrt(1 - dx * dx), dy or 1.0)
        return dx, dy

    @staticmethod
    def portal_room(r):
        """How far a portal of radius r keeps from any stone (opening, and drifting)."""
        return r + 30

    def drift_portals(self, dt):
        """The portals drift about mid-court: off the edges of their area and any stone (with room
        to spare), and apart from each other; they slowly turn."""
        lo, hi, edge = self.PORTAL_AREA
        lo, hi, top, bottom = BASE_W * lo, BASE_W * hi, edge, BASE_H - edge
        stones = [o for o in self.game.objects if getattr(o, "is_obstacle", False)]
        for door in self.portals:
            door["angle"] = (door["angle"] + door.get("spin", 0.0) * dt) % math.tau
            vx, vy = door.get("vx", 0.0), door.get("vy", 0.0)
            x, y = door["x"] + vx * dt, door["y"] + vy * dt
            if not lo <= x <= hi:
                vx, x = -vx, clamp(x, lo, hi)
            if not top <= y <= bottom:
                vy, y = -vy, clamp(y, top, bottom)
            room = self.portal_room(door.get("r", self.PORTAL_R))
            for hole in self.holes:
                # (1.8) clear of any black hole: heading towards one, it turns away
                gap_x, gap_y = door["x"] - hole["x"], door["y"] - hole["y"]
                if math.hypot(gap_x, gap_y) < room + self.HOLE_CLEAR * 0.6 and gap_x * vx + gap_y * vy < 0:
                    n = math.hypot(gap_x, gap_y) or 1.0
                    speed = math.hypot(vx, vy)
                    vx, vy = gap_x / n * speed, gap_y / n * speed
                    x, y = door["x"] + vx * dt, door["y"] + vy * dt
            for o in stones:
                near = lambda px, py: o.x0 - room < px < o.x1 + room and o.y0 - room < py < o.y1 + room
                if not near(x, y):
                    continue
                speed = math.hypot(vx, vy)
                if near(door["x"], door["y"]):
                    # already too close (a drifting stone came to it, or it grew): head straight away
                    cx, cy = (o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2
                    away = math.hypot(door["x"] - cx, door["y"] - cy) or 1.0
                    vx, vy = (door["x"] - cx) / away * speed, (door["y"] - cy) / away * speed
                    x, y = door["x"] + vx * dt, door["y"] + vy * dt
                else:
                    # bounce off the side it came at, and stay where it was
                    if door["x"] <= o.x0 - room or door["x"] >= o.x1 + room:
                        vx = -vx
                    else:
                        vy = -vy
                    x, y = door["x"], door["y"]
                break
            door["x"], door["y"], door["vx"], door["vy"] = x, y, vx, vy
        if len(self.portals) == 2:
            a, b = self.portals
            gap_x, gap_y = b["x"] - a["x"], b["y"] - a["y"]
            if math.hypot(gap_x, gap_y) < self.PORTAL_APART:
                # heading towards each other along the line between them: both turn back along it
                for door, sign in ((a, -1), (b, 1)):
                    toward = (door.get("vx", 0.0) * gap_x + door.get("vy", 0.0) * gap_y) * sign
                    if toward < 0:
                        n = math.hypot(gap_x, gap_y) or 1.0
                        ux, uy = gap_x / n, gap_y / n
                        along = door["vx"] * ux + door["vy"] * uy
                        door["vx"] -= 2 * along * ux
                        door["vy"] -= 2 * along * uy

    def update_portals(self, dt):
        """The portals drift and turn; a ball whose centre reaches one comes out of the other, at
        the same speed, the way that portal faces, and both grow a little."""
        for b in self.balls():
            if getattr(b, "transit", None):        # (a ball inside comes out even if they've closed)
                b.transit["left"] -= dt
                if b.transit["left"] <= 0:
                    self.come_out(b)
        if not self.portals:
            return
        self.drift_portals(dt)
        for door in self.portals:
            if door.get("flash"):
                door["flash"] = max(0.0, door["flash"] - dt / self.PORTAL_FLASH)
        for b in self.balls():
            b.portal_cool = max(0.0, getattr(b, "portal_cool", 0.0) - dt)
            if b.stuck or b.portal_cool > 0 or getattr(b, "transit", None):
                continue
            cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
            for i, door in enumerate(self.portals):
                if math.hypot(cx - door["x"], cy - door["y"]) > door.get("r", self.PORTAL_R) * 0.6:
                    continue
                out = self.portals[1 - i]
                # Inside for a moment (1.8), held at the portal's heart and out of sight, while the
                # way out flashes; then out of the other, a little slower each trip (never slower
                # than a serve, nor faster than it went in)
                speed = math.hypot(b.vx, b.vy)
                serve = getattr(b, "speed", 0) * math.sqrt(2)
                slower = max(speed * (1 - self.PORTAL_SLOW), min(speed, serve))
                b.transit = {"out": out, "left": self.PORTAL_TRANSIT, "speed": slower}
                r = b.width / 2
                b.x0, b.y0, b.x1, b.y1 = door["x"] - r, door["y"] - r, door["x"] + r, door["y"] + r
                b.vx = b.vy = 0.0
                out["flash"] = 1.0
                fx = self.game.app.fx
                fx.spark(door["x"], door["y"], 16, (170, 120, 255), speed = 260, life = .45)
                self.game.app.sound_manager.play("countdown_tick.wav", multiplier = 0.5)
                hook = getattr(self.game, "on_portal", None)
                if hook:
                    hook(door, out)
                if all(p.get("r", self.PORTAL_R) >= self.PORTAL_R for p in self.portals):
                    self.collapse_due = True        # full size: they collapse as this ball comes out (1.8)
                for p in self.portals:                     # both grow a little, to their full size
                    p["r"] = min(float(self.PORTAL_R), p.get("r", self.PORTAL_R) + self.PORTAL_GROW)
                self.portal_trips += 1
                if self.portal_trips >= self.PORTAL_TRIPS:
                    self.close_portals()        # round and round with nobody touching it: a loop
                    return
                break

    def transit_exit(self, ball):
        """Where a ball inside a portal will come out, and how: (x, y, vx, vy)."""
        transit = ball.transit
        out, r = transit["out"], ball.width / 2
        if "angle" in transit:                      # out of a black hole, the way it was flung (1.8)
            dx, dy = math.cos(transit["angle"]), math.sin(transit["angle"])
            reach = self.HOLE_CORE + r + 6
        else:
            dx, dy = self.portal_exit(out["angle"])
            reach = out.get("r", self.PORTAL_R) * 0.5 + r
        x = clamp(out["x"] + dx * reach, r + 2, BASE_W - r - 2)
        y = clamp(out["y"] + dy * reach, r + 2, BASE_H - r - 2)
        return x, y, transit["speed"] * dx, transit["speed"] * dy

    def come_out(self, ball):
        """Out of the far portal, the way it faces."""
        x, y, vx, vy = self.transit_exit(ball)
        out, r = ball.transit["out"], ball.width / 2
        hole = "angle" in ball.transit
        transit_speed = ball.transit["speed"]
        ball.transit = None
        ball.x0, ball.y0, ball.x1, ball.y1 = x - r, y - r, x + r, y + r
        ball.vx, ball.vy = vx, vy
        ball.portal_cool = self.PORTAL_COOL
        ball.hole_speed = None
        if hole:
            ball.hole_cool, ball.hole_time = self.HOLE_COOL, 0.0
            self.game.app.fx.spark(x, y, 30, (255, 196, 120), speed = 520, life = .55)
            self.game.app.sound_manager.play("countdown_go.wav", multiplier = 0.5)
            if out["kind"] == self.HOLE_COLLAPSE:
                self.spit(ball, out, transit_speed)
            return
        self.game.app.fx.spark(out["x"], out["y"], 22, (120, 230, 255), speed = 340, life = .5)
        if self.collapse_due and self.portals:
            self.collapse_portals()

    def close_portals(self):
        """The portals snap shut (a ball was looping through them with no paddle near).  In a Portal
        Pair match they open again at the next serve, as big as they'd grown."""
        for p in self.portals:
            self.game.app.fx.spark(p["x"], p["y"], 24, (170, 120, 255), speed = 300, life = .6)
            self.portal_grown = max(self.portal_grown, p.get("r", 0.0))
        self.shut(self.portals)
        self.portals = []
        self.portal_trips = 0
        self.collapse_due = False

    def shut(self, portals):
        """These portals shrink away rather than vanish (1.8)."""
        self.closing += [dict(p, shut = 1.0, flash = 0.0) for p in portals]

    def serve_portals(self):
        """At each serve: a Portal Pair match has its portals (opened at the first serve, and again
        after a loop shut them, never smaller than they'd grown); otherwise none stay open."""
        self.holes = []                             # (any black hole has imploded by the serve)
        self.minis = None
        if not self.settings.mode_portal_pair:
            self.portals = []
        elif not self.portals:
            self.open_portals(max(self.PORTAL_START, self.portal_grown))

    # ---------------- Black Hole ----------------

    @classmethod
    def hole_style(cls, kind):
        """How far a black hole of this kind pulls, how hard, and the radius of its heart."""
        if kind == cls.HOLE_MINI:
            return cls.MINI_REACH, cls.MINI_PULL, cls.MINI_CORE
        return cls.HOLE_REACH, cls.HOLE_PULL, cls.HOLE_CORE

    @classmethod
    def swallows(cls, hole):
        """Can a ball fall into this hole now?  Not Portal Pair's before it has formed (nor once it
        has a ball inside), nor a mini black hole while it's faint, fading in or out."""
        if hole["kind"] == cls.HOLE_COLLAPSE:
            return hole.get("age", 0.0) >= cls.COLLAPSE_TIME and not hole.get("full")
        if hole["kind"] == cls.HOLE_MINI:
            return hole.get("power", 1.0) >= 0.5
        return True

    def collapsed(self):
        """Portal Pair's portals have collapsed this point: its black hole, then the mini ones."""
        return bool(self.minis) or any(h["kind"] in (self.HOLE_COLLAPSE, self.HOLE_MINI) and h["dying"] is None
                                       for h in self.holes)

    @classmethod
    def hole_pull(cls, hole, x, y, pace = 1.0):
        """A black hole's pull on a ball centred at (x, y), in px/s^2 towards its heart: harder the
        closer in, nothing past its reach.  `pace` is the ball's speed over a serve's: a faster
        ball is pulled harder, so a pull still bends a quick shot (if less than a slow one).  (The
        friend's screen and the AI reckon it by this too.)"""
        dx, dy = hole["x"] - x, hole["y"] - y
        d = math.hypot(dx, dy)
        reach, pull, core = cls.hole_style(hole["kind"])
        if d >= reach or d < 1e-6:
            return 0.0, 0.0
        k = (1 - d / reach) ** 2 * cls.HOLE_NEAR / max(d, core) * pull * hole.get("power", 1.0) * max(0.25, pace)
        return dx / d * k, dy / d * k

    @classmethod
    def gravity(cls, holes, x, y, vx, vy, dt, entry, serve):
        """One step of the black holes' gravity on a ball centred at (x, y) that came into their
        pull at `entry` px/s (1.8 playtest: a pull that only bent its path didn't feel like gravity).
        It's pulled towards each heart, speeding up as it falls in; near a heart its sideways speed
        bleeds away, so it spirals in rather than sweeping past; and it's never more than
        HOLE_FASTEST times as fast as it came in (nor past the usual top speed, unless it came in
        faster).  Answers the new (vx, vy), and whether any pull reached it.  (The friend's screen
        and the AI work it out by this too.)"""
        pace = entry / (serve * math.sqrt(2)) if serve else 1.0
        pulled = False
        for hole in holes:
            ax, ay = cls.hole_pull(hole, x, y, pace)
            if not (ax or ay):
                continue
            pulled = True
            reach = cls.hole_style(hole["kind"])[0]
            d = math.hypot(hole["x"] - x, hole["y"] - y)
            ux, uy = (hole["x"] - x) / d, (hole["y"] - y) / d
            vx, vy = vx + ax * dt, vy + ay * dt
            near = (1 - d / reach) ** 2 * hole.get("power", 1.0)
            bleed = (vy * ux - vx * uy) * (math.exp(-cls.HOLE_SWIRL * near * dt) - 1)
            vx, vy = vx - uy * bleed, vy + ux * bleed
        if pulled:
            top = MAX_BALL_SPEEDUP * serve * math.sqrt(2) if serve else math.inf
            fastest = max(entry, min(entry * cls.HOLE_FASTEST, top))
            speed = math.hypot(vx, vy)
            if speed > fastest:
                vx, vy = vx * fastest / speed, vy * fastest / speed
        return vx, vy, pulled

    @staticmethod
    def pace_of(vx, vy, serve):
        """A ball's speed over a serve's (`serve` being the serve's speed on each axis)."""
        return math.hypot(vx, vy) / (serve * math.sqrt(2)) if serve else 1.0

    @staticmethod
    def bend(vx, vy, ax, ay, dt):
        """Turn a ball's path by a pull, keeping its speed (as the wind does: speed it gained would
        come straight back out of the next hit as a faster shot)."""
        speed = math.hypot(vx, vy)
        vx, vy = vx + ax * dt, vy + ay * dt
        turned = math.hypot(vx, vy)
        if turned:
            vx, vy = vx * speed / turned, vy * speed / turned
        return vx, vy

    @classmethod
    def falls_in(cls, hole, x, y, vx, vy, dt, r = 0.0):
        """Does a ball of radius r centred at (x, y) touch this hole's heart in the next `dt` (so a
        fast one can't skip across it)?"""
        _reach, _pull, core = cls.hole_style(hole["kind"])
        hx, hy = hole["x"] - x, hole["y"] - y
        span = vx * vx + vy * vy
        k = clamp((hx * vx + hy * vy) / span, 0.0, dt) if span else 0.0
        return math.hypot(hx - vx * k, hy - vy * k) <= core + r

    def pulling(self):
        """The black holes pulling now (not opening from nothing, nor imploding)."""
        return [h for h in self.holes if h["power"] > 0 and h["dying"] is None]

    def open_hole(self):
        """Black Hole: one opens mid-court, clear of stones, portals, other holes and the ball (or
        as clear as it can find)."""
        game, ball = self.game, self.game.ball
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
        best, best_room = None, -math.inf
        for _ in range(300):
            x = random.uniform(BASE_W * 0.32, BASE_W * 0.68)
            y = random.uniform(230, BASE_H - 230)
            room = math.hypot(x - bx, y - by) - 120
            for o in stones:
                room = min(room, math.hypot(x - clamp(x, o.x0, o.x1), y - clamp(y, o.y0, o.y1)))
            for door in self.portals:
                room = min(room, math.hypot(x - door["x"], y - door["y"]) - door.get("r", self.PORTAL_R))
            for hole in self.holes:
                room = min(room, math.hypot(x - hole["x"], y - hole["y"]) - self.HOLE_CLEAR)
            if room > best_room:
                best, best_room = (x, y), room
            if room >= self.HOLE_CLEAR:
                break
        x, y = best
        self.holes.append({"x": x, "y": y, "kind": self.HOLE_TALISMAN, "age": 0.0, "power": 0.0,
                           "spin": random.choice((-1, 1)), "way": None, "flash": 0.0, "dying": None})
        fx = game.app.fx
        fx.spark(x, y, 40, (170, 110, 255), speed = 520, life = .7)
        fx.spark(x, y, 20, (255, 190, 120), speed = 300, life = .6)
        renderer = getattr(game.app, "renderer", None)
        if renderer is not None:
            renderer.shake(8, 0.3)

    def update_holes(self, dt):
        """Black holes open, pull the balls, and swallow any that reach their heart (a ball circling
        in a pull too long is drawn in).  Each ball's speed stays as it was: only its path bends."""
        if not self.holes:
            return
        for hole in self.holes:
            hole["flash"] = max(0.0, hole.get("flash", 0.0) - dt / self.HOLE_FLARE)
            if hole["dying"] is not None:
                continue
            hole["age"] += dt
            if hole["kind"] == self.HOLE_COLLAPSE:
                hole["power"] = min(1.0, hole["age"] / self.COLLAPSE_TIME)    # its pull grows as it collapses
            elif hole["kind"] == self.HOLE_MINI:
                hole["left"] -= dt
                hole["power"] = clamp(min(hole["age"], hole["left"]) / self.MINI_FADE, 0.0, 1.0)
            else:
                hole["power"] = min(1.0, hole["age"] / self.HOLE_OPEN)
        self.holes = [h for h in self.holes if h["kind"] != self.HOLE_MINI or h["dying"] is not None or h["left"] > 0]
        pulling = self.pulling()
        if not pulling:
            return
        for b in self.balls():
            if b.stuck or getattr(b, "transit", None):
                continue
            cool = getattr(b, "hole_cool", 0.0)
            if cool > 0:
                b.hole_cool = cool - dt                # just flung out: not pulled back in at once
                continue
            cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
            r = b.width / 2
            into = next((h for h in pulling if self.swallows(h) and self.falls_in(h, cx, cy, b.vx, b.vy, dt, r)), None)
            if into:
                self.swallow(b, into)
                continue
            entry = getattr(b, "hole_speed", None) or math.hypot(b.vx, b.vy)
            vx, vy, pulled = self.gravity(pulling, cx, cy, b.vx, b.vy, dt, entry, getattr(b, "speed", 0))
            if not pulled:
                self.leave_pull(b)
                continue
            b.hole_speed = entry
            b.hole_time = getattr(b, "hole_time", 0.0) + dt
            ready = [h for h in pulling if self.swallows(h)]
            if b.hole_time > self.HOLE_TRAP and ready:
                self.swallow(b, min(ready, key = lambda h: math.hypot(cx - h["x"], cy - h["y"])))
                continue
            b.vx, b.vy = vx, vy

    @staticmethod
    def leave_pull(b):
        """Out of every pull: as fast as it came in again (gravity sped it up falling in, and slowed
        it climbing out; this squares it), and its clocks reset."""
        entry = getattr(b, "hole_speed", None)
        speed = math.hypot(b.vx, b.vy)
        if entry and speed:
            b.vx, b.vy = b.vx * entry / speed, b.vy * entry / speed
        b.hole_speed, b.hole_time = None, 0.0

    def fling_angle(self, hole, way):
        """The way a black hole flings out what it swallowed: on towards the same side (`way`, 1 for
        right), at any angle, but never steeper than a portal sends a ball (straight up or down, it
        would bounce between top and bottom).  (Any way at all, it soaked up attacking shots and
        sent half of them back: computer v computer points ran past two minutes.)"""
        steepest = math.acos(self.PORTAL_STEEPEST)
        angle = random.uniform(-steepest, steepest)
        return angle if way > 0 else math.pi - angle

    def swallow(self, b, hole):
        """A ball falls into a black hole: held at its heart, out of sight, for a moment (the heart
        pulses; the talisman's showed an arrow the way out until Rowan's playtest); then flung out
        as fast as it came into the pull (never slower than a serve)."""
        coming = getattr(b, "hole_speed", None) or math.hypot(b.vx, b.vy)     # (before it fell)
        serve = getattr(b, "speed", 0) * math.sqrt(2)
        speed, hold = max(coming, serve), self.HOLE_HOLD
        way = 1 if b.vx > 0 else -1 if b.vx < 0 else random.choice((-1, 1))
        if hole["kind"] == self.HOLE_MINI:
            # a mini black hole is a portal too: a little slower out, as out of a portal (never
            # slower than a serve, nor faster than it went in)
            speed, hold = max(coming * (1 - self.PORTAL_SLOW), min(coming, serve)), self.MINI_HOLD
        elif hole["kind"] == self.HOLE_COLLAPSE:
            way = self.scoring_way(b)               # Portal Pair's: see spit
            hole["full"] = True
        angle = self.fling_angle(hole, way)
        b.transit = {"out": hole, "left": hold, "speed": speed, "angle": angle}
        b.hole_speed = None
        r = b.width / 2
        b.x0, b.y0, b.x1, b.y1 = hole["x"] - r, hole["y"] - r, hole["x"] + r, hole["y"] + r
        b.vx = b.vy = 0.0
        b.hole_time = 0.0
        hole["way"], hole["flash"] = angle, 1.0
        app = self.game.app
        app.fx.spark(hole["x"], hole["y"], 26, (190, 130, 255), speed = 240, life = .4)
        app.sound_manager.play("countdown_tick.wav", multiplier = 0.6)

    def hole_path(self, x, y, vx, vy, r, line_x, judged = 1.0, field = 0.0, most = 3.0):
        """Where a ball flying from (x, y) at (vx, vy) reaches x = line_x, pulled by the black holes
        (each taken as `judged` times as strong as it is) and pushed by `field` (the wind):
        (seconds, y, False), or (seconds, None, True) if it falls into a hole first, or None if it
        doesn't get there within `most` seconds.  For the AI."""
        holes = [dict(hole, power = hole["power"] * judged) for hole in self.pulling()]
        step = 1 / 60
        way = 1 if line_x > x else -1
        swallows = [self.swallows(hole) for hole in holes]
        serve = getattr(self.game.ball, "speed", 0)
        entry = math.hypot(vx, vy)
        t = 0.0
        for _ in range(int(most / step)):
            for hole, can in zip(holes, swallows):
                if can and self.falls_in(hole, x, y, vx, vy, step, r):
                    return t, None, True
            vx, vy, pulled = self.gravity(holes, x, y, vx, vy, step, entry, serve)
            if not pulled:
                speed = math.hypot(vx, vy)
                if speed:
                    vx, vy = vx * entry / speed, vy * entry / speed
            if field:
                vx, vy = self.bend(vx, vy, 0.0, field, step)
            x, y = x + vx * step, y + vy * step
            if y < r:
                y, vy = 2 * r - y, abs(vy)
            elif y > BASE_H - r:
                y, vy = 2 * (BASE_H - r) - y, -abs(vy)
            t += step
            if (x - line_x) * way >= 0:
                return t, y, False
        return None

    # ---------------- Portal Pair's collapse ----------------

    def collapse_portals(self):
        """Full-size portals collapse (1.8): over COLLAPSE_TIME they flare, spiral in round each
        other and merge into a black hole between them, its pull growing as they do; see spit."""
        a, b = self.portals
        stones = [o for o in self.game.objects if getattr(o, "is_obstacle", False)]
        hx, hy = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
        for k in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8):            # (between them, clear of any stone)
            x, y = a["x"] + (b["x"] - a["x"]) * k, a["y"] + (b["y"] - a["y"]) * k
            if all(not (o.x0 - 70 < x < o.x1 + 70 and o.y0 - 70 < y < o.y1 + 70) for o in stones):
                hx, hy = x, y
                break
        self.holes.append({"x": hx, "y": hy, "kind": self.HOLE_COLLAPSE, "age": 0.0, "power": 0.0,
                           "spin": 1 if a.get("spin", 1.0) >= 0 else -1, "way": None, "flash": 0.0,
                           "dying": None, "doors": [(door["x"] - hx, door["y"] - hy) for door in (a, b)]})
        self.portals = []
        self.portal_trips = 0
        self.collapse_due = False
        self.portal_grown = 0.0                     # (a Portal Pair match's open small again at the next serve)
        app = self.game.app
        for door in (a, b):
            app.fx.spark(door["x"], door["y"], 30, (210, 170, 255), speed = 360, life = .7)
        app.sound_manager.play("countdown_tick.wav")

    def spit(self, ball, hole, speed):
        """Portal Pair's black hole spits out what it swallowed: a lone ball comes out as Twin Balls,
        red heading for Blue's goal and blue for Red's (where each can score), each at any angle
        (never straight up or down) and at half its speed, as Twin Balls split (never slower than
        half a serve).  With two balls in play already, the ball comes out alone, heading for the
        goal it can score in.  Then the hole implodes, and mini black holes come and go till the
        point ends.  (Until Rowan's playtest, two arrows on the hole showed the ways out.)"""
        game = self.game
        app = game.app
        if ball is game.ball and self.twin is None:
            blue = self.new_blue(ball)
            each = max(speed * 0.5, ball.speed * math.sqrt(2) * 0.5)
            r = ball.width / 2
            blues_goal = self.scoring_way(ball)
            for b, way, tint in ((ball, blues_goal, (255, 120, 100)), (blue, -blues_goal, (110, 170, 255))):
                angle = self.fling_angle(hole, way)
                dx, dy = math.cos(angle), math.sin(angle)
                cx = hole["x"] + dx * (self.HOLE_CORE + r + 6)
                cy = clamp(hole["y"] + dy * (self.HOLE_CORE + r + 6), r + 2, BASE_H - r - 2)
                b.x0, b.y0, b.x1, b.y1 = cx - r, cy - r, cx + r, cy + r
                b.vx, b.vy = each * dx, each * dy
                b.portal_cool, b.hole_cool, b.hole_time = self.PORTAL_COOL, self.HOLE_COOL, 0.0
                for n in range(1, 5):                                 # streaks the way it goes
                    app.fx.spark(cx + dx * 30 * n, cy + dy * 30 * n, 6, tint, speed = 160, life = .45)
            ball.side, blue.side = "red", "blue"
            self.twin = {"left": UNTIL_POINT, "ball": blue}
        hole["dying"], hole["power"] = self.HOLE_IMPLODE, 0.0
        self.minis = {"next": self.MINI_FIRST}
        renderer = getattr(app, "renderer", None)
        if renderer is not None:
            renderer.shake(10, 0.3)

    def scoring_way(self, ball):
        """Which way (1 right, -1 left) the goal this ball can score in lies: Twin Balls' blue ball
        scores in Red's goal, and any other in Blue's.  (A Switch moves the goals with the colours.)"""
        blues_goal = -1 if self.game.p1.colour == "blue" else 1
        return -blues_goal if getattr(ball, "side", None) == "blue" else blues_goal

    def update_minis(self, dt):
        """After the collapse, mini black holes fade in at random spots every so often, up to
        MINI_MOST at once, until the point ends."""
        if not self.minis:
            return
        self.minis["next"] -= dt
        if self.minis["next"] > 0:
            return
        self.minis["next"] = random.uniform(*self.MINI_EVERY)
        if sum(1 for h in self.holes if h["kind"] == self.HOLE_MINI and h["dying"] is None) < self.MINI_MOST:
            self.open_mini()

    def open_mini(self):
        """A mini black hole fades in, standing still: well out from both goals, clear of the stones,
        the balls and the other holes (or as clear as it can find)."""
        game = self.game
        stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
        balls = [((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2) for b in self.balls()]
        best, best_room = None, -math.inf
        for _ in range(80):
            x = random.uniform(self.MINI_GOAL_GAP, BASE_W - self.MINI_GOAL_GAP)
            y = random.uniform(150, BASE_H - 150)
            room = min([math.hypot(x - bx, y - by) - 200 for bx, by in balls] +
                       [math.hypot(x - clamp(x, o.x0, o.x1), y - clamp(y, o.y0, o.y1)) - 70 for o in stones] +
                       [math.hypot(x - h["x"], y - h["y"]) - 300 for h in self.holes] + [math.inf])
            if room > best_room:
                best, best_room = (x, y), room
            if room >= 0:
                break
        x, y = best
        spin = random.choice((-1, 1))
        self.holes.append({"x": x, "y": y, "kind": self.HOLE_MINI, "age": 0.0, "power": 0.0, "spin": spin,
                           "way": None, "flash": 0.0, "dying": None, "left": random.uniform(*self.MINI_LIFE)})

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

    def plough(self, ball, stone, data):
        """A big Snowball meeting a Tombstone's stone (1.8): it ploughs straight on through, losing
        a little speed, and the stone bursts apart.  Answers True if it did (False: it isn't big
        enough yet, and smashes the stone with a bounce)."""
        if not self.snow or self.snow["size"] < self.PLOUGH_SIZE:
            return False
        vx, vy = data.get("before", {}).get(ball, (ball.vx, ball.vy))
        ball.vx, ball.vy = vx * self.PLOUGH_KEEP, vy * self.PLOUGH_KEEP
        stone.crumble()
        cx, cy = (stone.x0 + stone.x1) / 2, (stone.y0 + stone.y1) / 2
        self.ploughs.append([cx, cy, 0.0])
        app = self.game.app
        app.fx.spark(cx, cy, 36, (236, 246, 255), speed = 640, life = .9)
        app.fx.spark(cx, cy, 20, (176, 160, 130), speed = 460, life = 1.0)
        renderer = getattr(app, "renderer", None)
        if renderer is not None:
            renderer.shake(12, 0.3)
        return True

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
            game.app.fx.burst(centre, (paddle.y0 + paddle.y1) / 2, 8, 44, paddle.colour,
                              life=(.5, .9))
            paddle.x0, paddle.x1 = x, x + paddle.width
            paddle.vx = 0.0
            paddle.ai.reset()

    def on_point(self):
        """A point ends whatever was riding on the ball, and clears the court: Open Court's wall
        goes back up, Tombstones sink away and the Snowball melts back into a ball.  What acts on
        both players (Sticky Goo, a Ghost Ball, the wind) ends too, so the next serve is a plain
        one.  Each player's own Boons and Curses carry on with the time they had left, and so do
        Lantern Night and the talismans waiting on the court (1.8).  Soul Swap ends, and whoever it
        left on the other's paddle goes back to their own (unless it's a Switch match: the
        switch goes on from where they are).  The wait for the next talisman carries on where it
        was (restarted at every point, quick points never got one)."""
        from objects.obstacle import Obstacle
        self.ghost = None
        self.wind = None
        for paddle in (self.game.p1, self.game.p2):
            paddle.effects.pop("sticky", None)
            paddle.charges.pop("teleport", None)        # an unused Safety Teleport is lost
        ball = self.game.ball
        ball.blazing = False
        ball.stuck = None
        ball.unstick = 0.0
        self.blink = None
        self.snow = None
        self.end_twin()
        if self.switch_plus and self.soul_swaps % 2 and not self.settings.switching:
            self.game.soul_undo = True              # (Hu_Taong.reset_round: back before the serve)
        self.switch_plus = False
        self.soul_swaps = 0
        if self.shape_shift:
            self.shape_shift = False
            self.game.settling = self.game.SETTLE   # sizes ease back to normal for the serve (1.8)
        self.curve_on = False
        self.double = False
        self.cracker = None
        # court stones broken or chipped during the point stand whole again for the next serve
        for stone in self.game.objects:
            if getattr(stone, "is_obstacle", False) and stone not in self.tombs and \
                    (stone.broken or stone.hp < stone.max_hp):
                stone.restore()
        if not self.settings.mode_portal_pair:
            self.shut(self.portals)
            self.portals = []                       # the talisman's last the point; the mode's, the match
        self.portal_trips = 0
        for hole in self.holes:                     # black holes implode (1.8)
            if hole["dying"] is None:
                hole["dying"] = self.HOLE_IMPLODE
                hole["power"] = 0.0
        for b in self.balls():
            b.hole_cool = b.hole_time = 0.0
            b.hole_speed = None
        self.collapse_due = False
        self.minis = None                           # (no more mini black holes)
        for b in self.balls():
            b.curve = 0.0
        for paddle in (self.game.p1, self.game.p2):
            paddle.shoved = 0.0
        for tomb in self.tombs:
            tomb.life = min(tomb.life, Obstacle.SINK)
        if self.wall_down > 0:
            self.wall_down = 0.0
            self.send_home()

    def swap_owners(self):
        """Switch: players take each other's paddles, and their power-ups go with them."""
        a, b = self.game.p1, self.game.p2
        a.effects, b.effects = b.effects, a.effects
        a.charges, b.charges = b.charges, a.charges

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
        self.lock_aim(ball.stuck)
        self.game.app.sound_manager.play("countdown_tick.wav", multiplier = 0.5)
        self.game.on_stick(paddle)

    @staticmethod
    def sling_angle(paddle, stuck=None):
        """Sticky Goo: the angle a stuck ball is slung at.  The paddle's movement aims it (moving up
        slings it up, as far as the steepest return angle); held still, it goes as it was returned.
        Once the aim has locked (AIM_LOCK before it goes), that's where it goes."""
        if stuck and "aim" in stuck:
            return stuck["aim"]
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

    def lock_aim(self, stuck):
        """Sticky Goo: from AIM_LOCK before it's slung, the aim holds where it is, so a last-moment
        fake no longer changes where it goes (1.8)."""
        if "aim" not in stuck and stuck["left"] <= self.AIM_LOCK:
            stuck["aim"] = self.sling_angle(stuck["paddle"], stuck)

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
        self.lock_aim(stuck)
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
            if getattr(paddle, "remote", False) and getattr(game, "net", None):
                continue                    # online, the friend's own screen judges their teleport (see apply_claim)
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

    @staticmethod
    def covered(paddle, ball):
        """Would the paddle stop the ball from where it is now?  (Online, the friend's screen asks
        it too, of its own paddle and ball.)"""
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
        self.teleported(paddle, old)

    def teleported(self, paddle, old):
        """The paddle has blinked from `old` (its centre) to where it is: the charge is spent, with
        a flash at both ends, the sound and the popup."""
        app = self.game.app
        cy = (paddle.y0 + paddle.y1) / 2
        paddle.charges["teleport"] -= 1
        if not paddle.charges["teleport"]:
            del paddle.charges["teleport"]
        tint = paddle.colour
        for x, y in (old, ((paddle.x0 + paddle.x1) / 2, cy)):
            app.fx.burst(x, y, 10, 48, tint, life=(.5, .9))
        app.sound_manager.play("hmyoop!.wav")
        self.popups.append(["Safety Teleport!", (paddle.x0 + paddle.x1) / 2, paddle.y0 - 20, 0.0,
                            FAMILY_COLOURS["Boon"]])
        self.game.on_teleport(paddle)
