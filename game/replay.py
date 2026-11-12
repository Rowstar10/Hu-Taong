"""Replays: every match is recorded as it's played, so it can be watched again, saved whole or in
part, and its best moments picked out as highlights.

Sixty times a second the recorder writes down what is on screen (paddles, ball, stones,
talismans, scores, what each player has on) as a row of numbers, plus the moments that make a
sound (hits, goals, power-ups).  Nothing is simulated again on playback: a replay simply draws
those rows back, so it always looks exactly like what happened.

Highlights: at the end of every point the recorder looks back over it for its best moment, scores
it, and keeps a clip around it.  What counts is judged against the match itself, so an ordinary
point doesn't make the reel just because something happened in it:
  a rally at least twice as long as this match's usual one (its last 12 seconds)
  a winner among the fastest shots of the match, or one that slipped past the defender by a whisker
  a save at full stretch, off the paddle's end or its very edge, that won the saver the point
  trick shots: off a stone, off three walls or more, Spirit Fire, Ghost Ball, Blink, a Soul Swap
  the score: the winning point, a match point saved, a late equaliser
The reel then takes the best five, preferring a mix of kinds to five of the same.
"""
import datetime, json, math, struct, zlib
from array import array
from pathlib import Path

from config import BASE_W, BASE_H
from game.powerups import BY_KEY, KINDS

RATE = 60                    # frames a second
MOST_FRAMES = RATE * 60 * 30 # half an hour; a longer match keeps its last half hour
MAGIC = b"HUTAONG-REPLAY 1\n"
KIND_KEYS = [kind.key for kind in KINDS]
STYLES = ["tomb", "pillar"]
GREAT = 14.0                 # a point's best moment worth an instant replay scores at least this
REEL_REPEAT = 0.6            # each repeat of a kind of moment in the reel counts for this much less


class Moment:
    """A highlight: what happened, how good it was, and the frames to show."""
    def __init__(self, title, score, at, start, end, side):
        self.title, self.score, self.at, self.start, self.end, self.side = title, score, at, start, end, side

    def to_dict(self):
        return {"title": self.title, "score": round(self.score, 1), "at": self.at, "start": self.start,
                "end": self.end, "side": self.side}

    @classmethod
    def from_dict(cls, d):
        return cls(str(d["title"]), float(d["score"]), int(d["at"]), int(d["start"]), int(d["end"]), int(d["side"]))


