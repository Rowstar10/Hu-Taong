import copy
import math
import random
from pathlib import Path

import pygame

from config import IMAGE_DIR
from core.platform import ANDROID, refresh_rate
from game import courts
from game.powerups import KINDS as POWERUP_KINDS

def find_backgrounds():
    numbered = {}
    for path in IMAGE_DIR.glob("bg*.*"):
        number = path.stem[2:]
        if number.isdigit():
            numbered[int(number)] = path.name
    return [numbered[number] for number in sorted(numbered)]

class Settings:
    """Match: the rules of a match, the same for both players (online, the host's).  The rest
    are each player's own: Gameplay (controls), Display, Audio and UI (`interface`)."""

    def __init__(self, app):
        self.app = app
        self.match = MatchSettings(app)
        self.gameplay = GameplaySettings(app)
        self.display = DisplaySettings(app)
        self.audio = AudioSettings(app)
        self.interface = InterfaceSettings(app)
        self.online = OnlineSettings(app)

    def group_of(self, name):
        """The group a setting belongs to (each name is in one group only), or None."""
        for group in (self.match, self.gameplay, self.display, self.audio, self.interface):
            if name in vars(group):
                return group
        return None


class OnlineSettings:
    """Which server online games find each other through: the free public ones, or your own
    (any MQTT broker; see server/hutaong_server.py).  Both players need the same one."""

    def __init__(self, app):
        self.app = app
        self.own_server = False
        self.server_address = ""     # like example.com or 203.0.113.7:1883
        self.server_user = ""        # if the server asks for a login
        self.server_password = ""

    def apply(self):
        from core import rooms
        rooms.use_server(self.server_address if self.own_server else None, self.server_user, self.server_password)

