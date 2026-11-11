import random
from pathlib import Path

import pygame

from config import IMAGE_DIR
from core.platform import ANDROID
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
    def __init__(self, app):
        self.app = app
        self.gameplay = GameplaySettings(app)
        self.display = DisplaySettings(app)
        self.audio = AudioSettings(app)
        self.interface = InterfaceSettings(app)
        self.online = OnlineSettings(app)


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

class GameplaySettings:
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
        self.powerup_rate_options = ["Rare", "Normal", "Frequent", "Chaotic"]

        # Courts: the stones a match starts with (see game/courts.py); the last one is Random
        self.court_options = courts.NAMES

        self.reset()

    def reset(self):
        self.paddle_width = (self.paddle_width_min + self.paddle_width_max) // 2
        self.paddle_height = (self.paddle_height_min + self.paddle_height_max) // 2
        self.paddle_speed = (self.paddle_speed_min + self.paddle_speed_max) // 2
        self.ball_diameter = (self.ball_diameter_min + self.ball_diameter_max) // 2
        self.ball_speed = (self.ball_speed_min + self.ball_speed_max) // 2
        self.pace = 1.0

        # Match setup (chosen on the Match Setup screen)
        self.vs_ai = True            # True: you play one paddle and the AI takes the other.
        self.play_as_blue = False    # Which paddle is yours vs the AI (Red: W A S D, Blue: Arrow Keys).

        self.winning_score_index = 2
        self.win_by_two = True
        self.middle_wall = True      # False: paddles may cross the centre line
        self.ai_difficulty = 2
        self.ai_style = 0
        self.adaptive_ai = False

        # Chaos mode: 0 off, 1 new random ball/paddle settings every round, 2 (Chaos Mode +)
        # sizes and speeds drift during play.  For 1 the player's own values are kept in
        # _chaos_backup and put back when the match ends.
        self.chaos_mode = 0
        self._chaos_backup = None

        # Chaos switch: 0 off, 1 players swap paddles after every point (Chaos Switch),
        # 2 the paddles swap places at random, telegraphed moments mid-rally (Chaos Switch +,
        # which needs the Middle Wall off), 3 both.
        self.chaos_switch = 0
        self.curveball = False       # every hit bends the way the paddle was moving (the Curveball power-up, for good)
        self.lantern_night = False   # the court is always dark but for lanterns (the Lantern Night power-up, for good)

        self.court = 0               # Classic: an open court
        self.online_host_blue = False    # online: the host plays Blue and the friend Red

        self.reset_powerups()

    @property
    def switch_each_point(self):
        """Chaos Switch: players take each other's paddles after every point."""
        return self.chaos_switch in (1, 3)

    @property
    def switch_mid_rally(self):
        """Chaos Switch +: the paddles swap places mid-rally."""
        return self.chaos_switch in (2, 3)

    def reset_powerups(self):
        """Power-ups on, at the normal rate, every one of them allowed."""
        self.powerups = True
        self.powerup_rate = 1
        for kind in POWERUP_KINDS:
            setattr(self, "pu_" + kind.key, True)

    CHAOS_KEYS = ("ball_speed", "ball_diameter", "paddle_height", "paddle_width", "paddle_speed")

    def stored(self, name):
        """The player's own value for a setting, even while chaos mode has it borrowed."""
        if self._chaos_backup is not None and name in self._chaos_backup:
            return self._chaos_backup[name]
        return getattr(self, name)

    def chaos_roll(self):
        if self._chaos_backup is None:
            self._chaos_backup = {key: getattr(self, key) for key in self.CHAOS_KEYS}
        self.ball_speed = self.ball_speed_min + random.random() * self.ball_speed_range
        self.ball_diameter = self.ball_diameter_min + random.random() * self.ball_diameter_range
        self.paddle_speed = self.paddle_speed_min + random.random() * self.paddle_speed_range
        t = random.random()
        self.paddle_height = self.paddle_height_min + t * self.paddle_height_range
        self.paddle_width = self.paddle_width_min + t * self.paddle_width_range

    def chaos_restore(self):
        if self._chaos_backup is not None:
            for key, value in self._chaos_backup.items():
                setattr(self, key, value)
            self._chaos_backup = None

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

