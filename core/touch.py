"""Playing with fingers, on a phone or tablet (only there: see core/platform.py).

In a match, a finger steers a paddle.  Put it down anywhere on your side and slide it: the paddle
moves as the finger does (Drag), or heads for the point under it (Follow), at no more than the
paddle's own speed, so a finger is no faster than the keys.  With two players on one screen,
each player has their half of it; against the AI, or online, the whole screen is yours.

On the menus a finger is the mouse, with a phone's manners: a tap clicks when the finger lifts,
sliding a finger scrolls a list, a slider or the seek bar follows the finger straight away, and
a finger resting on a control shows its tooltip (and then lifts without clicking it).

Online, the friend's game only reads keys, held or not (core/net.py); so a guest's finger is
sent as keys held for the right share of the time, which comes to the same, smooth, speed.
"""
import math, time

import pygame

from config import BASE_W, BASE_H

OFF = (-10000, -10000)        # no finger: the "mouse" is nowhere near anything

TAP_SLOP = 30                 # px a finger may wander and still tap
SCROLL_STEP = 90              # px of sliding per row of a list
DRAG_KEYS = ("scrollbar", "music_seek", "replay_timeline")

STEER_MODES = ["Drag", "Follow"]
SENSITIVITY = [0.8, 1.0, 1.3, 1.7]          # how far Drag moves the paddle for a finger's move
SENSITIVITY_NAMES = ["Low", "Normal", "High", "Very High"]
STEER_K = 18.0                # 1/s: how hard a paddle heads for its finger
STEER_DAMP = 0.09             # s: allowance for the paddle's own easing, so it never overshoots

COLOURS = {"left": (255, 112, 92), "right": (112, 162, 255)}


def is_drag_key(key):
    return bool(key) and (key.endswith("_slider") or key in DRAG_KEYS)


def _event(kind, **values):
    return pygame.event.Event(kind, touch = False, window = None, **values)


class Finger:
    __slots__ = ("id", "x", "y", "x0", "y0", "t0", "kind", "slot", "tx", "ty", "rows")

    def __init__(self, fid, x, y):
        self.id, self.x, self.y, self.x0, self.y0 = fid, x, y, x, y
        self.t0 = time.monotonic()
        self.kind, self.slot, self.tx, self.ty, self.rows = None, None, x, y, 0.0


