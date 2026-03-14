import math, pygame

from render import theme

class UILayout:

    def __init__(self, app):
        self.app = app

    def draw_button_grid(self,
                         state,
                         screen,
                         panel_rect,
                         buttons,
                         *,
                         cols=2,
                         btn_font,
                         btn_scale=0.12,
                         gap_scale_x=0.04,
                         gap_scale_y=0.06,
                         text_color=theme.BLACK):

        x, y, w, h = panel_rect
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        # ---------- Render text ----------
        text_surfs = []
        max_tw = 0
        max_th = 0

        for _, text, _, _ in buttons:
            surf = btn_font.render(text, True, text_color)
            text_surfs.append(surf)
            max_tw = max(max_tw, surf.get_width())
            max_th = max(max_th, surf.get_height())

        # ---------- Button size ----------
        pad_x = int(w * 0.06)
        pad_y = int(h * 0.06)

        btn_w = max_tw + pad_x
        btn_h = max_th + pad_y

        # ---------- Grid settings ----------
        gap_x = int(w * gap_scale_x)
        gap_y = int(h * gap_scale_y)

        rows = math.ceil(len(buttons) / cols)

        grid_h = rows * btn_h + (rows - 1) * gap_y
        start_y = y + int(h * 0.6) - grid_h // 2

        index = 0

        for row in range(rows):

            row_count = min(cols, len(buttons) - index)

            row_w = row_count * btn_w + (row_count - 1) * gap_x
            start_x = x + (w - row_w) // 2

            for col in range(row_count):

                key, text, color1, color2 = buttons[index]
                text_surf = text_surfs[index]

                rect = pygame.Rect(
                    start_x + col * (btn_w + gap_x),
                    start_y + row * (btn_h + gap_y),
                    btn_w,
                    btn_h
                )

                color = color2 if rect.collidepoint(mouse_pos) else color1

                pygame.draw.rect(screen, color, rect, border_radius=12)
                screen.blit(text_surf, text_surf.get_rect(center=rect.center))

                state.ui_hitboxes[key] = rect

                index += 1
