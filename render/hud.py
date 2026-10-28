import math
import pygame

from config import BASE_W, BASE_H
from render import theme
from render.theme import color


class Hud:
    def __init__(self, app):
        self.app = app

        # Font cache bust key — if BASE_H ever changes, fonts are rebuilt
        self._cached_base_h = None

        # Cached rendered surfaces — only re-rendered when the value changes
        self._p1_score = None
        self._p2_score = None
        self._p1_color = None
        self._p2_color = None
        self._p1_surf = None
        self._p2_surf = None

        self._rally = None
        self._rally_surf = None

        self._spd = None
        self._spd_surf = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_fonts(self):
        """Fetch (or create once) all HUD fonts via FontManager."""
        f = self.app.font_manager
        self.font_big   = f.get("helvetica", int(BASE_H * 0.12), bold=True)
        self.font_mid   = f.get("helvetica", int(BASE_H * 0.05), bold=True)
        self.font_small = f.get("helvetica", int(BASE_H * 0.02))
        self.font_btn   = f.get("helvetica", int(BASE_H * 0.04), bold=True)
        self._cached_base_h = BASE_H

        # Invalidate all cached surfaces so they are re-rendered at the new size
        self._p1_score = self._p2_score = None
        self._rally    = None
        self._spd      = None

    def _ensure_fonts(self):
        """Rebuild fonts only when BASE_H has changed (e.g. first call, or resolution switch)."""
        if self._cached_base_h != BASE_H:
            self._rebuild_fonts()

    # ------------------------------------------------------------------
    # Public draw entry point
    # ------------------------------------------------------------------

    def draw(self, state, screen, game):
        p1   = getattr(game, "p1",   None)
        p2   = getattr(game, "p2",   None)
        ball = getattr(game, "ball", None)

        # Fonts are fetched from FontManager (cached there by key).
        # _ensure_fonts() only calls _rebuild_fonts() when BASE_H changes.
        self._ensure_fonts()

        if not p1 or not p2:
            return

        # --- Scores (re-render only when value or colour changes) --------
        p1_col = color(p1.color1)
        p2_col = color(p2.color1)

        if p1.score != self._p1_score or p1_col != self._p1_color:
            self._p1_surf  = self.font_big.render(str(p1.score), True, p1_col)
            self._p1_score = p1.score
            self._p1_color = p1_col

        if p2.score != self._p2_score or p2_col != self._p2_color:
            self._p2_surf  = self.font_big.render(str(p2.score), True, p2_col)
            self._p2_score = p2.score
            self._p2_color = p2_col

        screen.blit(self._p1_surf, (5  * BASE_W // 16 - self._p1_surf.get_width() // 2, 20))
        screen.blit(self._p2_surf, (11 * BASE_W // 16 - self._p2_surf.get_width() // 2, 20))

        # --- Rally (re-render only when value changes) -------------------
        rally = getattr(ball, "rally_value", 0) if ball else 0

        if rally != self._rally:
            self._rally_surf = self.font_mid.render(f"Rally: {rally}", True, theme.WHITE)
            self._rally = rally

        screen.blit(self._rally_surf, (BASE_W // 2 - self._rally_surf.get_width() // 2, 40))

        # --- Ball speed (re-render only when value changes) --------------
        spd = int(math.hypot(ball.vx, ball.vy)) if ball else 0

        if spd != self._spd:
            self._spd_surf = self.font_small.render(f"Ball Speed: {spd} pps", True, theme.WHITE)
            self._spd = spd

        screen.blit(self._spd_surf, (BASE_W // 2 - self._spd_surf.get_width() // 2, 100))

        # --- AI buttons and pause button ---------------------------------
        self.draw_ai_button(state, screen, p1, left=True)
        self.draw_ai_button(state, screen, p2, left=False)
        self.draw_pause_button(state, screen)

    # ------------------------------------------------------------------
    # Button drawing (unchanged logic, mouse_pos fetched once)
    # ------------------------------------------------------------------

    def draw_pause_button(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        w  = 20
        h  = 80
        x1 = (BASE_W - 3 * w) // 2
        x2 = (BASE_W + w) // 2
        y  = BASE_H - h - 20
        tw = x2 + w - x1

        rect  = pygame.Rect(x1, y, tw, h)
        rect1 = pygame.Rect(x1, y, w,  h)
        rect2 = pygame.Rect(x2, y, w,  h)

        bg = theme.WHITE_HOVER if rect.collidepoint(mouse_pos) else theme.WHITE

        pygame.draw.rect(screen, bg, rect1, border_radius=4)
        pygame.draw.rect(screen, bg, rect2, border_radius=4)

        state.ui_hitboxes["pause"] = rect

    def draw_ai_button(self, state, screen, paddle, left: bool):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        label = "AI Enabled" if paddle.ai_enabled else "AI Disabled"
        fg    = theme.BLACK if paddle.ai_enabled else theme.GRAY
        surf  = self.font_btn.render(label, True, fg)

        pad = 10
        w   = surf.get_width()  + pad * 2
        h   = surf.get_height() + pad * 2
        x   = 60 if left else (BASE_W - 60 - w)
        y   = 40
        rect = pygame.Rect(x, y, w, h)

        if left:
            bg = (theme.RED_HOVER       if rect.collidepoint(mouse_pos) else theme.RED)       if paddle.ai_enabled \
            else (theme.ORANGE_RED_HOVER if rect.collidepoint(mouse_pos) else theme.ORANGE_RED)
        else:
            bg = (theme.BLUE_HOVER      if rect.collidepoint(mouse_pos) else theme.BLUE)      if paddle.ai_enabled \
            else (theme.ROYAL_BLUE_HOVER if rect.collidepoint(mouse_pos) else theme.ROYAL_BLUE)

        pygame.draw.rect(screen, bg, rect, border_radius=8)
        screen.blit(surf, (x + pad, y + pad))

        if left:
            state.ui_hitboxes["p1_ai"] = rect
        else:
            state.ui_hitboxes["p2_ai"] = rect
