import pygame

from config import BASE_W, BASE_H
from render import theme
from render.theme import color

class PygameRenderer:
    def __init__(self, app):
        self.app = app
        self.title_font = pygame.font.SysFont("Helvetica", 100, bold = True)
        self.subtitle_font = pygame.font.SysFont("Helvetica", 40, bold = True)
        self.button_font = pygame.font.SysFont("Helvetica", 20, bold = True)
        self.countdown_font = pygame.font.SysFont("Helvetica", 80, bold = True)

    def draw_world(self, screen, game):
        screen.fill((0, 0, 0))

        # Separator
        pygame.draw.line(screen, (160, 160, 160), (BASE_W // 2, 0), (BASE_W // 2, BASE_H), 2)

        # Draw objects (rectangles/circles)
        for obj in game.objects:
            if obj.is_ball:
                pygame.draw.ellipse(screen, color(getattr(obj, "color", "white")),
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)))
                
            elif obj.is_paddle:
                pygame.draw.rect(screen, color(getattr(obj, "color1", "white")),
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)))

            elif obj.is_wall:
                pygame.draw.rect(screen, color(getattr(obj, "color", None)),
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)))
                
        # Score message
        if getattr(game, "message_text", ""):
            surf = self.title_font.render(game.message_text, True, getattr(game, "message_color", (255, 255, 255)))
            screen.blit(surf, (BASE_W // 2 - surf.get_width() // 2, BASE_H // 2 - surf.get_height() // 2))

        # Countdown overlay
        if game.countdown is not None:
            v = game.countdown.shown_value
            txt = "GO!" if v == 0 else str(v)
            col = (60, 220, 120) if v == 0 else (255, 60, 60)
            surf = self.countdown_font.render(txt, True, col)
            screen.blit(surf, (BASE_W // 2 - surf.get_width() // 2, BASE_H // 2 - surf.get_height() // 2))
            
    def draw_pause_panel(self, screen, *, title="Paused", buttons=None, panel_rect=None, dim=True):
        W, H = screen.get_size()
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        if buttons is None:
            buttons = [
                ("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                ("reset", "Reset", theme.ORANGE, theme.ORANGE_HOVER),
                ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER),
            ]

        # ---------- Dim background ----------
        if dim:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

        # ---------- Panel ----------
        if panel_rect is None:
            panel_w = int(W * 0.4)
            panel_h = int(H * 0.25)
            panel_rect = pygame.Rect(
                W // 2 - panel_w // 2,
                H // 2 - panel_h // 2,
                panel_w,
                panel_h
            )
            
        x, y, w, h = panel_rect

        # ---------- Transparent Panel ----------
        panel_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 0))  # fully transparent surface

        pygame.draw.rect(
            panel_surface,
            (30, 30, 30, 230),  # slightly transparent panel
            panel_surface.get_rect(),
            border_radius=18
        )

        pygame.draw.rect(
            panel_surface,
            (90, 90, 90, 255),  # fully opaque border
            panel_surface.get_rect(),
            width=2,
            border_radius=18
        )

        screen.blit(panel_surface, (x, y))

        # ---------- Title ----------
        title_font = pygame.font.SysFont("Helvetica", int(h * 0.3), bold = True)
        title_surf = title_font.render(title, True, theme.WHITE_HOVER)
        title_rect = title_surf.get_rect(center=(x + w // 2, y + int(h * 0.3)))
        screen.blit(title_surf, title_rect)

        # ---------- Button row ----------
        button_font = pygame.font.SysFont("Helvetica", int(h * 0.12), bold = True)

        # Size buttons by largest label + padding (keeps equal sizes)
        text_surfs = []
        max_tw = 0
        max_th = 0
        for _, text, _, _ in buttons:
            s = button_font.render(text, True, theme.BLACK)
            text_surfs.append(s)
            max_tw = max(max_tw, s.get_width())
            max_th = max(max_th, s.get_height())

        pad_x = int(w * 0.06)
        pad_y = int(h * 0.06)
        btn_w = max_tw + pad_x
        btn_h = max_th + pad_y

        # If panel is too narrow, clamp button width so they still fit
        gap = int(w * 0.05)
        total_w = len(buttons) * btn_w + (len(buttons) - 1) * gap
        if total_w > int(w * 0.92):
            btn_w = int((w * 0.92 - (len(buttons) - 1) * gap) / len(buttons))
            # keep height based on text
            btn_h = max(btn_h, int(h * 0.18))

        row_y = y + int(h * 0.7)  # lower half of panel
        start_x = x + (w - (len(buttons) * btn_w + (len(buttons) - 1) * gap)) // 2

        for i, ((key, text, color1, color2), text_surf) in enumerate(zip(buttons, text_surfs)):
            rect = pygame.Rect(
                start_x + i * (btn_w + gap),
                row_y - btn_h // 2,
                btn_w,
                btn_h
            )
            color = color2 if rect.collidepoint(mouse_pos) else color1
            pygame.draw.rect(screen, color, rect, border_radius=12)
            screen.blit(text_surf, text_surf.get_rect(center=rect.center))
            self.app.ui_hitboxes[key] = rect

    def draw_button(self, screen, rect, text, color, font):
        pygame.draw.rect(screen, color, rect, border_radius=12)
        text_surf = font.render(text, True, (0, 0, 0))
        screen.blit(text_surf, text_surf.get_rect(center=rect.center))