class MatchSettings:
    """The rules of a match (Settings > Match, and Match Setup): the same for both players."""

    # Game modes, any of them together (see reset).  Chaos and Switch each come at a timing.
    MODES = ("chaos", "switch", "curveball", "lantern_night", "twin_ball", "talisman_rush", "black_hole")
    # (1.9, Rowan: Chaos is called Shape Shift, Switch Soul Swap and Talisman Rush CHAOS on screen.
    # Their settings keep their old names, so every version still reads the one save.)
    MODE_NAMES = {"chaos": "Shape Shift", "switch": "Soul Swap", "curveball": "Curveball",
                  "lantern_night": "Lantern Night", "twin_ball": "Twin Ball", "talisman_rush": "CHAOS",
                  "black_hole": "Black Hole"}
    CHAOS_TIMINGS = ("Every point", "Constant drift")
    SWITCH_TIMINGS = ("Every point", "Mid-rally")
    # How a ball comes off a paddle (1.8, see objects/paddle.py): 1.7's engine; classic Pong (angle
    # by where it meets the paddle, a little faster every hit); or Hu Taong 0.9's
    PHYSICS = ("Current", "Classic", "v0.9")

    def __init__(self, app):
        self.app = app

        # Paddle
        self.paddle_width_min = 20
        self.paddle_width_max = 60
        self.paddle_width_range = self.paddle_width_max - self.paddle_width_min

        self.paddle_height_min = 100
        self.paddle_height_max = 300
        self.paddle_height_range = self.paddle_height_max - self.paddle_height_min

        self.paddle_speed_min = 1000
        self.paddle_speed_max = 2000
        self.paddle_speed_range = self.paddle_speed_max - self.paddle_speed_min

        # Ball
        self.ball_diameter_min = 20
        self.ball_diameter_max = 100
        self.ball_diameter_range = self.ball_diameter_max - self.ball_diameter_min

        self.ball_speed_min = 200
        self.ball_speed_max = 800
        self.ball_speed_range = self.ball_speed_max - self.ball_speed_min

        # Game pace: the whole match runs at this speed (ball, paddles, AI, Chaos timers)
        self.pace_min = 0.5
        self.pace_max = 1.5
        self.pace_range = self.pace_max - self.pace_min

        # Match rules
        self.winning_scores = [3, 5, 11, 15, 21, "Endless Mode"]

        # AI
        self.ai_difficulties = ["Baby", "Easy", "Normal", "Hard", "Insane"]
        self.ai_styles = ["Balanced", "Guardian", "Striker", "Trickster"]

        # Power-ups
        self.powerup_rate_options = ["Rare", "Normal", "Frequent"]    # (Chaotic is CHAOS's own since 1.9)
        self.at_once_options = [1, 2, 3]      # talismans in play at once (1.8)

        # Courts: the stones a match starts with (see game/courts.py); the last one is Random
        self.court_options = courts.NAMES

        # The countdown before each serve, in seconds
        self.countdown_options = [3, 2, 1]

        self.reset()

    def reset(self):
        self.reset_ball_and_paddles()
        self.pace = 1.0
        self.physics = 0             # PHYSICS[physics]: how a ball comes off a paddle
        self.speed_cap = False       # a paddle can only pass on so much of its speed to the ball

        # Match setup (chosen on the Match Setup screen)
        self.vs_ai = True            # True: you play one paddle and the AI takes the other.
        self.play_as_blue = False    # Which paddle is yours vs the AI (Red: W A S D, Blue: Arrow Keys).

        self.winning_score_index = 2
        self.win_by_two = True
        self.middle_wall = True      # False: paddles may cross the centre line
        self.ai_difficulty = 2
        self.ai_style = 0
        self.adaptive_ai = False

        self.countdown = 0           # the serve countdown: 3 s

        # Game modes (Match Setup), any of them together.  Each mode remembers its timing while off.
        # Chaos, every point: new random sizes and speeds for the ball and paddles each point (rolled
        # into the match's own copy of the rules: see copy).
        # Chaos, constant drift: Shape Shift's drift for the whole match, sizes only.
        self.mode_chaos = False
        self.chaos_timing = 0        # 0 every point, 1 constant drift
        # Switch: each player takes over the other's paddle and goal, keeping their own keys and score
        self.mode_switch = False
        self.switch_timing = 0       # 0 after every point, 1 mid-rally (armed at random moments, set off by a hit)
        self.mode_curveball = False  # every hit bends the way the paddle was moving (the Curveball talisman, for good)
        self.mode_lantern_night = False   # the court is always dark but for lanterns (the Lantern Night talisman, for good)
        self.mode_twin_ball = False  # every point is played with two balls, Red's and Blue's (the Twin Balls rules)
        self.mode_talisman_rush = False   # CHAOS (Talisman Rush till 1.9): talismans on, every 1.5-3 s, no limit
        self.mode_black_hole = False      # a Black Hole all match, growing point after point till it collapses
                                          # (1.8: Portal Pair was the mode until Rowan's second playtest)

        self.court = 0               # Classic: an open court
        self.online_host_blue = False    # online: the host plays Blue and the friend Red

        self.reset_powerups()

    @property
    def switch_each_point(self):
        """Switch, every point: the players take over each other's paddle after every point."""
        return self.mode_switch and self.switch_timing == 0

    @property
    def switch_mid_rally(self):
        """Switch, mid-rally: at random moments during play, the next hit once one is armed."""
        return self.mode_switch and self.switch_timing == 1

    @property
    def switching(self):
        """Switch is on: the paddles change hands in this match."""
        return self.mode_switch

    @property
    def chaos_each_point(self):
        """Chaos, every point: new random sizes and speeds each point."""
        return self.mode_chaos and self.chaos_timing == 0

    @property
    def chaos_drift(self):
        """Chaos, constant drift: sizes drift all match, as Shape Shift's do for a point."""
        return self.mode_chaos and self.chaos_timing == 1

    @property
    def talisman_limit(self):
        """How many talismans may be in play at once, their effects and any waiting on the court
        (CHAOS lifts the limit)."""
        return math.inf if self.mode_talisman_rush else self.at_once_options[self.talismans_at_once]

    @property
    def classic_physics(self):
        return self.physics == 1

    @property
    def v09_physics(self):
        return self.physics == 2

    @property
    def talismans_on(self):
        """Talismans turn up: Power-Ups on, or CHAOS."""
        return self.powerups or self.mode_talisman_rush

    @property
    def serve_seconds(self):
        return self.countdown_options[self.countdown]

    def modes_on(self):
        """The game modes this match is played with, by name."""
        return [mode for mode in self.MODES if getattr(self, "mode_" + mode)]

    def reset_ball_and_paddles(self):
        """The ball's and paddles' sizes and speeds back to their defaults (what Randomise changes)."""
        self.paddle_width = (self.paddle_width_min + self.paddle_width_max) // 2
        self.paddle_height = (self.paddle_height_min + self.paddle_height_max) // 2
        self.paddle_speed = (self.paddle_speed_min + self.paddle_speed_max) // 2
        self.ball_diameter = (self.ball_diameter_min + self.ball_diameter_max) // 2
        self.ball_speed = (self.ball_speed_min + self.ball_speed_max) // 2

    def reset_powerups(self):
        """Power-ups on, at the normal rate, every one of them allowed."""
        self.powerups = True
        self.powerup_rate = 1
        self.talismans_at_once = 0       # at_once_options[...]: 1
        for kind in POWERUP_KINDS:
            setattr(self, "pu_" + kind.key, True)

    def copy(self):
        """The rules a match plays by: a copy, so what you change mid-match (from Pause) only comes
        in when the next serve takes a fresh one, and Chaos's every-point sizes and speeds are
        rolled into it, never into your own settings."""
        return copy.copy(self)

    def chaos_roll(self):
        """Chaos, every point: new random sizes and speeds (on the match's copy: see copy)."""
        self.ball_speed = self.ball_speed_min + random.random() * self.ball_speed_range
        self.ball_diameter = self.ball_diameter_min + random.random() * self.ball_diameter_range
        self.paddle_speed = self.paddle_speed_min + random.random() * self.paddle_speed_range
        t = random.random()
        self.paddle_height = self.paddle_height_min + t * self.paddle_height_range
        self.paddle_width = self.paddle_width_min + t * self.paddle_width_range

    def ai_skill(self, own_score, opponent_score):
        """AI skill right now, from 0 (Baby) to 4 (Insane).  With adaptive AI it eases
        off by a level for every 3 points it is ahead and sharpens up when behind,
        sliding between levels rather than jumping."""
        if not self.adaptive_ai:
            return float(self.ai_difficulty)
        skill = self.ai_difficulty - (own_score - opponent_score) / 3
        return max(0.0, min(len(self.ai_difficulties) - 1.0, skill))

    def ai_level(self, own_score, opponent_score):
        """AI difficulty to use right now, as a whole level."""
        return round(self.ai_skill(own_score, opponent_score))

