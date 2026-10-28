import pygame

from config import BASE_W, BASE_H
from render import theme
from render.theme import color

class Renderer:
    def __init__(self, app):
        self.app = app

        self.title_font     = app.font_manager.get("helvetica", 100, bold=True)
        self.countdown_font = app.font_manager.get("helvetica", 80,  bold=True)

        self._arrow_cache: dict = {}
        self._overlay_dim_surf: pygame.Surface | None = None
        self._panel_cache: dict = {}

        # Gap constants — BASE_W/H never change so compute once
        self._gx = int(BASE_W * 0.02)
        self._gy = int(BASE_H * 0.02)

    # ── Low-level helpers ──────────────────────────────────────────────────────

    def fnt(self, frac, bold=True):
        """Shorthand: proportional helvetica font by BASE_H fraction."""
        return self.app.font_manager.get("helvetica", int(BASE_H * frac), bold=bold)

    def get_arrow_surfs(self, font):
        key = id(font)
        if key not in self._arrow_cache:
            self._arrow_cache[key] = (
                font.render("<", True, theme.BLACK),
                font.render(">", True, theme.BLACK),
            )
        return self._arrow_cache[key]

    def get_overlay_dim_surf(self, W, H):
        if self._overlay_dim_surf is None or self._overlay_dim_surf.get_size() != (W, H):
            self._overlay_dim_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            self._overlay_dim_surf.fill((0, 0, 0, 170))
        return self._overlay_dim_surf

    def get_panel_surf(self, w, h):
        key = (w, h)
        if key not in self._panel_cache:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (30, 30, 30, 230), surf.get_rect(), border_radius=18)
            pygame.draw.rect(surf, (90, 90, 90, 255), surf.get_rect(), width=2, border_radius=18)
            self._panel_cache[key] = surf
        return self._panel_cache[key]

    # ── Mid-level draw helpers ─────────────────────────────────────────────────

    def draw_button(self, screen, mouse_pos, font, text, cx, cy,
                    col, hover, *, fg=None):
        """Draw a centred rounded button; return its Rect."""
        if fg is None:
            fg = theme.BLACK
        surf = font.render(text, True, fg)
        w = surf.get_width()  + self._gx
        h = surf.get_height() + self._gy
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(screen, hover if rect.collidepoint(mouse_pos) else col,
                         rect, border_radius=12)
        screen.blit(surf, surf.get_rect(center=rect.center))
        return rect

    def draw_toggle(self, screen, mouse_pos, font, text, cx, cy,
                    on, on_col, on_hov, off_col, off_hov):
        """draw_button with colour chosen by boolean `on`."""
        col, hov = (on_col, on_hov) if on else (off_col, off_hov)
        return self.draw_button(screen, mouse_pos, font, text, cx, cy, col, hov)

    def draw_title(self, screen, text, col, y_frac=0.1):
        """Draw a proportional title and return the bottom y coordinate."""
        surf = self.fnt(0.18).render(text, True, col)
        rect = surf.get_rect(center=(BASE_W // 2, int(BASE_H * y_frac)))
        screen.blit(surf, rect)
        return rect.bottom

    def draw_slider(self, screen, mouse_pos, cx, cy, slider_w, slider_h,
                    value, fill_color, *, label=None, label_font=None):
        """Draw a horizontal slider; return its Rect.
        If `label` is given, render it to the right of the track.
        """
        slider_x = cx - slider_w // 2
        rect = pygame.Rect(slider_x, cy, slider_w, slider_h)

        pygame.draw.rect(screen, theme.DARK_GRAY, rect, border_radius=6)
        fill_w = int(slider_w * max(0.0, min(1.0, value)))
        if fill_w > 0:
            pygame.draw.rect(screen, fill_color,
                             pygame.Rect(slider_x, cy, fill_w, slider_h),
                             border_radius=6)

        kr = slider_h * 1.2
        kx, ky = slider_x + fill_w, cy + slider_h // 2
        dx, dy = mouse_pos[0] - kx, mouse_pos[1] - ky
        pygame.draw.circle(screen,
                           theme.WHITE_HOVER if dx*dx + dy*dy <= kr*kr else theme.WHITE,
                           (int(kx), int(ky)), int(kr))

        if label is not None:
            lf = label_font or self.fnt(0.04)
            lsurf = lf.render(label, True, theme.WHITE)
            screen.blit(lsurf, lsurf.get_rect(midleft=(rect.right + self._gx, ky)))

        return rect

    def draw_labeled_cycle(self, screen, mouse_pos, font, text, col, cx, cy):
        """Render value text centred at (cx, cy), draw < > arrows, return (left_rect, right_rect)."""
        surf = font.render(text, True, col)
        rect = surf.get_rect(center=(cx, cy))
        screen.blit(surf, rect)
        return self.draw_cycle_row(screen, mouse_pos, font, cx, cy, surf, rect)

    def draw_cycle_row(self, screen, mouse_pos, font, cx, cy, label_surf, label_rect):
        """Draw < > arrows around an already-blitted label; return (left_rect, right_rect)."""
        arrow_l, arrow_r = self.get_arrow_surfs(font)
        aw, ah = font.size("<")
        bw, bh = aw + self._gx, ah + self._gy

        lr = pygame.Rect(label_rect.left  - bw - self._gx, cy - bh // 2, bw, bh)
        rr = pygame.Rect(label_rect.right + self._gx,      cy - bh // 2, bw, bh)

        lc = theme.GRAY_HOVER if lr.collidepoint(mouse_pos) else theme.GRAY
        rc = theme.GRAY_HOVER if rr.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, lc, lr, border_radius=12)
        pygame.draw.rect(screen, rc, rr, border_radius=12)
        screen.blit(arrow_l, arrow_l.get_rect(center=lr.center))
        screen.blit(arrow_r, arrow_r.get_rect(center=rr.center))
        return lr, rr

    def draw_back_button(self, screen, mouse_pos, font):
        """Back button pinned to the bottom centre; return its Rect."""
        return self.draw_button(
            screen, mouse_pos, font, "Back",
            BASE_W // 2, BASE_H - self.fnt(0.04).get_height() - self._gy * 2,
            theme.RED, theme.RED_HOVER)

    # ── Main menu ──────────────────────────────────────────────────────────────

    def draw_main_menu(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        sf = self.fnt(0.06)

        self.draw_title(screen, "Hu Taong!", theme.RED, y_frac=0.125)

        play_rect     = self.draw_button(screen, mouse_pos, sf, "Play Game",
                                         BASE_W // 2, int(BASE_H * 0.48),
                                         theme.GREEN,  theme.GREEN_HOVER)
        settings_rect = self.draw_button(screen, mouse_pos, sf, "Settings",
                                         BASE_W // 2, play_rect.bottom + 2 * self._gy,
                                         theme.ORANGE, theme.ORANGE_HOVER)
        quit_rect     = self.draw_button(screen, mouse_pos, sf, "Quit Game",
                                         BASE_W // 2, settings_rect.bottom + 2 * self._gy,
                                         theme.RED,    theme.RED_HOVER)

        state.ui_hitboxes["play"]        = play_rect
        state.ui_hitboxes["settings"]    = settings_rect
        state.ui_hitboxes["prompt_quit"] = quit_rect

    # ── Settings menu ──────────────────────────────────────────────────────────

    def draw_settings_menu(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        sf = self.fnt(0.06)

        self.draw_title(screen, "Settings", theme.ORANGE)

        btn_y = int(BASE_H * 0.55)
        # Centre button drives positioning of the two flanking ones
        gw = sf.size("Gameplay")[0] + self._gx          # gameplay button width
        cx = (BASE_W - gw) // 2 + gw // 2               # its centre x

        gameplay_rect = self.draw_button(screen, mouse_pos, sf, "Gameplay",
                                         cx, btn_y, theme.GREEN, theme.GREEN_HOVER)
        display_rect  = self.draw_button(screen, mouse_pos, sf, "Display",
                                         gameplay_rect.left - self._gx - sf.size("Display")[0] // 2 - self._gx // 2,
                                         btn_y, theme.ORANGE, theme.ORANGE_HOVER)
        audio_rect    = self.draw_button(screen, mouse_pos, sf, "Audio",
                                         gameplay_rect.right + self._gx + sf.size("Audio")[0] // 2 + self._gx // 2,
                                         btn_y, theme.BLUE, theme.BLUE_HOVER)

        back_rect = self.draw_back_button(screen, mouse_pos, self.fnt(0.04))

        state.ui_hitboxes.update(gameplay=gameplay_rect, display=display_rect,
                                 audio=audio_rect, back=back_rect)

    # ── Gameplay settings ──────────────────────────────────────────────────────

    def draw_gameplay_settings_menu(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        s  = self.app.settings.gameplay
        sf = self.fnt(0.06)
        f  = self.fnt(0.04)
        sm = self.fnt(0.03)
        ty = self.fnt(0.02)

        title_bottom = self.draw_title(screen, "Gameplay", theme.GREEN)
        current_y = title_bottom + 6 * self._gy

        lx, rx = BASE_W // 2 - 180, BASE_W // 2 + 180

        # Column headers
        for text, cx, anchor in [("AI Difficulty", lx, "midright"), ("Winning Score", rx, "midleft")]:
            surf = sf.render(text, True, theme.GREEN)
            rect = surf.get_rect(**{anchor: (cx, current_y)})
            screen.blit(surf, rect)
        ai_cx  = sf.render("AI Difficulty", True, theme.GREEN).get_rect(midright=(lx, current_y)).centerx
        win_cx = sf.render("Winning Score", True, theme.GREEN).get_rect(midleft=(rx, current_y)).centerx
        current_y += sf.get_height() + 2 * self._gy

        # AI difficulty cycle
        ai_diff  = s.ai_difficulties[s.ai_difficulty]
        ai_color = theme.GREEN if s.ai_difficulty == 0 else theme.WHITE if s.ai_difficulty < 4 else theme.RED
        left_ai_rect, right_ai_rect = self.draw_labeled_cycle(
            screen, mouse_pos, f, ai_diff, ai_color, ai_cx, current_y)

        # Win score cycle
        raw = s.winning_scores[s.winning_score_index]
        win_text  = "Endless Mode" if raw == "Endless Mode" else f"Score {raw} to win"
        win_color = theme.ORANGE if raw == "Endless Mode" else theme.WHITE
        left_win_rect, right_win_rect = self.draw_labeled_cycle(
            screen, mouse_pos, f, win_text, win_color, win_cx, current_y)

        current_y = right_win_rect.bottom + self._gy

        # Win by two toggle
        wbt_rect = self.draw_toggle(
            screen, mouse_pos, sm,
            "Win by Two: ON" if s.win_by_two else "Win by Two: OFF",
            win_cx, current_y, s.win_by_two,
            theme.GREEN, theme.GREEN_HOVER, theme.RED, theme.RED_HOVER)
        current_y = wbt_rect.bottom + 6 * self._gy

        # Paired slider rows
        slider_w = int(BASE_W * 0.25)
        slider_h = int(BASE_H * 0.02)

        for (header, cx, key, val, lo, hi) in [
            ("Ball Speed",   ai_cx,  "ball_speed_slider",
             s.ball_speed,   s.ball_speed_min,   s.ball_speed_range),
            ("Paddle Speed", win_cx, "paddle_speed_slider",
             s.paddle_speed, s.paddle_speed_min, s.paddle_speed_range),
        ]:
            screen.blit(sf.render(header, True, theme.GREEN),
                        sf.render(header, True, theme.GREEN).get_rect(center=(cx, current_y)))
        current_y += sf.get_height() + 2 * self._gy

        bs_rect = self.draw_slider(screen, mouse_pos, ai_cx,  current_y, slider_w, slider_h,
                                   (s.ball_speed   - s.ball_speed_min)  / s.ball_speed_range,
                                   theme.GREEN, label=str(int(s.ball_speed)), label_font=f)
        ps_rect = self.draw_slider(screen, mouse_pos, win_cx, current_y, slider_w, slider_h,
                                   (s.paddle_speed - s.paddle_speed_min) / s.paddle_speed_range,
                                   theme.GREEN, label=str(int(s.paddle_speed)), label_font=f)
        current_y = ps_rect.bottom + 4 * self._gy

        for (header, cx) in [("Ball Diameter", ai_cx), ("Paddle Size", win_cx)]:
            screen.blit(sf.render(header, True, theme.GREEN),
                        sf.render(header, True, theme.GREEN).get_rect(center=(cx, current_y)))
        current_y += sf.get_height() + 2 * self._gy

        bd_rect = self.draw_slider(screen, mouse_pos, ai_cx,  current_y, slider_w, slider_h,
                                   (s.ball_diameter  - s.ball_diameter_min)  / s.ball_diameter_range,
                                   theme.GREEN, label=str(int(s.ball_diameter)), label_font=f)
        pz_rect = self.draw_slider(screen, mouse_pos, win_cx, current_y, slider_w, slider_h,
                                   (s.paddle_height  - s.paddle_height_min)  / s.paddle_height_range,
                                   theme.GREEN,
                                   label=f"{int(s.paddle_height)} x {int(s.paddle_width)}",
                                   label_font=f)
        current_y = pz_rect.bottom + 2 * self._gy

        # Reset buttons — one shared surface blitted 4×
        reset_surf = ty.render("Reset", True, theme.BLACK)
        rw = reset_surf.get_width()  + self._gx
        rh = reset_surf.get_height() + self._gy
        reset_rects = {
            "reset_ball_speed":    pygame.Rect(bs_rect.left - rw - self._gx // 2, bs_rect.centery - rh // 2, rw, rh),
            "reset_paddle_speed":  pygame.Rect(ps_rect.left - rw - self._gx // 2, bs_rect.centery - rh // 2, rw, rh),
            "reset_ball_diameter": pygame.Rect(bd_rect.left - rw - self._gx // 2, bd_rect.centery - rh // 2, rw, rh),
            "reset_paddle_size":   pygame.Rect(pz_rect.left - rw - self._gx // 2, bd_rect.centery - rh // 2, rw, rh),
        }
        for rect in reset_rects.values():
            pygame.draw.rect(screen,
                             theme.WHITE_HOVER if rect.collidepoint(mouse_pos) else theme.WHITE,
                             rect, border_radius=12)
            screen.blit(reset_surf, reset_surf.get_rect(center=rect.center))

        rand_rect = self.draw_button(screen, mouse_pos, sm, "Randomise All",
                                     ai_cx,  current_y, theme.GREEN, theme.GREEN_HOVER)
        def_rect  = self.draw_button(screen, mouse_pos, sm, "Reset All",
                                     win_cx, current_y, theme.GREEN, theme.GREEN_HOVER)
        back_rect = self.draw_back_button(screen, mouse_pos, f)

        state.ui_hitboxes.update(
            cycle_ai_left=left_ai_rect, cycle_ai_right=right_ai_rect,
            cycle_win_score_left=left_win_rect, cycle_win_score_right=right_win_rect,
            toggle_win_by_two=wbt_rect,
            ball_speed_slider=bs_rect, paddle_speed_slider=ps_rect,
            ball_diameter_slider=bd_rect, paddle_size_slider=pz_rect,
            randomise_all=rand_rect, reset_all=def_rect, back=back_rect,
            **reset_rects)

    # ── Display settings ───────────────────────────────────────────────────────

    def draw_display_settings_menu(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        s  = self.app.settings.display
        sf = self.fnt(0.06)
        f  = self.fnt(0.04)
        sm = self.fnt(0.03)
        ty = self.fnt(0.02)

        title_bottom = self.draw_title(screen, "Display", theme.ORANGE)
        current_y = title_bottom + 3 * self._gy

        # Resolution
        res_hdr = sf.render("Resolution", True, theme.ORANGE)
        res_hdr_rect = res_hdr.get_rect(center=(BASE_W // 2, current_y))
        screen.blit(res_hdr, res_hdr_rect)
        current_y = res_hdr_rect.bottom + 3 * self._gy

        res = self.app.resolutions[state.res_index]
        left_rect, right_rect = self.draw_labeled_cycle(
            screen, mouse_pos, f, f"{res[0]} x {res[1]}", theme.WHITE,
            BASE_W // 2, current_y)
        current_y = right_rect.bottom + 3 * self._gy

        # Display mode
        mode_text = self.app.display_modes[state.display_mode_index].capitalize()
        mode_left_rect, mode_right_rect = self.draw_labeled_cycle(
            screen, mouse_pos, f, mode_text, theme.WHITE, BASE_W // 2, current_y)
        current_y = mode_right_rect.bottom + self._gy

        # Apply + Background header
        apply_rect = self.draw_button(screen, mouse_pos, sm, "Apply",
                                      BASE_W // 2, current_y, theme.ORANGE, theme.ORANGE_HOVER)
        current_y = apply_rect.bottom + 4 * self._gy

        bg_hdr = sf.render("Background", True, theme.ORANGE)
        bg_rect = bg_hdr.get_rect(center=(BASE_W // 2, current_y))
        screen.blit(bg_hdr, bg_rect)

        rot_rect = self.draw_toggle(
            screen, mouse_pos, sm,
            "Rotate: ON" if s.rotate_backgrounds else "Rotate: OFF",
            BASE_W // 2, BASE_H - 180, s.rotate_backgrounds,
            theme.ORANGE, theme.ORANGE_HOVER, theme.RED, theme.RED_HOVER)

        # FPS column (right)
        fps_cx = BASE_W // 2 + sf.size("Maximum FPS")[0] // 2 + 400
        fps_cy = res_hdr_rect.centery + 100
        screen.blit(sf.render("Maximum FPS", True, theme.ORANGE),
                    sf.render("Maximum FPS", True, theme.ORANGE).get_rect(center=(fps_cx, fps_cy)))
        fps_y = fps_cy + sf.get_height() + 3 * self._gy

        max_fps_left_rect, max_fps_right_rect = self.draw_labeled_cycle(
            screen, mouse_pos, f,
            str(s.max_fps_options[s.max_fps]), theme.WHITE, fps_cx, fps_y)

        show_fps_rect = self.draw_toggle(
            screen, mouse_pos, ty,
            "Show FPS: ON" if s.show_fps else "Show FPS: OFF",
            fps_cx, max_fps_right_rect.bottom + self._gy, s.show_fps,
            theme.ORANGE, theme.ORANGE_HOVER, theme.RED, theme.RED_HOVER)

        # Dim column (left)
        dim_cx = BASE_W // 2 - sf.size("Dim Overlay")[0] // 2 - 400
        screen.blit(sf.render("Dim Overlay", True, theme.ORANGE),
                    sf.render("Dim Overlay", True, theme.ORANGE).get_rect(center=(dim_cx, fps_cy)))
        dim_y = fps_cy + sf.get_height() + 3 * self._gy

        dim_rect = self.draw_slider(
            screen, mouse_pos, dim_cx, dim_y,
            int(BASE_W * 0.2), int(BASE_H * 0.02),
            s.dim, theme.ORANGE,
            label=f"{int(100 * s.dim)}%", label_font=f)

        back_rect = self.draw_back_button(screen, mouse_pos, f)

        state.ui_hitboxes.update(
            cycle_res_left=left_rect, cycle_res_right=right_rect,
            cycle_mode_left=mode_left_rect, cycle_mode_right=mode_right_rect,
            apply=apply_rect, toggle_rotate_bg=rot_rect,
            cycle_max_fps_left=max_fps_left_rect, cycle_max_fps_right=max_fps_right_rect,
            toggle_show_fps=show_fps_rect, dim_slider=dim_rect, back=back_rect)

    # ── Audio settings ─────────────────────────────────────────────────────────

    def draw_audio_settings_menu(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        sound = self.app.sound_manager
        audio   = self.app.settings.audio
        sf  = self.fnt(0.06)
        f   = self.fnt(0.04)
        sm  = self.fnt(0.03)

        title_bottom = self.draw_title(screen, "Audio", theme.BLUE)
        current_y = title_bottom + 4 * self._gy
        left_cx   = BASE_W // 2 - 400
        slider_w  = int(BASE_W * 0.3)
        slider_h  = int(BASE_H * 0.02)

        # Shared reset surface
        reset_surf = sm.render("Reset", True, theme.BLACK)
        rv_w = reset_surf.get_width()  + self._gx
        rv_h = reset_surf.get_height() + self._gy

        vol_slider_rects = {}
        reset_vol_rects  = {}

        for key, label, value in [
            ("master_volume_slider", "Master Volume", sound.master_volume),
            ("music_volume_slider",  "Music Volume",  sound.music_volume),
            ("sfx_volume_slider",    "SFX Volume",    sound.sfx_volume),
        ]:
            screen.blit(sf.render(label, True, theme.BLUE),
                        sf.render(label, True, theme.BLUE).get_rect(center=(left_cx, current_y)))
            current_y += sf.get_height() + 2 * self._gy

            sl = self.draw_slider(screen, mouse_pos, left_cx, current_y,
                                  slider_w, slider_h, value, theme.BLUE,
                                  label=f"{int(100 * value)}%", label_font=sf)
            vol_slider_rects[key] = sl

            rk = "reset_" + key.replace("_slider", "")
            rv_rect = pygame.Rect(sl.left - rv_w - self._gx // 2,
                                  sl.centery - rv_h // 2, rv_w, rv_h)
            reset_vol_rects[rk] = rv_rect
            pygame.draw.rect(screen,
                             theme.WHITE_HOVER if rv_rect.collidepoint(mouse_pos) else theme.WHITE,
                             rv_rect, border_radius=12)
            screen.blit(reset_surf, reset_surf.get_rect(center=rv_rect.center))
            current_y = sl.bottom + 3 * self._gy

        # Sound toggles
        paddle_cx = left_cx - sm.size("Paddle Sounds: ON")[0] // 2 - self._gx // 2
        for tog_key, text, flag, cx in [
            ("toggle_paddle_sounds",
             f"Paddle Sounds: {'ON' if sound.paddle_hit_sound else 'OFF'}",
             sound.paddle_hit_sound, paddle_cx),
            ("toggle_score_sounds",
             f"Score Sound: {'ON' if sound.score_sound else 'OFF'}",
             sound.score_sound, left_cx + self._gx // 2),
        ]:
            state.ui_hitboxes[tog_key] = self.draw_toggle(
                screen, mouse_pos, sm, text, cx, current_y, flag,
                theme.BLUE, theme.BLUE_HOVER, theme.RED, theme.RED_HOVER)

        current_y += sm.get_height() + 5 * self._gy

        # Music cycle rows
        music_cx  = BASE_W // 2 + 500
        music_y   = title_bottom + 4 * self._gy    # aligns with volume section top
        music_hitboxes = {}

        for base, label, track_list, idx in [
            ("menu_music", "Menu Music", audio.menu_track, audio.menu_music),
            ("game_music", "Game Music", audio.game_track, audio.game_music),
            ("win_music",  "Win Music",  audio.win_track,  audio.win_music),
            ("lose_music", "Lose Music", audio.lose_track, audio.lose_music),
        ]:
            screen.blit(sf.render(label, True, theme.BLUE),
                        sf.render(label, True, theme.BLUE).get_rect(center=(music_cx, music_y)))
            music_y += sf.get_height() + 2 * self._gy

            lr, rr = self.draw_labeled_cycle(
                screen, mouse_pos, f,
                track_list[idx].rstrip(".mp3"), theme.WHITE,
                music_cx, music_y)
            music_hitboxes[f"cycle_{base}_left"]  = lr
            music_hitboxes[f"cycle_{base}_right"] = rr
            music_y += f.get_height() + 3 * self._gy

        rand_rect = self.draw_button(screen, mouse_pos, sm, "Randomise Music",
                                     music_cx - 100, music_y, theme.BLUE, theme.BLUE_HOVER)
        loop_rect = self.draw_toggle(
            screen, mouse_pos, sm,
            "Loop" if audio.loop_music else "Shuffle",
            music_cx + 180, music_y, audio.loop_music,
            theme.BLUE, theme.BLUE_HOVER, theme.BLUE, theme.BLUE_HOVER)

        back_rect = self.draw_back_button(screen, mouse_pos, f)

        state.ui_hitboxes.update(vol_slider_rects)
        state.ui_hitboxes.update(reset_vol_rects)
        state.ui_hitboxes.update(music_hitboxes)
        state.ui_hitboxes.update(randomise_music=rand_rect,
                                 toggle_loop_music=loop_rect, back=back_rect)

    # ── Game world ─────────────────────────────────────────────────────────────

    def draw_world(self, screen, game):
        W, H = BASE_W, BASE_H
        pygame.draw.line(screen, (160, 160, 160), (W // 2, 0), (W // 2, H), 2)

        for obj in game.objects:
            rect = pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height))
            if obj.is_ball:
                pygame.draw.ellipse(screen, color(getattr(obj, "color",  "white")), rect)
                pygame.draw.ellipse(screen, theme.BLACK, rect, width=2)
            elif obj.is_paddle:
                pygame.draw.rect(screen, color(getattr(obj, "color1", "white")), rect)
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

    # ── Overlay ────────────────────────────────────────────────────────────────

    def draw_overlay(self, state, screen, *,
                     title=None, header=None, buttons=None,
                     title_size=0.3, header_size=0.3, btn_size=0.14,
                     title_y=0.2, header_y=0.4, btn_y=0.75,
                     title_color=theme.WHITE, panel_rect=None, dim=True):

        W, H = BASE_W, BASE_H
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        if panel_rect is None:
            pw, ph = int(W * 0.1), int(H * 0.2)
            panel_rect = pygame.Rect(W // 2 - pw // 2, H // 2 - ph // 2, pw, ph)
        x, y, w, h = panel_rect

        if dim:
            screen.blit(self.get_overlay_dim_surf(W, H), (0, 0))
        screen.blit(self.get_panel_surf(w, h), (x, y))

        from helpers import fit_text, draw_multicolor_text

        if title is not None:
            tf   = fit_text(title, int(w * 0.9), int(h * title_size), bold=True)
            surf = tf.render(title, True, title_color)
            screen.blit(surf, surf.get_rect(center=(x + w // 2, y + int(h * title_y))))

        if header is not None:
            hf = fit_text(header, int(w * 0.9), int(h * header_size), bold=True)
            if isinstance(header, list):
                draw_multicolor_text(screen, hf, header, (x + w // 2, y + int(h * header_y)))
            else:
                surf = hf.render(header, True, theme.WHITE)
                screen.blit(surf, surf.get_rect(center=(x + w // 2, y + int(h * header_y))))

        if buttons is not None:
            bf = self.app.font_manager.get("helvetica", int(h * btn_size), bold=True)
            cols = getattr(state, "ui_cols", len(buttons))
            self.app.ui_layout.draw_button_grid(
                state, screen, (x, y + int(h * 0.25), w, int(h * btn_y)),
                buttons, cols=cols, btn_font=bf)
