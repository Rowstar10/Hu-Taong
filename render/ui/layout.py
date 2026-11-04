import pygame

from config import BASE_W, BASE_H
from render import theme
from render.art import ADD, mix

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
    tip = None          # text (or a callable returning it) shown when the mouse rests here

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
    def __init__(self, key, w, h, tip=None):
        super().__init__()
        self.key = key
        self.w, self.h = w, h
        self.tip = tip

    def draw(self, ui):
        ui.state.ui_hitboxes[self.key] = self.rect
        ui.offer_tip(self.rect, self.tip)


class Text(Node):
    """`text` is a str, a callable returning a str, or a list of (str, colour) parts.
    `samples` lists every string it may show, so its width stays fixed."""

    def __init__(self, text, font, color=theme.PARCHMENT, samples=None, align="center"):
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
            y = self.rect.centery - surf.get_height() // 2
            ui.screen.blit(ui.text(self.font, t, theme.INK), (x + 2, y + 2))
            ui.screen.blit(surf, (x, y))
            x += surf.get_width()


class Label(Node):
    """A section heading between two plum blossoms."""

    FLOWER = 26

    def __init__(self, text, font):
        super().__init__()
        self.text, self.font = text, font

    def measure(self):
        self.w = self.font.size(self.text)[0] + 2 * (self.FLOWER + 12)
        self.h = self.font.size("Ag")[1]
        return self.w, self.h

    def draw(self, ui):
        cx, cy = self.rect.center
        ui.renderer.text(ui.screen, self.text, self.font, theme.GOLD, center=(cx, cy))
        half = self.w // 2 - self.FLOWER // 2
        flower = ui.art.blossom(self.FLOWER)
        ui.screen.blit(flower, flower.get_rect(center=(cx - half, cy)))
        ui.screen.blit(flower, flower.get_rect(center=(cx + half, cy)))


class Title(Node):
    """Gilded calligraphy, used for the headline of an overlay."""

    def __init__(self, text, font, color):
        super().__init__()
        self.text, self.font, self.color = text, font, color

    def measure(self):
        self.w, self.h = self.font.size(self.text)
        return self.w, self.h

    def draw(self, ui):
        tint = _val(self.color)
        surf = ui.art.gilded(self.text, self.font, top=mix(tint, (255, 255, 255), .55), bottom=tint)
        ui.screen.blit(surf, surf.get_rect(center=self.rect.center))


class Button(Node):
    """Lacquered button.  `colors` may be a callable returning (normal, hover);
    the normal colour picks the finish, and DARK_GRAY means greyed out."""

    def __init__(self, key, text, font, colors, samples=None, tip=None):
        super().__init__()
        self.key, self.text, self.font = key, text, font
        self.colors, self.samples, self.tip = colors, samples, tip

    def measure(self):
        samples = self.samples or [_val(self.text)]
        self.w = max(self.font.size(s)[0] for s in samples) + int(BASE_W * 0.03)
        self.h = self.font.size("Ag")[1] + int(BASE_H * 0.024)
        return self.w, self.h

    def draw(self, ui):
        normal, _ = _val(self.colors)
        enabled = normal != theme.DARK_GRAY
        ui.renderer.draw_lacquer(ui.screen, ui.mouse if enabled else (-1, -1), self.rect,
                                 _val(self.text), self.font, theme.finish(normal),
                                 fg=None if enabled else theme.GRAY)
        ui.state.ui_hitboxes[self.key] = self.rect
        ui.offer_tip(self.rect, self.tip)


class Toggle(Node):
    """Dark plaque stamped with a seal that reads on or off."""

    def __init__(self, key, text, font, on, samples, tip=None):
        super().__init__()
        self.key, self.text, self.font, self.on, self.samples = key, text, font, on, samples
        self.tip = tip

    def measure(self):
        self.h = self.font.size("Ag")[1] + 22
        self.w = max(self.font.size(s)[0] for s in self.samples) + self.h + 34
        return self.w, self.h

    def draw(self, ui):
        ui.renderer.draw_toggle(ui.screen, ui.mouse, self.rect, _val(self.text), self.font, _val(self.on))
        ui.state.ui_hitboxes[self.key] = self.rect
        ui.offer_tip(self.rect, self.tip)


