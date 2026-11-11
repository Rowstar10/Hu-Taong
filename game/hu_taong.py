import math, pygame, random, struct
from array import array
from collections import deque

from config import BASE_W, BASE_H
from render import theme
from game.game_base import GameBase
from game.physics import Physics
from game import courts
from game.powerups import PowerUps
from game.replay import Recorder
from objects.wall import Wall
from objects.ball import Ball
from objects.paddle import Paddle
from core.platform import ANDROID

# Things the AI says after a point, when AI Banter is on
BANTER_SCORED = ["Hehe~ too slow!", "Boo! Gotcha~", "Another one for the parlor!", "Don't blink~",
                 "Hehehe!", "Was that your best?"]
BANTER_CONCEDED = ["Hmph. Lucky shot.", "Ooh, not bad~", "Again! Again!", "You'll pay for that~",
                   "Okay, now I'm awake.", "Hey, no fair!"]


class Hu_Taong(GameBase):
    SWITCH_WARNING = 2.0        # seconds of warning before a Chaos Switch + swap

    def __init__(self, app, width=BASE_W, height=BASE_H):
        super().__init__(app, width, height)
        self.message_text = ""
        self.message_color = (255, 255, 255)
        self.message_timer = 0.0

    def stop(self):
        super().stop()
        self.message_timer = 0
        self.message_color = (255, 255, 255)
        self.message_text = ""

    def build_world(self):
        # Walls & Separator
        self.top_wall = Wall(self, -10, -10, BASE_W + 10, 0)
        self.bottom_wall = Wall(self, -10, BASE_H, BASE_W + 10, BASE_H + 10)
        self.left_wall = Wall(self, -10, -10, 5, BASE_H + 10, color = theme.RED, is_goal = True)
        self.right_wall = Wall(self, BASE_W - 5, -10, BASE_W + 10, BASE_H + 10, color = theme.BLUE, is_goal = True)
        self.separator = Wall(self, BASE_W / 2, -10, BASE_W / 2, BASE_H + 10, is_separator = True)

        settings = self.app.settings.gameplay
        keys = self.app.settings.interface

        # Red (left) and Blue (right) use the keys set in Settings > Interface
        p1_keys = keys.keys("p1")
        p2_keys = keys.keys("p2")

        # Players & Ball
        self.p1 = Paddle(self,
                         width = settings.paddle_width,
                         height = settings.paddle_height,
                         x = settings.paddle_width,
                         y = (BASE_H - settings.paddle_height) / 2,
                         speed = settings.paddle_speed,
                         **p1_keys,
                         color1 = "Red",
                         color2 = "Orange Red",
                         sound = "Hu.wav")

        self.p2 = Paddle(self,
                         width = settings.paddle_width,
                         height = settings.paddle_height,
                         x = BASE_W - 2 * settings.paddle_width,
                         y = (BASE_H - settings.paddle_height) / 2,
                         speed = settings.paddle_speed,
                         **p2_keys,
                         color1 = "Blue",
                         color2 = "Royal Blue",
                         sound = "Tao.wav")

        self.p1.controls_label, self.p2.controls_label = keys.keys_label("p1"), keys.keys_label("p2")
        if ANDROID:            # a phone is played with fingers: the whole screen, or a half each
            two = not settings.vs_ai
            self.p1.controls_label = "Left half" if two else "You"
            self.p2.controls_label = "Right half" if two else "You"

        # vs AI: the AI takes whichever paddle the player didn't pick
        self.p1.ai_enabled = settings.vs_ai and settings.play_as_blue
        self.p2.ai_enabled = settings.vs_ai and not settings.play_as_blue

        # Online, hosting: you are Red and your friend, over the internet, is Blue
        net = self.app.net if getattr(self.app, "net", None) and self.app.net.role == "host" else None
        self.net = net
        self.p1.remote = self.p2.remote = False
        if net:
            self.p1.ai_enabled = self.p2.ai_enabled = False
            friend, you = (self.p1, self.p2) if settings.online_host_blue else (self.p2, self.p1)
            friend.remote = True
            you.controls_label, friend.controls_label = "You", "Friend"
            net.game = self
            net.over = None

        self.ball = Ball(self, diameter = settings.ball_diameter, x = (BASE_W - settings.ball_diameter) / 2, y = (BASE_H - settings.ball_diameter) / 2, speed = settings.ball_speed, color = "white")

        # Chaos Mode +: each paddle and the ball drift through sizes and speeds on their own
        for obj in (self.p1, self.p2, self.ball):
            obj.drift = {"size": self.drift_track(obj, "size"), "speed": self.drift_track(obj, "speed")}

        # Chaos Switch
        self.switch_after_point = False
        self.next_switch = self.switch_gap()
        self.switch_warning = None      # seconds until a telegraphed swap, while one is coming
        self.switch_flash = 0.0         # time left on the "Switch!" banner
        self.switch_banner = "换 Switch!"
        self.switches = 0

        self.banter = None              # [text, paddle, time left]

        self.powerups = PowerUps(self)

        # The court's own stones, for the whole match (power-up Tombstones come and go)
        self.court = courts.pick(settings.court)
        self.stones = courts.build(self, self.court)

        self.recorder = Recorder(self)           # every match is recorded, for replays and highlights

        # Online: where the ball and the friend's paddle were, to check the friend's saves against
        self.history = deque(maxlen = 240)
        self.pending_goal = None                 # a goal into the friend's end, held for word of a save
        self.last_guest_hit = -1.0
        self.claim_lag = None                    # how late the friend's saves get here, smoothed
        self.shown = None                        # where the ball was last drawn: (host time, x, y)
        self.warp = 0.0                          # eases from 0 to 1 after each serve

    # ---------------- Hooks: things worth noticing (the replay recorder listens in) ----------------

    def on_hit(self, ball, paddle, data):
        self.recorder.on_hit(ball, paddle, data)

    def on_bounce(self, ball, other):
        self.recorder.on_bounce(ball, other)

    def on_powerup(self, kind, owner):
        self.recorder.on_powerup(kind, owner)

    def on_teleport(self, paddle):
        self.recorder.on_teleport(paddle)
        if getattr(paddle, "remote", False) and self.net:
            # the friend's teleport save: their screen can't claim it in time, so it's played here
            side = -1 if paddle.is_left else 1
            Physics.resolve_collision(paddle, self.ball, {"t": 0.0, "normal": (side, 0)})

    def on_stick(self, paddle):
        self.recorder.on_stick(paddle)

    def on_blink(self, x0, y0, x1, y1):
        self.recorder.on_blink(x0, y0, x1, y1)

    @property
    def wall_up(self):
        """The Middle Wall is standing: on in Settings, and not taken down by Open Court."""
        powerups = getattr(self, "powerups", None)
        return self.settings.middle_wall and not (powerups and powerups.wall_open())

    # ---------------- Online: the friend's saves ----------------

    def guest_paddle(self):
        return next((p for p in (self.p1, self.p2) if getattr(p, "remote", False)), None)

    def note_history(self):
        """Once a frame: where the ball and the friend's paddle are, by the replay clock."""
        b, g = self.ball, self.guest_paddle()
        self.history.append((self.recorder.clock, (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2, b.vx, b.vy,
                             g.x0 if g else 0.0, g.y0 if g else 0.0))

    def claim_delay(self):
        """How long after a save on the friend's screen word of it gets here."""
        if self.claim_lag is not None:
            lag = self.claim_lag
        else:
            lag = (self.net.ping if self.net and self.net.ping is not None else 0.1) / 2 + 0.02
        return max(0.02, min(0.3, lag + 0.015))

    def net_grace(self):
        """How long a goal into the friend's end waits, in case their screen saw a save."""
        return min(0.45, self.claim_delay() + 0.1)

    def shown_ball(self, dt):
        """Hosting: where to draw the ball, as (x0, y0), or None to draw it where it is.

        Word of a save on your friend's screen takes a moment to get here.  So as the ball nears
        their paddle it is drawn that moment in the past (from the ball's recent path), easing back
        to the present as it comes back to you.  It reaches their paddle on this screen just as
        word of their save arrives, and bounces off, instead of sailing through and jumping back."""
        ball, g = self.ball, self.guest_paddle()
        if g is None or not self.history:
            return None
        if self.paused and self.countdown is None and not self.message_text and self.shown:
            return self.shown[1] - ball.width / 2, self.shown[2] - ball.width / 2     # held still under the pause screen
        if self.paused or self.countdown is not None or self.message_text or getattr(ball, "stuck", None):
            self.warp, self.shown = 0.0, None
            return None
        self.warp = min(1.0, self.warp + dt / 0.4)
        host = self.p1 if g is self.p2 else self.p2
        their_face = g.x0 if g is self.p2 else g.x1
        my_face = host.x1 if host is self.p1 else host.x0
        way = 1 if g is self.p2 else -1
        span = their_face - my_face
        if span * way < 300:
            span = 300 * way
        x_then = self.shown[1] if self.shown else (ball.x0 + ball.x1) / 2
        reach = max(0.0, min(1.0, (x_then - my_face) / span))
        now = self.recorder.clock
        tau = now - self.claim_delay() * reach * self.warp
        if self.shown:
            tau = max(tau, self.shown[0])               # the ball never runs backwards
        tau = min(tau, now)
        h = self.history
        if tau >= h[-1][0]:
            x, y = h[-1][1], h[-1][2]
        else:
            i = len(h) - 1
            while i > 0 and h[i - 1][0] > tau:
                i -= 1
            a, b = h[max(0, i - 1)], h[i]
            span_t = b[0] - a[0]
            k = 0.0 if span_t <= 0 else max(0.0, min(1.0, (tau - a[0]) / span_t))
            if abs(b[1] - a[1]) > 150 or abs(b[2] - a[2]) > 150:
                k = 0.0 if k < 0.5 else 1.0
            x, y = a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k
        self.shown = (tau, x, y)
        r = ball.width / 2
        return x - r, y - r

    def rewrite_flight(self, t, cx, cy, vx, vy):
        """A save played late, from host time t: put the ball's path since then onto its new course,
        in the recent path the ball is drawn from and in the replay, so neither shows it sailing
        through the paddle first."""
        from helpers import reflect_in_range
        ball, g = self.ball, self.guest_paddle()
        r = ball.width / 2
        pace = self.settings.pace

        def at(clock):
            dt = (clock - t) * pace
            x = max(r, min(BASE_W - r, cx + vx * dt))
            y, n = reflect_in_range(cy + vy * dt, r, BASE_H - r)
            return x, y, vx, (-vy if n % 2 else vy)

        for i, h in enumerate(self.history):
            if h[0] > t:
                self.history[i] = (h[0], *at(h[0]), h[5], h[6])
        frames = self.recorder.frames
        flag = 8 if g is self.p1 else 16
        for i in range(len(frames) - 1, max(-1, len(frames) - 120), -1):
            clock = struct.unpack_from("<f", frames[i], 0)[0]
            if clock <= t:
                break
            row = array("f")
            row.frombytes(frames[i])
            x, y, rvx, rvy = at(clock)
            row[9], row[10], row[12], row[13] = x - r, y - r, rvx, rvy
            row[15] = (int(row[15]) & ~24) | flag
            frames[i] = row.tobytes()

    def into_guest_goal(self, data):
        g = self.guest_paddle()
        nx = data["normal"][0]
        return g is not None and ((nx == 1 and g is self.p1) or (nx == -1 and g is self.p2))

    def apply_claim(self, claim):
        """The friend's screen showed the ball meeting their paddle.  If that fits what happened here
        (the ball really was there then, and the paddle could have been), play the hit from that
        moment and carry the ball on to now.  Answers the host time it was played at, or -1."""
        g, ball = self.guest_paddle(), self.ball
        try:
            t = float(claim["t"])
            bx, by, px, py = (float(claim[k]) for k in ("bx", "by", "px", "py"))
            pvx, pvy = float(claim.get("pvx", 0)), float(claim.get("pvy", 0))
            nx, ny = (int(v) for v in claim["normal"])
        except (KeyError, TypeError, ValueError):
            return -1
        if g is None or getattr(ball, "stuck", None) or (nx, ny) not in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            return -1
        if not self.history:
            return -1
        # how late word of saves gets here, for drawing the ball on the friend's side
        lag = max(0.0, min(0.5, self.recorder.clock - t))
        self.claim_lag = lag if self.claim_lag is None else self.claim_lag + (lag - self.claim_lag) * 0.25
        latest = self.history[-1][0]
        if t > latest:
            if t - latest > 0.12:
                self.claim_note = ("future", round(t - latest, 3))
                return -1
            t = latest                                   # their clock ran a touch ahead of this one
        if t <= self.last_guest_hit + 0.15:
            self.claim_note = ("again", round(t - self.last_guest_hit, 3))
            return -1
        if self.message_text or self.countdown is not None or t <= getattr(self, "last_goal_clock", -1.0):
            self.claim_note = ("point over",)
            return -1                                    # that point is already over
        then = min(self.history, key = lambda h: abs(h[0] - t))
        if abs(then[0] - t) > 0.08:
            self.claim_note = ("no history", round(then[0] - t, 3))
            return -1
        _, hx, hy, hvx, hvy, gx, gy = then
        speed = math.hypot(hvx, hvy)
        if math.hypot(bx - hx, by - hy) > max(80, speed * 0.1):
            self.claim_note = ("ball", round(bx - hx), round(by - hy), round(speed))
            return -1                                    # the ball wasn't there
        reach = g.speed * 0.45 + 90
        if abs(px - gx) > reach or abs(py - gy) > reach:
            self.claim_note = ("paddle", round(px - gx), round(py - gy))
            return -1                                    # nor could the paddle have been
        keep = (g.x0, g.y0, g.vx, g.vy)
        g.x0, g.y0, g.x1, g.y1 = px, py, px + g.width, py + g.height
        g.vx, g.vy = pvx, pvy
        r = ball.width / 2
        if nx:                                           # the ball against the face it met
            cx = (g.x0 - r - 0.5) if nx > 0 else (g.x1 + r + 0.5)
            cy = hy
        else:
            cx = hx
            cy = (g.y0 - r - 0.5) if ny > 0 else (g.y1 + r + 0.5)
        ball.x0, ball.y0, ball.x1, ball.y1 = cx - r, cy - r, cx + r, cy + r
        ball.vx, ball.vy = hvx, hvy
        before = ball.last_paddle, ball.rally_value
        self.powerups.ball_v = (hvx, hvy)                # how it came at their paddle (for a Snowball's shove)
        shoved = getattr(g, "shoved", 0.0)
        Physics.resolve_collision(g, ball, {"t": 0.0, "normal": (nx, ny)})
        push = g.vx if getattr(g, "shoved", 0.0) > shoved else None
        # it hit if the ball now leaves the face it met (the same paddle may hit twice running,
        # say after the ball came back off a stone)
        hit = ball.last_paddle is g and (ball.vx * nx + ball.vy * ny) < 0
        try:
            cvx, cvy = float(claim["vx"]), float(claim["vy"])
        except (KeyError, TypeError, ValueError):
            cvx = cvy = None
        if hit and cvx is not None and not getattr(ball, "stuck", None):
            # The friend's screen has already sent the ball off on its way: if that's close to how
            # this game plays the hit, keep theirs, so the two screens agree exactly
            mine, theirs = math.hypot(ball.vx, ball.vy), math.hypot(cvx, cvy)
            turn = abs(math.atan2(ball.vx * cvy - ball.vy * cvx, ball.vx * cvx + ball.vy * cvy))
            if mine > 0 and 0.75 < theirs / mine < 1.33 and turn < math.radians(12):
                ball.vx, ball.vy = cvx, cvy
        g.x0, g.y0, g.vx, g.vy = keep[0], keep[1], keep[2], keep[3]
        g.x1, g.y1 = g.x0 + g.width, g.y0 + g.height
        if hit and push is not None:
            g.vx = push                                  # the Snowball knocks their paddle back too
        if not hit:
            self.claim_note = ("no contact", nx, ny, round(hvx), round(pvx), before[0] is g, before[1], ball.rally_value,
                               ball.last_paddle is g, round(ball.vx))
            return -1
        self.pending_goal = None                         # it was saved after all
        if self.paused and self.countdown is None and not self.message_text:
            self.resume()
        if not getattr(ball, "stuck", None):
            from helpers import reflect_in_range
            sx, sy, svx, svy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, ball.vx, ball.vy
            dt = max(0.0, self.recorder.clock - t) * self.settings.pace
            x = sx + svx * dt
            y, bounces = reflect_in_range(sy + svy * dt, r, BASE_H - r)
            if bounces % 2:
                ball.vy = -ball.vy
            x = max(r + 1, min(BASE_W - r - 1, x))
            ball.x0, ball.y0, ball.x1, ball.y1 = x - r, y - r, x + r, y + r
            self.rewrite_flight(t, sx, sy, svx, svy)
        self.last_guest_hit = t
        return round(self.recorder.clock, 3)

    def net_tick(self):
        """Hosting: check the friend's saves, and let a held goal go once no save has come."""
        net = self.net
        for claim in net.take_claims():
            net.acks[claim["id"]] = self.apply_claim(claim)
        goal = self.pending_goal
        if goal is not None and self.recorder.clock >= goal["until"]:
            self.pending_goal = None
            self.on_score(goal["obj"], goal["data"], held = True)

    def on_score(self, obj, data, held = False):
        if self.net and not held:
            if self.pending_goal is not None:
                return                                   # already waiting on this one
            if self.into_guest_goal(data):
                # In on this screen, but the friend may have just saved it on theirs: hold it a
                # moment for word of the save
                self.pending_goal = {"until": self.recorder.clock + self.net_grace(), "obj": obj, "data": data}
                obj.vx = obj.vy = 0.0
                return
        self.last_goal_clock = self.recorder.clock
        self.pause()
        nx, _ny = data["normal"]
        settings = self.app.settings.gameplay
        sound_manager = self.app.sound_manager
        win_score = settings.winning_scores[settings.winning_score_index]

        if nx != 0:
            cy = (obj.y0 + obj.y1) / 2
            arc = (-1.1, 1.1) if nx == 1 else (2.04, 4.24)
            self.app.fx.burst(0 if nx == 1 else BASE_W, cy, 18, 64, "blue" if nx == 1 else "red",
                              speed = (260, 620), arc = arc)
            self.app.fx.spark(0 if nx == 1 else BASE_W, cy, 40, theme.SPIRIT_BLUE if nx == 1 else theme.EMBER,
                              speed = 720, life = .9, arc = arc)

        points = self.powerups.point_value()           # Double or Nothing makes it 2
        if nx == 1:
            self.p2.score += points
            self.message_text = f"{self.p2.color1} scored!" + (" x2" if points == 2 else "")
            self.message_color = (60, 140, 255)

            if not win_score == "Endless Mode" and self.p2.score >= win_score:
                if not settings.win_by_two or self.p2.score >= self.p1.score + 2:
                    self.recorder.on_point(self.p2, True)
                    self.app.state_manager.push_state(
                        "win", p1 = self.p1, p2 = self.p2,
                        winner=self.p2, loser=self.p1)
                    return

        elif nx == -1:
            self.p1.score += points
            self.message_text = f"{self.p1.color1} scored!" + (" x2" if points == 2 else "")
            self.message_color = (255, 80, 80)

            if not win_score == "Endless Mode" and self.p1.score >= win_score:
                if not settings.win_by_two or self.p1.score >= self.p2.score + 2:
                    self.recorder.on_point(self.p1, True)
                    self.app.state_manager.push_state(
                        "win", p1 = self.p1, p2 = self.p2,
                        winner=self.p1, loser=self.p2)
                    return

        else:
            return

        scorer = self.p2 if nx == 1 else self.p1
        self.recorder.on_point(scorer, False)

        if sound_manager.score_sound:
            self.app.sound_manager.play("euugh.wav")

        self.powerups.on_point()

        self.say_something(self.p2 if nx == 1 else self.p1)
        if self.switch_warning is not None or self.next_switch <= 0:
            self.next_switch = self.switch_gap()   # a point cancels a coming swap; start a fresh wait
        self.switch_warning = None
        self.switch_after_point = settings.switch_each_point

        ball = self.ball                     # (a Twin Balls goal may have come from the blue ball)
        ball.spawn_vx = nx * ball.speed
        ball.spawn_vy = random.choice([1, -1]) * ball.speed

        self.message_timer = 2

    def reset_round(self):
        settings = self.app.settings.gameplay
        if settings.chaos_mode == 1:
            settings.chaos_roll()
            self.apply_gameplay_settings()
            for obj in self.objects:
                if obj.is_ball:   # launch at the new speed, in the same directions
                    obj.spawn_vx = obj.speed * (1 if obj.spawn_vx >= 0 else -1)
                    obj.spawn_vy = obj.speed * (1 if obj.spawn_vy >= 0 else -1)
        else:
            self.apply_gameplay_settings()      # a Snowball shrinks back to a ball before the serve

        for obj in self.objects:
            obj.reset()

        if self.switch_after_point:
            self.switch_after_point = False
            self.switch_sides()

        self.message_text = ""
        self.message_timer = 0.0

        self.start_countdown(self.app.settings.interface.serve_seconds)

    def keep_ball_in(self):
        """Safety net: whatever shoves it, the ball never leaves the court.  Out past an end it is
        a goal; out past the top or bottom it is put back and sent the other way."""
        if self.paused or self.countdown is not None:
            return
        for b in self.powerups.balls():
            r = b.diameter / 2
            cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
            for out, nx in ((cx < 0, 1), (cx > BASE_W, -1)):
                if not out:
                    continue
                if b.scores_in(nx):
                    self.on_score(b, {"normal": (nx, 0)})
                    return
                # Twin Balls: past its own colour's goal it is put back and turned round
                cx = r + 6 if nx == 1 else BASE_W - r - 6
                b.x0, b.x1 = cx - r, cx + r
                b.vx = nx * max(abs(b.vx), b.speed)
            if cy < r or cy > BASE_H - r:
                cy = min(max(cy, r), BASE_H - r)
                b.y0, b.y1 = cy - r, cy + r
                b.vy = abs(b.vy) if cy <= r else -abs(b.vy)

            # A ball going (nearly) straight up and down would bounce there for ever: tip it towards
            # the end of whoever didn't touch it last, keeping its speed
            speed = math.hypot(b.vx, b.vy)
            if speed and abs(b.vx) < speed * 0.2:
                last = getattr(b, "last_paddle", None)
                way = math.copysign(1, b.vx) if b.vx else (1 if last is None or last.is_left else -1)
                b.vx = way * speed * 0.3
                b.vy = math.copysign(speed * math.sqrt(1 - 0.09), b.vy or 1)

    def update(self, dt):
        super().update(dt)
        if self.running:
            self.keep_ball_in()
        if self.running and not self.paused and self.countdown is None:
            # Chaos timers keep time with the game pace; messages and the serve countdown don't
            play_dt = min(dt, self.MAX_STEP) * self.settings.pace
            for obj in self.objects:
                if getattr(obj, "is_obstacle", False):
                    obj.update(play_dt)
            self.update_drift(play_dt)
            self.update_switch(play_dt)
            self.powerups.update(play_dt)
        if self.running:
            self.powerups.update_popups(dt)

        if self.switch_flash > 0:
            self.switch_flash -= dt
        if self.banter:
            self.banter[2] -= dt
            if self.banter[2] <= 0:
                self.banter = None

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.reset_round()

    # ---------------- AI banter ----------------

    def say_something(self, scorer):
        ai = [p for p in (self.p1, self.p2) if p.ai_enabled]
        if len(ai) != 1 or not self.app.settings.interface.ai_banter:
            return
        lines = BANTER_SCORED if scorer is ai[0] else BANTER_CONCEDED
        self.banter = [random.choice(lines), ai[0], 2.2]

    # ---------------- Chaos Switch ----------------

    @staticmethod
    def switch_gap():
        return random.uniform(6, 14)

    def switch_sides(self):
        """Each player takes over the other paddle.  Their keys, and their score, go with them."""
        a, b = self.p1, self.p2
        for name in ("up", "down", "left", "right", "ai_enabled", "controls_label", "score", "remote"):
            first, second = getattr(a, name), getattr(b, name)
            setattr(a, name, second)
            setattr(b, name, first)
        a.ai.reset()
        b.ai.reset()
        self.powerups.swap_owners()

        self.switches += 1
        self.switch_flash = 1.3
        self.switch_banner = "换 Switch!"
        self.recorder.on_swap(0)
        self.app.sound_manager.play("hmyoop!.wav")
        for paddle, tint in ((a, "blue"), (b, "red")):
            cx, cy = (paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2
            self.app.fx.burst(cx, cy, 10, 48, tint, speed = (160, 380), life = (.6, 1.1))

    def swap_positions(self):
        """Chaos Switch +: the two paddles trade places on the court.  Keys, scores and goals stay
        with their players, so each one has to scramble back to defend their own end."""
        a, b = self.p1, self.p2
        centres = [((p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2) for p in (a, b)]
        for paddle, (cx, cy) in ((a, centres[1]), (b, centres[0])):
            paddle.x0, paddle.x1 = cx - paddle.width / 2, cx + paddle.width / 2
            paddle.y0, paddle.y1 = cy - paddle.height / 2, cy + paddle.height / 2
            paddle.vx = paddle.vy = 0.0
            Physics.clamp_to_world(paddle)
            paddle.ai.reset()
            self.app.fx.burst(cx, cy, 10, 48, "red" if paddle.is_left else "blue", life = (.6, .9))

            # Landed on the ball: push it clear out of the paddle's front, never through a wall
            b = self.ball
            if b.x0 < paddle.x1 and b.x1 > paddle.x0 and b.y0 < paddle.y1 and b.y1 > paddle.y0:
                forward = 1 if paddle.is_left else -1
                x0 = paddle.x1 + 2 if forward > 0 else paddle.x0 - 2 - b.width
                if not 0 <= x0 <= BASE_W - b.width:
                    x0 = paddle.x0 - 2 - b.width if forward > 0 else paddle.x1 + 2
                    forward = -forward
                b.x0, b.x1 = x0, x0 + b.width
                b.vx = forward * max(abs(b.vx), b.speed * 0.5)

        # Every ball on the court slows to half its speed, giving both players a moment to get
        # back and defend (a stuck ball leaves at half speed too)
        for ball in self.powerups.balls():
            ball.vx *= 0.5
            ball.vy *= 0.5
            if getattr(ball, "stuck", None):
                ball.stuck["vx"] *= 0.5
                ball.stuck["vy"] *= 0.5
            self.app.fx.spark((ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, 14, (200, 230, 255), speed = 240, life = .5)

        self.switches += 1
        self.switch_flash = 1.3
        self.switch_banner = "换 Swap!"
        self.recorder.on_swap(1)
        self.app.sound_manager.play("hmyoop!.wav")

    def start_switch_mode(self):
        """Soul Swap: Chaos Switch + until the point ends.  The wall has come down; the first swap
        comes soon, so it happens within the point."""
        if self.switch_warning is None:
            self.next_switch = min(self.next_switch, random.uniform(1.5, 3.0))

    def start_swap_warning(self):
        """The telegraphed countdown before the paddles swap places (Chaos Switch + or Soul Swap)."""
        if self.switch_warning is None and not self.wall_up:
            self.switch_warning = self.SWITCH_WARNING
            self.app.sound_manager.play("countdown_tick.wav")

    def update_switch(self, dt):
        if self.wall_up:
            self.switch_warning = None           # swapping places needs the wall down
            return

        if self.switch_warning is None:
            if self.powerups.swapping():
                self.next_switch -= dt
                if self.next_switch <= 0:
                    self.start_swap_warning()
            return

        before = self.switch_warning
        self.switch_warning -= dt
        third = self.SWITCH_WARNING / 3
        if int(before / third) != int(max(0, self.switch_warning) / third) and self.switch_warning > 0:
            self.app.sound_manager.play("countdown_tick.wav")
        if self.switch_warning <= 0:
            self.switch_warning = None
            self.next_switch = self.switch_gap()
            if not self.app.settings.gameplay.switch_mid_rally:
                self.next_switch = random.uniform(4, 8)     # Soul Swap's: sooner, as it only lasts the point
            self.swap_positions()

    # ---------------- Chaos Mode + ----------------

    def drift_track(self, obj, key):
        """[value, target, seconds until a new target], as a share of the setting's range."""
        s = self.app.settings.gameplay
        if obj.is_ball:
            name = "ball_diameter" if key == "size" else "ball_speed"
        else:
            name = "paddle_height" if key == "size" else "paddle_speed"
        value = (getattr(s, name) - getattr(s, name + "_min")) / getattr(s, name + "_range")
        return [value, value, 0.0]

    def reset_drift(self):
        """Back to the settings' own sizes and speeds (after a Chaos Mode + power-up's point)."""
        for obj in (self.p1, self.p2, self.ball):
            obj.drift = {"size": self.drift_track(obj, "size"), "speed": self.drift_track(obj, "speed")}

    def update_drift(self, dt):
        powerups = getattr(self, "powerups", None)
        if not (powerups.drifting() if powerups else self.app.settings.gameplay.chaos_mode == 2):
            return
        ease = 1 - math.exp(-dt / 1.1)
        for obj in (self.p1, self.p2, self.ball):
            for track in obj.drift.values():
                track[2] -= dt
                if track[2] <= 0:
                    track[1], track[2] = random.random(), random.uniform(1.5, 4.0)
                track[0] += (track[1] - track[0]) * ease

    # ---------------- Settings ----------------

    @staticmethod
    def resize(obj, width, height):
        """Change size about the object's centre."""
        cx, cy = (obj.x0 + obj.x1) / 2, (obj.y0 + obj.y1) / 2
        obj.width, obj.height = width, height
        obj.x0, obj.x1 = cx - width / 2, cx + width / 2
        obj.y0, obj.y1 = cy - height / 2, cy + height / 2

    def apply_gameplay_settings(self):
        super().apply_gameplay_settings()
        s = self.app.settings.gameplay
        powerups = getattr(self, "powerups", None)
        drifting = powerups.drifting() if powerups else s.chaos_mode == 2

        for obj in self.objects:
            if obj.is_paddle:
                if drifting:
                    t, pace = obj.drift["size"][0], obj.drift["speed"][0]
                    width = s.paddle_width_min + t * s.paddle_width_range
                    height = s.paddle_height_min + t * s.paddle_height_range
                    obj.speed = s.paddle_speed_min + pace * s.paddle_speed_range
                else:
                    width, height, obj.speed = s.paddle_width, s.paddle_height, s.paddle_speed

                # Giant Paddle, Shrink Curse, Swift Step and frost act on top of the settings
                powerups = getattr(self, "powerups", None)
                if powerups:
                    height = min(BASE_H * 0.62, height * powerups.size_factor(obj))
                    obj.speed *= powerups.speed_factor(obj)

                if (width, height) != (obj.width, obj.height):
                    self.resize(obj, width, height)
                    Physics.clamp_to_world(obj)

                if obj.is_left:
                    obj.spawn_x = obj.width
                    obj.spawn_y = (BASE_H - obj.height) / 2
                    obj.home_x = obj.spawn_x + obj.width / 2
                    obj.home_y = obj.spawn_y + obj.height / 2

                else:
                    obj.spawn_x = BASE_W - 2 * obj.width
                    obj.spawn_y = (BASE_H - obj.height) / 2
                    obj.home_x = obj.spawn_x + obj.width / 2
                    obj.home_y = obj.spawn_y + obj.height / 2


            if obj.is_ball:
                if drifting:
                    diameter = s.ball_diameter_min + obj.drift["size"][0] * s.ball_diameter_range
                    speed = s.ball_speed_min + obj.drift["speed"][0] * s.ball_speed_range
                    if obj.speed > 0:     # speed the ball up or down as the drift moves, keeping its direction
                        k = speed / obj.speed
                        obj.vx *= k
                        obj.vy *= k
                    obj.speed = speed
                else:
                    diameter, obj.speed = s.ball_diameter, s.ball_speed

                # A Snowball grows as it rolls (to 200 px at most)
                powerups = getattr(self, "powerups", None)
                if powerups and powerups.snowball() and obj is self.ball:
                    diameter = max(diameter, min(200.0, diameter * powerups.ball_size_factor()))

                if diameter != obj.diameter:
                    self.resize(obj, diameter, diameter)
                    obj.diameter = diameter
                    if obj.y0 < 0:
                        obj.y0, obj.y1 = 0, diameter
                    elif obj.y1 > BASE_H:
                        obj.y0, obj.y1 = BASE_H - diameter, BASE_H

                obj.spawn_x = (BASE_W - obj.width) /2
                obj.spawn_y = (BASE_H - obj.height) / 2
                obj.home_x = obj.spawn_x + obj.width / 2
                obj.home_y = obj.spawn_y + obj.height / 2
