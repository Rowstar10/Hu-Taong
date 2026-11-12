import math
import pygame

from config import BASE_W, BASE_H
from game.powerups import BY_KEY as POWERUPS, FAMILY_COLOURS
from render import theme
from render.art import mix

# What each power-up is doing, in a few words, for the Tab overview
SHORT = {"teleport": "Saves one goal", "giant": "Taller paddle", "swift": "Faster paddle",
         "fire": "Every hit is a blazing shot", "frost": "Next hit frosts the ball", "shrink": "Shorter paddle",
         "ghost": "Ball vanishes and reappears at random",
         "sticky": "Ball sticks to this paddle", "gravity": "Paddle falls; Up jumps",
         "wall": "Middle Wall is down", "swap": "Paddles about to swap", "blink": "Ball blinks about",
         "tomb": "A tombstone stands on the court", "snowball": "Heavy snowball: shoves paddles back",
         "twin": "Two balls: each scores only in the other side's goal",
         "chaos": "Sizes and speeds drifting", "curve": "Hits bend the way the paddle moved",
         "double": "This point is worth 2", "wind": "Wind bending the ball",
         "cracker": "Bangs after its last hit", "lantern": "Night: lanterns only",
         "portal": "Two linked portals"}


def seconds_text(left):
    """A countdown in whole seconds, or "point" for something that lasts until the point ends."""
    if left is None:
        return ""
    return "point" if math.isinf(left) else f"{math.ceil(left)}s"


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

    def draw(self, state, screen, game, live=True):
        p1   = getattr(game, "p1",   None)
        p2   = getattr(game, "p2",   None)
        ball = getattr(game, "ball", None)

        if not p1 or not p2:
            return

        left, right = 5 * BASE_W // 16, 11 * BASE_W // 16
        if live:                                 # a replay shows its score in its own bar instead
            self.draw_score(screen, "p1", p1.score, left, "crimson")
            self.draw_score(screen, "p2", p2.score, right, "azure")

        # With Chaos Switch the paddles change hands, so say who is playing each side
        if game.settings.switch_each_point:
            self.draw_owner(screen, p1, left)
            self.draw_owner(screen, p2, right)

        powerups = getattr(game, "powerups", None)
        if powerups:
            top = 196 if game.settings.switch_each_point else 150
            self.draw_effects(screen, powerups.effect_list(p1), left, top)
            self.draw_effects(screen, powerups.effect_list(p2), right, top)
            court = [(key, seconds, 0) for key, seconds, _ in powerups.court_list()
                     if key in ("wall", "blink", "snowball", "ghost", "twin", "swap", "chaos", "curve",
                                "double", "wind", "cracker", "lantern", "portal")]
            if court:                            # things that are on everyone sit in the middle
                self.draw_effects(screen, court, BASE_W // 2, 150)

        # --- Rally and ball speed (left out on the Minimal HUD) ----------
        if self.app.settings.interface.hud == 0 and live:
            renderer = self.app.renderer
            rally = getattr(ball, "rally_value", 0) if ball else 0
            plate = pygame.Rect(BASE_W // 2 - 110, 28, 220, 58)
            screen.blit(self.art.inset(plate.w, plate.h), plate)
            renderer.text(screen, f"Rally: {rally}", renderer.fnt(0.036), theme.GOLD_BRIGHT, center=plate.center)

            spd = int(math.hypot(ball.vx, ball.vy) * game.settings.pace) if ball else 0   # as seen on screen
            renderer.text(screen, f"Ball speed {spd}", renderer.fnt(0.023), theme.PARCHMENT,
                          center=(BASE_W // 2, plate.bottom + 22))

        if powerups and self.tab_held():
            self.draw_overview(screen, game, powerups)

        if live:
            self.draw_pause_button(state, screen)

    # ------------------------------------------------------------------
    # Tab: every power-up in play, larger and named
    # ------------------------------------------------------------------

    def tab_held(self):
        """Tab is down, and isn't one of the paddle keys."""
        if pygame.K_TAB not in self.app.keys_down:
            return False
        interface = self.app.settings.interface
        return pygame.K_TAB not in [getattr(interface, f) for f in interface.KEY_FIELDS]

    def draw_overview(self, screen, game, powerups):
        renderer, art = self.app.renderer, self.art
        frozen = {p: powerups.frozen(p) for p in (game.p1, game.p2)}

        def who(paddle):
            return f"{paddle.color1}  ({'AI' if paddle.ai_enabled else paddle.controls_label})"

        def rows_for(paddle):
            rows = []
            for key, left, charges in powerups.effect_list(paddle):
                note = SHORT[key]
                if key == "frost" and frozen[paddle]:
                    note = "Frozen: moves at half speed"
                rows.append((key, self.label(key, left, charges), note))
            return rows

        columns = [(who(game.p1), (255, 112, 92), rows_for(game.p1)),
                   ("Ball & Court", theme.GOLD_BRIGHT,
                    [(key, Hud.label(key, left, 0) if key in ("cracker", "double") else seconds_text(left), note)
                     for key, left, note in powerups.court_list()]),
                   (who(game.p2), (112, 162, 255), rows_for(game.p2))]

        row_h, col_w = 78, 480
        most = max(1, max(len(rows) for _, _, rows in columns))
        h = 110 + most * row_h + 40
        h = (h + 39) // 40 * 40                  # in steps, so only a few panel sizes are ever built
        w = 3 * col_w + 60
        panel = pygame.Rect(0, 0, w, h)
        panel.center = (BASE_W // 2, BASE_H // 2 + 30)
        renderer.draw_board(screen, panel)

        head, name_font, note_font = renderer.fnt(0.03), renderer.fnt(0.024), renderer.fnt(0.019, bold=False)
        for i, (title, colour, rows) in enumerate(columns):
            x = panel.x + 30 + i * col_w
            renderer.text(screen, title, head, colour, center=(x + col_w // 2, panel.y + 58))
            if not rows:
                renderer.text(screen, "Nothing", note_font, theme.GRAY, center=(x + col_w // 2, panel.y + 120))
            for j, (key, timer, note) in enumerate(rows):
                kind = POWERUPS[key]
                y = panel.y + 100 + j * row_h
                icon = art.power_icon(64, key, kind.family)
                screen.blit(icon, (x + 14, y))
                tint = mix(FAMILY_COLOURS[kind.family], (255, 255, 255), .45)
                renderer.text(screen, kind.name, name_font, tint, midleft=(x + 92, y + 20))
                renderer.text(screen, note, note_font, theme.PARCHMENT, midleft=(x + 92, y + 48))
                if timer:
                    renderer.text(screen, timer, name_font, theme.GOLD_BRIGHT, midright=(x + col_w - 18, y + 20))
            if i:
                pygame.draw.line(screen, theme.GOLD_DARK, (x, panel.y + 40), (x, panel.bottom - 40), 2)

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

    @staticmethod
    def label(key, left, charges):
        if key == "cracker" and left is not None and not math.isinf(left):
            hits = int(left)
            return "bang!" if hits <= 0 else f"{hits} hit" + ("s" if hits != 1 else "")
        if key == "double":
            return "x2"
        if left is not None:
            return seconds_text(left)
        return "ready" if charges <= 1 else f"x{charges}"

    def draw_effects(self, screen, items, cx, top):
        """What's on this player right now: each power-up's icon, a ring that empties as it runs
        out, and its seconds left (or "ready" for a charge waiting to be used)."""
        if not items:
            return
        renderer = self.app.renderer
        font = renderer.fnt(0.019)
        step = 66
        x = cx - step * (len(items) - 1) // 2
        for key, left, charges in items:
            kind = POWERUPS[key]
            icon = self.art.power_icon(44, key, kind.family)
            screen.blit(icon, icon.get_rect(center=(x, top + 22)))
            if left is not None and kind.seconds:
                k = max(0.0, min(1.0, left / kind.seconds))
                arc = pygame.Rect(0, 0, 54, 54)
                arc.center = (x, top + 22)
                pygame.draw.arc(screen, FAMILY_COLOURS[kind.family], arc, math.pi / 2, math.pi / 2 + k * math.tau, 3)
            renderer.text(screen, self.label(key, left, charges), font, theme.PARCHMENT, center=(x, top + 56))
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

        # a fingertip is bigger than a mouse pointer, so on a phone it has a little room around it
        state.ui_hitboxes["pause"] = rect.inflate(40, 34) if self.app.touch else rect
        renderer.tips.offer(rect, "Pause\nPause the match.\n~ Esc")
