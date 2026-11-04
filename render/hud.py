import math
import pygame

from config import BASE_W, BASE_H
from game.powerups import BY_KEY as POWERUPS, FAMILY_COLOURS
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

        left, right = 5 * BASE_W // 16, 11 * BASE_W // 16
        self.draw_score(screen, "p1", p1.score, left, "crimson")
        self.draw_score(screen, "p2", p2.score, right, "azure")

        # With Chaos Switch the paddles change hands, so say who is playing each side
        if game.settings.switch_each_point:
            self.draw_owner(screen, p1, left)
            self.draw_owner(screen, p2, right)

        powerups = getattr(game, "powerups", None)
        if powerups:
            top = 196 if game.settings.switch_each_point else 150
            self.draw_effects(screen, powerups, p1, left, top)
            self.draw_effects(screen, powerups, p2, right, top)
            if powerups.wall_open():             # Open Court is on everyone, so it sits in the middle
                kind = POWERUPS["wall"]
                coin = self.art.charm(40, kind.glyph, FAMILY_COLOURS[kind.family])
                screen.blit(coin, coin.get_rect(center=(BASE_W // 2, 170)))
                self.app.renderer.text(screen, f"{math.ceil(powerups.wall_down)}", self.app.renderer.fnt(0.019),
                                       theme.PARCHMENT, center=(BASE_W // 2, 202))

        # --- Rally and ball speed (left out on the Minimal HUD) ----------
        if self.app.settings.interface.hud == 0:
            renderer = self.app.renderer
            rally = getattr(ball, "rally_value", 0) if ball else 0
            plate = pygame.Rect(BASE_W // 2 - 110, 28, 220, 58)
            screen.blit(self.art.inset(plate.w, plate.h), plate)
            renderer.text(screen, f"Rally: {rally}", renderer.fnt(0.036), theme.GOLD_BRIGHT, center=plate.center)

            spd = int(math.hypot(ball.vx, ball.vy) * game.settings.pace) if ball else 0   # as seen on screen
            renderer.text(screen, f"Ball Speed: {spd} pps", renderer.fnt(0.02, bold=False), theme.PARCHMENT,
                          center=(BASE_W // 2, plate.bottom + 22))

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

    def draw_effects(self, screen, powerups, paddle, cx, top):
        """What's on this player right now: a coin for each power-up, with its seconds or charges."""
        items = [(key, f"{math.ceil(left)}") for key, left in paddle.effects.items()]
        if powerups.frosted(paddle):
            items.append(("frost", "ready" if paddle is powerups.frost["owner"] else f"{math.ceil(powerups.frost['left'])}"))
        if powerups.ghost and powerups.ghost["owner"] is paddle:
            items.append(("ghost", f"{math.ceil(powerups.ghost['left'])}"))
        items += [(key, f"x{count}") for key, count in paddle.charges.items()]
        if not items:
            return
        renderer = self.app.renderer
        font = renderer.fnt(0.019)
        step = 64
        x = cx - step * (len(items) - 1) // 2
        for key, label in items:
            kind = POWERUPS[key]
            coin = self.art.charm(40, kind.glyph, FAMILY_COLOURS[kind.family])
            screen.blit(coin, coin.get_rect(center=(x, top + 20)))
            renderer.text(screen, label, font, theme.PARCHMENT, center=(x, top + 52))
            x += step

    def draw_owner(self, screen, paddle, cx):
        renderer = self.app.renderer
        font = renderer.fnt(0.022)
        text = "AI" if paddle.ai_enabled else paddle.controls_label
        w = max(110, font.size(text)[0] + 32)
        plate = pygame.Rect(cx - w // 2, 144, w, 38)
        screen.blit(self.art.inset(plate.w, plate.h), plate)
        renderer.text(screen, text, font, theme.GOLD_BRIGHT, center=plate.center)

    def draw_pause_button(self, state, screen):
        renderer = self.app.renderer
        mouse_pos = renderer.mouse()

        rect = pygame.Rect(BASE_W // 2 - 42, BASE_H - 96, 84, 76)
        offset = renderer.draw_face(screen, mouse_pos, rect, "ink")

        bar = theme.GOLD_BRIGHT if rect.collidepoint(mouse_pos) else theme.GOLD
        for x in (rect.centerx - 15, rect.centerx + 5):
            pygame.draw.rect(screen, bar, (x, rect.y + 18 + offset, 10, 34), border_radius=3)

        state.ui_hitboxes["pause"] = rect
        renderer.tips.offer(rect, "Pause the match. (Esc)")
