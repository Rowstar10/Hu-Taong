"""Achievements (1.9, Rowan's 1.9 plan, phase 2, step 10: the 21 Rowan OK'd).

They're earned from what happens in a match, the same events the friend's screen gets online
(game/replay.py's: hits, bounces, talismans, points...), and from how a match ends.  "You" are the
paddle with no AI (or, online, your own); in a two-player match on one keyboard either player
earns the ones that aren't about winning, and nobody earns those that are.  Practice and replays
never count.  Saved in achievements.json, a file of their own (see core/save_data.py), so an older
version saving can't lose them.
"""
import datetime

from game.powerups import KINDS

# (key, name, how to earn it, its seal's character, its group)
LIST = (
    ("first_match", "Open for Business", "Play your first match", "始", "Getting going"),
    ("first_win", "First Client", "Win a match", "客", "Getting going"),
    ("matches_50", "Regular Customer", "Play 50 matches", "常", "Getting going"),
    ("beat_hard", "Hard Bargain", "Beat a Hard AI", "难", "Winning"),
    ("beat_insane", "The 77th Director", "Beat an Insane AI", "魁", "Winning"),
    ("three_in_a_row", "Three in a Row", "Win 3 matches in a row against the AI", "连", "Winning"),
    ("flawless", "Flawless Funeral", "Win a match without losing a point", "全", "Winning"),
    ("comeback", "Back from the Grave", "Win a match after being 5 points down", "归", "Winning"),
    ("rally_30", "All-Night Vigil", "Play a rally of 30 hits", "守", "Rallies and shots"),
    ("rocket", "Rocket", "Hit the ball at speed 3,000 or more", "箭", "Rallies and shots"),
    ("bank_shot", "Bank Shot", "Win a point with a shot off the walls 3 times", "弹", "Rallies and shots"),
    ("trick_shot", "Trick Shot", "Win a point with a shot off a stone", "巧", "Rallies and shots"),
    ("great_save", "Great Save", "Make a full-stretch save at your own goal", "救", "Rallies and shots"),
    ("paper_trail", "Paper Trail", "Take 100 talismans", "符", "Talismans"),
    ("collection", "Full Collection", "Take every talisman at least once", "集", "Talismans"),
    ("fire_winner", "Spirit Fire Winner", "Win a point with a blazing Spirit Fire shot", "火", "Talismans"),
    ("teleport_save", "Teleport Save", "Get saved by your Safety Teleport", "移", "Talismans"),
    ("into_the_void", "Into the Void", "See a Black Hole collapse", "渊", "Talismans"),
    ("grand_tour", "Grand Tour", "Win on all five courts", "游", "Modes, courts and online"),
    ("utter_chaos", "Utter CHAOS", "Win a match with CHAOS on", "乱", "Modes, courts and online"),
    ("far_away_friend", "Far-Away Friend", "Win an online match", "友", "Modes, courts and online"),
)
BY_KEY = {a[0]: a for a in LIST}

RALLY = 30              # hits in one rally
ROCKET = 3000           # ball speed (as the HUD shows it) off your paddle
BANK = 3                # bounces off the top and bottom between your hit and the goal
COMEBACK = 5            # points down
MATCHES = 50
TALISMANS = 100
HARD, INSANE = 3, 4     # (Match settings' AI levels: Baby 0 ... Insane 4)
TALISMAN_KEYS = [kind.key for kind in KINDS]
EDGE = 0                # (core/match_sounds.py's code for the top and bottom of the court)


class Watch:
    """What it takes to judge one match as it's played."""

    def __init__(self, you, scores):
        self.you = you              # () -> the set of sides (1 left, 2 right) that are "you" now
        self.scores = scores        # () -> (left's score, right's score)
        self.rally = 0
        self.shot = None            # the last hit: {"side", "walls", "stone", "blaze"}
        self.blazing = None         # the side of a Spirit Fire shot just struck (its "hit" comes next)
        self.down = 0               # the most points you've been behind