class TouchControls:
    def __init__(self, app):
        self.app = app
        self.fingers = {}           # finger id -> Finger
        self.menu_finger = None     # the one finger working the menus
        self.steer = {}             # "left" / "right" -> the id of the finger steering that paddle
        self.pointer = OFF          # where the menus see the mouse
        self.last = (BASE_W / 2, BASE_H / 2)
        self.queued = []            # a tap's clicks, handed over at the start of the next frame
        self.typing = False         # the phone's keyboard is up
        self.typing_state = None
        self.seen_focus = None      # the text box the screen had last frame
        self.tapped = False         # a tap was handed over this frame
        self.buzzed = 0.0
        self.report_in = 1.0
        self.ring = {}

    # ================================================================ events

    def translate(self, event):
        """The events to handle in place of `event`: fingers become steering or menu clicks."""
        kind = event.type
        if kind in (pygame.KEYDOWN, pygame.KEYUP) and event.key == getattr(pygame, "K_AC_BACK", None):
            # the phone's Back button is Esc: it closes a menu, or pauses a match
            return [pygame.event.Event(kind, key = pygame.K_ESCAPE, mod = 0, unicode = "\x1b",
                                       scancode = 41, window = None)]
        if kind == pygame.VIDEORESIZE:
            return []                                # the screen is the screen (see App.phone_display)
        if kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            return [] if getattr(event, "touch", False) else [event]     # SDL's copy of a finger
        if kind not in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return [event]
        if getattr(event, "touch_id", 0) == -1:
            return []                                                    # SDL's copy of the mouse
        x = min(BASE_W - 1.0, max(0.0, event.x * BASE_W))
        y = min(BASE_H - 1.0, max(0.0, event.y * BASE_H))
        if kind == pygame.FINGERDOWN:
            return self.down(event.finger_id, x, y)
        if kind == pygame.FINGERMOTION:
            return self.move(event.finger_id, x, y)
        return self.up(event.finger_id, x, y)

    def flush(self):
        """A tap's clicks, from the frame before (after one update with the finger over the
        control, so anything that clicks what is under the mouse sees it there)."""
        taps, self.queued = self.queued, []
        self.tapped = bool(taps)
        events = []
        for pos, key in taps:
            events += [_event(pygame.MOUSEMOTION, pos = pos, rel = (0, 0), buttons = (0, 0, 0)),
                       _event(pygame.MOUSEBUTTONDOWN, pos = pos, button = 1),
                       _event(pygame.MOUSEBUTTONUP, pos = pos, button = 1)]
            self.keyboard_for(key)
        if taps and self.menu_finger is None:
            self.pointer = OFF
        return events

    def top(self):
        return self.app.state_manager.current()

    def hit(self, x, y):
        state = self.top()
        return state.hit_test((x, y)) if state is not None and hasattr(state, "hit_test") else None

    def down(self, fid, x, y):
        finger = self.fingers[fid] = Finger(fid, x, y)
        self.last = (x, y)
        key = self.hit(x, y)
        if self.app.in_match():
            if key:                                  # the pause button: straight away
                finger.kind = "press"
                return self.press(finger)
            finger.kind = "steer"
            self.take_paddle(finger)
            return []
        if self.menu_finger is not None:
            finger.kind = "ignore"                   # one finger at a time works the menus
            return []
        self.menu_finger = fid
        self.pointer = (x, y)
        if is_drag_key(key):
            finger.kind = "press"
            return self.press(finger)
        finger.kind = "tap"
        return [_event(pygame.MOUSEMOTION, pos = (int(x), int(y)), rel = (0, 0), buttons = (0, 0, 0))]

    def press(self, finger):
        pos = (int(finger.x), int(finger.y))
        self.pointer = pos
        return [_event(pygame.MOUSEMOTION, pos = pos, rel = (0, 0), buttons = (0, 0, 0)),
                _event(pygame.MOUSEBUTTONDOWN, pos = pos, button = 1)]

    def move(self, fid, x, y):
        finger = self.fingers.get(fid)
        if finger is None:
            return []
        dx, dy = x - finger.x, y - finger.y
        finger.x, finger.y = x, y
        self.last = (x, y)
        if finger.kind == "steer":
            self.slide(finger, dx, dy)
            return []
        if finger.kind == "ignore":
            return []
        self.pointer = (x, y)
        pos = (int(x), int(y))
        if finger.kind == "press":
            return [_event(pygame.MOUSEMOTION, pos = pos, rel = (int(dx), int(dy)), buttons = (1, 0, 0))]
        if finger.kind == "tap" and math.hypot(x - finger.x0, y - finger.y0) > TAP_SLOP:
            finger.kind = "scroll"
        events = [_event(pygame.MOUSEMOTION, pos = pos, rel = (int(dx), int(dy)), buttons = (0, 0, 0))]
        if finger.kind == "scroll":
            finger.rows += dy / SCROLL_STEP
            while abs(finger.rows) >= 1:
                step = 1 if finger.rows > 0 else -1          # the list follows the finger
                finger.rows -= step
                events.append(_event(pygame.MOUSEWHEEL, x = 0, y = step, flipped = False,
                                     precise_x = 0.0, precise_y = float(step), which = 0))
        return events

    def up(self, fid, x, y):
        finger = self.fingers.pop(fid, None)
        if finger is None:
            return []
        finger.x, finger.y = x, y
        for slot, owner in list(self.steer.items()):
            if owner == fid:
                del self.steer[slot]
        if fid == self.menu_finger:
            self.menu_finger = None
        pos = (int(finger.x0), int(finger.y0))
        if finger.kind == "press":
            if not self.queued:
                self.pointer = OFF
            return [_event(pygame.MOUSEBUTTONUP, pos = (int(x), int(y)), button = 1)]
        if finger.kind == "tap":
            if self.app.renderer.tips.showing():
                self.pointer = OFF                   # a long press that read the tooltip
                return []
            self.pointer = pos
            self.queued.append((pos, self.hit(*pos)))
            return []
        if finger.kind == "scroll":
            self.pointer = OFF
        return []

    # ================================================================ steering

    def slots(self):
        """The sides with a paddle a finger here can steer: "left", "right", or both."""
        state = self.top()
        if getattr(state, "NAME", "") == "guest_match":
            net = self.app.net
            info = net.snaps[-1][2] if net and net.snaps else {}
            return ["left" if info.get("guest", 2) == 1 else "right"]
        game = getattr(state, "game", None)
        if game is None or not hasattr(game, "p1"):
            return []
        return ["left" if p.is_left else "right" for p in (game.p1, game.p2)
                if not p.ai_enabled and not getattr(p, "remote", False)]

    def take_paddle(self, finger):
        slots = self.slots()
        if not slots:
            finger.kind = "ignore"
            return
        if len(slots) == 1:
            slot = slots[0]
        else:
            slot = "left" if finger.x < BASE_W / 2 else "right"
        finger.slot = slot
        self.steer[slot] = finger.id                 # the newest finger on a side has its paddle
        centre = self.paddle_centre(slot)
        if self.app.settings.interface.touch_steer == 0 and centre is not None:
            finger.tx, finger.ty = centre            # Drag: the paddle moves on from where it is
        else:
            finger.tx, finger.ty = finger.x, finger.y

    def slide(self, finger, dx, dy):
        if self.app.settings.interface.touch_steer == 0:
            gain = SENSITIVITY[self.app.settings.interface.touch_sensitivity]
            finger.tx = min(BASE_W, max(0.0, finger.tx + dx * gain))
            finger.ty = min(BASE_H, max(0.0, finger.ty + dy * gain))
        else:
            finger.tx, finger.ty = finger.x, finger.y

    def paddle_centre(self, slot):
        state = self.top()
        game = getattr(state, "game", None)
        if game is not None and hasattr(game, "p1"):
            for p in (game.p1, game.p2):
                if ("left" if p.is_left else "right") == slot:
                    return (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2
        box = getattr(state, "own_box", None)
        if box is not None:
            x, y, w, h = box
            return x + w / 2, y + h / 2
        return None

    def target(self, slot, w, h):
        finger = self.fingers.get(self.steer.get(slot))
        if finger is None:
            return None
        # the paddle's centre can't go past the court's edges, so neither does the target: a
        # finger that ran on past the wall moves the paddle back as soon as it turns
        finger.tx = min(BASE_W - w / 2, max(w / 2, finger.tx))
        finger.ty = min(BASE_H - h / 2, max(h / 2, finger.ty))
        return finger.tx, finger.ty

    @staticmethod
    def ask(error, velocity, speed):
        return max(-speed, min(speed, STEER_K * (error - STEER_DAMP * velocity)))

    def steer_paddle(self, paddle):
        """The velocity a finger asks of this paddle, or None when no finger is on it."""
        slot = "left" if paddle.is_left else "right"
        if slot not in self.steer:
            return None
        aim = self.target(slot, paddle.width, paddle.height)
        if aim is None:
            return None
        cx, cy = (paddle.x0 + paddle.x1) / 2, (paddle.y0 + paddle.y1) / 2
        return (self.ask(aim[0] - cx, paddle.vx, paddle.speed),
                self.ask(aim[1] - cy, paddle.vy, paddle.speed))

    def guest_axis(self, state, speed):
        """Online, as a guest: the finger on your paddle as a share of full speed on each axis
        (-1 to 1), or None when no finger is on it."""
        slots = self.slots()
        box, pred = getattr(state, "own_box", None), getattr(state, "pred", None)
        if not slots or slots[0] not in self.steer or box is None or pred is None:
            return None
        x, y, w, h = box
        aim = self.target(slots[0], w, h)
        if aim is None:
            return None
        speed = max(1.0, speed)
        return (self.ask(aim[0] - (x + w / 2), pred[2], speed) / speed,
                self.ask(aim[1] - (y + h / 2), pred[3], speed) / speed)

    # ================================================================ the phone's keyboard

    def keyboard_for(self, key):
        """A tap on a text box brings up the phone's keyboard; a tap anywhere else puts it away."""
        if key and key.endswith("_field"):
            self.start_typing()
        elif self.typing:
            self.stop_typing()

    def start_typing(self):
        self.typing, self.typing_state = True, self.top()
        try:
            pygame.key.start_text_input()            # (again, if Back put the keyboard away)
        except Exception:
            pass

    def stop_typing(self):
        self.typing, self.typing_state = False, None
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass

    def update(self, dt):
        self.report_in -= dt
        if self.report_in <= 0:              # a line in the phone's log now and then (adb logcat)
            self.report_in = 5.0
            print(f"[Hu Taong] {self.app.clock.get_fps():.0f} FPS on {getattr(self.top(), 'NAME', '?')}", flush = True)
        state = self.top()
        focus = getattr(state, "focus", None) if hasattr(state, "type_into") else None
        if focus and focus != self.seen_focus and self.tapped and not self.typing:
            self.start_typing()                      # a tap opened a text box (Join, say): type straight away
        self.seen_focus, self.tapped = focus, False
        if self.typing and (state is not self.typing_state or not focus):
            self.stop_typing()
        if not self.app.in_match():
            for finger in self.fingers.values():
                if finger.kind == "steer":            # the match ended under the finger
                    finger.kind = "ignore"
            self.steer.clear()
            return
        slots = None
        for finger in self.fingers.values():
            if finger.kind == "steer" and self.steer.get(finger.slot) == finger.id:
                slots = self.slots() if slots is None else slots
                if finger.slot not in slots:          # Chaos Switch handed its paddle to the AI
                    del self.steer[finger.slot]
                    self.take_paddle(finger)

    def reset(self):
        """The game went into the background: every finger has lifted."""
        self.fingers.clear()
        self.steer.clear()
        self.menu_finger = None
        self.pointer = OFF

    # ================================================================ tilt

    def tilt(self, dt):
        """How far the phone is tipped from the way it is usually held, -1 to 1 across and down,
        for the background's parallax (on a PC the mouse does it)."""
        if not hasattr(self, "accel"):
            self.accel, self.rest_x, self.rest_y, self.tipped = None, None, None, (0.0, 0.0)
            try:
                pygame.joystick.init()
                for i in range(pygame.joystick.get_count()):
                    stick = pygame.joystick.Joystick(i)
                    if "accel" in stick.get_name().lower() and stick.get_numaxes() >= 2:
                        stick.init()
                        self.accel = stick
                        pygame.event.set_blocked([pygame.JOYAXISMOTION])
                        break
            except Exception:
                self.accel = None
        if self.accel is None:
            return 0.0, 0.0
        try:
            x, y = self.accel.get_axis(0), self.accel.get_axis(1)
        except Exception:
            return 0.0, 0.0
        if self.rest_x is None:
            self.rest_x, self.rest_y = x, y
        settle = min(1.0, dt / 4.0)                 # the resting angle follows how it's held, slowly
        self.rest_x += (x - self.rest_x) * settle
        self.rest_y += (y - self.rest_y) * settle
        want = (max(-1.0, min(1.0, (x - self.rest_x) * 4)), max(-1.0, min(1.0, (y - self.rest_y) * 4)))
        ease = min(1.0, 8 * dt)                      # and the sensor's jitter is smoothed away
        self.tipped = (self.tipped[0] + (want[0] - self.tipped[0]) * ease,
                       self.tipped[1] + (want[1] - self.tipped[1]) * ease)
        return self.tipped

    # ================================================================ feel

    def buzz(self, ms, strength = 110):
        if not self.app.settings.interface.vibration:
            return
        now = time.monotonic()
        if now - self.buzzed < 0.06:
            return
        self.buzzed = now
        from core import android
        android.vibrate(ms, strength)

    def felt_hit(self, paddle):
        """Your paddle hit the ball."""
        if not paddle.ai_enabled and not getattr(paddle, "remote", False):
            self.buzz(16, 90)

    def draw(self, screen):
        """A soft ring under each finger that is steering, in its paddle's colour."""
        for slot, fid in self.steer.items():
            finger = self.fingers.get(fid)
            if finger is None:
                continue
            ring = self.ring.get(slot)
            if ring is None:
                ring = self.ring[slot] = pygame.Surface((132, 132), pygame.SRCALPHA)
                colour = COLOURS[slot]
                pygame.draw.circle(ring, colour + (34,), (66, 66), 62)
                pygame.draw.circle(ring, colour + (110,), (66, 66), 62, 3)
            screen.blit(ring, (int(finger.x) - 66, int(finger.y) - 66))

    def draw_typing(self, screen, renderer):
        """While the phone's keyboard covers the bottom of the screen, what you type shows at the top."""
        state = self.top()
        name = getattr(state, "focus", None) if self.typing else None
        texts = getattr(state, "text", None)
        if not name or not isinstance(texts, dict):
            return
        text = str(texts.get(name, ""))
        if "password" in name:
            text = "•" * len(text)
        label = {"code": "Room code"}.get(name, name.replace("_", " ").capitalize())
        art = self.app.art
        font, small = art.ui(40), art.ui(24, bold = False)
        shown = text + ("|" if int(time.monotonic() * 2) % 2 == 0 else " ")
        w = max(720, font.size(shown)[0] + 120)
        plate = pygame.Rect(BASE_W // 2 - w // 2, 24, w, 128)
        screen.blit(art.inset(plate.w, plate.h), plate)
        from render import theme
        renderer.text(screen, label, small, theme.GOLD, center = (plate.centerx, plate.y + 30))
        renderer.text(screen, shown, font, theme.GOLD_BRIGHT, center = (plate.centerx, plate.y + 80))
