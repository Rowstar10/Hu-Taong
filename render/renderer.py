import math, random, pygame
from pygame import gfxdraw
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from config import BASE_W, BASE_H
from helpers import clamp, clamp01, lerp, reflect_in_range
from render import theme
from render.art import ADD, blank, mix, scaled, v_gradient
from core.settings import key_name
from core import net as netcode
from core.platform import ANDROID
from core.gamepad import LABELS as _PAD_LABELS


def gamepad_labels(family):
    return _PAD_LABELS[family]
from core import rooms
from game import courts
from game.powerups import BY_KEY as POWERUPS, FAMILY_COLOURS, FAMILY_NOTES, KINDS as POWERUP_KINDS, PowerUps
from render.ui.layout import Node, Space
from core.states.match_controls import in_match, match_rules
from render.ui.layout import (Stack, Grid, Text, Label, Title, Button, Toggle, CycleToggle, KeyButton,
                              Cycle, Slider, Slot, Space, TrackBar, Icon, Picture, TextField, Form)

# What each control does, shown when the mouse rests on it.  First line: the title.  Then one
# short line on what it does, and bullets for the details (see Tooltips for the markers).
TIPS = {
    # Main menu and the settings hub
    "play": "Play\nChoose your opponent, paddle and court, then start.\n~ Enter",
    "stats": "Stats\nYour lifetime record, and your saved replays.",
    "settings": "Settings\nYour controls, display, sound and UI; in a match, its rules too.",
    "prompt_quit": "Quit\nClose the game. Settings and stats are saved.\n~ Esc",
    "match": "Match\nThis match's rules: modes, points to win, the court, talismans, the ball and paddles, and the AI.\n"
             "• This match only, from the next serve: a new match starts from Match Setup's\n"
             "~ The same for both players: online, the host's",
    "gameplay": "Controls\nYour keys, a controller's buttons and stick, the mouse, and the emotes' buttons.",
    "display": "Display\nWindow, frame rate, background, dimming and effects.",
    "audio": "Audio\nVolume, sound effects and the jukebox.",
    "interface": "UI\nTooltips, the HUD, AI banter, replays and Auto-Pause.",
    "reset_all": "Reset All Settings\nEvery setting back to its default, Match Setup's rules too.\n• Your stats and replays are kept",
    "export_settings": "Export Settings\nSave every setting to a file, to keep or to take to another computer.\n"
                       "• Not your stats, nor your own server's login",
    "import_settings": "Import Settings\nLoad every setting from an exported file.\n~ They replace the settings here",

    # Match setup
    "opponent_ai": "Practice Mode\nYou play one paddle; the AI plays the other, or the far end is a wall.\n"
                   "• Every setting, mode and talisman works as usual\n"
                   "• Against the AI with goals on, it's a real match and counts towards your stats\n"
                   "• Against the wall or with goals off, it's practice: nothing counts",
    "opponent_human": "Multiplayer\nTwo players here, on one keyboard or with controllers.",
    "opponent_online": "Online\nPlay a friend over the internet: one of you hosts, the other joins with a code.",
    "toggle_friend_emotes": "Friend's Emotes\nOnline, your friend's quick emotes (Nice shot!, Oops...) show by "
                            "their side of the court.\n• Off: you don't see theirs; yours still go to them\n"
                            "~ Send your own with keys 1-5, or the controller buttons set in Controls > Emotes",
    "practice_wall": "Against a wall\nThe other end of the court is a wall: the ball always comes back.\n"
                     "• With goals on, it counts your misses; the match never ends\n"
                     "• No Soul Swap or Switch: there's no one to swap with\n• Doesn't count towards your stats",
    "practice_ai": "Against the AI\nThe AI plays the other paddle, at the AI Level set here (its style is in Match Settings).",
    "toggle_goals": "Goals\nON: the ends of the court are goals, as in a match.  OFF: both ends are walls, so the "
                    "ball always comes back and the rally never ends; no scores are shown, and nothing counts "
                    "towards your stats.",
    "start_match": "Start Match\nPlay with the settings chosen here and in Match Settings.\n~ Enter",

    # Gameplay
    "toggle_adaptive_ai": "Adaptive AI\nKeeps matches close.\n• Eases off a level for every 3 points it leads\n• Sharpens up when it's behind",
    "toggle_win_by_two": "Win by Two\nThe winner needs a two-point lead.",
    "ball_speed_slider": "Ball Speed\nHow fast the ball is served.\n• Hard hits speed it up, to about 4.5 times this",
    "pace_slider": "Game Pace\nSlows down or speeds up the whole match.\n• Ball, paddles, AI and Chaos timers together\n~ Turn it down if the ball is too quick to follow",
    "paddle_speed_slider": "Paddle Speed\nHow fast the paddles move.",
    "ball_diameter_slider": "Ball Size\nHow big the ball is.",
    "paddle_size_slider": "Paddle Size\nHow tall and wide the paddles are.",
    "randomise_all": "Randomise All\nRandom ball and paddle speeds and sizes.",
    "reset_ball_and_paddles": "Reset Ball & Paddles\nThe ball and paddle speeds and sizes back to their defaults.",
    "toggle_speed_cap": "Speed Cap\nA paddle can only pass on so much of its speed to the ball, so charging into "
                        "a slow ball can't make a shot nobody could reach.\n• The paddle gives way rather than "
                        "catching its own ball again\n~ Classic physics never passes on a paddle's speed: no "
                        "difference there",
    "open_powerups": "Choose Talismans\nSee what each talisman does, and choose which can appear.",
    "switch_to_modes": "Switch to Modes\nThe game modes, on a page like this one.",
    "switch_to_talismans": "Switch to Talismans\nBack to the talismans.",
    "open_ball_paddles": "Ball & Paddles\nThe ball's and paddles' sizes and speeds, the game's pace, and the physics.",
    "toggle_powerups": "Talismans\nTalismans appear on the court during a match.\n• Touch one with your paddle, or a ball you hit last\n~ Hold Tab in a match to see every talisman in play",
    "toggle_lantern_night": "Lantern Night\nThe court is always dark, lit only by lanterns round the paddles and the ball's glow.\n~ Off by default",
    "open_match_settings": "Match Settings\nThe rest of the rules: goals, the modes, talismans, the ball and paddles, "
                           "the AI's style and more.\n~ Kept for every new match",
    "toggle_curveball": "Curveball\nEvery hit bends the way the paddle was moving as it hit.\n"
                        "• Sweep up or down as you hit to curve the ball; a still paddle hits it straight\n"
                        "• The spin fades as it flies\n~ Off by default",
    "toggle_middle_wall": "Middle Wall\nEach paddle stays in its own half.\n• Off: paddles can roam the whole court",
    "cycle_effects": "Effects\nButterflies, embers, petals and bursts.\n• Reduced: half as many\n• Off: none, the calmest and fastest",

    # Display
    "cycle_res": "Resolution\nThe window's size.\n~ Press Apply to use it",
    "cycle_mode": "Window Mode\nWindowed, borderless or fullscreen.\n~ Press Apply to use it",
    "apply": "Apply\nUse the resolution and window mode above.",
    "cycle_max_fps": "Maximum FPS\nThe frame-rate cap.\n• Lower saves power, higher is smoother\n~ Starts at your screen's refresh rate",
    "toggle_show_fps": "Show FPS\nThe frame rate, in the bottom corner.",
    "toggle_show_ping": "Show Ping\nOnline, in a match: how long a message takes to reach your friend and come back, "
                        "in the top corner.\n• Green is quick, orange slower, red slow",
    "background_thumb": "Background\nChoose the picture behind the game.",
    "toggle_rotate_bg": "Rotate\nFade to a different background every so often.",
    "cycle_rotate_every": "Change Every\nHow long each background stays before Rotate fades to the next.",
    "cycle_parallax": "Parallax\nThe menu background drifts against the mouse, for depth.",
    "dim_slider": "Dim\nDarkens the background so the ball stands out.",
    "court_dim_slider": "Court Dim\nDarkens the picture behind a match, so the ball and paddles stand out.\n"
                        "• On top of the Dim Overlay",

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

    # UI (Settings' "interface" screen)
    "toggle_tooltips": "Tooltips\nThese notes, when you rest the mouse on a control.",
    "toggle_ai_banter": "AI Banter\nThe AI's quips after a point, in a speech bubble.",
    "toggle_screen_shake": "Screen Shake\nThe screen shakes when someone scores.",
    "toggle_ball_trail": "Ball Trail\nA fire trail behind the ball.",
    "toggle_auto_pause": "Auto-Pause\nPause the match if you click away from the game.",
    "toggle_mouse_steer": "Mouse Steering\nSteer your paddle with the mouse: it heads for the pointer, no faster "
                          "than the keys move it.\n• It takes over when you move the mouse in a match, and lets go "
                          "when you use the keys or a controller\n~ Off by default, so a nudged mouse never "
                          "moves your paddle",
    "cycle_mouse_side": "Mouse Plays\nWith two players here, the side the mouse steers.\n"
                        "• On your own (against the AI, or online) it steers your paddle",
    "open_emotes": "Emote Buttons\nThe controller button for each quick emote (keys 1-5 send them too).",
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
    """The panel under the tiles: the power-up the mouse is on, in full (or a hint), and your stats
    for it (1.9)."""
    LINES = 8

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
            hint = "Point at a talisman to see what it does.  Click its switch to turn it on or off."
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
        for line in kind.about.split("\n")[:self.LINES - 2]:
            ui.screen.blit(ui.text(self.body_font, line, theme.PARCHMENT), (x, y))
            y += self.line_h
        stats = ui.text(self.body_font, ui.app.stats.talisman_line(key), theme.GOLD)
        ui.screen.blit(stats, (x, r.bottom - self.pad - stats.get_height()))


class _ModeDetails(_PowerDetails):
    """The Modes view's panel (1.9): the game mode the mouse is on, in full (its tip), or a hint."""

    def draw(self, ui):
        key = getattr(ui.state, "pu_hover", None)
        ui.state.pu_hover = None                    # the tiles mark it again next frame, if still pointed at
        r = self.rect
        ui.screen.blit(ui.art.inset(r.w, r.h), r)
        renderer = ui.renderer
        if key not in renderer.MODE_TIPS:
            hint = "Point at a mode to see what it does.  Click its switch to turn it on or off."
            surf = ui.text(self.body_font, hint, theme.PARCHMENT)
            ui.screen.blit(surf, surf.get_rect(center=r.center))
            return
        icon = ui.art.power_icon(int(r.h * 0.42), renderer.MODE_ICONS[key], "Wild")
        ui.screen.blit(icon, icon.get_rect(midleft=(r.x + self.pad, r.centery)))
        x = r.x + self.pad * 2 + icon.get_width()
        y = r.y + self.pad
        lines = renderer.MODE_TIPS[key].split("\n")
        title = ui.text(self.title_font, lines[0], theme.GOLD_BRIGHT)
        note = ui.text(self.body_font, "   Game mode: all match long", FAMILY_COLOURS["Wild"])
        ui.screen.blit(title, (x, y))
        ui.screen.blit(note, (x + title.get_width(), y + (title.get_height() - note.get_height()) // 2))
        y += title.get_height() + int(8 * self.s)
        for line in lines[1:self.LINES - 1]:
            ui.screen.blit(ui.text(self.body_font, line, theme.PARCHMENT), (x, y))
            y += self.line_h


class _AchievementTile(Node):
    """One achievement on the Achievements screen: its seal, name, how to earn it and when it was."""

    def __init__(self, achievement, w, h, title_font, body_font, got):
        super().__init__()
        self.key, self.name, self.how, self.glyph, _ = achievement
        self.w, self.h = w, h
        self.title_font, self.body_font, self.got = title_font, body_font, got

    def draw(self, ui):
        r = self.rect
        earned = self.got.get(self.key)
        ui.screen.blit(ui.art.inset(r.w, r.h), r)
        size = int(r.h * 0.66)
        seal = ui.art.seal(size, bool(earned), self.glyph)
        ui.screen.blit(seal, seal.get_rect(midleft=(r.x + int(r.h * 0.15), r.centery)))
        x = r.x + int(r.h * 0.3) + seal.get_width()
        name = ui.text(self.title_font, self.name, theme.GOLD_BRIGHT if earned else theme.GRAY)
        how = ui.text(self.body_font, self.how + (f"   ({earned})" if earned else ""),
                      theme.PARCHMENT if earned else theme.OFF_TEXT)
        top = r.centery - (name.get_height() + how.get_height()) // 2
        ui.screen.blit(name, (x, top))
        ui.screen.blit(how, (x, top + name.get_height()))


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


def pad_tip(text):
    """A tip as a controller player sees it: no keyboard shortcuts, and controls are pressed."""
    lines = []
    for line in text.split("\n"):
        hint = line[2:] if line.startswith("~ ") else None
        if hint is not None and (hint.startswith(KEY_HINTS) or (len(hint) == 1 and hint.isupper())):
            continue
        lines.append(line.replace("Click", "Press").replace("click", "press"))
    return "\n".join(lines)


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
            self.offered = touch_tip(text) if ANDROID else pad_tip(text) if self.app.renderer.using_pad() else text

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
        self._paddle_tracks = {}                 # each side's paddle, its last few frames: deque of (x, y, time)

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

    # The settings pages, as rows (1.9, Rowan's 1.9 plan, phase 3, step 13b): a small heading over
    # each section, then each setting on a row of its own, its name in a right-aligned column and
    # its control beside it.  See render/ui/layout.py Form.

    def row_font(self, ui, s):
        return ui.fnt(0.027, s)

    def rows(self, ui, s, rows):
        """A column of a settings page: headings, and (name, control) rows that line up."""
        return Form(rows, self.row_font(ui, s), gap_x=int(BASE_W * 0.012 * s), gap_y=self.vgap(ui, s, 0.5),
                    section_gap=self.vgap(ui, s, 1.1))

    def heading(self, ui, s, text, sub=False):
        if sub:
            return Label(text, ui.fnt(0.025, s), flower=max(12, int(18 * s)))
        return Label(text, ui.fnt(0.03, s), flower=max(14, int(24 * s)))

    def switch(self, font, key, flag, tip=None):
        """A row's on/off: its seal, and ON or OFF (the row says what it is)."""
        return Toggle(key, lambda: "ON" if flag() else "OFF", font, flag, ["ON", "OFF"], tip=tip or TIPS.get(key))

    def column_gap(self, s, share=0.06):
        return int(BASE_W * share * s)

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

    def using_pad(self):
        """A controller is what's being used now (1.9): the prompts on screen name its buttons and
        stick.  The keyboard or mouse used since puts the keys back."""
        pads = getattr(self.app, "gamepads", None)
        return bool(pads is not None and pads.pads and pads.using == "pad")

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

    def draw_lacquer(self, screen, mouse_pos, rect, text, font, finish, fg=None, arrow=None):
        offset = self.draw_face(screen, mouse_pos, rect, finish)
        fg = fg or theme.LACQUER[finish][3]
        shadow = None if finish == "paper" else theme.INK
        cy = rect.centery - 3 + offset
        if arrow not in ("down", "up"):
            self.text(screen, text, font, fg, shadow, center=(rect.centerx, cy))
            return rect
        # A small triangle after the text, pointing down while what it opens is closed, up while
        # it's open (the font has no arrow characters, so it's drawn)
        from render.ui.layout import arrow_room
        room = arrow_room(font)
        tw = font.size(text)[0]
        left = rect.centerx - (tw + room) // 2
        self.text(screen, text, font, fg, shadow, center=(left + tw // 2, cy))
        size = max(6, int(font.get_height() * 0.3))
        ax = left + tw + room - size // 2 - 2
        ay = cy + 2
        down = arrow == "down"
        tip, half = size * 0.45, size * 0.55
        points = [(ax - half, ay - tip), (ax + half, ay - tip), (ax, ay + tip)] if down else \
                 [(ax - half, ay + tip), (ax + half, ay + tip), (ax, ay - tip)]
        if shadow:
            pygame.draw.polygon(screen, shadow, [(x + 2, y + 2) for x, y in points])
        pygame.draw.polygon(screen, fg, points)
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

        jobs.append(lambda: art.ball(self.app.settings.match.ball_diameter))
        for kind in POWERUPS.values():
            jobs.append(lambda k=kind: [art.power_icon(size, k.key, k.family) for size in self.ICON_SIZES])
        jobs.append(lambda: art.glow(48, (120, 54, 20)))

        # What a match builds the first time it's shown, which stuttered play (1.6 profiling):
        # each talisman on the court (32-38 ms the first time), its name rising as it's taken, the
        # serve countdown's swelling digits and faint marks, the Firecracker's BANG and the swap banners
        for kind in POWERUPS.values():
            tint = FAMILY_COLOURS[kind.family]
            jobs.append(lambda k=kind: art.power_icon(2 * PowerUps.RADIUS, k.key, k.family))
            jobs.append(lambda k=kind, tint=tint: art.gilded(k.name, self.brush(0.04), top=mix(tint, white, .6),
                                                             bottom=tint, glow=None))
        for tint in set(FAMILY_COLOURS.values()):            # the glow behind a talisman, as it fades in
            for level in range(1, 7):
                jobs.append(lambda tint=tint, level=level: art.glow(64, scaled(tint, .1 * level)))
        jobs.append(lambda: art.gilded("BANG!", self.brush(0.04), top=mix((255, 200, 80), white, .6),
                                       bottom=(255, 200, 80), glow=None))
        for n in range(1, 6):                                 # the Firecracker's 5-to-1 over the ball
            jobs.append(lambda n=n: self.cracker_digit(n))
        for R in range(self.PORTAL_STEP, PowerUps.PORTAL_R + 1, self.PORTAL_STEP):   # every size a portal shuts through
            jobs.append(lambda R=R: art.glow(int(R * 2.2) // 4 * 4, scaled((150, 100, 255), .7)))
        jobs.append(lambda: [self.portal_burst(PowerUps.PORTAL_R, level / 4) for level in range(1, 5)])
        jobs.append(lambda: [self.path_dot(level) for level in range(1, self.PATH_LEVELS + 1)])
        jobs.append(lambda: [self.hole_sprites(level) for level in range(1, self.HOLE_LEVELS + 1)])      # Black Hole (1.8)
        jobs.append(lambda: [art.glow(level * 14 + 16, scaled((255, 236, 210), level / 8)) for level in range(1, 9)])
        jobs.append(lambda: art.glow(5, (150, 104, 230)))
        for mark in "三二一":
            jobs.append(lambda mark=mark: art.get(("countdown_mark", mark), self._faint_mark, mark))
        for text in ("3", "2", "1", "GO!"):
            for step in range(round(40 * .55) + 1):          # every size draw_countdown swells it through
                jobs.append(lambda text=text, step=step:
                            art.get(("countdown_digit", text, step), self._swollen_digit, text, step))
        for text in ("换 Switch!", "换 Swap!"):
            jobs.append(lambda text=text: (art.plaque(520, 120), art.gilded(text, self.brush(0.075), glow=None)))
        return jobs

    def idle_jobs(self):
        """Every angle of the butterflies that burst out of goals, hits and swaps.  These are
        built a little at a time while the menus are up, so a match never waits on them."""
        art = self.art
        jobs = []
        g = self.app.settings.match

        # A paddle's flash as the ball hits it, at its own size (up to 14 ms the first time)
        w, h = max(4, int(g.paddle_width / 2) * 2), max(8, int(g.paddle_height / 4) * 4)
        for finish in ("red", "blue"):
            for level in range(1, 5):
                jobs.append(lambda finish=finish, level=level: art.paddle_flash(w, h, finish, level))
        jobs.append(self.warm_pause_screen)
        jobs.append(lambda: art.stone(self.PRACTICE_WALL, BASE_H, "pillar"))      # (Practice's wall, 1.9)
        # Each quick emote's bubble (1.9)
        from core.emotes import EMOTES
        for n in range(len(EMOTES)):
            jobs.append(lambda n=n: art.get(("emote_bubble", n), self.emote_bubble, n))
        # Each achievement's banner, ready for the moment it's earned (6 ms to make: a jolt mid-rally)
        from core.achievements import LIST as ACHIEVEMENTS
        for a in ACHIEVEMENTS:
            jobs.append(lambda key=a[0]: art.get(("achievement", key), self.achievement_banner, key))

        # Every size and colour of butterfly the game sends out, at every angle: goal bursts (64),
        # hits (48, 40), talismans taken (44), the Firecracker's bang (80), the swarm (88) and the
        # few drifting over a match (32)
        for size, tints in ((64, ("red", "blue")), (48, ("red", "blue")), (44, ("red", "blue")),
                            (40, ("red", "blue")), (80, ("red",)), (88, ("red",)), (32, ("red",))):
            for tint in tints:
                for frame in range(art.FLAP_FRAMES):
                    for turn in range(art.TURN_STEPS):
                        jobs.append(lambda size=size, frame=frame, turn=turn, tint=tint:
                                    art.butterfly(size, frame, turn, tint))

        # Lantern Night's pools of light
        for radius in (PowerUps.LANTERN_LIGHT, 150):          # round each paddle, and each ball (draw_night)
            jobs.append(lambda radius=radius: art.get(("night_hole", radius), self._night_hole, radius))

        # Every paddle and ball size the Chaos modes can reach, in the steps draw_paddle uses
        for h in range(g.paddle_height_min, g.paddle_height_max + 1, 4):
            t = (h - g.paddle_height_min) / g.paddle_height_range
            w = int((g.paddle_width_min + t * g.paddle_width_range) / 2) * 2
            for finish in ("red", "blue"):
                jobs.append(lambda w=w, h=h, finish=finish: (art.paddle(w, h, finish), art.paddle_glow(w, h, finish)))
            for finish in ("gold", "violet"):                 # a Boon's or a Curse's aura at that size
                jobs.append(lambda w=w, h=h, finish=finish: art.paddle_glow(w, h, finish))
        for d in range(g.ball_diameter_min, g.ball_diameter_max + 1, 2):
            jobs.append(lambda d=d: art.ball(d))

        # Tombstones, in the two sizes raise_tomb makes, rising and sinking in their ten steps
        for w, h in ((64, 124), (78, 148)):
            def tomb(w=w, h=h):
                sprite = art.stone(w, h, "tomb")
                art.get(("stone_shadow", w, h), self._stone_shadow, w, h)
                for level in range(1, 11):
                    art.get(("stone_fade", w, h, "tomb", level), self._faded, sprite, level / 10)
            jobs.append(tomb)
        jobs.append(lambda: art.glow(64, (70, 26, 16)))       # a drifting one's glow

        # Your paddle as Giant Paddle and Shrink Curse leave it, with the power-up auras
        w = max(4, int(g.paddle_width / 2) * 2)
        for k in (1.0, PowerUps.GIANT, PowerUps.SHRINK, PowerUps.GIANT * PowerUps.SHRINK):
            h = max(8, int(min(BASE_H * 0.62, g.paddle_height * k) / 4) * 4)
            for finish in ("red", "blue", "gold", "violet"):
                jobs.append(lambda w=w, h=h, finish=finish: art.paddle_glow(w, h, finish))
            for finish in ("red", "blue"):
                jobs.append(lambda w=w, h=h, finish=finish: art.paddle(w, h, finish))

        jobs.reverse()          # taken from the end, so the goal-burst butterflies come first
        return jobs

    def warm_pause_screen(self):
        """Draw the pause screen once, off-screen, over a stand-in match (its Red and Blue AI
        switches and all, so it's laid out as in a real one), so opening it the first time
        doesn't build its panel, buttons and lettering then.  Nothing is shown, and no tooltip
        is offered: the pointer is kept off it while it draws."""
        from types import SimpleNamespace
        from core.state_manager import StateManager
        app = self.app
        state = StateManager.create("pause", app)
        match = SimpleNamespace(net = None, p1 = SimpleNamespace(ai_enabled = False, color1 = "Red"),
                                p2 = SimpleNamespace(ai_enabled = True, color1 = "Blue"))
        state.game_state = SimpleNamespace(game = match)
        offered = self.tips.offered
        app.pointer = lambda: (-10000, -10000)
        try:
            state.draw(pygame.Surface((BASE_W, BASE_H)))
        finally:
            del app.pointer                     # back to App.pointer
            self.tips.offered = offered

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

        pads = self.app.gamepads
        hint = ("Tap Play Game to begin   ·   Back to quit" if ANDROID else
                f"{pads.label('a')} to play   ·   {pads.label('b')} to quit" if self.using_pad() else
                "Enter to play   ·   Esc to quit")
        self.text(screen, hint,
                  self.fnt(0.024, bold=False),
                  theme.GOLD, center=(cx, 944))

    # ── Match setup ────────────────────────────────────────────────────────────

    MODE_TIPS = {
        "chaos": "Shape Shift\nShakes up the ball's and paddles' sizes and speeds.\n"
                 "• Every point: new random sizes and speeds each point, fixed through the rally\n"
                 "• Constant drift: sizes keep drifting all match, both paddles together and the ball on its own; speeds stay put\n"
                 "~ Click to step through. The Shape Shift talisman doesn't turn up with Constant drift",
        "switch": "Soul Swap\nThe players take over each other's paddle, and the goal it defends.\n"
                  "• Your keys and your score stay yours; the paddles stay where they are\n"
                  "• Every point: after each point, paddle colour and all\n"
                  "• Mid-rally: at random moments both paddles glow, and the next hit swaps them; your colour stays yours\n"
                  "~ Click to step through. The Soul Swap talisman doesn't turn up mid-rally",
        "curveball": "Curveball\nEvery hit bends the way the paddle was moving, all match.\n"
                     "~ The Curveball talisman doesn't turn up",
        "lantern_night": "Lantern Night\nThe court is always dark, lit only by lanterns round the paddles and the ball's glow.\n"
                         "~ The Lantern Night talisman doesn't turn up",
        "twin_ball": "Twin Ball\nEvery point is played with two balls, Red's and Blue's.\n"
                     "• Red scores only with the red ball, in Blue's goal; Blue only with the blue one, in Red's\n"
                     "• A ball that reaches its own colour's goal just bounces off\n"
                     "~ The Twin Balls talisman doesn't turn up",
        "talisman_rush": "CHAOS\nA new talisman every 1.5 to 3 seconds, as many at once as come.\n"
                         "• Even with Talismans off: the ones switched on in Choose Talismans are used\n"
                         "• Spawn rate and Talismans at Once don't apply",
        "black_hole": "Black Hole\nA black hole drifts about mid-court all match, pulling the ball in and flinging it out.\n"
                      "• It grows with each ball it swallows, and stays that big point after point\n"
                      "• Grown five times, the next ball it swallows makes it collapse in on itself: the ball bursts\n"
                      "  out, heading for the goal it can score in, and mini black holes come and go till the point ends;\n"
                      "  a new one opens at the next serve\n"
                      "~ The Black Hole talisman doesn't turn up"}

    # The modes in the order they're shown; on the Modes page (1.9), each with its talisman's icon
    # (CHAOS has none: its own, a flurry of talismans) and the seals its switch steps through
    MODE_ORDER = ("chaos", "switch", "black_hole", "curveball", "lantern_night", "twin_ball", "talisman_rush")
    MODE_ICONS = {"chaos": "shape", "switch": "swap", "black_hole": "hole", "curveball": "curve",
                  "lantern_night": "lantern", "twin_ball": "twin", "talisman_rush": "rush"}
    MODE_SEALS = {"chaos": "关乱狂", "switch": "关换狂", "black_hole": "关渊", "curveball": "关旋",
                  "lantern_night": "关灯", "twin_ball": "关双", "talisman_rush": "关狂"}

    def modes_section(self, ui, s, font, m=None, columns=3, uniform=False):
        return self.section(ui, s, "Modes", self.modes_grid(ui, s, font, m, columns, uniform))

    def modes_grid(self, ui, s, font, m=None, columns=3, uniform=False):
        """The game modes, any of them together: an on/off for each, and for Chaos and Switch one
        button that cycles Off and each of their versions.  `m`: the rules shown, if not your own;
        `columns`: how many to a row (the online host's screen has room for fewer rows);
        `uniform`: all one width, a tidy block (1.9, where there's room).  A short last row is
        centred."""
        m = m or self.app.settings.match
        gap = int(BASE_W * 0.012 * s)

        def mode(key):
            return self.toggle(font, f"toggle_mode_{key}", m.MODE_NAMES[key], lambda: getattr(m, "mode_" + key),
                               tip=self.MODE_TIPS[key])

        def cycled(key, versions, glyphs):
            name = m.MODE_NAMES[key]
            texts = [f"{name}: OFF"] + [f"{name}: {v}" for v in versions]      # (OFF in capitals, as every switch: 1.9)
            level = lambda: (getattr(m, "mode_" + key) and getattr(m, key + "_timing") + 1) or 0
            return CycleToggle(f"cycle_mode_{key}", texts, font, level, glyphs, tip=self.MODE_TIPS[key])

        buttons = [cycled("chaos", m.CHAOS_TIMINGS, "关乱狂"), cycled("switch", m.SWITCH_TIMINGS, "关换狂"),
                   mode("black_hole"), mode("curveball"), mode("lantern_night"), mode("twin_ball"),
                   mode("talisman_rush")]
        if uniform:
            widest = [t for b in buttons for t in (getattr(b, "samples", None) or b.texts)]
            for b in buttons:
                b.samples = widest
        return Grid([buttons[i:i + columns] for i in range(0, len(buttons), columns)],
                    gap_x=int(BASE_W * 0.02 * s), gap_y=self.vgap(ui, s, 0.6))

    def draw_match_setup_menu(self, state, screen):
        ui = self.ui
        g = self.app.settings.match
        red_keys = self.app.settings.gameplay.keys_label("p1")
        blue_keys = self.app.settings.gameplay.keys_label("p2")
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

            # (Mode and Opponent, as in Match settings' Players: Opponent and Against till Rowan
            # renamed them, 1.9)
            # (Online on a row of its own under the other two, between them: Rowan, 1.9.  It went back
            # beside them for a while, to make room)
            opponent = self.section(ui, s, "Mode", Grid([
                [choice("opponent_ai",     "Practice Mode", lambda: g.vs_ai),       # (Rowan, 1.9: vs AI, then
                 choice("opponent_human",  "Multiplayer",   lambda: not g.vs_ai)],  # Practice vs AI; vs Human)
                [choice("opponent_online", "Online",        lambda: False, (theme.BLUE, theme.BLUE_HOVER))]],
                gap_x=gap, gap_y=self.vgap(ui, s, 0.6), uniform=True))

            vs_ai = lambda: g.vs_ai
            paddle = self.section(ui, s, "Your Paddle", Stack([
                choice("side_red",  "Red",  lambda: not g.play_as_blue, (theme.RED,  theme.RED_HOVER),  vs_ai),
                choice("side_blue", "Blue", lambda: g.play_as_blue,     (theme.BLUE, theme.BLUE_HOVER), vs_ai)],
                vertical=False, gap=gap, uniform=True))

            def summary():
                # (what each side plays with, as you're playing now: worked out afresh each frame, 1.9;
                # one line for each side, so the block stays narrow enough for the court beside it)
                red, blue = self.setup_controls(*(self.app.settings.gameplay.keys_label(p) for p in ("p1", "p2")))
                if not g.vs_ai:
                    return f"Red: {red}", f"Blue: {blue}"
                me, ai = ("Blue", "Red") if g.play_as_blue else ("Red", "Blue")
                keys = blue if g.play_as_blue else red
                if g.vs_wall:
                    return f"You: {me} ({keys})", f"{ai}'s end: a wall"
                return f"You: {me} ({keys})", f"AI: {ai}"
            red_keys, blue_keys = (self.app.settings.gameplay.keys_label(p) for p in ("p1", "p2"))
            samples = [f"You: Blue ({blue_keys} or mouse)", f"You: Red ({red_keys} or mouse)", "Red's end: a wall",
                       f"Red: {red_keys} or mouse", f"Blue: {blue_keys} or mouse", "Red: Pad 1, right stick",
                       "Blue: Pad 2, right stick", "You: Blue (Either stick)"]
            caption = Stack([Text(lambda: summary()[0], sm, theme.PARCHMENT, samples=samples),
                             Text(lambda: summary()[1], sm, theme.PARCHMENT, samples=samples)], gap=int(2 * s))


            names = g.court_options
            court_tip = lambda: self.court_tip(g.court)
            # (its description wrapped under the picture, to keep the court narrow beside the choices: 1.9)
            wrapped = [self.wrap_words(sm, self.court_about(i), int(424 * s)) for i in range(len(names))]
            lines = max(len(w) for w in wrapped)
            about = [Text(lambda i=i: (wrapped[g.court] + [""] * lines)[i], sm, theme.PARCHMENT,
                          samples=[line for w in wrapped for line in w]) for i in range(lines)]
            court = self.section(ui, s, "Court",
                                 Cycle("cycle_court", lambda: names[g.court], f, names, tip=court_tip),
                                 Picture(int(384 * s), int(216 * s), lambda screen, rect: self.draw_court_preview(screen, rect, g.court),
                                         tip=court_tip),
                                 Stack(about, gap=int(2 * s)))
            against = self.section(ui, s, "Opponent", Stack([
                choice("practice_ai",   "AI",   lambda: not g.vs_wall, enabled=vs_ai),
                choice("practice_wall", "Wall", lambda: g.vs_wall,     enabled=vs_ai)],
                vertical=False, gap=gap, uniform=True))

            # The rules most matches change (Rowan, 1.9): the rest (Goals, the modes, talismans...)
            # are in Match Settings
            levels, win_texts, styles = list(g.ai_difficulties), self.win_texts(g), list(g.ai_styles)
            both = levels + win_texts + styles              # (the boxes one width)
            ai_on, win_on = self.setup_ai_on(g), self.setup_win_on(g)
            ai_col = lambda: self.ai_level_colour(g) if ai_on() else theme.GRAY
            win_col = lambda: (theme.GRAY if not win_on() else
                               theme.FLAME if g.winning_scores[g.winning_score_index] == "Endless Mode" else theme.PARCHMENT)
            points = self.section(ui, s, "Points to Win", Cycle(
                "cycle_win_score", lambda: win_texts[g.winning_score_index], f, both, win_col,
                tip=lambda: self.win_tip(g, None if win_on() else
                                         "Goals are off (Match Settings): nobody scores" if not g.scoring else
                                         "Against the wall the match never ends")))
            # Choose Talismans and Choose Modes under Points to Win (Rowan, 1.9): two clicks quicker
            # than through Match Settings, to what changes a match most after the rest here
            points = Stack([points, self.choosers(ui, s, ui.fnt(0.026, s), ui.fnt(0.024, s), g)],
                           gap=self.vgap(ui, s, 0.7))
            # The AI's level and style under one heading, one just under the other (Rowan, 1.9),
            # greyed out where there's no AI.  (Adaptive AI was under them for a while: it's in Match
            # Settings)
            ai = self.section(ui, s, "AI Level / Style", Stack([
                Cycle("cycle_ai", lambda: levels[g.ai_difficulty], f, both, ai_col,
                      tip=lambda: self.ai_level_tip(g, None if ai_on() else "Practice Mode against the AI only")),
                Cycle("cycle_ai_style", lambda: styles[g.ai_style], f, both,
                      lambda: theme.PARCHMENT if ai_on() else theme.GRAY,
                      tip=lambda: options_tip("AI Style", "What the AI tries to do.",
                                              [(name, STYLE_TIPS[name]) for name in g.ai_styles], g.ai_style,
                                              None if ai_on() else "Practice Mode against the AI only"))],
                gap=self.vgap(ui, s, 0.35)))
            # (Points to Win under Your Paddle and the AI under Against, which it goes with; the line
            # saying who plays with what under them)
            choices = Grid([[paddle, against], [points, ai]], gap_x=int(BASE_W * 0.04 * s),
                           gap_y=self.vgap(ui, s, 1.4))
            left = Stack([opponent, choices, caption], gap=self.vgap(ui, s, 1.4))
            # The choices, and the court on their right, the two centred together (Rowan, 1.9: it was
            # on their left for a while).  (Match Settings and Start Match: the footer.)
            return Stack([left, court], vertical=False, gap=int(BASE_W * 0.04 * s))

        ui.screen_menu(state, screen, build, title="对局 Match Setup", mark="战")

        # Start Match in the middle and Match Settings at the bottom right, level with Back at the
        # bottom left, one width (Rowan, after 1.9's release: "the back button to swap with match
        # settings"; till then Match Settings was at the left, Back in the middle, Start Match right)
        font = self.fnt(0.04)
        w = max(280, max(font.size(t)[0] for t in ("Match Settings", "Start Match")) + 2 * self._gx)
        mouse = self.mouse()
        for key, text, colour, x in (("start_match", "Start Match", theme.ORANGE, BASE_W // 2),
                                     ("open_match_settings", "Match Settings", theme.BLUE, ui.PANEL.right - w // 2)):
            rect = self.draw_button(screen, mouse, font, text, x, ui.FOOTER_Y, colour, width=w)
            self.tips.offer(rect, TIPS[key])
            state.ui_hitboxes[key] = rect

    @staticmethod
    def wrap_words(font, text, width):
        """`text` in lines no wider than `width` (as near as whole words allow)."""
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if line and font.size(trial)[0] > width:
                lines.append(line)
                line = word
            else:
                line = trial
        return lines + [line]

    def setup_controls(self, red, blue):
        """What Match Setup says each side plays with (1.9), given each side's keys: what you're
        using now.  On your own, the keys (and the mouse, if Controls has it steering) or, while
        you're using a controller, the stick it steers with.  Two players: the side each controller
        plays shows its stick, and the mouse's side its keys "or mouse"."""
        g, pads, controls = self.app.settings.match, self.app.gamepads, self.app.settings.gameplay
        mouse = bool(controls.mouse_steer) and not ANDROID
        order = pads.order()
        if g.vs_ai:
            if self.using_pad():
                mine = pads.stick_label()
            else:
                mine = (blue if g.play_as_blue else red) + (" or mouse" if mouse else "")
            return (red, mine) if g.play_as_blue else (mine, blue)
        sides = [red, blue]
        if mouse:
            sides[controls.mouse_side] += " or mouse"
        if order:
            first = controls.pad_first
            sides[first] = pads.side_label(order[:1])
            if len(order) > 1:
                sides[1 - first] = pads.side_label(order[1:2])
        return sides[0], sides[1]

    # Match Setup's AI Level and Points to Win (1.9), greyed out where they don't count: the same
    # rules as its clicks (core/states/match_setup_state.py)

    @staticmethod
    def setup_ai_on(g):
        return lambda: g.vs_ai and not g.vs_wall

    @staticmethod
    def setup_win_on(g):
        return lambda: g.scoring and not (g.vs_ai and g.vs_wall)

    AI_LEVEL_NOTES = ("slow to react, often misreads the ball", "reacts late and rarely aims",
                      "a fair match", "quick, aims its returns", "reads everything; rarely misses")

    def ai_level_tip(self, g, hint=None):
        return options_tip("AI Level", "How quickly the AI reacts and how well it reads the ball.",
                           list(zip(g.ai_difficulties, self.AI_LEVEL_NOTES)), g.ai_difficulty, hint)

    @staticmethod
    def ai_level_colour(g):
        if g.ai_difficulty == 0:
            return theme.GREEN
        return theme.PARCHMENT if g.ai_difficulty < len(g.ai_difficulties) - 1 else theme.CRIMSON_BRIGHT

    @staticmethod
    def win_texts(g):
        return ["Endless Mode" if v == "Endless Mode" else f"First to {v}" for v in g.winning_scores]

    def win_tip(self, g, hint=None):
        # (every option, the one in use marked, as the other tips: Rowan, 1.9)
        return options_tip("Points to Win", "The score that wins the match.",
                           [(text, "it never ends" if text == "Endless Mode" else "") for text in self.win_texts(g)],
                           g.winning_score_index, hint or "With Win by Two on, the winner also needs a two-point lead")

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
        g = self.app.settings.match

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
                            "• The match uses your Match settings, and you pick the modes there")
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
                    Button("host_blue", "Blue", sm, blue, tip="Blue\nYou play the right paddle, your friend Red."),
                    Space(int(BASE_W * 0.02 * s)),
                    Toggle("toggle_goals", lambda: "Goals: ON" if g.scoring else "Goals: OFF", sm,      # (1.9)
                           lambda: g.scoring, ["Goals: ON", "Goals: OFF"], tip=TIPS["toggle_goals"])],
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
                    self.modes_section(ui, s, sm, columns=4),
                    Text(lambda: net.settings_summary(modes=False) if net else "", ty, theme.GOLD,
                         samples=["First to 21  -  Court: Narrow Pass  -  Talismans off"]),
                    Stack([Button("online_settings", "Match Settings", sm, (theme.BLUE, theme.BLUE_HOVER),
                                  tip=TIPS["open_match_settings"]),
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
                          samples=["First to 21  -  Court: Narrow Pass  -  Talismans off  -  Shape Shift: Constant drift  -  Soul Swap: Mid-rally  -  3 more modes  -  You play Blue"])
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
                                      samples=["First to 21  -  Court: Narrow Pass  -  Talismans off  -  Shape Shift: Constant drift  -  Soul Swap: Mid-rally  -  3 more modes"],
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

    def draw_card(self, state, screen, mouse_pos, key, x, mark, label, finish, w=360):
        h = 540
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

        rect = pygame.Rect(0, 0, min(300, w - 40), 76)
        rect.center = (x + w // 2, y + h - 104)
        self.draw_lacquer(screen, mouse_pos if hovered else (-1, -1), rect, label, self.fnt(0.042), finish)
        state.ui_hitboxes[key] = hit
        self.tips.offer(hit, TIPS[key])

    def draw_settings_menu(self, state, screen):
        mouse_pos = self.mouse()
        ui = self.ui
        self.draw_plaque(screen, "设置 Settings", ui.PANEL.top)

        # The match's rules first, then your own settings.  The Match card only in a match (Rowan,
        # 1.9: the rules belong with a match), for that match: a new match's are on Match Setup (and
        # the hosting screen).  Online the host's rules are the match's, so the friend who joined
        # has none
        net = self.app.net
        cards = (("match", "战", "Match", "jade"), ("display", "画", "Display", "amber"),
                 ("audio", "音", "Audio", "azure"), ("interface", "界", "UI", "crimson"),
                 ("gameplay", "控", "Controls", "ink"))          # (Controls after UI: Rowan, 1.9)
        # (nor opened by Match settings' More Settings: your own settings only, as from the main menu)
        if not in_match(self.app) or (net is not None and getattr(net, "role", None) == "guest") or \
                getattr(state, "general", False):
            cards = cards[1:]
        w, gap = 300, 34
        left = (BASE_W - (len(cards) * w + (len(cards) - 1) * gap)) // 2
        for i, (key, mark, label, finish) in enumerate(cards):
            self.draw_card(state, screen, mouse_pos, key, left + i * (w + gap), mark, label, finish, w=w)

        # Back at the bottom left, Export and Import in the middle, Reset All at the right (Rowan, after
        # 1.9's release: Back was in the middle, Export and Import at the left)
        back_rect = self.draw_button(screen, mouse_pos, self.fnt(0.04), "Back",
                                     ui.PANEL.left + 140, ui.FOOTER_Y, theme.RED, width=280)
        font = self.fnt(0.034)
        text = "Reset All Settings"
        w = font.size(text)[0] + 2 * self._gx
        reset_rect = self.draw_button(screen, mouse_pos, font, text, ui.PANEL.right - w // 2,
                                      ui.FOOTER_Y, theme.WHITE, width=w)
        self.tips.offer(reset_rect, TIPS["reset_all"])

        # Export and import every setting (1.9)
        pair = (("export_settings", "Export", theme.GREEN), ("import_settings", "Import", theme.BLUE))
        widths = [font.size(text)[0] + 2 * self._gx for _, text, _ in pair]
        x = (BASE_W - sum(widths) - 24) // 2
        for (key, text, colour), w in zip(pair, widths):
            rect = self.draw_button(screen, mouse_pos, font, text, x + w // 2, ui.FOOTER_Y, colour, width=w)
            self.tips.offer(rect, TIPS[key])
            state.ui_hitboxes[key] = rect
            x += w + 24

        state.ui_hitboxes.update(reset_all=reset_rect, back=back_rect)

    # ── Gameplay settings ──────────────────────────────────────────────────────

    BIG_SWITCH_SAMPLES = [f"{name}: {state}" for name in ("Win by Two", "Goals", "Middle Wall", "Adaptive AI",
                                                          "Talismans") for state in ("ON", "OFF")]

    def draw_match_settings_menu(self, state, screen):
        """Match settings: the rules of a match, the same for both players (online, only the host
        has it).  1.9: two rows of three sections (Rowan's layout), the on/offs whole buttons, and the
        modes behind Choose Modes, so it all fits without scrolling (it scrolls only if it must);
        from the pause menu, the note that changes come in at the next serve stays at the top."""
        ui = self.ui
        g = match_rules(self.app)         # (mid-match, this match's own: 1.9)

        def build(s):
            f, ty = self.row_font(ui, s), ui.fnt(0.022, s)
            win_texts = self.win_texts(g)
            win_col = lambda: theme.FLAME if g.winning_scores[g.winning_score_index] == "Endless Mode" else theme.PARCHMENT
            win_tip = lambda: self.win_tip(g)
            seconds = [f"{n} s" for n in g.countdown_options]
            countdown_tip = lambda: options_tip("Countdown", "How long the countdown before each serve lasts.",
                                                [(f"{n} second{'s' if n != 1 else ''}", "") for n in g.countdown_options],
                                                g.countdown)
            levels, styles = list(g.ai_difficulties), list(g.ai_styles)
            ai_col = lambda: self.ai_level_colour(g)
            ai_tip = lambda: self.ai_level_tip(g)
            style_tip = lambda: options_tip("AI Style", "What the AI tries to do.",
                                            [(name, STYLE_TIPS[name]) for name in g.ai_styles], g.ai_style)
            names = g.court_options
            court_tip = lambda: self.court_tip(g.court)

            sf = ui.fnt(0.022, s)       # (the whole-button switches and the Choose buttons: smaller, to fit)

            def big_switch(key, name, flag):
                # One whole button reading its name and ON or OFF (Rowan, 1.9: not a name beside a switch)
                button = self.toggle(sf, key, name, flag)
                button.samples = self.BIG_SWITCH_SAMPLES
                return button

            players = self.player_rows(ui, s, f, g)         # (mid-match only, and not online)
            court = self.rows(ui, s, [
                self.heading(ui, s, "Court"),
                ("Court", Cycle("cycle_court", lambda: names[g.court], f, names, tip=court_tip)),
                Picture(int(320 * s), int(180 * s),
                        lambda screen, rect: self.draw_court_preview(screen, rect, g.court), tip=court_tip)])
            # Win by Two, Goals and Middle Wall as a 2 by 2 block, the fourth left empty (Rowan)
            switches = [big_switch("toggle_win_by_two", "Win by Two", lambda: g.win_by_two),
                        big_switch("toggle_goals", "Goals", lambda: g.scoring),      # (any match, online too: 1.9)
                        big_switch("toggle_middle_wall", "Middle Wall", lambda: g.middle_wall)]
            rules = self.rows(ui, s, [
                self.heading(ui, s, "Match Rules"),
                ("Points to Win", Cycle("cycle_win_score", lambda: win_texts[g.winning_score_index], f, win_texts,
                                        win_col, tip=win_tip)),
                ("Countdown", Cycle("cycle_countdown", lambda: seconds[g.countdown], f, seconds, tip=countdown_tip)),
                ("", Grid([switches[:2], switches[2:]], gap_x=int(BASE_W * 0.012 * s), gap_y=self.vgap(ui, s, 0.6)))])
            ai = self.rows(ui, s, [
                self.heading(ui, s, "AI"),
                ("Level", Cycle("cycle_ai", lambda: levels[g.ai_difficulty], f, levels, ai_col, tip=ai_tip)),
                ("Style", Cycle("cycle_ai_style", lambda: styles[g.ai_style], f, styles, tip=style_tip)),
                ("", big_switch("toggle_adaptive_ai", "Adaptive AI", lambda: g.adaptive_ai))])

            rates = list(g.powerup_rate_options)
            rate_tip = lambda: options_tip("Spawn Rate", "How often a new talisman appears.",
                                           [("Rare", "every 14-22 s"), ("Normal", "every 8-14 s"),
                                            ("Frequent", "every 4-8 s")],
                                           g.powerup_rate, "CHAOS brings one every 1.5-3 s, whatever this is set to")
            at_once = [str(n) for n in g.at_once_options]
            at_once_tip = lambda: options_tip(
                "Talismans at Once", "How many talismans can be in play at once: their effects, and any waiting "
                "on the court.  A new one only turns up while there's room.",
                [(str(n), None) for n in g.at_once_options], g.talismans_at_once,
                "Safety Teleport, Double or Nothing, Lantern Night and Open Court don't count, nor do game "
                "modes.  CHAOS lifts the limit")

            # Talismans and the game modes together, with Choose Talismans and Choose Modes side by
            # side (Rowan, 1.9; the modes were a block of buttons here before)
            talismans = self.rows(ui, s, [
                self.heading(ui, s, "Talismans & Modes"),
                ("", big_switch("toggle_powerups", "Talismans", lambda: g.powerups)),     # (Power-Ups till 1.9)
                ("Spawn Rate", Cycle("cycle_powerup_rate", lambda: rates[g.powerup_rate], f, rates, tip=rate_tip)),
                ("At Once", Cycle("cycle_at_once", lambda: at_once[g.talismans_at_once], f, at_once, tip=at_once_tip)),
                ("", self.choosers(ui, s, sf, ty, g))])
            ball_paddles = self.rows(ui, s, [
                self.heading(ui, s, "Ball & Paddles"),
                Button("open_ball_paddles", "Ball & Paddles", f, (theme.GREEN, theme.GREEN_HOVER),
                       tip=TIPS["open_ball_paddles"]),
                Text(lambda: f"Ball {int(g.ball_diameter)} px, speed {int(g.ball_speed)}", ty, theme.PARCHMENT,
                     samples=["Ball 100 px, speed 800"]),
                Text(lambda: f"Paddles {int(g.paddle_height)} x {int(g.paddle_width)}, speed {int(g.paddle_speed)}",
                     ty, theme.PARCHMENT, samples=["Paddles 300 x 60, speed 2000"]),
                Text(lambda: f"Pace {g.pace:.2f}x   -   Physics: {g.PHYSICS[g.physics]}", ty, theme.PARCHMENT,
                     samples=[f"Pace 1.50x   -   Physics: {p}" for p in g.PHYSICS]),
                Text(lambda: f"Speed Cap {'on' if g.speed_cap else 'off'}", ty, theme.PARCHMENT,
                     samples=["Speed Cap off"])])
            # Two rows of three (Rowan, 1.9): Players, Court and Match Rules; AI, Talismans & Modes and
            # Ball & Paddles.  Without Players (from Match Setup, or online) AI takes its place
            if players:
                rows = [[self.rows(ui, s, players), court, rules], [ai, talismans, ball_paddles]]
            else:
                rows = [[ai, court, rules], [Space(), talismans, ball_paddles]]
            return Grid(rows, gap_x=self.column_gap(s, 0.015), gap_y=self.vgap(ui, s, 1.6))

        pinned = (lambda s: Text(state.note, self.row_font(ui, s), theme.FLAME)) if state.note else None
        # More Settings in the footer's middle: your own settings (Display, Audio, UI, Controls), as
        # from the main menu (Rowan, after 1.9's release)
        more = ("more_settings", "More Settings", (theme.ORANGE, theme.ORANGE_HOVER),
                "More Settings\nYour own settings: Display, Audio, UI and Controls.")
        ui.screen_menu(state, screen, build, title="对局 Match", mark="战", reset="Reset to Default",
                       pinned=pinned, scroll=True, middle=[more])

    OPPONENTS = ["Practice Mode", "Multiplayer"]

    def player_rows(self, ui, s, font, g):
        """Match settings' Players (1.9, Rowan): Match Setup's choices.  Mid-match (from Pause) they
        change this match from its next serve: a second player can take over the AI's paddle, or you
        the other paddle, the wall can come or go, and the goals close or open.  Only mid-match:
        opened from Match Setup, they're on the screen behind it.  Not online: there, your friend
        is the other player."""
        if self.app.net is not None or not in_match(self.app):
            return []
        practice = lambda: theme.PARCHMENT if g.vs_ai else theme.GRAY
        side_col = lambda: (theme.GRAY if not g.vs_ai else (112, 162, 255) if g.play_as_blue else (255, 112, 92))
        sides, against = ["Red", "Blue"], ["AI", "Wall"]
        only = "\n~ Practice Mode only: in Multiplayer, two players play here"
        return [
            self.heading(ui, s, "Players"),
            # (Mode and Opponent: Opponent and Against till Rowan renamed them, 1.9)
            ("Mode", Cycle("cycle_opponent", lambda: self.OPPONENTS[0 if g.vs_ai else 1], font, self.OPPONENTS,
                               tip=lambda: options_tip("Mode", "Who plays the other paddle.",
                                                       [("Practice Mode", "the AI, or a wall"),
                                                        ("Multiplayer", "a second player here: mid-match, they "
                                                                        "take over the AI's paddle")],
                                                       0 if g.vs_ai else 1))),
            ("Opponent", Cycle("cycle_against", lambda: against[1 if g.vs_wall else 0], font, against, practice,
                              tip=lambda: options_tip("Opponent", "What's at the other end.",
                                                      [("AI", "the AI plays the other paddle"),
                                                       ("Wall", "the far end is a wall: the ball always comes back")],
                                                      1 if g.vs_wall else 0) + only)),
            ("Your Paddle", Cycle("cycle_your_paddle", lambda: sides[1 if g.play_as_blue else 0], font, sides, side_col,
                                  tip="Your Paddle\nThe paddle you play, with its keys (Red: the first set, Blue: the "
                                      "second); the AI or the wall has the other." + only))]

    def choosers(self, ui, s, font, small, g):
        """Match settings' Choose Talismans and Choose Modes, side by side, one width, each with how
        many are on under it (Rowan, 1.9).  Both open the Talismans page, each on its own view."""
        labels = ["Choose Talismans", "Choose Modes"]
        colours = (theme.ORANGE, theme.ORANGE_HOVER)
        talismans = Button("open_powerups", labels[0], font, colours, samples=labels, tip=TIPS["open_powerups"])
        modes = Button("open_modes", labels[1], font, colours, samples=labels, tip=lambda: self.modes_tip(g))
        n, k = len(POWERUP_KINDS), len(g.MODES)
        counts = [Text(lambda: f"{sum(getattr(g, 'pu_' + kind.key) for kind in POWERUP_KINDS)} of {n} on", small,
                       theme.PARCHMENT, samples=[f"{n} of {n} on"]),
                  Text(lambda: f"{len(g.modes_on())} of {k} on", small, theme.PARCHMENT, samples=[f"{k} of {k} on"])]
        return Grid([[talismans, modes], counts], gap_x=int(BASE_W * 0.012 * s), gap_y=self.vgap(ui, s, 0.4))

    def modes_tip(self, g):
        """Choose Modes' tip: what it does, and each mode, the ones on marked."""
        lines = ["Choose Modes", "See what each game mode does, and switch them on."]
        for key in self.MODE_ORDER:
            name, on = g.MODE_NAMES[key], getattr(g, "mode_" + key)
            if on and key in ("chaos", "switch"):
                versions = g.CHAOS_TIMINGS if key == "chaos" else g.SWITCH_TIMINGS
                lines.append(f"» {name}: {versions[getattr(g, key + '_timing')]}")
            else:
                lines.append(("» " if on else "• ") + f"{name}: {'ON' if on else 'OFF'}")
        return "\n".join(lines)

    PHYSICS_NOTES = ("1.7's: a hit's speed comes from how hard the paddle drives into the ball, eased "
                     "towards a top speed",
                     "the angle comes from where the ball meets the paddle, every hit is a little faster "
                     "up to the top speed, and paddle movement adds no speed",
                     "Hu Taong 0.9's: drive into the ball to speed it up, a still paddle slows it, and "
                     "there's no top speed")

    def draw_ball_paddles_menu(self, state, screen):
        """Settings > Match > Ball & Paddles: their sizes and speeds, the game's pace, and (1.8) the
        physics and the Speed Cap.  (1.9: in rows.)"""
        ui = self.ui
        g = match_rules(self.app)         # (mid-match, this match's own: 1.9)

        def build(s):
            f, ty = self.row_font(ui, s), ui.fnt(0.023, s)
            G = theme.GREEN
            track_w = int(BASE_W * 0.17 * s)
            label_sample = f"{g.paddle_height_max} x {g.paddle_width_max}"  # widest label; shared so tracks line up

            def slider(key, reset, value, lo, rng, label):
                return Slider(key, lambda: (value() - lo) / rng, theme.EMBER, f, label, label_sample,
                              reset_key=reset, reset_font=ty, track_w=track_w, tip=TIPS[key], reset_last=True)

            names = list(g.PHYSICS)
            physics_tip = lambda: options_tip("Physics", "How a ball comes off a paddle.",
                                              list(zip(g.PHYSICS, self.PHYSICS_NOTES)), g.physics,
                                              "Changes come in at the next serve")
            rand = Button("randomise_all", "Randomise Ball & Paddles", f, (G, theme.GREEN_HOVER), tip=TIPS["randomise_all"])
            unrand = Button("reset_ball_and_paddles", "Reset Ball & Paddles", f, (theme.BLUE, theme.BLUE_HOVER),
                            tip=TIPS["reset_ball_and_paddles"])
            sliders = self.rows(ui, s, [
                self.heading(ui, s, "Speeds"),
                ("Ball Speed", slider("ball_speed_slider", "reset_ball_speed", lambda: g.ball_speed,
                                      g.ball_speed_min, g.ball_speed_range, lambda: str(int(g.ball_speed)))),
                ("Paddle Speed", slider("paddle_speed_slider", "reset_paddle_speed", lambda: g.paddle_speed,
                                        g.paddle_speed_min, g.paddle_speed_range, lambda: str(int(g.paddle_speed)))),
                ("Game Pace", slider("pace_slider", "reset_pace", lambda: g.pace, g.pace_min, g.pace_range,
                                     lambda: f"{g.pace:.2f}x")),
                self.heading(ui, s, "Sizes"),
                ("Ball Diameter", slider("ball_diameter_slider", "reset_ball_diameter", lambda: g.ball_diameter,
                                         g.ball_diameter_min, g.ball_diameter_range, lambda: str(int(g.ball_diameter)))),
                ("Paddle Size", slider("paddle_size_slider", "reset_paddle_size", lambda: g.paddle_height,
                                       g.paddle_height_min, g.paddle_height_range,
                                       lambda: f"{int(g.paddle_height)} x {int(g.paddle_width)}"))])
            physics = self.rows(ui, s, [
                self.heading(ui, s, "Physics"),
                ("Physics", Cycle("cycle_physics", lambda: names[g.physics], f, names, tip=physics_tip)),
                ("Speed Cap", self.switch(f, "toggle_speed_cap", lambda: g.speed_cap)),
                Space(0, self.vgap(ui, s, 1.6)),
                Stack([rand, unrand], gap=self.vgap(ui, s, 0.5))])      # (Reset under Randomise: Rowan, 1.6)
            return Grid([[sliders, physics]], gap_x=self.column_gap(s))

        ui.screen_menu(state, screen, build, title="球拍 Ball & Paddles", mark="球", reset="Reset to Default")

    def draw_gameplay_settings_menu(self, state, screen):
        """Settings > Controls ("Gameplay" till 1.9): your own controls.  The keys and the mouse
        (on a phone, the touch steering and vibration), and a controller's buttons and stick.
        (1.9: in rows; Auto-Pause went to UI, and the emotes' buttons to a page of their own.)"""
        ui = self.ui
        controls = self.app.settings.gameplay

        def build(s):
            f, ty = self.row_font(ui, s), ui.fnt(0.021, s)
            if ANDROID:
                play = self.rows(ui, s, [self.heading(ui, s, "Play"),
                                         ("Vibration", self.switch(f, "toggle_vibration", lambda: controls.vibration))])
                return Grid([[play, self.touch_section(ui, s, state)]], gap_x=self.column_gap(s))

            samples = ["Press a key", "Right Shift", "Backspace"]
            def bind(field):
                return KeyButton(f"key_{field}", lambda: key_name(getattr(controls, field)), f,
                                 lambda: state.listening == field, samples, tip=TIPS["key"])

            rows = [[Space(), Text("Red", f, (255, 112, 92)), Text("Blue", f, (112, 162, 255))]]
            for action in controls.ACTIONS:
                rows.append([Text(action.title(), f, theme.GOLD, align="right"),
                             bind(f"p1_{action}"), bind(f"p2_{action}")])
            sides = controls.SIDES
            left = self.rows(ui, s, [
                self.heading(ui, s, "Keys"),
                Grid(rows, gap_x=int(BASE_W * 0.012 * s), gap_y=self.vgap(ui, s, 0.5), middle=True),
                Text("Click a key, then press the new one.", ty, theme.PARCHMENT),
                self.heading(ui, s, "Mouse"),
                ("Mouse Steering", self.switch(f, "toggle_mouse_steer", lambda: controls.mouse_steer,
                                               tip=TIPS["toggle_mouse_steer"])),
                ("Mouse Plays", Cycle("cycle_mouse_side", lambda: sides[controls.mouse_side], f, sides,
                                      tip=TIPS["cycle_mouse_side"])),
                self.heading(ui, s, "Emotes"),
                ("", Button("open_emotes", "Emote Buttons", f, (theme.ORANGE, theme.ORANGE_HOVER),
                            tip=TIPS["open_emotes"]))])
            return Grid([[left, self.pad_section(ui, s, state, f, ty)]], gap_x=self.column_gap(s, 0.08))

        ui.screen_menu(state, screen, build, title="控制 Controls", mark="控", reset="Reset to Default")

    PAD_NAMES = {"pause": "Pause", "list": "Talisman list", "up": "Up", "down": "Down", "left": "Left",
                 "right": "Right"}

    def pad_bind(self, state, action, font, name):
        """A controller button for a match action (1.9): click it, then press the button."""
        controls, pads = self.app.settings.gameplay, self.app.gamepads
        samples = ["Press a button", "Triangle", "Options", "D-pad right"]
        return KeyButton(f"pad_{action}", lambda: pads.label(getattr(controls, "pad_" + action)), font,
                         lambda: state.listening_pad == action, samples,
                         tip=f"{name}\nThe controller button for it in a match"
                             f"{' (online; keys 1-5 send them too)' if action.startswith('emote') else ''}.\n"
                             "• Click, then press the button on the controller\n"
                             "• A button that's already used swaps over\n~ Esc cancels")

    def pad_section(self, ui, s, state, font, small):
        """Controls' Controller section (1.9): which side the first controller plays when two play
        here, which stick steers and how much of its travel is ignored, and its buttons for the
        paddle's four directions, Pause and the talisman list.  (The emotes' are on their page.)"""
        controls, pads = self.app.settings.gameplay, self.app.gamepads
        sides, sticks, zones = controls.SIDES, controls.PAD_STICKS, controls.PAD_DEADZONES
        stick_tip = lambda: options_tip("Steer With", "Which stick steers your paddle in a match.",
                                        [(name, "") for name in sticks], controls.pad_stick,
                                        "The direction buttons below steer too, at full speed")
        zone_tip = lambda: options_tip("Dead Zone", "How far the stick must move before the paddle does.",
                                       [("Small", "the slightest push moves it"), ("Normal", ""),
                                        ("Large", "for a stick that drifts when let go")], controls.pad_deadzone)
        status = Text(lambda: (", ".join(p.name for p in pads.order()) + " connected") if pads.pads else
                      "No controller connected", small, theme.PARCHMENT,
                      samples=["No controller connected", "Xbox 360 Controller, Xbox 360 Controller connected"])
        bind = lambda action: (self.PAD_NAMES[action], self.pad_bind(state, action, font, self.PAD_NAMES[action]))
        return self.rows(ui, s, [
            self.heading(ui, s, "Controller"),
            ("First Controller", Cycle("cycle_pad_first", lambda: sides[controls.pad_first], font, sides,
                                       tip="First Controller\nWith two players here, the side the first controller "
                                           "plays; the second plays the other.  The keyboard works for either.\n"
                                           "• On your own (against the AI, or online) any controller plays your paddle")),
            ("Steer With", Cycle("cycle_pad_stick", lambda: sticks[controls.pad_stick], font, sticks, tip=stick_tip)),
            ("Dead Zone", Cycle("cycle_pad_deadzone", lambda: zones[controls.pad_deadzone], font, zones, tip=zone_tip)),
            self.heading(ui, s, "Buttons", sub=True),
            bind("up"), bind("down"), bind("left"), bind("right"), bind("pause"), bind("list"),
            status])

    def draw_emote_settings_menu(self, state, screen):
        """Settings > Controls > Emotes (1.9): the controller button for each quick emote, beside
        the key that sends it."""
        ui = self.ui
        from core.emotes import EMOTES

        def build(s):
            f, ty = self.row_font(ui, s), ui.fnt(0.022, s)
            rows = [[Space(), Text("Key", f, theme.GOLD), Text("Controller", f, theme.GOLD)]]
            for i, (text, _) in enumerate(EMOTES):
                rows.append([Text(text, f, theme.PARCHMENT, align="right"), Text(str(i + 1), f, theme.GOLD_BRIGHT),
                             self.pad_bind(state, f"emote_{i + 1}", f, f"Emote: {text}")])
            notes = Stack([Text("Online only: each shows in a bubble by your side of the court, on both screens.",
                                ty, theme.PARCHMENT),
                           Text("Click a controller button, then press the new one.  Friend's Emotes in UI "
                                "settings hides your friend's.", ty, theme.PARCHMENT)],
                          gap=int(ui.gap * 0.4 * s))
            return Stack([self.heading(ui, s, "Emotes (online)"),
                          Grid(rows, gap_x=int(BASE_W * 0.02 * s), gap_y=self.vgap(ui, s, 0.5), middle=True), notes],
                         gap=self.vgap(ui, s, 0.8))

        ui.screen_menu(state, screen, build, title="表情 Emotes", mark="笑", reset="Reset to Default")

    # ── Power-ups ──────────────────────────────────────────────────────────────

    def draw_powerups_menu(self, state, screen):
        """The Talismans page (Power-Ups till 1.9), and since 1.9 its Modes view (Rowan): the same
        page for the game modes, a tile each and the panel describing the one pointed at.  The
        button at the bottom left switches between them."""
        modes = getattr(state, "view", "talismans") == "modes"
        if modes:
            self.draw_modes_view(state, screen)
        else:
            self.draw_talismans_view(state, screen)
        ui = self.ui
        font = self.fnt(0.034)
        text = "Switch to Talismans" if modes else "Switch to Modes"
        w = font.size("Switch to Talismans")[0] + 2 * self._gx       # (one width, whichever it says)
        # (in the footer's middle: Back took the bottom left, after 1.9's release)
        rect = self.draw_button(screen, self.mouse(), font, text, BASE_W // 2, ui.FOOTER_Y, theme.ORANGE, width=w)
        self.tips.offer(rect, TIPS["switch_to_talismans" if modes else "switch_to_modes"])
        state.ui_hitboxes["switch_view"] = rect

    def draw_talismans_view(self, state, screen):
        """Every talisman as a tile (its picture and its switch), four to a row, and a panel below
        that describes whichever one the mouse is on, in full.  (The Talismans switch and the spawn
        rate are on the Match screen only, since Rowan's playtest: not here as well.)"""
        ui = self.ui
        g = match_rules(self.app)         # (mid-match, this match's own: 1.9)
        ui.screen_menu(state, screen, lambda s: self.talismans_body(ui, s, g), title="法宝 Talismans", mark="宝",
                       reset="Reset to Default")

    def talismans_body(self, ui, s, g):
        """The talismans' view: All On and All Off, the colours' legend, the tiles and the panel."""
        sm, ty = ui.fnt(0.025, s), ui.fnt(0.023, s)
        head = Stack([Button("all_pu_on", "All On", sm, (theme.GREEN, theme.GREEN_HOVER),
                             tip="All On\nSwitch every talisman on."),
                      Button("all_pu_off", "All Off", sm, (theme.WHITE, theme.WHITE_HOVER),
                             tip="All Off\nSwitch every talisman off (Match settings' Talismans switch stays on, so you can pick a few).")],
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
        grid = Grid(rows, gap_x=int(BASE_W * 0.016 * s), gap_y=self.vgap(ui, s, 0.5))
        grid.measure()
        details = _PowerDetails(max(grid.w, int(BASE_W * 0.6)), ui.fnt(0.028, s), ui.fnt(0.022, s), s)
        return Stack([head, legend, grid, details], gap=self.vgap(ui, s, 0.8))

    def draw_modes_view(self, state, screen):
        """The Talismans page's Modes view (Rowan, 1.9): laid out as the talismans are, All On and All
        Off, a tile for each game mode (its talisman's picture beside its switch; Shape Shift and Soul
        Swap step through Off and their versions), and the panel below describing the one the mouse
        is on.  Three to a row: the versions make the switches wide."""
        ui = self.ui
        g = match_rules(self.app)         # (mid-match, this match's own)

        def build(s):
            sm, ty = ui.fnt(0.025, s), ui.fnt(0.023, s)
            head = Stack([Button("all_modes_on", "All On", sm, (theme.GREEN, theme.GREEN_HOVER),
                                 tip="All On\nSwitch every mode on (Shape Shift and Soul Swap as they're set)."),
                          Button("all_modes_off", "All Off", sm, (theme.WHITE, theme.WHITE_HOVER),
                                 tip="All Off\nSwitch every mode off: a plain match.")],
                         vertical=False, gap=int(BASE_W * 0.02 * s))
            legend = Text("Mix any of them.  While a mode is on, its talisman doesn't turn up.", ty, theme.PARCHMENT)
            switches = []
            for key in self.MODE_ORDER:
                name = g.MODE_NAMES[key]
                if key in ("chaos", "switch"):
                    versions = g.CHAOS_TIMINGS if key == "chaos" else g.SWITCH_TIMINGS
                    texts = [f"{name}: OFF"] + [f"{name}: {v}" for v in versions]
                    level = lambda key=key: (getattr(g, "mode_" + key) and getattr(g, key + "_timing") + 1) or 0
                    button = f"cycle_mode_{key}"
                else:
                    texts = [f"{name}: OFF", f"{name}: ON"]
                    level = lambda key=key: int(getattr(g, "mode_" + key))
                    button = f"toggle_mode_{key}"
                switches.append(CycleToggle(button, texts, sm, level, self.MODE_SEALS[key]))
            widest = [t for b in switches for t in b.texts]
            tiles = []
            for key, switch in zip(self.MODE_ORDER, switches):
                switch.samples = widest
                tile = Stack([Icon(self.MODE_ICONS[key], "Wild", int(BASE_H * 0.058 * s)), switch],
                             vertical=False, gap=int(BASE_W * 0.006 * s))
                tiles.append(_PowerTile(tile, key))
            across = 3
            grid = Grid([tiles[i:i + across] for i in range(0, len(tiles), across)],
                        gap_x=int(BASE_W * 0.016 * s), gap_y=self.vgap(ui, s, 0.5))
            grid.measure()
            details = _ModeDetails(max(grid.w, int(BASE_W * 0.6)), ui.fnt(0.028, s), ui.fnt(0.022, s), s)
            body = Stack([head, legend, grid, details], gap=self.vgap(ui, s, 0.8))
            body.measure()
            # (as tall as the talismans' view, so All On and All Off don't jump when you switch)
            talismans = self.talismans_body(ui, s, g)
            talismans.measure()
            return Stack([body, Space(0, max(0, talismans.h - body.h))])

        ui.screen_menu(state, screen, build, title="玩法 Modes", mark="玩", reset="Reset to Default")

    # ── Display settings ───────────────────────────────────────────────────────

    def draw_display_settings_menu(self, state, screen):
        """Settings > Display.  (1.9: in rows; Parallax with the background; then Rowan's layout, two
        rows of sections.)"""
        ui = self.ui
        d = self.app.settings.display
        app = self.app

        def build(s):
            f = self.row_font(ui, s)
            O = theme.ORANGE
            res_texts = [f"{w} x {h}" for (w, h) in app.resolutions]
            mode_texts = [m.capitalize() for m in app.display_modes]
            fps_texts = [str(o) for o in d.max_fps_options]

            window = None if ANDROID else self.rows(ui, s, [    # (a phone's screen has one size, always full)
                self.heading(ui, s, "Window"),
                ("Resolution", Cycle("cycle_res", lambda: res_texts[state.res_index], f, res_texts,
                                     tip=TIPS["cycle_res"])),
                ("Mode", Cycle("cycle_mode", lambda: mode_texts[state.display_mode_index], f, mode_texts,
                               tip=TIPS["cycle_mode"])),
                ("", Button("apply", "Apply", f, (O, theme.ORANGE_HOVER), tip=TIPS["apply"]))])
            frame_rate = self.rows(ui, s, [
                self.heading(ui, s, "Frame Rate"),
                ("Maximum FPS", Cycle("cycle_max_fps", lambda: str(d.max_fps_options[d.max_fps]), f, fps_texts,
                                      tip=TIPS["cycle_max_fps"])),
                ("Show FPS", self.switch(f, "toggle_show_fps", lambda: d.show_fps)),
                ("Show Ping", self.switch(f, "toggle_show_ping", lambda: d.show_ping))])
            effects = self.rows(ui, s, [
                self.heading(ui, s, "Effects"),
                ("Amount", Cycle("cycle_effects", lambda: d.effects_options[d.effects], f, list(d.effects_options),
                                 tip=TIPS["cycle_effects"])),
                ("Screen Shake", self.switch(f, "toggle_screen_shake", lambda: d.screen_shake)),
                ("Ball Trail", self.switch(f, "toggle_ball_trail", lambda: d.ball_trail))])

            track_w = int(BASE_W * 0.15 * s)
            background = self.rows(ui, s, [
                self.heading(ui, s, "Background"),
                Slot("background_thumb", int(256 * s), int(144 * s), tip=TIPS["background_thumb"]),
                ("Rotate", self.switch(f, "toggle_rotate_bg", lambda: d.rotate_backgrounds)),
                ("Change Every", Cycle("cycle_rotate_every", lambda: d.rotate_options[d.rotate_every], f,
                                       list(d.rotate_options), tip=TIPS["cycle_rotate_every"])),
                ("Parallax", Cycle("cycle_parallax", lambda: d.parallax_options[d.parallax], f,
                                   list(d.parallax_options), tip=TIPS["cycle_parallax"]))])
            dimming = self.rows(ui, s, [
                self.heading(ui, s, "Dimming"),
                ("Dim Overlay", Slider("dim_slider", lambda: d.dim, theme.EMBER, f, lambda: f"{int(100 * d.dim)}%",
                                       "100%", track_w=track_w, tip=TIPS["dim_slider"])),
                ("Court Dim", Slider("court_dim_slider", lambda: d.court_dim_level, theme.EMBER, f,
                                     lambda: f"{int(100 * d.court_dim_level)}%", "100%",
                                     track_w=track_w, tip=TIPS["court_dim_slider"]))])
            # Two rows (Rowan, 1.9): Frame Rate, Window and Effects across the top, then Background
            # and Dimming, each row centred on its own
            top = Grid([[c for c in (frame_rate, window, effects) if c is not None]], gap_x=self.column_gap(s, 0.04))
            bottom = Grid([[background, dimming]], gap_x=self.column_gap(s, 0.08))
            return Stack([top, bottom], gap=self.vgap(ui, s, 1.8))

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

        # (at the bottom left, under the panel's left edge: after 1.9's release; in the middle till then)
        state.ui_hitboxes["back"] = self.draw_button(screen, mouse_pos, self.fnt(0.036), "Back",
                                                     54 + 130, 1036, theme.RED, width=260)

    # ── Audio settings ─────────────────────────────────────────────────────────

    def draw_audio_settings_menu(self, state, screen):
        """Settings > Audio.  (1.9: in rows; the volumes in one block, the sound switches each on
        a row, and the music's own settings under the jukebox.)"""
        ui = self.ui
        sound = self.app.sound_manager
        audio = self.app.settings.audio

        def build(s):
            f, ty = self.row_font(ui, s), ui.fnt(0.022, s)
            track_w = int(BASE_W * 0.15 * s)

            def volume(key, value):
                name = key.split("_")[0]          # master, music or sfx
                return Slider(key + "_slider", value, theme.EMBER, f, lambda: f"{int(round(100 * value()))}%", "100%",
                              reset_key="reset_" + key, reset_font=ty, track_w=track_w, tip=TIPS[key + "_slider"],
                              mute_key="mute_" + key, muted=lambda: getattr(sound, name + "_muted"), reset_last=True)

            def big_switch(key, name, flag):
                button = self.toggle(f, key, name, flag)
                button.samples = [f"{n}: {v}" for n in ("Paddle Sounds", "Score Sound", "Menu Sounds")
                                  for v in ("ON", "OFF")]
                return button

            mood_notes = {"menu":    "Relaxed music for the menus",
                          "game":    "Upbeat music for matches",
                          "victory": "Triumphant music",
                          "defeat":  "Downbeat music"}

            left = self.rows(ui, s, [
                self.heading(ui, s, "Volume"),
                ("Master", volume("master_volume", lambda: sound.master_volume)),
                ("Music", volume("music_volume", lambda: sound.music_volume)),
                ("Sound Effects", volume("sfx_volume", lambda: sound.sfx_volume)),
                self.heading(ui, s, "Sounds"),         # (each one whole button: Rowan, 1.9)
                ("", big_switch("toggle_paddle_sounds", "Paddle Sounds", lambda: sound.paddle_hit_sound)),
                ("", big_switch("toggle_score_sounds", "Score Sound", lambda: sound.score_sound)),
                ("", big_switch("toggle_menu_sounds", "Menu Sounds", lambda: audio.menu_sounds))])

            right = self.rows(ui, s, [
                self.heading(ui, s, "Jukebox"),
                *self.jukebox_controls(state, f, f, track_w),
                Text(lambda: mood_notes[sound.mood], ty, theme.GOLD, samples=list(mood_notes.values())),
                self.heading(ui, s, "Music"),
                ("Even Out Volume", self.switch(f, "toggle_even_volume", lambda: audio.even_volume)),
                ("Track Fade", Cycle("cycle_fade", lambda: audio.fade_options[audio.fade], f, list(audio.fade_options),
                                     tip=lambda: options_tip("Track Fade", "How long one track takes to fade into the next.",
                                                             [("Quick", "0.4 s"), ("Smooth", "1 s"), ("Slow", "2.5 s")],
                                                             audio.fade))),
                ("Ambience", Cycle("cycle_ambience", lambda: audio.ambience_options[audio.ambience], f,
                                   list(audio.ambience_options),
                                   tip=lambda: options_tip("Ambience", "Crackling spirit fire and crickets under the music.",
                                                           [("Off", ""), ("Menus", "in the menus only"),
                                                            ("Everywhere", "in matches too")], audio.ambience)))])
            return Grid([[left, right]], gap_x=self.column_gap(s))

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
                             Button("open_achievements", "Achievements", sm, (theme.ORANGE, theme.ORANGE_HOVER),
                                    tip="Achievements\nThe 21 achievements: the ones you've earned, and how to earn the rest.")],
                            vertical=False, gap=int(BASE_W * 0.015 * s), uniform=True)
            return Stack([table, buttons], gap=self.vgap(ui, s, 1.4))

        # Export and Import in the footer's middle and Reset Stats at its right, out of the panel,
        # with Back at the bottom left; Replays and Achievements stay in it (Rowan, after 1.9's
        # release: all five were in a row in the panel, Back in the footer's middle)
        middle = [("export_stats", "Export Stats", (theme.GREEN, theme.GREEN_HOVER), TIPS["export_stats"]),
                  ("import_stats", "Import Stats", (theme.BLUE, theme.BLUE_HOVER), TIPS["import_stats"])]
        right = ("reset_stats", "Reset Stats", (theme.RED, theme.RED_HOVER), TIPS["reset_stats"])
        ui.screen_menu(state, screen, build, title="战绩 Stats", mark="绩", middle=middle, right=right)

    def draw_achievements_menu(self, state, screen):
        """Every achievement (1.9): a red seal for those earned (with the day), a grey one for the
        rest, and how to earn each."""
        ui = self.ui
        from core.achievements import LIST as ACHIEVEMENTS
        got = self.app.achievements.earned

        def build(s):
            title_font, body_font = ui.fnt(0.026, s), ui.fnt(0.019, s)
            count = Text(lambda: f"{len(got)} of {len(ACHIEVEMENTS)} earned", ui.fnt(0.03, s), theme.GOLD,
                         samples=[f"{len(ACHIEVEMENTS)} of {len(ACHIEVEMENTS)} earned"])
            tiles = [_AchievementTile(a, int(BASE_W * 0.27 * s), int(BASE_H * 0.082 * s), title_font, body_font, got)
                     for a in ACHIEVEMENTS]
            rows = [tiles[i:i + 3] for i in range(0, len(tiles), 3)]
            grid = Grid(rows, gap_x=int(BASE_W * 0.01 * s), gap_y=self.vgap(ui, s, 0.3))
            return Stack([count, grid], gap=self.vgap(ui, s, 0.6))

        ui.screen_menu(state, screen, build, title="成就 Achievements", mark="成", reset="Reset Achievements")

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
        if getattr(view, "scoreless", False):
            score = "Practice: no score"             # (Practice Mode with scoring off: 1.9)
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
        if self.using_pad():            # a controller's buttons for them (1.9)
            a, x, b = (self.app.gamepads.label(n) for n in ("a", "x", "b"))
            hint = f"{a}: next highlight      {x}: save this one      {b}: stop" if state.mode == "reel" else \
                   f"{a}: skip      {x}: save this moment      {b}: back to the match"
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
        if state.highlights:          # the match's highlights, from the win screen
            w = 170
            rect = self.draw_button(screen, mouse, f, "Highlights", x + w // 2, y, theme.ORANGE, width=w)
            state.ui_hitboxes["replay_highlights"] = rect
            self.tips.offer(rect, "Highlights\nThe best moments of this match, one after another.\n"
                                  "• Back here when they're done")
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

    # ── UI settings ("interface") ──────────────────────────────────────────────

    def draw_interface_settings_menu(self, state, screen):
        """Settings > UI: menus, the HUD and tooltips.  (1.9: in rows.)"""
        ui = self.ui
        i = self.app.settings.interface

        def build(s):
            f = self.row_font(ui, s)

            def flag(attr):
                return self.switch(f, f"toggle_{attr}", lambda: getattr(i, attr))

            hud_tip = lambda: options_tip("HUD", "What the match shows besides the scores.",
                                          [("Full", "rally count and ball speed too"), ("Minimal", "just the scores")], i.hud)
            replay_tip = lambda: options_tip("Instant Replay", "When a match's best moments replay by themselves.",
                                             [("Off", "only when you ask: Pause or the win screen"),
                                              ("Great Points", "straight after a point with a great moment"),
                                              ("After the Match", "the highlights, before the win screen"),
                                              ("Both", "")], i.instant_replay)
            menus = self.rows(ui, s, [self.heading(ui, s, "Menus"),
                                      ("Tooltips", flag("tooltips")),
                                      ("Hide Mouse", flag("hide_cursor")) if not ANDROID else None])
            match = self.rows(ui, s, [
                self.heading(ui, s, "In a Match"),
                ("HUD", Cycle("cycle_hud", lambda: i.hud_options[i.hud], f, list(i.hud_options), tip=hud_tip)),
                ("AI Banter", flag("ai_banter")),
                ("Auto-Pause", flag("auto_pause")),
                ("Friend's Emotes", flag("friend_emotes")),
                ("Instant Replay", Cycle("cycle_instant_replay", lambda: i.instant_replay_options[i.instant_replay], f,
                                         list(i.instant_replay_options), tip=replay_tip))])
            return Grid([[menus, match]], gap_x=self.column_gap(s, 0.1))

        ui.screen_menu(state, screen, build, title="界面 UI", mark="界", reset="Reset to Default")

    def touch_section(self, ui, s, state):
        """On a phone, the Gameplay screen's Touch section, in place of the keys."""
        i = self.app.settings.gameplay
        f, ty = self.row_font(ui, s), ui.fnt(0.02, s)
        steer, feel = i.touch_steer_options, i.touch_sensitivity_options
        steer_tip = lambda: options_tip("Steering", "How a finger moves your paddle.",
                                        [("Drag", "it moves as your finger moves, from wherever you touch"),
                                         ("Follow", "it heads for the point under your finger")],
                                        i.touch_steer)
        feel_tip = lambda: options_tip("Sensitivity", "How far Drag moves the paddle for each move of your finger.",
                                       [(name, "") for name in feel], i.touch_sensitivity,
                                       "Follow always goes to your finger")
        notes = Stack([Text("Against the AI or online, the whole screen steers your paddle.", ty, theme.PARCHMENT),
                       Text("Two players on one phone: each has their own half.", ty, theme.PARCHMENT),
                       Text("Back, or the button at the bottom, pauses a match.", ty, theme.PARCHMENT)],
                      gap=int(ui.gap * 0.4 * s))
        return self.rows(ui, s, [
            self.heading(ui, s, "Touch"),
            ("Steering", Cycle("cycle_touch_steer", lambda: steer[i.touch_steer], f, steer, tip=steer_tip)),
            ("Sensitivity", Cycle("cycle_touch_sensitivity", lambda: feel[i.touch_sensitivity], f, feel, tip=feel_tip)),
            notes])

    # ── Game feel (purely visual) ──────────────────────────────────────────────

    def shake(self, magnitude, duration):
        if not self.app.settings.display.screen_shake:
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

    BANNER = (760, 124)         # an achievement's banner (1.9)

    def show_achievement(self, key):
        """An achievement earned: its banner drops in at the top of the screen (one after another)."""
        if not hasattr(self, "_banners"):
            self._banners = []
        self._banners.append([self.art.get(("achievement", key), self.achievement_banner, key), 0.0])

    def achievement_banner(self, key):
        from core.achievements import BY_KEY
        _, name, how, glyph, _ = BY_KEY[key]
        w, h = self.BANNER
        surf = blank(w, h)
        surf.blit(self.art.inset(w, h), (0, 0))
        seal = self.art.seal(84, True, glyph)
        surf.blit(seal, seal.get_rect(midleft=(18, h // 2)))
        x = 18 + seal.get_width() + 18
        head = self.ui.fnt(0.022).render("Achievement earned", True, theme.GOLD)     # (the UI font has no Chinese)
        title = self.ui.fnt(0.036).render(name, True, theme.GOLD_BRIGHT)
        line = self.ui.fnt(0.022).render(how, True, theme.PARCHMENT)
        y = (h - head.get_height() - title.get_height() - line.get_height()) // 2
        for part in (head, title, line):
            surf.blit(part, (x, y))
            y += part.get_height()
        return surf

    def draw_achievement(self, screen, dt):
        """Drops in at the top, holds, then fades: the next one waits its turn."""
        banners = getattr(self, "_banners", None)
        if not banners:
            return
        surf, age = banners[0]
        age += dt
        banners[0][1] = age
        drop, hold, fade = 0.35, 3.5, 0.6
        if age > drop + hold + fade:
            banners.pop(0)
            return
        t = min(1.0, age / drop)
        y = int(lerp(-surf.get_height(), BASE_H * 0.02, 1 - (1 - t) ** 3))
        surf.set_alpha(None if age < drop + hold else int(255 * (1 - (age - drop - hold) / fade)))
        screen.blit(surf, (BASE_W // 2 - surf.get_width() // 2, y))

    # ── Controllers (1.9) ──────────────────────────────────────────────────────

    PAD_COLOURS = {"a": (84, 168, 64), "b": (204, 64, 52), "x": (56, 112, 206), "y": (222, 178, 40)}

    def pad_badge(self, name, size):
        """A controller button as a round badge, as its maker draws it: Xbox's coloured letters,
        PlayStation's shapes, otherwise its name."""
        fam = self.app.gamepads.labels() is gamepad_labels("playstation")
        return self.art.get(("pad_badge", name, size, fam), self._pad_badge, name, size, fam)

    def _pad_badge(self, name, size, playstation):
        surf = blank(size, size)
        r = size // 2
        face = name in ("a", "b", "x", "y")
        tint = self.PAD_COLOURS.get(name, (200, 190, 170)) if face else (200, 190, 170)
        pygame.draw.circle(surf, (24, 18, 18), (r, r), r)
        pygame.draw.circle(surf, tint, (r, r), r, max(2, size // 12))
        if face and playstation:
            k, c, w = size * 0.22, (r, r), max(2, size // 10)
            ps = {"a": (150, 190, 255), "b": (255, 110, 110), "x": (240, 150, 210), "y": (110, 220, 160)}[name]
            if name == "a":
                pygame.draw.line(surf, ps, (r - k, r - k), (r + k, r + k), w)
                pygame.draw.line(surf, ps, (r - k, r + k), (r + k, r - k), w)
            elif name == "b":
                pygame.draw.circle(surf, ps, c, int(k * 1.1), w)
            elif name == "x":
                pygame.draw.rect(surf, ps, (r - k, r - k, 2 * k, 2 * k), w)
            else:
                pygame.draw.polygon(surf, ps, [(r, r - k * 1.15), (r - k * 1.15, r + k * 0.8), (r + k * 1.15, r + k * 0.8)], w)
            return surf
        text = self.app.gamepads.labels().get(name, name)
        font = self.ui.fnt(0.022 if len(text) < 3 else 0.016)
        label = font.render(text if len(text) < 6 else text[:5], True, tint if face else theme.PARCHMENT)
        surf.blit(label, label.get_rect(center=(r, r)))
        return surf

    def emote_bubble(self, n):
        """A quick emote's bubble (1.9): its words, and Hu Tao's ghost for the two that have her."""
        from core.emotes import EMOTES
        text, mood = EMOTES[n]
        font = self.ui.fnt(0.034)
        label = font.render(text, True, theme.GOLD_BRIGHT)
        ghost = self.art.emote_ghost(64, mood) if mood else None
        w = label.get_width() + 44 + (ghost.get_width() + 12 if ghost else 0)
        h = max(label.get_height(), ghost.get_height() if ghost else 0) + 28
        surf = blank(w, h)
        surf.blit(self.art.inset(w, h), (0, 0))
        x = 22
        if ghost:
            surf.blit(ghost, ghost.get_rect(midleft=(x, h // 2)))
            x += ghost.get_width() + 12
        surf.blit(label, label.get_rect(midleft=(x, h // 2)))
        return surf

    def draw_emotes(self, screen):
        """Online, the quick emotes showing: each by its sender's side of the court, popping up and
        fading away."""
        from core.emotes import SHOW
        for n, side, age in self.app.emotes.bubbles:
            surf = self.art.get(("emote_bubble", n), self.emote_bubble, n)
            pop = min(1.0, age / 0.15)
            fade = min(1.0, (SHOW - age) / 0.5)
            if pop < 1:
                surf = pygame.transform.smoothscale(surf, (max(1, int(surf.get_width() * (0.6 + 0.4 * pop))),
                                                           max(1, int(surf.get_height() * (0.6 + 0.4 * pop)))))
            else:
                surf = surf.copy()
            surf.set_alpha(None if fade >= 1 else int(255 * max(0.0, fade)))
            cx = BASE_W * 0.2 if side == 1 else BASE_W * 0.8
            screen.blit(surf, surf.get_rect(center=(int(cx), int(BASE_H * 0.24))))

    def draw_pad_prompts(self, screen):
        """While a controller works the menus: what A and B do, at the top right (clear of every
        screen's buttons)."""
        nav = self.app.navigator
        if not nav.active or not self.using_pad():
            return
        font, size = self.ui.fnt(0.026), 44
        x, y = BASE_W - 40, 44
        for name, what in (("b", "Back"), ("a", "Select")):
            text = font.render(what, True, theme.GOLD_BRIGHT)
            x -= text.get_width()
            screen.blit(text, text.get_rect(midleft=(x, y)))
            badge = self.pad_badge(name, size)
            x -= size + 10
            screen.blit(badge, (x, y - size // 2))
            x -= 34

    def draw_toast(self, screen, dt):
        """Slides in at the bottom-left, holds, then fades out.  Over a menu it's at the top-left
        instead: the menus' Back button is at the bottom left (after 1.9's release), and the toast
        hid it."""
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
        menu = getattr(self.app.state_manager.current(), "is_menu", False)
        y = int(BASE_H * 0.03) if menu else BASE_H - surf.get_height() - int(BASE_H * 0.03)
        screen.blit(surf, (x, y))

    # ── Game world ─────────────────────────────────────────────────────────────

    def draw_arena(self, screen, ox, oy, wall=True, cord=True, flipped=False):
        """The court.  `cord` False leaves out the line down the middle (Open Court has taken the wall down).
        `flipped`: a Switch has given Blue the left paddle, so the goals' colours swap too."""
        W, H = BASE_W, BASE_H
        art = self.art
        t = self.app.fx.time

        # Spirit fire along each goal, in its player's colour
        red, blue = (150, 34, 22), (26, 70, 170)
        for side, tint in (("left", blue if flipped else red), ("right", red if flipped else blue)):
            level = 4 + round(2 * (math.sin(t * 2.6 + (side == "left") * 2) * .5 + .5))
            strip = art.goal_glow(side, tint, level)
            screen.blit(strip, (0 if side == "left" else W - strip.get_width(), 0), special_flags=ADD)

        if random.random() < 40 * self.app.dt:
            left, right = (theme.SPIRIT_BLUE, theme.EMBER) if flipped else (theme.EMBER, theme.SPIRIT_BLUE)
            x, col = random.choice(((random.uniform(0, 16), left), (W - random.uniform(0, 16), right)))
            self.app.fx.spark(x, random.uniform(0, H), 1, col, speed=90, life=1.1,
                              arc=(-1.9, -1.2), gravity=-60)

        seal = art.watermark("往", 300, 26)
        screen.blit(seal, seal.get_rect(center=(W // 2 + ox, H // 2 + oy)))
        ring = art.faint_sigil(420, 44)
        screen.blit(ring, ring.get_rect(center=(W // 2 + ox, H // 2 + oy)))

        shown = self.fade_toward("cord", cord, 0.5)            # (1.8: Open Court's wall fades back)
        if shown > 0:
            line = art.cord(H, faint=not wall)
            if shown < 1:
                level = max(1, round(shown * 10))
                line = art.get(("cord_fade", H, not wall, level), self._faded, line, level / 10)
            screen.blit(line, line.get_rect(midtop=(W // 2 + ox, oy)))

        rail = art.rail(W, flowers=False)
        screen.blit(rail, rail.get_rect(midtop=(W // 2 + ox, oy - 4)))
        screen.blit(rail, rail.get_rect(midbottom=(W // 2 + ox, H + oy + 4)))

    def fade_toward(self, key, on, seconds):
        """A fade kept here, for what comes and goes on the court: eases up to 1 while `on`, and
        back down to 0 over `seconds` when not (so it never cuts straight back to normal)."""
        fades = self.__dict__.setdefault("_fades", {})
        now = fades.get(key, 1.0 if on else 0.0)
        step = min(self.app.dt, 1 / 20) / seconds
        now = min(1.0, now + step) if on else max(0.0, now - step)
        fades[key] = now
        return now

    def track_paddle(self, paddle, rect):
        """Note where this side's paddle is drawn this frame (for Swift Step's streaks and the
        Snowball's warning); answers its recent track, oldest first.  A jump (a serve, a teleport,
        a swap, a replay skipping on) starts it afresh."""
        track = self._paddle_tracks.setdefault(paddle.is_left, deque(maxlen=7))
        x, y = rect.center
        if track and math.hypot(x - track[-1][0], y - track[-1][1]) > 160:
            track.clear()
        track.append((x, y, self.app.fx.time))
        return track

    def paddle_velocity(self, paddle):
        """How fast this side's paddle is moving across the court, px/s, from where it was drawn."""
        track = self._paddle_tracks.get(paddle.is_left)
        if not track or len(track) < 3 or track[-1][2] <= track[0][2]:
            return 0.0
        return (track[-1][0] - track[0][0]) / (track[-1][2] - track[0][2])

    def draw_paddle(self, screen, paddle, rect):
        finish = paddle.colour                  # the player's colour, wherever a Switch has put them
        # Sprites come in 2-4 px steps, so a size that keeps drifting (Chaos Mode +) reuses them.
        # They round down, so the paddle is never drawn bigger than its hitbox.
        centre = rect.center
        rect = pygame.Rect(0, 0, max(4, int(rect.w / 2) * 2), max(8, int(rect.h / 4) * 4))
        rect.center = centre
        track = self.track_paddle(paddle, rect)
        powerups = getattr(paddle.game, "powerups", None)
        if powerups and powerups.has(paddle, "swift"):
            self.draw_swift_streaks(screen, rect, track, finish)
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

        if powerups:
            self.draw_paddle_effects(screen, paddle, rect, powerups)

    def draw_swift_streaks(self, screen, rect, track, finish):
        """Swift Step: fading after-images of the paddle behind it as it moves, and gold streaks,
        so the other player (and anyone watching) can see it's on."""
        sprite = self.art.paddle(rect.w, rect.h, finish)
        x, y = rect.center
        for i, (px, py, _) in enumerate(list(track)[:-1]):
            if math.hypot(px - x, py - y) < 6:
                continue
            k = (i + 1) / len(track)
            sprite.set_alpha(int(110 * k))
            screen.blit(sprite, sprite.get_rect(center=(px, py)))
            pygame.draw.line(screen, scaled((255, 214, 120), .35 + .5 * k), (px, py - rect.h * .35), (x, y - rect.h * .35), 2)
            pygame.draw.line(screen, scaled((255, 214, 120), .35 + .5 * k), (px, py + rect.h * .35), (x, y + rect.h * .35), 2)
        sprite.set_alpha(255, pygame.RLEACCEL)

    # One aura per paddle, the first that applies: boons gold, curses violet, and Sticky Goo the
    # paddle's own colour (violet over red read as pink, so you lost track of yours)
    EFFECT_GLOWS = (("giant", "gold"), ("swift", "gold"), ("shrink", "violet"), ("sticky", None))
    ICON_SIZES = (80, 64, 44, 34)

    def draw_paddle_effects(self, screen, paddle, rect, powerups):
        art = self.art
        pulse = .65 + .35 * math.sin(self.app.fx.time * 6)
        for key, finish in self.EFFECT_GLOWS:
            if powerups.has(paddle, key):
                halo = art.paddle_glow(rect.w, rect.h, finish or paddle.colour)
                halo.set_alpha(int(255 * pulse))
                screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
                halo.set_alpha(255, pygame.RLEACCEL)
                break
        coat = self.fade_toward(("goo", paddle.is_left), powerups.has(paddle, "sticky"), 0.4)    # (1.8: it fades off)
        if coat > 0:
            goo = art.get(("goo_coat", rect.w, rect.h), self._goo_coat, rect.w, rect.h)
            if coat < 1:
                level = max(1, round(coat * 10))
                goo = art.get(("goo_fade", rect.w, rect.h, level), self._faded, goo, level / 10)
            screen.blit(goo, goo.get_rect(midtop=rect.midtop))
        if any(key == "teleport" and charges for key, _, charges in powerups.effect_list(paddle)):
            # a Safety Teleport save is waiting: a gold glow and its glyph on the paddle
            halo = art.paddle_glow(rect.w, rect.h, "gold")
            halo.set_alpha(int(60 * pulse))
            screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
            halo.set_alpha(255, pygame.RLEACCEL)
            size = max(16, min(40, rect.w + 10)) // 2 * 2
            charm = art.power_icon(size, "teleport", "Boon")
            screen.blit(charm, charm.get_rect(center=rect.center))

    @staticmethod
    def _goo_coat(w, h):
        """Sticky Goo: goo smeared round the paddle's edges, dripping off it.  Its middle stays
        clear, so the paddle still shows red or blue (both turned the same yellow-green)."""
        coat = blank(w, h + 18)
        green = (190, 220, 60, 150)
        pygame.draw.rect(coat, green, (0, 0, w, h), border_radius=max(3, w // 3))
        core = max(2, w // 4)
        coat.fill((0, 0, 0, 0), (core, max(6, h // 8), w - 2 * core, h - 2 * max(6, h // 8)))
        rng = random.Random(w * 1000 + h)
        for _ in range(max(2, h // 60)):
            x = rng.uniform(2, w - 6)
            y = rng.uniform(h * .2, h * .95)
            length = rng.uniform(8, 18)
            pygame.draw.rect(coat, (200, 230, 70, 190), (x, y, 4, length), border_radius=2)
            pygame.draw.circle(coat, (210, 240, 90, 210), (x + 2, y + length), 3)
        pygame.draw.rect(coat, (230, 250, 140, 200), (0, 0, w, h), 2, border_radius=max(3, w // 3))
        return coat

    def draw_ball(self, screen, ball, rect, ox, oy):
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        r = rect.w // 2

        trail = self._trail if ball is getattr(ball.game, "ball", ball) else self._twin_trail
        if not self.app.settings.display.ball_trail:
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
        fire = (40, 96, 220) if paddle and paddle.colour == "blue" else (200, 60, 22)
        side = getattr(ball, "side", None)
        if side:                                   # Twin Balls: each keeps its own colour, whoever hits it
            fire = (200, 60, 22) if side == "red" else (40, 96, 220)
        snow = bool(powerups) and powerups.snowball()
        ghost = bool(powerups) and powerups.ghostly()
        if getattr(ball, "blazing", False):
            fire = (255, 116, 30)                  # Spirit Fire
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
        fuse = powerups.cracker_fuse(ball) if powerups and hasattr(powerups, "cracker_fuse") else 0
        if fuse > 0:
            self.draw_cracker(screen, rect, fuse)
        if snow and ball is getattr(ball.game, "ball", ball):
            d = max(8, round(rect.w / 4) * 4)
            coat = self.art.get(("snow_ball", d), self._snow_ball, d)
            screen.blit(coat, coat.get_rect(center=rect.center))
        elif ghost:
            d = max(8, round(rect.w / 4) * 4)
            veil = self.art.get(("ghost_veil", d), self._ghost_veil, d)
            screen.blit(veil, veil.get_rect(center=rect.center))

    FUSE_LENGTH = 46        # px of Firecracker fuse when it's lit

    def draw_cracker(self, screen, rect, fuse):
        """Firecracker: a red cracker strapped to the ball, and its fuse burning down: the fuse
        shortens over its 5 seconds, a spark fizzing at the burning end (harder in the last one)."""
        t = self.app.fx.time
        x, y = rect.right - 4, rect.top + 2
        body = pygame.Rect(0, 0, 14, 32)
        body.midbottom = (x, y + 20)
        pygame.draw.rect(screen, (196, 30, 34), body, border_radius=4)
        pygame.draw.rect(screen, (250, 200, 80), (body.x, body.y + 6, body.w, 4))
        pygame.draw.rect(screen, (250, 200, 80), (body.x, body.bottom - 10, body.w, 4))
        pygame.draw.rect(screen, (90, 10, 14), body, 2, border_radius=4)
        # the fuse: a gentle S up and away from the cracker, as much of it as is left unburnt
        left = max(0.0, min(1.0, fuse / POWERUPS["cracker"].seconds))
        length = max(3.0, self.FUSE_LENGTH * left)
        points = [(body.centerx + 0.45 * s + 3 * math.sin(s / 9), body.top - 0.9 * s)
                  for s in [i * length / 8 for i in range(9)]]
        pygame.draw.lines(screen, (52, 34, 24), False, points, 6)         # a dark edge...
        pygame.draw.lines(screen, (226, 196, 132), False, points, 3)      # ...round a pale cord
        tip = points[-1]
        last = fuse < 1.0                                     # the last second: it fizzes harder
        flicker = 0.5 + 0.5 * math.sin(t * (40 if last else 22))
        glow = self.art.glow(40 if last else 30, scaled((255, 200, 80), 0.6 + 0.4 * flicker))
        screen.blit(glow, glow.get_rect(center=tip), special_flags=ADD)
        if random.random() < (0.9 if last else 0.45):
            self.app.fx.spark(tip[0], tip[1], 2 if last else 1, (255, 210, 120), speed = 160, life = .25)

    CRACKER_DIGIT_GAP = 34      # px from the ball's edge to the middle of the Firecracker's number

    def draw_cracker_count(self, screen, game, powerups, ox, oy):
        """Firecracker: its seconds left, counting 5 to 1 over the ball (under it by the top wall),
        red for the last two.  Drawn after night falls so it reads in the dark too; hidden, like the
        fuse, while a Ghost Ball fades."""
        ball = game.ball
        fuse = powerups.cracker_fuse(ball) if hasattr(powerups, "cracker_fuse") else 0
        if fuse <= 0 or powerups.ball_alpha(ball) < 1.0:
            return
        gap = self.CRACKER_DIGIT_GAP
        top, bottom = ball.y0 + oy, ball.y1 + oy
        y = top - gap if top > 2 * gap else bottom + gap
        mark = self.cracker_digit(max(1, math.ceil(fuse - 1e-6)))
        screen.blit(mark, mark.get_rect(center=(int((ball.x0 + ball.x1) / 2 + ox) - 6, int(y))))

    def cracker_digit(self, n):
        """The Firecracker's countdown number: cream with a dark edge, then bigger and red for 2 and 1."""
        if n > 2:
            return self.art.gilded(str(n), self.art.ui(46), top=(255, 250, 228), bottom=(242, 200, 126), glow=None)
        return self.art.gilded(str(n), self.art.ui(56), top=(255, 170, 150), bottom=(226, 34, 30), glow=None)

    def draw_portals(self, screen, powerups, ox, oy):
        """Portal Pair: two swirling ovals, linked, each with a dotted line along the way a ball comes
        out of it (1.8 playtest: turning arrows, and then a bright side, were hard to keep track of).
        Closing ones shrink away (1.8)."""
        portals = getattr(powerups, "portals", [])
        closing = getattr(powerups, "closing", [])
        if not portals and not closing:
            return
        t = self.app.fx.time
        stones = [o for o in getattr(getattr(powerups, "game", None), "objects", ()) if getattr(o, "is_obstacle", False)]
        for i, door in enumerate(portals + closing):
            shut = door.get("shut", 1.0) if door in closing else 1.0
            R = self.portal_size(door)
            if shut < 1.0:
                R = max(self.PORTAL_STEP, int(R * shut / self.PORTAL_STEP) * self.PORTAL_STEP)
            x, y = door["x"] + ox, door["y"] + oy
            glow = self.art.glow(int(R * 2.2) // 4 * 4, scaled((150, 100, 255), .7))
            screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
            facing = self.portal_facing(door)
            flash = round(door.get("flash", 0.0) * 4) / 4         # (1.8: the way out, just before a ball comes out)
            if shut >= 1.0:
                self.draw_portal_path(screen, door, R, facing, t, flash, stones, ox, oy)
            if flash > 0:
                burst = self.portal_burst(R, flash)
                screen.blit(burst, burst.get_rect(center=(x, y)), special_flags=ADD)
            self.draw_portal(screen, x, y, R, facing, t, 1 if i else -1, flash)
            if flash > 0:
                pulse = self.portal_outline(x, y, R, facing, 1.05 + 0.3 * (1 - flash))
                pygame.draw.lines(screen, (235, 255, 255), True, pulse, max(2, int(7 * flash)))

    PORTAL_SQUASH = 0.62        # a portal's depth along its way out, over its width across its face
    PORTAL_STEP = 8             # a portal's radius as drawn goes in these steps (so each size's glow is built once)
    PATH_GAP, PATH_DOTS, PATH_LEVELS = 30, 16, 6      # its dotted way out: px apart, how many dots, how many strengths

    @staticmethod
    def portal_facing(door):
        """The way a ball comes out of this portal (never steeper than a portal sends it)."""
        dx, dy = PowerUps.portal_exit(door["angle"])
        return math.atan2(dy, dx)

    @classmethod
    def portal_point(cls, x, y, R, facing, u, scale = 1.0):
        """A point on a portal's oval, `u` radians round it from the middle of its front (the way
        out): R across its face and PORTAL_SQUASH as deep."""
        along, across = R * cls.PORTAL_SQUASH * scale * math.cos(u), R * scale * math.sin(u)
        dx, dy = math.cos(facing), math.sin(facing)
        return x + dx * along - dy * across, y + dy * along + dx * across

    # (cos, sin) round an oval, worked out once: all of it, its back half and its front half
    OVAL = {part: [(math.cos(start + (end - start) * j / n), math.sin(start + (end - start) * j / n)) for j in range(n + 1)]
            for part, start, end, n in (("all", 0.0, math.tau, 40), ("back", math.pi / 2, 3 * math.pi / 2, 20),
                                        ("front", -math.pi / 2, math.pi / 2, 20))}

    @classmethod
    def portal_outline(cls, x, y, R, facing, scale = 1.0, part = "all"):
        """Points round a portal's oval (or its back or front half)."""
        dx, dy = math.cos(facing), math.sin(facing)
        b, a = R * cls.PORTAL_SQUASH * scale, R * scale
        bx, by, ax, ay = dx * b, dy * b, -dy * a, dx * a
        return [(x + bx * c + ax * s, y + by * c + ay * s) for c, s in cls.OVAL[part]]

    def portal_burst(self, R, flash):
        """The glow as a ball is about to come out of a portal: in three sizes and four strengths,
        all built ahead (one for every size it grows through was built the first time it flashed)."""
        size = 160 if R < 80 else 256 if R < 104 else 384
        return self.art.glow(size, scaled((200, 250, 255), max(1, min(4, round(flash * 4))) / 4))

    def draw_portal(self, screen, x, y, R, facing, t, spin, flash = 0.0):
        """A portal: an oval, wide across its face and shallow along its way out, so a ball comes out
        of a wide side; swirling inside, and rimmed with light all round.  (1.8 playtest: its way
        out was a turning arrow, then its bright front; now it's dotted, see draw_portal_path.)"""
        outline = self.portal_outline(x, y, R, facing)
        gfxdraw.filled_polygon(screen, outline, (20, 8, 40, 200))
        gfxdraw.filled_polygon(screen, self.portal_outline(x, y, R, facing, 0.7), (60, 30, 120, 150))
        for k in range(10):                                    # a swirl inside
            px, py = self.portal_point(x, y, R, facing, spin * t * 3.2 + k * math.tau / 10,
                                       0.55 + 0.12 * math.sin(t * 4 + k))
            pygame.draw.circle(screen, (210, 190, 255), (int(px), int(py)), 3)
        pygame.draw.lines(screen, (40, 20, 90), True, outline, 9)
        pygame.draw.lines(screen, mix((190, 150, 255), (255, 255, 255), flash), True, outline, 4)

    def path_dot(self, level):
        return self.art.glow(10, scaled((150, 235, 255), level / self.PATH_LEVELS))

    def draw_portal_path(self, screen, door, R, facing, t, flash, stones, ox, oy):
        """The way a ball comes out of a portal, dotted (1.8 playtest): from its front along the path
        a ball takes, bouncing off the top and bottom, up to any stone in the way.  Small dim dots,
        edged dark so they show over any background, drifting outwards; big and bright, and
        glowing, as a ball is about to come out."""
        dx, dy = math.cos(facing), math.sin(facing)
        r = 16                                                 # (about a ball's radius)
        start = R * self.PORTAL_SQUASH + 8
        offset = (t * 45) % self.PATH_GAP
        length = self.PATH_GAP * self.PATH_DOTS
        for i in range(self.PATH_DOTS):
            d = start + offset + i * self.PATH_GAP
            px = door["x"] + dx * d
            py, _ = reflect_in_range(door["y"] + dy * d, r, BASE_H - r)
            if not r < px < BASE_W - r or any(o.x0 < px < o.x1 and o.y0 < py < o.y1 for o in stones):
                break
            fade = (1 - (d - start) / length) * min(1.0, (d - start) / self.PATH_GAP)    # (in at the portal, out far off)
            centre = (int(px + ox), int(py + oy))
            if flash > 0:
                level = round(flash * fade * self.PATH_LEVELS)
                if level > 0:
                    dot = self.path_dot(level)
                    screen.blit(dot, dot.get_rect(center=centre), special_flags=ADD)
            size = round(1 + 2.5 * fade + 2 * flash * fade)
            if size < 1:
                continue
            pygame.draw.circle(screen, (14, 18, 38), centre, size + 1)
            pygame.draw.circle(screen, mix(scaled((140, 225, 255), 0.6 + 0.4 * fade), (255, 255, 255), flash), centre, size)

    @classmethod
    def portal_size(cls, door):
        """A portal's radius as drawn: in PORTAL_STEP steps, so each size's sprites are built once."""
        step = cls.PORTAL_STEP
        return max(step, int(round(door.get("r", PowerUps.PORTAL_R) / step)) * step)

    HOLE_TINT = (150, 70, 255)
    HOLE_LEVELS = 16            # sizes of a black hole's disc: 8 as it opens, then up to 16 as it grows
    HOLE_MOTES = [(_r.uniform(0, math.tau), _r.random(), _r.uniform(0.22, 0.38))
                  for _r in [random.Random(1808)] for _ in range(40)]    # dust round a black hole: where, when, how fast

    def hole_sprites(self, level):
        """A black hole's glowing disc and the glow round it, at one of HOLE_LEVELS sizes (it opens,
        grows and implodes through them)."""
        art = self.art
        disc = art.get(("hole_disc", level), self._hole_disc, level)
        glow = art.glow((int(150 * level / 8) // 4) * 4 + 8, scaled(self.HOLE_TINT, .55))
        return disc, glow

    @staticmethod
    def _hole_disc(level):
        """A disc of swirling light round a black hole: hot gold close in, violet at its rim."""
        R = max(8, int(118 * level / 8))
        s = 2 * R + 4
        c = s // 2
        disc = blank(s, s)
        steps = 24
        for i in range(steps, 0, -1):
            k = i / steps
            rr = int(R * k)
            if rr < 2:
                continue
            tint = mix((255, 200, 128), (110, 44, 200), k)
            pygame.draw.circle(disc, (*tint, int(36 + 180 * (1 - k) ** 0.8)), (c, c), rr)
        return disc

    def draw_holes(self, screen, powerups, ox, oy):
        """Black holes (1.8): dust drawn in from the edge of the pull, a glowing disc swirling round
        a black heart that pulses as it swallows a ball, bigger as it grows; a collapse; and at the
        point's end, an implosion.  No arrows: none shows which way a ball will come out (Rowan's
        playtest).  (Everything is worked out from the time and the hole itself, so replays and the
        friend's screen draw the same.)"""
        holes = getattr(powerups, "holes", [])
        if not holes:
            return
        art, t = self.art, self.app.fx.time
        mote = art.glow(5, (150, 104, 230))
        for hole in holes:
            x, y = hole["x"] + ox, hole["y"] + oy
            reach, _pull, core = PowerUps.hole_style(hole)
            spin = hole.get("spin", 1)
            dying = hole.get("dying")
            kind = hole["kind"]
            size = hole.get("size", 1.0)
            if dying is not None:
                self.draw_implosion(screen, x, y, core, spin, 1 - dying / PowerUps.HOLE_IMPLODE,
                                    0.4 if kind == PowerUps.HOLE_MINI else size)
                continue
            if kind == PowerUps.HOLE_MINI:
                self.draw_mini(screen, hole, x, y, reach, core, t)
                continue
            if hole.get("collapse") is not None:
                self.draw_collapse(screen, hole, x, y, core, size, spin, t)
                continue
            s = min(1.0, hole.get("age", 1.0) / PowerUps.HOLE_OPEN)
            s = 1 - (1 - s) ** 3                                   # it bursts open, then settles
            # dust drawn in from the edge of its pull, faster as it nears the heart
            for a0, p0, rate in self.HOLE_MOTES:
                p = (t * rate + p0) % 1.0
                rr = core + (reach - core) * (1 - p) ** 1.7 * s
                a = a0 + spin * p * 5.0
                screen.blit(mote, mote.get_rect(center=(x + math.cos(a) * rr, y + math.sin(a) * rr)), special_flags=ADD)
            # the glow and the disc
            level = max(1, min(self.HOLE_LEVELS, round(s * 8 * size)))
            disc, glow = self.hole_sprites(level)
            screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
            screen.blit(disc, disc.get_rect(center=(x, y)))
            # bright streaks swirling round it, the inner ones faster
            self.draw_hole_swirl(screen, x, y, core, spin, t, s, spread = 76 * size)
            # the black heart, rimmed with light
            heart = max(2, int(core * s))
            pygame.draw.circle(screen, (0, 0, 0), (int(x), int(y)), heart)
            pygame.draw.circle(screen, (255, 230, 196), (int(x), int(y)), heart, 2)
            pygame.draw.circle(screen, (200, 150, 255), (int(x), int(y)), int(heart * (1.3 + 0.06 * math.sin(t * 5))), 1)
            if hole.get("flash", 0.0) > 0:                   # the heart pulses as it swallows a ball
                self.draw_swallowing(screen, x, y, core, spin, hole["flash"], t)

    @staticmethod
    def draw_hole_swirl(screen, x, y, core, spin, t, s, inward = 0.0, spread = 76):
        """Streaks of light circling a black hole's heart, each with a short tail, out to `spread` px
        past it; `inward` (0-1) draws them spiralling down into it as it implodes."""
        for i in range(18):
            ring = (i % 6) / 5
            rr = (core * 1.15 + spread * ring * (1 - inward)) * s
            a = spin * t * (4.4 - 2.8 * ring) * (1 + 3 * inward) + i * 2.39996
            tint = mix((255, 214, 150), (196, 130, 255), ring)
            for j in range(3):
                aj = a - spin * j * 0.13
                pygame.draw.circle(screen, scaled(tint, 1 - j * 0.3),
                                   (int(x + math.cos(aj) * rr), int(y + math.sin(aj) * rr)), max(1, 3 - j))

    def draw_swallowing(self, screen, x, y, core, spin, flash, t):
        """A black hole has a ball: it's drawn out into a streak spiralling into the heart, and the
        heart pulses."""
        held = PowerUps.HOLE_HOLD / PowerUps.HOLE_FLARE
        k = (1 - flash) / held                                # 0 as it falls in, 1 as it comes out
        if k < 1:
            for i in range(9):
                f = i / 8
                rr = core + (50 * (1 - k) + 6) * (1 - f)
                a = spin * (t * 6 + f * 2.4)
                size = max(2, int((10 - 7 * f) * (1 - 0.6 * k)))
                pygame.draw.circle(screen, mix((255, 250, 235), (255, 196, 120), f),
                                   (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr)), size)
        pulse = int(core * (1.2 + 1.6 * min(1.0, k)))
        pygame.draw.circle(screen, scaled((255, 236, 210), max(0.2, flash)), (int(x), int(y)), pulse, max(1, int(5 * flash)))

    COLLAPSE_SQUEEZE = 0.7      # the share of a collapse its disc takes to spiral in; then it's a blazing point

    def draw_collapse(self, screen, hole, x, y, core, size, spin, t):
        """A full-grown Black Hole collapses in on itself (1.8 playtest), holding the ball, over
        COLLAPSE_TIME: its disc spirals down into the heart, faster and faster, as light pours in
        from all round and the heart blazes hotter; then it's a single blazing point, trembling, as
        a ring of light closes in on it.  Then it bursts: draw_implosion's flash and ring."""
        c = clamp(hole.get("collapse", 0.0) / PowerUps.COLLAPSE_TIME, 0.0, 1.0)
        squeeze = min(1.0, c / self.COLLAPSE_SQUEEZE)
        s = size * (1 - 0.9 * squeeze)
        if s > 0.1:
            disc, glow = self.hole_sprites(max(1, min(self.HOLE_LEVELS, round(s * 8))))
            screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
            screen.blit(disc, disc.get_rect(center=(x, y)))
        self.draw_hole_swirl(screen, x, y, core, spin, t, max(0.25, 1 - squeeze), inward = squeeze, spread = 76 * size)
        for k in range(20):                                    # light pouring in from all round, spiralling
            f = (t * 1.6 + k / 20) % 1.0                        # (0 far out, 1 at the heart)
            a = k * 2.39996 + spin * f * 2.5
            rr = (1 - f) ** 1.4 * 330 * size + 6
            pygame.draw.circle(screen, mix((190, 140, 255), (255, 244, 225), f),
                               (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr)), max(2, int(2 + 4 * f)))
        late = c >= self.COLLAPSE_SQUEEZE
        level = max(1, min(8, round(2 + 6 * squeeze + (1.5 * math.sin(t * 38) if late else 0))))
        flare = self.art.glow(level * 14 + 16, scaled((255, 236, 210), level / 8))
        screen.blit(flare, flare.get_rect(center=(x, y)), special_flags=ADD)
        if not late:                                           # the heart, shrinking
            heart = max(3, int(core * (1 - 0.85 * squeeze)))
            pygame.draw.circle(screen, (0, 0, 0), (int(x), int(y)), heart)
            pygame.draw.circle(screen, (255, 236, 210), (int(x), int(y)), heart, 2)
            return
        q = (c - self.COLLAPSE_SQUEEZE) / (1 - self.COLLAPSE_SQUEEZE)
        jx, jy = int(math.sin(t * 71) * 3), int(math.cos(t * 59) * 3)        # a blazing point, trembling
        pygame.draw.circle(screen, (255, 252, 240), (int(x) + jx, int(y) + jy), max(3, int(8 - 4 * q)))
        ring = int((1 - q) ** 1.5 * 170 * size) + 8                           # and a ring of light closing in
        pygame.draw.circle(screen, mix((200, 150, 255), (255, 240, 220), q), (int(x), int(y)), ring, max(2, int(2 + 4 * q)))

    def draw_mini(self, screen, hole, x, y, reach, core, t):
        """A mini black hole (1.8): a small swirling disc round a black heart, fading in and out
        (its heart pulses as it swallows a ball)."""
        s = hole.get("power", 1.0)
        if s <= 0.02:
            return
        art = self.art
        spin = hole.get("spin", 1)
        mote = art.glow(5, (150, 104, 230))
        for a0, p0, rate in self.HOLE_MOTES[:14]:
            p = (t * rate * 1.4 + p0) % 1.0
            rr = core + (reach - core) * (1 - p) ** 1.7 * s
            a = a0 + spin * p * 5.0
            screen.blit(mote, mote.get_rect(center=(x + math.cos(a) * rr, y + math.sin(a) * rr)), special_flags=ADD)
        disc, glow = self.hole_sprites(max(1, round(3 * s)))
        screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
        screen.blit(disc, disc.get_rect(center=(x, y)))
        self.draw_hole_swirl(screen, x, y, core * 0.6, spin, t, s * 0.55)
        heart = max(2, int(core * s))
        pygame.draw.circle(screen, (0, 0, 0), (int(x), int(y)), heart)
        pygame.draw.circle(screen, (255, 230, 196), (int(x), int(y)), heart, 2)
        if hole.get("flash", 0.0) > 0:
            self.draw_swallowing(screen, x, y, core, spin, hole["flash"], t)

    def draw_implosion(self, screen, x, y, core, spin, k, scale = 1.0):
        """A black hole implodes at the point's end: its disc spirals down into the heart, then a
        flash, and a ring of light racing out and fading."""
        t = self.app.fx.time
        burst = 1 - PowerUps.HOLE_BURST                      # (where its flash starts: a collapse shows only that)
        if k < burst:
            q = k / burst
            s = (1 - q) * scale
            level = max(1, round(s * 8))
            disc, glow = self.hole_sprites(level)
            screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
            screen.blit(disc, disc.get_rect(center=(x, y)))
            self.draw_hole_swirl(screen, x, y, core, spin, t, max(0.2, s), inward = q)
            heart = max(2, int(core * (1 - 0.8 * q)))
            pygame.draw.circle(screen, (0, 0, 0), (int(x), int(y)), heart)
            pygame.draw.circle(screen, (255, 240, 220), (int(x), int(y)), heart, 2)
            return
        q = (k - burst) / PowerUps.HOLE_BURST
        level = max(1, round((1 - q) * 8))
        flash = self.art.glow(level * 14 + 16, scaled((255, 236, 210), level / 8))
        screen.blit(flash, flash.get_rect(center=(x, y)), special_flags=ADD)
        r = int(20 + 300 * scale * (1 - (1 - q) ** 2))
        fade = 1 - q
        if fade > 0.05:
            # (ring by ring, blended straight onto the court: a surface the ring's size, made every
            # frame, was slow to make once a grown hole's ring was wide)
            tint = (220, 180, 255, int(220 * fade))
            for w in range(max(2, int(8 * fade))):
                gfxdraw.circle(screen, int(x), int(y), r - w, tint)

    def draw_wind(self, screen, powerups):
        """Wind Gust: leaves blowing across the court the way the wind does (any way, since 1.9),
        swaying as they go."""
        wx, wy = powerups.wind_vector() if hasattr(powerups, "wind_vector") else (0.0, 0.0)
        force = math.hypot(wx, wy)
        leaves = self._leaves
        dt = min(self.app.dt, 1 / 20)
        if force:
            ux, uy = wx / force, wy / force         # which way it blows
            for _ in range(int(force / PowerUps.WIND * 48 * dt * 10) + (1 if random.random() < force / PowerUps.WIND * 0.5 else 0)):
                # in from the edges the wind blows from: the top or bottom, or a side, as much as it
                # blows that way
                if random.random() < abs(uy) / (abs(ux) + abs(uy)):
                    x, y = random.uniform(0, BASE_W), -20 if uy > 0 else BASE_H + 20
                else:
                    x, y = -20 if ux > 0 else BASE_W + 20, random.uniform(0, BASE_H)
                speed, drift = random.uniform(300, 520), random.uniform(-60, 60)
                leaves.append([x, y, ux * speed - uy * drift, uy * speed + ux * drift,
                               random.uniform(0, math.tau), random.uniform(-4, 4), random.choice(self.LEAF_COLOURS),
                               random.uniform(10, 17), random.uniform(0, math.tau), -uy, ux])
        keep = []
        t = self.app.fx.time
        for leaf in leaves:
            sway = math.sin(t * 2.5 + leaf[8]) * 90         # (side to side, across the way it blows)
            across = leaf[9:11] if len(leaf) > 9 else (1.0, 0.0)
            leaf[0] += (leaf[2] + sway * across[0]) * dt
            leaf[1] += (leaf[3] + sway * across[1]) * dt
            leaf[4] += leaf[5] * dt
            if -40 < leaf[0] < BASE_W + 40 and -40 < leaf[1] < BASE_H + 40:
                keep.append(leaf)
                x, y, a, col, size = leaf[0], leaf[1], leaf[4], leaf[6], leaf[7]
                ca, sa = math.cos(a), math.sin(a)
                pts = [(x + ca * size, y + sa * size), (x - sa * size * 0.45, y + ca * size * 0.45),
                       (x - ca * size, y - sa * size), (x + sa * size * 0.45, y - ca * size * 0.45)]
                pygame.draw.polygon(screen, col, pts)
                pygame.draw.polygon(screen, (70, 36, 12), pts, 2)
                pygame.draw.line(screen, (90, 50, 20), pts[0], pts[2], 1)
        self._leaves[:] = keep[-320:]

    LEAF_COLOURS = ((214, 96, 32), (236, 150, 40), (190, 52, 30), (240, 196, 70), (160, 90, 40))

    def draw_night(self, screen, game, level, ox, oy):
        """Lantern Night: the court goes dark but for lantern light round each paddle and each
        ball's own glow."""
        if self._night is None or self._night.get_size() != (BASE_W, BASE_H):
            self._night = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
        dark = self._night
        dark.fill((6, 4, 16, int(236 * level)))
        lights = [((o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2, PowerUps.LANTERN_LIGHT) for o in (game.p1, game.p2)]
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
        pygame.draw.circle(ring, (*tint, 200), (c, c), d // 2)          # properly red, or blue, all over
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

    def draw_goal_alerts(self, screen, game, powerups):
        """Goals lit up by power-ups.  Under Twin Balls each goal pulses in the colour of the ball
        that can score in it; with a Snowball, a paddle being shoved back at its own goal lights
        that goal up, so it's clear what's about to happen."""
        t = self.app.fx.time
        court = {item[0] for item in powerups.court_list()}
        if "twin" in court:
            # Red's goal is where the blue ball scores, and Blue's where the red one does: a flashing
            # band of that colour along each goal line (a Switch can put Blue's goal on the left)
            k = math.sin(t * 5) * .5 + .5
            red, blue = (232, 70, 40), (60, 130, 255)
            left = red if game.p1.colour == "blue" else blue
            for side, tint in (("left", left), ("right", blue if left == red else red)):
                band = self.art.get(("goal_band", tint, side), self._goal_band, tint, side)
                band.set_alpha(int(110 + 145 * k))
                screen.blit(band, (0 if side == "left" else BASE_W - band.get_width(), 0))
                band.set_alpha(255, pygame.RLEACCEL)
        if "snowball" in court:
            for paddle in (game.p1, game.p2):
                if self.shoved_home(paddle):
                    side = "left" if paddle.is_left else "right"
                    strip = self.art.goal_glow(side, (210, 236, 255), 4 + round(2 * (math.sin(t * 14) * .5 + .5)))
                    for _ in range(2):
                        screen.blit(strip, (0 if side == "left" else BASE_W - strip.get_width(), 0), special_flags=ADD)

    @staticmethod
    def _goal_band(tint, side):
        """Twin Balls: a band of colour down a goal line, solid at the edge and fading inwards."""
        band = blank(28, BASE_H)
        for x in range(28):
            a = 255 if x < 10 else int(255 * (1 - (x - 10) / 18))
            pygame.draw.line(band, (*tint, a), (x, 0), (x, BASE_H))
        return band if side == "left" else pygame.transform.flip(band, True, False)

    def shoved_home(self, paddle):
        """Is a Snowball's shove carrying this paddle back at its own goal?  The host's game knows;
        on the joining player's screen and in replays, it's a paddle going back fast near its goal."""
        gap = paddle.x0 if paddle.is_left else BASE_W - paddle.x1
        speed = self.paddle_velocity(paddle)
        back = -speed if paddle.is_left else speed
        shoved = getattr(paddle, "shoved", None)
        if shoved is not None:
            return shoved > 0 and back > 100 and gap < 500
        return back > 250 and gap < 400

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
        self.draw_arena(screen, ox, oy, game.wall_up, cord=not open_court, flipped=game.p1.colour == "blue")
        for side in getattr(game, "closed", ()):        # Practice Mode's wall, and Goals off's (1.9)
            self.draw_practice_wall(screen, side == "left", ox, oy)
        if powerups:
            self.draw_goal_alerts(screen, game, powerups)
        for obj in game.objects:
            if getattr(obj, "is_obstacle", False):
                self.draw_stone(screen, obj, ox, oy)
        night = powerups.lantern_level() if powerups and hasattr(powerups, "lantern_level") else 0.0
        if powerups:
            self.draw_portals(screen, powerups, ox, oy)
            self.draw_holes(screen, powerups, ox, oy)
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
                self.draw_portals(screen, powerups, ox, oy)     # portals and talismans glow in the dark
                self.draw_holes(screen, powerups, ox, oy)
                self.draw_pickups(screen, powerups, ox, oy)
            self.draw_cracker_count(screen, game, powerups, ox, oy)
            self.draw_blasts(screen, powerups, ox, oy)
            self.draw_ploughs(screen, powerups, ox, oy)
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

            # first serve, or just after a Switch: remind players who has which paddle
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

    PRACTICE_WALL = 30          # px (as Hu_Taong.PRACTICE_WALL)

    def draw_practice_wall(self, screen, left, ox, oy):
        """Practice Mode's wall, or a goal closed with Goals off (1.9): a lacquered wall down that end
        of the court."""
        sprite = self.art.stone(self.PRACTICE_WALL, BASE_H, "pillar")
        screen.blit(sprite, (int((0 if left else BASE_W - self.PRACTICE_WALL) + ox), int(oy)))

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

    def draw_ploughs(self, screen, powerups, ox, oy):
        """A big Snowball ploughs through a Tombstone (1.8): a flash of snow, a ring of frost racing
        out, and chunks of stone and snow flung away and falling.  (Each burst is drawn the same
        way every time, from where it was, so replays and the friend's screen match.)"""
        ploughs = getattr(powerups, "ploughs", [])
        total = PowerUps.PLOUGH_TIME
        for x, y, age in ploughs:
            k = min(1.0, age / total)
            fade = 1 - k
            cx, cy = int(x + ox), int(y + oy)
            if k < 0.35:
                flash = self.art.glow(int(240 * (1 - k)) // 4 * 4 + 40, scaled((210, 235, 255), 1 - k / 0.35))
                screen.blit(flash, flash.get_rect(center=(cx, cy)), special_flags=ADD)
            for reach, width, tint in ((230, 9, (235, 246, 255)), (150, 5, (170, 210, 255))):
                r = int(18 + reach * (1 - (1 - k) ** 2))
                if r > 4 and fade > 0.05:
                    ring = pygame.Surface((r * 2 + 20, r * 2 + 20), pygame.SRCALPHA)
                    pygame.draw.circle(ring, (*tint, int(210 * fade)), (r + 10, r + 10), r, max(2, int(width * fade)))
                    screen.blit(ring, ring.get_rect(center=(cx, cy)))
            rng = random.Random(int(x) * 7919 + int(y) * 104729)
            for _ in range(14):
                a, speed, size = rng.uniform(0, math.tau), rng.uniform(240, 640), rng.uniform(5, 13) * (0.4 + 0.6 * fade)
                spin = rng.uniform(-9, 9) * age
                px = cx + math.cos(a) * speed * age
                py = cy + math.sin(a) * speed * age + 700 * age * age
                tint = (236, 246, 255) if rng.random() < 0.4 else (172, 156, 128)
                ca, sa = math.cos(spin) * size, math.sin(spin) * size
                pygame.draw.polygon(screen, tint, [(px + ca, py + sa), (px - sa * 0.7, py + ca * 0.7),
                                                   (px - ca, py - sa), (px + sa * 0.7, py - ca * 0.7)])

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
            # from the face itself, even when the ball hangs off the paddle's end
            start = (face + ox, min(max(cy + dy * r * 1.2, paddle.y0 + oy), paddle.y1 + oy))
            end = (cx - stuck["side"] * r * 0.6, cy + dy * r * 0.7)
            pygame.draw.line(screen, (150, 176, 40), start, end, width + 2)
            pygame.draw.line(screen, (204, 230, 80), start, end, width)
        # The aim: an arrow from the ball the way it will be slung (moving the paddle aims it)
        angle = PowerUps.sling_angle(paddle, stuck)
        dx, dy = stuck["side"] * math.cos(angle), math.sin(angle)
        tail = (cx + dx * (r + 10), cy + dy * (r + 10))
        tip = (cx + dx * (r + 70), cy + dy * (r + 70))
        pulse = 1.0 if "aim" in stuck else 0.6 + 0.4 * math.sin(self.app.fx.time * 10)   # (steady: locked)
        colour = (int(214 + 41 * pulse), int(236 + 19 * pulse), 120 + 100 * ("aim" in stuck))
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
        """A mid-rally Switch is armed: both paddles glow, each saying who takes it over, and the
        next hit sets it off."""
        art = self.art
        W, H = BASE_W, BASE_H
        pulse = .5 + .5 * math.sin(self.app.fx.time * 12)

        sign = art.gilded("换", art.brush(250), thickness=0, top=(255, 226, 170), bottom=(214, 96, 40))
        sign.set_alpha(int(70 + 120 * pulse))
        screen.blit(sign, sign.get_rect(center=(W // 2, H // 2 - 40)))
        self.text(screen, "Swap on the next hit", self.fnt(0.034), theme.FLAME, center=(W // 2, H // 2 + 110))

        font = self.fnt(0.024)
        for paddle, other in ((game.p1, game.p2), (game.p2, game.p1)):
            rect = pygame.Rect(int(paddle.x0), int(paddle.y0), int(paddle.width), int(paddle.height))
            halo = art.paddle_glow(rect.w, rect.h, paddle.colour)
            halo.set_alpha(int(255 * pulse))
            screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
            halo.set_alpha(255, pygame.RLEACCEL)

            # who takes this paddle over: whoever plays the other one now
            text = f"{'AI' if other.ai_enabled else other.controls_label} takes over"
            tw = font.size(text)[0] + 30
            plate = pygame.Rect(0, 0, tw, 40)
            plate.midbottom = (rect.centerx, rect.top - 14)
            plate.clamp_ip(pygame.Rect(8, 8, W - 16, H - 16))
            screen.blit(art.inset(plate.w, plate.h), plate)
            self.text(screen, text, font, theme.FLAME, center=plate.center)

    def draw_switch_banner(self, screen, left, text="换 Swap!"):
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
            held = "Tab"
            if self.using_pad():                # (a controller's button for it, 1.9)
                held = self.app.gamepads.label(self.app.settings.gameplay.pad_list)
            text = f"Hold {held} to see every talisman in play"
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
                arrows = getattr(state, "button_arrows", {})        # (1.9: e.g. Reset's, in the pause menu)
                nodes = [Button(key, text, bf, (c1, c2), tip=tips.get(key), arrow=arrows.get(key))
                         for key, text, c1, c2 in buttons]
                rows = [nodes[i:i + cols] for i in range(0, len(nodes), cols)]
                items.append(Grid(rows, gap_x=int(BASE_W * 0.015 * s), gap_y=int(ui.gap * s), uniform=True))
            if jukebox:
                jf, js = ui.fnt(0.03, s), ui.fnt(0.024, s)
                items.append(Stack([Label("Jukebox", ui.fnt(0.03, s)),
                                    *self.jukebox_controls(state, jf, js, int(BASE_W * 0.16 * s))],
                                   gap=int(ui.gap * 0.7 * s)))
            return Stack(items, gap=int(ui.gap * 1.6 * s))

        ui.overlay(state, screen, build, dim=dim, mark=mark)
