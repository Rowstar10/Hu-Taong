"""Controllers (1.9, Rowan's 1.9 plan, phase 3, step 12).

Any controller SDL knows (Xbox, PlayStation, Nintendo and most others) plays the game and works the
menus.  Like the phone's fingers (core/touch.py), it turns what it's given into the game's own:

* In a match, the left stick (or the D-pad) steers a paddle, as finely as the stick is pushed.
  With one player here (against the AI, or online) every controller steers that player's paddle;
  with two, the first controller takes the side set in Gameplay and the second the other, and the
  keyboard still works for either.  The buttons for Pause and the talisman list can be changed in
  Gameplay settings.
* In the menus, the D-pad or stick moves a highlight from control to control, A presses it, B goes
  back, the right stick scrolls and left/right on a slider moves it.  The arrow keys and Enter
  move the same highlight from the keyboard (Navigator).
* Button prompts name the buttons as the controller in use labels them (Cross for a PlayStation
  pad's A, and so on).

It keeps each controller's state from SDL's events, so the tests can drive it with made-up ones.
"""
import math
import os
import time

import pygame

try:
    from pygame._sdl2 import controller as sdl_controller
except Exception:                       # (an older pygame, or a phone without it: no controllers)
    sdl_controller = None

DEADZONE = 0.28                         # of the stick's travel, ignored (sticks never rest at 0)
AXIS_MAX = 32767
REPEAT_FIRST, REPEAT_EVERY = 0.38, 0.11     # seconds: holding a direction in the menus
SCROLL_EVERY = 0.12                     # seconds between scroll steps with the right stick held

# SDL's names for the buttons, as the settings keep them
BUTTONS = {name: getattr(pygame, "CONTROLLER_BUTTON_" + name.upper(), None) for name in
           ("a", "b", "x", "y", "back", "guide", "start", "leftstick", "rightstick",
            "leftshoulder", "rightshoulder", "dpad_up", "dpad_down", "dpad_left", "dpad_right")}
NAME_OF = {code: name for name, code in BUTTONS.items() if code is not None}
DPAD = {"dpad_up": (0, -1), "dpad_down": (0, 1), "dpad_left": (-1, 0), "dpad_right": (1, 0)}
FIXED = ("a", "dpad_up", "dpad_down", "dpad_left", "dpad_right")     # not for actions: steering, and A selects

# What each family of controller calls its buttons
_LETTERS = {"a": "A", "b": "B", "x": "X", "y": "Y", "start": "Start", "back": "Back", "guide": "Guide",
            "leftshoulder": "LB", "rightshoulder": "RB", "leftstick": "LS", "rightstick": "RS",
            "dpad_up": "D-pad up", "dpad_down": "D-pad down", "dpad_left": "D-pad left", "dpad_right": "D-pad right"}
LABELS = {
    "xbox": _LETTERS,
    "xbox_one": dict(_LETTERS, start = "Menu", back = "View"),
    "playstation": dict(_LETTERS, a = "Cross", b = "Circle", x = "Square", y = "Triangle", start = "Options",
                        back = "Share", leftshoulder = "L1", rightshoulder = "R1", leftstick = "L3", rightstick = "R3"),
    "nintendo": dict(_LETTERS, start = "+", back = "-", leftshoulder = "L", rightshoulder = "R"),
}
LABELS["generic"] = _LETTERS


def family(name):
    """Which labels a controller of this name uses."""
    n = (name or "").lower()
    if any(w in n for w in ("playstation", "ps3", "ps4", "ps5", "dualsense", "dualshock", "sony")):
        return "playstation"
    if any(w in n for w in ("nintendo", "switch", "pro controller", "joy-con", "joycon")):
        return "nintendo"
    if any(w in n for w in ("xbox one", "xbox series", "xbox wireless", "xbox elite")):
        return "xbox_one"
    if any(w in n for w in ("xbox", "xinput", "x-input", "x360")):
        return "xbox"
    return "generic"


