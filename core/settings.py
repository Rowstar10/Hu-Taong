import random
from pathlib import Path

from config import IMAGE_DIR

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

        # Match rules
        self.winning_scores = [3, 5, 11, 15, 21, "Endless Mode"]

        # AI
        self.ai_difficulties = ["Baby", "Easy", "Normal", "Hard", "Insane"]

        self.reset()

    def reset(self):
        self.paddle_width = (self.paddle_width_min + self.paddle_width_max) // 2
        self.paddle_height = (self.paddle_height_min + self.paddle_height_max) // 2
        self.paddle_speed = (self.paddle_speed_min + self.paddle_speed_max) // 2
        self.ball_diameter = (self.ball_diameter_min + self.ball_diameter_max) // 2
        self.ball_speed = (self.ball_speed_min + self.ball_speed_max) // 2

        # Match setup (chosen on the Match Setup screen)
        self.vs_ai = True            # True: you play one paddle and the AI takes the other.
        self.play_as_blue = False    # Which paddle is yours vs the AI (Red: W A S D, Blue: Arrow Keys).

        self.winning_score_index = 2
        self.win_by_two = True
        self.ai_difficulty = 2
        self.adaptive_ai = False

        # Chaos mode: new random ball/paddle settings every round.  The player's own
        # values are kept in _chaos_backup and put back when the match ends.
        self.chaos_mode = False
        self._chaos_backup = None

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

    def ai_level(self, own_score, opponent_score):
        """AI difficulty to use right now.  With adaptive AI it drops a level for every
        3 points the AI is ahead, and rises one for every 3 it is behind."""
        if not self.adaptive_ai:
            return self.ai_difficulty
        level = round(self.ai_difficulty - (own_score - opponent_score) / 3)
        return max(0, min(len(self.ai_difficulties) - 1, level))

class DisplaySettings:
    def __init__(self, app):
        self.app = app

        self.max_fps_options = [30, 60, 120, 144, 165, 240, "Unlimited"]

        self.backgrounds = find_backgrounds()

        self.background = self.backgrounds.index(random.choice(self.backgrounds))

        self.reset()

    def reset(self):
        self.max_fps = 2
        self.show_fps = True
        self.dim = 0
        self.resolution = (1920, 1080)
        self.rotate_backgrounds = True

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
                        "Jade Kings Throne.mp3"],

            "game":    ["Hillichurl REMIX.mp3",
                        "Epic Conquest.mp3",
                        "Arcade Retro.mp3",
                        "Operation Awesome.mp3",
                        "Shenyang.mp3",
                        "Big Mojo.mp3",
                        "Mountain Emperor.mp3",
                        "Scheming Weasel.mp3",
                        "Graveyard Shift.mp3",
                        "Burnt Spirit.mp3",
                        "Sunrise in the Dynasty.mp3",
                        "Chipnese.ogg",
                        "Taiko Drums.ogg"],

            "victory": ["Triumphant Win.mp3",
                        "Epic Win.mp3",
                        "Winner Winner.mp3",
                        "Our Story Begins.mp3",
                        "Finding Movement.mp3",
                        "Ten Fanfares.ogg"],

            "defeat":  ["Grand Defeat.mp3",
                        "Sweet Melancholy.mp3",
                        "Ghost Processional.mp3",
                        "Peaceful Desolation.mp3",
                        "On the Shore.mp3",
                        "Nu Flute.mp3",
                        "Asian Duet.mp3",
                        "Death of a Ninja.mp3"],
        }

        self.reset()

    def reset(self):
        self.loop_music = False

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