def key_name(key):
    """How a key is shown on screen: W, Up, Left Shift..."""
    name = pygame.key.name(key)
    return name.upper() if len(name) == 1 else name.title()

class GameplaySettings:
    """Your own controls: the keys, Auto-Pause, and on a phone the touch steering."""

    ACTIONS = ("up", "down", "left", "right")
    KEY_FIELDS = ("p1_up", "p1_down", "p1_left", "p1_right", "p2_up", "p2_down", "p2_left", "p2_right")
    DEFAULT_KEYS = {"p1_up": pygame.K_w, "p1_down": pygame.K_s, "p1_left": pygame.K_a, "p1_right": pygame.K_d,
                    "p2_up": pygame.K_UP, "p2_down": pygame.K_DOWN, "p2_left": pygame.K_LEFT, "p2_right": pygame.K_RIGHT}

    def __init__(self, app):
        self.app = app
        # On a phone (core/touch.py): how a finger steers, and how far Drag moves the paddle
        self.touch_steer_options = ["Drag", "Follow"]
        self.touch_sensitivity_options = ["Low", "Normal", "High", "Very High"]
        self.reset()

    def reset(self):
        self.auto_pause = True       # pause a match when the window loses focus
        self.touch_steer = 0         # (a phone) Drag
        self.touch_sensitivity = 1   # (a phone) Normal
        self.vibration = True        # (a phone) a buzz when your paddle hits the ball, and at each point
        self.reset_keys()

    def reset_keys(self):
        for field, key in self.DEFAULT_KEYS.items():
            setattr(self, field, key)

    def keys(self, player):
        return {action: getattr(self, f"{player}_{action}") for action in self.ACTIONS}

    def keys_label(self, player):
        keys = self.keys(player)
        if keys == {a: self.DEFAULT_KEYS[f"p2_{a}"] for a in self.ACTIONS}:
            return "Arrow Keys"
        return " ".join(key_name(keys[a]) for a in ("up", "left", "down", "right"))

    def bind(self, field, key):
        """Give `field` this key.  A binding that already had it swaps, so no key is used twice."""
        for other in self.KEY_FIELDS:
            if other != field and getattr(self, other) == key:
                setattr(self, other, getattr(self, field))
        setattr(self, field, key)

    def keys_valid(self):
        keys = [getattr(self, f) for f in self.KEY_FIELDS]
        named = all(isinstance(k, int) and pygame.key.name(k) for k in keys)
        return named and len(set(keys)) == len(keys) and pygame.K_ESCAPE not in keys

