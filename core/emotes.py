"""Quick emotes, online (1.9, Rowan's 1.9 plan, phase 3, step 13a).

"Nice shot!", "Oops", "Good game", Hu Tao laughing and Hu Tao thinking: keys 1-5, or the controller
buttons set in Controls > Emote Buttons.  Each shows in a bubble by the sender's side of the court, on both
screens, with a few seconds' wait before you can send another.  Settings > UI can mute your friend's.
(The two Hu Tao ones are her ghost, as the game draws the ball: laughing, and thinking.)

Each side sends its latest emote with a running count in every message (the host's snapshots, the
friend's inputs) until the next, so a lost packet doesn't lose it; the count shows a new one.  A
game that doesn't know the field just ignores it, so this needs no new protocol number.
"""
import time

import pygame

# (what it says, the ghost's face for it or None)
EMOTES = (("Nice shot!", None), ("Oops", None), ("Good game", None), ("Hahaha!", "laugh"), ("Hmm...", "think"))
KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4,
        pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3, pygame.K_KP5: 4}
COOLDOWN = 3.0          # seconds between your emotes
SHOW = 2.6              # seconds a bubble stays up


class Emotes:
    def __init__(self, app):
        self.app = app
        self.last_sent = -COOLDOWN
        self.bubbles = []           # [emote, side 1 or 2, age]

    # ---------------- Sending ----------------

    def online(self):
        """The online match being played here, if one is: (session, your side), else None."""
        net, state = self.app.net, self.app.state_manager.current()
        if net is None or not getattr(state, "is_game", False):
            return None
        if getattr(net, "role", "") == "host":
            game = getattr(net, "game", None)
            if game is None:
                return None
            return net, 2 if getattr(game.p1, "remote", False) else 1
        side = getattr(state, "my_side", None)
        return net, side() if side else 2

    def send(self, n):
        """Yours: shown by your side here, and sent.  Not offline, nor straight after another."""
        here = self.online()
        now = time.perf_counter()
        if here is None or not 0 <= n < len(EMOTES) or now - self.last_sent < COOLDOWN:
            return False
        net, side = here
        self.last_sent = now
        count = net.emote[0] + 1 if getattr(net, "emote", None) else 1
        net.emote = [count, n]          # (sent with every message till the next: see core/net.py)
        self.show(n, side)
        return True

    def key(self, event):
        """Keys 1-5 in an online match (unless they steer a paddle)."""
        if event.type != pygame.KEYDOWN or event.key not in KEYS:
            return
        controls = self.app.settings.gameplay
        if event.key in [getattr(controls, f) for f in controls.KEY_FIELDS]:
            return
        self.send(KEYS[event.key])

    # ---------------- Receiving ----------------

    def receive(self, net, value):
        """The friend's latest, as their message carries it: [count, emote]."""
        if not (isinstance(value, list) and len(value) == 2 and all(isinstance(v, int) for v in value)):
            return
        count, n = value
        if count <= getattr(net, "emote_seen", 0) or not 0 <= n < len(EMOTES):
            return
        net.emote_seen = count
        if not self.app.settings.interface.friend_emotes:
            return                      # muted (Settings > UI)
        here = self.online()
        mine = here[1] if here else (2 if getattr(net, "role", "") == "host" else 1)
        self.show(n, 3 - mine)

    # ---------------- Showing ----------------

    def show(self, n, side):
        self.bubbles = [b for b in self.bubbles if b[1] != side] + [[n, side, 0.0]]

    def update(self, dt):
        for b in self.bubbles:
            b[2] += dt
        self.bubbles = [b for b in self.bubbles if b[2] < SHOW]

    def clear(self):
        self.bubbles = []
