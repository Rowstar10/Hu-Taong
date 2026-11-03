import math, random, pygame
from collections import deque

from config import BASE_W, BASE_H
from helpers import clamp01, lerp
from render import theme
from render.art import ADD, blank, mix, scaled
from core.settings import key_name
from render.ui.layout import (Stack, Grid, Text, Label, Title, Button, Toggle, CycleToggle, KeyButton,
                              Cycle, Slider, Slot, Space)

# What each control does, shown when the mouse rests on it
TIPS = {
    # Main menu and the settings hub
    "play": "Choose your opponent and paddle, then start a match.",
    "stats": "Your lifetime record: wins, streaks, longest rally and more.",
    "settings": "Display, gameplay, sound and interface options.",
    "prompt_quit": "Close the game. Settings and stats are saved.",
    "display": "Window size, frame rate, background and dimming.",
    "gameplay": "The AI, match rules, ball and paddle tuning, and the Chaos modes.",
    "audio": "Volume, sound effects and the music jukebox.",
    "interface": "Tooltips, HUD, effects, countdown and key bindings.",
    "reset_all": "Put every setting in every menu back to its default. Your stats are kept.",

    # Match setup
    "opponent_ai": "Play against the AI.",
    "opponent_human": "Two players sharing one keyboard.",
    "start_match": "Start with the current gameplay settings.",

    # Gameplay
    "cycle_ai": "How quickly the AI reacts and how well it reads the ball.",
    "toggle_adaptive_ai": "The AI eases off while it's ahead and sharpens up when it's behind, to keep matches close.",
    "cycle_win_score": "Points needed to win. Endless Mode never ends.",
    "toggle_win_by_two": "The winner needs a two-point lead.",
    "toggle_middle_wall": "On: each paddle stays in its own half. Off: paddles can roam the whole court.",
    "ball_speed_slider": "How fast the ball is served.",
    "paddle_speed_slider": "How fast the paddles move.",
    "ball_diameter_slider": "How big the ball is.",
    "paddle_size_slider": "How tall and wide the paddles are.",
    "randomise_all": "Random ball and paddle speeds and sizes.",
    "cycle_chaos_mode": "Click to cycle. Chaos Mode: new random sizes and speeds every round. "
                        "Chaos Mode +: sizes and speeds keep drifting during play, separately for each paddle and the ball.",
    "cycle_chaos_switch": "Click to cycle. Chaos Switch: after every point you take over your opponent's paddle "
                          "and they take yours, scores and all. Chaos Switch +: the swap comes at random moments "
                          "mid-rally, with a warning first. Best with the Middle Wall off.",

    # Display
    "cycle_res": "Window size. Press Apply to use it.",
    "cycle_mode": "Windowed, borderless or fullscreen. Press Apply to use it.",
    "apply": "Use the resolution and window mode above.",
    "cycle_max_fps": "Frame-rate cap. Lower saves power; higher is smoother.",
    "toggle_show_fps": "Show the frame rate in the corner.",
    "background_thumb": "Choose the background.",
    "toggle_rotate_bg": "Fade to a different background every 30 to 60 seconds.",
    "dim_slider": "Darken the background so the ball stands out.",

    # Audio
    "master_volume_slider": "Overall volume.",
    "music_volume_slider": "Music volume.",
    "sfx_volume_slider": "Sound effect volume.",
    "toggle_paddle_sounds": "The sound each paddle makes when it hits the ball.",
    "toggle_score_sounds": "The sound when a point is scored.",
    "cycle_music": "Skip through tracks that suit the moment: calm in menus, upbeat in matches.",
    "randomise_music": "Play a random track for this moment.",
    "toggle_loop_music": "Loop repeats the current track. Shuffle plays another when it ends.",

    # Interface
    "toggle_tooltips": "Show these explanations when you rest the mouse on a control.",
    "toggle_ai_banter": "The AI teases you when it scores and grumbles when it doesn't.",
    "toggle_screen_shake": "Shake the screen when a point is scored.",
    "toggle_ball_trail": "A fire trail behind the ball.",
    "toggle_auto_pause": "Pause the match if you click away from the game window.",
    "toggle_hide_cursor": "Hide the mouse during a match until you move it.",
    "cycle_hud": "Full shows scores, rally and ball speed. Minimal shows just the scores.",
    "cycle_effects": "Butterflies, embers, petals and bursts. Turn them down if they distract or slow the game.",
    "cycle_countdown": "How long the countdown before each serve lasts.",
    "key": "Click, then press the new key. Esc cancels. A key that's already used swaps over.",

    # Stats
    "reset_stats": "Clear every lifetime stat. This can't be undone.",
}

