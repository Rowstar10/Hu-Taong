"""What a match sounds like (1.9, Rowan's 1.9 plan, phase 1): the ball off each kind of surface, each
talisman as it's taken, and the big moment of the talismans that have one.

The match plays each of these as it happens and records it as an event (game/replay.py), and a
friend's screen online and a replay play the event's sound from there: the same sound, heard once
by each player.  Everything goes through SoundManager.play, so the Effects and Master sliders and
the mute buttons apply.  The files are in Resources/Sounds/Match (Kenney's CC0 packs, and tunes made
for Hu Taong: see CREDITS.md).  The paddle hits ("Hu", "Tao"), the countdown, scoring, winning, the
menus and the Black Hole's hum are as they were (see SoundManager and HoleSounds).
"""
import math
import random
import time

FOLDER = "Match"

# What the ball bounced off, as a "wall" or "stone" event's third value (events from before 1.9 have
# none: those were the top and bottom walls and tombstones, which it falls back to).  (The Middle
# Wall only stops paddles: the ball goes through it, so it has no sound.)
EDGE, GOAL, PRACTICE = 0, 1, 2      # "wall": the top or bottom of the court, a Twin Balls goal, Practice's wall
TOMB, GATE, PILLAR = 0, 1, 2        # "stone": a tombstone, a Ferry Gate, Narrow Pass's long walls
WALL_SOUNDS = {EDGE: "edge", GOAL: "goal", PRACTICE: "pillar"}
STONE_SOUNDS = {TOMB: "tomb", GATE: "gate", PILLAR: "pillar"}
STONE_KINDS = {"tomb": TOMB, "gate": GATE, "wall": PILLAR}       # Obstacle.kind -> the sound's code

# Each sound: (how many takes of it there are, picked at random; its level, a share of the effects slider)
SOUNDS = {
    "edge": (3, 0.8), "goal": (2, 0.9),
    "tomb": (3, 0.9), "gate": (3, 0.9), "pillar": (3, 0.9),
    "chip": (2, 0.8), "crumble": (1, 0.9),
    "portal_in": (1, 0.7), "portal_out": (1, 0.7),
    "hole_fling": (1, 0.8),
    "plough": (1, 0.9), "shove": (1, 0.8),
    "goo_stick": (1, 0.8), "goo_sling": (1, 0.7),
    "tomb_sink": (1, 0.8), "blaze": (1, 0.8), "blink": (1, 0.8),
}
TALISMAN_LEVEL = 0.75               # each talisman's pickup (talisman_<key>.wav)

# The events that are a talisman's moment, and their sounds
MOMENTS = {
    "chip": "chip",                 # a stone chipped (Spirit Fire, the Snowball)...
    "crumble": "crumble",           # ...and broken
    "portal": "portal_in",          # Portal Pair: into one...
    "portal_out": "portal_out",     # ...and out of the other
    "fling": "hole_fling",          # a Black Hole flings a ball out
    "plough": "plough",             # the Snowball ploughs through a stone...
    "shove": "shove",               # ...and shoves back the paddle that hit it
    "stick": "goo_stick",           # Sticky Goo: the ball sticks...
    "sling": "goo_sling",           # ...and is slung off
    "sink": "tomb_sink",            # Tombstones sink away as the point ends
    "blaze": "blaze",               # Spirit Fire: a blazing shot
    "blink": "blink",               # Blink Ball hops
}
# Moments whose sounds were already in the game, heard online and in replays since 1.9
OLD_SOUNDS = {
    "bang": ("firecracker_bang.wav", 1.0),      # the Firecracker's bang
    "armed": ("countdown_tick.wav", 1.0),       # a mid-rally swap is armed (Soul Swap)
}

AGAIN = 0.05        # seconds: the same sound again this soon isn't played (a ball rattling in a corner)
heard = {}          # sound -> when it was last played (time.perf_counter)


def force(ball):
    """0-1: how hard the ball is going, from a serve's speed (0) to three and a half times it (1).
    Bounces are louder the harder it's going."""
    serve = getattr(ball, "speed", 0) * math.sqrt(2)
    if not serve:
        return 0.5
    return max(0.0, min(1.0, (math.hypot(ball.vx, ball.vy) / serve - 1) / 2.5))


def surface(other):
    """The code for what the ball bounced off (see above)."""
    if getattr(other, "is_obstacle", False):
        return STONE_KINDS.get(getattr(other, "kind", "tomb"), TOMB)
    if getattr(other, "is_goal", False):
        return GOAL
    if getattr(other, "practice", False):
        return PRACTICE
    return EDGE


def file_name(sound, take = 1):
    takes = SOUNDS[sound][0]
    return f"{FOLDER}/{sound}_{take}.wav" if takes > 1 else f"{FOLDER}/{sound}.wav"


def files():
    """Every file these sounds use."""
    from game.powerups import KINDS
    names = [file_name(s, k) for s, (takes, _) in SOUNDS.items() for k in range(1, takes + 1)]
    return names + [talisman_file(kind.key) for kind in KINDS]


def talisman_file(key):
    return f"{FOLDER}/talisman_{key}.wav"


def sound(app, name, level, key = None):
    """Play one file, unless the same sound (`key`, any of its takes) played a moment ago."""
    key = key or name
    now = time.perf_counter()
    if now - heard.get(key, -1.0) < AGAIN:
        return None
    heard[key] = now
    return app.sound_manager.play(name, multiplier = level)


def talisman(app, key):
    """A talisman taken."""
    if key:
        return sound(app, talisman_file(key), TALISMAN_LEVEL)


def bounce(app, sound_key, values):
    takes, level = SOUNDS[sound_key]
    hard = values[3] if len(values) > 3 else 0.5
    return sound(app, file_name(sound_key, random.randint(1, takes)), level * (0.5 + 0.5 * hard), sound_key)


def play(app, kind, values = ()):
    """The sound of one event (game/replay.py's), if it has one here.  Answers its channel, or None."""
    try:
        if kind == "wall":
            return bounce(app, WALL_SOUNDS.get(int(values[2]) if len(values) > 2 else EDGE, "edge"), values)
        if kind == "stone":
            return bounce(app, STONE_SOUNDS.get(int(values[2]) if len(values) > 2 else TOMB, "tomb"), values)
        if kind in OLD_SOUNDS:
            return sound(app, *OLD_SOUNDS[kind])
        name = MOMENTS.get(kind)
        if name:
            takes, level = SOUNDS[name]
            return sound(app, file_name(name, random.randint(1, takes)), level, name)
    except (IndexError, TypeError, ValueError):
        pass                    # a damaged event is skipped
    return None


def happen(game, kind, *values):
    """Something worth hearing happened in a match: recorded (see Hu_Taong.moment) and heard here.
    A game without a recorder just plays it."""
    moment = getattr(game, "moment", None)
    if moment is not None:
        return moment(kind, *values)
    return play(game.app, kind, values)
