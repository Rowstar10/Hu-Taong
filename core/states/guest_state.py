"""Playing in a friend's game: their game runs the match, this screen shows it and sends your keys.

Two clocks meet on this screen.  The host's pictures take a moment to get here, so they show the
court a little in the past, while your own paddle moves the instant you press a key, in the
present.  A ball drawn only from the pictures would reach your paddle late, so the ball is drawn
on a sliding clock: by the host's paddle it is where their pictures show it (so it meets their
paddle, drawn from the same pictures), and as it comes towards you it catches up with the present,
flown on from the newest picture, so it meets your paddle where your paddle really is.  You hit it
when it meets your paddle here; your game tells the host's at once, and the host's plays the hit
from that moment.  Here the ball flies on from your paddle until the host's pictures include it."""
import bisect, math, struct, time
from array import array

import pygame

from config import BASE_W, BASE_H, MAX_BOUNCE_ANGLE
from core import net as netcode
from core.states.base_state import State
from core.states.jukebox import JukeboxControls
from core.states.replay_state import play_event
from game.replay import Clip, Moment, ReplayView
from objects.paddle import FLAT_ANGLE
from render import theme

WARP_IN = 0.4            # seconds after a serve over which the sliding clock eases in
GLIDE = 0.07             # how quickly a corrected ball glides to where it should be
SNAP = 160               # a correction bigger than this is a jump (a Blink, a serve), not a glide
BALL_EVENTS = ("hit", "wall", "stone")     # heard when the ball is drawn there, not by the pictures' clock


class _Feed:
    """What ReplayView needs to know about where its rows come from."""
    def __init__(self, info):
        self.info, self.frames, self.events, self.moments = info, [], [], []


def held_keys(app):
    """Either set of paddle keys, as the bits the host reads."""
    keys, interface = app.keys_down, app.settings.interface
    bits = 0
    for player in ("p1", "p2"):
        k = interface.keys(player)
        bits |= (netcode.UP if k["up"] in keys else 0) | (netcode.DOWN if k["down"] in keys else 0)
        bits |= (netcode.LEFT if k["left"] in keys else 0) | (netcode.RIGHT if k["right"] in keys else 0)
    return bits


def match_clip(app, moments = ()):
    """Everything this side saw of the match so far, with the host's highlights and the sounds."""
    net = app.net
    frames = list(net.frames) if net else []
    if not frames or not net.snaps:
        return None
    clocks = [struct.unpack_from("<f", f, 0)[0] for f in frames]

    def frame_at(clock):
        return max(0, min(len(frames) - 1, bisect.bisect_left(clocks, clock)))

    found = []
    for m in moments:
        try:
            title, score, at, start, end, side = m
            found.append(Moment(str(title), float(score), frame_at(at), frame_at(start), frame_at(end), int(side)))
        except (TypeError, ValueError):
            continue
    events = [(frame_at(clock), kind, *values) for clock, kind, values in getattr(net, "event_log", [])
              if isinstance(kind, str)]
    info = dict(net.snaps[-1][2].get("info", {}))
    info["labels"] = ["Friend", "You"] if net.snaps[-1][2].get("guest", 2) == 2 else ["You", "Friend"]
    return Clip(frames, events, info, found)


def ball_in(row):
    """(centre x, centre y, vx, vy, diameter) of the ball in one of the host's pictures."""
    x0, y0, d, vx, vy = struct.unpack_from("<5f", row, 9 * 4)
    return x0 + d / 2, y0 + d / 2, vx, vy, d