class DisplaySettings:
    def __init__(self, app):
        self.app = app

        self.max_fps_options = [30, 60, 120, 144, 165, 240, "Unlimited"]
        self.effects_options = ["Full", "Reduced", "Off"]

        # How far the menu background drifts against the mouse, for a sense of depth
        self.parallax_options = ["Off", "Gentle", "Full"]
        self.parallax_strength = [0.0, 0.5, 1.0]

        # How often Rotate fades to a new background: (shortest, longest) wait in seconds
        self.rotate_options = ["30-60 s", "2 min", "5 min"]
        self.rotate_waits = [(30, 60), (100, 140), (270, 330)]

        self.backgrounds = find_backgrounds()

        self.background = self.backgrounds.index(random.choice(self.backgrounds))

        self.reset()

    def fps_for_screen(self, hz):
        """The Max FPS option for a screen refreshing hz times a second: that rate if it's offered,
        else the next one up (a cap under the screen's rate judders); 60 if the rate isn't known."""
        if not hz:
            return self.max_fps_options.index(60)
        for i, option in enumerate(self.max_fps_options):
            if option == "Unlimited" or option >= hz - 1:      # a 59.94 Hz screen reports 59
                return i

    def reset(self):
        # A phone: 60, which its battery thanks it for.  A PC: the screen's own refresh rate (it
        # was 120 whatever the screen).  A saved choice is kept (see save_data).
        self.max_fps = 1 if ANDROID else self.fps_for_screen(refresh_rate())
        self.show_fps = True
        self.dim = 0
        self.resolution = (1920, 1080)
        self.rotate_backgrounds = True
        self.rotate_every = 0
        self.parallax = 2
        # How much the background is darkened during a match (0-1), on top of the Dim Overlay,
        # so the ball and paddles stand out.  The default is the old Court Dim: Medium.
        self.court_dim_level = 100 / 255
        self.effects = 0             # butterflies, embers and bursts: Full
        self.screen_shake = True
        self.ball_trail = True