class CycleToggle(Node):
    """A toggle that steps through several settings, one per click, with a seal for each."""

    def __init__(self, key, texts, font, level, glyphs, tip=None):
        super().__init__()
        self.key, self.texts, self.font, self.level, self.glyphs = key, texts, font, level, glyphs
        self.tip = tip

    def measure(self):
        self.h = self.font.size("Ag")[1] + 22
        self.w = max(self.font.size(s)[0] for s in self.texts) + self.h + 34
        return self.w, self.h

    def draw(self, ui):
        level = _val(self.level)
        ui.renderer.draw_toggle(ui.screen, ui.mouse, self.rect, self.texts[level], self.font, level > 0,
                                glyph=self.glyphs[level], hot=level > 1)
        ui.state.ui_hitboxes[self.key] = self.rect
        ui.offer_tip(self.rect, self.tip)


class KeyButton(Node):
    """A key binding.  While it waits for a new key it glows and asks for one."""

    def __init__(self, key, text, font, listening, samples, tip=None):
        super().__init__()
        self.key, self.text, self.font, self.listening, self.samples = key, text, font, listening, samples
        self.tip = tip

    def measure(self):
        self.w = max(self.font.size(s)[0] for s in self.samples) + int(BASE_W * 0.03)
        self.h = self.font.size("Ag")[1] + int(BASE_H * 0.02)
        return self.w, self.h

    def draw(self, ui):
        waiting = _val(self.listening)
        text = "Press a key" if waiting else _val(self.text)
        ui.renderer.draw_lacquer(ui.screen, ui.mouse, self.rect, text, self.font, "crimson" if waiting else "ink")
        ui.state.ui_hitboxes[self.key] = self.rect
        ui.offer_tip(self.rect, self.tip)