class Pad:
    """One controller, as its events have left it."""

    def __init__(self, instance_id, name, device = None):
        self.id, self.name, self.device = instance_id, name, device
        self.family = family(name)
        self.buttons = set()            # names of the buttons held
        self.axes = {}                  # SDL axis -> -1..1

    def axis(self, axis):
        v = self.axes.get(axis, 0.0)
        return 0.0 if abs(v) < DEADZONE else math.copysign((abs(v) - DEADZONE) / (1 - DEADZONE), v)

    def stick(self):
        """The left stick, or the D-pad if it's held: (x, y), each -1..1."""
        x = self.axis(getattr(pygame, "CONTROLLER_AXIS_LEFTX", 0))
        y = self.axis(getattr(pygame, "CONTROLLER_AXIS_LEFTY", 1))
        dx = ("dpad_right" in self.buttons) - ("dpad_left" in self.buttons)
        dy = ("dpad_down" in self.buttons) - ("dpad_up" in self.buttons)
        if dx or dy:
            return float(dx), float(dy)
        return x, y


class Gamepads:
    def __init__(self, app):
        self.app = app
        self.pads = {}                  # instance id -> Pad, in the order they came
        self.last = None                # the one used last (its labels for the prompts)
        self.held = None                # menus: (direction, when it repeats next)
        self.scroll_next = 0.0
        self.listen = None              # (action, done) while Gameplay settings waits for a button
        self.available = False
        if sdl_controller is None or os.environ.get("HUTAONG_NO_PADS"):
            return                      # (the tests leave real controllers out, and add made-up ones)
        try:
            sdl_controller.init()
            sdl_controller.set_eventstate(True)
            self.available = True
            for i in range(sdl_controller.get_count()):
                self.open(i, quiet = True)          # (already there: no need to say so)
        except Exception as e:
            print(f"[gamepad] controllers unavailable: {e}")

    # ---------------- Coming and going ----------------

    def open(self, index, quiet = False):
        if sdl_controller is None or not sdl_controller.is_controller(index):
            return
        try:
            device = sdl_controller.Controller(index)
            stick = device.as_joystick()
            self.add(stick.get_instance_id(), device.name, device, quiet)
        except Exception as e:
            print(f"[gamepad] couldn't open controller {index}: {e}")

    def add(self, instance_id, name, device = None, quiet = False):
        """(Tests add made-up ones.)"""
        if instance_id not in self.pads:
            self.pads[instance_id] = Pad(instance_id, name, device)
            if not quiet:
                self.app.renderer.show_toast(f"Controller connected: {name}")

    def remove(self, instance_id):
        pad = self.pads.pop(instance_id, None)
        if pad is not None:
            self.app.renderer.show_toast(f"Controller disconnected: {pad.name}", important = True)
            if self.app.in_match() and not self.app.net:
                self.app.state_manager.push_state("pause", mute = True)     # its player can't play on
        if self.last is pad:
            self.last = None

    def order(self):
        return list(self.pads.values())

    # ---------------- Events ----------------

    def translate(self, event):
        """The game's own events for one of SDL's (most pass straight through)."""
        t = event.type
        if t == getattr(pygame, "CONTROLLERDEVICEADDED", -1):
            self.open(event.device_index)
            return []
        if t == getattr(pygame, "CONTROLLERDEVICEREMOVED", -1):
            self.remove(event.instance_id)
            return []
        if t == getattr(pygame, "CONTROLLERAXISMOTION", -1):
            pad = self.pads.get(event.instance_id)
            if pad is not None:
                pad.axes[event.axis] = max(-1.0, min(1.0, event.value / AXIS_MAX))
                if abs(pad.axes[event.axis]) > 0.5:
                    self.last = pad
            return []
        if t in (getattr(pygame, "CONTROLLERBUTTONDOWN", -1), getattr(pygame, "CONTROLLERBUTTONUP", -1)):
            pad = self.pads.get(event.instance_id)
            name = NAME_OF.get(event.button)
            if pad is None or name is None:
                return []
            down = t == pygame.CONTROLLERBUTTONDOWN
            (pad.buttons.add if down else pad.buttons.discard)(name)
            if down:
                self.last = pad
                return self.pressed(name)
            return self.released(name)
        if t in (getattr(pygame, "JOYAXISMOTION", -1), getattr(pygame, "JOYBUTTONDOWN", -1),
                 getattr(pygame, "JOYBUTTONUP", -1), getattr(pygame, "JOYHATMOTION", -1)):
            return []                   # (the same presses again, as a plain joystick's)
        return self.app.navigator.translate(event)

    def action_of(self, name):
        """The match action a button is set to, if any."""
        g = self.app.settings.gameplay
        for action in g.PAD_ACTIONS:
            if getattr(g, "pad_" + action) == name:
                return action
        return None

    def pressed(self, name):
        if self.listen is not None:                 # Gameplay settings: setting a button
            action, done = self.listen
            if name not in FIXED and name != "guide":
                self.listen = None
                done(name)
            return []
        nav = self.app.navigator
        if self.app.in_match():
            action = self.action_of(name)
            if action == "pause":
                return [key_event(pygame.KEYDOWN, pygame.K_ESCAPE), key_event(pygame.KEYUP, pygame.K_ESCAPE)]
            if action == "list":
                self.app.keys_down.add(pygame.K_TAB)        # (the HUD's talisman list, while held)
            if action and action.startswith("emote_"):
                self.app.emotes.send(int(action[6:]) - 1)   # (online only)
            return []
        if name in DPAD:
            self.held = (DPAD[name], time.perf_counter() + REPEAT_FIRST)
            return nav.move(*DPAD[name], via = "pad")
        if name == "a":
            return nav.activate(via = "pad")
        if name == "b" or name == "back":
            return [key_event(pygame.KEYDOWN, pygame.K_ESCAPE), key_event(pygame.KEYUP, pygame.K_ESCAPE)]
        if name == "start":
            top = self.app.state_manager.current()
            if getattr(top, "NAME", "") == "pause":
                return [key_event(pygame.KEYDOWN, pygame.K_ESCAPE), key_event(pygame.KEYUP, pygame.K_ESCAPE)]
            return nav.activate(via = "pad")
        return []

    def released(self, name):
        if name in DPAD:
            self.held = None
        if self.action_of(name) == "list":
            self.app.keys_down.discard(pygame.K_TAB)
        return []

    def update(self, dt):
        """Each frame: a held direction repeats in the menus; the stick works them too, and the
        right stick scrolls."""
        if not self.pads or self.app.in_match():
            return
        now = time.perf_counter()
        events = []
        stick = self.menu_stick()
        if stick != (0, 0):
            if self.held is None or self.held[0] != stick:
                self.held = (stick, now + REPEAT_FIRST)
                events += self.app.navigator.move(*stick, via = "pad")
            elif now >= self.held[1]:
                self.held = (stick, now + REPEAT_EVERY)
                events += self.app.navigator.move(*stick, via = "pad")
        elif self.held is not None and not any(DPAD.keys() & p.buttons for p in self.pads.values()):
            self.held = None
        scroll = sum(p.axis(getattr(pygame, "CONTROLLER_AXIS_RIGHTY", 3)) for p in self.pads.values())
        if abs(scroll) > 0.3 and now >= self.scroll_next:
            self.scroll_next = now + SCROLL_EVERY
            events.append(pygame.event.Event(pygame.MOUSEWHEEL, x = 0, y = -1 if scroll > 0 else 1,
                                             flipped = False, synthetic = True))
        for e in events:
            self.app.state_manager.handle_event(e)

    def menu_stick(self):
        """The direction the D-pad or a stick is pushed, for the menus: one of the four, or (0, 0)."""
        for pad in self.pads.values():
            for name, d in DPAD.items():
                if name in pad.buttons:
                    return d
            x, y = pad.axis(getattr(pygame, "CONTROLLER_AXIS_LEFTX", 0)), pad.axis(getattr(pygame, "CONTROLLER_AXIS_LEFTY", 1))
            if max(abs(x), abs(y)) > 0.5:
                return (1 if x > 0 else -1, 0) if abs(x) > abs(y) else (0, 1 if y > 0 else -1)
        return (0, 0)

    # ---------------- Play ----------------

    def players_here(self, game):
        """The paddles played on this computer (no AI, not the friend online)."""
        return [p for p in (game.p1, game.p2) if not p.ai_enabled and not getattr(p, "remote", False)
                and p is not getattr(game, "bench", None)]

    def pad_for(self, paddle):
        """The controller (or controllers) steering this paddle: [] for none."""
        pads = self.order()
        if not pads:
            return []
        game = paddle.game
        here = self.players_here(game)
        if paddle not in here:
            return []
        if len(here) == 1:
            return pads                                 # one player: any controller
        g = self.app.settings.gameplay
        red_keys = paddle.up == g.p1_up                # (a Switch moves the keys, and so the controller)
        first_is_red = g.pad_first == 0
        index = 0 if red_keys == first_is_red else 1
        return pads[index:index + 1]

    def steer_paddle(self, paddle):
        """(dvx, dvy) from its controller's stick, or None when it isn't being pushed (the keys then)."""
        x = y = 0.0
        for pad in self.pad_for(paddle):
            px, py = pad.stick()
            if abs(px) > abs(x):
                x = px
            if abs(py) > abs(y):
                y = py
        if not x and not y:
            return None
        return paddle.speed * max(-1.0, min(1.0, x)), paddle.speed * max(-1.0, min(1.0, y))

    def held_bits(self, netcode):
        """Online, on the friend's screen: the stick as the key bits the host reads."""
        bits = 0
        for pad in self.pads.values():
            x, y = pad.stick()
            bits |= (netcode.UP if y < -0.5 else 0) | (netcode.DOWN if y > 0.5 else 0)
            bits |= (netcode.LEFT if x < -0.5 else 0) | (netcode.RIGHT if x > 0.5 else 0)
        return bits

    # ---------------- Prompts ----------------

    def labels(self):
        pad = self.last or (self.order()[0] if self.pads else None)
        return LABELS[pad.family if pad else "xbox"]

    def label(self, name):
        return self.labels().get(name, name)

    def label_for(self, paddle):
        """How a paddle's player steers it, for the HUD and Match Setup: None if not by controller."""
        pads = self.pad_for(paddle)
        if not pads:
            return None
        if len(pads) > 1 or len(self.pads) == 1:
            return "Controller"
        return f"Controller {self.order().index(pads[0]) + 1}"


