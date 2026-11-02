import math


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
                    play_time = 0.0)

    def __init__(self):
        self.reset()

    def reset(self):
        for key, value in self.DEFAULTS.items():
            setattr(self, key, value)

    # ---------------- Saving ----------------

    def to_dict(self):
        return {key: getattr(self, key) for key in self.DEFAULTS}

    def load_dict(self, data):
        for key, default in self.DEFAULTS.items():
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                setattr(self, key, type(default)(value))

    # ---------------- Recording ----------------

    def track(self, game, dt):
        """Called every frame while a match is on screen."""
        if not game.running or game.paused or game.countdown is not None:
            return
        ball = game.ball
        self.play_time += dt
        self.best_rally = max(self.best_rally, ball.rally_value)
        self.top_ball_speed = max(self.top_ball_speed, int(math.hypot(ball.vx, ball.vy)))

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
            if winner is p1:
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