class AudioSettings:
    def __init__(self, app):
        self.app = app

        # One jukebox.  Each track has a mood and the jukebox only picks from the
        # mood that suits where you are: relaxed in the menus, upbeat in a match,
        # triumphant on a win, downbeat on a loss.
        self.pools = {
            "menu":    ["Lofi Hiphop Tao.mp3",
                        "Lofi Vibe.mp3",
                        "Relaxed Tao 1.mp3",
                        "Relaxed Tao 2.mp3",
                        "Relaxed Tao 3.mp3",
                        "Retro Relax.mp3",
                        "Living Beware.mp3",
                        "Guzheng City.mp3",
                        "Ishikari Lore.mp3",
                        "Ripples.mp3",
                        "Path of the Goblin King.mp3",
                        "Liyan.mp3",
                        "Asian String Suite.mp3",
                        "New Dusks Light.mp3",
                        "Jade Kings Throne.mp3",
                        "Shenyang.mp3",
                        "Finding Movement.mp3",
                        "Eastern Thought.mp3",
                        "Tea Roots.mp3",
                        "Senbazuru.mp3",
                        "Million Elephants.ogg",
                        "Thinking Music.mp3",           # (1.9: quirky, a little spooky)
                        "Brittle Rille.mp3",
                        # 1.9, Rowan: too calm for a match, so they play here now
                        "Scheming Weasel.mp3",
                        "Sunrise in the Dynasty.mp3",
                        "Monster Promenade.mp3",
                        "Sneaky Snitch.mp3"],

            "game":    ["Hillichurl REMIX.mp3",
                        "Epic Conquest.mp3",
                        "Arcade Retro.mp3",
                        "Operation Awesome.mp3",
                        "Big Mojo.mp3",
                        "Mountain Emperor.mp3",
                        "Graveyard Shift.mp3",
                        "Burnt Spirit.mp3",
                        "Chipnese.ogg",
                        "Taiko Drums.ogg",
                        "One-eyed Maestro.mp3",
                        "Malicious.mp3",
                        "Chinese Tales.mp3",
                        "Drums of Dawn.mp3",
                        # 1.9: spooky and playful (Waltz of the Carnies, the circus one, is gone),
                        # and Rowan's two picks (played once their files are in the folder).
                        # (Rowan found seven too calm for a match: four play in the menus now, and
                        # Investigations, Professor and the Plant and Marty Gots a Plan are gone.)
                        "Moonlight Hall.mp3",
                        "Netherworld Shanty.mp3",
                        "Chinese Game.mp3",
                        "Halloween Playful.mp3"],

            "victory": ["Triumphant Win.mp3",
                        "Epic Win.mp3",
                        "Winner Winner.mp3",
                        "Our Story Begins.mp3",
                        "Ten Fanfares.ogg",
                        "Monkeys Spinning Monkeys.mp3",
                        "Heroic Age.mp3",
                        "Super Friendly.mp3",
                        "Comic Hero.mp3"],

            "defeat":  ["Grand Defeat.mp3",
                        "Sweet Melancholy.mp3",
                        "Ghost Processional.mp3",
                        "Peaceful Desolation.mp3",
                        "On the Shore.mp3",
                        "Nu Flute.mp3",
                        "Asian Duet.mp3",
                        "Death of a Ninja.mp3",
                        "Funeral March for Brass.mp3",
                        "Decline.mp3",
                        "Laconic Granny.mp3"],
        }

        # How long a track takes to fade out and the next to fade in
        self.fade_options = ["Quick", "Smooth", "Slow"]
        self.fade_ms = [400, 1000, 2500]

        # Crackling spirit fire and crickets under the music
        self.ambience_options = ["Off", "Menus", "Everywhere"]

        self.reset()

    def reset(self):
        self.play_mode = 1           # when a track ends: 0 the next in order, 1 a random one, 2 the same again
        self.even_volume = True      # quieten tracks recorded much louder than the rest
        self.fade = 1
        self.menu_sounds = True      # clicks and whooshes when using the menus
        self.ambience = 1

    @property
    def all_tracks(self):
        seen = []
        for tracks in self.pools.values():
            seen += [t for t in tracks if t not in seen]
        return seen

    @staticmethod
    def track_name(track):
        """Display name: file name without its extension."""
        return Path(track).stem if track else ""

class InterfaceSettings:
    """Menus, the HUD and tooltips."""

    def __init__(self, app):
        self.app = app

        self.hud_options = ["Full", "Minimal"]
        # When a match's best moments replay on their own: after a great point, after the match, both
        self.instant_replay_options = ["Off", "Great Points", "After the Match", "Both"]

        self.reset()

    def reset(self):
        self.tooltips = True
        self.ai_banter = True
        self.hide_cursor = True      # hide the mouse during a match until it moves
        self.hud = 0
        self.instant_replay = 2      # the highlights after the match
