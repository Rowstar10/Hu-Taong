import math
import pygame

from config import BASE_W, BASE_H
from render import theme
from render.theme import color

class Hud:
    def __init__(self, app):
        self.app = app

    def draw(self, state, screen, game):
        p1 = getattr(game, "p1", None)
        p2 = getattr(game, "p2", None)
        ball = getattr(game, "ball", None)

        self.font_big = pygame.font.SysFont("Helvetica", int(BASE_H * 0.12), bold=True)
        self.font_mid = pygame.font.SysFont("Helvetica", int(BASE_H * 0.05), bold=True)
        self.font_small = pygame.font.SysFont("Helvetica", int(BASE_H * 0.02))
        self.font_btn = pygame.font.SysFont("Helvetica", int(BASE_H * 0.04), bold=True)

        if not p1 or not p2:
            return

        p1_text = self.font_big.render(f"{p1.score}", True, color(p1.color1))
        p2_text = self.font_big.render(f"{p2.score}", True, color(p2.color1))
        screen.blit(p1_text, (5 * BASE_W // 16 - p1_text.get_width() // 2, 20))
        screen.blit(p2_text, (11 * BASE_W // 16 - p2_text.get_width() // 2, 20))

        # Rally + speed
        rally = getattr(ball, "rally_value", 0) if ball else 0
        rally_surf = self.font_mid.render(f"Rally: {rally}", True, theme.WHITE)
        screen.blit(rally_surf, (BASE_W // 2 - rally_surf.get_width() // 2, 40))

        if ball:
            spd = int(math.hypot(ball.vx, ball.vy))
        else:
            spd = 0
            
        spd_surf = self.font_small.render(f"Ball Speed: {spd} pps", True, theme.WHITE)
        screen.blit(spd_surf, (BASE_W // 2 - spd_surf.get_width() // 2, 100))

        # AI toggle "buttons" (clickable rects)
        self.draw_ai_button(state, screen, p1, left=True)
        self.draw_ai_button(state, screen, p2, left=False)
        
        self.draw_pause_button(state, screen)

    def draw_pause_button(self, state, screen):
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        w = 20
        h = 80
        x1 = (BASE_W - 3 * w) // 2
        x2 = (BASE_W + w) // 2
        y = BASE_H - h - 20

        tw = x2 + w - x1

        rect = pygame.Rect(x1, y, tw, h)
        rect1 = pygame.Rect(x1, y, w, h)
        rect2 = pygame.Rect(x2, y, w, h)
        
        bg = theme.WHITE_HOVER if rect.collidepoint(mouse_pos) else theme.WHITE
        
        pygame.draw.rect(screen, bg, rect1, border_radius=4)
        pygame.draw.rect(screen, bg, rect2, border_radius=4)
        
        state.ui_hitboxes["pause"] = rect
        
    def draw_ai_button(self, state, screen, paddle, left: bool):
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
            state.ui_hitboxes["p1_ai"] = rect
        else:
            state.ui_hitboxes["p2_ai"] = rect
