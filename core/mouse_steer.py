"""Steering a paddle with the mouse (1.9, Rowan: "Also make controls for moving the paddle with
your mouse").

Turned on in Settings > Controls (Mouse: On; it's off unless you turn it on, so a nudged mouse
never takes your paddle).  The paddle heads for the pointer, up and down and across, at no more
than its own speed, so the mouse is no faster than the keys; it eases in as a finger's Follow does
on a phone (core/touch.py).  The mouse takes over once it moves in a match, and lets go as soon as
a paddle key or a controller is used, till it moves again: whatever you're using now steers.

With one player here (against the AI, or online) the mouse plays that player's paddle; with two,
the side set in Controls.  As a friend who joined online, the pointer is sent as a share of full
speed, as a finger is.
"""
import pygame

from config import BASE_W, BASE_H
from core.touch import STEER_K, STEER_DAMP


def ask(error, velocity, speed):
    return max(-speed, min(speed, STEER_K * (error - STEER_DAMP * velocity)))


class MouseSteer:
    def __init__(self, app):
        self.app = app
        self.active = False             # the mouse moved in a match, and nothing else has steered since
        self.at = None                  # the pointer, in the game's own 1920 x 1080

    def on(self):
        return bool(self.app.settings.gameplay.mouse_steer) and not getattr(self.app, "touch", None)

    def notice(self, event):
        """Every event the keyboard or mouse sends (core/gamepad.py passes them on)."""
        t = event.type
        if t == pygame.MOUSEMOTION:
            self.at = self.app.window_to_base(event.pos)
            if self.on() and event.rel != (0, 0) and self.in_play():
                self.active = True
        elif t == pygame.KEYDOWN and event.key in self.paddle_keys():
            self.active = False         # the keys again

    def let_go(self):
        self.active = False

    def in_play(self):
        top = self.app.state_manager.current()
        return getattr(top, "is_game", False) or getattr(top, "NAME", "") == "guest_match"

    def paddle_keys(self):
        g = self.app.settings.gameplay
        return {getattr(g, field) for field in g.KEY_FIELDS}

    # ---------------- Which paddle ----------------

    def plays(self, paddle):
        """Whether the mouse plays this paddle (on or not, steering or not)."""
        game = paddle.game
        pads = getattr(self.app, "gamepads", None)
        here = pads.players_here(game) if pads is not None else [paddle]
        if paddle not in here:
            return False
        if len(here) == 1:
            return True
        g = self.app.settings.gameplay
        red_keys = paddle.up == g.p1_up                # (a Switch moves the keys, and so the mouse)
        return red_keys == (g.mouse_side == 0)

    def steering(self, paddle):
        return self.on() and self.active and self.at is not None and self.plays(paddle)

    # ---------------- Steering ----------------

    def target(self, w, h):
        x, y = self.at
        return min(BASE_W - w / 2, max(w / 2, x)), min(BASE_H - h / 2, max(h / 2, y))

    def steer_paddle(self, paddle):
        """The velocity the pointer asks of this paddle, or None when the mouse isn't steering it."""
        if not self.steering(paddle):
            return None
        tx, ty = self.target(paddle.width, paddle.height)
        cx, cy = (paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2
        return ask(tx - cx, paddle.vx, paddle.speed), ask(ty - cy, paddle.vy, paddle.speed)

    def guest_axis(self, state, speed):
        """Online, as the friend who joined: the pointer as a share of full speed each way (-1 to
        1), or None when the mouse isn't steering."""
        box, pred = getattr(state, "own_box", None), getattr(state, "pred", None)
        if not (self.on() and self.active and self.at is not None) or box is None or pred is None:
            return None
        x, y, w, h = box
        tx, ty = self.target(w, h)
        speed = max(1.0, speed)
        return (ask(tx - (x + w / 2), pred[2], speed) / speed,
                ask(ty - (y + h / 2), pred[3], speed) / speed)