class Clip:
    """Frames and events, for watching or saving.  Frames are packed rows of 32-bit floats."""
    def __init__(self, frames, events, info, moments=()):
        self.frames = frames         # list of bytes
        self.events = events         # [(frame, kind, values...)]
        self.info = info             # labels, pace, strings...
        self.moments = list(moments)

    @property
    def length(self):
        return len(self.frames) / RATE

    def part(self, start, end, title=None):
        """Frames start..end (inclusive) as a clip of their own."""
        start, end = max(0, start), min(len(self.frames) - 1, end)
        events = [(f - start, *rest) for f, *rest in self.events if start <= f <= end]
        moments = [Moment(m.title, m.score, m.at - start, max(0, m.start - start), min(end, m.end) - start, m.side)
                   for m in self.moments if start <= m.at <= end]
        info = dict(self.info)
        if title:
            info["title"] = title
        return Clip(self.frames[start:end + 1], events, info, moments)

    # ---------------- Files ----------------

    def save(self, path, kind):
        lengths = array("H", [len(f) // 4 for f in self.frames])
        payload = struct.pack("<I", len(self.frames)) + lengths.tobytes() + b"".join(self.frames)
        last = array("f")
        if self.frames:
            last.frombytes(self.frames[-1])
        header = dict(self.info, version = 1, kind = kind, length = round(self.length, 2),
                      created = datetime.datetime.now().isoformat(timespec = "seconds"),
                      score = [int(last[16]), int(last[17])] if self.frames else [0, 0],
                      kinds = KIND_KEYS, events = self.events, moments = [m.to_dict() for m in self.moments])
        head = json.dumps(header).encode("utf-8")
        data = MAGIC + struct.pack("<I", len(head)) + head + zlib.compress(payload, 6)
        path = Path(path)
        path.parent.mkdir(parents = True, exist_ok = True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return path

    @staticmethod
    def read_header(path):
        with open(path, "rb") as f:
            if f.read(len(MAGIC)) != MAGIC:
                return None
            size, = struct.unpack("<I", f.read(4))
            if size > 20_000_000:
                return None
            return json.loads(f.read(size).decode("utf-8"))

    @classmethod
    def load(cls, path):
        """A saved replay, or None if the file isn't one (or is damaged)."""
        try:
            raw = Path(path).read_bytes()
            if not raw.startswith(MAGIC):
                return None
            at = len(MAGIC)
            size, = struct.unpack_from("<I", raw, at)
            header = json.loads(raw[at + 4:at + 4 + size].decode("utf-8"))
            payload = zlib.decompress(raw[at + 4 + size:])
            count, = struct.unpack_from("<I", payload, 0)
            lengths = array("H"); lengths.frombytes(payload[4:4 + 2 * count])
            frames, pos = [], 4 + 2 * count
            for n in lengths:
                frames.append(payload[pos:pos + 4 * n])
                pos += 4 * n
            if header.get("kinds") != KIND_KEYS:
                header["remap"] = [KIND_KEYS.index(k) if k in KIND_KEYS else -1 for k in header.get("kinds", [])]
            events = [tuple(e) for e in header.pop("events", [])]
            moments = [Moment.from_dict(m) for m in header.pop("moments", [])]
            return cls(frames, events, header, moments)
        except (OSError, ValueError, KeyError, TypeError, struct.error, zlib.error, UnicodeDecodeError):
            return None


# ======================================================================
#  Recording
# ======================================================================

class Recorder:
    def __init__(self, game):
        self.game = game
        self.frames = []
        self.events = []
        self.moments = []
        self.dropped = 0             # frames let go from the front of a very long match
        self.clock = 0.0
        self.due = 0.0
        self.strings = []            # banter lines, so a frame can name one by number
        self.point = self.new_point()
        self.shots = []              # every shot's speed this match, to judge a fast one by
        self.rallies = []            # every point's number of hits, to judge a long rally by
        self.instant = None          # a moment waiting to be replayed straight after its point
        self.winner = None           # the match-winning moment, once there is one

    def info(self):
        g = self.game
        return {"labels": ["AI" if g.p1.ai_enabled else g.p1.controls_label,
                           "AI" if g.p2.ai_enabled else g.p2.controls_label],
                "pace": g.settings.pace, "switch_each_point": g.settings.switch_each_point,
                "court": g.court.name, "strings": self.strings,
                "title": f"{datetime.datetime.now():%d %b %Y, %H:%M}"}

    def new_point(self):
        return {"start": len(self.frames) + self.dropped, "hits": 0, "top": 0.0, "saves": [], "bounces": 0,
                "stone": False, "teleports": [], "swap": None, "blinks": 0, "fire": False, "ghost": False,
                "first_hit": None, "last_shot": None, "gaps": {1: None, 2: None}}

    @property
    def now(self):
        """The frame being recorded, counted from the match's first."""
        return len(self.frames) + self.dropped

    def clip(self):
        return Clip(list(self.frames), [(f - self.dropped, *rest) for f, *rest in self.events if f >= self.dropped],
                    self.info(), [Moment(m.title, m.score, m.at - self.dropped, max(0, m.start - self.dropped),
                                         m.end - self.dropped, m.side) for m in self.moments if m.start >= self.dropped])

    def string(self, text):
        if text not in self.strings:
            self.strings.append(text)
        return self.strings.index(text)

    # ---------------- Each frame ----------------

    def capture(self, dt):
        """Called every frame the match is on screen; writes a row at RATE a second."""
        self.clock += dt
        self.track_pass()
        if self.clock < self.due:
            return
        self.due = max(self.due + 1 / RATE, self.clock - 0.1)
        self.frames.append(self.row())
        if len(self.frames) > MOST_FRAMES:
            cut = RATE * 60
            del self.frames[:cut]
            self.dropped += cut
        ball = self.game.ball
        self.point["top"] = max(self.point["top"], math.hypot(ball.vx, ball.vy))

    def row(self):
        g, ball, pu = self.game, self.game.ball, self.game.powerups
        flags = (1 if getattr(ball, "blazing", False) else 0) | (2 if pu.ball_frosted() else 0)
        flags |= 32 if getattr(ball, "side", None) == "red" else 0         # Twin Balls: the ball is Red's
        last = ball.last_paddle
        flags |= 8 if last is g.p1 else 16 if last is g.p2 else 0
        state = (1 if g.wall_up else 0) | (2 if g.p1.ai_enabled else 0) | (4 if g.p2.ai_enabled else 0)
        state |= (32 if pu.frosted(g.p1) else 0) | (64 if pu.frosted(g.p2) else 0)
        state |= (128 if pu.frozen(g.p1) else 0) | (256 if pu.frozen(g.p2) else 0)
        cd = g.countdown
        message = 0 if not g.message_text else (1 if g.message_text.startswith(g.p1.color1) else 2)
        if message and g.message_text.endswith("x2"):
            message += 2                     # Double or Nothing: 3 Red or 4 Blue scored 2 (older replays: 1 or 2)
        banter = g.banter
        stuck = getattr(ball, "stuck", None)
        if stuck:
            flags |= 4
        values = [self.clock,
                  g.p1.x0, g.p1.y0, g.p1.width, g.p1.height,
                  g.p2.x0, g.p2.y0, g.p2.width, g.p2.height,
                  ball.x0, ball.y0, ball.width, ball.vx, ball.vy, pu.ball_alpha(), flags,
                  g.p1.score, g.p2.score, ball.rally_value, state,
                  cd.remaining if cd else -1, cd.shown_value if cd else -1, message,
                  g.switch_warning if g.switch_warning is not None else -1, g.switch_flash,
                  1 if g.switch_banner.endswith("Swap!") else 0,
                  self.string(banter[0]) if banter else -1, (1 if banter[1] is g.p1 else 2) if banter else 0,
                  banter[2] if banter else 0,
                  stuck["side"] if stuck else 0, (1 if stuck["paddle"] is g.p1 else 2) if stuck else 0,
                  (1 - stuck["left"] / stuck["total"]) if stuck else 0]
        stones = [o for o in g.objects if getattr(o, "is_obstacle", False)]
        fx1, fx2, court = pu.effect_list(g.p1), pu.effect_list(g.p2), pu.court_list()
        values += [len(pu.pickups), len(stones), len(fx1), len(fx2), len(court), len(pu.hops)]
        for item in pu.pickups:
            values += [KIND_KEYS.index(item["kind"]), item["x"], item["y"], item["age"], item["phase"]]
        for s in stones:
            values += [s.x0, s.y0, s.width, s.height, s.visibility(), STYLES.index(s.style), s.speed]
        for items in (fx1, fx2):
            for key, left, charges in items:
                values += [KIND_KEYS.index(key), -1 if left is None else left, charges]
        for key, left, note in court:
            values += [KIND_KEYS.index(key), -1 if left is None else left]
        for hop in pu.hops:
            values += hop
        # Twin Balls' blue ball, at the very end (older replays simply stop before this)
        extra = [b for b in pu.balls() if b is not ball] if hasattr(pu, "balls") else []
        values.append(len(extra))
        for b in extra:
            values += [b.x0, b.y0, b.width, b.vx, b.vy, 2 if getattr(b, "side", None) == "blue" else 1,
                       1 if getattr(b, "blazing", False) else 0]
        # then the ball's spin, the wind, the night, the firecracker and the portals
        portals = getattr(pu, "portals", [])
        values += [getattr(ball, "curve", 0.0), pu.wind_force() if hasattr(pu, "wind_force") else 0.0,
                   pu.lantern_level() if hasattr(pu, "lantern_level") else 0.0,
                   pu.cracker_hits(ball) if hasattr(pu, "cracker_hits") else 0, len(portals)]
        for door in portals:
            values += [door["x"], door["y"], door["angle"]]
        # then the Firecracker's shockwaves, and how chipped each stone is
        blasts = getattr(pu, "blasts", [])
        values.append(len(blasts))
        for blast in blasts:
            values += blast
        values += [getattr(st, "hp", 1) / max(1, getattr(st, "max_hp", 1)) for st in stones]
        return array("f", values).tobytes()

    def track_pass(self):
        """As the ball goes past a paddle, how near it came to it (for "Just out of reach!")."""
        g = self.game
        ball = g.ball
        if not ball.vx or getattr(ball, "stuck", None):
            return
        defender = g.p2 if ball.vx > 0 else g.p1
        r = ball.width / 2
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        if defender.x0 - r <= cx <= defender.x1 + r:
            gap = max(0.0, defender.y0 - (cy + r), (cy - r) - defender.y1)
            gaps = self.point["gaps"]
            side = 1 if defender is g.p1 else 2
            gaps[side] = gap if gaps[side] is None else min(gaps[side], gap)

    # ---------------- Events ----------------

    def event(self, kind, *values):
        self.events.append((self.now, kind, *[round(v, 1) if isinstance(v, float) else v for v in values]))

    def on_hit(self, ball, paddle, data):
        p = self.point
        p["hits"] += 1
        p["bounces"] = 0
        p["stone"] = False
        p["fire"] = bool(getattr(ball, "blazing", False))
        p["gaps"] = {1: None, 2: None}                     # a fresh shot: how near it comes, afresh
        if p["first_hit"] is None:
            p["first_hit"] = self.now
        side = 1 if paddle.is_left else 2
        incoming = p["last_shot"][1] if p["last_shot"] else 0.0
        speed = math.hypot(ball.vx, ball.vy)                # the shot, as it leaves the paddle
        p["last_shot"] = (side, speed)
        self.shots.append(speed)
        self.event("hit", side, (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2)
        # A save near your own goal, at full stretch: off the paddle's end or its very edge
        offset = abs(((ball.y0 + ball.y1) / 2 - (paddle.y0 + paddle.y1) / 2) / (paddle.height / 2))
        nx, ny = data["normal"]
        stretch = math.hypot(paddle.vx, paddle.vy) > paddle.speed * 0.6
        if stretch and (ny != 0 or offset > 0.8):
            near_goal = ((ball.x0 + ball.x1) / 2 < BASE_W * 0.3) if paddle.is_left else ((ball.x0 + ball.x1) / 2 > BASE_W * 0.7)
            if near_goal:
                p["saves"].append((self.now, side, "end" if ny else "edge", p["hits"], incoming))

    def on_bounce(self, ball, other):
        self.point["bounces"] += 1
        if getattr(other, "is_obstacle", False):
            self.point["stone"] = True
            self.event("stone", (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2)
        else:
            self.event("wall", (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2)

    def on_powerup(self, kind, owner):
        self.event("pickup", KIND_KEYS.index(kind.key), 1 if owner.is_left else 2)
        if kind.key == "ghost":
            self.point["ghost"] = True

    def on_teleport(self, paddle):
        self.point["teleports"].append((self.now, 1 if paddle.is_left else 2))
        self.event("teleport", 1 if paddle.is_left else 2)

    def on_stick(self, paddle):
        self.event("stick", 1 if paddle.is_left else 2)

    def on_blink(self, *xy):
        self.point["blinks"] += 1
        self.event("blink")

    def on_swap(self, banner):
        self.point["swap"] = self.now
        self.event("swap", banner)

    # ---------------- The end of a point ----------------

    def on_point(self, scorer, match_won):
        """Look back over the point just won and keep its best moment, if it had one worth keeping.
        Scores run from about 10 (worth a look) to 20 and more (unmissable)."""
        g, p = self.game, self.point
        side = 1 if scorer is g.p1 else 2
        lost = 2 if side == 1 else 1
        goal = self.now
        self.event("score", side)
        options = []
        hits = p["hits"]

        def winner(title, score, before = 4.0):
            options.append(Moment(title, score, goal, goal - int(before * RATE), goal + int(1.2 * RATE), side))

        # A long rally, by this match's standards: shown whole (up to 18 seconds)
        usual = sorted(self.rallies)[len(self.rallies) // 2] if len(self.rallies) >= 3 else 4
        if hits >= 8 and hits >= 2 * usual:
            first = p["first_hit"] if p["first_hit"] is not None else goal
            winner(f"{hits}-hit rally!", min(20.0, 8 + 0.5 * hits), before = min(12.0, (goal - first) / RATE + 1.0))

        # The winning shot: one of the fastest of the match, or one that only just got past
        shot = p["last_shot"]
        if shot and shot[0] == side and hits >= 2 and len(self.shots) >= 6:
            speeds = sorted(self.shots)
            median, top = speeds[len(speeds) // 2], speeds[int(len(speeds) * 0.85)]
            if shot[1] >= max(1.35 * median, top):
                winner("Rocket!", min(16.0, 10 + 12 * (shot[1] / median - 1.35)), before = 3.0)
        gap = p["gaps"][lost]
        if gap is not None and gap <= 20 and hits >= 2:
            winner("Just out of reach!", 11 + (20 - gap) / 8, before = 3.0)

        # Trick shots
        if p["stone"]:
            winner("Trick shot off the stone!", 14)
        elif p["bounces"] >= 3:
            winner("Bank shot!", 9 + min(p["bounces"], 6))
        if p["fire"] and shot and shot[0] == side:
            winner("Spirit Fire winner!", 12)
        if p["ghost"] and hits:
            winner("Ghost ball!", 10)
        if p["blinks"] >= 2:
            winner("Blink and you'll miss it!", 10)
        if p["swap"] is not None and goal - p["swap"] < 3 * RATE:
            winner("Swapped and scored!", 12)

        # Saves that mattered: at full stretch, and the saver went on to win the point soon after
        median = sorted(self.shots)[len(self.shots) // 2] if self.shots else 0.0
        for at, who, how, at_hit, incoming in p["saves"]:
            if who == side and hits - at_hit <= 6:
                score = 12 + (2 if how == "end" else 0) + (2 if median and incoming >= 1.3 * median else 0)
                title = "Great save!" if how == "edge" else "Off the end of the paddle!"
                options.append(Moment(title, score, at, at - int(2.5 * RATE), min(goal + int(1.0 * RATE), at + int(2.5 * RATE)), who))
        for at, who in p["teleports"]:
            options.append(Moment("Teleport save!", 12 + (2 if who == side else 0), at,
                                  at - int(2.5 * RATE), at + int(2.0 * RATE), who))

        # The score makes a point matter more: the winning point, a match point saved, a late equaliser
        bonus = 0.0
        win = g.app.settings.gameplay.winning_scores[g.app.settings.gameplay.winning_score_index]
        mine, theirs = (g.p1.score, g.p2.score) if side == 1 else (g.p2.score, g.p1.score)
        if isinstance(win, int):
            if theirs >= win - 1 and mine - 1 < theirs:
                bonus += 3                            # they were a point from winning
                winner("Match point saved!", 13)
            elif mine == theirs and mine >= win - 3:
                bonus += 1.5                          # level, late on
        if match_won:
            winner("Match point!", 14)
            bonus += 4                                # the winning point always makes the reel

        self.rallies.append(hits)
        start = p["start"]
        best = max(options, key = lambda m: m.score) if options else None
        if best:
            best.start = max(start, best.start)
            best.score += bonus
            self.moments.append(best)
            if match_won:
                self.winner = best
            elif best.score >= GREAT:
                self.instant = best
        self.point = self.new_point()
        self.point["start"] = goal

    def reel(self, most=5):
        """The match's best moments, in the order they happened: the winning point, then the best
        of the rest, each repeat of a kind counting for less, so the reel is a mix."""
        pool = [m for m in self.moments if m.score >= 10 or m is self.winner]
        chosen, seen = [], {}
        if self.winner in pool:
            chosen.append(self.winner)
            pool.remove(self.winner)
            seen[moment_kind(self.winner)] = 1
        while pool and len(chosen) < most:
            pick = max(pool, key = lambda m: m.score * REEL_REPEAT ** seen.get(moment_kind(m), 0))
            pool.remove(pick)
            chosen.append(pick)
            seen[moment_kind(pick)] = seen.get(moment_kind(pick), 0) + 1
        return sorted(chosen, key = lambda m: m.at)


def moment_kind(moment):
    """What sort of moment it is (every long rally is one sort, whatever its length)."""
    return "rally" if "rally" in moment.title else moment.title


# ======================================================================
#  Playback: stand-ins the renderer and HUD draw just like the real game
# ======================================================================

class _Box:
    def __init__(self):
        self.x0 = self.y0 = self.x1 = self.y1 = 0.0
        self.width = self.height = 0.0
        self.vx = self.vy = 0.0

    def place(self, x0, y0, w, h):
        self.x0, self.y0, self.width, self.height = x0, y0, w, h
        self.x1, self.y1 = x0 + w, y0 + h


class ViewPaddle(_Box):
    is_paddle, is_ball, is_wall = True, False, False

    def __init__(self, game, left, colour, label):
        super().__init__()
        self.game, self.is_left, self.color1 = game, left, colour
        self.controls_label, self.ai_enabled = label, False
        self.score, self.flash = 0, 0.0
        self.speed = 1500
        self.effects = {}


class ViewBall(_Box):
    is_paddle, is_ball, is_wall = False, True, False

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.diameter = 60
        self.rally_value = 0
        self.last_paddle = None
        self.blazing = False
        self.stuck = None
        self.side = None             # Twin Balls: "red" or "blue"


class ViewStone(_Box):
    is_paddle = is_ball = is_wall = False
    is_obstacle = True

    def __init__(self):
        super().__init__()
        self.k, self.style, self.speed = 1.0, "tomb", 0.0
        self.strength = 1.0          # how whole it is (Spirit Fire and the Snowball chip stones)

    def visibility(self):
        return self.k


class ViewPowerUps:
    LIFETIME, RADIUS = 14.0, 56

    def __init__(self, game):
        self.game = game
        self.pickups, self.popups, self.hops = [], [], []
        self.fx = {}, {}
        self.court = []
        self.flags = 0
        self.alpha = 1.0
        self.ball_frost = False
        self.wind, self.night, self.cracker, self.portals = 0.0, 0.0, 0, []
        self.blasts = []

    def effect_list(self, paddle):
        return self.fx[0 if paddle.is_left else 1]

    def court_list(self):
        from render.hud import SHORT
        return [(key, left, SHORT.get(key, "")) for key, left in self.court]

    def has(self, paddle, key):
        return any(k == key and left is not None for k, left, _ in self.effect_list(paddle))

    def frosted(self, paddle):
        return bool(self.flags & (32 if paddle.is_left else 64))

    def frozen(self, paddle):
        return bool(self.flags & (128 if paddle.is_left else 256))

    def ball_alpha(self, ball=None):
        return self.alpha if ball is None or ball is self.game.ball else 1.0

    def ball_frosted(self):
        return self.ball_frost

    def wall_open(self):
        return any(key == "wall" for key, _ in self.court)

    def snowball(self):
        return any(key == "snowball" for key, _ in self.court)

    def ghostly(self):
        return any(key == "ghost" for key, _ in self.court)

    def wind_force(self):
        return self.wind

    def lantern_level(self):
        return self.night

    def cracker_hits(self, ball):
        return self.cracker if ball is self.game.ball else 0


class _Countdown:
    def __init__(self, remaining, shown):
        self.remaining, self.shown_value = remaining, shown


class _Settings:
    def __init__(self, info):
        self.switch_each_point = bool(info.get("switch_each_point"))
        self.pace = float(info.get("pace", 1.0))
        self.powerups = False


class ReplayView:
    """Looks enough like a Hu_Taong match for Renderer.draw_world and Hud.draw to show a frame."""
    SWITCH_WARNING = 2.0

    def __init__(self, clip, app):
        info = clip.info
        self.app, self.clip = app, clip
        self.settings = _Settings(info)
        labels = info.get("labels", ["", ""])
        self.p1 = ViewPaddle(self, True, "Red", labels[0])
        self.p2 = ViewPaddle(self, False, "Blue", labels[1])
        self.ball = ViewBall(self)
        self.extra_balls = []           # Twin Balls' blue ball
        self.powerups = ViewPowerUps(self)
        self.stones = []
        self.objects = []
        self.remap = info.get("remap")
        self.strings = info.get("strings", [])
        self.running = True
        self.paused = False

    def kind(self, index):
        index = int(index)
        if self.remap is not None:
            index = self.remap[index] if 0 <= index < len(self.remap) else -1
        return KIND_KEYS[index] if 0 <= index < len(KIND_KEYS) else None

    def show(self, position):
        """Set everything to how it was `position` frames in (between frames is blended)."""
        frames = self.clip.frames
        i = max(0, min(len(frames) - 1, int(position)))
        a = array("f"); a.frombytes(frames[i])
        b = a
        if i + 1 < len(frames):
            b = array("f"); b.frombytes(frames[i + 1])
        t = position - i
        self.apply(a, b, t)

    def apply(self, a, b, t):
        def mixed(n, jump=150):
            va, vb = a[n], b[n]
            return va if abs(vb - va) > jump else va + (vb - va) * t

        self.p1.place(mixed(1), mixed(2), a[3], a[4])
        self.p2.place(mixed(5), mixed(6), a[7], a[8])
        ball = self.ball
        ball.place(mixed(9), mixed(10), a[11], a[11])
        ball.diameter = a[11]
        ball.vx, ball.vy = a[12], a[13]
        pu = self.powerups
        pu.alpha = a[14]
        flags = int(a[15])
        ball.blazing = bool(flags & 1)
        ball.side = "red" if flags & 32 else None
        pu.ball_frost = bool(flags & 2)
        ball.last_paddle = self.p1 if flags & 8 else self.p2 if flags & 16 else None
        self.p1.score, self.p2.score, ball.rally_value = int(a[16]), int(a[17]), int(a[18])
        state = int(a[19])
        pu.flags = state
        self.wall_up = bool(state & 1)
        self.p1.ai_enabled, self.p2.ai_enabled = bool(state & 2), bool(state & 4)
        self.countdown = _Countdown(a[20], int(a[21])) if a[20] >= 0 else None
        message = int(a[22])
        red = message in (1, 3)
        self.message_text = "" if not message else ("Red scored!" if red else "Blue scored!") + (" x2" if message > 2 else "")
        self.message_color = (255, 80, 80) if red else (60, 140, 255)
        self.switch_warning = a[23] if a[23] >= 0 else None
        self.switch_flash = a[24]
        self.switch_banner = "换 Swap!" if a[25] else "换 Switch!"
        banter = int(a[26])
        self.banter = ([self.strings[banter], self.p1 if a[27] == 1 else self.p2, a[28]]
                       if 0 <= banter < len(self.strings) else None)
        ball.stuck = None
        if a[29]:
            paddle = self.p1 if a[30] == 1 else self.p2
            k = max(0.0, min(0.999, a[31]))
            ball.stuck = {"paddle": paddle, "side": int(a[29]), "left": 1 - k, "total": 1.0}

        n_pick, n_stone, n_fx1, n_fx2, n_court, n_hops = (int(v) for v in a[32:38])
        pos = 38
        pu.pickups = []
        for _ in range(n_pick):
            key = self.kind(a[pos])
            if key:
                pu.pickups.append({"kind": key, "x": a[pos + 1], "y": a[pos + 2], "age": a[pos + 3], "phase": a[pos + 4]})
            pos += 5
        while len(self.stones) < n_stone:
            self.stones.append(ViewStone())
        del self.stones[n_stone:]
        for stone in self.stones:
            stone.place(a[pos], a[pos + 1], a[pos + 2], a[pos + 3])
            stone.k, stone.style, stone.speed = a[pos + 4], STYLES[int(a[pos + 5]) % len(STYLES)], a[pos + 6]
            pos += 7
        fx = ([], [])
        for which, count in ((0, n_fx1), (1, n_fx2)):
            for _ in range(count):
                key = self.kind(a[pos])
                if key:
                    left = None if a[pos + 1] < 0 else a[pos + 1]
                    fx[which].append((key, left, int(a[pos + 2])))
                pos += 3
        pu.fx = fx
        pu.court = []
        for _ in range(n_court):
            key = self.kind(a[pos])
            if key:
                pu.court.append((key, None if a[pos + 1] < 0 else a[pos + 1]))
            pos += 2
        pu.hops = [list(a[pos + 5 * j:pos + 5 * j + 5]) for j in range(n_hops)]
        pos += 5 * n_hops
        for paddle, items in ((self.p1, fx[0]), (self.p2, fx[1])):
            paddle.effects = {key: left for key, left, _ in items if left is not None}
        # Twin Balls' blue ball (not in replays made before it existed)
        n_extra = int(a[pos]) if pos < len(a) else 0
        pos += 1
        while len(self.extra_balls) < n_extra:
            self.extra_balls.append(ViewBall(self))
        del self.extra_balls[n_extra:]
        same = len(b) > pos + 7 * n_extra - 1 and len(b) == len(a)
        for extra in self.extra_balls:
            x, y = a[pos], a[pos + 1]
            if same and abs(b[pos] - x) < 150 and abs(b[pos + 1] - y) < 150:
                x, y = x + (b[pos] - x) * t, y + (b[pos + 1] - y) * t
            extra.place(x, y, a[pos + 2], a[pos + 2])
            extra.diameter = a[pos + 2]
            extra.vx, extra.vy = a[pos + 3], a[pos + 4]
            extra.side = "blue" if int(a[pos + 5]) == 2 else "red"
            extra.blazing = bool(a[pos + 6])
            pos += 7
        # the ball's spin, the wind, the night, the firecracker and the portals (newer frames only)
        ball.curve, pu.wind, pu.night, pu.cracker, pu.portals = 0.0, 0.0, 0.0, 0, []
        if pos + 5 <= len(a):
            ball.curve, pu.wind, pu.night, pu.cracker = a[pos], a[pos + 1], a[pos + 2], int(a[pos + 3])
            n_portals = int(a[pos + 4])
            pos += 5
            for _ in range(n_portals):
                if pos + 3 <= len(a):
                    pu.portals.append({"x": a[pos], "y": a[pos + 1], "angle": a[pos + 2]})
                pos += 3
        pu.blasts = []
        for stone in self.stones:
            stone.strength = 1.0
        if pos < len(a):
            n_blasts = int(a[pos])
            pos += 1
            for _ in range(n_blasts):
                if pos + 3 <= len(a):
                    pu.blasts.append([a[pos], a[pos + 1], a[pos + 2]])
                pos += 3
            for stone in self.stones:
                if pos < len(a):
                    stone.strength = a[pos]
                pos += 1
        self.objects = [*self.stones, self.p1, self.p2, ball, *self.extra_balls]


def replays_folder():
    from core.save_data import save_path
    return save_path().parent / "replays"


def saved_replays():
    """[(path, header)] for every replay in the folder, newest first."""
    folder = replays_folder()
    found = []
    if folder.is_dir():
        for path in folder.glob("*.htreplay"):
            try:
                header = Clip.read_header(path)
            except (OSError, ValueError, UnicodeDecodeError, struct.error):
                header = None
            if header:
                found.append((path, header))
    found.sort(key = lambda item: item[1].get("created", ""), reverse = True)
    return found


def file_name(clip, kind):
    last = array("f"); last.frombytes(clip.frames[-1])
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    return f"{stamp} {kind} Red {int(last[16])}-{int(last[17])} Blue.htreplay"
