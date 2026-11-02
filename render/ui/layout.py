import pygame

from config import BASE_W, BASE_H
from render import theme

# ======================================================================
#  Layout engine
#
#  Menus are described as a small tree of nodes (Text, Button, Cycle,
#  Slider, Stack, Grid ...).  Every node reports its own size, its parent
#  decides where it goes, and nothing is positioned with magic numbers --
#  so nodes cannot overlap, and a screen that is too big for the display
#  is automatically scaled down instead of running off the edge.
#
#  Sizes never depend on the *current* value of a setting (they are
#  measured from sample strings), so a screen is laid out once and only
#  drawn afterwards.  Dynamic values are passed as callables.
# ======================================================================

def _val(v):
    return v() if callable(v) else v


# ---------------------------------------------------------------- Nodes

class Node:
    def __init__(self):
        self.w = self.h = 0
        self.rect = pygame.Rect(0, 0, 0, 0)

    def measure(self):
        return self.w, self.h

    def place(self, x, y, w, h):
        """Centre this node inside the slot (x, y, w, h)."""
        self.rect = pygame.Rect(x + (w - self.w) // 2, y + (h - self.h) // 2, self.w, self.h)

    def draw(self, ui):
        pass


class Space(Node):
    def __init__(self, w=0, h=0):
        super().__init__()
        self.w, self.h = w, h


class Slot(Node):
    """Empty reserved area that registers a hitbox (e.g. for a thumbnail)."""
    def __init__(self, key, w, h):
        super().__init__()
        self.key = key
        self.w, self.h = w, h

    def draw(self, ui):
        ui.state.ui_hitboxes[self.key] = self.rect


class Text(Node):
    """`text` is a str, a callable returning a str, or a list of (str, colour) parts.
    `samples` lists every string it may show, so its width stays fixed."""

    def __init__(self, text, font, color=theme.WHITE, samples=None, align="center"):
        super().__init__()
        self.text, self.font, self.color = text, font, color
        self.samples, self.align = samples, align

    @staticmethod
    def _flat(t):
        return "".join(p[0] for p in t) if isinstance(t, list) else t

    def measure(self):
        samples = self.samples or [_val(self.text)]
        self.w = max(self.font.size(self._flat(s))[0] for s in samples)
        self.h = self.font.size("Ag")[1]
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        if self.align == "left":
            self.rect.left = x
        elif self.align == "right":
            self.rect.right = x + w

    def draw(self, ui):
        text = _val(self.text)
        parts = text if isinstance(text, list) else [(text, _val(self.color))]
        total = sum(self.font.size(t)[0] for t, _ in parts)
        x = {"left": self.rect.left, "right": self.rect.right - total}.get(
            self.align, self.rect.centerx - total // 2)
        for t, col in parts:
            surf = ui.text(self.font, t, col)
            ui.screen.blit(surf, (x, self.rect.centery - surf.get_height() // 2))
            x += surf.get_width()


class Button(Node):
    """Rounded button.  `colors` may be a callable returning (normal, hover)."""

    def __init__(self, key, text, font, colors, samples=None, fg=theme.BLACK):
        super().__init__()
        self.key, self.text, self.font = key, text, font
        self.colors, self.samples, self.fg = colors, samples, fg

    def measure(self):
        samples = self.samples or [_val(self.text)]
        self.w = max(self.font.size(s)[0] for s in samples) + int(BASE_W * 0.02)
        self.h = self.font.size("Ag")[1] + int(BASE_H * 0.02)
        return self.w, self.h

    def draw(self, ui):
        normal, hover = _val(self.colors)
        col = hover if self.rect.collidepoint(ui.mouse) else normal
        pygame.draw.rect(ui.screen, col, self.rect, border_radius=12)
        surf = ui.text(self.font, _val(self.text), self.fg)
        ui.screen.blit(surf, surf.get_rect(center=self.rect.center))
        ui.state.ui_hitboxes[self.key] = self.rect


class Cycle(Node):
    """[<]  value  [>]  -- the value box is as wide as the widest option."""

    def __init__(self, key, text, font, samples, color=theme.WHITE):
        super().__init__()
        self.key, self.text, self.font, self.samples, self.color = key, text, font, samples, color

    def measure(self):
        gap = int(BASE_W * 0.01)
        self.arrow_w = self.font.size("<")[0] + int(BASE_W * 0.02)
        self.arrow_h = self.font.size("Ag")[1] + int(BASE_H * 0.02)
        value_w = max(self.font.size(s)[0] for s in self.samples) + 2 * gap
        self.w = 2 * self.arrow_w + value_w + 2 * gap
        self.h = self.arrow_h
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        r = self.rect
        self.left = pygame.Rect(r.left, r.top, self.arrow_w, self.arrow_h)
        self.right = pygame.Rect(r.right - self.arrow_w, r.top, self.arrow_w, self.arrow_h)

    def draw(self, ui):
        for rect, glyph, suffix in ((self.left, "<", "_left"), (self.right, ">", "_right")):
            col = theme.GRAY_HOVER if rect.collidepoint(ui.mouse) else theme.GRAY
            pygame.draw.rect(ui.screen, col, rect, border_radius=12)
            surf = ui.text(self.font, glyph, theme.BLACK)
            ui.screen.blit(surf, surf.get_rect(center=rect.center))
            ui.state.ui_hitboxes[self.key + suffix] = rect

        surf = ui.text(self.font, _val(self.text), _val(self.color))
        ui.screen.blit(surf, surf.get_rect(center=self.rect.center))


class Slider(Node):
    """[Reset]  ----o----  label"""

    def __init__(self, key, value, color, font, label, label_sample,
                 reset_key=None, reset_font=None, track_w=None):
        super().__init__()
        self.key, self.value, self.color = key, value, color
        self.font, self.label, self.label_sample = font, label, label_sample
        self.reset_key, self.reset_font = reset_key, reset_font
        self.track_w = track_w or int(BASE_W * 0.18)

    def measure(self):
        self.gap = int(BASE_W * 0.012)
        self.track_h = int(BASE_H * 0.02)
        self.knob_r = int(self.track_h * 1.2)
        self.reset_w = self.reset_h = 0
        if self.reset_key:
            self.reset_w = self.reset_font.size("Reset")[0] + int(BASE_W * 0.015)
            self.reset_h = self.reset_font.size("Ag")[1] + int(BASE_H * 0.012)
        self.label_w = self.font.size(self.label_sample)[0]
        self.pad = self.knob_r + self.gap // 2      # the knob overhangs both ends of the track
        self.w = self.reset_w + self.pad + self.track_w + self.pad + self.label_w
        self.h = max(2 * self.knob_r + 2, self.reset_h)
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        r = self.rect
        x0 = r.left + self.reset_w + self.pad
        self.reset_rect = pygame.Rect(r.left, r.centery - self.reset_h // 2, self.reset_w, self.reset_h)
        self.track = pygame.Rect(x0, r.centery - self.track_h // 2, self.track_w, self.track_h)
        self.label_x = self.track.right + self.pad
        # grab area is as tall as the knob, not just the thin track
        self.grab = self.track.inflate(0, 2 * self.knob_r - self.track_h)

    def draw(self, ui):
        screen, t = ui.screen, self.track
        value = max(0.0, min(1.0, _val(self.value)))

        pygame.draw.rect(screen, theme.DARK_GRAY, t, border_radius=6)
        fill_w = int(t.width * value)
        if fill_w > 0:
            pygame.draw.rect(screen, self.color, (t.x, t.y, fill_w, t.height), border_radius=6)

        kx, ky = t.x + fill_w, t.centery
        dx, dy = ui.mouse[0] - kx, ui.mouse[1] - ky
        hot = dx * dx + dy * dy <= self.knob_r ** 2
        pygame.draw.circle(screen, theme.WHITE_HOVER if hot else theme.WHITE, (kx, ky), self.knob_r)

        surf = ui.text(self.font, _val(self.label), theme.WHITE)
        screen.blit(surf, surf.get_rect(midleft=(self.label_x, ky)))

        if self.reset_key:
            hov = self.reset_rect.collidepoint(ui.mouse)
            pygame.draw.rect(screen, theme.WHITE_HOVER if hov else theme.WHITE,
                             self.reset_rect, border_radius=12)
            rs = ui.text(self.reset_font, "Reset", theme.BLACK)
            screen.blit(rs, rs.get_rect(center=self.reset_rect.center))
            ui.state.ui_hitboxes[self.reset_key] = self.reset_rect

        ui.state.ui_hitboxes[self.key] = self.grab


# ----------------------------------------------------------- Containers

class Stack(Node):
    """Children in a column (vertical) or a row, centred on the cross axis.
    `uniform` makes every child as large as the largest one."""

    def __init__(self, children, vertical=True, gap=0, uniform=False):
        super().__init__()
        self.children, self.vertical, self.gap, self.uniform = children, vertical, gap, uniform

    def measure(self):
        sizes = [c.measure() for c in self.children]
        if self.uniform and sizes:
            mw, mh = max(s[0] for s in sizes), max(s[1] for s in sizes)
            for c in self.children:
                c.w, c.h = mw, mh
            sizes = [(mw, mh)] * len(sizes)
        gaps = self.gap * max(0, len(sizes) - 1)
        if self.vertical:
            self.w = max((s[0] for s in sizes), default=0)
            self.h = sum(s[1] for s in sizes) + gaps
        else:
            self.w = sum(s[0] for s in sizes) + gaps
            self.h = max((s[1] for s in sizes), default=0)
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        r = self.rect
        pos = r.top if self.vertical else r.left
        for c in self.children:
            if self.vertical:
                c.place(r.left, pos, r.width, c.h)
                pos += c.h + self.gap
            else:
                c.place(pos, r.top, c.w, r.height)
                pos += c.w + self.gap

    def draw(self, ui):
        for c in self.children:
            c.draw(ui)


class Grid(Node):
    """Rows of cells; columns share a width and rows share a height, so
    everything lines up.  Cells hang from the top of their row so headers share a
    line; a short row is centred under the full ones."""

    def __init__(self, rows, gap_x=0, gap_y=0, uniform=False):
        super().__init__()
        self.rows, self.gap_x, self.gap_y, self.uniform = rows, gap_x, gap_y, uniform

    def measure(self):
        cols = max((len(r) for r in self.rows), default=0)
        sizes = [[c.measure() for c in row] for row in self.rows]
        self.col_w = [max((sizes[r][c][0] for r in range(len(sizes)) if c < len(sizes[r])), default=0)
                      for c in range(cols)]
        self.row_h = [max((s[1] for s in row), default=0) for row in sizes]
        if self.uniform:
            self.col_w = [max(self.col_w, default=0)] * cols
            self.row_h = [max(self.row_h, default=0)] * len(self.rows)
            for row in self.rows:
                for c in row:
                    c.w, c.h = self.col_w[0], self.row_h[0]
        self.w = sum(self.col_w) + self.gap_x * max(0, cols - 1)
        self.h = sum(self.row_h) + self.gap_y * max(0, len(self.rows) - 1)
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        cy = self.rect.top
        for ri, row in enumerate(self.rows):
            row_w = sum(self.col_w[:len(row)]) + self.gap_x * max(0, len(row) - 1)
            cx = self.rect.left + (self.w - row_w) // 2
            for ci, c in enumerate(row):
                c.place(cx, cy, self.col_w[ci], c.h)
                cx += self.col_w[ci] + self.gap_x
            cy += self.row_h[ri] + self.gap_y

    def draw(self, ui):
        for row in self.rows:
            for c in row:
                c.draw(ui)


class Frame(Node):
    """Panel with padding around a single child (used by overlays)."""

    def __init__(self, child, pad):
        super().__init__()
        self.child, self.pad = child, pad

    def measure(self):
        cw, ch = self.child.measure()
        self.w, self.h = cw + 2 * self.pad, ch + 2 * self.pad
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        r = self.rect
        self.child.place(r.left + self.pad, r.top + self.pad,
                         r.width - 2 * self.pad, r.height - 2 * self.pad)

    def draw(self, ui):
        ui.screen.blit(ui.panel_surf(self.rect.width, self.rect.height), self.rect.topleft)
        self.child.draw(ui)


# ------------------------------------------------------------ UILayout

class UILayout:
    """Owns the shared drawing caches and turns a builder into a laid-out,
    cached screen.  A builder is `builder(scale) -> body node`; the engine
    tries scale 1.0 and shrinks until the screen fits."""

    SCALES = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5)

    def __init__(self, app):
        self.app = app
        self.margin_x = int(BASE_W * 0.04)
        self.margin_y = int(BASE_H * 0.03)
        self.gap = int(BASE_H * 0.02)

        self._text_cache = {}
        self._panel_cache = {}
        self._dim_surf = None

        # set every frame by screen_menu()/overlay()
        self.screen = None
        self.state = None
        self.mouse = (0, 0)

    # ---------- Shared caches ----------
    def fnt(self, frac, scale=1.0, bold=True):
        return self.app.font_manager.get("helvetica", max(8, int(BASE_H * frac * scale)), bold=bold)

    def text(self, font, text, color):
        key = (font, text, color)
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 512:
                self._text_cache.clear()
            surf = self._text_cache[key] = font.render(text, True, color)
        return surf

    def panel_surf(self, w, h):
        key = (w, h)
        if key not in self._panel_cache:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (30, 30, 30, 230), surf.get_rect(), border_radius=18)
            pygame.draw.rect(surf, (90, 90, 90, 255), surf.get_rect(), width=2, border_radius=18)
            self._panel_cache[key] = surf
        return self._panel_cache[key]

    def dim_surf(self):
        if self._dim_surf is None:
            self._dim_surf = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
            self._dim_surf.fill((0, 0, 0, 170))
        return self._dim_surf

    # ---------- Full-screen menus ----------
    def screen_menu(self, state, screen, builder, *, title, color,
                    title_size=0.14, back=True):
        """Title at the top, optional Back button at the bottom, body centred between."""
        laid = getattr(state, "_laid", None)
        if laid is None:
            laid = state._laid = self._fit_screen(builder, title, color, title_size, back)
        title_node, body, back_node = laid

        self._begin(state, screen)
        title_node.draw(self)
        body.draw(self)
        if back_node:
            back_node.draw(self)

    def _fit_screen(self, builder, title, color, title_size, back):
        for scale in self.SCALES:
            title_node = Text(title, self.fnt(title_size, scale), color)
            back_node = (Button("back", "Back", self.fnt(0.04, scale),
                                (theme.RED, theme.RED_HOVER)) if back else None)
            body = builder(scale)

            title_node.measure()
            body.measure()
            if back_node:
                back_node.measure()

            top = self.margin_y
            title_node.place(0, top, BASE_W, title_node.h)
            top += title_node.h + self.gap
            bottom = BASE_H - self.margin_y
            if back_node:
                back_node.place(0, bottom - back_node.h, BASE_W, back_node.h)
                bottom -= back_node.h + self.gap

            fits = body.h <= bottom - top and body.w <= BASE_W - 2 * self.margin_x
            if fits or scale == self.SCALES[-1]:
                body.place(0, top, BASE_W, bottom - top)
                return title_node, body, back_node

    # ---------- Overlays ----------
    def overlay(self, state, screen, builder, *, dim=True, pad=None):
        """Auto-sized panel centred on screen, over an optional dimmed backdrop."""
        laid = getattr(state, "_laid", None)
        if laid is None:
            laid = state._laid = self._fit_overlay(builder, pad)

        self._begin(state, screen)
        if dim:
            screen.blit(self.dim_surf(), (0, 0))
        laid.draw(self)

    def _fit_overlay(self, builder, pad):
        pad = pad if pad is not None else int(BASE_H * 0.04)
        for scale in self.SCALES:
            frame = Frame(builder(scale), int(pad * scale))
            frame.measure()
            if (frame.w <= BASE_W * 0.9 and frame.h <= BASE_H * 0.9) or scale == self.SCALES[-1]:
                frame.place(0, 0, BASE_W, BASE_H)
                return frame

    def _begin(self, state, screen):
        self.screen, self.state = screen, state
        self.mouse = self.app.window_to_base(pygame.mouse.get_pos())
