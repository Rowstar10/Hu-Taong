import random
from dataclasses import dataclass

from config import BASE_W, BASE_H
from game.physics import Physics

@dataclass
class Countdown:
    remaining: float
    shown_value: int

class GameBase:
    MAX_STEP = 1 / 30   # a hitch slows the game for a moment instead of letting the ball jump

    def __init__(self, app, width=BASE_W, height=BASE_H):
        self.app = app
        self.settings = self.app.settings.gameplay
        self.width = width
        self.height = height

        self.objects = []
        self.running = False
        self.paused = False

        self.countdown = None
        self.countdown_on_finish = None

    def start(self):
        self.objects.clear()
        self.build_world()

        self.app.loop()
        self.app.clock_tick()
        
        self.running = True
        self.paused = False

        self.start_countdown(self.app.settings.interface.serve_seconds)

    def stop(self):
        self.running = False
        self.paused = False
        self.countdown = None

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def reset_game(self):
        self.stop()
        self.start()

    def build_world(self):
        raise NotImplementedError

    def apply_gameplay_settings(self):
        pass

    # ---------------- Countdown ----------------

    def start_countdown(self, seconds, on_finish = None):
        self.countdown = Countdown(remaining = float(seconds), shown_value = int(seconds))
        self.countdown_on_finish = on_finish
        self.paused = True
        self.app.sound_manager.play("countdown_tick.wav") 

    def tick_countdown(self, dt):
        cd = self.countdown
        if cd is None:
            return
        cd.remaining -= min(dt, self.MAX_STEP)     # a slow frame mustn't swallow the countdown

        new_shown = int(cd.remaining + 0.999)
        if new_shown != cd.shown_value:
            cd.shown_value = max(0, new_shown)
            self.app.sound_manager.play("countdown_tick.wav")

        if cd.remaining <= 0:
            self.countdown = None
            self.paused = False
            self.app.sound_manager.play("countdown_go.wav")
            if self.countdown_on_finish:
                self.countdown_on_finish()
                self.countdown_on_finish = None

    # ---------------- Main update ----------------

    def update(self, dt):
        if not self.running:
            return

        if self.countdown is not None:
            self.tick_countdown(dt)
            return

        if self.paused:
            return

        self.apply_gameplay_settings()
        Physics.step(self, min(dt, self.MAX_STEP) * self.settings.pace)