class Cycle(Node):
    """[<]  value  [>]  -- the value box is as wide as the widest option.  With `pick` the value
    box itself is clickable too (its hitbox is `pick`), e.g. to open a list of every option."""

    def __init__(self, key, text, font, samples, color=theme.PARCHMENT, tip=None, pick=None):
        super().__init__()
        self.key, self.text, self.font, self.samples, self.color = key, text, font, samples, color
        self.tip, self.pick = tip, pick

    def measure(self):
        gap = int(BASE_W * 0.007)
        self.arrow = self.font.size("Ag")[1] + 12
        value_w = max(self.font.size(s)[0] for s in self.samples) + 4 * gap
        self.w = 2 * self.arrow + value_w + 2 * gap
        self.h = self.arrow
        self.gap = gap
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        r = self.rect
        self.left = pygame.Rect(r.left, r.top, self.arrow, self.arrow)
        self.right = pygame.Rect(r.right - self.arrow, r.top, self.arrow, self.arrow)
        self.plate = pygame.Rect(self.left.right + self.gap, r.top + 2,
                                 r.width - 2 * (self.arrow + self.gap), self.arrow - 4)

    def draw(self, ui):
        ui.screen.blit(ui.art.inset(self.plate.w, self.plate.h), self.plate)
        color = _val(self.color)
        if self.pick:
            hot = self.plate.collidepoint(ui.mouse)
            color = theme.GOLD_BRIGHT if hot else color
            # a small down-pointing mark says the box opens
            x, y, s = self.plate.right - self.gap - 10, self.plate.centery + 2, 7
            pygame.draw.polygon(ui.screen, theme.GOLD_BRIGHT if hot else theme.GOLD,
                                [(x - s, y - s // 2), (x + s, y - s // 2), (x, y + s // 2 + 1)])
            ui.state.ui_hitboxes[self.pick] = self.plate
        ui.renderer.text(ui.screen, _val(self.text), self.font, color, center=self.plate.center)

        for rect, left, suffix in ((self.left, True, "_left"), (self.right, False, "_right")):
            ui.screen.blit(ui.art.chevron(rect.w, left, rect.collidepoint(ui.mouse)), rect)
            ui.state.ui_hitboxes[self.key + suffix] = rect
        ui.offer_tip(self.rect, self.tip)


class Slider(Node):
    """[Reset]  ----o----  label"""

    def __init__(self, key, value, color, font, label, label_sample,
                 reset_key=None, reset_font=None, track_w=None, tip=None):
        super().__init__()
        self.key, self.value, self.color, self.tip = key, value, color, tip
        self.font, self.label, self.label_sample = font, label, label_sample
        self.reset_key, self.reset_font = reset_key, reset_font
        self.track_w = track_w or int(BASE_W * 0.18)

    def measure(self):
        self.gap = int(BASE_W * 0.012)
        self.track_h = int(BASE_H * 0.017)
        self.knob_r = int(self.track_h * 1.4)
        self.reset_w = self.reset_h = 0
        if self.reset_key:
            self.reset_w = self.reset_font.size("Reset")[0] + int(BASE_W * 0.018)
            self.reset_h = self.reset_font.size("Ag")[1] + int(BASE_H * 0.014)
        self.label_w = self.font.size(self.label_sample)[0] + 28
        self.label_h = self.font.size("Ag")[1] + 6
        self.pad = self.knob_r + self.gap // 2      # the knob overhangs both ends of the track
        self.w = self.reset_w + self.pad + self.track_w + self.pad + self.label_w
        self.h = max(2 * self.knob_r + 2, self.reset_h, self.label_h)
        return self.w, self.h

    def place(self, x, y, w, h):
        super().place(x, y, w, h)
        r = self.rect
        x0 = r.left + self.reset_w + self.pad
        self.reset_rect = pygame.Rect(r.left, r.centery - self.reset_h // 2, self.reset_w, self.reset_h)
        self.track = pygame.Rect(x0, r.centery - self.track_h // 2, self.track_w, self.track_h)
        self.plate = pygame.Rect(self.track.right + self.pad, r.centery - self.label_h // 2,
                                 self.label_w, self.label_h)
        # grab area is as tall as the knob, not just the thin track
        self.grab = self.track.inflate(0, 2 * self.knob_r - self.track_h)

    def draw(self, ui):
        screen, t, art = ui.screen, self.track, ui.art
        value = max(0.0, min(1.0, _val(self.value)))

        screen.blit(art.inset(t.w, t.h), t)
        fill_w = int((t.w - 6) * value)
        if fill_w > 0:
            bar = art.slider_fill(t.w - 6, t.h - 6, self.color)
            screen.blit(bar, (t.x + 3, t.y + 3), (0, 0, fill_w, t.h - 6))

        kx, ky = t.x + 3 + fill_w, t.centery
        dx, dy = ui.mouse[0] - kx, ui.mouse[1] - ky
        hot = dx * dx + dy * dy <= self.knob_r ** 2
        if hot:
            halo = art.glow(48, (120, 54, 20))
            screen.blit(halo, halo.get_rect(center=(kx, ky)), special_flags=ADD)
        knob = art.blossom(2 * self.knob_r + (8 if hot else 0), (214, 168, 88), (150, 26, 26))
        screen.blit(knob, knob.get_rect(center=(kx, ky)))

        screen.blit(art.inset(self.plate.w, self.plate.h), self.plate)
        ui.renderer.text(screen, _val(self.label), self.font, theme.PARCHMENT, center=self.plate.center)

        if self.reset_key:
            ui.renderer.draw_lacquer(screen, ui.mouse, self.reset_rect, "Reset", self.reset_font, "ink")
            ui.state.ui_hitboxes[self.reset_key] = self.reset_rect

        ui.state.ui_hitboxes[self.key] = self.grab
        if self.reset_key and self.reset_rect.collidepoint(ui.mouse):
            ui.offer_tip(self.reset_rect, "Back to the default value.")
        else:
            ui.offer_tip(self.rect, self.tip)


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
    """Lacquered panel with padding around a single child (used by overlays)."""

    def __init__(self, child, pad, mark=None):
        super().__init__()
        self.child, self.pad, self.mark = child, pad, mark

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
        ui.renderer.draw_board(ui.screen, self.rect, self.mark)
        self.child.draw(ui)


# ------------------------------------------------------------ UILayout

class UILayout:
    """Owns the shared drawing caches and turns a builder into a laid-out,
    cached screen.  A builder is `builder(scale) -> body node`; the engine
    tries scale 1.0 and shrinks until the screen fits."""

    SCALES = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5)

    # The lacquered board every settings screen sits on, and the room inside it
    PANEL = pygame.Rect(120, 130, 1680, 790)
    PANEL_TOP = 72
    PANEL_BOTTOM = 56
    PANEL_SIDE = 60
    FOOTER_Y = 1004

    def __init__(self, app):
        self.app = app
        self.art = app.art
        self.gap = int(BASE_H * 0.02)

        self._text_cache = {}
        self._dim_surf = None

        # set every frame by screen_menu()/overlay()
        self.screen = None
        self.state = None
        self.mouse = (0, 0)

    @property
    def renderer(self):
        return self.app.renderer

    # ---------- Shared caches ----------
    def fnt(self, frac, scale=1.0, bold=True):
        return self.app.font_manager.get("ui", max(8, int(BASE_H * frac * scale)), bold=bold)

    def brush(self, frac, scale=1.0):
        return self.app.font_manager.get("brush", max(8, int(BASE_H * frac * scale)))

    def text(self, font, text, color):
        key = (font, text, color)
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 512:
                self._text_cache.clear()
            surf = self._text_cache[key] = font.render(text, True, color)
        return surf

    def dim_surf(self):
        if self._dim_surf is None:
            self._dim_surf = pygame.Surface((BASE_W, BASE_H))
            self._dim_surf.fill((14, 3, 5))
            self._dim_surf.set_alpha(165)
        return self._dim_surf

    # ---------- Full-screen menus ----------
    def screen_menu(self, state, screen, builder, *, title, mark, reset=None, back=True):
        """Title board, a lacquered panel holding the body, and a footer of Back and Reset."""
        laid = getattr(state, "_laid", None)
        if laid is None:
            laid = state._laid = self._fit_screen(builder, reset, back)
        body, footer = laid

        self._begin(state, screen)
        self.renderer.draw_frame(screen, title, mark)
        body.draw(self)
        for node in footer:
            node.draw(self)

    def _fit_screen(self, builder, reset, back):
        p = self.PANEL
        top, bottom = p.top + self.PANEL_TOP, p.bottom - self.PANEL_BOTTOM

        for scale in self.SCALES:
            body = builder(scale)
            body.measure()
            fits = body.h <= bottom - top and body.w <= p.width - 2 * self.PANEL_SIDE
            if fits or scale == self.SCALES[-1]:
                body.place(p.left, top, p.width, bottom - top)
                break

        footer = []
        if back:
            node = Button("back", "Back", self.fnt(0.04), (theme.RED, theme.RED_HOVER))
            node.measure()
            node.w = max(node.w, 280)
            node.place(0, self.FOOTER_Y - node.h // 2, BASE_W, node.h)
            footer.append(node)
        if reset:
            node = Button("reset_defaults", reset, self.fnt(0.034), (theme.WHITE, theme.WHITE_HOVER),
                          tip="Put every setting on this screen back to its default.")
            node.measure()
            node.place(p.right - node.w, self.FOOTER_Y - node.h // 2, node.w, node.h)
            footer.append(node)
        return body, footer

    # ---------- Overlays ----------
    def overlay(self, state, screen, builder, *, dim=True, pad=None, mark=None):
        """Auto-sized panel centred on screen, over an optional dimmed backdrop."""
        laid = getattr(state, "_laid", None)
        if laid is None:
            laid = state._laid = self._fit_overlay(builder, pad, mark)

        self._begin(state, screen)
        if dim:
            screen.blit(self.dim_surf(), (0, 0))
        laid.draw(self)

    def _fit_overlay(self, builder, pad, mark):
        pad = pad if pad is not None else int(BASE_H * 0.065)
        for scale in self.SCALES:
            frame = Frame(builder(scale), int(pad * scale), mark)
            frame.measure()
            if (frame.w <= BASE_W * 0.9 and frame.h <= BASE_H * 0.9) or scale == self.SCALES[-1]:
                frame.place(0, 0, BASE_W, BASE_H)
                return frame

    def offer_tip(self, rect, tip):
        if tip and rect.collidepoint(self.mouse):
            self.renderer.tips.offer(rect, _val(tip))

    def _begin(self, state, screen):
        self.screen, self.state = screen, state
        self.mouse = self.app.window_to_base(pygame.mouse.get_pos())
