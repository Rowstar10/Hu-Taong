import datetime, json, math

from game.powerups import KINDS

TALISMAN_KEYS = [kind.key for kind in KINDS]      # (a "spawn" or "pickup" event's index, as game/replay.py's KIND_KEYS)


class Stats:
    """Lifetime statistics.  Saved with the settings (see core/save_data.py)."""

    DEFAULTS = dict(matches = 0,
                    wins_vs_ai = 0,
                    losses_vs_ai = 0,
                    wins_red = 0,
                    wins_blue = 0,
                    points = 0,
                    win_streak = 0,
                    best_win_streak = 0,
                    best_rally = 0,
                    top_ball_speed = 0,
                    play_time = 0.0,
                    online_matches = 0,
                    online_wins = 0,
                    online_losses = 0,
                    online_streak = 0,
                    online_best_streak = 0)

    def __init__(self):
        self.reset()

    def reset(self):
        for key, value in self.DEFAULTS.items():
            setattr(self, key, value)
        # Each talisman (1.9, Rowan's plan): [times it turned up, times taken, points won by whoever
        # took it, points they lost], counting the point it was taken in.  Saved in a file of its
        # own (see core/save_data.py), so an older version saving can't lose it.
        self.talismans = {}
        self.this_point = []        # (talisman, side 1 or 2) taken in the point being played

    # ---------------- Talismans ----------------

    def talisman(self, key):
        return self.talismans.setdefault(key, [0, 0, 0, 0])

    def new_match(self):
        self.this_point = []

    def tally(self, kind, values, key_of = None):
        """One event of a match being played (game/replay.py's: here, or the host's online), for
        the talisman stats: one turning up, one taken, a point won.  Each player's own stats count
        their own matches, online too; Practice and replays don't count."""
        key_of = key_of or (lambda i: TALISMAN_KEYS[int(i)] if 0 <= int(i) < len(TALISMAN_KEYS) else None)
        try:
            if kind == "spawn":
                key = key_of(values[0])
                if key:
                    self.talisman(key)[0] += 1
            elif kind == "pickup":
                key = key_of(values[0])
                if key:
                    self.talisman(key)[1] += 1
                    self.this_point.append((key, int(values[1])))
            elif kind == "score":
                for key, side in self.this_point:
                    self.talisman(key)[2 if int(values[0]) == side else 3] += 1
                self.this_point = []
        except (IndexError, TypeError, ValueError):
            pass                        # a damaged event is skipped

    def talisman_line(self, key):
        """The talisman page's line about it."""
        seen, taken, won, lost = self.talismans.get(key, (0, 0, 0, 0))
        if not seen and not taken:
            return "Your stats: not seen in a match yet"
        line = f"Your stats: turned up {seen} time{'s' if seen != 1 else ''}, taken {taken}"
        if won + lost:
            line += f", and whoever took it won {won} of the {won + lost} point{'s' if won + lost != 1 else ''} it was taken in"
        return line

    def talismans_dict(self):
        return {key: list(counts) for key, counts in self.talismans.items()}

    def load_talismans(self, data):
        """From the file, or an import: anything unknown or nonsensical is dropped."""
        self.talismans = {}
        if not isinstance(data, dict):
            return
        for key, counts in data.items():
            if key in TALISMAN_KEYS and isinstance(counts, list) and len(counts) == 4 and \
                    all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in counts):
                self.talismans[key] = list(counts)

    # ---------------- Saving ----------------

    def to_dict(self):
        return {key: getattr(self, key) for key in self.DEFAULTS}

    def load_dict(self, data):
        for key, default in self.DEFAULTS.items():
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                setattr(self, key, type(default)(value))

    # ---------------- Export and import ----------------

    FILE_KIND = "Hu Taong stats"

    def export_text(self):
        return json.dumps({"kind": self.FILE_KIND, "version": 1,
                           "exported": datetime.datetime.now().isoformat(timespec = "seconds"),
                           "stats": self.to_dict(), "talismans": self.talismans_dict()}, indent = 2)

    @staticmethod
    def read_export_talismans(text):
        """The talisman stats in an exported file (1.9), or None."""
        try:
            data = json.loads(text)
        except ValueError:
            return None
        return data.get("talismans") if isinstance(data, dict) else None

    @classmethod
    def read_export(cls, text):
        """The stats in an exported file, or None if it isn't one.  Anything unknown or
        nonsensical in it is dropped, the same way a damaged save is."""
        try:
            data = json.loads(text)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        stats = data.get("stats") if data.get("kind") == cls.FILE_KIND else None
        if stats is None and set(cls.DEFAULTS) & set(data):
            stats = data                        # a bare stats block, e.g. copied out of save.json
        if not isinstance(stats, dict) or not set(cls.DEFAULTS) & set(stats):
            return None
        clean = cls()
        clean.load_dict(stats)
        return clean.to_dict()

    # ---------------- Recording ----------------

    def track(self, game, dt):
        """Called every frame while a match is on screen."""
        if not game.running or game.paused or game.countdown is not None:
            return
        ball = game.ball
        self.play_time += dt
        self.best_rally = max(self.best_rally, ball.rally_value)
        self.top_ball_speed = max(self.top_ball_speed, int(math.hypot(ball.vx, ball.vy)))

    def record_online(self, won):
        """A match against a friend over the internet, from this player's side."""
        self.online_matches += 1
        if won:
            self.online_wins += 1
            self.online_streak += 1
            self.online_best_streak = max(self.online_best_streak, self.online_streak)
        else:
            self.online_losses += 1
            self.online_streak = 0

    @property
    def online_win_rate(self):
        games = self.online_wins + self.online_losses
        return round(100 * self.online_wins / games) if games else 0

    def record_match(self, p1, winner, loser):
        self.matches += 1

        if not winner.ai_enabled and loser.ai_enabled:
            self.wins_vs_ai += 1
            self.win_streak += 1
            self.best_win_streak = max(self.best_win_streak, self.win_streak)
        elif winner.ai_enabled and not loser.ai_enabled:
            self.losses_vs_ai += 1
            self.win_streak = 0
        elif not winner.ai_enabled and not loser.ai_enabled:
            if winner.color1 == "Red":                   # (a Switch can hand Red the right paddle)
                self.wins_red += 1
            else:
                self.wins_blue += 1

    # ---------------- Display ----------------

    @property
    def win_rate(self):
        games = self.wins_vs_ai + self.losses_vs_ai
        return round(100 * self.wins_vs_ai / games) if games else 0

    @staticmethod
    def format_time(seconds):
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"
