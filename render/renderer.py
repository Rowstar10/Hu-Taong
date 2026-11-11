import math, random, pygame
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from config import BASE_W, BASE_H
from helpers import clamp01, lerp
from render import theme
from render.art import ADD, blank, mix, scaled, v_gradient
from core.settings import key_name
from core import net as netcode
from core.platform import ANDROID
from core import rooms
from game import courts
from game.powerups import BY_KEY as POWERUPS, FAMILY_COLOURS, FAMILY_NOTES, KINDS as POWERUP_KINDS, PowerUps
from render.ui.layout import Node, Space
from render.ui.layout import (Stack, Grid, Text, Label, Title, Button, Toggle, CycleToggle, KeyButton,
                              Cycle, Slider, Slot, Space, TrackBar, Icon, Picture, TextField)

# What each control does, shown when the mouse rests on it.  First line: the title.  Then one
# short line on what it does, and bullets for the details (see Tooltips for the markers).
TIPS = {
    # Main menu and the settings hub
    "play": "Play\nChoose your opponent, paddle and court, then start.\n~ Enter",
    "stats": "Stats\nYour lifetime record, and your saved replays.",
    "settings": "Settings\nDisplay, gameplay, sound and interface.",
    "prompt_quit": "Quit\nClose the game. Settings and stats are saved.\n~ Esc",
    "display": "Display\nWindow, frame rate and background.",
    "gameplay": "Gameplay\nThe AI, match rules, ball and paddles, Chaos modes and power-ups.",
    "audio": "Audio\nVolume, sound effects and the jukebox.",
    "interface": "Interface\nTooltips, HUD, effects, replays and keys.",
    "reset_all": "Reset All Settings\nEvery setting on every screen back to its default.\n• Your stats and replays are kept",

    # Match setup
    "opponent_ai": "vs AI\nYou play one paddle, the AI the other.",
    "opponent_human": "vs Human\nTwo players on one keyboard.",
    "opponent_online": "Online\nPlay a friend over the internet: one of you hosts, the other joins with a code.",
    "start_match": "Start Match\nPlay with the settings chosen here and in Gameplay.\n~ Enter",

    # Gameplay
    "toggle_adaptive_ai": "Adaptive AI\nKeeps matches close.\n• Eases off a level for every 3 points it leads\n• Sharpens up when it's behind",
    "toggle_win_by_two": "Win by Two\nThe winner needs a two-point lead.",
    "ball_speed_slider": "Ball Speed\nHow fast the ball is served.\n• Hard hits speed it up, to about 4.5 times this",
    "pace_slider": "Game Pace\nSlows down or speeds up the whole match.\n• Ball, paddles, AI and Chaos timers together\n~ Turn it down if the ball is too quick to follow",
    "paddle_speed_slider": "Paddle Speed\nHow fast the paddles move.",
    "ball_diameter_slider": "Ball Size\nHow big the ball is.",
    "paddle_size_slider": "Paddle Size\nHow tall and wide the paddles are.",
    "randomise_all": "Randomise All\nRandom ball and paddle speeds and sizes.",
    "open_powerups": "Power-Ups\nSee what each power-up does, and choose which can appear.",
    "toggle_powerups": "Power-Ups\nTalismans appear on the court during a match.\n• Touch one with your paddle, or a ball you hit last\n~ Hold Tab in a match to see every power-up in play",
    "toggle_lantern_night": "Lantern Night\nThe court is always dark, lit only by lanterns round the paddles and the ball's glow.\n~ Off by default",
    "toggle_curveball": "Curveball\nEvery hit bends the way the paddle was moving as it hit.\n"
                        "• Sweep up or down as you hit to curve the ball; a still paddle hits it straight\n"
                        "• The spin fades as it flies\n~ Off by default",
    "toggle_middle_wall": "Middle Wall\nEach paddle stays in its own half.\n• Off: paddles can roam the whole court\n~ Turning it on turns Chaos Switch + off",

    # Display
    "cycle_res": "Resolution\nThe window's size.\n~ Press Apply to use it",
    "cycle_mode": "Window Mode\nWindowed, borderless or fullscreen.\n~ Press Apply to use it",
    "apply": "Apply\nUse the resolution and window mode above.",
    "cycle_max_fps": "Maximum FPS\nThe frame-rate cap.\n• Lower saves power, higher is smoother",
    "toggle_show_fps": "Show FPS\nThe frame rate, in the bottom corner.",
    "background_thumb": "Background\nChoose the picture behind the game.",
    "toggle_rotate_bg": "Rotate\nFade to a different background every so often.",
    "cycle_rotate_every": "Change Every\nHow long each background stays before Rotate fades to the next.",
    "cycle_parallax": "Parallax\nThe menu background drifts against the mouse, for depth.",
    "dim_slider": "Dim\nDarkens the background so the ball stands out.",

    # Audio
    "master_volume_slider": "Master Volume\nEverything: music and effects.",
    "music_volume_slider": "Music Volume\nThe jukebox.",
    "sfx_volume_slider": "Effects Volume\nHits, scores, menus and ambience.",
    "toggle_paddle_sounds": "Paddle Sounds\nThe sound of each hit.",
    "toggle_score_sounds": "Score Sound\nThe sound when someone scores.",
    "toggle_menu_sounds": "Menu Sounds\nClicks and whooshes in the menus.",
    "cycle_music": "Track\nSkip through tracks for this moment: calm in menus, upbeat in matches.\n~ Click the name for the full list",
    "music_seek": "Progress\nHow far through the track you are.\n~ Click or drag along the bar to jump",
    "music_pause": "Play / Pause\nPause or resume the music.",
    "toggle_even_volume": "Even Out Volume\nTurns down tracks recorded much louder than the rest.",

    # Interface
    "toggle_tooltips": "Tooltips\nThese notes, when you rest the mouse on a control.",
    "toggle_ai_banter": "AI Banter\nThe AI's quips after a point, in a speech bubble.",
    "toggle_screen_shake": "Screen Shake\nThe screen shakes when someone scores.",
    "toggle_ball_trail": "Ball Trail\nA fire trail behind the ball.",
    "toggle_auto_pause": "Auto-Pause\nPause the match if you click away from the game.",
    "toggle_hide_cursor": "Hide Mouse\nHide the mouse in a match until you move it.",
    "toggle_vibration": "Vibration\nA little buzz when your paddle hits the ball, and a bigger one at each point.",
    "key": "Key\nClick, then press the new key.\n• A key that's already used swaps over\n~ Esc cancels",

    # Stats
    "reset_stats": "Reset Stats\nClear every lifetime stat.\n~ This can't be undone",
    "export_stats": "Export Stats\nSave your stats to a file, to keep or to move to another computer.",
    "import_stats": "Import Stats\nLoad stats from an exported file.\n~ They replace the stats here",
    "open_replays": "Replays\nWatch or delete the matches, clips and highlights you've saved.",
}