class Achievements:
    def __init__(self):
        self.reset()
        self.on_earn = None         # (key) -> None: the app shows it (see App)

    def reset(self):
        self.earned = {}            # key -> the date it was earned ("2026-11-19")
        self.counts = {"matches": 0, "taken": 0, "kinds": [], "streak": 0, "courts": []}
        self.watch = None

    # ---------------- Earning ----------------

    def earn(self, key):
        if key in BY_KEY and key not in self.earned:
            self.earned[key] = datetime.date.today().isoformat()
            if self.on_earn:
                self.on_earn(key)

    def start(self, you, scores):
        """A match starts (or starts over)."""
        self.watch = Watch(you, scores)

    def event(self, kind, values, key_of = None):
        """One event of the match being played (game/replay.py's)."""
        w = self.watch
        if w is None:
            return
        try:
            you = w.you()
            if not you:
                return                  # computer v computer: nobody's playing
            if kind == "hit":
                side = int(values[0])
                w.rally += 1
                if w.rally >= RALLY:
                    self.earn("rally_30")
                if side in you and len(values) > 3 and values[3] >= ROCKET:
                    self.earn("rocket")
                w.shot = {"side": side, "walls": 0, "stone": False, "blaze": w.blazing == side}
                w.blazing = None
            elif kind == "blaze":
                w.blazing = int(values[0])
            elif kind == "wall" and w.shot is not None:
                if (int(values[2]) if len(values) > 2 else EDGE) == EDGE:
                    w.shot["walls"] += 1
            elif kind == "stone" and w.shot is not None:
                w.shot["stone"] = True
            elif kind == "save" and int(values[0]) in you:
                self.earn("great_save")
            elif kind == "teleport" and int(values[0]) in you:
                self.earn("teleport_save")
            elif kind == "collapse":
                self.earn("into_the_void")
            elif kind == "pickup" and int(values[1]) in you:
                key_of = key_of or (lambda i: TALISMAN_KEYS[int(i)] if 0 <= int(i) < len(TALISMAN_KEYS) else None)
                key = key_of(values[0])
                self.counts["taken"] += 1
                if key and key not in self.counts["kinds"]:
                    self.counts["kinds"].append(key)
                if self.counts["taken"] >= TALISMANS:
                    self.earn("paper_trail")
                if set(TALISMAN_KEYS) <= set(self.counts["kinds"]):
                    self.earn("collection")
            elif kind == "score":
                side, shot = int(values[0]), w.shot
                if shot is not None and shot["side"] == side and side in you:
                    if shot["walls"] >= BANK:
                        self.earn("bank_shot")
                    if shot["stone"]:
                        self.earn("trick_shot")
                    if shot["blaze"]:
                        self.earn("fire_winner")
                w.rally, w.shot, w.blazing = 0, None, None
                self.note_score()
        except (IndexError, TypeError, ValueError):
            pass                        # a damaged event is skipped

    def note_score(self):
        """How far behind you are: only one of you can be behind (a two-player match has no comeback)."""
        w = self.watch
        you = w.you()
        if len(you) != 1:
            return
        mine = next(iter(you))
        scores = w.scores()
        w.down = max(w.down, scores[2 - mine] - scores[mine - 1])

    def match_over(self, won, lost_score = 0, ai_level = None, court = None, chaos = False, online = False):
        """A match has ended.  `won`: True or False for you, None when there's no one "you" (two
        players on one keyboard).  `ai_level` only against the AI.  Practice never comes here."""
        if self.watch is not None:
            self.note_score()
        self.counts["matches"] += 1
        self.earn("first_match")
        if self.counts["matches"] >= MATCHES:
            self.earn("matches_50")
        if won and online:
            self.earn("far_away_friend")
        if won is not None and ai_level is not None:
            self.counts["streak"] = self.counts["streak"] + 1 if won else 0
        if won:
            self.earn("first_win")
            if ai_level is not None:
                if ai_level >= HARD:
                    self.earn("beat_hard")
                if ai_level >= INSANE:
                    self.earn("beat_insane")
                if self.counts["streak"] >= 3:
                    self.earn("three_in_a_row")
            if lost_score == 0:
                self.earn("flawless")
            if self.watch is not None and self.watch.down >= COMEBACK:
                self.earn("comeback")
            if court and court not in self.counts["courts"]:
                self.counts["courts"].append(court)
            from game.courts import COURTS
            if all(c.name in self.counts["courts"] for c in COURTS):
                self.earn("grand_tour")
            if chaos:
                self.earn("utter_chaos")
        self.watch = None

    # ---------------- Saving ----------------

    def to_dict(self):
        return {"earned": dict(self.earned), "counts": {k: (list(v) if isinstance(v, list) else v)
                                                         for k, v in self.counts.items()}}

    def load_dict(self, data):
        """From the file: anything unknown or nonsensical is dropped."""
        self.reset()
        if not isinstance(data, dict):
            return
        earned = data.get("earned")
        if isinstance(earned, dict):
            self.earned = {k: v for k, v in earned.items() if k in BY_KEY and isinstance(v, str)}
        counts = data.get("counts")
        if isinstance(counts, dict):
            for key in ("matches", "taken", "streak"):
                n = counts.get(key)
                if isinstance(n, int) and not isinstance(n, bool) and n >= 0:
                    self.counts[key] = n
            for key in ("kinds", "courts"):
                items = counts.get(key)
                if isinstance(items, list):
                    self.counts[key] = [i for i in items if isinstance(i, str)]