class DisplaySettings:
    def __init__(self, app):
        self.app = app

        self.max_fps_options = [30, 60, 120, 144, 165, 240, "Unlimited"]

        # How far the menu background drifts against the mouse, for a sense of depth
        self.parallax_options = ["Off", "Gentle", "Full"]
        self.parallax_strength = [0.0, 0.5, 1.0]

        # How much the background is darkened during a match, so the ball and paddles stand out
        self.court_dim_options = ["Off", "Light", "Medium", "Strong"]
        self.court_dim_levels = [0, 60, 100, 150]

        # How often Rotate fades to a new background: (shortest, longest) wait in seconds
        self.rotate_options = ["30-60 s", "2 min", "5 min"]
        self.rotate_waits = [(30, 60), (100, 140), (270, 330)]

        self.backgrounds = find_backgrounds()

        self.background = self.backgrounds.index(random.choice(self.backgrounds))

        self.reset()

    def reset(self):
        self.max_fps = 1 if ANDROID else 2          # a phone: 60, which its battery thanks it for
        self.show_fps = True
        self.dim = 0
        self.resolution = (1920, 1080)
        self.rotate_backgrounds = True
        self.rotate_every = 0
        self.parallax = 2
        self.court_dim = 2

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
                        "Million Elephants.ogg"],

            "game":    ["Hillichurl REMIX.mp3",
                        "Epic Conquest.mp3",
                        "Arcade Retro.mp3",
                        "Operation Awesome.mp3",
                        "Big Mojo.mp3",
                        "Mountain Emperor.mp3",
                        "Scheming Weasel.mp3",
                        "Graveyard Shift.mp3",
                        "Burnt Spirit.mp3",
                        "Sunrise in the Dynasty.mp3",
                        "Chipnese.ogg",
                        "Taiko Drums.ogg",
                        "One-eyed Maestro.mp3",
                        "Monster Promenade.mp3",
                        "Waltz of the Carnies.mp3",
                        "Malicious.mp3",
                        "Chinese Tales.mp3",
                        "Drums of Dawn.mp3"],

            "victory": ["Triumphant Win.mp3",
                        "Epic Win.mp3",
                        "Winner Winner.mp3",
                        "Our Story Begins.mp3",
                        "Ten Fanfares.ogg",
                        "Monkeys Spinning Monkeys.mp3",
                        "Heroic Age.mp3",
                        "Super Friendly.mp3"],

            "defeat":  ["Grand Defeat.mp3",
                        "Sweet Melancholy.mp3",
                        "Ghost Processional.mp3",
                        "Peaceful Desolation.mp3",
                        "On the Shore.mp3",
                        "Nu Flute.mp3",
                        "Asian Duet.mp3",
                        "Death of a Ninja.mp3",
                        "Funeral March for Brass.mp3",
                        "Decline.mp3"],
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

def key_name(key):
    """How a key is shown on screen: W, Up, Left Shift..."""
    name = pygame.key.name(key)
    return name.upper() if len(name) == 1 else name.title()

class InterfaceSettings:
    ACTIONS = ("up", "down", "left", "right")
    KEY_FIELDS = ("p1_up", "p1_down", "p1_left", "p1_right", "p2_up", "p2_down", "p2_left", "p2_right")
    DEFAULT_KEYS = {"p1_up": pygame.K_w, "p1_down": pygame.K_s, "p1_left": pygame.K_a, "p1_right": pygame.K_d,
                    "p2_up": pygame.K_UP, "p2_down": pygame.K_DOWN, "p2_left": pygame.K_LEFT, "p2_right": pygame.K_RIGHT}

    def __init__(self, app):
        self.app = app

        self.hud_options = ["Full", "Minimal"]
        # When a match's best moments replay on their own: after a great point, after the match, both
        self.instant_replay_options = ["Off", "Great Points", "After the Match", "Both"]
        self.effects_options = ["Full", "Reduced", "Off"]
        self.countdown_options = [3, 2, 1]
        # On a phone (core/touch.py): how a finger steers, and how far Drag moves the paddle
        self.touch_steer_options = ["Drag", "Follow"]
        self.touch_sensitivity_options = ["Low", "Normal", "High", "Very High"]

        self.reset()

    def reset(self):
        self.tooltips = True
        self.ai_banter = True
        self.screen_shake = True
        self.ball_trail = True
        self.auto_pause = True       # pause a match when the window loses focus
        self.hide_cursor = True      # hide the mouse during a match until it moves
        self.touch_steer = 0         # (a phone) Drag
        self.touch_sensitivity = 1   # (a phone) Normal
        self.vibration = True        # (a phone) a buzz when your paddle hits the ball, and at each point

        self.hud = 0
        self.instant_replay = 2      # the highlights after the match
        self.effects = 0
        self.countdown = 0
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

    @property
    def serve_seconds(self):
        return self.countdown_options[self.countdown]
