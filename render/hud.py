import math
import pygame

from config import BASE_W, BASE_H
from render import theme


class Hud:
    def __init__(self, app):
        self.app = app
        self.art = app.art

        # Each score plate swells briefly when its score changes
        self._scores = {}
        self._pops = {}

    # ------------------------------------------------------------------
    # Public draw entry point
    # ------------------------------------------------------------------

    def draw(self, state, screen, game):
        p1   = getattr(game, "p1",   None)
        p2   = getattr(game, "p2",   None)
        ball = getattr(game, "ball", None)

        if not p1 or not p2:
            return

        self.draw_score(screen, "p1", p1.score, 5 * BASE_W // 16, "crimson")
        self.draw_score(screen, "p2", p2.score, 11 * BASE_W // 16, "azure")

        # --- Rally and ball speed ----------------------------------------
        renderer = self.app.renderer
        rally = getattr(ball, "rally_value", 0) if ball else 0
        plate = pygame.Rect(BASE_W // 2 - 110, 28, 220, 58)
        screen.blit(self.art.inset(plate.w, plate.h), plate)
        renderer.text(screen, f"Rally: {rally}", renderer.fnt(0.036), theme.GOLD_BRIGHT, center=plate.center)

        spd = int(math.hypot(ball.vx, ball.vy)) if ball else 0
        renderer.text(screen, f"Ball Speed: {spd} pps", renderer.fnt(0.02, bold=False), theme.PARCHMENT,
                      center=(BASE_W // 2, plate.bottom + 22))

        # --- AI buttons and pause button ---------------------------------
        self.draw_ai_button(state, screen, p1, left=True)
        self.draw_ai_button(state, screen, p2, left=False)
        self.draw_pause_button(state, screen)

    # ------------------------------------------------------------------
    # Pieces
    # ------------------------------------------------------------------

    def draw_score(self, screen, key, score, cx, finish):
        if self._scores.get(key, score) != score:
            self._pops[key] = 1.0
        self._scores[key] = score

        pop = self._pops.get(key, 0.0)
        if pop > 0:
            self._pops[key] = max(0.0, pop - 3.5 * self.app.dt)

        w, h = 150, 116
        m = self.art.BUTTON_MARGIN
        screen.blit(self.art.button(w, h, finish), (cx - w // 2 - m, 18 - m))

        digits = self.art.gilded(str(score), self.art.ui(82), thickness=3, glow=None)
        if pop > 0:
            k = 1 + .45 * pop
            digits = pygame.transform.smoothscale(digits, (int(digits.get_width() * k), int(digits.get_height() * k)))
        screen.blit(digits, digits.get_rect(center=(cx, 18 + h // 2 - 4)))

    def draw_pause_button(self, state, screen):
        renderer = self.app.renderer
        mouse_pos = renderer.mouse()

        rect = pygame.Rect(BASE_W // 2 - 42, BASE_H - 96, 84, 76)
        offset = renderer.draw_face(screen, mouse_pos, rect, "ink")

        bar = theme.GOLD_BRIGHT if rect.collidepoint(mouse_pos) else theme.GOLD
        for x in (rect.centerx - 15, rect.centerx + 5):
            pygame.draw.rect(screen, bar, (x, rect.y + 18 + offset, 10, 34), border_radius=3)

        state.ui_hitboxes["pause"] = rect

    def draw_ai_button(self, state, screen, paddle, left: bool):
        renderer = self.app.renderer
        mouse_pos = renderer.mouse()
        font = renderer.fnt(0.032)

        label = "AI Enabled" if paddle.ai_enabled else "AI Disabled"
        w, h = 236, 66
        x = 60 if left else BASE_W - 60 - w
        rect = pygame.Rect(x, 32, w, h)

        if paddle.ai_enabled:
            finish = "crimson" if left else "azure"
        else:
            finish = "ink"

        renderer.draw_lacquer(screen, mouse_pos, rect, label, font, finish)

        if left:
            state.ui_hitboxes["p1_ai"] = rect
        else:
            state.ui_hitboxes["p2_ai"] = rect