class _PowerTile(Node):
    """A power-up's tile on the Power-Ups screen; it notes when the mouse is on it, so the details
    panel below can describe that power-up."""

    def __init__(self, child, key):
        super().__init__()
        self.child, self.key = child, key

    def measure(self):
        self.w, self.h = self.child.measure()
        return self.w, self.h

    def place(self, x, y, w, h):
        self.rect = pygame.Rect(x, y + (h - self.h) // 2, self.w, self.h)      # left-aligned in its column
        self.child.place(self.rect.x, self.rect.y, self.w, self.h)

    def draw(self, ui):
        self.child.draw(ui)
        if self.rect.inflate(10, 10).collidepoint(ui.mouse):
            ui.state.pu_hover = self.key


class _PowerDetails(Node):
    """The panel under the tiles: the power-up the mouse is on, in full (or a hint)."""
    LINES = 7

    def __init__(self, width, title_font, body_font, s):
        super().__init__()
        self.title_font, self.body_font, self.s = title_font, body_font, s
        self.line_h = body_font.size("Ag")[1] + int(4 * s)
        self.pad = int(18 * s)
        self.w = width
        self.h = self.pad * 2 + title_font.size("Ag")[1] + int(8 * s) + self.line_h * (self.LINES - 1)

    def draw(self, ui):
        key = getattr(ui.state, "pu_hover", None)
        ui.state.pu_hover = None                    # the tiles mark it again next frame, if still pointed at
        r = self.rect
        ui.screen.blit(ui.art.inset(r.w, r.h), r)
        if key is None:
            hint = "Point at a power-up to see what it does.  Click its switch to turn it on or off."
            surf = ui.text(self.body_font, hint, theme.PARCHMENT)
            ui.screen.blit(surf, surf.get_rect(center=r.center))
            return
        kind = POWERUPS[key]
        icon = ui.art.power_icon(int(r.h * 0.42), kind.key, kind.family)
        ui.screen.blit(icon, icon.get_rect(midleft=(r.x + self.pad, r.centery)))
        x = r.x + self.pad * 2 + icon.get_width()
        y = r.y + self.pad
        title = ui.text(self.title_font, kind.name, theme.GOLD_BRIGHT)
        note = ui.text(self.body_font, "   " + FAMILY_NOTES[kind.family], FAMILY_COLOURS[kind.family])
        ui.screen.blit(title, (x, y))
        ui.screen.blit(note, (x + title.get_width(), y + (title.get_height() - note.get_height()) // 2))
        y += title.get_height() + int(8 * self.s)
        for line in kind.about.split("\n")[:self.LINES - 1]:
            ui.screen.blit(ui.text(self.body_font, line, theme.PARCHMENT), (x, y))
            y += self.line_h


STYLE_TIPS = {
    "Balanced": "a steady all-rounder.",
    "Guardian": "a wall: reads the ball best, keeps to the middle of its goal and rarely misses. Rarely attacks.",
    "Striker": "steps in and drives through the ball at sharp angles. With the wall down it storms past halfway and hits harder still. Leaves gaps behind it.",
    "Trickster": "fakes one angle and plays another, lunges as if to drive then drops it short, darts about between shots, and loves bank shots.",
}


def options_tip(title, intro, options, current=None, hint=None):
    """A tip for a control that steps through options: what it is, then each option on its own
    line, the one in use marked."""
    lines = [title, intro]
    for i, (name, meaning) in enumerate(options):
        lines.append(("» " if i == current else "• ") + (f"{name}: {meaning}" if meaning else name))
    if hint:
        lines.append("~ " + hint)
    return "\n".join(lines)


KEY_HINTS = ("Esc", "Enter", "Space", "Ctrl", "Tab", "Keys:", "Mouse wheel", "Left / Right", "Hold Tab")


def touch_tip(text):
    """A tip as a phone shows it: no keyboard shortcuts, and controls are tapped, not clicked."""
    lines = []
    for line in text.split("\n"):
        hint = line[2:] if line.startswith("~ ") else None
        if hint is not None and (hint.startswith(KEY_HINTS) or (len(hint) == 1 and hint.isupper())):
            continue
        lines.append(line.replace("click away", "switch away").replace("Click", "Tap").replace("click", "tap"))
    return "\n".join(lines)


class Tooltips:
    """Short explanations that appear when the mouse rests on a control (on a phone, a finger).

    A tip is a few lines: the first is its title and the rest explain it.  A line starting with
    "• " is a bullet, "» " the bullet for the option in use, and "~ " a quiet hint (a shortcut,
    a warning).  A tip with no line breaks is shown as one plain paragraph."""

    DELAY = 0.45
    WIDTH = 520

    def __init__(self, app):
        self.app = app
        self.offered = None
        self.text = None
        self.rest = 0.0
        self.cache = {}

    def offer(self, rect, text):
        if text and rect.collidepoint(self.app.renderer.mouse()):
            self.offered = touch_tip(text) if ANDROID else text

    def showing(self):
        """A tip is up (on a phone, a finger resting on a control asked for it)."""
        return self.text is not None and self.rest >= self.DELAY

    def wrap(self, font, text, width):
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if line and font.size(trial)[0] > width:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        return lines

    def layout(self, text):
        """[(font, colour, indent, marker, line)] for every line the tip draws."""
        art = self.app.art
        title_font, body_font, hint_font = art.ui(25), art.ui(23, bold=False), art.ui(20, bold=False)
        parts = text.split("\n")
        if len(parts) == 1:
            return [(body_font, theme.PARCHMENT, 0, None, l) for l in self.wrap(body_font, text, self.WIDTH)], []
        rows = [(title_font, theme.GOLD_BRIGHT, 0, None, l) for l in self.wrap(title_font, parts[0], self.WIDTH)]
        gaps = [len(rows)]                         # a little space under the title
        for part in parts[1:]:
            if part.startswith(("• ", "» ")):
                current = part.startswith("» ")
                colour = theme.GOLD_BRIGHT if current else theme.PARCHMENT
                for i, l in enumerate(self.wrap(body_font, part[2:], self.WIDTH - 26)):
                    rows.append((body_font, colour, 26, ("current" if current else "bullet") if i == 0 else None, l))
            elif part.startswith("~ "):
                rows.append((hint_font, theme.GOLD, 0, None, ""))     # breathing room
                rows += [(hint_font, theme.GOLD, 0, None, l) for l in self.wrap(hint_font, part[2:], self.WIDTH)]
            else:
                rows += [(body_font, theme.PARCHMENT, 0, None, l) for l in self.wrap(body_font, part, self.WIDTH)]
        return rows, gaps

    def surface(self, text):
        surf = self.cache.get(text)
        if surf is None:
            art = self.app.art
            rows, gaps = self.layout(text)
            pad = 16
            heights = [font.get_linesize() if line or marker else font.get_linesize() // 3
                       for font, _, _, marker, line in rows]
            extra = 8 * len(gaps)
            w = max(font.size(line)[0] + indent for font, _, indent, _, line in rows) + 2 * pad
            h = sum(heights) + extra + 2 * pad
            surf = blank(w, h)
            surf.blit(art.inset(w, h), (0, 0))
            y = pad
            for i, ((font, colour, indent, marker, line), step) in enumerate(zip(rows, heights)):
                if i in gaps:
                    pygame.draw.line(surf, theme.GOLD_DARK, (pad, y + 3), (w - pad, y + 3), 1)
                    y += 8
                x = pad + indent
                if marker == "bullet":
                    pygame.draw.circle(surf, theme.GOLD, (x - 13, y + step // 2 + 1), 4)
                elif marker == "current":
                    cy = y + step // 2 + 1
                    pygame.draw.polygon(surf, theme.EMBER, [(x - 19, cy - 6), (x - 19, cy + 6), (x - 9, cy)])
                if line:
                    surf.blit(font.render(line, True, colour), (x, y))
                y += step
            if len(self.cache) > 300:
                self.cache.clear()
            self.cache[text] = surf
        return surf

    def draw(self, screen, dt):
        text, self.offered = self.offered, None
        if text is None or not self.app.settings.interface.tooltips:
            self.text, self.rest = None, 0.0
            return
        if text != self.text:
            # the same control with a new value (a cycle's tip) keeps showing, without a new wait
            same = self.text is not None and self.text.split("\n")[0] == text.split("\n")[0]
            self.text = text
            if not same:
                self.rest = 0.0
        self.rest += dt
        if self.rest < self.DELAY:
            return

        surf = self.surface(text)
        surf.set_alpha(int(255 * min(1.0, (self.rest - self.DELAY) / 0.15)))
        mx, my = self.app.renderer.mouse()
        x, y = mx + 20, my + 28
        if ANDROID:
            # above the finger, which would hide anything under it
            x, y = mx - surf.get_width() // 2, my - surf.get_height() - 90
            if y < 8:
                y = my + 110
            x = min(x, BASE_W - 8 - surf.get_width())
        if x + surf.get_width() > BASE_W - 8:
            x = mx - surf.get_width() - 12
        if y + surf.get_height() > BASE_H - 8:
            y = my - surf.get_height() - 12
        screen.blit(surf, (max(8, x), max(8, y)))


class Renderer:
    def __init__(self, app):
        self.app = app
        self.art = app.art

        self._sigil_turns: dict = {}
        self._sigil_shown: dict = {}
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sigil")
        self._lift: dict = {}
        self._bubbles: dict = {}
        self.tips = Tooltips(app)

        # Gap constants — BASE_W/H never change so compute once
        self._gx = int(BASE_W * 0.02)
        self._gy = int(BASE_H * 0.02)

        # Game feel: all purely visual, none of it touches the physics.
        self._toast = None              # [surface, age]
        self._shake_time = 0.0
        self._shake_total = 0.0
        self._shake_mag = 0
        self._trail = deque(maxlen=14)
        self._twin_trail = deque(maxlen=14)     # Twin Balls' blue ball has its own
        self._leaves = []                        # Wind Gust's leaves: [x, y, vx, vy, angle, spin, colour, size, phase]
        self._night = None                       # Lantern Night's darkness, made once

    # ── Shorthands ─────────────────────────────────────────────────────────────
    # Menus are *described* here (what is on the screen); UILayout decides where
    # everything goes.  See render/ui/layout.py.

    @property
    def ui(self):
        return self.app.ui_layout

    def section(self, ui, s, header, *controls):
        """A gold heading with its controls underneath."""
        return Stack([Label(header, ui.fnt(0.034, s)), *controls], gap=int(ui.gap * 0.9 * s))

    def vgap(self, ui, s, mult=1.0):
        return int(ui.gap * mult * s)

    def toggle(self, ui_font, key, name, flag, tip=None):
        return Toggle(key, lambda: f"{name}: {'ON' if flag() else 'OFF'}", ui_font, flag,
                      [f"{name}: ON", f"{name}: OFF"], tip=tip or TIPS.get(key))

    def fnt(self, frac, bold=True):
        """Shorthand: proportional UI font by BASE_H fraction."""
        return self.app.font_manager.get("ui", int(BASE_H * frac), bold=bold)

    def brush(self, frac):
        """Shorthand: proportional calligraphy font by BASE_H fraction."""
        return self.app.font_manager.get("brush", int(BASE_H * frac))

    def fit_font(self, text, max_width, size, name="ui"):
        """Largest font up to `size` that keeps `text` inside `max_width`."""
        manager = self.app.font_manager
        while size > 12:
            font = manager.get(name, size, bold=True)
            if font.size(text)[0] <= max_width:
                return font
            size -= 2
        return manager.get(name, 12, bold=True)

    def mouse(self):
        return self.app.pointer()

    def lift(self, key, active):
        """Eases towards 1 while `active`, so hovered things rise smoothly."""
        now = self._lift.get(key, 0.0)
        now += ((1.0 if active else 0.0) - now) * min(1, 14 * self.app.dt)
        self._lift[key] = now
        return now

    def text(self, screen, text, font, col, shadow=theme.INK, **anchor):
        """Blit cached text with a small drop shadow; return its Rect."""
        surf = self.art.text(text, font, col)
        rect = surf.get_rect(**anchor)
        if shadow:
            screen.blit(self.art.text(text, font, shadow), rect.move(2, 3))
        screen.blit(surf, rect)
        return rect

    # ── Lacquerwork shared by the layout nodes ─────────────────────────────────

    def draw_face(self, screen, mouse_pos, rect, finish):
        """Draw a lacquered button face; return the press offset for its contents."""
        hovered = rect.collidepoint(mouse_pos)
        down = hovered and self.app.pointer_down()
        offset = 3 if down else 0
        m = self.art.BUTTON_MARGIN
        screen.blit(self.art.button(rect.w, rect.h, finish, hovered, down), (rect.x - m, rect.y - m + offset))
        return offset

    def draw_lacquer(self, screen, mouse_pos, rect, text, font, finish, fg=None):
        offset = self.draw_face(screen, mouse_pos, rect, finish)
        fg = fg or theme.LACQUER[finish][3]
        shadow = None if finish == "paper" else theme.INK
        self.text(screen, text, font, fg, shadow, center=(rect.centerx, rect.centery - 3 + offset))
        return rect

    def draw_button(self, screen, mouse_pos, font, text, cx, cy, col, *, width=None):
        """A lacquered button for the screens not built by the layout engine."""
        w = width or font.size(text)[0] + 2 * self._gx
        h = font.get_height() + self._gy
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        return self.draw_lacquer(screen, mouse_pos, rect, text, font, theme.finish(col))

    def draw_toggle(self, screen, mouse_pos, rect, text, font, on, glyph=None, hot=False):
        offset = self.draw_face(screen, mouse_pos, rect, "ink")

        size = rect.h - 18
        screen.blit(self.art.seal(size, on, glyph, hot), (rect.x + 12, rect.y + 6 + offset))
        col = theme.FLAME if hot else theme.GOLD_BRIGHT if on else theme.OFF_TEXT
        centre = rect.x + size + 20 + (rect.w - size - 28) // 2
        self.text(screen, text, font, col, center=(centre, rect.centery - 3 + offset))

    def draw_board(self, screen, rect, mark=None):
        """The lacquered panel, with an optional faint character across it."""
        m = self.art.PANEL_MARGIN
        x, y = rect.x - m, rect.y - m
        screen.blits([(piece, (x + dx, y + dy)) for piece, (dx, dy) in self.art.board(rect.w, rect.h, mark)], False)

    def draw_plaque(self, screen, text, cy):
        """Title board, centred at the top of the screen."""
        w, h = 620, 112
        m = self.art.PLAQUE_MARGIN
        screen.blit(self.art.plaque(w, h), (BASE_W // 2 - w // 2 - m, cy - h // 2 - m))
        title = self.art.gilded(text, self.fit_font(text, w - 150, 74, "brush"), glow=None)
        screen.blit(title, title.get_rect(center=(BASE_W // 2, cy - 2)))

    def draw_frame(self, screen, text, mark, panel=None):
        """The board and title shared by every settings screen."""
        panel = panel or self.ui.PANEL
        self.draw_board(screen, panel, mark)
        self.draw_plaque(screen, text, panel.top)

    def draw_sigil(self, screen, center, size, alpha, speed=5.0):
        """Slowly turning seal, re-turned 10 times a second.  Each turn is rotated a step ahead
        on a worker thread, as a full rotozoom is too slow to do mid-frame, and its faintness
        is baked in (in steps of 15) because a blit with extra transparency is slow too."""
        tick = int(self.app.fx.time * 10)
        level = max(15, min(255, round(alpha / 15) * 15))
        turns = self._sigil_turns.setdefault((size, level), {})
        for t in (tick, tick + 1):
            if t not in turns:
                turns[t] = self.worker.submit(pygame.transform.rotozoom, self.art.faint_sigil(size, level),
                                              t / 10 * speed, 1)

        ready = [t for t, job in turns.items() if t <= tick and job.done()]
        if ready:
            newest = max(ready)
            self._sigil_shown[size] = (level, turns[newest].result())
            for t in [t for t in turns if t < newest or t > tick + 1]:
                del turns[t]

        # Until this faintness has a turn ready, the last one shown stands in
        shown = self._sigil_shown.get(size)
        if shown is None:
            shown = self._sigil_shown[size] = (level, turns[tick].result())
        shown_level, sprite = shown
        sprite.set_alpha(255 if shown_level == level else min(255, round(255 * alpha / shown_level)))
        screen.blit(sprite, sprite.get_rect(center=center))

        # Faintness levels nobody has drawn for a second are let go
        for key in [k for k, jobs in self._sigil_turns.items() if not jobs or max(jobs) < tick - 10]:
            del self._sigil_turns[key]

    def close(self):
        self.worker.shutdown(wait=True, cancel_futures=True)

    # ── Loading ────────────────────────────────────────────────────────────────

    def prewarm_jobs(self):
        """Sprites a match needs, built while loading so nothing stutters mid-rally."""
        art = self.art
        ui, brush = art.ui, art.brush
        red, blue = (255, 80, 80), (60, 140, 255)
        white = (255, 255, 255)
        panel = self.ui.PANEL

        jobs = [lambda: art.mist(BASE_W, 340, (190, 90, 90), 3),
                lambda: art.mist(BASE_W, 170, (190, 90, 90), 3),
                lambda: art.side_shade(),
                lambda: art.faint_sigil(420, 44),
                lambda: art.sigil(460),
                lambda: art.sigil(330),
                lambda: art.rail(860),
                lambda: art.rail(BASE_W, flowers=False),
                lambda: art.cord(BASE_H),
                lambda: art.plaque(620, 112),
                lambda: art.plaque(680, 136),
                lambda: art.panel(panel.w, panel.h),
                lambda: art.board(360, 540),
                lambda: art.watermark("往", 300, 26),
                lambda: art.gilded("Red scored!", self.brush(0.085), top=mix(red, white, .6), bottom=red, glow=None),
                lambda: art.gilded("Blue scored!", self.brush(0.085), top=mix(blue, white, .6), bottom=blue, glow=None)]

        for key, zh, label, _ in self.TALISMANS:
            jobs.append(lambda zh=zh, label=label: art.talisman(*self.TALISMAN_SIZE, zh, label=label))
            jobs.append(lambda zh=zh, label=label: art.talisman(*self.TALISMAN_SIZE, zh, label=label, hot=True))

        for digit in "123":
            jobs.append(lambda digit=digit: art.gilded(digit, ui(230), thickness=6))
        for mark in "三二一":
            jobs.append(lambda mark=mark: art.gilded(mark, brush(420), thickness=0, top=(120, 30, 30), bottom=(70, 14, 18)))

        for side, tint in (("left", (150, 34, 22)), ("right", (26, 70, 170))):
            for level in range(4, 7):
                jobs.append(lambda side=side, tint=tint, level=level: art.goal_glow(side, tint, level))

        for size in (32, 40, 48, 64, 88):
            for frame in range(art.FLAP_FRAMES):
                for tint in ("red", "blue"):
                    jobs.append(lambda size=size, frame=frame, tint=tint: art.butterfly(size, frame, 0, tint))

        jobs.append(lambda: art.ball(self.app.settings.gameplay.ball_diameter))
        for kind in POWERUPS.values():
            jobs.append(lambda k=kind: [art.power_icon(size, k.key, k.family) for size in self.ICON_SIZES])
        jobs.append(lambda: art.glow(48, (120, 54, 20)))
        return jobs

    def idle_jobs(self):
        """Every angle of the butterflies that burst out of goals, hits and swaps.  These are
        built a little at a time while the menus are up, so a match never waits on them."""
        art = self.art
        jobs = []
        for size in (64, 40, 48):
            for tint in ("red", "blue"):
                for frame in range(art.FLAP_FRAMES):
                    for turn in range(art.TURN_STEPS):
                        jobs.append(lambda size=size, frame=frame, turn=turn, tint=tint:
                                    art.butterfly(size, frame, turn, tint))

        # Every paddle and ball size the Chaos modes can reach, in the steps draw_paddle uses
        g = self.app.settings.gameplay
        for h in range(g.paddle_height_min, g.paddle_height_max + 1, 4):
            t = (h - g.paddle_height_min) / g.paddle_height_range
            w = int((g.paddle_width_min + t * g.paddle_width_range) / 2) * 2
            for finish in ("red", "blue"):
                jobs.append(lambda w=w, h=h, finish=finish: (art.paddle(w, h, finish), art.paddle_glow(w, h, finish)))
        for d in range(g.ball_diameter_min, g.ball_diameter_max + 1, 2):
            jobs.append(lambda d=d: art.ball(d))

        # Your paddle as Giant Paddle and Shrink Curse leave it, with the power-up auras
        w = max(4, int(g.paddle_width / 2) * 2)
        for k in (1.0, PowerUps.GIANT, PowerUps.SHRINK, PowerUps.GIANT * PowerUps.SHRINK):
            h = max(8, int(min(BASE_H * 0.62, g.paddle_height * k) / 4) * 4)
            for finish in ("red", "blue", "gold", "violet", "jade", "ice"):
                jobs.append(lambda w=w, h=h, finish=finish: art.paddle_glow(w, h, finish))
            for finish in ("red", "blue"):
                jobs.append(lambda w=w, h=h, finish=finish: art.paddle(w, h, finish))
            jobs.append(lambda w=w, h=h: art.get(("ice_coat", w, h), self._ice_coat, w, h))

        jobs.reverse()          # taken from the end, so the goal-burst butterflies come first
        return jobs

    def draw_loading_screen(self, screen, progress):
        screen.fill(theme.INK)
        hall = self.art.gilded("往生堂", self.art.brush(120))
        screen.blit(hall, hall.get_rect(center=(BASE_W // 2, BASE_H // 2 - 70)))

        w, h = 620, 18
        x, y = BASE_W // 2 - w // 2, BASE_H // 2 + 40
        screen.blit(self.art.inset(w, h), (x, y))
        bar = self.art.slider_fill(w - 6, h - 6, theme.EMBER)
        screen.blit(bar, (x + 3, y + 3), (0, 0, int((w - 6) * clamp01(progress)), h - 6))

        self.text(screen, "Preparing the parlor...", self.fnt(0.026, bold=False), theme.GOLD,
                  center=(BASE_W // 2, y + 56))

    # ── Main menu ──────────────────────────────────────────────────────────────

    TALISMAN_SIZE = (196, 520)
    TALISMANS = (("play", "开始", "Play Game", 146),
                 ("stats", "战绩", "Stats", 362),
                 ("settings", "设置", "Settings", 578),
                 ("prompt_quit", "退出", "Quit Game", 794))

    def draw_main_menu(self, state, screen):
        mouse_pos = self.mouse()
        art = self.art
        t = self.app.fx.time
        cx = 470

        screen.blit(art.side_shade(), (0, 0))
        self.draw_sigil(screen, (cx, 214), 460, 95)

        title = art.gilded("Hu Taong!", art.brush(178), thickness=4)
        screen.blit(title, title.get_rect(center=(cx, 170)))

        hall = art.gilded("往生堂", art.brush(46), glow=None, thickness=2)
        rect = hall.get_rect(center=(cx - 150, 308))
        screen.blit(hall, rect)
        self.text(screen, "Wangsheng Funeral Parlor", self.fnt(0.028), theme.GOLD,
                  midleft=(rect.right - 8, 308))

        # A gilded rail with the menu hanging from it on red cords
        rail_y = 372
        rail = art.rail(860)
        screen.blit(rail, rail.get_rect(center=(cx, rail_y)))

        w, h = self.TALISMAN_SIZE
        m = art.TALISMAN_MARGIN

        for i, (key, zh, label, x) in enumerate(self.TALISMANS):
            hit = pygame.Rect(x - w // 2, rail_y + 20, w, h)
            hovered = hit.collidepoint(mouse_pos)
            rise = self.lift(key, hovered)
            top = rail_y + 26 + math.sin(t * 1.1 + i * 1.3) * 5 - rise * 20

            for side in (-1, 1):
                pygame.draw.line(screen, theme.CINNABAR, (x + side * 56, rail_y), (x + side * 56, top + 2), 3)

            screen.blit(art.talisman(w, h, zh, label=label, hot=hovered), (x - w // 2 - m, top - m))
            state.ui_hitboxes[key] = hit
            self.tips.offer(hit, TIPS[key])

            if hovered and random.random() < 12 * self.app.dt:
                edge = random.choice((x - w // 2, x + w // 2))
                self.app.fx.spark(edge, top + random.uniform(0, h), 2, speed=120, life=.8,
                                  arc=(-2.2, -.9), gravity=-120)

        self.text(screen, "Tap Play Game to begin   ·   Back to quit" if ANDROID else "Enter to play   ·   Esc to quit",
                  self.fnt(0.024, bold=False),
                  theme.GOLD, center=(cx, 944))

    # ── Match setup ────────────────────────────────────────────────────────────

    def draw_match_setup_menu(self, state, screen):
        ui = self.ui
        g = self.app.settings.gameplay
        red_keys = self.app.settings.interface.keys_label("p1")
        blue_keys = self.app.settings.interface.keys_label("p2")
        tips = dict(TIPS, side_red=f"Red\nPlay the left paddle.\n~ Keys: {red_keys}",
                    side_blue=f"Blue\nPlay the right paddle.\n~ Keys: {blue_keys}")

        def build(s):
            f, sm = ui.fnt(0.042, s), ui.fnt(0.03, s)
            G = theme.GREEN
            gap = int(BASE_W * 0.02 * s)

            def choice(key, text, selected, on=(G, theme.GREEN_HOVER), enabled=lambda: True):
                def colors():
                    if not enabled():
                        return (theme.DARK_GRAY, theme.DARK_GRAY)    # greyed out, not clickable
                    return on if selected() else (theme.GRAY, theme.GRAY_HOVER)
                return Button(key, text, f, colors, tip=tips.get(key))

            opponent = self.section(ui, s, "Opponent", Stack([
                choice("opponent_ai",     "vs AI",    lambda: g.vs_ai),
                choice("opponent_human",  "vs Human", lambda: not g.vs_ai),
                choice("opponent_online", "Online",   lambda: False, (theme.BLUE, theme.BLUE_HOVER))],
                vertical=False, gap=gap, uniform=True))

            vs_ai = lambda: g.vs_ai
            paddle = self.section(ui, s, "Your Paddle", Stack([
                choice("side_red",  "Red",  lambda: not g.play_as_blue, (theme.RED,  theme.RED_HOVER),  vs_ai),
                choice("side_blue", "Blue", lambda: g.play_as_blue,     (theme.BLUE, theme.BLUE_HOVER), vs_ai)],
                vertical=False, gap=gap, uniform=True))

            def summary():
                if not g.vs_ai:
                    return f"Red: {red_keys}      Blue: {blue_keys}"
                me, ai = ("Blue", "Red") if g.play_as_blue else ("Red", "Blue")
                keys = blue_keys if g.play_as_blue else red_keys
                return f"You: {me} ({keys})      AI: {ai}"
            samples = [f"You: Blue ({blue_keys})      AI: Red", f"You: Red ({red_keys})      AI: Blue",
                       f"Red: {red_keys}      Blue: {blue_keys}"]
            caption = Text(summary, sm, theme.PARCHMENT, samples=samples)

            start = Button("start_match", "Start Match", ui.fnt(0.05, s), (theme.ORANGE, theme.ORANGE_HOVER),
                           tip=TIPS["start_match"])

            names = g.court_options
            court_tip = lambda: self.court_tip(g.court)
            court = self.section(ui, s, "Court",
                                 Cycle("cycle_court", lambda: names[g.court], f, names, tip=court_tip),
                                 Picture(int(384 * s), int(216 * s), lambda screen, rect: self.draw_court_preview(screen, rect, g.court),
                                         tip=court_tip),
                                 Text(lambda: self.court_about(g.court), sm, theme.PARCHMENT,
                                      samples=[self.court_about(i) for i in range(len(names))]))
            left = Stack([opponent, paddle, caption], gap=self.vgap(ui, s, 2))
            return Stack([Grid([[left, court]], gap_x=int(BASE_W * 0.06 * s)), start], gap=self.vgap(ui, s, 2))

        ui.screen_menu(state, screen, build, title="对局 Match Setup", mark="战")

    @staticmethod
    def court_about(index):
        if index >= len(courts.COURTS):
            return "A different court every match."
        return courts.COURTS[index].about

    def court_tip(self, index):
        lines = ["Court", "The stones a match starts with. The ball bounces off them; paddles pass through."]
        for i, name in enumerate(courts.NAMES):
            lines.append(("» " if i == index else "• ") + f"{name}: {self.court_about(i)}")
        return "\n".join(lines)

    def draw_court_preview(self, screen, rect, index):
        """A small map of the court: the centre line, the serve spot and every stone."""
        screen.blit(self.art.inset(rect.w, rect.h), rect)
        inner = rect.inflate(-12, -12)
        k = inner.w / BASE_W
        pygame.draw.line(screen, theme.GOLD_DARK, (inner.centerx, inner.top), (inner.centerx, inner.bottom), 1)
        pygame.draw.rect(screen, (150, 34, 22), (inner.left, inner.top, 3, inner.h))
        pygame.draw.rect(screen, (26, 70, 170), (inner.right - 3, inner.top, 3, inner.h))
        pygame.draw.circle(screen, theme.PARCHMENT, inner.center, 4)
        if index >= len(courts.COURTS):
            self.text(screen, "?", self.brush(0.08), theme.GOLD_BRIGHT, center=inner.center)
            return
        for cx, cy, w, h, speed, style in courts.COURTS[index].pieces:
            r = pygame.Rect(0, 0, max(3, int(w * k)), max(3, int(h * k)))
            r.center = (inner.left + int(cx * k), inner.top + int(cy * k))
            colour = (190, 50, 44) if style == "pillar" else (170, 164, 156)
            pygame.draw.rect(screen, colour, r, border_radius=2)
            if speed:
                for sign in (-1, 1):
                    tip = (r.centerx, r.centery + sign * (r.h // 2 + 12))
                    pygame.draw.polygon(screen, theme.GOLD, [(tip[0] - 5, tip[1] - sign * 6), (tip[0] + 5, tip[1] - sign * 6), tip])
        # the two paddles at home
        for x in (inner.left + int(40 * k), inner.right - int(80 * k)):
            pygame.draw.rect(screen, theme.GOLD, (x, inner.centery - int(100 * k), max(2, int(40 * k)), int(200 * k)))

    # ── Online ─────────────────────────────────────────────────────────────────

    HELP_HOST = ("How to connect",
                 "Send your friend the code. Your two games find each other and open the way through your routers.",
                 "• If Windows asks, allow Hu Taong through the firewall",
                 "• On the same Wi-Fi? The local address works too",
                 "• Still can't connect? Swap who hosts, forward UDP port {port} on your router to this PC, or both "
                 "join a free VPN such as Tailscale or ZeroTier")

    def draw_online_lobby(self, state, screen):
        ui = self.ui
        net = self.app.net
        g = self.app.settings.gameplay

        def field(name, font, width, hint, tip, secret=False):
            shown = (lambda: "•" * len(state.text[name])) if secret else (lambda: state.text[name])
            return TextField(name + "_field", shown, font, width, hint=hint, tip=tip,
                             focused=lambda: state.focus == name)

        def build(s):
            f, sm, ty = ui.fnt(0.034, s), ui.fnt(0.028, s), ui.fnt(0.023, s)
            big = ui.fnt(0.046, s)
            message = Text(lambda: state.message, ty, theme.FLAME,
                           samples=["Found your friend's game, but couldn't get through to it. One of your routers may be "
                                    "blocking it: try the other of you hosting, or see How to connect."])

            if state.mode == "choose":
                def card(key, text, colour, line, tip):
                    return Stack([Button(key, text, big, colour, tip=tip), Text(line, ty)], gap=self.vgap(ui, s, 0.6))
                host = card("host_game", "Host a Game", (theme.GREEN, theme.GREEN_HOVER),
                            "Start a game: share its code, or list it publicly",
                            "Host a Game\nStart a game here.\n• Send a friend its code\n• Or list it, so anyone can find it\n"
                            "• The match uses your Gameplay settings")
                join = card("join_game", "Join with a Code", (theme.BLUE, theme.BLUE_HOVER),
                            "Type the code your friend sent you",
                            "Join with a Code\nType the code your friend sent you.")
                find = card("find_rooms", "Find a Room", (theme.ORANGE, theme.ORANGE_HOVER),
                            "Browse the games people have listed",
                            "Find a Room\nSee the public games anyone with Hu Taong is hosting, and join one.")
                server = Stack([Text(state.server_line, sm, theme.GOLD, align="right",
                                     samples=["Server: your own (hutaong.example.net)"]),
                                Button("change_server", "Change", sm, (theme.WHITE, theme.WHITE_HOVER),
                                       tip="Server\nChoose what online games find each other through: the free public "
                                           "servers, or your own.\n• You and your friend need the same one")],
                               vertical=False, gap=int(BASE_W * 0.015 * s))
                return Stack([Grid([[host, join, find]], gap_x=int(BASE_W * 0.04 * s)), message, server,
                              Text("Either player can pause, and the match waits while either of you is in a menu.", ty,
                                   theme.PARCHMENT)],
                             gap=self.vgap(ui, s, 2.0))

            if state.mode == "server":
                online = self.app.settings.online
                chosen = lambda own: (lambda: (theme.GREEN, theme.GREEN_HOVER) if online.own_server == own
                                      else (theme.GRAY, theme.GRAY_HOVER))
                choice = Stack([
                    Button("server_public", "Free Public Servers", f, chosen(False),
                           tip="Free Public Servers\nFree message servers anyone can use (EMQX and HiveMQ).\n"
                               "• Nothing to set up\n~ They promise nothing: if they're down, use your own"),
                    Button("server_own", "Your Own Server", f, chosen(True),
                           tip="Your Own Server\nA server you or a friend runs (see SERVER.md).\n"
                               "• Steadier than the free ones\n~ If it's down, switch back to the free ones here")],
                    vertical=False, gap=int(BASE_W * 0.03 * s))
                items = [Label("Server", ui.fnt(0.034, s)),
                         Text("Online games find each other through a server. You and your friend need the same one.",
                              ty, theme.PARCHMENT),
                         choice]
                if online.own_server:
                    items += [
                        Stack([Text("Address", sm, theme.GOLD),
                               field("server_address", sm, int(BASE_W * 0.3 * s), "example.com or 203.0.113.7:1883",
                                     "Address\nYour server's address, with its port if it isn't 1883.\n~ Ctrl+V pastes")],
                              vertical=False, gap=int(BASE_W * 0.012 * s)),
                        Stack([Text("Login", sm, theme.GOLD),
                               field("server_user", sm, int(BASE_W * 0.14 * s), "Username, if asked",
                                     "Username\nOnly if the server asks for a login.\n~ Tab moves on"),
                               field("server_password", sm, int(BASE_W * 0.14 * s), "Password, if asked",
                                     "Password\nOnly if the server asks for a login.\n• Kept in your save file", secret=True)],
                              vertical=False, gap=int(BASE_W * 0.012 * s)),
                        Stack([Button("server_test", "Test", sm, (theme.BLUE, theme.BLUE_HOVER),
                                      tip="Test\nTry connecting to the server now.\n~ Enter"),
                               Text(lambda: state.server_check, ty, theme.FLAME,
                                    samples=["Couldn't reach it (No connection could be made because the target machine refused it)."])],
                              vertical=False, gap=int(BASE_W * 0.015 * s))]
                items += [Button("server_done", "Done", f, (theme.ORANGE, theme.ORANGE_HOVER),
                                 tip="Done\nBack to the online menu, with this server."),
                          Text("If your server is ever down, switch back to Free Public Servers here (both of you).",
                               ty, theme.PARCHMENT)]
                return Stack(items, gap=self.vgap(ui, s, 0.9))

            if state.mode == "host":
                def status():
                    if not net:
                        return ""
                    if net.connected():
                        ping = f"  (ping {round(net.ping * 1000)} ms)" if net.ping is not None else ""
                        return "Your friend is here!" + ping
                    return net.reach() or "Waiting for someone to join..."

                def code():
                    if not net:
                        return ""
                    return net.code() or f"{net.lan}:{net.port}"

                def where():
                    if not net:
                        return ""
                    internet = net.internet_address()
                    lan = f"Same Wi-Fi: {net.lan}:{net.port}"
                    return f"Internet: {internet}      {lan}" if internet else lan

                ready = lambda: (theme.ORANGE, theme.ORANGE_HOVER) if net and net.connected() else (theme.DARK_GRAY, theme.DARK_GRAY)
                names = g.court_options
                red = lambda: (theme.RED, theme.RED_HOVER) if not g.online_host_blue else (theme.GRAY, theme.GRAY_HOVER)
                blue = lambda: (theme.BLUE, theme.BLUE_HOVER) if g.online_host_blue else (theme.GRAY, theme.GRAY_HOVER)
                choices = Stack([
                    Text("Court", sm, theme.GOLD),
                    Cycle("cycle_court", lambda: names[g.court], sm, names, tip=lambda: self.court_tip(g.court)),
                    Space(int(BASE_W * 0.02 * s)),
                    Text("You play", sm, theme.GOLD),
                    Button("host_red", "Red", sm, red, tip="Red\nYou play the left paddle, your friend Blue."),
                    Button("host_blue", "Blue", sm, blue, tip="Blue\nYou play the right paddle, your friend Red.")],
                    vertical=False, gap=int(BASE_W * 0.01 * s))
                public = Toggle("toggle_public", lambda: "Public Room: ON" if net and net.ad else "Public Room: OFF", sm,
                                lambda: bool(net and net.ad), ["Public Room: ON", "Public Room: OFF"],
                                tip="Public Room\nList this game so anyone with Hu Taong can find it in Find a Room.\n"
                                    "• Its name, rules and internet address are shown on the list\n"
                                    "~ Add a password to choose who gets in")
                room = Stack([public,
                              field("room_name", sm, int(BASE_W * 0.17 * s), "Room name",
                                    "Room Name\nWhat the room is called on the public list."),
                              field("password", sm, int(BASE_W * 0.13 * s), "Password (optional)",
                                    "Password\nAnyone joining, by the list or by code, has to type it.\n~ Leave it empty for none",
                                    secret=True)],
                             vertical=False, gap=int(BASE_W * 0.012 * s))
                head, *lines = self.HELP_HOST
                return Stack([
                    Stack([Text(code, ui.fnt(0.055, s), theme.GOLD_BRIGHT, samples=["255.255.255.255:65535"]),
                           Button("copy_code", "Copy", sm, (theme.BLUE, theme.BLUE_HOVER),
                                  tip="Copy\nPut the code on the clipboard, to paste into a message.")],
                          vertical=False, gap=int(BASE_W * 0.02 * s)),
                    Text(where, ty, theme.PARCHMENT, samples=["Internet: 255.255.255.255:65535      Same Wi-Fi: 255.255.255.255:65535"]),
                    Text(status, ty, theme.FLAME, samples=["Couldn't reach the servers codes go through (the network may block them): use an address below",
                                                           "Your friend is here!  (ping 999 ms)"]),
                    room,
                    Text(lambda: net.listing() if net else "", ty, theme.GOLD,
                         samples=["Can't list it: your router didn't open the port, so nobody outside could join"]),
                    choices,
                    Text(lambda: net.settings_summary() if net else "", ty, theme.GOLD,
                         samples=["First to 21  -  Court: Narrow Pass  -  Power-ups off  -  Chaos Mode +"]),
                    Stack([Button("online_settings", "Gameplay Settings", sm, (theme.WHITE, theme.WHITE_HOVER),
                                  tip="Gameplay Settings\nChoose the rules and power-ups for this match."),
                           Button("start_online", "Start Match", f, ready,
                                  tip="Start Match\nStart playing once your friend has joined.")],
                          vertical=False, gap=int(BASE_W * 0.03 * s)),
                    Stack([Text(head, ty, theme.GOLD), *[Text(l.format(port=net.port if net else netcode.PORT), ty,
                                                               theme.PARCHMENT, align="left") for l in lines]],
                          gap=int(4 * s), align="start")],
                    gap=self.vgap(ui, s, 0.75))

            def status():
                if not net or net.role != "guest":
                    return ""
                if net.status == "connecting":
                    if net.knock and not net.knock.host:
                        return "Looking up the code..."
                    return "Knocking on the host's door..."
                if net.status == "waiting":
                    return "In! Waiting for the host to start the match"
                return ""

            joined = Text(lambda: (net.summary + ("  -  You play " + ("Red" if net.side == 1 else "Blue")))
                          if net and net.role == "guest" and net.summary else "", ty, theme.GOLD,
                          samples=["First to 21  -  Court: Narrow Pass  -  Power-ups off  -  Chaos Mode +  -  You play Blue"])
            waiting = Text(status, f, theme.FLAME, samples=["In! Waiting for the host to start the match"])

            if state.mode == "browse":
                rooms_list = state.room_list
                def look():
                    if rooms_list is None:
                        return ""
                    if rooms_list.status == "connecting":
                        return "Looking for rooms..."
                    if rooms_list.status == "refused":
                        return "Your server turned the login away: check its username and password under Server."
                    if rooms_list.status == "failed":
                        return f"Couldn't reach {rooms.where()} for the room list. Try the other server under Server."
                    return "" if state.shown_rooms else "No public rooms right now. Host one, and it'll show here."
                rows = []
                for i, r in enumerate(state.shown_rooms):
                    other = r.get("v") != netcode.PROTOCOL
                    full = r.get("players", 1) >= 2 or r.get("playing") or other
                    word = ("Other version" if other else "Full" if r.get("players", 1) >= 2 else
                            "Playing" if r.get("playing") else "Join")
                    tip = {"Other version": "Other version\nThis room is on a different version of Hu Taong.",
                           "Full": "Full\nThis room already has two players.",
                           "Playing": "Playing\nThis room is in the middle of a match.",
                           "Join": "Join\nJoin this room." + ("\n~ It asks for a password" if r.get("locked") else "")}[word]
                    lock = "  (password)" if r.get("locked") else ""
                    rows.append([Text(r.get("name", "A room") + lock, sm, theme.GOLD_BRIGHT,
                                      samples=["W" * 28 + "  (password)"], align="left"),
                                 Text(r.get("rules", ""), ty, theme.PARCHMENT,
                                      samples=["First to 21  -  Court: Narrow Pass  -  Power-ups off  -  Chaos Mode +"],
                                      align="left"),
                                 Button(f"join_room_{i}", word, sm,
                                        (theme.DARK_GRAY, theme.DARK_GRAY) if full else (theme.GREEN, theme.GREEN_HOVER),
                                        tip=tip)])
                items = [Label("Public Rooms", ui.fnt(0.034, s)),
                         Text(look, sm, theme.PARCHMENT,
                              samples=["Couldn't reach the room list. The network may block it; codes still work."])]
                if rows:
                    items.append(Grid(rows, gap_x=int(BASE_W * 0.02 * s), gap_y=self.vgap(ui, s, 0.5)))
                if state.picked is not None:
                    items.append(Stack([Text(f"Password for {state.picked.get('name', 'the room')}", sm, theme.GOLD),
                                        field("room_password", sm, int(BASE_W * 0.15 * s), "Password",
                                              "Password\nThe password the host set for this room.", secret=True),
                                        Button("join_picked", "Join", sm, (theme.GREEN, theme.GREEN_HOVER),
                                               tip="Join\nJoin with this password.\n~ Enter")],
                                       vertical=False, gap=int(BASE_W * 0.012 * s)))
                items += [waiting, joined, message,
                          Text(lambda: f"Rooms are found through {rooms.where()}; joining goes straight to the host.",
                               ty, theme.OFF_TEXT)]
                return Stack(items, gap=self.vgap(ui, s, 0.8))

            return Stack([
                Label("Your Friend's Code", ui.fnt(0.034, s)),
                field("code", ui.fnt(0.05, s), int(BASE_W * 0.32 * s), "K7Q2-9FHD",
                      "Code\nType the code your friend sent, or their address.\n~ Ctrl+V pastes"),
                field("join_password", sm, int(BASE_W * 0.2 * s), "Password, if it has one",
                      "Password\nOnly needed if your friend set one for their game.\n~ Tab switches boxes",
                      secret=True),
                Stack([Button("paste_code", "Paste", sm, (theme.WHITE, theme.WHITE_HOVER),
                              tip="Paste\nPaste the code from the clipboard.\n~ Ctrl+V"),
                       Button("join_now", "Join", f, (theme.GREEN, theme.GREEN_HOVER),
                              tip="Join\nConnect to your friend's game.\n~ Enter")],
                      vertical=False, gap=int(BASE_W * 0.03 * s)),
                waiting, joined, message,
                Text("Can't connect? Swap who hosts, or see How to connect on the Host screen.",
                     ty, theme.PARCHMENT)],
                gap=self.vgap(ui, s, 1.0))

        ui.screen_menu(state, screen, build, title="联机 Online", mark="联")

    def draw_online_waiting(self, screen, text):
        words = self.art.gilded(text, self.brush(0.06), glow=None)
        screen.blit(words, words.get_rect(center=(BASE_W // 2, BASE_H // 2)))

    def draw_ping(self, screen, ping):
        """Online: how long a message takes to get to the host and back."""
        if ping is None:
            return
        ms = round(ping * 1000)
        colour = theme.GREEN_HOVER if ms < 80 else theme.FLAME if ms < 160 else theme.CRIMSON_BRIGHT
        self.text(screen, f"Ping {ms} ms", self.fnt(0.02), colour, topleft=(18, 16))

    # ── Settings menu ──────────────────────────────────────────────────────────

    def draw_card(self, state, screen, mouse_pos, key, x, mark, label, finish):
        w, h = 360, 540
        hit = pygame.Rect(x, 240, w, h)
        hovered = hit.collidepoint(mouse_pos)
        rise = self.lift(key, hovered)
        y = hit.y - rise * 16
        m = self.art.PANEL_MARGIN

        if rise > .02:
            # in eight steps: every new shade is a big sprite to build
            halo = self.art.glow(330, scaled((110, 40, 18), max(1, round(rise * 8)) / 8))
            screen.blit(halo, halo.get_rect(center=(x + w // 2, y + h // 2)), special_flags=ADD)

        screen.blits([(piece, (x - m + dx, y - m + dy)) for piece, (dx, dy) in self.art.board(w, h)], False)
        self.draw_sigil(screen, (x + w // 2, y + 230), 330, 80 + int(rise * 90))

        top = theme.GOLD_BRIGHT if not hovered else (255, 240, 190)
        sprite = self.art.gilded(mark, self.art.brush(220), top=top, glow=theme.LACQUER[finish][0])
        screen.blit(sprite, sprite.get_rect(center=(x + w // 2, y + 226)))

        rect = pygame.Rect(0, 0, 300, 76)
        rect.center = (x + w // 2, y + h - 104)
        self.draw_lacquer(screen, mouse_pos if hovered else (-1, -1), rect, label, self.fnt(0.042), finish)
        state.ui_hitboxes[key] = hit
        self.tips.offer(hit, TIPS[key])

    def draw_settings_menu(self, state, screen):
        mouse_pos = self.mouse()
        ui = self.ui
        self.draw_plaque(screen, "设置 Settings", ui.PANEL.top)

        cards = (("display", "画", "Display", "amber"), ("gameplay", "玩", "Gameplay", "jade"),
                 ("audio", "音", "Audio", "azure"), ("interface", "界", "Interface", "crimson"))
        left = (BASE_W - (4 * 360 + 3 * 46)) // 2
        for i, (key, mark, label, finish) in enumerate(cards):
            self.draw_card(state, screen, mouse_pos, key, left + i * 406, mark, label, finish)

        back_rect = self.draw_button(screen, mouse_pos, self.fnt(0.04), "Back",
                                     BASE_W // 2, ui.FOOTER_Y, theme.RED, width=280)
        font = self.fnt(0.034)
        text = "Reset All Settings"
        w = font.size(text)[0] + 2 * self._gx
        reset_rect = self.draw_button(screen, mouse_pos, font, text, ui.PANEL.right - w // 2,
                                      ui.FOOTER_Y, theme.WHITE, width=w)
        self.tips.offer(reset_rect, TIPS["reset_all"])

        state.ui_hitboxes.update(reset_all=reset_rect, back=back_rect)

    # ── Gameplay settings ──────────────────────────────────────────────────────

    def draw_gameplay_settings_menu(self, state, screen):
        ui = self.ui
        g = self.app.settings.gameplay

        def build(s):
            f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.023, s)
            G = theme.GREEN
            track_w = int(BASE_W * 0.17 * s)

            label_sample = f"{g.paddle_height_max} x {g.paddle_width_max}"  # widest label; shared so tracks line up

            def slider(key, reset, value, lo, rng, label, sample=None):
                return Slider(key, lambda: (value() - lo) / rng, theme.EMBER, sm, label, label_sample,
                              reset_key=reset, reset_font=ty, track_w=track_w, tip=TIPS[key])

            win_texts = ["Endless Mode" if v == "Endless Mode" else f"Score {v} to win"
                         for v in g.winning_scores]
            ai_col = lambda: (theme.GREEN if g.ai_difficulty == 0 else
                              theme.PARCHMENT if g.ai_difficulty < len(g.ai_difficulties) - 1 else theme.CRIMSON_BRIGHT)
            win_col = lambda: theme.FLAME if g.winning_scores[g.winning_score_index] == "Endless Mode" else theme.PARCHMENT

            levels = [f"Level: {d}" for d in g.ai_difficulties]
            styles = [f"Style: {d}" for d in g.ai_styles]
            level_notes = ["slow to react, often misreads the ball", "reacts late and rarely aims",
                           "a fair match", "quick, aims its returns", "reads everything; rarely misses"]
            ai_tip = lambda: options_tip("AI Level", "How quickly the AI reacts and how well it reads the ball.",
                                         list(zip(g.ai_difficulties, level_notes)), g.ai_difficulty)
            style_tip = lambda: options_tip("AI Style", "What the AI tries to do.",
                                            [(name, STYLE_TIPS[name]) for name in g.ai_styles], g.ai_style)
            ai = self.section(ui, s, "AI",
                              Cycle("cycle_ai", lambda: levels[g.ai_difficulty], f, levels, ai_col, tip=ai_tip),
                              Cycle("cycle_ai_style", lambda: styles[g.ai_style], f, styles, tip=style_tip),
                              self.toggle(sm, "toggle_adaptive_ai", "Adaptive AI", lambda: g.adaptive_ai))
            win = self.section(ui, s, "Match Rules",
                               Cycle("cycle_win_score", lambda: win_texts[g.winning_score_index],
                                     f, win_texts, win_col,
                                     tip="Points to Win\nThe score that wins the match.\n• Endless Mode never ends"),
                               self.toggle(sm, "toggle_win_by_two", "Win by Two", lambda: g.win_by_two),
                               self.toggle(sm, "toggle_middle_wall", "Middle Wall", lambda: g.middle_wall))

            ball_speed = self.section(ui, s, "Ball Speed", slider(
                "ball_speed_slider", "reset_ball_speed", lambda: g.ball_speed,
                g.ball_speed_min, g.ball_speed_range,
                lambda: str(int(g.ball_speed))))
            paddle_speed = self.section(ui, s, "Paddle Speed", slider(
                "paddle_speed_slider", "reset_paddle_speed", lambda: g.paddle_speed,
                g.paddle_speed_min, g.paddle_speed_range,
                lambda: str(int(g.paddle_speed))))
            ball_size = self.section(ui, s, "Ball Diameter", slider(
                "ball_diameter_slider", "reset_ball_diameter", lambda: g.ball_diameter,
                g.ball_diameter_min, g.ball_diameter_range,
                lambda: str(int(g.ball_diameter))))
            paddle_size = self.section(ui, s, "Paddle Size", slider(
                "paddle_size_slider", "reset_paddle_size", lambda: g.paddle_height,
                g.paddle_height_min, g.paddle_height_range,
                lambda: f"{int(g.paddle_height)} x {int(g.paddle_width)}"))
            pace = self.section(ui, s, "Game Pace", slider(
                "pace_slider", "reset_pace", lambda: g.pace,
                g.pace_min, g.pace_range,
                lambda: f"{g.pace:.2f}x"))

            rand = Button("randomise_all", "Randomise Ball & Paddles", sm, (G, theme.GREEN_HOVER), tip=TIPS["randomise_all"])
            chaos_tip = lambda: options_tip(
                "Chaos Mode", "Shakes up the ball's and paddles' sizes and speeds.",
                [("Off", ""), ("Chaos Mode", "new random sizes and speeds every point"),
                 ("Chaos Mode +", "they keep drifting during play, separately for each paddle and the ball")],
                g.chaos_mode, "Click to step through")
            switch_tip = lambda: options_tip(
                "Chaos Switch", "Swaps things round mid-match.",
                [("Off", ""), ("Chaos Switch", "after every point you take over the other paddle, score and all"),
                 ("Chaos Switch +", "at random moments, after a warning, the paddles swap places and every ball slows to half speed; keys, scores and goals stay yours"),
                 ("Chaos Switch & +", "both")],
                g.chaos_switch, "Chaos Switch + takes the Middle Wall down")
            chaos = CycleToggle("cycle_chaos_mode", ["Chaos Mode: Off", "Chaos Mode", "Chaos Mode +"], sm,
                                lambda: g.chaos_mode, "关乱狂", tip=chaos_tip)
            switch = CycleToggle("cycle_chaos_switch",
                                 ["Chaos Switch: Off", "Chaos Switch", "Chaos Switch +", "Chaos Switch & +"], sm,
                                 lambda: g.chaos_switch, "关换狂双", tip=switch_tip)
            powers = Button("open_powerups", "Power-Ups", sm, (theme.ORANGE, theme.ORANGE_HOVER),
                            tip=TIPS["open_powerups"])
            curve = self.toggle(sm, "toggle_curveball", "Curveball", lambda: g.curveball)
            night = self.toggle(sm, "toggle_lantern_night", "Lantern Night", lambda: g.lantern_night)
            extras = self.section(ui, s, "Chaos & Power-Ups",
                                  Stack([chaos, switch, curve, night, powers], vertical=False, gap=int(BASE_W * 0.012 * s)))

            return Grid([[ai, win],
                         [ball_speed, paddle_speed],
                         [ball_size, paddle_size],
                         [pace, Stack([rand], gap=0)],
                         [extras]],
                        gap_x=int(BASE_W * 0.06 * s), gap_y=self.vgap(ui, s, 1.6))

        ui.screen_menu(state, screen, build, title="玩法 Gameplay", mark="玩", reset="Reset to Default")

    # ── Power-ups ──────────────────────────────────────────────────────────────

    def draw_powerups_menu(self, state, screen):
        """Every power-up as a tile (its picture and its switch), four to a row, and a panel below
        that describes whichever one the mouse is on, in full."""
        ui = self.ui
        g = self.app.settings.gameplay

        def build(s):
            sm, ty = ui.fnt(0.025, s), ui.fnt(0.023, s)
            rates = [f"Spawn: {r}" for r in g.powerup_rate_options]
            head = Stack([self.toggle(sm, "toggle_powerups", "Power-Ups", lambda: g.powerups),
                          Cycle("cycle_powerup_rate", lambda: rates[g.powerup_rate], sm, rates,
                                tip=lambda: options_tip("Spawn Rate", "How often a new talisman appears.",
                                                        [("Rare", "every 14-22 s"), ("Normal", "every 8-14 s"),
                                                         ("Frequent", "every 4-8 s"),
                                                         ("Chaotic", "every 1.5-3 s, up to three at once")],
                                                        g.powerup_rate)),
                          Button("all_pu_on", "All On", sm, (theme.GREEN, theme.GREEN_HOVER),
                                 tip="All On\nSwitch every power-up on."),
                          Button("all_pu_off", "All Off", sm, (theme.WHITE, theme.WHITE_HOVER),
                                 tip="All Off\nSwitch every power-up off (Power-Ups stays on, so you can pick a few).")],
                         vertical=False, gap=int(BASE_W * 0.02 * s))
            legend = Text([("Round: ", FAMILY_COLOURS["Boon"]), ("Boon, helps you      ", theme.PARCHMENT),
                           ("Diamond: ", FAMILY_COLOURS["Curse"]), ("Curse, hinders your opponent      ", theme.PARCHMENT),
                           ("Hexagon: ", FAMILY_COLOURS["Wild"]), ("Wild, shakes up the court", theme.PARCHMENT)], ty)

            names = [f"{kind.name}: OFF" for kind in POWERUP_KINDS]
            tiles = []
            for kind in POWERUP_KINDS:
                name = "pu_" + kind.key
                switch = CycleToggle("toggle_" + name, [f"{kind.name}: OFF", f"{kind.name}: ON"], sm,
                                     lambda name=name: int(getattr(g, name)), "关" + kind.glyph)
                switch.samples = names
                tile = Stack([Icon(kind.key, kind.family, int(BASE_H * 0.058 * s)), switch],
                             vertical=False, gap=int(BASE_W * 0.006 * s))
                tiles.append(_PowerTile(tile, kind.key))
            across = 4
            rows = [tiles[i:i + across] for i in range(0, len(tiles), across)]
            rows[-1] += [Space() for _ in range(across - len(rows[-1]))]
            grid = Grid(rows, gap_x=int(BASE_W * 0.012 * s), gap_y=self.vgap(ui, s, 0.35))
            grid.measure()
            details = _PowerDetails(max(grid.w, int(BASE_W * 0.6)), ui.fnt(0.028, s), ui.fnt(0.022, s), s)
            return Stack([head, legend, grid, details], gap=self.vgap(ui, s, 0.6))

        ui.screen_menu(state, screen, build, title="法宝 Power-Ups", mark="宝", reset="Reset to Default")

    # ── Display settings ───────────────────────────────────────────────────────

    def draw_display_settings_menu(self, state, screen):
        ui = self.ui
        d = self.app.settings.display
        app = self.app

        def build(s):
            f, sm = ui.fnt(0.032, s), ui.fnt(0.028, s)
            O = theme.ORANGE

            res_texts = [f"{w} x {h}" for (w, h) in app.resolutions]
            mode_texts = [m.capitalize() for m in app.display_modes]

            resolution = self.section(
                ui, s, "Resolution",
                Cycle("cycle_res", lambda: res_texts[state.res_index], f, res_texts, tip=TIPS["cycle_res"]),
                Cycle("cycle_mode", lambda: mode_texts[state.display_mode_index], f, mode_texts,
                      tip=TIPS["cycle_mode"]),
                Button("apply", "Apply", sm, (O, theme.ORANGE_HOVER), tip=TIPS["apply"]))

            max_fps = self.section(
                ui, s, "Maximum FPS",
                Cycle("cycle_max_fps", lambda: str(d.max_fps_options[d.max_fps]), f,
                      [str(o) for o in d.max_fps_options], tip=TIPS["cycle_max_fps"]),
                self.toggle(sm, "toggle_show_fps", "Show FPS", lambda: d.show_fps))

            rotate_texts = [f"Change: {o}" for o in d.rotate_options]
            parallax_texts = [f"Parallax: {o}" for o in d.parallax_options]

            background = self.section(
                ui, s, "Background",
                Slot("background_thumb", int(256 * s), int(144 * s), tip=TIPS["background_thumb"]),
                self.toggle(sm, "toggle_rotate_bg", "Rotate", lambda: d.rotate_backgrounds),
                Cycle("cycle_rotate_every", lambda: rotate_texts[d.rotate_every], sm, rotate_texts,
                      tip=TIPS["cycle_rotate_every"]))

            court_texts = [f"Court Dim: {o}" for o in d.court_dim_options]
            dim = self.section(
                ui, s, "Dim Overlay",
                Slider("dim_slider", lambda: d.dim, theme.EMBER, sm, lambda: f"{int(100 * d.dim)}%", "100%",
                       track_w=int(BASE_W * 0.17 * s), tip=TIPS["dim_slider"]),
                Cycle("cycle_court_dim", lambda: court_texts[d.court_dim], sm, court_texts,
                      tip=lambda: options_tip("Court Dim", "Darkens the picture behind a match, so the ball and paddles stand out.",
                                              [("Off", ""), ("Light", ""), ("Medium", ""), ("Strong", "")], d.court_dim,
                                              "Menus keep their own Dim Overlay")),
                Cycle("cycle_parallax", lambda: parallax_texts[d.parallax], sm, parallax_texts,
                      tip=TIPS["cycle_parallax"]))

            if ANDROID:                        # a phone's screen has one size, and is always full
                return Grid([[background, dim], [max_fps]],
                            gap_x=int(BASE_W * 0.08 * s), gap_y=self.vgap(ui, s, 2.2))
            return Grid([[resolution, max_fps],
                         [background, dim]],
                        gap_x=int(BASE_W * 0.08 * s), gap_y=self.vgap(ui, s, 2.2))

        ui.screen_menu(state, screen, build, title="画面 Display", mark="画", reset="Reset to Default")

    # ── Background picker ──────────────────────────────────────────────────────

    def draw_background_selection(self, state, screen):
        mouse_pos = self.mouse()
        self.draw_frame(screen, "背景 Backgrounds", "景", pygame.Rect(54, 130, 1812, 854))

        screen.set_clip(state.view)
        for button in state.buttons:
            if button.rect.colliderect(state.view):
                button.draw(screen)
        screen.set_clip(None)

        # -------- Scrollbar --------
        if state.max_scroll > 0:
            handle = state.scrollbar_handle()
            hovered = state.dragging_scrollbar or state.track.collidepoint(mouse_pos)
            screen.blit(self.art.inset(state.track.w, state.track.h), state.track)
            pygame.draw.rect(screen, theme.GOLD_BRIGHT if hovered else theme.GOLD, handle.inflate(-6, -6), border_radius=6)
            state.ui_hitboxes["scrollbar"] = state.track

        state.ui_hitboxes["back"] = self.draw_button(screen, mouse_pos, self.fnt(0.036), "Back",
                                                     BASE_W // 2, 1036, theme.RED, width=260)

    # ── Audio settings ─────────────────────────────────────────────────────────

    def draw_audio_settings_menu(self, state, screen):
        ui = self.ui
        sound = self.app.sound_manager
        audio = self.app.settings.audio

        def build(s):
            f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.023, s)
            B = theme.BLUE
            track_w = int(BASE_W * 0.16 * s)

            def volume(header, key, value):
                return self.section(ui, s, header, Slider(
                    key + "_slider", value, theme.EMBER, sm, lambda: f"{int(round(100 * value()))}%", "100%",
                    reset_key="reset_" + key, reset_font=ty, track_w=track_w, tip=TIPS[key + "_slider"]))

            mood_notes = {"menu":    "Relaxed music for the menus",
                          "game":    "Upbeat music for matches",
                          "victory": "Triumphant music",
                          "defeat":  "Downbeat music"}

            volumes = Stack([
                volume("Master Volume", "master_volume", lambda: sound.master_volume),
                volume("Music Volume",  "music_volume",  lambda: sound.music_volume),
                volume("SFX Volume",    "sfx_volume",    lambda: sound.sfx_volume),
                Stack([self.toggle(sm, "toggle_paddle_sounds", "Paddle Sounds", lambda: sound.paddle_hit_sound),
                       self.toggle(sm, "toggle_score_sounds",  "Score Sound",   lambda: sound.score_sound),
                       self.toggle(sm, "toggle_menu_sounds",   "Menu Sounds",   lambda: audio.menu_sounds)],
                      vertical=False, gap=int(BASE_W * 0.01 * s))],
                gap=self.vgap(ui, s, 1.4))

            fades = [f"Track Fade: {o}" for o in audio.fade_options]
            ambience = [f"Ambience: {o}" for o in audio.ambience_options]

            jukebox = self.section(
                ui, s, "Jukebox",
                *self.jukebox_controls(state, f, sm, track_w),
                Text(lambda: mood_notes[sound.mood], ty, theme.GOLD, samples=list(mood_notes.values())),
                self.toggle(sm, "toggle_even_volume", "Even Out Volume", lambda: audio.even_volume),
                Cycle("cycle_fade", lambda: fades[audio.fade], sm, fades,
                      tip=lambda: options_tip("Track Fade", "How long one track takes to fade into the next.",
                                              [("Quick", "0.4 s"), ("Smooth", "1 s"), ("Slow", "2.5 s")], audio.fade)),
                Cycle("cycle_ambience", lambda: ambience[audio.ambience], sm, ambience,
                      tip=lambda: options_tip("Ambience", "Crackling spirit fire and crickets under the music.",
                                              [("Off", ""), ("Menus", "in the menus only"),
                                               ("Everywhere", "in matches too")], audio.ambience)))

            return Grid([[volumes, jukebox]], gap_x=int(BASE_W * 0.04 * s))

        ui.screen_menu(state, screen, build, title="音频 Audio", mark="音", reset="Reset to Default")

    def jukebox_controls(self, state, font, small, track_w):
        """The track's arrows (its name opens the list) and the progress bar with play/pause:
        shared by the Audio menu and the pause screen."""
        sound, audio = self.app.sound_manager, self.app.settings.audio
        return (Cycle("cycle_music", lambda: audio.track_name(sound.now_playing), font,
                      [audio.track_name(t) for t in audio.all_tracks], tip=TIPS["cycle_music"],
                      pick="cycle_music_value"),
                TrackBar(small, sound.music_position, sound.music_length, lambda: sound.music_paused,
                         lambda: state.seek_drag, track_w, tip=TIPS["music_seek"],
                         mode=lambda: audio.play_mode,
                         mode_tip=lambda: options_tip("When a Track Ends", "Click to change what plays next.",
                                                      [("In order", "the next track in the list"),
                                                       ("Shuffle", "a random track"),
                                                       ("Loop", "the same track again")], audio.play_mode)))

    TRACK_ROWS = 9      # tracks shown at once in the jukebox list; the rest scroll

    def track_list_rect(self, state):
        """Where the jukebox's track list opens: under the track name, or above it if there's no room."""
        audio, sound = self.app.settings.audio, self.app.sound_manager
        anchor = state.ui_hitboxes.get("cycle_music_value")
        if anchor is None:
            return None, 0
        font = self.fnt(0.026, bold=False)
        row_h = font.get_linesize() + 14
        rows = min(self.TRACK_ROWS, len(sound.pool))
        w = max(anchor.w, max(font.size(audio.track_name(t))[0] for t in sound.pool) + 110)
        rect = pygame.Rect(0, 0, w, rows * row_h + 16)
        rect.centerx = anchor.centerx
        rect.top = anchor.bottom + 6
        if rect.bottom > BASE_H - 20:
            rect.bottom = anchor.top - 6
        rect.clamp_ip(pygame.Rect(20, 20, BASE_W - 40, BASE_H - 40))
        return rect, row_h

    def draw_track_list(self, state, screen):
        """Every track for this moment, the one playing marked with a blossom."""
        audio, sound = self.app.settings.audio, self.app.sound_manager
        rect, row_h = self.track_list_rect(state)
        if rect is None:
            return
        pool = sound.pool
        mouse = self.mouse()
        font = self.fnt(0.026, bold=False)
        bold = self.fnt(0.026)

        shadow = blank(rect.w, rect.h)
        shadow.fill((0, 0, 0, 120))
        screen.blit(shadow, rect.move(6, 8))
        pygame.draw.rect(screen, mix(theme.INK, theme.LACQUER_BOTTOM, .5), rect, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD_DARK, rect, 2, border_radius=6)
        state.ui_hitboxes["track_list"] = rect          # clicks on the list's own padding go nowhere

        first = state.track_scroll
        scrolls = len(pool) > self.TRACK_ROWS
        text_right = rect.right - (26 if scrolls else 12)
        for row, index in enumerate(range(first, min(len(pool), first + self.TRACK_ROWS))):
            track = pool[index]
            r = pygame.Rect(rect.x + 8, rect.y + 8 + row * row_h, text_right - rect.x - 8, row_h)
            playing = track == sound.now_playing
            hot = r.collidepoint(mouse)
            if hot:
                glow = blank(r.w, r.h)
                glow.fill((*theme.EMBER, 70))
                screen.blit(glow, r)
            if playing:
                flower = self.art.blossom(22)
                screen.blit(flower, flower.get_rect(midleft=(r.x + 10, r.centery)))
            color = theme.GOLD_BRIGHT if playing or hot else theme.PARCHMENT
            self.text(screen, audio.track_name(track), bold if playing else font, color,
                      midleft=(r.x + 44, r.centery))
            state.ui_hitboxes[f"track_{index}"] = r

        if scrolls:
            track_rect = pygame.Rect(rect.right - 18, rect.y + 10, 8, rect.h - 20)
            pygame.draw.rect(screen, theme.INK, track_rect, border_radius=4)
            h = max(30, track_rect.h * self.TRACK_ROWS // len(pool))
            y = track_rect.y + (track_rect.h - h) * first // max(1, len(pool) - self.TRACK_ROWS)
            pygame.draw.rect(screen, theme.GOLD, (track_rect.x, y, track_rect.w, h), border_radius=4)

        # The controls underneath shouldn't explain themselves through the list
        if rect.collidepoint(mouse):
            self.tips.offered = None

    # ── Stats ──────────────────────────────────────────────────────────────────

    def draw_stats_menu(self, state, screen):
        ui = self.ui
        st = self.app.stats

        def build(s):
            f, sm = ui.fnt(0.033, s), ui.fnt(0.03, s)
            rows = [("Matches Played",      lambda: str(st.matches)),
                    ("Wins vs AI",          lambda: str(st.wins_vs_ai)),
                    ("Losses vs AI",        lambda: str(st.losses_vs_ai)),
                    ("Win Rate vs AI",      lambda: f"{st.win_rate}%"),
                    ("Win Streak",          lambda: f"{st.win_streak}  (best {st.best_win_streak})"),
                    ("2-Player Wins",       lambda: f"Red {st.wins_red}  -  {st.wins_blue} Blue"),
                    ("Points Scored",       lambda: str(st.points)),
                    ("Longest Rally",       lambda: str(st.best_rally)),
                    ("Fastest Ball",        lambda: f"{st.top_ball_speed} pps"),
                    ("Time Played",         lambda: st.format_time(st.play_time)),
                    ("Online Matches",      lambda: f"{st.online_matches}  ({st.online_wins} won, {st.online_losses} lost)"),
                    ("Online Win Rate",     lambda: f"{st.online_win_rate}%"),
                    ("Online Win Streak",   lambda: f"{st.online_streak}  (best {st.online_best_streak})")]
            table = Grid([[Text(label, f, theme.GOLD, align="right"),
                           Text(value, f, theme.PARCHMENT, align="left",
                                samples=["Red 9999  -  9999 Blue", "9999  (best 9999)", "9999  (9999 won, 9999 lost)"])]
                          for label, value in rows],
                         gap_x=int(BASE_W * 0.03 * s), gap_y=int(ui.gap * 0.5 * s))
            buttons = Stack([Button("open_replays", "Replays", sm, (theme.ORANGE, theme.ORANGE_HOVER),
                                    tip=TIPS["open_replays"]),
                             Button("export_stats", "Export Stats", sm, (theme.GREEN, theme.GREEN_HOVER),
                                    tip=TIPS["export_stats"]),
                             Button("import_stats", "Import Stats", sm, (theme.BLUE, theme.BLUE_HOVER),
                                    tip=TIPS["import_stats"]),
                             Button("reset_stats", "Reset Stats", sm, (theme.RED, theme.RED_HOVER),
                                    tip=TIPS["reset_stats"])],
                            vertical=False, gap=int(BASE_W * 0.015 * s), uniform=True)
            return Stack([table, buttons], gap=self.vgap(ui, s, 1.4))

        ui.screen_menu(state, screen, build, title="战绩 Stats", mark="绩")

    # ── Replays ────────────────────────────────────────────────────────────────

    def draw_replay(self, state, screen):
        """A replay: the match as it was, its HUD, and the controls for the kind of replay it is."""
        view = state.view
        self.draw_world(screen, view)
        self.app.hud.draw(state, screen, view, live=False)
        mouse = self.mouse()

        # It must never pass for the live match: the picture is tinted like old film and framed
        # like a camera's viewfinder.  Nothing covers the court's edges, so the ball is always
        # in sight; the labels sit on see-through plates
        screen.blit(self.art.get(("replay_tint",), self._replay_tint), (0, 0))
        self.draw_replay_frame(screen)

        pulse = .5 + .5 * math.sin(self.app.fx.time * 5)
        badge = pygame.Rect(26, 22, 268, 56)
        screen.blit(self.glass(badge.w, badge.h), badge)
        pygame.draw.circle(screen, mix((120, 20, 20), (255, 60, 50), pulse), (badge.x + 26, badge.centery), 10)
        mark = self.art.gilded("回放  REPLAY", self.brush(0.04), glow=None)
        screen.blit(mark, mark.get_rect(midleft=(badge.x + 46, badge.centery)))
        if state.slowed() or state.rate() != 1.0:
            label = "SLOW MOTION" if state.rate() < 1 else f"{state.rate():g}x"
            self.text(screen, label, self.fnt(0.024), theme.FLAME, midleft=(badge.right + 14, badge.centery))

        score = f"Red {view.p1.score}  -  {view.p2.score} Blue"
        font = self.fnt(0.028)
        plate = pygame.Rect(0, 0, font.size(score)[0] + 44, 56)
        plate.topright = (BASE_W - 26, 22)
        screen.blit(self.glass(plate.w, plate.h), plate)
        self.text(screen, score, font, theme.PARCHMENT, center=plate.center)

        caption = state.caption()
        if caption:
            words = self.art.gilded(caption, self.brush(0.05), glow=None)
            plate = words.get_rect(center=(BASE_W // 2, 50)).inflate(60, 16)
            screen.blit(self.glass(plate.w, plate.h), plate)
            screen.blit(words, words.get_rect(center=plate.center))

        self.draw_replay_intro(screen, state)

        if state.mode == "viewer":
            self.draw_replay_bar(state, screen, mouse)
            return
        font = self.fnt(0.022)
        hint = "Space: next highlight      S: save this one      Esc: stop" if state.mode == "reel" else \
               "Space: skip      S: save this moment      Esc: back to the match"
        if ANDROID:                     # a phone has the buttons, and Back
            hint = "Save keeps this one      Skip or Back stops the highlights" if state.mode == "reel" else \
                   "Save keeps this moment      Skip or Back returns to the match"
        plate = pygame.Rect(0, 0, font.size(hint)[0] + 50, 44)
        plate.midbottom = (BASE_W // 2, BASE_H - 20)
        screen.blit(self.glass(plate.w, plate.h), plate)
        self.text(screen, hint, font, theme.PARCHMENT, center=plate.center)
        state.ui_hitboxes["replay_save"] = self.draw_button(screen, mouse, self.fnt(0.022), "Save",
                                                            BASE_W - 250, BASE_H - 46, theme.GREEN, width=120)
        state.ui_hitboxes["replay_back"] = self.draw_button(screen, mouse, self.fnt(0.022), "Skip",
                                                            BASE_W - 106, BASE_H - 46, theme.RED, width=120)

    @staticmethod
    def _replay_tint():
        tint = pygame.Surface((BASE_W, BASE_H))
        tint.fill((92, 58, 26))
        tint.set_alpha(85)
        return tint

    def glass(self, w, h):
        """A see-through plate: the court shows through it."""
        return self.art.get(("glass", w, h), self._glass, w, h)

    def _glass(self, w, h):
        plate = self.art.inset(w, h).copy()
        plate.fill((255, 255, 255, 165), special_flags=pygame.BLEND_RGBA_MULT)
        return plate

    def draw_replay_frame(self, screen):
        """A thin frame at the very edge of the screen, with viewfinder corners."""
        pygame.draw.rect(screen, theme.GOLD_DARK, (0, 0, BASE_W, BASE_H), 3)
        arm, t = 70, 5
        for x, y, dx, dy in ((8, 8, 1, 1), (BASE_W - 8, 8, -1, 1), (8, BASE_H - 8, 1, -1), (BASE_W - 8, BASE_H - 8, -1, -1)):
            pygame.draw.line(screen, theme.GOLD, (x, y), (x + dx * arm, y), t)
            pygame.draw.line(screen, theme.GOLD, (x, y), (x, y + dy * arm), t)

    def draw_replay_intro(self, screen, state):
        """The first moment of a replay: a rewind flash and a big REPLAY stamp, so the switch
        from the live match can't be missed."""
        age = state.age
        if age >= 0.7:
            return
        k = age / 0.7
        streaks = max(0, int(14 * (1 - k)))
        rng = random.Random(int(age * 30))
        for _ in range(streaks):
            y = rng.randrange(20, BASE_H - 20)
            pygame.draw.line(screen, (255, 240, 220), (0, y), (BASE_W, y), rng.choice((1, 2, 3)))
        stamp = self.art.gilded("回放 REPLAY", self.brush(0.12), thickness=4)
        size = 1.5 - 0.5 * min(1.0, k * 2.5)
        if size != 1.0:
            stamp = pygame.transform.smoothscale(stamp, (int(stamp.get_width() * size), int(stamp.get_height() * size)))
        stamp.set_alpha(int(255 * (1 - k) ** 0.5))
        screen.blit(stamp, stamp.get_rect(center=(BASE_W // 2, BASE_H // 2)))

    def draw_replay_bar(self, state, screen, mouse):
        """The viewer's controls: a timeline with the highlights marked, and the buttons below it.
        They tuck away while a replay plays and the mouse is still."""
        if state.playing and state.idle > 3.0 and not state.dragging:
            return
        clip = state.clip
        total = max(1, len(clip.frames) - 1)
        panel = pygame.Rect(40, BASE_H - 168, BASE_W - 80, 152)
        screen.blit(self.glass(panel.w, panel.h), panel)

        bar = pygame.Rect(panel.x + 40, panel.y + 30, panel.w - 80, 20)
        screen.blit(self.art.inset(bar.w, bar.h), bar)
        if state.mark_in is not None:
            end = state.mark_out if state.mark_out is not None else state.position
            a, b = sorted((state.mark_in, end))
            x0, x1 = bar.x + int(bar.w * a / total), bar.x + int(bar.w * b / total)
            shade = blank(max(2, x1 - x0), bar.h - 4)
            shade.fill((*theme.EMBER, 120))
            screen.blit(shade, (x0, bar.y + 2))
            for x in (x0, x1) if state.mark_out is not None else (x0,):
                pygame.draw.line(screen, theme.FLAME, (x, bar.y - 8), (x, bar.bottom + 8), 3)
        k = state.position / total
        fill_w = int((bar.w - 6) * k)
        if fill_w > 0:
            fill = self.art.slider_fill(bar.w - 6, bar.h - 6, theme.EMBER)
            screen.blit(fill, (bar.x + 3, bar.y + 3), (0, 0, fill_w, bar.h - 6))
        for m in state.moments:
            mx = bar.x + int(bar.w * m.at / total)
            diamond = [(mx, bar.y - 18), (mx + 8, bar.y - 9), (mx, bar.y), (mx - 8, bar.y - 9)]
            pygame.draw.polygon(screen, theme.GOLD_BRIGHT, diamond)
            pygame.draw.polygon(screen, theme.INK, diamond, 1)
            hot = pygame.Rect(mx - 10, bar.y - 20, 20, 22)
            self.tips.offer(hot, f"{m.title}\nA highlight. Click Next or Previous to jump to it.")
        knob = self.art.blossom(30, (214, 168, 88), (150, 26, 26))
        screen.blit(knob, knob.get_rect(center=(bar.x + 3 + fill_w, bar.centery)))
        state.ui_hitboxes["replay_timeline"] = bar.inflate(0, 24)
        self.tips.offer(bar.inflate(0, 24), "Timeline\nClick or drag to move through the replay.\n"
                                            "• Gold diamonds are highlights\n~ Left / Right: 5 s, or a frame when paused")

        from render.ui.layout import clock
        f = self.fnt(0.024)
        y = panel.y + 104
        buttons = [("replay_back", "Back", theme.RED, 130, "Back\nLeave the replay.\n~ Esc"),
                   ("replay_prev", "|<", theme.WHITE, 70, "Previous Highlight\nJump back to the last highlight."),
                   ("replay_play", "Pause" if state.playing else "Play", theme.GREEN, 130, "Play / Pause\n~ Space"),
                   ("replay_next", ">|", theme.WHITE, 70, "Next Highlight\nJump on to the next highlight."),
                   ("replay_speed", f"{[0.25, 0.5, 1.0, 2.0][state.speed]:g}x", theme.BLUE, 100,
                    "Speed\nClick to step through quarter, half, normal and double speed.")]
        x = panel.x + 30
        for key, text, colour, w, tip in buttons:
            rect = self.draw_button(screen, mouse, f, text, x + w // 2, y, colour, width=w)
            state.ui_hitboxes[key] = rect
            self.tips.offer(rect, tip)
            x += w + 14
        self.text(screen, f"{clock(state.position / 60)} / {clock(total / 60)}", f, theme.PARCHMENT,
                  midleft=(x + 10, y))

        right = [("replay_in", "Mark In", theme.WHITE, 150, "Mark In\nWhere the part to save starts.\n~ I"),
                 ("replay_out", "Mark Out", theme.WHITE, 150, "Mark Out\nWhere the part to save ends.\n~ O"),
                 ("replay_clear", "Clear", theme.WHITE, 110, "Clear\nForget the marks."),
                 ("replay_save_part", "Save Part", theme.ORANGE, 170,
                  "Save Part\nSave just the marked part to your Replays."),
                 ("replay_save_all", "Save All", theme.GREEN, 160,
                  "Save All\nSave the whole replay to your Replays." if not state.saved else
                  "Save All\nSave another copy of this replay.")]
        x = panel.right - 30
        for key, text, colour, w, tip in reversed(right):
            if key in ("replay_save_part", "replay_clear") and state.mark_in is None:
                colour = theme.DARK_GRAY
            rect = self.draw_button(screen, mouse, f, text, x - w // 2, y, colour, width=w)
            state.ui_hitboxes[key] = rect
            self.tips.offer(rect, tip)
            x -= w + 14

    def draw_replays_menu(self, state, screen):
        ui = self.ui

        def build(s):
            f, sm, ty = ui.fnt(0.028, s), ui.fnt(0.024, s), ui.fnt(0.02, s)
            shown = state.shown()
            if not shown:
                body = [Text("No replays saved yet.", f, theme.GOLD),
                        Text("Save one while you watch: Pause > Replay, the win screen's Replay or Highlights,", ty),
                        Text("or press S during an instant replay.", ty)]
                return Stack([*body, Button("open_folder", "Open Folder", sm, (theme.BLUE, theme.BLUE_HOVER),
                                            tip="Open Folder\nThe folder your replays are saved in.")],
                             gap=self.vgap(ui, s, 1.2))
            rows = []
            for i, (path, header) in enumerate(shown):
                kind = str(header.get("kind", "match")).title()
                score = header.get("score", [0, 0])
                length = float(header.get("length", 0))
                when = str(header.get("created", ""))[:16].replace("T", "  ")
                court = header.get("court", "Classic")
                title = (header.get("title", "") if kind == "Highlight" else
                         "The whole match" if kind == "Match" else "Part of a match")
                rows.append([Text(kind, sm, theme.FLAME if kind == "Highlight" else theme.GOLD,
                                  samples=["Highlight", "Match", "Clip"], align="left"),
                             Text(f"Red {score[0]} - {score[1]} Blue", sm, theme.PARCHMENT,
                                  samples=["Red 99 - 99 Blue"]),
                             Text(title, ty, theme.PARCHMENT, samples=["Off the end of the paddle!  "], align="left"),
                             Text(f"{when}   {int(length // 60)}:{int(length % 60):02d}   {court}", ty, theme.GRAY,
                                  samples=["2026-11-04  20:44   59:59   Ferry Gates"], align="left"),
                             Button(f"watch_{i}", "Watch", sm, (theme.GREEN, theme.GREEN_HOVER),
                                    tip="Watch\nPlay this replay."),
                             Button(f"delete_{i}", "Delete", sm, (theme.RED, theme.RED_HOVER),
                                    tip="Delete\nRemove this replay for good.")])
            pages = max(1, (len(state.items) + state.PER_PAGE - 1) // state.PER_PAGE)
            texts = [f"Page {n + 1} of {pages}" for n in range(pages)]
            footer = Stack([Cycle("page", lambda: texts[state.page], sm, texts,
                                  tip="Pages\nMore replays, oldest last.\n~ Mouse wheel"),
                            Button("open_folder", "Open Folder", sm, (theme.BLUE, theme.BLUE_HOVER),
                                   tip="Open Folder\nThe folder your replays are saved in.")],
                           vertical=False, gap=int(BASE_W * 0.03 * s))
            return Stack([Grid(rows, gap_x=int(BASE_W * 0.014 * s), gap_y=self.vgap(ui, s, 0.5)), footer],
                         gap=self.vgap(ui, s, 1.2))

        ui.screen_menu(state, screen, build, title="回放 Replays", mark="映")

    # ── Interface settings ─────────────────────────────────────────────────────

    def draw_interface_settings_menu(self, state, screen):
        ui = self.ui
        i = self.app.settings.interface

        def build(s):
            f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.02, s)

            def flag(name, attr):
                return self.toggle(sm, f"toggle_{attr}", name, lambda: getattr(i, attr))

            last = flag("Vibration", "vibration") if ANDROID else flag("Hide Mouse", "hide_cursor")
            toggles = Grid([[flag("Tooltips", "tooltips"), flag("AI Banter", "ai_banter")],
                            [flag("Screen Shake", "screen_shake"), flag("Ball Trail", "ball_trail")],
                            [flag("Auto-Pause", "auto_pause"), last]],
                           gap_x=int(BASE_W * 0.012 * s), gap_y=int(ui.gap * 0.8 * s), uniform=True)

            notes = {"hud": ("HUD", "What the match shows besides the scores.",
                             [("Full", "rally count and ball speed too"), ("Minimal", "just the scores")]),
                     "effects": ("Effects", "Butterflies, embers, petals and bursts.",
                                 [("Full", ""), ("Reduced", "half as many"), ("Off", "none: the calmest, and fastest")]),
                     "countdown": ("Countdown", "How long the countdown before each serve lasts.",
                                   [(f"{n} second{'s' if n != 1 else ''}", "") for n in i.countdown_options]),
                     "instant_replay": ("Instant Replay", "When a match's best moments replay by themselves.",
                                        [("Off", "only when you ask: Pause or the win screen"),
                                         ("Great Points", "straight after a point with a great moment"),
                                         ("After the Match", "the highlights, before the win screen"),
                                         ("Both", "")])}

            def cycle(name, title, texts):
                head, intro, options = notes[name]
                tip = lambda: options_tip(head, intro, options, getattr(i, name))
                return [Text(title, sm, theme.GOLD, align="right"),
                        Cycle(f"cycle_{name}", lambda: texts[getattr(i, name)], f, texts, tip=tip)]

            seconds = [f"{n} second{'s' if n != 1 else ''}" for n in i.countdown_options]
            cycles = Grid([cycle("hud", "HUD", i.hud_options),
                           cycle("effects", "Effects", i.effects_options),
                           cycle("countdown", "Countdown", seconds),
                           cycle("instant_replay", "Replays", i.instant_replay_options)],
                          gap_x=int(BASE_W * 0.012 * s), gap_y=int(ui.gap * 0.8 * s))

            left = self.section(ui, s, "Interface", toggles, cycles)

            if ANDROID:
                return Grid([[left, self.touch_section(ui, s, state)]], gap_x=int(BASE_W * 0.06 * s))

            samples = ["Press a key", "Right Shift", "Backspace"]
            def bind(field):
                return KeyButton(f"key_{field}", lambda: key_name(getattr(i, field)), sm,
                                 lambda: state.listening == field, samples, tip=TIPS["key"])

            rows = [[Space(), Text("Red", sm, (255, 112, 92)), Text("Blue", sm, (112, 162, 255))]]
            for action in i.ACTIONS:
                rows.append([Text(action.title(), sm, theme.GOLD, align="right"),
                             bind(f"p1_{action}"), bind(f"p2_{action}")])
            keys = self.section(ui, s, "Keys",
                                Grid(rows, gap_x=int(BASE_W * 0.01 * s), gap_y=int(ui.gap * 0.6 * s)),
                                Text("Click a key, then press the new one.", ty, theme.PARCHMENT))

            return Grid([[left, keys]], gap_x=int(BASE_W * 0.06 * s))

        ui.screen_menu(state, screen, build, title="界面 Interface", mark="界", reset="Reset to Default")

    def touch_section(self, ui, s, state):
        """On a phone, the Interface screen's Touch section, in place of the keys."""
        i = self.app.settings.interface
        f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.02, s)
        steer, feel = i.touch_steer_options, i.touch_sensitivity_options
        steer_tip = lambda: options_tip("Steering", "How a finger moves your paddle.",
                                        [("Drag", "it moves as your finger moves, from wherever you touch"),
                                         ("Follow", "it heads for the point under your finger")],
                                        i.touch_steer)
        feel_tip = lambda: options_tip("Sensitivity", "How far Drag moves the paddle for each move of your finger.",
                                       [(name, "") for name in feel], i.touch_sensitivity,
                                       "Follow always goes to your finger")
        rows = Grid([[Text("Steering", sm, theme.GOLD, align="right"),
                      Cycle("cycle_touch_steer", lambda: steer[i.touch_steer], f, steer, tip=steer_tip)],
                     [Text("Sensitivity", sm, theme.GOLD, align="right"),
                      Cycle("cycle_touch_sensitivity", lambda: feel[i.touch_sensitivity], f, feel, tip=feel_tip)]],
                    gap_x=int(BASE_W * 0.012 * s), gap_y=int(ui.gap * 0.8 * s))
        notes = Stack([Text("Against the AI or online, the whole screen steers your paddle.", ty, theme.PARCHMENT),
                       Text("Two players on one phone: each has their own half.", ty, theme.PARCHMENT),
                       Text("Back, or the button at the bottom, pauses a match.", ty, theme.PARCHMENT)],
                      gap=int(ui.gap * 0.4 * s))
        return self.section(ui, s, "Touch", rows, notes)

    # ── Game feel (purely visual) ──────────────────────────────────────────────

    def shake(self, magnitude, duration):
        if not self.app.settings.interface.screen_shake:
            return
        self._shake_mag, self._shake_time, self._shake_total = magnitude, duration, duration

    def _shake_offset(self):
        if self._shake_time <= 0:
            return 0, 0
        self._shake_time = max(0.0, self._shake_time - self.app.dt)
        mag = self._shake_mag * self._shake_time / self._shake_total
        return random.uniform(-mag, mag), random.uniform(-mag, mag)

    def show_toast(self, text, important=False):
        """A note in the bottom-left corner.  An important one (someone left the game...) isn't
        pushed off by a routine one, like the next track's name."""
        current = self._toast
        if not important and current is not None and len(current) > 2 and current[2] and current[1] < 3.0:
            return
        font = self.ui.fnt(0.03)
        label = font.render(text, True, theme.GOLD_BRIGHT)
        flower = self.art.blossom(32)
        pad = int(BASE_H * 0.015)
        w = flower.get_width() + label.get_width() + 3 * pad
        h = label.get_height() + 2 * pad

        surf = blank(w, h)
        surf.blit(self.art.inset(w, h), (0, 0))
        surf.blit(flower, flower.get_rect(midleft=(pad, h // 2)))
        surf.blit(label, label.get_rect(midleft=(2 * pad + flower.get_width(), h // 2)))
        self._toast = [surf, 0.0, important]

    def draw_toast(self, screen, dt):
        """Slides in at the bottom-left, holds, then fades out."""
        if self._toast is None:
            return
        surf, age = self._toast[0], self._toast[1]
        age += dt
        self._toast[1] = age
        slide, hold, fade = 0.35, 3.0, 0.5
        if age > slide + hold + fade:
            self._toast = None
            return
        t = min(1.0, age / slide)
        x = int(lerp(-surf.get_width(), BASE_W * 0.02, 1 - (1 - t) ** 3))
        surf.set_alpha(255 if age < slide + hold else int(255 * (1 - (age - slide - hold) / fade)))
        screen.blit(surf, (x, BASE_H - surf.get_height() - int(BASE_H * 0.03)))

    # ── Game world ─────────────────────────────────────────────────────────────

    def draw_arena(self, screen, ox, oy, wall=True, cord=True):
        """The court.  `cord` False leaves out the line down the middle (Open Court has taken the wall down)."""
        W, H = BASE_W, BASE_H
        art = self.art
        t = self.app.fx.time

        # Spirit fire along each goal
        for side, tint in (("left", (150, 34, 22)), ("right", (26, 70, 170))):
            level = 4 + round(2 * (math.sin(t * 2.6 + (side == "left") * 2) * .5 + .5))
            strip = art.goal_glow(side, tint, level)
            screen.blit(strip, (0 if side == "left" else W - strip.get_width(), 0), special_flags=ADD)

        if random.random() < 40 * self.app.dt:
            x, col = random.choice(((random.uniform(0, 16), theme.EMBER),
                                    (W - random.uniform(0, 16), theme.SPIRIT_BLUE)))
            self.app.fx.spark(x, random.uniform(0, H), 1, col, speed=90, life=1.1,
                              arc=(-1.9, -1.2), gravity=-60)

        seal = art.watermark("往", 300, 26)
        screen.blit(seal, seal.get_rect(center=(W // 2 + ox, H // 2 + oy)))
        ring = art.faint_sigil(420, 44)
        screen.blit(ring, ring.get_rect(center=(W // 2 + ox, H // 2 + oy)))

        if cord:
            line = art.cord(H, faint=not wall)
            screen.blit(line, line.get_rect(midtop=(W // 2 + ox, oy)))

        rail = art.rail(W, flowers=False)
        screen.blit(rail, rail.get_rect(midtop=(W // 2 + ox, oy - 4)))
        screen.blit(rail, rail.get_rect(midbottom=(W // 2 + ox, H + oy + 4)))

    def draw_paddle(self, screen, paddle, rect):
        finish = "red" if paddle.is_left else "blue"
        # Sprites come in 2-4 px steps, so a size that keeps drifting (Chaos Mode +) reuses them.
        # They round down, so the paddle is never drawn bigger than its hitbox.
        centre = rect.center
        rect = pygame.Rect(0, 0, max(4, int(rect.w / 2) * 2), max(8, int(rect.h / 4) * 4))
        rect.center = centre
        halo = self.art.paddle_glow(rect.w, rect.h, finish)
        screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)

        flash = getattr(paddle, "flash", 0.0)
        if flash > 0:
            paddle.flash = max(0.0, flash - self.app.dt * 5)
            screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
            sprite = self.art.paddle_flash(rect.w, rect.h, finish, max(1, math.ceil(flash * 4)))
        else:
            sprite = self.art.paddle(rect.w, rect.h, finish)
        screen.blit(sprite, rect)

        powerups = getattr(paddle.game, "powerups", None)
        if powerups:
            self.draw_paddle_effects(screen, paddle, rect, powerups)

    # One aura per paddle, the first that applies: boons gold, curses violet, Gravity jade
    EFFECT_GLOWS = (("giant", "gold"), ("swift", "gold"), ("shrink", "violet"),
                    ("sticky", "violet"), ("gravity", "jade"))
    ICON_SIZES = (80, 64, 44, 34)

    def draw_paddle_effects(self, screen, paddle, rect, powerups):
        art = self.art
        pulse = .65 + .35 * math.sin(self.app.fx.time * 6)
        for key, finish in self.EFFECT_GLOWS:
            if powerups.has(paddle, key):
                halo = art.paddle_glow(rect.w, rect.h, finish)
                halo.set_alpha(int(255 * pulse))
                screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
                halo.set_alpha(255, pygame.RLEACCEL)
                break
        if powerups.frosted(paddle):
            halo = art.paddle_glow(rect.w, rect.h, "ice")
            screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
            ice = art.get(("ice_coat", rect.w, rect.h), self._ice_coat, rect.w, rect.h)
            screen.blit(ice, rect)
        if powerups.has(paddle, "sticky"):
            goo = art.get(("goo_coat", rect.w, rect.h), self._goo_coat, rect.w, rect.h)
            screen.blit(goo, goo.get_rect(midtop=rect.midtop))

    @staticmethod
    def _goo_coat(w, h):
        """Sticky Goo: goo smeared over the paddle, dripping off it."""
        coat = blank(w, h + 18)
        green = (190, 220, 60, 150)
        pygame.draw.rect(coat, green, (0, 0, w, h), border_radius=max(3, w // 3))
        rng = random.Random(w * 1000 + h)
        for _ in range(max(2, h // 60)):
            x = rng.uniform(2, w - 6)
            y = rng.uniform(h * .2, h * .95)
            length = rng.uniform(8, 18)
            pygame.draw.rect(coat, (200, 230, 70, 190), (x, y, 4, length), border_radius=2)
            pygame.draw.circle(coat, (210, 240, 90, 210), (x + 2, y + length), 3)
        pygame.draw.rect(coat, (230, 250, 140, 200), (0, 0, w, h), 2, border_radius=max(3, w // 3))
        return coat

    @staticmethod
    def _ice_coat(w, h):
        coat = blank(w, h)
        pygame.draw.rect(coat, (200, 232, 255, 120), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(coat, (236, 248, 255, 200), (0, 0, w, h), 2, border_radius=6)
        return coat

    def draw_ball(self, screen, ball, rect, ox, oy):
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        r = rect.w // 2

        trail = self._trail if ball is getattr(ball.game, "ball", ball) else self._twin_trail
        if not self.app.settings.interface.ball_trail:
            trail.clear()
        elif trail:
            lx, ly = trail[-1]
            moved = math.hypot(cx - lx, cy - ly)
            if moved > ball.width * 4:          # ball respawned: don't smear across the court
                trail.clear()
            elif moved >= ball.width * 0.2:
                trail.append((cx, cy))
        else:
            trail.append((cx, cy))

        # A Ghost Ball fades mid-court, trail and all
        powerups = getattr(ball.game, "powerups", None)
        alpha = powerups.ball_alpha(ball) if powerups else 1.0
        if alpha < 1.0:
            sprite = self.art.ball(max(8, round(rect.w / 2) * 2))
            sprite.set_alpha(int(255 * alpha))
            screen.blit(sprite, sprite.get_rect(center=rect.center))
            sprite.set_alpha(255, pygame.RLEACCEL)
            return

        # Soul-fire tail in the colour of whoever hit it last, oldest and faintest first
        paddle = getattr(ball, "last_paddle", None)
        fire = (40, 96, 220) if paddle and not paddle.is_left else (200, 60, 22)
        side = getattr(ball, "side", None)
        if side:                                   # Twin Balls: each keeps its own colour, whoever hits it
            fire = (200, 60, 22) if side == "red" else (40, 96, 220)
        snow = bool(powerups) and powerups.snowball()
        ghost = bool(powerups) and powerups.ghostly()
        if getattr(ball, "blazing", False):
            fire = (255, 116, 30)                  # Spirit Fire
        elif powerups and powerups.ball_frosted():
            fire = (120, 190, 240)                 # Frostbite
        elif snow:
            fire = (190, 214, 240)                 # Snowball
        elif ghost:
            fire = (120, 230, 200)                 # Ghost Ball: a pale spirit-green trail
        count = len(trail)
        for i, (x, y) in enumerate(list(trail)):
            k = (i + 1) / count
            level = 1 + int(k * 5)
            radius = max(6, int(r * (.5 + 1.0 * k)) // 4 * 4)
            glow = self.art.glow(radius, scaled(fire, (level / 6) ** 2))
            screen.blit(glow, (x + ox - radius, y + oy - radius), special_flags=ADD)

        size = 2.6 if not getattr(ball, "blazing", False) else 3.6
        halo = self.art.glow(max(24, int(r * size) // 4 * 4), scaled(fire, .75))
        screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
        sprite = self.art.ball(max(8, round(rect.w / 2) * 2))
        screen.blit(sprite, sprite.get_rect(center=rect.center))
        if side:
            d = max(8, round(rect.w / 4) * 4)
            ring = self.art.get(("twin_ring", d, side), self._twin_ring, d, side)
            screen.blit(ring, ring.get_rect(center=rect.center))
        hits = powerups.cracker_hits(ball) if powerups and hasattr(powerups, "cracker_hits") else 0
        if hits or (powerups and getattr(powerups, "cracker", None) and ball is getattr(ball.game, "ball", None)):
            self.draw_cracker(screen, rect, hits)
        if powerups and powerups.ball_frosted() and ball is getattr(ball.game, "ball", ball):
            ice = self.art.get(("ice_ball", rect.w), self._ice_ball, max(8, round(rect.w / 2) * 2))
            screen.blit(ice, ice.get_rect(center=rect.center))
        elif snow and ball is getattr(ball.game, "ball", ball):
            d = max(8, round(rect.w / 4) * 4)
            coat = self.art.get(("snow_ball", d), self._snow_ball, d)
            screen.blit(coat, coat.get_rect(center=rect.center))
        elif ghost:
            d = max(8, round(rect.w / 4) * 4)
            veil = self.art.get(("ghost_veil", d), self._ghost_veil, d)
            screen.blit(veil, veil.get_rect(center=rect.center))

    def draw_cracker(self, screen, rect, hits):
        """Firecracker: a red cracker strapped to the ball, its fuse fizzing; the number of hits
        left before it bangs beside it (none: the fuse is burning down)."""
        t = self.app.fx.time
        x, y = rect.right - 4, rect.top + 2
        body = pygame.Rect(0, 0, 14, 32)
        body.midbottom = (x, y + 20)
        pygame.draw.rect(screen, (196, 30, 34), body, border_radius=4)
        pygame.draw.rect(screen, (250, 200, 80), (body.x, body.y + 6, body.w, 4))
        pygame.draw.rect(screen, (250, 200, 80), (body.x, body.bottom - 10, body.w, 4))
        pygame.draw.rect(screen, (90, 10, 14), body, 2, border_radius=4)
        tip = (body.centerx + 8, body.top - 10)
        pygame.draw.line(screen, (60, 50, 40), (body.centerx, body.top), tip, 3)
        flicker = 0.5 + 0.5 * math.sin(t * (40 if not hits else 18))
        glow = self.art.glow(28 if hits else 40, scaled((255, 200, 80), 0.6 + 0.4 * flicker))
        screen.blit(glow, glow.get_rect(center=tip), special_flags=ADD)
        if random.random() < (0.9 if not hits else 0.35):
            self.app.fx.spark(tip[0], tip[1], 1, (255, 210, 120), speed = 160, life = .25)
        if hits:
            self.text(screen, str(hits), self.fnt(0.026), (255, 236, 200), midleft=(body.right + 6, body.centery))

    def draw_portals(self, screen, powerups, ox, oy):
        """Portal Pair: two swirling rings, linked, each with arrows showing the way a ball leaves it."""
        portals = getattr(powerups, "portals", [])
        if not portals:
            return
        t = self.app.fx.time
        R = PowerUps.PORTAL_R
        for i, door in enumerate(portals):
            x, y = door["x"] + ox, door["y"] + oy
            glow = self.art.glow(int(R * 2.2) // 4 * 4, scaled((150, 100, 255), .7))
            screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
            ring = self.art.get(("portal_ring", R), self._portal_ring, R)
            screen.blit(ring, ring.get_rect(center=(x, y)))
            spin = 1 if i else -1
            for k in range(10):
                a = spin * t * 3.2 + k * math.tau / 10
                rr = R * (0.55 + 0.12 * math.sin(t * 4 + k))
                pygame.draw.circle(screen, (210, 190, 255), (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr)), 3)
            dx, dy = math.cos(door["angle"]), math.sin(door["angle"])
            px, py = -dy, dx
            for n in range(2):
                d = R * 0.15 + n * 16 + (t * 40) % 16
                cx, cy = x + dx * d, y + dy * d
                tipp = (cx + dx * 10, cy + dy * 10)
                pygame.draw.line(screen, (120, 240, 255), (cx - px * 12, cy - py * 12), tipp, 4)
                pygame.draw.line(screen, (120, 240, 255), (cx + px * 12, cy + py * 12), tipp, 4)

    @staticmethod
    def _portal_ring(R):
        s = int(R * 2 + 12)
        c = s // 2
        ring = blank(s, s)
        pygame.draw.circle(ring, (20, 8, 40, 200), (c, c), int(R))
        pygame.draw.circle(ring, (60, 30, 120, 160), (c, c), int(R * 0.7))
        pygame.draw.circle(ring, (170, 120, 255, 255), (c, c), int(R), 5)
        pygame.draw.circle(ring, (230, 210, 255, 200), (c, c), int(R) - 6, 2)
        return ring

    def draw_wind(self, screen, powerups):
        """Wind Gust: leaves blowing up or down the court, swaying as they go."""
        force = powerups.wind_force() if hasattr(powerups, "wind_force") else 0.0
        leaves = self._leaves
        dt = min(self.app.dt, 1 / 20)
        if force:
            way = 1 if force > 0 else -1
            for _ in range(int(abs(force) / PowerUps.WIND * 30 * dt * 10) + (1 if random.random() < abs(force) / PowerUps.WIND * 0.3 else 0)):
                leaves.append([random.uniform(0, BASE_W), -20 if way > 0 else BASE_H + 20,
                               random.uniform(-60, 60), way * random.uniform(260, 460),
                               random.uniform(0, math.tau), random.uniform(-4, 4), random.choice(self.LEAF_COLOURS),
                               random.uniform(7, 13), random.uniform(0, math.tau)])
        keep = []
        t = self.app.fx.time
        for leaf in leaves:
            leaf[0] += (leaf[2] + math.sin(t * 2.5 + leaf[8]) * 90) * dt
            leaf[1] += leaf[3] * dt
            leaf[4] += leaf[5] * dt
            if -40 < leaf[1] < BASE_H + 40:
                keep.append(leaf)
                x, y, a, col, size = leaf[0], leaf[1], leaf[4], leaf[6], leaf[7]
                ca, sa = math.cos(a), math.sin(a)
                pts = [(x + ca * size, y + sa * size), (x - sa * size * 0.45, y + ca * size * 0.45),
                       (x - ca * size, y - sa * size), (x + sa * size * 0.45, y - ca * size * 0.45)]
                pygame.draw.polygon(screen, col, pts)
                pygame.draw.line(screen, (90, 50, 20), pts[0], pts[2], 1)
        self._leaves[:] = keep[-220:]

    LEAF_COLOURS = ((214, 96, 32), (236, 150, 40), (190, 52, 30), (240, 196, 70), (160, 90, 40))

    def draw_night(self, screen, game, level, ox, oy):
        """Lantern Night: the court goes dark but for lantern light round each paddle and each
        ball's own glow."""
        if self._night is None or self._night.get_size() != (BASE_W, BASE_H):
            self._night = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
        dark = self._night
        dark.fill((6, 4, 16, int(236 * level)))
        lights = [((o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2, 300) for o in (game.p1, game.p2)]
        lights += [((o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2, 150) for o in game.objects if o.is_ball]
        for x, y, radius in lights:
            hole = self.art.get(("night_hole", radius), self._night_hole, radius)
            dark.blit(hole, hole.get_rect(center=(int(x + ox), int(y + oy))), special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(dark, (0, 0))
        for paddle in (game.p1, game.p2):
            glow = self.art.glow(240, scaled((255, 170, 80), 0.32 * level))
            screen.blit(glow, glow.get_rect(center=(int((paddle.x0 + paddle.x1) / 2 + ox), int((paddle.y0 + paddle.y1) / 2 + oy))),
                        special_flags=ADD)

    @staticmethod
    def _night_hole(radius):
        """A soft round hole in the dark: fully lit in the middle, fading out to the edge."""
        hole = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -4):
            k = 1 - i / radius
            pygame.draw.circle(hole, (0, 0, 0, int(255 * min(1.0, k * 1.6))), (radius, radius), i)
        return hole

    @staticmethod
    def _twin_ring(d, side):
        """Twin Balls: the ball tinted and ringed in its side's colour, so the two are easy to tell apart."""
        s = d + 10
        c = s // 2
        ring = blank(s, s)
        tint = (232, 70, 40) if side == "red" else (60, 130, 255)
        pygame.draw.circle(ring, (*tint, 110), (c, c), d // 2)
        pygame.draw.circle(ring, (*tint, 255), (c, c), d // 2 + 3, max(2, d // 14))
        return ring

    @staticmethod
    def _ghost_veil(d):
        """Ghost Ball: a pale, see-through veil over the ball, with wisps trailing off it."""
        s = d + 16
        c = s // 2
        veil = blank(s, s)
        pygame.draw.circle(veil, (170, 255, 220, 90), (c, c), d // 2 + 2)
        pygame.draw.circle(veil, (220, 255, 240, 170), (c, c), d // 2 + 2, max(1, d // 20))
        for i in range(5):
            a = i / 5 * math.tau + 0.4
            x, y = c + math.cos(a) * (d // 2 + 4), c + math.sin(a) * (d // 2 + 4)
            pygame.draw.circle(veil, (200, 255, 235, 120), (int(x), int(y)), max(2, d // 10))
        return veil

    @staticmethod
    def _snow_ball(d):
        """Snowball: packed snow over the ball, with a few darker clumps."""
        coat = blank(d + 4, d + 4)
        c = d // 2 + 2
        pygame.draw.circle(coat, (236, 244, 255, 235), (c, c), d // 2)
        pygame.draw.circle(coat, (255, 255, 255, 255), (c - d // 7, c - d // 7), max(2, d // 4))
        rng = random.Random(d)
        for _ in range(6 + d // 12):
            a, k = rng.uniform(0, math.tau), rng.uniform(0.2, 0.8)
            x, y = c + math.cos(a) * k * d / 2, c + math.sin(a) * k * d / 2
            pygame.draw.circle(coat, (178, 198, 222, 200), (int(x), int(y)), max(1, d // 18))
        pygame.draw.circle(coat, (200, 220, 245, 255), (c, c), d // 2, max(1, d // 30))
        return coat

    @staticmethod
    def _ice_ball(d):
        coat = blank(d + 8, d + 8)
        pygame.draw.circle(coat, (200, 232, 255, 110), (d // 2 + 4, d // 2 + 4), d // 2 + 2)
        pygame.draw.circle(coat, (240, 250, 255, 220), (d // 2 + 4, d // 2 + 4), d // 2 + 2, 2)
        return coat

    def draw_pickups(self, screen, powerups, ox, oy):
        """Power-up talismans bobbing on the court; they blink before they fade away."""
        t = self.app.fx.time
        for item in powerups.pickups:
            kind = POWERUPS[item["kind"]]
            tint = FAMILY_COLOURS[kind.family]
            alpha = min(1.0, item["age"] / 0.3)
            left = powerups.LIFETIME - item["age"]
            if left < 2.0 and int(left * 6) % 2:
                alpha *= 0.35
            x = item["x"] + ox
            y = item["y"] + oy + math.sin(t * 2.4 + item["phase"]) * 7
            level = max(1, round(alpha * 6))
            glow = self.art.glow(64, scaled(tint, .1 * level))
            screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
            coin = self.art.power_icon(2 * powerups.RADIUS, kind.key, kind.family)
            coin.set_alpha(int(255 * alpha))
            screen.blit(coin, coin.get_rect(center=(x, y)))
            coin.set_alpha(255, pygame.RLEACCEL)
            if self.app.hud.tab_held():               # Tab: name every talisman on the court
                font = self.fnt(0.021)
                label = self.art.text(kind.name, font, mix(tint, (255, 255, 255), .55))
                plate = label.get_rect(midtop=(x, y + powerups.RADIUS + 6)).inflate(18, 8)
                screen.blit(self.art.inset(plate.w, plate.h), plate)
                screen.blit(label, label.get_rect(center=plate.center))

    def draw_popups(self, screen, powerups):
        """The name of a power-up, rising and fading from where it was taken."""
        for text, x, y, age, tint in powerups.popups:
            k = age / 1.4
            surf = self.art.gilded(text, self.brush(0.04), top=mix(tint, (255, 255, 255), .6), bottom=tint, glow=None)
            surf.set_alpha(int(255 * min(1.0, (1 - k) * 2.5)))
            rect = surf.get_rect(center=(x, y - 40 - 70 * k))
            rect.clamp_ip(pygame.Rect(10, 140, BASE_W - 20, BASE_H - 150))
            screen.blit(surf, rect)
            surf.set_alpha(255, pygame.RLEACCEL)

    def draw_world(self, screen, game):
        W, H = BASE_W, BASE_H
        ox, oy = self._shake_offset()
        powerups = getattr(game, "powerups", None)
        open_court = bool(powerups) and powerups.wall_open()
        self.draw_arena(screen, ox, oy, game.wall_up, cord=not open_court)
        for obj in game.objects:
            if getattr(obj, "is_obstacle", False):
                self.draw_stone(screen, obj, ox, oy)
        night = powerups.lantern_level() if powerups and hasattr(powerups, "lantern_level") else 0.0
        if powerups:
            self.draw_portals(screen, powerups, ox, oy)
            if not night:
                self.draw_pickups(screen, powerups, ox, oy)
            self.draw_hops(screen, powerups, game.ball, ox, oy)

        for obj in game.objects:
            rect = pygame.Rect(int(obj.x0 + ox), int(obj.y0 + oy), int(obj.width), int(obj.height))
            if obj.is_ball:
                if getattr(obj, "stuck", None):
                    self.draw_goo(screen, obj, ox, oy)
                self.draw_ball(screen, obj, rect, ox, oy)
            elif obj.is_paddle:
                self.draw_paddle(screen, obj, rect)

        if powerups:
            self.draw_wind(screen, powerups)
            if night:
                self.draw_night(screen, game, night, ox, oy)
                self.draw_pickups(screen, powerups, ox, oy)     # talismans still glow in the dark
            self.draw_blasts(screen, powerups, ox, oy)
            self.draw_popups(screen, powerups)

        if getattr(game, "switch_warning", None) is not None:
            self.draw_switch_warning(screen, game)
        if getattr(game, "banter", None):
            self.draw_banter(screen, game.banter)

        if getattr(game, "message_text", ""):
            tint = getattr(game, "message_color", theme.WHITE)
            w, h = 680, 136
            m = self.art.PLAQUE_MARGIN
            screen.blit(self.art.plaque(w, h), (W // 2 - w // 2 - m, H // 2 - h // 2 - m))
            surf = self.art.gilded(game.message_text, self.brush(0.085), top=mix(tint, (255, 255, 255), .6),
                                   bottom=tint, glow=None)
            screen.blit(surf, surf.get_rect(center=(W // 2, H // 2)))

        if game.countdown is not None:
            self.draw_countdown(screen, game.countdown)
            self.draw_point_plaque(screen, game)

            # first serve, or just after a Chaos Switch: remind players who has which paddle
            if game.p1.score + game.p2.score == 0 or game.settings.switch_each_point:
                self._draw_controls_hint(screen, game)

        if getattr(game, "switch_flash", 0) > 0:
            self.draw_switch_banner(screen, game.switch_flash, game.switch_banner)
        if getattr(game, "live_banner", 0) > 0 and game.countdown is None:
            self.draw_live_banner(screen, game.live_banner)

    def draw_point_plaque(self, screen, game):
        """Above the serve countdown: which point this is, so a new round never looks like a replay."""
        number = game.p1.score + game.p2.score + 1
        text = "First point" if number == 1 else f"Point {number}"
        font = self.fnt(0.034)
        w = font.size(text)[0] + 80
        plate = pygame.Rect(0, 0, w, 58)
        plate.center = (BASE_W // 2, int(BASE_H * 0.27))
        screen.blit(self.art.inset(plate.w, plate.h), plate)
        self.text(screen, text, font, theme.GOLD_BRIGHT, center=plate.center)

    def draw_live_banner(self, screen, left):
        """Straight after a replay: back to the live match."""
        alpha = int(255 * min(1.0, left / 0.4, (1.8 - left) / 0.2 if left > 1.6 else 1.0))
        board = self.art.get(("live_banner",), self._live_banner)
        board.set_alpha(alpha)
        screen.blit(board, board.get_rect(center=(BASE_W // 2, int(BASE_H * 0.27))))
        board.set_alpha(255, pygame.RLEACCEL)

    def _live_banner(self):
        w, h = 560, 96
        m = self.art.PLAQUE_MARGIN
        surf = blank(w + 2 * m, h + 2 * m)
        surf.blit(self.art.plaque(w, h), (0, 0))
        dot_x = m + 48
        pygame.draw.circle(surf, (230, 40, 36), (dot_x, m + h // 2), 12)
        pygame.draw.circle(surf, (255, 150, 140), (dot_x - 3, m + h // 2 - 3), 4)
        words = self.art.gilded("LIVE  -  back to the match", self.fnt(0.036), glow=None)
        surf.blit(words, words.get_rect(midleft=(dot_x + 28, m + h // 2 - 2)))
        return surf

    def draw_stone(self, screen, stone, ox, oy):
        """A court stone, rising out of the ground when it arrives and sinking when it goes."""
        k = stone.visibility()
        if k <= 0:
            return
        w, h = int(stone.width), int(stone.height)
        sprite = self.art.stone(w, h, stone.style)
        x, y = int(stone.x0 + ox), int(stone.y0 + oy)
        if stone.speed:
            glow = self.art.glow(max(40, w), (70, 26, 16))
            screen.blit(glow, glow.get_rect(center=(x + w // 2, y + h // 2)), special_flags=ADD)
        shadow = self.art.get(("stone_shadow", w, h), self._stone_shadow, w, h)
        if k < 1:
            level = max(1, round(k * 10))           # in ten steps, so the faded copies can be kept
            sprite = self.art.get(("stone_fade", w, h, stone.style, level), self._faded, sprite, level / 10)
            shadow = None
            y += int((1 - k) * 24)
        if shadow:
            screen.blit(shadow, (x + 8, y + 12))
        screen.blit(sprite, (x, y))
        # Chipped by Spirit Fire or the Snowball: cracks spread as it weakens
        strength = getattr(stone, "strength", None)
        if strength is None:
            strength = getattr(stone, "hp", 1) / max(1, getattr(stone, "max_hp", 1))
        if strength < 0.99 and k > 0.3:
            level = min(3, max(1, round((1 - strength) * 3)))
            cracks = self.art.get(("cracks", w, h, level), self._cracks, w, h, level)
            screen.blit(cracks, (x, y))

    @staticmethod
    def _cracks(w, h, level):
        """Dark zig-zag cracks over a stone, more and longer the more it has been chipped."""
        surf = blank(w, h)
        rng = random.Random(w * 7919 + h * 31 + level)
        for _ in range(level * 2):
            x, y = rng.uniform(w * .2, w * .8), rng.uniform(h * .1, h * .3)
            points = [(x, y)]
            for _ in range(3 + level * 2):
                x = min(w - 2, max(2, x + rng.uniform(-w * .22, w * .22)))
                y = min(h - 2, y + rng.uniform(h * .05, h * .16))
                points.append((x, y))
            pygame.draw.lines(surf, (30, 24, 22, 230), False, points, 3)
            pygame.draw.lines(surf, (210, 196, 170, 90), False, [(px + 1, py + 1) for px, py in points], 1)
        return surf

    def draw_blasts(self, screen, powerups, ox, oy):
        """Firecracker: a flash, a shockwave ring racing out, and a second, slower one."""
        blasts = getattr(powerups, "blasts", [])
        if not blasts:
            return
        total = PowerUps.BLAST_TIME
        for x, y, age in blasts:
            k = min(1.0, age / total)
            cx, cy = int(x + ox), int(y + oy)
            if k < 0.3:
                flash = self.art.glow(int(260 * (1 - k)) // 4 * 4 + 40, scaled((255, 230, 160), 1 - k / 0.3))
                screen.blit(flash, flash.get_rect(center=(cx, cy)), special_flags=ADD)
            for speed, width, tint in ((PowerUps.BLAST_R * 1.25, 10, (255, 210, 120)), (PowerUps.BLAST_R * 0.8, 6, (255, 120, 60))):
                r = int(30 + speed * (1 - (1 - k) ** 2))
                fade = 1 - k
                if r > 4 and fade > 0.05:
                    ring = pygame.Surface((r * 2 + 24, r * 2 + 24), pygame.SRCALPHA)
                    pygame.draw.circle(ring, (*tint, int(220 * fade)), (r + 12, r + 12), r, max(2, int(width * fade)))
                    screen.blit(ring, ring.get_rect(center=(cx, cy)))

    @staticmethod
    def _stone_shadow(w, h):
        shadow = blank(w, h)
        pygame.draw.rect(shadow, (0, 0, 0, 110), (0, 0, w, h), border_radius=max(4, w // 3))
        return shadow

    @staticmethod
    def _faded(sprite, k):
        faded = sprite.copy()
        faded.fill((255, 255, 255, int(255 * k)), special_flags=pygame.BLEND_RGBA_MULT)
        return faded

    def draw_goo(self, screen, ball, ox, oy):
        """Sticky Goo: strands of goo stretch from the paddle's face as the ball peels away."""
        stuck = ball.stuck
        paddle = stuck["paddle"]
        k = 1 - stuck["left"] / stuck["total"]
        face = paddle.x1 if stuck["side"] > 0 else paddle.x0
        cx, cy = (ball.x0 + ball.x1) / 2 + ox, (ball.y0 + ball.y1) / 2 + oy
        r = ball.width / 2
        width = max(2, int(r * (0.9 - 0.7 * k)))
        for dy in (-0.55, 0.0, 0.55):
            start = (face + ox, cy + dy * r * 1.2)
            end = (cx - stuck["side"] * r * 0.6, cy + dy * r * 0.7)
            pygame.draw.line(screen, (150, 176, 40), start, end, width + 2)
            pygame.draw.line(screen, (204, 230, 80), start, end, width)
        # The aim: an arrow from the ball the way it will be slung (moving the paddle aims it)
        angle = PowerUps.sling_angle(paddle, stuck)
        dx, dy = stuck["side"] * math.cos(angle), math.sin(angle)
        tail = (cx + dx * (r + 10), cy + dy * (r + 10))
        tip = (cx + dx * (r + 70), cy + dy * (r + 70))
        pulse = 0.6 + 0.4 * math.sin(self.app.fx.time * 10)
        colour = (int(214 + 41 * pulse), int(236 + 19 * pulse), 120)
        pygame.draw.line(screen, (60, 70, 20), tail, tip, 7)
        pygame.draw.line(screen, colour, tail, tip, 4)
        for turn in (2.6, -2.6):
            back = (tip[0] + math.cos(math.atan2(dy, dx) + turn) * 16, tip[1] + math.sin(math.atan2(dy, dx) + turn) * 16)
            pygame.draw.line(screen, colour, tip, back, 4)

    def draw_hops(self, screen, powerups, ball, ox, oy):
        """Blink Ball: a fading ghost of the ball where it just was, and a spark trail to where it went."""
        sprite = self.art.ball(max(8, round(ball.width / 2) * 2))
        for x0, y0, x1, y1, age in powerups.hops:
            k = 1 - age / 0.35
            level = max(1, round(k * 5))
            glow = self.art.glow(max(16, int(ball.width)), scaled((90, 150, 220), level / 5))
            screen.blit(glow, glow.get_rect(center=(x0 + ox, y0 + oy)), special_flags=ADD)
            ghost = self.art.get(("ball_fade", sprite.get_width(), level), self._faded, sprite, level / 10)
            screen.blit(ghost, ghost.get_rect(center=(x0 + ox, y0 + oy)))
            for i in range(1, 5):
                t = i / 5
                dot = self.art.glow(6, scaled((150, 210, 255), k))
                screen.blit(dot, dot.get_rect(center=(x0 + (x1 - x0) * t + ox, y0 + (y1 - y0) * t + oy)),
                            special_flags=ADD)

    def draw_switch_warning(self, screen, game):
        """Two seconds of warning before Chaos Switch + swaps the paddles."""
        art = self.art
        W, H = BASE_W, BASE_H
        k = 1 - game.switch_warning / game.SWITCH_WARNING          # 0 to 1 as the swap nears
        pulse = .5 + .5 * math.sin(self.app.fx.time * (9 + 16 * k))

        sign = art.gilded("换", art.brush(250), thickness=0, top=(255, 226, 170), bottom=(214, 96, 40))
        sign.set_alpha(int(70 + 120 * pulse))
        screen.blit(sign, sign.get_rect(center=(W // 2, H // 2 - 40)))

        filled = min(3, int(k * 3) + 1)
        for i in range(3):
            centre = (W // 2 - 60 + i * 60, H // 2 + 110)
            pygame.draw.circle(screen, theme.INK, centre, 15)
            pygame.draw.circle(screen, theme.FLAME if i < filled else theme.GOLD_DARK, centre, 12)

        font = self.fnt(0.024)
        for paddle, other in ((game.p1, game.p2), (game.p2, game.p1)):
            rect = pygame.Rect(int(paddle.x0), int(paddle.y0), int(paddle.width), int(paddle.height))
            halo = art.paddle_glow(rect.w, rect.h, "red" if paddle.is_left else "blue")
            halo.set_alpha(int(255 * pulse))
            screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
            halo.set_alpha(255, pygame.RLEACCEL)

            # where this paddle is about to land
            target = (int((other.x0 + other.x1) / 2), int((other.y0 + other.y1) / 2))
            pygame.draw.line(screen, theme.FLAME, rect.center, target, 2)
            text = "Swapping places"
            tw = font.size(text)[0] + 30
            plate = pygame.Rect(0, 0, tw, 40)
            plate.midbottom = (rect.centerx, rect.top - 14)
            plate.clamp_ip(pygame.Rect(8, 8, W - 16, H - 16))
            screen.blit(art.inset(plate.w, plate.h), plate)
            self.text(screen, text, font, theme.FLAME, center=plate.center)

    def draw_switch_banner(self, screen, left, text="换 Switch!"):
        w, h = 520, 120
        m = self.art.PLAQUE_MARGIN
        y = int(BASE_H * 0.3)
        board = self.art.plaque(w, h)
        words = self.art.gilded(text, self.brush(0.075), glow=None)
        alpha = int(255 * min(1.0, left / 0.3))
        board.set_alpha(alpha)
        words.set_alpha(alpha)
        screen.blit(board, (BASE_W // 2 - w // 2 - m, y - h // 2 - m))
        screen.blit(words, words.get_rect(center=(BASE_W // 2, y)))
        board.set_alpha(255, pygame.RLEACCEL)
        words.set_alpha(255, pygame.RLEACCEL)

    def bubble(self, text):
        surf = self._bubbles.get(text)
        if surf is None:
            font = self.fnt(0.026)
            ghost = self.art.ghost(44)
            pad = 14
            w = ghost.get_width() + font.size(text)[0] + 3 * pad
            h = max(ghost.get_height(), font.get_height()) + 2 * pad
            surf = blank(w, h + 14)
            surf.blit(self.art.inset(w, h), (0, 0))
            pygame.draw.polygon(surf, (34, 14, 14), [(w // 2 - 12, h - 2), (w // 2 + 12, h - 2), (w // 2, h + 14)])
            surf.blit(ghost, ghost.get_rect(midleft=(pad, h // 2)))
            label = font.render(text, True, theme.GOLD_BRIGHT)
            surf.blit(label, label.get_rect(midleft=(2 * pad + ghost.get_width(), h // 2)))
            self._bubbles[text] = surf
        return surf

    def draw_banter(self, screen, banter):
        """The AI's quip after a point, in a speech bubble over its paddle."""
        text, paddle, left = banter
        surf = self.bubble(text)
        rect = surf.get_rect(midbottom=((paddle.x0 + paddle.x1) / 2, paddle.y0 - 10))
        rect.clamp_ip(pygame.Rect(8, 150, BASE_W - 16, BASE_H - 160))
        surf.set_alpha(int(255 * min(1.0, left / 0.3)))
        screen.blit(surf, rect)
        surf.set_alpha(255, pygame.RLEACCEL)

    def draw_countdown(self, screen, countdown):
        W, H = BASE_W, BASE_H
        v = countdown.shown_value
        beat = clamp01(countdown.remaining - (v - 1))       # 1 falling to 0 on each number

        mark = {3: "三", 2: "二", 1: "一"}.get(v)
        if mark:
            # the big faint character, its faintness baked in once
            sprite = self.art.get(("countdown_mark", mark), self._faint_mark, mark)
            screen.blit(sprite, sprite.get_rect(center=(W // 2, H // 2)))

        # the number swells and settles; its sizes come in 40 steps, each scaled only once
        text = "GO!" if v == 0 else str(v)
        step = round(40 * .55 * beat ** 3)
        scaled_digit = self.art.get(("countdown_digit", text, step), self._swollen_digit, text, step)
        screen.blit(scaled_digit, scaled_digit.get_rect(center=(W // 2, H // 2)))

    def _faint_mark(self, mark):
        sprite = self.art.gilded(mark, self.art.brush(420), thickness=0, top=(120, 30, 30), bottom=(70, 14, 18)).copy()
        sprite.fill((255, 255, 255, 170), special_flags=pygame.BLEND_RGBA_MULT)
        return sprite

    def _swollen_digit(self, text, step):
        digit = self.art.gilded(text, self.art.ui(230), thickness=6)
        k = 1 + step / 40
        return pygame.transform.smoothscale(digit, (int(digit.get_width() * k), int(digit.get_height() * k)))

    def _draw_controls_hint(self, screen, game):
        font = self.ui.fnt(0.032)
        pad = int(BASE_H * 0.015)
        for paddle, cx in ((game.p1, BASE_W * 0.25), (game.p2, BASE_W * 0.75)):
            text = "AI" if paddle.ai_enabled else paddle.controls_label
            tw, th = font.size(text)
            rect = pygame.Rect(0, 0, tw + 3 * pad, th + 2 * pad)
            rect.center = (int(cx), int(BASE_H * 0.74))
            screen.blit(self.art.inset(rect.w, rect.h), rect)
            self.text(screen, text, font, theme.GOLD_BRIGHT, center=rect.center)
        if game.settings.powerups and game.p1.score + game.p2.score == 0 and not ANDROID:   # (no Tab on a phone)
            font = self.fnt(0.024)
            text = "Hold Tab to see every power-up in play"
            plate = pygame.Rect(0, 0, font.size(text)[0] + 50, 50)
            plate.center = (BASE_W // 2, int(BASE_H * 0.84))
            screen.blit(self.art.inset(plate.w, plate.h), plate)
            self.text(screen, text, font, theme.PARCHMENT, center=plate.center)

    # ── Overlay ────────────────────────────────────────────────────────────────

    def draw_overlay(self, state, screen, *, title=None, header=None, buttons=None,
                     title_size=0.08, header_size=0.05, btn_size=0.045,
                     title_color=theme.GOLD_BRIGHT, dim=True, mark=None, toggles=None, tips=None,
                     jukebox=False):
        """Auto-sized panel: title, optional header (str or list of (text, colour)
        parts), optional toggles [(key, label, flag)] and a grid of (key, text, colour, hover) buttons."""
        ui = self.ui
        tips = tips or {}

        def build(s):
            items = []
            if title is not None:
                items.append(Title(title, ui.brush(title_size * 1.3, s), title_color))
            if header is not None:
                items.append(Text(header, ui.fnt(header_size, s)))
            if toggles:
                tf = ui.fnt(btn_size * 0.8, s)
                items.append(Stack([self.toggle(tf, key, label, flag, tips.get(key)) for key, label, flag in toggles],
                                   vertical=False, gap=int(BASE_W * 0.012 * s)))
            if buttons is not None:
                bf = ui.fnt(btn_size, s)
                cols = getattr(state, "ui_cols", len(buttons))
                nodes = [Button(key, text, bf, (c1, c2), tip=tips.get(key)) for key, text, c1, c2 in buttons]
                rows = [nodes[i:i + cols] for i in range(0, len(nodes), cols)]
                items.append(Grid(rows, gap_x=int(BASE_W * 0.015 * s), gap_y=int(ui.gap * s), uniform=True))
            if jukebox:
                jf, js = ui.fnt(0.03, s), ui.fnt(0.024, s)
                items.append(Stack([Label("Jukebox", ui.fnt(0.03, s)),
                                    *self.jukebox_controls(state, jf, js, int(BASE_W * 0.16 * s))],
                                   gap=int(ui.gap * 0.7 * s)))
            return Stack(items, gap=int(ui.gap * 1.6 * s))

        ui.overlay(state, screen, build, dim=dim, mark=mark)
