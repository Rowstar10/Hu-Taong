import math, pygame, random

from config import BASE_W, BASE_H
from render import theme
from game.game_base import GameBase
from game.physics import Physics
from game.powerups import PowerUps
from objects.wall import Wall
from objects.ball import Ball
from objects.paddle import Paddle

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

        # vs AI: the AI takes whichever paddle the player didn't pick
        self.p1.ai_enabled = settings.vs_ai and settings.play_as_blue
        self.p2.ai_enabled = settings.vs_ai and not settings.play_as_blue

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

    @property
    def wall_up(self):
        """The Middle Wall is standing: on in Settings, and not taken down by Open Court."""
        powerups = getattr(self, "powerups", None)
        return self.settings.middle_wall and not (powerups and powerups.wall_open())

    def on_score(self, obj, data):
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

        if nx == 1:
            self.p2.score += 1
            self.message_text = f"{self.p2.color1} scored!"
            self.message_color = (60, 140, 255)

            if not win_score == "Endless Mode" and self.p2.score >= win_score:
                if not settings.win_by_two or self.p2.score >= self.p1.score + 2:
                    self.app.state_manager.push_state(
                        "win", p1 = self.p1, p2 = self.p2,
                        winner=self.p2, loser=self.p1)
                    return

        elif nx == -1:
            self.p1.score += 1
            self.message_text = f"{self.p1.color1} scored!"
            self.message_color = (255, 80, 80)

            if not win_score == "Endless Mode" and self.p1.score >= win_score:
                if not settings.win_by_two or self.p1.score >= self.p2.score + 2:
                    self.app.state_manager.push_state(
                        "win", p1 = self.p1, p2 = self.p2,
                        winner=self.p1, loser=self.p2)
                    return

        else:
            return

        if sound_manager.score_sound:
            self.app.sound_manager.play("euugh.wav")

        self.powerups.on_point()

        self.say_something(self.p2 if nx == 1 else self.p1)
        if self.switch_warning is not None or self.next_switch <= 0:
            self.next_switch = self.switch_gap()   # a point cancels a coming swap; start a fresh wait
        self.switch_warning = None
        self.switch_after_point = settings.switch_each_point

        obj.spawn_vx = nx * obj.speed
        obj.spawn_vy = random.choice([1, -1]) * obj.speed

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

        for obj in self.objects:
            obj.reset()

        if self.switch_after_point:
            self.switch_after_point = False
            self.switch_sides()

        self.message_text = ""
        self.message_timer = 0.0

        self.start_countdown(self.app.settings.interface.serve_seconds)

    def update(self, dt):
        super().update(dt)
        if self.running and not self.paused and self.countdown is None:
            # Chaos timers keep time with the game pace; messages and the serve countdown don't
            play_dt = min(dt, self.MAX_STEP) * self.settings.pace
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
        for name in ("up", "down", "left", "right", "ai_enabled", "controls_label", "score"):
            first, second = getattr(a, name), getattr(b, name)
            setattr(a, name, second)
            setattr(b, name, first)
        a.ai.reset()
        b.ai.reset()
        self.powerups.swap_owners()

        self.switches += 1
        self.switch_flash = 1.3
        self.switch_banner = "换 Switch!"
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

        self.switches += 1
        self.switch_flash = 1.3
        self.switch_banner = "换 Swap!"
        self.app.sound_manager.play("hmyoop!.wav")

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
            if self.app.settings.gameplay.switch_mid_rally:
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

    def update_drift(self, dt):
        if self.app.settings.gameplay.chaos_mode != 2:
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
        drifting = s.chaos_mode == 2

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
