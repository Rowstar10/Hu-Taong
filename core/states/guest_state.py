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
from types import SimpleNamespace

import pygame

from config import BASE_W, BASE_H, MAX_BOUNCE_ANGLE
from core import net as netcode
from core.states.base_state import State
from core.states.jukebox import JukeboxControls
from core.states.replay_state import play_event
from game.powerups import PowerUps
from game.replay import Clip, Moment, ReplayView
from objects.paddle import FLAT_ANGLE
from render import theme

WARP_IN = 0.4            # seconds after a serve over which the sliding clock eases in
GLIDE = 0.07             # how quickly a corrected ball glides to where it should be
SNAP = 160               # a correction bigger than this is a jump (a Blink, a serve), not a glide
RUN_ON = 0.1             # seconds the picture clock may run on past the newest picture when they stop coming
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
        self.pred_gravity = False    # ...under Gravity (it falls, and Up jumps)
        self.jump_held = None        # ...and how long Up has been held into a jump
        self.teleport_hold = None    # a Safety Teleport made here: until then the host's word can't pull the paddle back
        self.teleport_claim = False  # ...and the save it made is still to be claimed
        self.quiet_teleport_until = -1.0   # the host's echo of that teleport, heard here already
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
        if net is not None and net.status == "lost" and net.snaps:
            return                                  # the host left mid-match: the app shows the result screen
        if net is None or net.status in ("lost", "refused"):
            self.app.renderer.show_toast(net.reason if net else "The online game ended.", important = True)
            self.set_state("main_menu", mute = True)
            return
        net.keys = held_keys(self.app) if self.app.state_manager.current() is self else 0
        touch = self.app.touch        # on a phone, a finger on your paddle (core/touch.py)
        net.axis = (touch.guest_axis(self, getattr(self, "own_speed", 1500))
                    if touch and self.app.state_manager.current() is self else None)
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
        # When pictures are late (a lost one, a spike), the clock runs on a moment past the newest
        # instead of stopping on it: the host's side holds its last picture, but the ball's own
        # clock (which leads this one) keeps it flying on instead of freezing in mid-air.  Once
        # pictures come again the clock is ahead of its target and eases back, running a touch slow.
        self.clock = min(self.clock, newest + RUN_ON)

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
            self.watch_for_teleport(side)
            self.watch_for_save(side, info)
            # tell the host how far on the ball is shown here, so a goal it holds for word of a
            # save can be let go as soon as this screen has shown the ball reach the goal without one
            net.ball_clock = self.tau if self.tau is not None else self.clock

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
        self.teleport_hold, self.teleport_claim = None, False
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
            if kind == "teleport" and values and values[0] == side and self.clock <= self.quiet_teleport_until:
                continue                            # your own teleport, made (and heard) here already
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
        gravity = "gravity" in effects
        self.own_box = (auth[0], auth[1], w, h)
        self.own_speed = info.get("speed", [1500, 1500])[side - 1]
        if frozen or self.pred is None or gravity != self.pred_gravity:
            # (Gravity starting or ending: start again from where the host has it)
            self.pred = [auth[0], auth[1], 0.0, 0.0]
            self.pred_gravity, self.jump_held = gravity, None
            self.history.clear()
            return
        # Where the paddle was when the last input went out: those are the keys that input
        # carries, so that is where the host's game will have it once it has used them.  (Noted
        # after this frame's move, it was a frame ahead of the host, so every correction pulled
        # the paddle back while it moved, and on again after it stopped.)
        if net.seq != self.last_seq:
            self.last_seq = net.seq
            self.history.append((net.seq, self.pred[0], self.pred[1]))
            del self.history[:-120]
        # A newer word from the host: compare it with where we thought we'd be by then (not while
        # a Safety Teleport made here is on its way to the host: its word would pull the paddle back)
        if self.teleport_hold is not None:
            if math.hypot(auth[0] - self.pred[0], auth[1] - self.pred[1]) < 160 or self.clock > self.teleport_hold:
                self.teleport_hold = None              # the host has it there too (or it never came)
                self.history.clear()
        if net.last_snap != self.last_snap and self.teleport_hold is None:
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
        if net.axis is not None:
            dx, dy = net.axis                                # a finger: what the host's paddle averages to
        step = min(dt, 1 / 30) * pace
        p = self.pred
        self.jump_held = self.step_paddle(p, dx, dy, speed, w, h, step, gravity, self.jump_held)
        self.own_box = (p[0], p[1], w, h)
        if state & 1:                                        # the Middle Wall keeps it in its half
            if side == 1:
                p[0] = min(p[0], BASE_W / 2 - w)
            else:
                p[0] = max(p[0], BASE_W / 2)

    @staticmethod
    def step_paddle(p, dx, dy, speed, w, h, step, gravity = False, jump = None):
        """One frame of your paddle on your keys, as the host's game moves it: Physics.step's drag,
        then Paddle.apply_inputs, and under Gravity Paddle.gravity_jump (it falls, and Up jumps:
        a tap hops, holding climbs on).  `p` is [x, y, vx, vy], moved in place; `jump` is how long
        Up has been held into a jump (None on the floor or falling), and the new one is answered.
        tests/test_powerup_online.py checks it against the host's own paddle."""
        drag = math.exp(-step)
        p[2] *= drag
        p[3] *= drag
        k = 1 - math.exp(-8 * step)
        p[2] += (speed * dx - p[2]) * k
        if gravity:
            vy = p[3] / drag                                  # a clean fall: no drag
            g = PowerUps.PADDLE_GRAVITY
            up = dy < -0.3
            if p[1] + h >= BASE_H - 0.5 and up and vy >= -1 and jump is None:
                vy, jump = -PowerUps.JUMP, 0.0                # off the floor
            elif jump is not None:
                if up and vy < 0 and jump < PowerUps.JUMP_HOLD:
                    jump += step                              # still holding: climbs on
                    g *= PowerUps.HOLD_GRAVITY
                else:
                    if not up and vy < -PowerUps.JUMP_CUT:
                        vy = -PowerUps.JUMP_CUT               # let go early: the climb is cut short
                    jump = None
            p[3] = vy + g * step
        else:
            jump = None
            p[3] += (speed * dy - p[3]) * k
        p[0] = max(0.0, min(BASE_W - w, p[0] + p[2] * step))
        y = p[1] + p[3] * step
        if gravity and not 0.0 <= y <= BASE_H - h:
            p[3] = 0.0                                        # the floor (or the top) stops it dead
        p[1] = max(0.0, min(BASE_H - h, y))
        return jump

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
        plus the trip here (the quickest of late: a stall shouldn't send the ball on ahead)."""
        net = self.net
        trip = net.quick_trip()
        if trip is not None:
            self.rtt = trip if self.rtt is None else self.rtt + (trip - self.rtt) * 0.05
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

    def watch_for_teleport(self, side):
        """Safety Teleport, judged on this screen as your saves are: the ball about to slip past your
        paddle here (not on the host's late copy of it, which fired it on saves you were making)
        blinks your paddle in front of it.  The save it then makes tells the host it teleported."""
        view = self.view
        ball = view.ball
        paddle = view.p1 if side == 1 else view.p2
        if self.pred is None or self.tau is None or self.bounce or ball.stuck:
            return
        if view.countdown is not None or view.message_text or self.teleport_hold is not None:
            return
        if not any(key == "teleport" and charges for key, _, charges in view.powerups.effect_list(paddle)):
            return
        if getattr(ball, "side", None) == ("red" if paddle.is_left else "blue"):
            return                                  # Twin Balls: your own colour can't score on you
        toward = -1 if paddle.is_left else 1
        if ball.vx * toward <= 0:
            return
        to_goal = ball.x0 if paddle.is_left else BASE_W - ball.x1
        if to_goal > abs(ball.vx) * PowerUps.TELEPORT_WARNING + 40 or PowerUps.covered(paddle, ball):
            return
        old = ((paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2)
        w, h = paddle.width, paddle.height
        x0 = ball.x0 - 6 - w if paddle.is_left else ball.x1 + 6
        y0 = (ball.y0 + ball.y1) / 2 - h / 2
        x0, y0 = max(0.0, min(BASE_W - w, x0)), max(0.0, min(BASE_H - h, y0))
        self.pred[:] = [x0, y0, 0.0, 0.0]
        paddle.place(x0, y0, w, h)
        paddle.vx = paddle.vy = 0.0
        self.history.clear()
        self.last_ball = None                       # no sweep across the jump for a save
        self.teleport_hold = self.clock + 1.0
        self.teleport_claim = True
        self.quiet_teleport_until = self.clock + 1.5
        tint = "red" if paddle.is_left else "blue"
        for x, y in (old, (x0 + w / 2, y0 + h / 2)):
            self.app.fx.burst(x, y, 10, 48, tint, life = (.5, .9))
        self.app.sound_manager.play("hmyoop!.wav")

    def watch_for_save(self, side, info):
        """Did the ball meet your paddle on this screen?  If so, tell the host at once (it decides
        hits on your paddle by what you saw), and fly the ball on from your paddle here."""
        net, view = self.net, self.view
        ball = view.ball
        paddle = view.p1 if side == 1 else view.p2
        r = ball.width / 2
        bx, by = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        w, h = paddle.width, paddle.height
        last, self.last_ball = self.last_ball, (bx, by, self.tau, paddle.x0, paddle.y0)
        if self.bounce or self.claim_rest > 0 or view.countdown is not None or view.message_text or ball.stuck:
            return
        if self.pred is None or self.tau is None:
            return
        pvx, pvy = self.pred[2], self.pred[3]
        met = None
        if last is not None and last[2] is not None:
            # Where the ball went against the paddle since last frame (both may have moved): the
            # first face it crossed on the way is where they met, however far it went in one frame.
            # (Only looking at where it ended up let a quick ball, or any ball after a hitch, pass
            # right through, or meet the paddle's back.)
            met = self.meet(r, w, h, (last[0] - last[3], last[1] - last[4]), (bx - paddle.x0, by - paddle.y0))
        if met is not None:
            k, normal = met
            px, py = last[3] + (paddle.x0 - last[3]) * k, last[4] + (paddle.y0 - last[4]) * k
            bx, by = last[0] + (bx - last[0]) * k, last[1] + (by - last[1]) * k
            tau = last[2] + (self.tau - last[2]) * k
        elif ball.x1 > paddle.x0 and ball.x0 < paddle.x1 and ball.y1 > paddle.y0 and ball.y0 < paddle.y1:
            # touching already (since last frame, or this is the first): judged by where its centre is
            px, py, tau = paddle.x0, paddle.y0, self.tau
            cx, cy = px + w / 2, py + h / 2
            if py <= by <= py + h or abs(bx - cx) > w / 2:
                normal = (-1, 0) if bx > cx else (1, 0)
            else:
                normal = (0, -1) if by > cy else (0, 1)
        else:
            return
        if (pvx - ball.vx) * normal[0] + (pvy - ball.vy) * normal[1] >= 0:
            return                                  # moving apart already
        effects = view.powerups.effect_list(paddle)
        mine_fx = [k for k, _, _ in effects]
        lively = any(key == "gravity" for fx in view.powerups.fx for key, _, _ in fx)
        at = SimpleNamespace(x0 = px, y0 = py, x1 = px + w, y1 = py + h, width = w, height = h)   # where they met
        serve = float(info.get("serve", 0.0) or 0.0)
        # Swift Step: the host plays a hit as if the paddle went at its normal top speed
        frozen = any(k == "frost" and left is not None for k, left, _ in effects)
        factor = (PowerUps.SWIFT if "swift" in mine_fx else 1.0) * (PowerUps.FROZEN if frozen else 1.0)
        speed = getattr(self, "own_speed", 0)
        top = speed / factor if factor > 1 and speed else math.inf
        if serve:
            vx, vy, bx, by = self.bounce_off(at, side, normal, bx, by, r, ball.vx, ball.vy, pvx, pvy, serve = serve,
                                             lively = lively, fire = "fire" in mine_fx, top = top)
        else:       # a host on an earlier 1.5 doesn't send its serve speed, and expects the simpler bounce
            vx, vy, bx, by = self.simple_bounce(at, side, normal, bx, by, r, ball.vx, ball.vy, pvx, pvy)
        net.claim_id += 1
        claim = {"id": net.claim_id, "t": round(tau, 4), "bx": round(bx, 1), "by": round(by, 1),
                 "px": round(px, 1), "py": round(py, 1), "pvx": round(pvx), "pvy": round(pvy),
                 "normal": list(normal), "vx": round(vx, 1), "vy": round(vy, 1), "rule": 2 if serve else 1}
        if getattr(self, "teleport_claim", False) and getattr(self, "teleport_hold", None) is not None:
            claim["teleport"] = 1                   # the save your Safety Teleport made here
            self.teleport_claim = False
        net.claims.append(claim)
        net.send_input()                            # straight away, not with the next keys
        net.last_send = time.perf_counter()
        self.claim_rest = 0.25
        sticky = any(k == "sticky" for k, _, _ in view.powerups.effect_list(paddle))
        if not sticky:                              # a Sticky paddle holds it instead: the host shows that
            self.bounce = {"id": net.claim_id, "t0": tau, "x": bx, "y": by, "vx": vx, "vy": vy}
        self.quiet_hit_until = self.tau + 0.8
        sound = self.app.sound_manager
        if sound.paddle_hit_sound:
            sound.play("Hu.wav" if side == 1 else "Tao.wav")
        paddle.flash = 1.0
        self.app.fx.spark(bx, by, 22, (255, 122, 44) if side == 1 else (120, 190, 255), speed = 520)

    @staticmethod
    def meet(r, w, h, a, b):
        """A ball (reaching r either side of its centre) going from a to b, measured from the top
        left of a paddle w by h: where it first touches the paddle, as (share of the way there,
        normal into the face it crossed), or None if it misses, or was touching it already."""
        lo, hi = (-r, -r), (w + r, h + r)
        if lo[0] < a[0] < hi[0] and lo[1] < a[1] < hi[1]:
            return None
        enter, leave, axis = 0.0, 1.0, None
        for i in (0, 1):
            d = b[i] - a[i]
            if d == 0:
                if not lo[i] < a[i] < hi[i]:
                    return None
                continue
            t0, t1 = sorted(((lo[i] - a[i]) / d, (hi[i] - a[i]) / d))
            if t0 > enter:
                enter, axis = t0, i
            leave = min(leave, t1)
        if axis is None or enter >= leave:
            return None
        way = 1 if b[axis] > a[axis] else -1
        return enter, ((way, 0) if axis == 0 else (0, way))

    @staticmethod
    def simple_bounce(paddle, side, normal, bx, by, r, bvx, bvy, pvx, pvy):
        """The bounce as 1.5 first worked it out (the ball keeps its speed), for a host on that build:
        it keeps a bounce within a third of its own, and this is what it expects."""
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
        if chasing > 0 and 0 < leaving < need and normal[0]:
            vx, vy = vx * need / leaving, vy * need / leaving
        return vx, vy, bx, by

    @staticmethod
    def bounce_off(paddle, side, normal, bx, by, r, bvx, bvy, pvx, pvy, serve = 0.0, lively = False, fire = False,
                   top = math.inf):
        """The ball off your paddle, as the host's game plays a hit (Physics.resolve_collision, then
        objects/paddle.py on_contact): the knock takes pace off a blocked ball (never below its
        serve speed), it's angled by where on the paddle it met, eased under the speed ceiling, and
        off the face always leaves faster than the paddle chases it.  `top` is the paddle's normal
        top speed when Swift Step has it going faster: its hits are played as if at that speed.
        Answers (vx, vy, x, y), the ball just clear of the face it met.  It must match the host
        exactly: tests/test_online_hits.py checks it does, against the host's own code."""
        from config import MAX_BALL_SPEEDUP
        from objects.paddle import SPEED_KNEE
        nx, ny = normal
        # the knock, as Physics.resolve_collision plays it: paddle inv_mass 0.05, ball 1,
        # restitution the average of the paddle's 0.6 and the ball's (1.2 under Gravity, else 0.4)
        res = (0.6 + (1.2 if lively else 0.4)) / 2
        rvn = (pvx - bvx) * nx + (pvy - bvy) * ny
        kvx, kvy, qvx, qvy = bvx, bvy, pvx, pvy
        if rvn <= 0:
            imp = -(1 + res) * rvn / 1.05
            kvx, kvy = bvx - imp * nx, bvy - imp * ny
            qvx, qvy = pvx + imp * nx * 0.05, pvy + imp * ny * 0.05
        drive = -(pvx * nx + pvy * ny)
        if nx and drive > top:                                 # Swift Step: knocked as if at its normal speed
            cvx, cvy = pvx + nx * (drive - top), pvy + ny * (drive - top)
            crvn = (cvx - bvx) * nx + (cvy - bvy) * ny
            kvx, kvy = bvx, bvy
            if crvn <= 0:
                cimp = -(1 + res) * crvn / 1.05
                kvx, kvy = bvx - cimp * nx, bvy - cimp * ny
        speed = max(math.hypot(kvx, kvy), serve)
        if ny:
            speed = max(math.hypot(bvx, bvy), serve)          # off an end it keeps the speed it came in at
        cap = MAX_BALL_SPEEDUP * serve * math.sqrt(2)
        knee = SPEED_KNEE * cap
        if serve and speed > knee:
            speed = knee + (cap - knee) * math.tanh((speed - knee) / (cap - knee))
        cy = (paddle.y0 + paddle.y1) / 2
        forward = 1 if side == 1 else -1
        pinched = False
        if nx:
            offset = max(-1.0, min(1.0, (by - cy) / (paddle.height / 2)))
            angle = offset * MAX_BOUNCE_ANGLE
            if abs(angle) < FLAT_ANGLE:
                angle = math.copysign(1.5 * FLAT_ANGLE, angle or 1.0)
            vx, vy = -nx * speed * math.cos(angle), speed * math.sin(angle)
            bx = paddle.x1 + r if nx < 0 else paddle.x0 - r
        else:
            vx = forward * speed * math.cos(MAX_BOUNCE_ANGLE)
            vy = -ny * speed * math.sin(MAX_BOUNCE_ANGLE)
            room = paddle.y0 if ny > 0 else BASE_H - paddle.y1
            if room < 2 * r + 6:                               # no room by the wall: out along it
                pinched = True
                vx, vy = forward * speed, 0.0
            by = paddle.y1 + r if ny < 0 else paddle.y0 - r
        out_x, out_y = -nx, -ny
        chasing = qvx * out_x + qvy * out_y
        leaving = vx * out_x + vy * out_y
        need = chasing + 150
        want = max(need, min(min(chasing, top) * 1.3, cap if serve else math.inf))
        if chasing > 0 and leaving < want and not pinched and ny == 0:
            total = math.hypot(vx, vy)
            share = leaving / total if total and leaving > 0 else 0.0
            limit = max(cap, need) if serve else math.inf
            new_speed = min(limit, want / share) if share else need
            normal_part = max(need, new_speed * share)
            new_speed = max(new_speed, normal_part)
            side_x, side_y = vx - out_x * leaving, vy - out_y * leaving
            side_len = math.hypot(side_x, side_y)
            keep = math.sqrt(max(0.0, new_speed * new_speed - normal_part * normal_part)) / side_len if side_len else 0.0
            vx, vy = out_x * normal_part + side_x * keep, out_y * normal_part + side_y * keep
        total = math.hypot(vx, vy)
        if total and abs(vx) < total * 0.3:
            vx = forward * total * 0.3
            vy = math.copysign(total * math.sqrt(1 - 0.09), vy or -1)
        if fire:                                               # Spirit Fire: every hit a blazing shot...
            vx, vy = vx * PowerUps.FIRE, vy * PowerUps.FIRE
            limit = PowerUps.FIRE_TOP * cap                    # ...a little past the top speed at most
            total = math.hypot(vx, vy)
            if serve and total > limit:
                vx, vy = vx * limit / total, vy * limit / total
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

    def __init__(self, app, left = None):
        super().__init__(app)
        self.ui_cols = 2
        self.init_jukebox()
        net = app.net
        self.over = dict(net.snaps[-1][2].get("over") or {}) if net and net.snaps else {}
        self.side = net.snaps[-1][2].get("guest", 2) if net and net.snaps else 2
        self.won = self.over.get("winner") == self.side
        self.asked = False
        self.reel_shown = False
        # The host left (or went quiet) mid-match: it ends where it was, with no winner, and
        # doesn't count in the stats.  The score is the last one this side saw.
        self.left = left
        if left:
            match = app.state_manager.get_state(GuestMatchState)
            view = match.view if match else None
            self.over = {"score": [view.p1.score, view.p2.score] if view else [0, 0]}

    def host_gone(self):
        """The host has left: no rematch to ask for."""
        net = self.app.net
        return bool(self.left) or net is None or net.status != "playing"

    def enter(self, **kwargs):
        if self.app.net:
            self.app.net.keys = 0
        if self.left:
            self.app.sound_manager.play("shutdown.wav")
            self.app.sound_manager.set_mood("menu")
            return
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
        gone = self.host_gone()
        if gone:                                    # nobody to ask for a rematch: watch, save, then go
            buttons = [b for b in buttons if b[0] != "rematch"]
            if self.left:                           # highlights come from the host, at the end of a match
                buttons = [b for b in buttons if b[0] != "highlights"]
                buttons[-1] = ("leave", "Main Menu", theme.RED, theme.RED_HOVER)
        drawn = (self.asked, gone)
        self._laid = None if getattr(self, "_asked_drawn", None) != drawn else getattr(self, "_laid", None)
        self._asked_drawn = drawn
        title = "You Win!" if self.won else f"{winner} Wins!"
        if self.left:
            title = "Lost Touch" if "Lost touch" in self.left else "Your Friend Left"
        self.app.renderer.draw_overlay(
            self, screen, title = title, header = header, buttons = buttons,
            title_size = 0.1, title_color = theme.PARCHMENT if self.left else theme.color(winner),
            mark = "离" if self.left else "胜" if self.won else "败", jukebox = True,
            tips = {"rematch": "Rematch\nAsk your friend for another match. It starts when they agree.",
                    "watch_replay": ("Replay\nWatch the match so far, and save all or part of it." if self.left else
                                     "Replay\nWatch this match again, and save all or part of it."),
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
            if key == "rematch" and net and not self.asked and not self.host_gone():
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
