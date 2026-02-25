from __future__ import annotations

from dataclasses import dataclass

from config import BASE_W, BASE_H
from game.physics import Physics


@dataclass
class Countdown:
    remaining: float
    shown_value: int


class GameBase:
    """Framework-agnostic game world.

    Pygame (or any other frontend) should:
      - call game.start() once
      - call game.update(dt) every frame
      - call renderer.draw(game)

    The game holds simulation state only (no UI widgets).
    """

    def __init__(self, app, width=BASE_W, height=BASE_H):
        self.app = app
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
        self.running = True
        self.paused = False
        self.start_countdown(3)

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

    # ---------------- Countdown ----------------

    def start_countdown(self, seconds, on_finish = None):
        self.countdown = Countdown(remaining = float(seconds), shown_value = int(seconds))
        self.countdown_on_finish = on_finish
        self.paused = True

    def tick_countdown(self, dt):
        cd = self.countdown
        if cd is None:
            return
        cd.remaining -= dt

        new_shown = int(cd.remaining + 0.9999)  # ceiling-ish
        if new_shown != cd.shown_value:
            cd.shown_value = max(0, new_shown)

        if cd.remaining <= 0:
            self.countdown = None
            self.paused = False
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

        Physics.step(self, dt)