def key_event(kind, key):
    return pygame.event.Event(kind, key = key, mod = 0, unicode = "", scancode = 0, synthetic = True)


class Navigator:
    """The highlight that the D-pad, a stick or the arrow keys move from control to control in the
    menus, and that A or Enter presses (as a click on it, so every screen works as it does with
    the mouse).  It shows only while it's being used: the mouse moving puts it away."""

    FIRST = ("resume", "play", "start_match", "confirm", "back")      # where it starts, if it can
    SKIP = ("scrollbar",)           # dragged, not pressed: the highlight passes it by

    def __init__(self, app):
        self.app = app
        self.active = False
        self.via = "keys"               # "pad" or "keys": what's moving it (for the prompts)
        self.key = None
        self.seen = (None, {}, {})      # the top screen as last drawn: (screen, its controls, sliders' values)
        self.unrolled = {}              # a scrolling page's controls, as if scrolled to the bottom (see targets)

    def state(self):
        return self.app.state_manager.current()

    def snapshot(self):
        """After each frame is drawn: the controls on the top screen.  (A screen forgets them as it
        starts drawing the next, so the highlight works from the last whole frame.)"""
        state = self.state()
        self.seen = (state, dict(getattr(state, "ui_hitboxes", {})), dict(getattr(state, "ui_values", {})))
        self.unrolled = dict(getattr(state, "ui_unrolled", None) or {})

    def shown(self):
        """The controls on show: where the highlight is drawn, and where it presses."""
        state = self.state()
        if not getattr(state, "is_menu", False):
            return {}
        seen_state, boxes, _ = self.seen
        if seen_state is not state:
            boxes = getattr(state, "ui_hitboxes", {})
        return {k: r for k, r in boxes.items() if r.w > 0 and r.h > 0 and k not in self.SKIP}

    def targets(self):
        """Every control it can go to, and where, for finding the next one.  On a page that scrolls
        (1.9) that's every one on the page, on show or not, placed as if the page were scrolled to
        the bottom: so they keep their order, and Back and Reset stay below them all."""
        targets = self.shown()
        state = self.state()
        unrolled = self.unrolled if self.seen[0] is state else getattr(state, "ui_unrolled", None)
        if targets and unrolled:
            targets.update(unrolled)
        return targets

    def values(self):
        seen_state, _, values = self.seen
        return values if seen_state is self.state() else getattr(self.state(), "ui_values", {})

    def rect(self):
        targets = self.targets()
        if self.key not in targets:
            self.key = self.first(targets)
        return targets.get(self.key)

    def on_show(self):
        """The highlighted control where it's drawn now, or None (while it scrolls into sight)."""
        if self.rect() is None:
            return None
        return self.shown().get(self.key)

    def reveal(self):
        reveal = getattr(self.state(), "reveal", None)
        if reveal is not None and self.key is not None:
            reveal(self.key)

    def first(self, targets):
        for key in self.FIRST:
            if key in targets:
                return key
        if not targets:
            return None
        return min(targets, key = lambda k: (targets[k].top // 40, targets[k].left))

    def point(self):
        """Where the highlight is, as the mouse would be (the screens' hover and tooltips follow it)."""
        r = self.on_show() if self.active else None
        return r.center if r is not None else None

    def wake(self, via):
        was = self.active
        self.active, self.via = True, via
        return not was

    def move(self, dx, dy, via = "keys"):
        if self.wake(via) and self.rect() is not None:
            return []                   # the first push only shows where it is
        targets = self.targets()
        here = self.rect()
        if here is None:
            return []
        if dx and self.key in self.values():
            return self.nudge(dx)       # left and right move a slider
        cx, cy = here.center
        best, score = None, math.inf
        for key, r in targets.items():
            if key == self.key:
                continue
            vx, vy = r.centerx - cx, r.centery - cy
            along = vx * dx + vy * dy
            if along <= 4:
                continue
            across = abs(vx * dy - vy * dx)
            if across > along * 2.5:
                continue
            s = along + 2.2 * across
            if s < score:
                best, score = key, s
        if best is not None:
            self.key = best
            self.reveal()
            self.app.sound_manager.play("click.wav", multiplier = 0.4)
        return []

    def nudge(self, dx):
        """Left or right on a slider moves it a step (as a click there would)."""
        values = self.values()
        r = self.on_show()
        if not dx or self.key not in values or r is None:
            return []
        value = max(0.0, min(1.0, values[self.key] + 0.05 * dx))
        return self.click((r.left + value * r.width, r.centery))

    def activate(self, via = "keys"):
        if self.wake(via) and self.via == "pad" and self.rect() is None:
            return []
        r = self.on_show()
        if r is None:
            self.reveal()               # out of sight: scroll to it first
            return []
        return self.click(r.center)

    def click(self, base_pos):
        app = self.app
        pos = (int(base_pos[0] / app.sx), int(base_pos[1] / app.sy))
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos, synthetic = True),
                pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos, synthetic = True)]

    def translate(self, event):
        """The keyboard's part: the arrow keys and Enter in the menus.  Screens that use the arrows
        themselves (the replay viewer, the background picker) keep them."""
        t = event.type
        if t in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and not getattr(event, "synthetic", False):
            if t == pygame.MOUSEBUTTONDOWN or event.rel != (0, 0):
                self.active = False     # the mouse is back: put the highlight away
            return [event]
        if t != pygame.KEYDOWN or getattr(event, "synthetic", False):
            return [event]
        state = self.state()
        if not getattr(state, "is_menu", False) or getattr(state, "own_arrows", False):
            return [event]
        if getattr(state, "typing", lambda: False)():
            return [event]
        arrows = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}
        if event.key in arrows:
            return self.move(*arrows[event.key], via = "keys")
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.active and self.rect() is not None:
            return self.activate(via = "keys")
        return [event]

    def draw(self, screen):
        if not self.active:
            return
        r = self.on_show()
        if r is None:
            return
        from render import theme
        pulse = 0.5 + 0.5 * math.sin(time.perf_counter() * 5.0)
        ring = r.inflate(10, 10)
        colour = tuple(int(a + (b - a) * pulse) for a, b in zip(theme.GOLD, theme.GOLD_BRIGHT))
        pygame.draw.rect(screen, colour, ring, 3, border_radius = 10)