class GuestMatchState(State):
    NAME = "guest_match"
    is_game = True
    dims_court = True

    def __init__(self, app):
        super().__init__(app)
        self.view = None
        self.clock = None            # where the host's pictures are shown, on the host's clock
        self.pending = []            # [(host clock, kind, values)] waiting to be heard
        self.pred = None             # your paddle as predicted: [x0, y0, vx, vy]
        self.history = []            # [(input number, x0, y0)]
        self.last_seq = 0
        self.last_snap = 0
        self.countdown_shown = None
        self.started = False
        self.bounce = None           # your save, flown on here until the host's pictures include it
        self.last_ball = None        # the ball's centre last frame, to catch a quick ball between frames
        self.claim_rest = 0.0        # a moment after a save before another can be claimed
        self.quiet_hit_until = -1.0  # the host's echo of a save heard here already
        self.tau = None              # the host time the ball is drawn at (see the top of this file)
        self.warp = 0.0              # eases from 0 to 1 after each serve
        self.basis = None            # what the ball's place was worked out from last frame
        self.offset = [0.0, 0.0]     # a correction still being glided out
        self.shown_x = None          # where the ball was drawn last frame, across the court
        self.rtt = None              # the round trip to the host, smoothed

    @property
    def net(self):
        return self.app.net

    def enter(self, **kwargs):
        super().enter(mute = True)
        self.app.sound_manager.play("startup2.wav")
        self.app.sound_manager.set_mood("game")
        self.app.fx.swarm()

    def exit(self, **kwargs):
        super().exit(mute = True)
        if not getattr(self, "keep_session", False):
            self.app.leave_online()

    def back_to_lobby(self):
        """The host went back to the lobby (to change the court or sides, say): wait there with
        them, still connected."""
        self.keep_session = True
        self.app.renderer.show_toast("Your friend went back to the lobby", important = True)
        sm = self.app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("match_setup", mute = True)
        sm.push_state("online", mute = True, resume = "guest")

    # ---------------- Each frame ----------------

    def update(self, dt):
        net = self.net
        if net is None or net.status in ("lost", "refused"):
            self.app.renderer.show_toast(net.reason if net else "The online game ended.", important = True)
            self.set_state("main_menu", mute = True)
            return
        net.keys = held_keys(self.app) if self.app.state_manager.current() is self else 0
        if not net.snaps:
            return
        newest, row, info, _ = net.snaps[-1]
        if self.view is None or (self.clock is not None and newest < self.clock - 1.0):
            self.restart(info)                      # first picture, or the host started a new match
        target = newest - net.BUFFER
        if self.clock is None:
            self.clock = target
        self.clock += dt
        self.clock += (target - self.clock) * min(1.0, 4 * dt)
        self.clock = min(self.clock, newest)

        side = info.get("guest", 2)                 # Chaos Switch can hand you the other paddle
        self.view.p1.controls_label = "You" if side == 1 else "Friend"
        self.view.p2.controls_label = "You" if side == 2 else "Friend"
        self.take_events()
        self.predict(dt, row, info)
        self.claim_rest = max(0.0, self.claim_rest - dt)
        popups = self.view.powerups.popups          # the floating names of power-ups fade as in a match
        for popup in popups:
            popup[3] += dt
        self.view.powerups.popups = [p for p in popups if p[3] < 1.4]
        if self.show(dt):
            self.play_due_events(side)
            self.watch_for_save(side, info)

        top = self.app.state_manager.current()
        if top is self:
            if info.get("over"):
                self.push_state("guest_result", mute = True)
            elif info.get("paused"):
                self.push_state("guest_pause", mute = True)

    def restart(self, info):
        meta = dict(info.get("info", {}))
        labels = ["Friend", "You"] if info.get("guest", 2) == 2 else ["You", "Friend"]
        meta["labels"] = labels
        self.view = ReplayView(_Feed(meta), self.app)
        self.clock = None
        self.pending.clear()
        self.pred = None
        self.history.clear()
        self.bounce = None
        self.calm()
        self.started = True

    def take_events(self):
        net = self.net
        for clock, row, info, _ in net.snaps[-6:]:
            for event in info.get("events", []):
                if not isinstance(event, list) or len(event) < 2:
                    continue
                if isinstance(event[0], int) and event[0] > net.played:
                    net.played = event[0]
                    self.pending.append((clock, event[1], event[2:]))
                    log = net.__dict__.setdefault("event_log", [])
                    log.append((clock, event[1], event[2:]))     # for the replay afterwards
                    del log[:-20000]

    def play_due_events(self, side):
        """Sounds and sparks, as their moment comes on screen: the ball's own (hits, bounces) when
        the ball is drawn there, everything else by the pictures' clock."""
        ball_clock = self.tau if self.tau is not None else self.clock
        keep = []
        for clock, kind, values in self.pending:
            due = ball_clock if kind in BALL_EVENTS else self.clock
            if clock > due:
                keep.append((clock, kind, values))
                continue
            if kind == "hit" and values and values[0] == side and clock <= self.quiet_hit_until:
                continue                            # heard already, the moment it happened here
            play_event(self.app, self.view, kind, values)
        self.pending = keep

    # ---------------- Your paddle ----------------

    def predict(self, dt, row, info):
        """Move your own paddle from your keys straight away, as the host's game will."""
        net = self.net
        side = info.get("guest", 2)
        a = array("f"); a.frombytes(row)
        base = 1 if side == 1 else 5
        auth = (a[base], a[base + 1])
        w, h = a[base + 2], a[base + 3]
        state = int(a[19])
        frozen = a[20] >= 0 or a[22] != 0 or info.get("paused")    # countdown, a goal, or paused
        effects = [k for k, _, _ in self.view.powerups.effect_list(self.view.p1 if side == 1 else self.view.p2)]
        if frozen or "gravity" in effects or self.pred is None:
            self.pred = [auth[0], auth[1], 0.0, 0.0]
            self.history.clear()
            return
        # A newer word from the host: compare it with where we thought we'd be by then
        if net.last_snap != self.last_snap:
            self.last_snap = net.last_snap
            ack = info.get("seq", 0)
            for i, (seq, x, y) in enumerate(self.history):
                if seq == ack:
                    ex, ey = auth[0] - x, auth[1] - y
                    if abs(ex) > 160 or abs(ey) > 160:       # a teleport or a swap: jump there
                        self.pred[0], self.pred[1] = auth
                        self.history.clear()
                    else:
                        self.pred[0] += ex * 0.35
                        self.pred[1] += ey * 0.35
                        self.history = [(s, hx + ex * 0.35, hy + ey * 0.35) for s, hx, hy in self.history[i + 1:]]
                    break
        speed = info.get("speed", [1500, 1500])[side - 1]
        pace = float(info.get("info", {}).get("pace", 1.0))
        keys = net.keys
        dx = ((keys & netcode.RIGHT) > 0) - ((keys & netcode.LEFT) > 0)
        dy = ((keys & netcode.DOWN) > 0) - ((keys & netcode.UP) > 0)
        step = min(dt, 1 / 30) * pace
        p = self.pred
        drag = math.exp(-step)
        p[2] *= drag
        p[3] *= drag
        k = 1 - math.exp(-8 * step)
        p[2] += (speed * dx - p[2]) * k
        p[3] += (speed * dy - p[3]) * k
        p[0] = max(0.0, min(BASE_W - w, p[0] + p[2] * step))
        p[1] = max(0.0, min(BASE_H - h, p[1] + p[3] * step))
        if state & 1:                                        # the Middle Wall keeps it in its half
            if side == 1:
                p[0] = min(p[0], BASE_W / 2 - w)
            else:
                p[0] = max(p[0], BASE_W / 2)
        if net.seq != self.last_seq:
            self.last_seq = net.seq
            self.history.append((net.seq, p[0], p[1]))
            del self.history[:-120]

    # ---------------- Drawing ----------------

    def show(self, dt = 0.0):
        """Set the view to the host's picture at the current clock, with your paddle where you have
        it, and the ball on its sliding clock."""
        snaps = self.net.snaps
        clocks = [s[0] for s in snaps]
        i = bisect.bisect_right(clocks, self.clock) - 1
        i = max(0, min(len(snaps) - 1, i))
        j = min(len(snaps) - 1, i + 1)
        a = array("f"); a.frombytes(snaps[i][1])
        b = array("f"); b.frombytes(snaps[j][1])
        span = clocks[j] - clocks[i]
        t = 0.0 if span <= 0 else max(0.0, min(1.0, (self.clock - clocks[i]) / span))
        try:
            self.view.apply(a, b, t)
        except (IndexError, ValueError):
            return False
        side = snaps[-1][2].get("guest", 2)
        paddle = self.view.p1 if side == 1 else self.view.p2
        was = (paddle.x0, paddle.y0)
        if self.pred:
            paddle.place(self.pred[0], self.pred[1], paddle.width, paddle.height)
            paddle.vx, paddle.vy = self.pred[2], self.pred[3]        # (it aims a Sticky Goo sling)
        self.place_ball(dt, side, clocks, was)
        return True

    # ---------------- The ball's sliding clock ----------------

    def calm(self):
        """Between points: the ball is drawn straight from the host's pictures."""
        self.warp, self.tau, self.basis, self.shown_x = 0.0, None, None, None
        self.offset = [0.0, 0.0]

    def lead(self):
        """How far the host's present is ahead of its pictures here: the hold-back for smoothing,
        plus the trip here."""
        net = self.net
        if net.ping is not None:
            self.rtt = net.ping if self.rtt is None else self.rtt + (net.ping - self.rtt) * 0.05
        rtt = self.rtt if self.rtt is not None else 0.1
        return max(0.03, min(0.35, net.BUFFER + rtt / 2 + 0.004))

    def reach(self, bx, side):
        """0 by the host's paddle, 1 by yours, and in between by how far across the ball is."""
        view = self.view
        mine, theirs = (view.p1, view.p2) if side == 1 else (view.p2, view.p1)
        my_face = mine.x1 if side == 1 else mine.x0
        their_face = theirs.x0 if side == 1 else theirs.x1
        way = -1 if side == 1 else 1                   # from their paddle towards yours
        span = my_face - their_face
        if span * way < 300:
            span = 300 * way
        return max(0.0, min(1.0, (bx - their_face) / span))

    def place_ball(self, dt, side, clocks, was):
        view = self.view
        ball = view.ball
        mine = view.p1 if side == 1 else view.p2
        if ball.stuck:
            # held on a paddle (Sticky Goo): on yours, it rides where your paddle is here
            if ball.stuck["paddle"] is mine:
                ball.place(ball.x0 + mine.x0 - was[0], ball.y0 + mine.y0 - was[1], ball.width, ball.height)
            self.calm()
            return
        if view.countdown is not None or view.message_text:
            if view.countdown is not None:
                self.bounce = None
            self.calm()
            return
        self.warp = min(1.0, self.warp + dt / WARP_IN)
        r = ball.width / 2
        lead = self.lead()
        x_then = self.shown_x if self.shown_x is not None else (ball.x0 + ball.x1) / 2
        tau = self.clock + lead * self.reach(x_then, side) * self.warp
        if self.tau is not None:
            tau = max(tau, self.tau)                   # the ball never runs backwards
        tau = min(tau, self.clock + lead)
        self.tau = tau
        basis = self.basis_for(tau, clocks, r)
        cx, cy, vx, vy = self.evaluate(basis, tau, clocks)
        if self.basis is not None and basis != self.basis:
            ox, oy, _, _ = self.evaluate(self.basis, tau, clocks)
            dx, dy = ox - cx, oy - cy
            if math.hypot(dx + self.offset[0], dy + self.offset[1]) < SNAP:
                self.offset[0] += dx                   # a nudge: glide into it
                self.offset[1] += dy
            else:
                self.offset = [0.0, 0.0]               # a Blink, a teleport, a new serve: jump
        self.basis = basis
        if dt > 0:
            k = math.exp(-dt / GLIDE)
            self.offset = [self.offset[0] * k, self.offset[1] * k]
        x, y = cx + self.offset[0], cy + self.offset[1]
        ball.place(x - r, y - r, ball.width, ball.height)
        ball.vx, ball.vy = vx, vy
        self.shown_x = x

    def basis_for(self, tau, clocks, r):
        """What to work the ball's place out from: your save (until the host's pictures include it),
        the pictures themselves, or the newest picture flown on."""
        b = self.bounce
        if b is not None:
            answer = self.net.acks.get(b["id"])
            if answer is not None and (answer < 0 or (clocks[-1] >= answer and tau >= answer)):
                self.bounce = None                     # refused, or the pictures show it now
            elif self.clock - b["t0"] > 1.0:
                self.bounce = None                     # no word: go with the pictures
            elif tau >= b["t0"]:
                return ("bounce", b["t0"], b["x"], b["y"], b["vx"], b["vy"], r)
        if tau <= clocks[-1]:
            return ("interp",)
        cx, cy, vx, vy, d = ball_in(self.net.snaps[-1][1])
        return ("fly", clocks[-1], cx, cy, vx, vy, d / 2)

    def evaluate(self, basis, tau, clocks):
        """The ball's centre and velocity at host time `tau`, worked out from `basis`."""
        if basis[0] == "interp":
            snaps = self.net.snaps
            i = bisect.bisect_right(clocks, tau) - 1
            i = max(0, min(len(snaps) - 1, i))
            j = min(len(snaps) - 1, i + 1)
            ax, ay, avx, avy, _ = ball_in(snaps[i][1])
            bx, by, bvx, bvy, _ = ball_in(snaps[j][1])
            span = clocks[j] - clocks[i]
            t = 0.0 if span <= 0 else max(0.0, min(1.0, (tau - clocks[i]) / span))
            if abs(bx - ax) > 150 or abs(by - ay) > 150:
                t = 0.0 if t < 0.5 else 1.0            # a jump between pictures: no blending across it
            return ax + (bx - ax) * t, ay + (by - ay) * t, avx + (bvx - avx) * t, avy + (bvy - avy) * t
        _, t0, x, y, vx, vy, r = basis
        return self.fly(x, y, vx, vy, r, tau - t0)

    def fly(self, cx, cy, vx, vy, r, seconds):
        """The ball flown on for `seconds` of the host's clock: straight, off the top and bottom and
        any stones, falling under Gravity.  It stops at the goal lines."""
        from game.powerups import PowerUps as PortalSize
        view = self.view
        t = max(0.0, min(0.5, seconds)) * float(view.settings.pace or 1.0)
        if t <= 0:
            return cx, cy, vx, vy
        gravity = any(key == "gravity" for fx in view.powerups.fx for key, _, _ in fx)
        stones = [(s.x0, s.y0, s.x1, s.y1) for s in view.stones if getattr(s, "k", 1) > 0.5]
        if view.powerups.alpha < 0.99 or view.powerups.ghostly():
            stones = []                                # a Ghost Ball goes through them
        steps = int(t * 240) + 1
        h = t / steps
        curve = getattr(view.ball, "curve", 0.0)            # Curveball's spin, fading as it flies
        wind = getattr(view.powerups, "wind", 0.0)           # and Wind Gust's push
        portals = getattr(view.powerups, "portals", [])
        cool = 0.0
        for _ in range(steps):
            if gravity:
                vy = max(-2400.0, min(2400.0, vy + 1500 * h))
            if curve or wind:
                vy = max(-2600.0, min(2600.0, vy + (curve + wind) * h))
                curve *= math.exp(-1.3 * h)
            cool = max(0.0, cool - h)
            if portals and cool <= 0:
                for i, door in enumerate(portals):
                    if math.hypot(cx - door["x"], cy - door["y"]) <= PortalSize.PORTAL_R * 0.6:
                        out = portals[1 - i] if len(portals) > 1 else door
                        dx, dy = math.cos(out["angle"]), math.sin(out["angle"])
                        speed = math.hypot(vx, vy)
                        cx, cy = out["x"] + dx * (PortalSize.PORTAL_R * 0.5 + r), out["y"] + dy * (PortalSize.PORTAL_R * 0.5 + r)
                        vx, vy = speed * dx, speed * dy
                        cool = 0.35
                        break
            nx, ny = cx + vx * h, cy + vy * h
            if ny < r:
                ny, vy = 2 * r - ny, abs(vy)
            elif ny > BASE_H - r:
                ny, vy = 2 * (BASE_H - r) - ny, -abs(vy)
            for x0, y0, x1, y1 in stones:
                if x0 - r < nx < x1 + r and y0 - r < ny < y1 + r:
                    if cx <= x0 - r or cx >= x1 + r:
                        vx, nx = -vx, cx
                    else:
                        vy, ny = -vy, cy
                    break
            cx, cy = nx, ny
            if cx < r or cx > BASE_W - r:
                cx = max(r, min(BASE_W - r, cx))
                break
        return cx, cy, vx, vy

    # ---------------- Your saves ----------------

    def watch_for_save(self, side, info):
        """Did the ball meet your paddle on this screen?  If so, tell the host at once (it decides
        hits on your paddle by what you saw), and fly the ball on from your paddle here."""
        net, view = self.net, self.view
        ball = view.ball
        paddle = view.p1 if side == 1 else view.p2
        r = ball.width / 2
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        last, self.last_ball = self.last_ball, (bx, by)
        if self.bounce or self.claim_rest > 0 or view.countdown is not None or view.message_text or ball.stuck:
            return
        if self.pred is None or self.tau is None:
            return
        pvx, pvy = self.pred[2], self.pred[3]
        overlap = (ball.x1 > paddle.x0 and ball.x0 < paddle.x1 and ball.y1 > paddle.y0 and ball.y0 < paddle.y1)
        if not overlap and last is not None:
            # a quick ball can skip right over the paddle between frames: did it cross a face?
            for face in (paddle.x0 - r, paddle.x1 + r):
                if (last[0] - face) * (bx - face) < 0:
                    t = (face - last[0]) / (bx - last[0])
                    y = last[1] + (by - last[1]) * t
                    if paddle.y0 - r < y < paddle.y1 + r:
                        overlap, bx, by = True, face, y
                    break
        if not overlap:
            return
        cx, cy = (paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2
        if paddle.y0 <= by <= paddle.y1 or abs(bx - cx) > paddle.width / 2:
            normal = (-1, 0) if bx > cx else (1, 0)
        else:
            normal = (0, -1) if by > cy else (0, 1)
        if (pvx - ball.vx) * normal[0] + (pvy - ball.vy) * normal[1] >= 0:
            return                                  # moving apart already
        vx, vy, bx, by = self.bounce_off(paddle, side, normal, bx, by, r, ball.vx, ball.vy, pvx, pvy)
        net.claim_id += 1
        net.claims.append({"id": net.claim_id, "t": round(self.tau, 4), "bx": round(bx, 1), "by": round(by, 1),
                           "px": round(paddle.x0, 1), "py": round(paddle.y0, 1), "pvx": round(pvx), "pvy": round(pvy),
                           "normal": list(normal), "vx": round(vx, 1), "vy": round(vy, 1)})
        net.send_input()                            # straight away, not with the next keys
        net.last_send = time.perf_counter()
        self.claim_rest = 0.25
        sticky = any(k == "sticky" for k, _, _ in view.powerups.effect_list(paddle))
        if not sticky:                              # a Sticky paddle holds it instead: the host shows that
            self.bounce = {"id": net.claim_id, "t0": self.tau, "x": bx, "y": by, "vx": vx, "vy": vy}
        self.quiet_hit_until = self.tau + 0.8
        sound = self.app.sound_manager
        if sound.paddle_hit_sound:
            sound.play("Hu.wav" if side == 1 else "Tao.wav")
        paddle.flash = 1.0
        self.app.fx.spark(bx, by, 22, (255, 122, 44) if side == 1 else (120, 190, 255), speed = 520)

    @staticmethod
    def bounce_off(paddle, side, normal, bx, by, r, bvx, bvy, pvx, pvy):
        """The ball off your paddle, as the host's game plays a hit (objects/paddle.py): angled by
        where on the paddle it met, and always leaving faster than the paddle chases it.  Answers
        (vx, vy, x, y), the ball just clear of the face it met."""
        speed = max(1.0, math.hypot(bvx, bvy))
        cy = (paddle.y0 + paddle.y1) / 2
        if normal[0]:
            offset = max(-1.0, min(1.0, (by - cy) / (paddle.height / 2)))
            angle = offset * MAX_BOUNCE_ANGLE
            if abs(angle) < FLAT_ANGLE:
                angle = math.copysign(1.5 * FLAT_ANGLE, angle or 1.0)
            vx, vy = -normal[0] * speed * math.cos(angle), speed * math.sin(angle)
            bx = paddle.x1 + r if normal[0] < 0 else paddle.x0 - r
        else:
            forward = 1 if side == 1 else -1
            vx = forward * speed * math.cos(MAX_BOUNCE_ANGLE)
            vy = -normal[1] * speed * math.sin(MAX_BOUNCE_ANGLE)
            by = paddle.y1 + r if normal[1] < 0 else paddle.y0 - r
        out_x, out_y = -normal[0], -normal[1]
        chasing = pvx * out_x + pvy * out_y
        leaving = vx * out_x + vy * out_y
        need = chasing + 150
        if chasing > 0 and 0 < leaving < need:
            vx, vy = vx * need / leaving, vy * need / leaving
        return vx, vy, bx, by

    # ---------------- Drawing ----------------

    def draw(self, screen):
        super().draw(screen)
        renderer = self.app.renderer
        net = self.net
        if net is None or not net.snaps or self.view is None or self.clock is None or not self.show():
            renderer.draw_online_waiting(screen, "Joining your friend's game...")
            return
        # the serve countdown ticks here too
        cd = self.view.countdown
        shown = cd.shown_value if cd else None
        if shown != self.countdown_shown:
            if shown is None and self.countdown_shown is not None:
                self.app.sound_manager.play("countdown_go.wav")
            elif shown is not None:
                self.app.sound_manager.play("countdown_tick.wav")
            self.countdown_shown = shown
        renderer.draw_world(screen, self.view)
        self.app.hud.draw(self, screen, self.view, live=True)
        renderer.draw_ping(screen, net.ping)

    def handle_event(self, event):
        super().handle_event(event)
        net = self.net
        if net is None:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            net.request("pause")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hit_test(self.app.window_to_base(event.pos)) == "pause":
                net.request("pause")


class GuestPauseState(JukeboxControls, State):
    """The match is paused (by either player): resume it for both, or leave."""
    NAME = "guest_pause"
    is_menu = True
    is_overlay = True

    def __init__(self, app):
        super().__init__(app)
        self.ui_cols = 2
        self.init_jukebox()

    def enter(self, **kwargs):
        if self.app.net:
            self.app.net.keys = 0                   # let go of the paddle while the menu is up
        sound = self.app.sound_manager
        sound.play("startup2.wav")
        sound.multiplier = 0.3
        sound.update_music_volume()

    def exit(self, **kwargs):
        super().exit(mute = True)
        sound = self.app.sound_manager
        sound.multiplier = 1
        sound.update_music_volume()

    def update(self, dt):
        net = self.app.net
        if net is None or net.status != "playing" or not net.snaps:
            return                                  # leaving, or off to the lobby: that's seen to elsewhere
        if not net.snaps[-1][2].get("paused"):
            self.pop_state(mute = True)

    def draw(self, screen):
        super().draw(screen)
        buttons = [("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                   ("restart", "Restart?", theme.BLUE, theme.BLUE_HOVER),
                   ("watch_replay", "Replay", theme.ORANGE, theme.ORANGE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("leave", "Leave Match", theme.RED, theme.RED_HOVER)]
        net = self.app.net
        header = lambda: ("Your friend is in the settings..." if net and net.snaps and
                          net.snaps[-1][2].get("host_menu") == 2 else "The match is paused for both of you")
        self.app.renderer.draw_overlay(self, screen, title = "Paused", header = header,
                                       buttons = buttons, mark = "停", jukebox = True,
                                       tips = {"resume": "Resume\nCarry on the match, for both of you.\n~ Esc",
                                               "restart": "Restart\nAsk your friend to start this match again from 0-0.",
                                               "watch_replay": "Replay\nWatch the match so far, and save all or part of it.",
                                               "settings": "Settings\nDisplay, sound and interface. The match waits.\n"
                                                           "• The host's Gameplay settings are used online",
                                               "leave": "Leave Match\nStop playing and go back to the menu."})
        self.draw_jukebox_extras(screen)

    def handle_event(self, event):
        if self.track_list:
            self.handle_track_list(event)
            return
        super().handle_event(event)
        key = self.hit_test(self.app.window_to_base(event.pos)) if hasattr(event, "pos") else None
        if self.handle_jukebox(event, key if event.type == pygame.MOUSEBUTTONDOWN else None):
            return
        net = self.app.net
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and net:
            net.request("resume")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if key == "resume" and net:
                net.request("resume")
            if key == "restart" and net:
                net.request("restart")
                self.app.renderer.show_toast("Asked your friend to restart the match")
            if key == "watch_replay":
                clip = match_clip(self.app)
                if clip is None:
                    self.app.renderer.show_toast("Nothing was recorded yet")
                else:
                    self.push_state("replay", clip = clip, mode = "viewer", mute = True)
            if key == "settings":
                self.push_state("settings")
            if key == "leave":
                action = lambda: self.set_state("main_menu", mute = True)
                self.push_state("confirm_choice", action = action, header = "Leave the match?", mute = True)


class GuestResultState(JukeboxControls, State):
    """The host's game has ended the match: the result, the highlights (which play by themselves,
    as after any match), the whole replay, a rematch, or leave."""
    NAME = "guest_result"
    is_menu = True
    is_overlay = True

    def __init__(self, app):
        super().__init__(app)
        self.ui_cols = 2
        self.init_jukebox()
        net = app.net
        self.over = dict(net.snaps[-1][2].get("over") or {}) if net and net.snaps else {}
        self.side = net.snaps[-1][2].get("guest", 2) if net and net.snaps else 2
        self.won = self.over.get("winner") == self.side
        self.asked = False
        self.reel_shown = False

    def enter(self, **kwargs):
        if self.app.net:
            self.app.net.keys = 0
        sound = self.app.sound_manager
        sound.play("you_win.wav" if self.won else "you_lose.wav")
        sound.set_mood("victory" if self.won else "defeat")
        app = self.app
        app.stats.record_online(self.won)
        from core import save_data
        save_data.save(app)
        tint = "red" if self.over.get("winner") == 1 else "blue"
        app.fx.burst(BASE_W / 2 - 430, BASE_H / 2, 22 if self.won else 6, 64, tint, arc = (2.2, 4.1))
        app.fx.burst(BASE_W / 2 + 430, BASE_H / 2, 22 if self.won else 6, 64, tint, arc = (-.95, .95))

    def update(self, dt):
        net = self.app.net
        if net is None or net.status != "playing":
            return                                  # leaving, or off to the lobby: that's seen to elsewhere
        if not net.snaps or not net.snaps[-1][2].get("over"):
            self.app.sound_manager.set_mood("game")
            self.pop_state(mute = True)               # the host started the rematch
            return
        # the match's highlights play by themselves, as after any match (Settings > Interface > Replays)
        if not self.reel_shown:
            self.reel_shown = True
            clip = self.clip()
            if self.app.settings.interface.instant_replay in (2, 3) and clip and clip.moments:
                self.push_state("replay", clip = clip, mode = "reel", mute = True)

    def clip(self):
        return match_clip(self.app, self.over.get("moments", []))

    def draw(self, screen):
        super().draw(screen)
        score = self.over.get("score", [0, 0])
        winner = "Red" if self.over.get("winner") == 1 else "Blue"
        header = [("Red: ", theme.color("Red")), (f"{score[0]}      ", theme.PARCHMENT),
                  ("Blue: ", theme.color("Blue")), (f"{score[1]}", theme.PARCHMENT)]
        buttons = [("rematch", "Rematch?" if not self.asked else "Asked...", theme.GREEN, theme.GREEN_HOVER),
                   ("watch_replay", "Replay", theme.ORANGE, theme.ORANGE_HOVER),
                   ("highlights", "Highlights", theme.ORANGE, theme.ORANGE_HOVER),
                   ("settings", "Settings", theme.WHITE, theme.WHITE_HOVER),
                   ("leave", "Leave", theme.RED, theme.RED_HOVER)]
        self._laid = None if getattr(self, "_asked_drawn", None) != self.asked else getattr(self, "_laid", None)
        self._asked_drawn = self.asked
        self.app.renderer.draw_overlay(
            self, screen, title = "You Win!" if self.won else f"{winner} Wins!", header = header, buttons = buttons,
            title_size = 0.1, title_color = theme.color(winner), mark = "胜" if self.won else "败", jukebox = True,
            tips = {"rematch": "Rematch\nAsk your friend for another match. It starts when they agree.",
                    "watch_replay": "Replay\nWatch this match again, and save all or part of it.",
                    "highlights": "Highlights\nThe best moments of this match.",
                    "settings": "Settings\nDisplay, sound and interface, then back here.",
                    "leave": "Leave\nStop playing and go back to the menu."})
        self.draw_jukebox_extras(screen)

    def handle_event(self, event):
        if self.track_list:
            self.handle_track_list(event)
            return
        super().handle_event(event)
        key = self.hit_test(self.app.window_to_base(event.pos)) if hasattr(event, "pos") else None
        if self.handle_jukebox(event, key if event.type == pygame.MOUSEBUTTONDOWN else None):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            net = self.app.net
            if key == "rematch" and net and not self.asked:
                net.request("rematch")
                self.asked = True
                self.app.renderer.show_toast("Asked your friend for a rematch")
            if key in ("watch_replay", "highlights"):
                clip = self.clip()
                if clip is None:
                    self.app.renderer.show_toast("Nothing was recorded")
                elif key == "watch_replay":
                    self.push_state("replay", clip = clip, mode = "viewer", mute = True)
                elif clip.moments:
                    self.push_state("replay", clip = clip, mode = "reel", mute = True)
                else:
                    self.app.renderer.show_toast("No highlights this time")
            if key == "settings":
                self.push_state("settings")
            if key == "leave":
                self.set_state("main_menu", mute = True)
