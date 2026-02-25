import math
import pygame

from config import BASE_W
from render import theme
from render.theme import color

class Hud:
    def __init__(self, app):
        self.app = app

    def draw(self, screen, game):
        screen_w, screen_h = screen.get_size()
        p1 = getattr(game, "p1", None)
        p2 = getattr(game, "p2", None)
        ball = getattr(game, "ball", None)

        self.font_big = pygame.font.SysFont("Helvetica", int(screen_h * 0.12), bold=True)
        self.font_mid = pygame.font.SysFont("Helvetica", int(screen_h * 0.05), bold=True)
        self.font_small = pygame.font.SysFont("Helvetica", int(screen_h * 0.02))
        self.font_btn = pygame.font.SysFont("Helvetica", int(screen_h * 0.04), bold=True)

        if not p1 or not p2:
            return

        p1_text = self.font_big.render(f"{p1.score}", True, color(p1.color1))
        p2_text = self.font_big.render(f"{p2.score}", True, color(p2.color1))
        screen.blit(p1_text, (5 * screen_w // 16 - p1_text.get_width() // 2, 20))
        screen.blit(p2_text, (11 * screen_w // 16 - p2_text.get_width() // 2, 20))

        # Rally + speed
        rally = getattr(ball, "rally_value", 0) if ball else 0
        rally_surf = self.font_mid.render(f"Rally: {rally}", True, theme.WHITE)
        screen.blit(rally_surf, (BASE_W // 2 - rally_surf.get_width() // 2, 40))

        if ball:
            spd = int(math.hypot(ball.vx, ball.vy))
        else:
            spd = 0
        spd_surf = self.font_small.render(f"Ball Speed: {spd} pps", True, theme.WHITE)
        screen.blit(spd_surf, (BASE_W // 2 - spd_surf.get_width() // 2, 85))

        # AI toggle "buttons" (clickable rects)
        self.draw_ai_button(screen, p1, left=True)
        self.draw_ai_button(screen, p2, left=False)

    def draw_ai_button(self, screen, paddle, left: bool):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        label = "AI Enabled" if paddle.ai_enabled else "AI Disabled"
        fg = theme.BLACK if paddle.ai_enabled else theme.GRAY
        surf = self.font_btn.render(label, True, fg)

        pad = 10
        w = surf.get_width() + pad * 2
        h = surf.get_height() + pad * 2
        x = 60 if left else (BASE_W - 60 - w)
        y = 40
        rect = pygame.Rect(x, y, w, h)

        if left:
            if paddle.ai_enabled:
                 bg = theme.RED_HOVER if rect.collidepoint(mouse_pos) else theme.RED
            else:
                bg = theme.ORANGE_RED_HOVER if rect.collidepoint(mouse_pos) else theme.ORANGE_RED
        else:
            if paddle.ai_enabled:
                 bg = theme.BLUE_HOVER if rect.collidepoint(mouse_pos) else theme.BLUE
            else:
                bg = theme.ROYAL_BLUE_HOVER if rect.collidepoint(mouse_pos) else theme.ROYAL_BLUE
                
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        screen.blit(surf, (x + pad, y + pad))

        # store for click hit-testing
        if left:
            self.app.ui_hitboxes["p1_ai"] = rect
        else:
            self.app.ui_hitboxes["p2_ai"] = rect