STYLE_TIPS = {
    "Balanced": "Balanced: a steady all-rounder.",
    "Guardian": "Guardian: hangs back and defends. Rarely misses, rarely attacks.",
    "Striker": "Striker: steps in to meet the ball and fires sharp angles. "
               "With the Middle Wall off it charges past halfway.",
    "Trickster": "Trickster: feints one way, goes the other, and aims for the corners.",
}


class Tooltips:
    """Short explanations that appear when the mouse rests on a control."""

    DELAY = 0.45
    WIDTH = 470

    def __init__(self, app):
        self.app = app
        self.offered = None
        self.text = None
        self.rest = 0.0
        self.cache = {}

    def offer(self, rect, text):
        if text and rect.collidepoint(self.app.renderer.mouse()):
            self.offered = text

    def surface(self, text):
        surf = self.cache.get(text)
        if surf is None:
            art = self.app.art
            font = art.ui(24, bold=False)
            lines, line = [], ""
            for word in text.split():
                trial = f"{line} {word}".strip()
                if line and font.size(trial)[0] > self.WIDTH:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            lines.append(line)

            pad, flower = 14, art.blossom(24)
            step = font.get_linesize()
            w = max(font.size(l)[0] for l in lines) + 3 * pad + flower.get_width()
            h = step * len(lines) + 2 * pad
            surf = blank(w, h)
            surf.blit(art.inset(w, h), (0, 0))
            surf.blit(flower, (pad, pad + (step - flower.get_height()) // 2))
            for i, l in enumerate(lines):
                surf.blit(font.render(l, True, theme.PARCHMENT), (2 * pad + flower.get_width(), pad + i * step))
            self.cache[text] = surf
        return surf

    def draw(self, screen, dt):
        text, self.offered = self.offered, None
        if text is None or not self.app.settings.interface.tooltips:
            self.text, self.rest = None, 0.0
            return
        if text != self.text:
            self.text, self.rest = text, 0.0
        self.rest += dt
        if self.rest < self.DELAY:
            return

        surf = self.surface(text)
        surf.set_alpha(int(255 * min(1.0, (self.rest - self.DELAY) / 0.15)))
        mx, my = self.app.renderer.mouse()
        x, y = mx + 20, my + 28
        if x + surf.get_width() > BASE_W - 8:
            x = mx - surf.get_width() - 12
        if y + surf.get_height() > BASE_H - 8:
            y = my - surf.get_height() - 12
        screen.blit(surf, (max(8, x), max(8, y)))


class Renderer:
    def __init__(self, app):
        self.app = app
        self.art = app.art

        self._sigil_cache: dict = {}
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
        return self.app.window_to_base(pygame.mouse.get_pos())

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
        down = hovered and pygame.mouse.get_pressed()[0]
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
        col = theme.FLAME if hot else theme.GOLD_BRIGHT if on else theme.GRAY
        centre = rect.x + size + 20 + (rect.w - size - 28) // 2
        self.text(screen, text, font, col, center=(centre, rect.centery - 3 + offset))

    def draw_board(self, screen, rect, mark=None):
        """The lacquered panel, with an optional faint character across it."""
        m = self.art.PANEL_MARGIN
        screen.blit(self.art.panel(rect.w, rect.h), (rect.x - m, rect.y - m))
        if mark:
            sprite = self.art.watermark(mark, min(400, int(rect.h * .8)), 26)
            screen.blit(sprite, sprite.get_rect(center=rect.center))

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
        """Slowly turning seal; re-rotated 10 times a second, as a full rotozoom is costly."""
        tick = int(self.app.fx.time * 10)
        cached = self._sigil_cache.get(size)
        if cached is None or cached[0] != tick:
            sprite = pygame.transform.rotozoom(self.art.sigil(size), tick / 10 * speed, 1)
            cached = self._sigil_cache[size] = (tick, sprite)
        sprite = cached[1]
        sprite.set_alpha(alpha)
        screen.blit(sprite, sprite.get_rect(center=center))

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
                lambda: art.panel(360, 540),
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
            w = round((g.paddle_width_min + t * g.paddle_width_range) / 2) * 2
            for finish in ("red", "blue"):
                jobs.append(lambda w=w, h=h, finish=finish: (art.paddle(w, h, finish), art.paddle_glow(w, h, finish)))
        for d in range(g.ball_diameter_min, g.ball_diameter_max + 1, 2):
            jobs.append(lambda d=d: art.ball(d))

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

        self.text(screen, "Enter to play   ·   Esc to quit", self.fnt(0.024, bold=False),
                  theme.GOLD, center=(cx, 944))

    # ── Match setup ────────────────────────────────────────────────────────────

    def draw_match_setup_menu(self, state, screen):
        ui = self.ui
        g = self.app.settings.gameplay
        red_keys = self.app.settings.interface.keys_label("p1")
        blue_keys = self.app.settings.interface.keys_label("p2")
        tips = dict(TIPS, side_red=f"Play Red, the left paddle ({red_keys}).",
                    side_blue=f"Play Blue, the right paddle ({blue_keys}).")

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
                choice("opponent_ai",    "vs AI",    lambda: g.vs_ai),
                choice("opponent_human", "vs Human", lambda: not g.vs_ai)],
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
            return Stack([opponent, paddle, caption, start], gap=self.vgap(ui, s, 2))

        ui.screen_menu(state, screen, build, title="对局 Match Setup", mark="战")

    # ── Settings menu ──────────────────────────────────────────────────────────

    def draw_card(self, state, screen, mouse_pos, key, x, mark, label, finish):
        w, h = 360, 540
        hit = pygame.Rect(x, 240, w, h)
        hovered = hit.collidepoint(mouse_pos)
        rise = self.lift(key, hovered)
        y = hit.y - rise * 16
        m = self.art.PANEL_MARGIN

        if rise > .02:
            halo = self.art.glow(330, scaled((110, 40, 18), rise))
            screen.blit(halo, halo.get_rect(center=(x + w // 2, y + h // 2)), special_flags=ADD)

        screen.blit(self.art.panel(w, h), (x - m, y - m))
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
            f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.02, s)
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
            ai = self.section(ui, s, "AI",
                              Cycle("cycle_ai", lambda: levels[g.ai_difficulty], f, levels, ai_col,
                                    tip=TIPS["cycle_ai"]),
                              Cycle("cycle_ai_style", lambda: styles[g.ai_style], f, styles,
                                    tip=lambda: STYLE_TIPS[g.ai_styles[g.ai_style]]),
                              self.toggle(sm, "toggle_adaptive_ai", "Adaptive AI", lambda: g.adaptive_ai))
            win = self.section(ui, s, "Match Rules",
                               Cycle("cycle_win_score", lambda: win_texts[g.winning_score_index],
                                     f, win_texts, win_col, tip=TIPS["cycle_win_score"]),
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

            rand = Button("randomise_all", "Randomise All", sm, (G, theme.GREEN_HOVER), tip=TIPS["randomise_all"])
            chaos = CycleToggle("cycle_chaos_mode", ["Chaos Mode: Off", "Chaos Mode", "Chaos Mode +"], sm,
                                lambda: g.chaos_mode, "关乱狂", tip=TIPS["cycle_chaos_mode"])
            switch = CycleToggle("cycle_chaos_switch", ["Chaos Switch: Off", "Chaos Switch", "Chaos Switch +"], sm,
                                 lambda: g.chaos_switch, "关换狂", tip=TIPS["cycle_chaos_switch"])
            actions = Stack([rand, chaos, switch], vertical=False, gap=int(BASE_W * 0.02 * s))

            return Grid([[ai, win],
                         [ball_speed, paddle_speed],
                         [ball_size, paddle_size],
                         [actions]],
                        gap_x=int(BASE_W * 0.06 * s), gap_y=self.vgap(ui, s, 1.9))

        ui.screen_menu(state, screen, build, title="玩法 Gameplay", mark="玩", reset="Reset to Default")

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

            background = self.section(
                ui, s, "Background",
                Slot("background_thumb", int(256 * s), int(144 * s), tip=TIPS["background_thumb"]),
                self.toggle(sm, "toggle_rotate_bg", "Rotate", lambda: d.rotate_backgrounds))

            dim = self.section(
                ui, s, "Dim Overlay",
                Slider("dim_slider", lambda: d.dim, theme.EMBER, sm, lambda: f"{int(100 * d.dim)}%", "100%",
                       track_w=int(BASE_W * 0.17 * s), tip=TIPS["dim_slider"]))

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
            f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.02, s)
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
                       self.toggle(sm, "toggle_score_sounds",  "Score Sound",   lambda: sound.score_sound)],
                      vertical=False, gap=int(BASE_W * 0.01 * s))],
                gap=self.vgap(ui, s, 1.4))

            jukebox = self.section(
                ui, s, "Music",
                Cycle("cycle_music", lambda: audio.track_name(sound.now_playing), f,
                      [audio.track_name(t) for t in audio.all_tracks], tip=TIPS["cycle_music"]),
                Stack([Button("randomise_music", "Randomise Music", sm, (B, theme.BLUE_HOVER),
                              tip=TIPS["randomise_music"]),
                       Toggle("toggle_loop_music", lambda: "Loop" if audio.loop_music else "Shuffle", sm,
                              lambda: audio.loop_music, ["Loop", "Shuffle"], tip=TIPS["toggle_loop_music"])],
                      vertical=False, gap=int(BASE_W * 0.01 * s)),
                Text(lambda: mood_notes[sound.mood], ty, theme.GOLD, samples=list(mood_notes.values())))

            return Grid([[volumes, jukebox]], gap_x=int(BASE_W * 0.04 * s))

        ui.screen_menu(state, screen, build, title="音频 Audio", mark="音", reset="Reset to Default")

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
                    ("Time Played",         lambda: st.format_time(st.play_time))]
            table = Grid([[Text(label, f, theme.GOLD, align="right"),
                           Text(value, f, theme.PARCHMENT, align="left",
                                samples=["Red 9999  -  9999 Blue", "9999  (best 9999)"])]
                          for label, value in rows],
                         gap_x=int(BASE_W * 0.03 * s), gap_y=int(ui.gap * 0.5 * s))
            return Stack([table, Button("reset_stats", "Reset Stats", sm, (theme.RED, theme.RED_HOVER),
                                        tip=TIPS["reset_stats"])],
                         gap=self.vgap(ui, s, 1.4))

        ui.screen_menu(state, screen, build, title="战绩 Stats", mark="绩")

    # ── Interface settings ─────────────────────────────────────────────────────

    def draw_interface_settings_menu(self, state, screen):
        ui = self.ui
        i = self.app.settings.interface

        def build(s):
            f, sm, ty = ui.fnt(0.032, s), ui.fnt(0.028, s), ui.fnt(0.02, s)

            def flag(name, attr):
                return self.toggle(sm, f"toggle_{attr}", name, lambda: getattr(i, attr))

            toggles = Grid([[flag("Tooltips", "tooltips"), flag("AI Banter", "ai_banter")],
                            [flag("Screen Shake", "screen_shake"), flag("Ball Trail", "ball_trail")],
                            [flag("Auto-Pause", "auto_pause"), flag("Hide Mouse", "hide_cursor")]],
                           gap_x=int(BASE_W * 0.012 * s), gap_y=int(ui.gap * 0.8 * s), uniform=True)

            def cycle(name, title, texts):
                return [Text(title, sm, theme.GOLD, align="right"),
                        Cycle(f"cycle_{name}", lambda: texts[getattr(i, name)], f, texts, tip=TIPS[f"cycle_{name}"])]

            seconds = [f"{n} second{'s' if n != 1 else ''}" for n in i.countdown_options]
            cycles = Grid([cycle("hud", "HUD", i.hud_options),
                           cycle("effects", "Effects", i.effects_options),
                           cycle("countdown", "Countdown", seconds)],
                          gap_x=int(BASE_W * 0.012 * s), gap_y=int(ui.gap * 0.8 * s))

            left = self.section(ui, s, "Interface", toggles, cycles)

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

    def show_toast(self, text):
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
        self._toast = [surf, 0.0]

    def draw_toast(self, screen, dt):
        """Slides in at the bottom-left, holds, then fades out."""
        if self._toast is None:
            return
        surf, age = self._toast
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

    def draw_arena(self, screen, ox, oy, wall=True):
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

        cord = art.cord(H, faint=not wall)
        screen.blit(cord, cord.get_rect(midtop=(W // 2 + ox, oy)))

        rail = art.rail(W, flowers=False)
        screen.blit(rail, rail.get_rect(midtop=(W // 2 + ox, oy - 4)))
        screen.blit(rail, rail.get_rect(midbottom=(W // 2 + ox, H + oy + 4)))

    def draw_paddle(self, screen, paddle, rect):
        finish = "red" if paddle.is_left else "blue"
        # Sprites come in 2-4 px steps, so a size that keeps drifting (Chaos Mode +) reuses them
        centre = rect.center
        rect = pygame.Rect(0, 0, max(4, round(rect.w / 2) * 2), max(8, round(rect.h / 4) * 4))
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

    def draw_ball(self, screen, ball, rect, ox, oy):
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        r = rect.w // 2

        trail = self._trail
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

        # Soul-fire tail in the colour of whoever hit it last, oldest and faintest first
        paddle = getattr(ball, "last_paddle", None)
        fire = (40, 96, 220) if paddle and not paddle.is_left else (200, 60, 22)
        count = len(trail)
        for i, (x, y) in enumerate(list(trail)):
            k = (i + 1) / count
            level = 1 + int(k * 5)
            radius = max(6, int(r * (.5 + 1.0 * k)) // 4 * 4)
            glow = self.art.glow(radius, scaled(fire, (level / 6) ** 2))
            screen.blit(glow, (x + ox - radius, y + oy - radius), special_flags=ADD)

        halo = self.art.glow(max(24, int(r * 2.6) // 4 * 4), scaled(fire, .75))
        screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
        sprite = self.art.ball(max(8, round(rect.w / 2) * 2))
        screen.blit(sprite, sprite.get_rect(center=rect.center))

    def draw_world(self, screen, game):
        W, H = BASE_W, BASE_H
        ox, oy = self._shake_offset()
        self.draw_arena(screen, ox, oy, game.settings.middle_wall)

        for obj in game.objects:
            rect = pygame.Rect(int(obj.x0 + ox), int(obj.y0 + oy), int(obj.width), int(obj.height))
            if obj.is_ball:
                self.draw_ball(screen, obj, rect, ox, oy)
            elif obj.is_paddle:
                self.draw_paddle(screen, obj, rect)

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

            # first serve, or just after a Chaos Switch: remind players who has which paddle
            if game.p1.score + game.p2.score == 0 or game.settings.chaos_switch == 1:
                self._draw_controls_hint(screen, game)

        if getattr(game, "switch_flash", 0) > 0:
            self.draw_switch_banner(screen, game.switch_flash)

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
        for paddle, other, glow in ((game.p1, game.p2, "blue"), (game.p2, game.p1, "red")):
            rect = pygame.Rect(int(paddle.x0), int(paddle.y0), int(paddle.width), int(paddle.height))
            halo = art.paddle_glow(rect.w, rect.h, glow)
            halo.set_alpha(int(255 * pulse))
            screen.blit(halo, halo.get_rect(center=rect.center), special_flags=ADD)
            halo.set_alpha(255)

            # who takes this paddle when the swap happens
            text = "Next: " + ("AI" if other.ai_enabled else other.controls_label)
            tw = font.size(text)[0] + 30
            plate = pygame.Rect(0, 0, tw, 40)
            plate.midbottom = (rect.centerx, rect.top - 14)
            plate.clamp_ip(pygame.Rect(8, 8, W - 16, H - 16))
            screen.blit(art.inset(plate.w, plate.h), plate)
            self.text(screen, text, font, theme.FLAME, center=plate.center)

    def draw_switch_banner(self, screen, left):
        w, h = 520, 120
        m = self.art.PLAQUE_MARGIN
        y = int(BASE_H * 0.3)
        board = self.art.plaque(w, h)
        words = self.art.gilded("换 Switch!", self.brush(0.075), glow=None)
        alpha = int(255 * min(1.0, left / 0.3))
        board.set_alpha(alpha)
        words.set_alpha(alpha)
        screen.blit(board, (BASE_W // 2 - w // 2 - m, y - h // 2 - m))
        screen.blit(words, words.get_rect(center=(BASE_W // 2, y)))
        board.set_alpha(255)
        words.set_alpha(255)

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
        surf.set_alpha(255)

    def draw_countdown(self, screen, countdown):
        W, H = BASE_W, BASE_H
        v = countdown.shown_value
        beat = clamp01(countdown.remaining - (v - 1))       # 1 falling to 0 on each number

        mark = {3: "三", 2: "二", 1: "一"}.get(v)
        if mark:
            sprite = self.art.gilded(mark, self.art.brush(420), thickness=0, top=(120, 30, 30), bottom=(70, 14, 18))
            sprite.set_alpha(170)
            screen.blit(sprite, sprite.get_rect(center=(W // 2, H // 2)))

        digit = self.art.gilded("GO!" if v == 0 else str(v), self.art.ui(230), thickness=6)
        k = 1 + .55 * beat ** 3
        size = (int(digit.get_width() * k), int(digit.get_height() * k))
        scaled_digit = pygame.transform.smoothscale(digit, size)
        screen.blit(scaled_digit, scaled_digit.get_rect(center=(W // 2, H // 2)))

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

    # ── Overlay ────────────────────────────────────────────────────────────────

    def draw_overlay(self, state, screen, *, title=None, header=None, buttons=None,
                     title_size=0.08, header_size=0.05, btn_size=0.045,
                     title_color=theme.GOLD_BRIGHT, dim=True, mark=None, toggles=None, tips=None):
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
            return Stack(items, gap=int(ui.gap * 1.6 * s))

        ui.overlay(state, screen, build, dim=dim, mark=mark)
