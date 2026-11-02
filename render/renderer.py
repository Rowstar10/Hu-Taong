import math, random, pygame
from collections import deque

from config import BASE_W, BASE_H
from render import theme
from render.theme import color
from helpers import lerp
from render.ui.layout import (Stack, Grid, Text, Button, Cycle, Slider, Slot, Space)

class Renderer:
    def __init__(self, app):
        self.app = app

        self.title_font     = app.font_manager.get("helvetica", 100, bold=True)
        self.countdown_font = app.font_manager.get("helvetica", 80,  bold=True)

        # Game feel: all purely visual, none of it touches the physics.
        self._toast = None              # [surface, age]
        self._shake_time = 0.0
        self._shake_total = 0.0
        self._shake_mag = 0
        self._trail = deque(maxlen=10)
        self._trail_sprites = {}

    # ── Shorthands ─────────────────────────────────────────────────────────────
    # Menus are *described* here (what is on the screen); UILayout decides where
    # everything goes.  See render/ui/layout.py.

    @property
    def ui(self):
        return self.app.ui_layout

    def section(self, ui, s, header, col, *controls):
        """A coloured header with its controls underneath."""
        return Stack([Text(header, ui.fnt(0.05, s), col), *controls], gap=int(ui.gap * 0.9 * s))

    def vgap(self, ui, s, mult=1.0):
        return int(ui.gap * mult * s)

    # ── Main menu ──────────────────────────────────────────────────────────────

    def draw_main_menu(self, state, screen):
        ui = self.ui

        def build(s):
            f = ui.fnt(0.06, s)
            return Stack([Button("play",        "Play Game", f, (theme.GREEN,  theme.GREEN_HOVER)),
                          Button("stats",       "Stats",     f, (theme.BLUE,   theme.BLUE_HOVER)),
                          Button("settings",    "Settings",  f, (theme.ORANGE, theme.ORANGE_HOVER)),
                          Button("prompt_quit", "Quit Game", f, (theme.RED,    theme.RED_HOVER))],
                         gap=self.vgap(ui, s, 1.5), uniform=True)

        ui.screen_menu(state, screen, build, title="Hu Taong!", color=theme.RED,
                       title_size=0.18, back=False)

    # ── Match setup ────────────────────────────────────────────────────────────

    def draw_match_setup_menu(self, state, screen):
        ui = self.ui
        g = self.app.settings.gameplay

        def build(s):
            f, sm = ui.fnt(0.05, s), ui.fnt(0.03, s)
            G = theme.GREEN
            gap = int(BASE_W * 0.02 * s)

            def choice(key, text, selected, on=(G, theme.GREEN_HOVER), enabled=lambda: True):
                def colors():
                    if not enabled():
                        return (theme.DARK_GRAY, theme.DARK_GRAY)    # greyed out, not clickable
                    return on if selected() else (theme.GRAY, theme.GRAY_HOVER)
                return Button(key, text, f, colors)

            opponent = self.section(ui, s, "Opponent", G, Stack([
                choice("opponent_ai",    "vs AI",    lambda: g.vs_ai),
                choice("opponent_human", "vs Human", lambda: not g.vs_ai)],
                vertical=False, gap=gap, uniform=True))

            vs_ai = lambda: g.vs_ai
            paddle = self.section(ui, s, "Your Paddle", G, Stack([
                choice("side_red",  "Red",  lambda: not g.play_as_blue, (theme.RED,  theme.RED_HOVER),  vs_ai),
                choice("side_blue", "Blue", lambda: g.play_as_blue,     (theme.BLUE, theme.BLUE_HOVER), vs_ai)],
                vertical=False, gap=gap, uniform=True))

            def summary():
                if not g.vs_ai:
                    return "Red: W A S D      Blue: Arrow Keys"
                me, ai = ("Blue", "Red") if g.play_as_blue else ("Red", "Blue")
                keys = "Arrow Keys" if g.play_as_blue else "W A S D"
                return f"You: {me} ({keys})      AI: {ai}"
            samples = ["You: Blue (Arrow Keys)      AI: Red", "Red: W A S D      Blue: Arrow Keys"]
            caption = Text(summary, sm, theme.WHITE, samples=samples)

            start = Button("start_match", "Start Match", ui.fnt(0.06, s), (theme.ORANGE, theme.ORANGE_HOVER))
            return Stack([opponent, paddle, caption, start], gap=self.vgap(ui, s, 2))

        ui.screen_menu(state, screen, build, title="Match Setup", color=theme.GREEN)

    # ── Settings menu ──────────────────────────────────────────────────────────

    def draw_settings_menu(self, state, screen):
        ui = self.ui

        def build(s):
            f = ui.fnt(0.06, s)
            return Stack([Button("display",  "Display",  f, (theme.ORANGE, theme.ORANGE_HOVER)),
                          Button("gameplay", "Gameplay", f, (theme.GREEN,  theme.GREEN_HOVER)),
                          Button("audio",    "Audio",    f, (theme.BLUE,   theme.BLUE_HOVER))],
                         vertical=False, gap=int(BASE_W * 0.02 * s), uniform=True)

        ui.screen_menu(state, screen, build, title="Settings", color=theme.ORANGE)

    # ── Gameplay settings ──────────────────────────────────────────────────────

    def draw_gameplay_settings_menu(self, state, screen):
        ui = self.ui
        g = self.app.settings.gameplay

        def build(s):
            f, sm, ty = ui.fnt(0.04, s), ui.fnt(0.03, s), ui.fnt(0.022, s)
            G = theme.GREEN
            track_w = int(BASE_W * 0.17 * s)

            label_sample = f"{g.paddle_height_max} x {g.paddle_width_max}"  # widest label; shared so tracks line up

            def slider(key, reset, value, lo, rng, label, sample=None):
                return Slider(key, lambda: (value() - lo) / rng, G, f, label, label_sample,
                              reset_key=reset, reset_font=ty, track_w=track_w)

            win_texts = ["Endless Mode" if v == "Endless Mode" else f"Score {v} to win"
                         for v in g.winning_scores]
            ai_col = lambda: (theme.GREEN if g.ai_difficulty == 0 else
                              theme.WHITE if g.ai_difficulty < len(g.ai_difficulties) - 1 else theme.RED)
            win_col = lambda: theme.ORANGE if g.winning_scores[g.winning_score_index] == "Endless Mode" else theme.WHITE

            ai = self.section(ui, s, "AI Difficulty", G,
                              Cycle("cycle_ai", lambda: g.ai_difficulties[g.ai_difficulty],
                                    f, g.ai_difficulties, ai_col),
                              Button("toggle_adaptive_ai",
                                     lambda: f"Adaptive AI: {'ON' if g.adaptive_ai else 'OFF'}", sm,
                                     lambda: ((theme.GREEN, theme.GREEN_HOVER) if g.adaptive_ai
                                              else (theme.RED, theme.RED_HOVER)),
                                     samples=["Adaptive AI: ON", "Adaptive AI: OFF"]))
            win = self.section(ui, s, "Winning Score", G,
                               Cycle("cycle_win_score", lambda: win_texts[g.winning_score_index],
                                     f, win_texts, win_col),
                               Button("toggle_win_by_two",
                                      lambda: f"Win by Two: {'ON' if g.win_by_two else 'OFF'}", sm,
                                      lambda: ((theme.GREEN, theme.GREEN_HOVER) if g.win_by_two
                                               else (theme.RED, theme.RED_HOVER)),
                                      samples=["Win by Two: ON", "Win by Two: OFF"]))

            ball_speed = self.section(ui, s, "Ball Speed", G, slider(
                "ball_speed_slider", "reset_ball_speed", lambda: g.ball_speed,
                g.ball_speed_min, g.ball_speed_range,
                lambda: str(int(g.ball_speed))))
            paddle_speed = self.section(ui, s, "Paddle Speed", G, slider(
                "paddle_speed_slider", "reset_paddle_speed", lambda: g.paddle_speed,
                g.paddle_speed_min, g.paddle_speed_range,
                lambda: str(int(g.paddle_speed))))
            ball_size = self.section(ui, s, "Ball Diameter", G, slider(
                "ball_diameter_slider", "reset_ball_diameter", lambda: g.ball_diameter,
                g.ball_diameter_min, g.ball_diameter_range,
                lambda: str(int(g.ball_diameter))))
            paddle_size = self.section(ui, s, "Paddle Size", G, slider(
                "paddle_size_slider", "reset_paddle_size", lambda: g.paddle_height,
                g.paddle_height_min, g.paddle_height_range,
                lambda: f"{int(g.paddle_height)} x {int(g.paddle_width)}"))

            rand = Button("randomise_all", "Randomise All", sm, (G, theme.GREEN_HOVER))
            reset = Button("reset_all", "Reset All", sm, (G, theme.GREEN_HOVER))
            chaos = Button("toggle_chaos_mode", lambda: f"Chaos Mode: {'ON' if g.chaos_mode else 'OFF'}", sm,
                           lambda: ((theme.ORANGE, theme.ORANGE_HOVER) if g.chaos_mode
                                    else (theme.RED, theme.RED_HOVER)),
                           samples=["Chaos Mode: ON", "Chaos Mode: OFF"])
            actions = Stack([rand, chaos, reset], vertical=False, gap=int(BASE_W * 0.015 * s))

            return Grid([[ai, win],
                         [ball_speed, paddle_speed],
                         [ball_size, paddle_size],
                         [actions]],
                        gap_x=int(BASE_W * 0.06 * s), gap_y=self.vgap(ui, s, 2.2))

        ui.screen_menu(state, screen, build, title="Gameplay", color=theme.GREEN)

    # ── Display settings ───────────────────────────────────────────────────────

    def draw_display_settings_menu(self, state, screen):
        ui = self.ui
        d = self.app.settings.display
        app = self.app

        def build(s):
            f, sm, ty = ui.fnt(0.04, s), ui.fnt(0.03, s), ui.fnt(0.022, s)
            O = theme.ORANGE

            res_texts = [f"{w} x {h}" for (w, h) in app.resolutions]
            mode_texts = [m.capitalize() for m in app.display_modes]

            resolution = self.section(
                ui, s, "Resolution", O,
                Cycle("cycle_res", lambda: res_texts[state.res_index], f, res_texts),
                Cycle("cycle_mode", lambda: mode_texts[state.display_mode_index], f, mode_texts),
                Button("apply", "Apply", sm, (O, theme.ORANGE_HOVER)))

            max_fps = self.section(
                ui, s, "Maximum FPS", O,
                Cycle("cycle_max_fps", lambda: str(d.max_fps_options[d.max_fps]), f,
                      [str(o) for o in d.max_fps_options]),
                Button("toggle_show_fps", lambda: f"Show FPS: {'ON' if d.show_fps else 'OFF'}", sm,
                       lambda: ((O, theme.ORANGE_HOVER) if d.show_fps else (theme.RED, theme.RED_HOVER)),
                       samples=["Show FPS: ON", "Show FPS: OFF"]))

            background = self.section(
                ui, s, "Background", O,
                Slot("background_thumb", int(256 * s), int(144 * s)),
                Button("toggle_rotate_bg", lambda: f"Rotate: {'ON' if d.rotate_backgrounds else 'OFF'}", sm,
                       lambda: ((O, theme.ORANGE_HOVER) if d.rotate_backgrounds else (theme.RED, theme.RED_HOVER)),
                       samples=["Rotate: ON", "Rotate: OFF"]))

            dim = self.section(
                ui, s, "Dim Overlay", O,
                Slider("dim_slider", lambda: d.dim, O, f, lambda: f"{int(100 * d.dim)}%", "100%",
                       track_w=int(BASE_W * 0.17 * s)))

            return Grid([[resolution, max_fps],
                         [background, dim]],
                        gap_x=int(BASE_W * 0.08 * s), gap_y=self.vgap(ui, s, 2.4))

        ui.screen_menu(state, screen, build, title="Display", color=theme.ORANGE)

    # ── Audio settings ─────────────────────────────────────────────────────────

    def draw_audio_settings_menu(self, state, screen):
        ui = self.ui
        sound = self.app.sound_manager
        audio = self.app.settings.audio

        def build(s):
            f, sm, ty = ui.fnt(0.04, s), ui.fnt(0.03, s), ui.fnt(0.022, s)
            B = theme.BLUE
            track_w = int(BASE_W * 0.2 * s)

            def volume(header, key, value):
                return self.section(ui, s, header, B, Slider(
                    key + "_slider", value, B, f, lambda: f"{int(round(100 * value()))}%", "100%",
                    reset_key="reset_" + key, reset_font=ty, track_w=track_w))

            def sound_toggle(key, name, flag):
                return Button(key, lambda: f"{name}: {'ON' if flag() else 'OFF'}", sm,
                              lambda: ((B, theme.BLUE_HOVER) if flag() else (theme.RED, theme.RED_HOVER)),
                              samples=[f"{name}: ON", f"{name}: OFF"])

            mood_notes = {"menu":    "Relaxed music for the menus",
                          "game":    "Upbeat music for matches",
                          "victory": "Triumphant music",
                          "defeat":  "Downbeat music"}

            volumes = Stack([
                volume("Master Volume", "master_volume", lambda: sound.master_volume),
                volume("Music Volume",  "music_volume",  lambda: sound.music_volume),
                volume("SFX Volume",    "sfx_volume",    lambda: sound.sfx_volume),
                Stack([sound_toggle("toggle_paddle_sounds", "Paddle Sounds", lambda: sound.paddle_hit_sound),
                       sound_toggle("toggle_score_sounds",  "Score Sound",   lambda: sound.score_sound)],
                      vertical=False, gap=int(BASE_W * 0.01 * s))],
                gap=self.vgap(ui, s, 1.4))

            jukebox = self.section(
                ui, s, "Music", B,
                Cycle("cycle_music", lambda: audio.track_name(sound.now_playing), f,
                      [audio.track_name(t) for t in audio.all_tracks]),
                Stack([Button("randomise_music", "Randomise Music", sm, (B, theme.BLUE_HOVER)),
                       Button("toggle_loop_music", lambda: "Loop" if audio.loop_music else "Shuffle", sm,
                              (B, theme.BLUE_HOVER), samples=["Loop", "Shuffle"])],
                      vertical=False, gap=int(BASE_W * 0.01 * s)),
                Text(lambda: mood_notes[sound.mood], ty, theme.WHITE, samples=list(mood_notes.values())))

            return Grid([[volumes, jukebox]], gap_x=int(BASE_W * 0.07 * s))

        ui.screen_menu(state, screen, build, title="Audio", color=theme.BLUE)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def draw_stats_menu(self, state, screen):
        ui = self.ui
        st = self.app.stats

        def build(s):
            f, sm = ui.fnt(0.035, s), ui.fnt(0.03, s)
            B = theme.BLUE
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
            table = Grid([[Text(label, f, B, align="right"),
                           Text(value, f, theme.WHITE, align="left",
                                samples=["Red 9999  -  9999 Blue", "9999  (best 9999)"])]
                          for label, value in rows],
                         gap_x=int(BASE_W * 0.03 * s), gap_y=int(ui.gap * 0.6 * s))
            return Stack([table, Button("reset_stats", "Reset Stats", sm, (theme.RED, theme.RED_HOVER))],
                         gap=self.vgap(ui, s, 2))

        ui.screen_menu(state, screen, build, title="Stats", color=theme.BLUE)

    # ── Game feel (purely visual) ──────────────────────────────────────────────

    def shake(self, magnitude, duration):
        self._shake_mag, self._shake_time, self._shake_total = magnitude, duration, duration

    def _shake_offset(self):
        if self._shake_time <= 0:
            return 0, 0
        self._shake_time = max(0.0, self._shake_time - self.app.dt)
        mag = self._shake_mag * self._shake_time / self._shake_total
        return random.uniform(-mag, mag), random.uniform(-mag, mag)

    def show_toast(self, text):
        font = self.ui.fnt(0.03)
        label = font.render(text, True, theme.WHITE)
        pad = int(BASE_H * 0.015)
        surf = pygame.Surface((label.get_width() + 2 * pad, label.get_height() + 2 * pad), pygame.SRCALPHA)
        pygame.draw.rect(surf, (20, 20, 20, 215), surf.get_rect(), border_radius=14)
        pygame.draw.rect(surf, (90, 90, 90, 255), surf.get_rect(), width=2, border_radius=14)
        surf.blit(label, (pad, pad))
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

    def _trail_sprite(self, diameter, i, rgb):
        key = (diameter, i, rgb)
        sprite = self._trail_sprites.get(key)
        if sprite is None:
            n = self._trail.maxlen
            size = max(4, int(diameter * (0.45 + 0.5 * (i + 1) / n)))
            sprite = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.ellipse(sprite, (*rgb, int(35 + 85 * (i + 1) / n)), sprite.get_rect())
            if len(self._trail_sprites) > 400:
                self._trail_sprites.clear()
            self._trail_sprites[key] = sprite
        return sprite

    def _draw_trail(self, screen, ball, ox, oy):
        cx, cy = (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2
        if self._trail:
            lx, ly = self._trail[-1]
            moved = math.hypot(cx - lx, cy - ly)
            if moved > ball.width * 4:          # ball respawned: don't smear across the court
                self._trail.clear()
            elif moved >= ball.width * 0.35:
                self._trail.append((cx, cy))
        else:
            self._trail.append((cx, cy))

        paddle = getattr(ball, "last_paddle", None)
        rgb = tuple(color(paddle.color1)) if paddle else (255, 255, 255)
        d = int(ball.width)
        for i, (x, y) in enumerate(list(self._trail)[:-1]):
            sprite = self._trail_sprite(d, i, rgb)
            screen.blit(sprite, (int(x + ox - sprite.get_width() / 2), int(y + oy - sprite.get_height() / 2)))

    # ── Game world ─────────────────────────────────────────────────────────────

    def draw_world(self, screen, game):
        W, H = BASE_W, BASE_H
        ox, oy = self._shake_offset()
        pygame.draw.line(screen, (160, 160, 160), (W // 2 + ox, oy), (W // 2 + ox, H + oy), 2)

        for obj in game.objects:
            if obj.is_ball:
                self._draw_trail(screen, obj, ox, oy)

        for obj in game.objects:
            rect = pygame.Rect(int(obj.x0 + ox), int(obj.y0 + oy), int(obj.width), int(obj.height))
            if obj.is_ball:
                pygame.draw.ellipse(screen, color(getattr(obj, "color",  "white")), rect)
                pygame.draw.ellipse(screen, theme.BLACK, rect, width=2)
            elif obj.is_paddle:
                col = color(getattr(obj, "color1", "white"))
                flash = getattr(obj, "flash", 0.0)
                if flash > 0:
                    obj.flash = max(0.0, flash - self.app.dt * 5)
                    col = tuple(int(lerp(c, 255, 0.7 * flash)) for c in col)
                pygame.draw.rect(screen, col, rect)
                pygame.draw.rect(screen, theme.BLACK, rect, width=2)
            elif obj.is_wall:
                pygame.draw.rect(screen, theme.BLACK, rect)
                pygame.draw.rect(screen, theme.BLACK, rect, width=2)

        if getattr(game, "message_text", ""):
            surf = self.title_font.render(
                game.message_text, True, getattr(game, "message_color", (255, 255, 255)))
            screen.blit(surf, surf.get_rect(center=(W // 2, H // 2)))

        if game.countdown is not None:
            v    = game.countdown.shown_value
            surf = self.countdown_font.render(
                "GO!" if v == 0 else str(v), True,
                (60, 220, 120) if v == 0 else (255, 60, 60))
            screen.blit(surf, surf.get_rect(center=(W // 2, H // 2)))

            if game.p1.score + game.p2.score == 0:   # first serve: remind players of the controls
                self._draw_controls_hint(screen, game)

    def _draw_controls_hint(self, screen, game):
        ui = self.ui
        font = ui.fnt(0.032)
        for paddle, cx in ((game.p1, BASE_W * 0.25), (game.p2, BASE_W * 0.75)):
            text = "AI" if paddle.ai_enabled else paddle.controls_label
            label = ui.text(font, text, theme.WHITE)
            pad = int(BASE_H * 0.015)
            w, h = label.get_width() + 2 * pad, label.get_height() + 2 * pad
            x, y = int(cx - w / 2), int(BASE_H * 0.7)
            screen.blit(ui.panel_surf(w, h), (x, y))
            screen.blit(label, (x + pad, y + pad))

    # ── Overlay ────────────────────────────────────────────────────────────────

    def draw_overlay(self, state, screen, *, title=None, header=None, buttons=None,
                     title_size=0.08, header_size=0.05, btn_size=0.045,
                     title_color=theme.WHITE, dim=True):
        """Auto-sized panel: title, optional header (str or list of (text, colour)
        parts) and a grid of (key, text, colour, hover) buttons."""
        ui = self.ui

        def build(s):
            items = []
            if title is not None:
                items.append(Text(title, ui.fnt(title_size, s), title_color))
            if header is not None:
                items.append(Text(header, ui.fnt(header_size, s)))
            if buttons is not None:
                bf = ui.fnt(btn_size, s)
                cols = getattr(state, "ui_cols", len(buttons))
                nodes = [Button(key, text, bf, (c1, c2)) for key, text, c1, c2 in buttons]
                rows = [nodes[i:i + cols] for i in range(0, len(nodes), cols)]
                items.append(Grid(rows, gap_x=int(BASE_W * 0.015 * s), gap_y=int(ui.gap * s), uniform=True))
            return Stack(items, gap=int(ui.gap * 1.6 * s))

        ui.overlay(state, screen, build, dim=dim)
