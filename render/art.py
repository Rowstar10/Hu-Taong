"""Procedural Hu Tao art.

Everything here is drawn once, usually at a higher resolution and scaled down
for smooth edges, then cached. The main loop only ever blits the results.
"""
import math, random, pygame

from render import theme

SRCALPHA = pygame.SRCALPHA
ADD = pygame.BLEND_RGB_ADD
MULT = pygame.BLEND_RGBA_MULT
CUT = pygame.BLEND_RGBA_MIN

# ---------- Palette helpers ----------

def rgba(color, alpha=255):
    return (color[0], color[1], color[2], alpha)

def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def scaled(color, k):
    if len(color) == 3:     # the usual case, spelt out as this runs a few hundred times a frame
        r, g, b = color
        return (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))
    return tuple(min(255, int(c * k)) for c in color)

# ---------- Surface helpers ----------

def blank(w, h):
    return pygame.Surface((max(1, int(w)), max(1, int(h))), SRCALPHA)

def shrink(surf, w, h):
    return pygame.transform.smoothscale(surf, (max(1, int(w)), max(1, int(h))))

def blur(surf, factor):
    w, h = surf.get_size()
    small = shrink(surf, w / factor, h / factor)
    return pygame.transform.smoothscale(small, (w, h))

def v_gradient(w, h, stops):
    """Vertical gradient through [(position, rgba), ...] stops."""
    h = max(2, int(h))
    strip = blank(1, h)
    for y in range(h):
        t = y / (h - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if t <= p1:
                strip.set_at((0, y), mix(c0, c1, (t - p0) / max(p1 - p0, 1e-6)))
                break
    return pygame.transform.scale(strip, (max(1, int(w)), h))

def h_gradient(w, h, stops):
    return pygame.transform.rotate(v_gradient(h, w, stops), 90)

def radial(radius, inner, outer, power=2.0):
    """Soft radial blob, built small and scaled up."""
    n = min(radius, 48)
    surf = blank(2 * n, 2 * n)
    for y in range(2 * n):
        for x in range(2 * n):
            d = math.hypot(x - n + 0.5, y - n + 0.5) / n
            t = min(1.0, d) ** (1 / power)
            surf.set_at((x, y), mix(inner, outer, t))
    return pygame.transform.smoothscale(surf, (2 * radius, 2 * radius))

_SPECKLE_TILES = {}

def speckle(w, h, low, high, seed=7):
    """Grain to multiply over paper and lacquer.  The 128 px tile is made from random bytes in
    one go (setting pixels one at a time took long enough to stall a menu on the first hover)."""
    n = 128
    key = (low, high, seed)
    tile = _SPECKLE_TILES.get(key)
    if tile is None:
        table = bytes(low + i * (high - low + 1) // 256 for i in range(256))
        grey = random.Random(seed).randbytes(n * n).translate(table)
        rgb = bytearray(3 * n * n)
        rgb[0::3] = rgb[1::3] = rgb[2::3] = grey
        tile = _SPECKLE_TILES[key] = pygame.image.frombuffer(bytes(rgb), (n, n), "RGB").copy()
    surf = pygame.Surface((max(1, int(w)), max(1, int(h))))
    for y in range(0, int(h), n):
        for x in range(0, int(w), n):
            surf.blit(tile, (x, y))
    return surf

def bezier(p0, p1, p2, p3, steps=24):
    pts = []
    for i in range(steps):
        t = i / steps
        u = 1 - t
        pts.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return pts

def stepped_rect(x, y, w, h, s):
    """Rectangle with the stepped corners of a Chinese window frame."""
    r, b = x + w, y + h
    return [(x + 2*s, y), (r - 2*s, y), (r - 2*s, y + s), (r - s, y + s), (r - s, y + 2*s), (r, y + 2*s),
            (r, b - 2*s), (r - s, b - 2*s), (r - s, b - s), (r - 2*s, b - s), (r - 2*s, b),
            (x + 2*s, b), (x + 2*s, b - s), (x + s, b - s), (x + s, b - 2*s), (x, b - 2*s),
            (x, y + 2*s), (x + s, y + 2*s), (x + s, y + s), (x + 2*s, y + s)]

def split(surf, inset):
    """Cut a sprite into its middle and four edges, as (piece, offset) pairs.  The middle
    comes out opaque, so it should be one that is (all but) opaque already."""
    w, h = surf.get_size()
    if w <= 2 * inset or h <= 2 * inset:
        return [(surf, (0, 0))]
    middle = pygame.Surface((w - 2 * inset, h - 2 * inset))
    middle.blit(surf, (-inset, -inset))
    pieces = [(middle, (inset, inset))]
    for rect in ((0, 0, w, inset), (0, h - inset, w, inset),
                 (0, inset, inset, h - 2 * inset), (w - inset, inset, inset, h - 2 * inset)):
        pieces.append((surf.subsurface(rect).copy(), rect[:2]))
    return pieces

def meander_band(w, color, unit=22):
    """A strip of the square-spiral fret pattern (hui wen)."""
    band = blank(w, unit)
    u = unit - 2
    path = [(0, u), (0, 0), (u, 0), (u, u * .72), (u * .28, u * .72), (u * .28, u * .3),
            (u * .68, u * .3), (u * .68, u * .5)]
    for x in range(0, w, unit + 4):
        pygame.draw.lines(band, color, False, [(x + px, 1 + py) for px, py in path], 2)
    return band


class Art:
    def __init__(self, app):
        self.app = app
        self.cache = {}

    def get(self, key, build, *args):
        surf = self.cache.get(key)
        if surf is None:
            surf = self.cache[key] = self.fast(build(*args))
        return surf

    def fast(self, surf):
        """Match the display's pixel format, so blits skip a conversion.  Sprites with see-through
        parts are also run-length encoded: the blit then skips their clear pixels in whole runs,
        which draws them two to ten times faster, and exactly the same."""
        if pygame.display.get_surface() is None:
            return surf
        if surf.get_flags() & SRCALPHA:
            # keep the sprite's own see-through level (a tint layer has one); only add the encoding
            alpha = surf.get_alpha()
            surf = surf.convert_alpha()
            surf.set_alpha(255 if alpha is None else alpha, pygame.RLEACCEL)
            return surf
        return surf.convert()

    def brush(self, size):
        return self.app.font_manager.get("brush", int(size))

    def ui(self, size, bold=True):
        return self.app.font_manager.get("ui", int(size), bold=bold)

    # ---------- Text ----------

    def text(self, text, font, color):
        key = ("text", id(font), text, color)
        if key not in self.cache:
            if len(self.cache) > 6000:
                self.cache = {k: v for k, v in self.cache.items() if k[0] != "text"}
            self.cache[key] = self.fast(font.render(text, True, color))
        return self.cache[key]

    def gilded(self, text, font, top=theme.GOLD_BRIGHT, bottom=(204, 130, 58),
               outline=theme.INK, thickness=3, glow=theme.CRIMSON):
        """Gradient lettering with an outline and a soft glow behind it."""
        key = ("gilded", id(font), text, top, bottom, outline, thickness, glow)
        return self.get(key, self._gilded, text, font, top, bottom, outline, thickness, glow)

    def _gilded(self, text, font, top, bottom, outline, thickness, glow):
        mask = font.render(text, True, (255, 255, 255))
        w, h = mask.get_size()
        margin = thickness + 26
        surf = blank(w + 2 * margin, h + 2 * margin)

        if glow:
            halo = blank(w + 2 * margin, h + 2 * margin)
            halo.blit(font.render(text, True, glow), (margin, margin))
            halo = blur(blur(halo, 4), 3)
            surf.blit(halo, (0, 0))
            surf.blit(halo, (0, 0))

        if thickness:
            edge = font.render(text, True, outline)
            for i in range(16):
                a = i * math.tau / 16
                surf.blit(edge, (margin + math.cos(a) * thickness, margin + math.sin(a) * thickness))

        fill = v_gradient(w, h, [(0, rgba(top)), (.55, rgba(mix(top, bottom, .45))), (1, rgba(bottom))])
        fill.blit(mask, (0, 0), special_flags=CUT)
        surf.blit(fill, (margin, margin))
        return surf

    # ---------- Light ----------

    def glow(self, radius, color, power=2.2):
        """Opaque black-backed blob, meant for additive blits."""
        key = ("glow", radius, color, power)
        return self.get(key, self._glow, radius, color, power)

    def _glow(self, radius, color, power):
        # Scaled from one small master, tinted before it is scaled up: tinting a big surface
        # is slow enough to stall the frame that first asks for it
        small = self.get(("glow_master", power), self._glow_master, power).copy()
        small.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        return pygame.transform.smoothscale(small, (2 * radius, 2 * radius))

    def _glow_master(self, power):
        surf = pygame.Surface((96, 96))
        surf.blit(radial(48, (255, 255, 255, 255), (0, 0, 0, 255), power), (0, 0))
        return surf

    def vignette(self, w, h, color=(14, 2, 4), strength=150, spread=1.8):
        return self.get(("vignette", w, h, color, strength, spread), self._vignette, w, h, color, strength, spread)

    def _vignette(self, w, h, color, strength, spread):
        small = blank(96, 54)
        for y in range(54):
            for x in range(96):
                dx, dy = (x - 47.5) / 47.5, (y - 26.5) / 26.5
                d = min(1.0, (dx * dx + dy * dy) / spread)
                small.set_at((x, y), rgba(color, int(strength * d * d)))
        return pygame.transform.smoothscale(small, (w, h))

    # ---------- Plum blossom ----------

    def blossom(self, size, petal=(214, 40, 52), heart=(255, 214, 140)):
        return self.get(("blossom", size, petal, heart), self._blossom, size, petal, heart)

    def _blossom(self, size, petal, heart):
        s = size * 4
        c = s / 2
        surf = blank(s, s)
        for layer, (col, k) in enumerate(((scaled(petal, .62), 1.0), (petal, .86), (mix(petal, (255, 170, 160), .5), .52))):
            r = s * .235 * k
            for i in range(5):
                a = -math.pi / 2 + i * math.tau / 5
                d = s * .245
                pygame.draw.circle(surf, col, (c + math.cos(a) * d, c + math.sin(a) * d), r)
        pygame.draw.circle(surf, scaled(petal, .55), (c, c), s * .13)
        for i in range(11):
            a = i * math.tau / 11
            tip = (c + math.cos(a) * s * .21, c + math.sin(a) * s * .21)
            pygame.draw.line(surf, heart, (c, c), tip, max(1, s // 90))
            pygame.draw.circle(surf, heart, tip, max(1, s // 56))
        pygame.draw.circle(surf, heart, (c, c), s * .05)
        return shrink(surf, size, size)

    def petal(self, size, step):
        """A single falling petal; step picks one of 16 rotations."""
        return self.get(("petal", size, step), self._petal, size, step)

    def _petal(self, size, step):
        s = size * 4
        surf = blank(s, s)
        pts = bezier((s*.5, s*.05), (s*1.0, s*.3), (s*.8, s*.85), (s*.5, s*.95), 14)
        pts += bezier((s*.5, s*.95), (s*.2, s*.85), (s*0, s*.3), (s*.5, s*.05), 14)
        pygame.draw.polygon(surf, (206, 44, 58, 235), pts)
        pygame.draw.polygon(surf, (246, 110, 110, 150), [(x * .7 + s * .15, y * .7 + s * .12) for x, y in pts])
        return pygame.transform.rotozoom(shrink(surf, size, size), step * 22.5, 1)

    # ---------- Butterfly ----------

    FLAP_FRAMES = 10
    TURN_STEPS = 24

    def butterfly(self, size, frame, turn, tint="red"):
        """size in px, frame of the wing beat, turn of TURN_STEPS rotations."""
        key = ("fly", size, frame, turn, tint)
        return self.get(key, self._butterfly, size, frame, turn, tint)

    def _butterfly(self, size, frame, turn, tint):
        if turn == 0:
            return self._butterfly_frame(size, frame, tint)
        level = self.butterfly(size, frame, 0, tint)
        return pygame.transform.rotozoom(level, -turn * 360 / self.TURN_STEPS, 1)

    def _wing(self, size, tint):
        """The right-hand pair of wings, drawn large and hot at the root."""
        return self.get(("wing", size, tint), self._build_wing, size, tint)

    def _build_wing(self, size, tint):
        s = size * 4
        w, h = s // 2, s
        surf = blank(w, h)

        upper = bezier((0, h*.47), (w*.18, h*.16), (w*.62, h*.02), (w*.97, h*.1), 20)
        upper += bezier((w*.97, h*.1), (w*1.02, h*.28), (w*.72, h*.48), (w*.42, h*.52), 20)
        upper += bezier((w*.42, h*.52), (w*.22, h*.54), (w*.08, h*.52), (0, h*.5), 8)

        lower = bezier((0, h*.5), (w*.3, h*.5), (w*.74, h*.52), (w*.78, h*.66), 16)
        lower += bezier((w*.78, h*.66), (w*.78, h*.8), (w*.5, h*.9), (w*.34, h*.92), 16)
        lower += bezier((w*.34, h*.92), (w*.24, h*.8), (w*.08, h*.64), (0, h*.52), 16)

        if tint == "blue":
            layers = (((70, 130, 255), 225), ((130, 190, 255), 225), ((220, 240, 255), 235))
            vein = (20, 40, 110, 150)
        else:
            layers = (((214, 30, 34), 230), ((255, 92, 48), 232), ((255, 196, 128), 238))
            vein = (92, 8, 10, 170)

        for wing in (lower, upper):
            pygame.draw.polygon(surf, rgba(*layers[0]), wing)
            for (col, alpha), k in ((layers[1], .78), (layers[2], .46)):
                pygame.draw.polygon(surf, rgba(col, alpha), [(x * k, h*.5 + (y - h*.5) * k) for x, y in wing])
            pygame.draw.lines(surf, vein, True, wing, max(2, s // 64))

        root = (0, h * .5)
        for tx, ty in ((.9, .11), (.74, .2), (.62, .34), (.46, .44), (.7, .64), (.52, .8), (.34, .88)):
            pygame.draw.line(surf, vein, root, (w * tx, h * ty), max(1, s // 110))
        return surf

    def _butterfly_frame(self, size, frame, tint):
        wing = self._wing(size, tint)
        wh = wing.get_height()
        open_k = .2 + .8 * abs(math.cos(frame * math.pi / self.FLAP_FRAMES))
        ww = max(4, int(wing.get_width() * open_k))
        right = pygame.transform.smoothscale(wing, (ww, wh))
        left = pygame.transform.flip(right, True, False)

        pad = wh // 3
        full = wh + 2 * pad
        c = full // 2
        art = blank(full, full)
        art.blit(right, (c, pad))
        art.blit(left, (c - ww, pad))

        body = (44, 8, 12, 255) if tint == "red" else (10, 20, 60, 255)
        pygame.draw.ellipse(art, body, (c - wh * .018, c - wh * .17, wh * .036, wh * .36))
        for side in (-1, 1):
            tip = (c + side * wh * .13, c - wh * .34)
            pts = bezier((c, c - wh * .16), (c + side * wh * .02, c - wh * .26), (c + side * wh * .09, c - wh * .3), tip, 8)
            pygame.draw.lines(art, body, False, pts, max(1, wh // 160))

        halo = blur(blur(art, 8), 3)
        halo.fill((255, 255, 255, 190), special_flags=MULT)
        out = blank(full, full)
        out.blit(halo, (0, 0))
        out.blit(art, (0, 0))
        return shrink(out, full / 4, full / 4)

    # ---------- Paper talismans ----------

    TALISMAN_MARGIN = 34

    def talisman(self, w, h, main, top="敕令", label=None, hot=False, seal="往"):
        key = ("talisman", w, h, main, top, label, hot, seal)
        return self.get(key, self._talisman, w, h, main, top, label, hot, seal)

    def _talisman(self, w, h, main, top, label, hot, seal):
        rng = random.Random(main + str(w))
        margin = self.TALISMAN_MARGIN
        out = blank(w + 2 * margin, h + 2 * margin)

        paper = v_gradient(w, h, [(0, rgba(theme.PAPER)), (.7, rgba(mix(theme.PAPER, theme.PAPER_DARK, .55))), (1, rgba(theme.PAPER_DARK))])
        grain = speckle(w, h, 226, 255, seed=len(main) * 31 + w)
        paper.blit(grain, (0, 0), special_flags=MULT)

        fibre = scaled(theme.PAPER_DARK, .92)
        for _ in range(int(w * h / 1400)):
            x, y = rng.randrange(w), rng.randrange(h)
            pygame.draw.line(paper, fibre, (x, y), (x + rng.randint(-14, 14), y + rng.randint(-5, 5)))

        edge = self.vignette(w, h, (92, 52, 20), 120, 1.5)
        paper.blit(edge, (0, 0))

        # Ink: a double border, the header decree and the main characters
        red = theme.CINNABAR
        inset = max(6, w // 18)
        pygame.draw.rect(paper, red, (inset, inset, w - 2 * inset, h - 2 * inset), max(2, w // 60))
        pygame.draw.rect(paper, red, (inset + 6, inset + 6, w - 2 * inset - 12, h - 2 * inset - 12), 1)

        y = inset + max(10, h // 40)
        if top:
            head = self.brush(max(18, w * .17))
            surf = head.render(top, True, red)
            paper.blit(surf, surf.get_rect(midtop=(w // 2, y)))
            y += surf.get_height() + max(2, h // 90)

        bottom = h - inset - 12
        if label:
            bottom -= int(h * .1)

        # Sweeping brush strokes either side of the characters, as on a real fu
        for side in (-1, 1):
            cx = w / 2 + side * w * .3
            pts = [(cx + side * math.sin(t * .22) * w * .045, y + (bottom - y) * t / 40) for t in range(41)]
            pygame.draw.aalines(paper, red, False, pts)

        chars = [c for c in main]
        cell = min(w * .62, (bottom - y) / max(1, len(chars)))
        big = self.brush(cell * .96)
        for i, ch in enumerate(chars):
            surf = big.render(ch, True, red)
            paper.blit(surf, surf.get_rect(center=(w // 2, y + cell * (i + .5))))

        if seal and not label:
            sz = max(26, w // 4)
            stamp = pygame.Surface((sz, sz), SRCALPHA)
            pygame.draw.rect(stamp, rgba(theme.CRIMSON, 230), stamp.get_rect(), border_radius=max(2, sz // 10))
            mark = self.brush(sz * .78).render(seal, True, theme.PAPER)
            stamp.blit(mark, mark.get_rect(center=(sz / 2, sz / 2)))
            paper.blit(stamp, (w - inset - sz - 8, h - inset - sz - 8))

        if label:
            plate_h = int(h * .1)
            plate = pygame.Rect(inset + 8, h - inset - 8 - plate_h, w - 2 * inset - 16, plate_h)
            pygame.draw.rect(paper, rgba(theme.CINNABAR), plate)
            pygame.draw.rect(paper, rgba(theme.GOLD), plate, 2)
            font = self.ui(min(plate_h * .62, (w - 2 * inset - 26) / max(1, len(label)) * 1.9))
            surf = font.render(label, True, theme.GOLD_BRIGHT)
            paper.blit(surf, surf.get_rect(center=plate.center))

        # A torn, slightly burnt bottom edge
        mask = blank(w, h)
        pts = [(0, 0), (w, 0), (w, h - 8)]
        steps = max(6, w // 16)
        for i in range(1, steps):
            pts.append((w - i * w / steps, h - rng.randint(0, 14)))
        pts.append((0, h - 6))
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        paper.blit(mask, (0, 0), special_flags=CUT)

        shadow = blank(w + 2 * margin, h + 2 * margin)
        shadow.blit(paper, (margin + 7, margin + 12))
        shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MIN)
        shadow.fill((255, 255, 255, 130), special_flags=MULT)
        out.blit(blur(shadow, 6), (0, 0))

        if hot:
            halo = blank(w + 2 * margin, h + 2 * margin)
            pygame.draw.rect(halo, rgba(theme.EMBER, 255), (margin - 4, margin - 4, w + 8, h + 8), border_radius=8)
            out.blit(blur(blur(halo, 6), 3), (0, 0))

        out.blit(paper, (margin, margin))
        return out

    def turned(self, name, sprite, step, unit):
        """Cached rotation of a hanging sprite, so it can sway cheaply."""
        return self.get(("turned", name, step), lambda: pygame.transform.rotozoom(sprite, step * unit, 1))

    # ---------- Lantern ----------

    def lantern(self, w):
        return self.get(("lantern", w), self._lantern, w)

    def _lantern(self, w):
        s = w * 3
        h = int(s * 1.95)
        surf = blank(s, h)
        cx = s / 2
        top, bh = s * .2, s * .9
        body = pygame.Rect(s * .04, top, s * .92, bh)

        shade = h_gradient(body.w, body.h, [(0, (112, 10, 16, 255)), (.3, (224, 42, 36, 255)), (.5, (255, 118, 58, 255)),
                                            (.7, (224, 42, 36, 255)), (1, (112, 10, 16, 255))])
        mask = blank(body.w, body.h)
        pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
        shade.blit(mask, (0, 0), special_flags=CUT)
        surf.blit(shade, body.topleft)

        for k in (-.78, -.52, -.26, 0, .26, .52, .78):
            pts = []
            for i in range(25):
                a = -math.pi / 2 + math.pi * i / 24
                pts.append((cx + math.cos(a) * k * body.w / 2, body.centery + math.sin(a) * body.h / 2))
            pygame.draw.lines(surf, (88, 8, 12, 190), False, pts, 3)

        gold = theme.GOLD
        for y in (top - s * .02, top + bh - s * .13):
            cap = pygame.Rect(cx - s * .26, y, s * .52, s * .15)
            pygame.draw.rect(surf, scaled(gold, .7), cap, border_radius=8)
            pygame.draw.rect(surf, theme.GOLD_BRIGHT, cap.inflate(-8, -cap.h * .55), border_radius=6)

        pygame.draw.line(surf, theme.CINNABAR, (cx, 0), (cx, top), 6)

        tassel_top = top + bh + s * .02
        pygame.draw.circle(surf, gold, (cx, tassel_top + s * .03), s * .05)
        for i in range(-9, 10):
            x = cx + i * s * .018
            length = s * (.42 - abs(i) * .006)
            pygame.draw.line(surf, (206, 34, 34) if i % 2 else (246, 92, 56), (x, tassel_top + s * .06),
                             (x + i * .5, tassel_top + s * .06 + length), 4)
        pygame.draw.rect(surf, gold, (cx - s * .11, tassel_top + s * .07, s * .22, s * .05), border_radius=4)
        return shrink(surf, w, h / 3)

    # ---------- Boo Tao ----------

    def ghost(self, w):
        return self.get(("ghost", w), self._ghost, w)

    def _ghost(self, w):
        s = w * 4
        h = int(s * 1.1)
        out = blank(s, h)
        U = lambda x, y: (x * s, y * h)

        body = bezier(U(.5, .05), U(.82, .05), U(.95, .32), U(.92, .55))
        body += bezier(U(.92, .55), U(.9, .76), U(.8, .86), U(.66, .9))
        body += bezier(U(.66, .9), U(.52, .96), U(.34, 1.0), U(.12, .95))
        body += bezier(U(.12, .95), U(.3, .88), U(.28, .8), U(.2, .68))
        body += bezier(U(.2, .68), U(.1, .5), U(.16, .05), U(.5, .05))

        shape = blank(s, h)
        pygame.draw.polygon(shape, (255, 255, 255, 255), body)
        pygame.draw.circle(shape, (255, 255, 255, 255), U(.13, .5), s * .05)
        pygame.draw.circle(shape, (255, 255, 255, 255), U(.95, .5), s * .05)

        fill = v_gradient(s, h, [(0, (255, 255, 255, 255)), (.6, (240, 244, 255, 255)), (1, (190, 204, 240, 255))])
        fill.blit(shape, (0, 0), special_flags=CUT)

        halo = blank(s, h)
        halo.blit(shape, (0, 0))
        halo.fill((255, 150, 120, 255), special_flags=pygame.BLEND_RGB_MIN)
        out.blit(blur(blur(halo, 8), 3), (0, 0))
        out.blit(fill, (0, 0))

        red = (214, 44, 44)
        for (x, y, tilt) in ((.37, .35, 18), (.67, .33, -18)):
            eye = blank(s * .16, s * .09)
            pygame.draw.ellipse(eye, red, eye.get_rect())
            eye = pygame.transform.rotate(eye, tilt)
            out.blit(eye, eye.get_rect(center=U(x, y)))

        mouth = [(s * .4, h * .46), (s * .64, h * .45), (s * .6, h * .55), (s * .52, h * .6), (s * .44, h * .55)]
        pygame.draw.polygon(out, red, mouth)
        pygame.draw.circle(out, (250, 150, 150), U(.3, .47), s * .045)
        pygame.draw.circle(out, (250, 150, 150), U(.76, .45), s * .045)
        return shrink(out, w, h / 4)

    # ---------- Spinning seal ----------

    def sigil(self, size):
        return self.get(("sigil", size), self._sigil, size)

    def faint_sigil(self, size, alpha):
        return self.get(("faint_sigil", size, alpha), self._faint_sigil, size, alpha)

    def _faint_sigil(self, size, alpha):
        ring = self.sigil(size).copy()
        ring.fill((255, 255, 255, alpha), special_flags=MULT)
        return ring

    def _sigil(self, size):
        s = size * 2
        c = s / 2
        surf = blank(s, s)
        gold = rgba(theme.GOLD, 255)
        for k, width in ((.495, 5), (.47, 2), (.33, 3), (.31, 1), (.16, 2)):
            pygame.draw.circle(surf, gold, (c, c), s * k, width)

        for i in range(72):
            a = i * math.tau / 72
            r0, r1 = (.45, .47) if i % 9 else (.43, .47)
            pygame.draw.line(surf, gold, (c + math.cos(a) * s * r0, c + math.sin(a) * s * r0),
                             (c + math.cos(a) * s * r1, c + math.sin(a) * s * r1), 2)

        # Eight trigrams around the ring
        for i, bars in enumerate(("111", "011", "101", "001", "110", "010", "100", "000")):
            a = i * math.tau / 8 + math.tau / 16
            piece = blank(s * .12, s * .09)
            pw, ph = piece.get_size()
            for row, bit in enumerate(bars):
                y = row * ph / 3 + 2
                bh = ph / 4.4
                if bit == "1":
                    pygame.draw.rect(piece, gold, (0, y, pw, bh))
                else:
                    pygame.draw.rect(piece, gold, (0, y, pw * .42, bh))
                    pygame.draw.rect(piece, gold, (pw * .58, y, pw * .42, bh))
            turned = pygame.transform.rotozoom(piece, -math.degrees(a) - 90, 1)
            surf.blit(turned, turned.get_rect(center=(c + math.cos(a) * s * .395, c + math.sin(a) * s * .395)))

        # Five-point plum star and petals at the heart
        pts = [(c + math.cos(-math.pi / 2 + i * 2 * math.tau / 5) * s * .3,
                c + math.sin(-math.pi / 2 + i * 2 * math.tau / 5) * s * .3) for i in range(5)]
        pygame.draw.polygon(surf, gold, pts, 2)
        for i in range(5):
            a = -math.pi / 2 + i * math.tau / 5
            pygame.draw.circle(surf, gold, (c + math.cos(a) * s * .23, c + math.sin(a) * s * .23), s * .065, 2)
        return shrink(surf, size, size)

    # ---------- Mist ----------

    def mist(self, w, h, tint, seed):
        return self.get(("mist", w, h, tint, seed), self._mist, w, h, tint, seed)

    def _mist(self, w, h, tint, seed):
        rng = random.Random(seed)
        sw, sh = 256, 64
        small = blank(sw, sh)
        for _ in range(90):
            x, y = rng.randrange(sw), int(sh * .4 + rng.random() * sh * .7)
            r = rng.randint(6, 22)
            blob = blank(2 * r, 2 * r)
            pygame.draw.circle(blob, rgba(tint, rng.randint(6, 26)), (r, r), r)
            for ox in (-sw, 0, sw):
                small.blit(blob, (x - r + ox, y - r))
        surf = pygame.transform.smoothscale(small, (w, h))
        return blur(surf, 4)

    def side_shade(self):
        """Darkens the left of the title screen so the menu reads over any artwork."""
        return self.get("side_shade", h_gradient, 980, 1080,
                        [(0, (12, 3, 5, 214)), (.55, (12, 3, 5, 150)), (1, (12, 3, 5, 0))])

    def watermark(self, text, size, alpha):
        return self.get(("watermark", text, size, alpha), self._watermark, text, size, alpha)

    def _watermark(self, text, size, alpha):
        surf = self.brush(size).render(text, True, theme.GOLD)
        surf.fill((255, 255, 255, alpha), special_flags=MULT)
        return surf

    # ---------- Lacquered panels and buttons ----------

    BUTTON_MARGIN = 22
    PANEL_MARGIN = 30
    PLAQUE_MARGIN = 24

    def shadowed(self, w, h, step, margin, depth=10, alpha=170):
        shadow = blank(w + 2 * margin, h + 2 * margin)
        pygame.draw.polygon(shadow, (0, 0, 0, alpha), stepped_rect(margin, margin + depth, w, h, step))
        return blur(blur(shadow, 6), 3)

    def panel(self, w, h, step=14):
        return self.get(("panel", w, h, step), self._panel, w, h, step)

    def board(self, w, h, mark=None):
        """A panel with its faint character baked in, cut into pieces (see split).  The lacquer
        is all but opaque, and an opaque blit costs a third of a blended one."""
        key = ("board", w, h, mark)
        pieces = self.cache.get(key)
        if pieces is None:
            surf = self.panel(w, h).copy()
            if mark:
                m = self.PANEL_MARGIN
                sprite = self.watermark(mark, min(400, int(h * .8)), 26)
                surf.blit(sprite, sprite.get_rect(center=(m + w // 2, m + h // 2)))
            pieces = self.cache[key] = [(self.fast(piece), offset)
                                        for piece, offset in split(surf, self.PANEL_MARGIN + 3 * 14)]
        return pieces

    def _panel(self, w, h, step):
        margin = self.PANEL_MARGIN
        out = self.shadowed(w, h, step, margin, 14, 190)

        body = v_gradient(w, h, [(0, rgba(theme.LACQUER_TOP, 240)), (.45, rgba(theme.LACQUER_MID, 240)), (1, rgba(theme.LACQUER_BOTTOM, 246))])
        body.blit(speckle(w, h, 232, 255, seed=w), (0, 0), special_flags=MULT)

        sheen = blank(w, h)
        sheen.blit(pygame.transform.smoothscale(radial(64, (150, 50, 40, 34), (150, 50, 40, 0), 1.3), (int(w * 1.3), int(h * 1.5))), (-w * .15, -h * .95))
        body.blit(sheen, (0, 0))

        band_y = step * 2 + 12
        band = meander_band(w - 8 * step, rgba(theme.GOLD_DARK, 120))
        body.blit(band, (4 * step, band_y - 8))
        body.blit(pygame.transform.flip(band, False, True), (4 * step, h - band_y - 14))

        mask = blank(w, h)
        pts = stepped_rect(0, 0, w, h, step)
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        body.blit(mask, (0, 0), special_flags=CUT)

        pygame.draw.lines(body, theme.GOLD_DARK, True, pts, 6)
        pygame.draw.lines(body, theme.GOLD, True, pts, 3)
        inner = stepped_rect(9, 9, w - 18, h - 18, step - 2)
        pygame.draw.lines(body, rgba(theme.GOLD_DARK, 190), True, inner, 1)

        flower = self.blossom(34, (196, 150, 74), theme.GOLD_BRIGHT)
        for x, y in ((14, 14), (w - 48, 14), (14, h - 48), (w - 48, h - 48)):
            body.blit(flower, (x, y))

        out.blit(body, (margin, margin))
        return out

    def plaque(self, w, h):
        """Title board that sits across the top of a panel."""
        return self.get(("plaque", w, h), self._plaque, w, h)

    def _plaque(self, w, h):
        margin = self.PLAQUE_MARGIN
        step = 10
        out = self.shadowed(w, h, step, margin, 8, 200)
        face = v_gradient(w, h, [(0, (196, 42, 42, 255)), (.5, (140, 22, 28, 255)), (1, (84, 12, 18, 255))])
        face.blit(speckle(w, h, 226, 255, seed=h), (0, 0), special_flags=MULT)

        mask = blank(w, h)
        pts = stepped_rect(0, 0, w, h, step)
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        face.blit(mask, (0, 0), special_flags=CUT)

        pygame.draw.lines(face, theme.GOLD_DARK, True, pts, 6)
        pygame.draw.lines(face, theme.GOLD_BRIGHT, True, pts, 2)
        pygame.draw.lines(face, rgba(theme.GOLD, 200), True, stepped_rect(9, 9, w - 18, h - 18, step - 2), 1)

        flower = self.blossom(38, theme.GOLD, (120, 20, 20))
        for x in (16, w - 54):
            face.blit(flower, (x, h / 2 - 19))
        out.blit(face, (margin, margin))
        return out

    def button(self, w, h, finish="crimson", hover=False, down=False):
        return self.get(("button", w, h, finish, hover, down), self._button, w, h, finish, hover, down)

    def _button(self, w, h, finish, hover, down):
        margin = self.BUTTON_MARGIN
        step = max(3, min(7, h // 9))
        lip = 2 if down else 7
        top, bottom, lip_col, _ = theme.LACQUER[finish]
        if hover:
            top, bottom = scaled(top, 1.24), scaled(bottom, 1.28)

        out = self.shadowed(w, h, step, margin, 3 if down else 8, 150)

        if hover:
            halo = blank(w + 2 * margin, h + 2 * margin)
            pygame.draw.polygon(halo, rgba(theme.EMBER), stepped_rect(margin - 3, margin - 3, w + 6, h + 6, step))
            out.blit(blur(blur(halo, 5), 2), (0, 0))

        face_h = h - lip
        art = blank(w, h)
        pygame.draw.polygon(art, lip_col, stepped_rect(0, 0, w, h, step))

        face = v_gradient(w, face_h, [(0, rgba(scaled(top, 1.15))), (.12, rgba(top)), (1, rgba(bottom))])
        face.blit(speckle(w, face_h, 236, 255, seed=w + h), (0, 0), special_flags=MULT)
        mask = blank(w, face_h)
        pts = stepped_rect(0, 0, w, face_h, step)
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        face.blit(mask, (0, 0), special_flags=CUT)

        gilt = theme.GOLD_BRIGHT if hover else theme.GOLD
        pygame.draw.lines(face, theme.GOLD_DARK, True, pts, 3)
        pygame.draw.lines(face, gilt, True, stepped_rect(1, 1, w - 2, face_h - 2, step), 1)
        pygame.draw.line(face, rgba(scaled(top, 1.5), 170), (step * 2 + 3, 4), (w - step * 2 - 3, 4))

        art.blit(face, (0, 0))
        out.blit(art, (margin, margin))
        return out

    def seal(self, size, on, glyph=None, hot=False):
        return self.get(("seal", size, on, glyph, hot), self._seal, size, on, glyph, hot)

    def _seal(self, size, on, glyph, hot):
        out = blank(size + 8, size + 8)
        fill = (214, 122, 26) if hot else (196, 34, 34) if on else (72, 58, 54)
        ink = theme.PAPER if on else (150, 134, 120)
        pygame.draw.rect(out, rgba((0, 0, 0), 120), (5, 6, size, size), border_radius=max(3, size // 8))
        pygame.draw.rect(out, fill, (2, 2, size, size), border_radius=max(3, size // 8))
        pygame.draw.rect(out, ink, (5, 5, size - 6, size - 6), 1, border_radius=max(2, size // 10))
        mark = self.brush(size * .74).render(glyph or ("开" if on else "关"), True, ink)
        out.blit(mark, mark.get_rect(center=(2 + size / 2, 2 + size / 2)))
        return out

    def chevron(self, size, left, hover):
        return self.get(("chevron", size, left, hover), self._chevron, size, left, hover)

    def _chevron(self, size, left, hover):
        s = size * 3
        c = s / 2
        surf = blank(s, s)
        top, bottom, lip, _ = theme.LACQUER["crimson" if hover else "ink"]
        diamond = [(c, s * .03), (s * .97, c), (c, s * .97), (s * .03, c)]
        pygame.draw.polygon(surf, lip, [(x, y + s * .03) for x, y in diamond])
        fill = v_gradient(s, s, [(0, rgba(scaled(top, 1.2))), (1, rgba(bottom))])
        mask = blank(s, s)
        pygame.draw.polygon(mask, (255, 255, 255, 255), diamond)
        fill.blit(mask, (0, 0), special_flags=CUT)
        surf.blit(fill, (0, 0))
        pygame.draw.polygon(surf, theme.GOLD_BRIGHT if hover else theme.GOLD, diamond, 5)
        k = -1 if left else 1
        pts = [(c - k * s * .1, c - s * .2), (c + k * s * .14, c), (c - k * s * .1, c + s * .2)]
        pygame.draw.lines(surf, theme.GOLD_BRIGHT, False, pts, 9)
        return shrink(surf, size, size)

    def inset(self, w, h):
        """Dark sunken plate that values sit on."""
        return self.get(("inset", w, h), self._inset, w, h)

    def _inset(self, w, h):
        surf = blank(w, h)
        face = v_gradient(w, h, [(0, (8, 3, 4, 235)), (.25, (20, 8, 9, 225)), (1, (34, 14, 14, 220))])
        mask = blank(w, h)
        pts = stepped_rect(0, 0, w, h, 4)
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        face.blit(mask, (0, 0), special_flags=CUT)
        surf.blit(face, (0, 0))
        pygame.draw.lines(surf, rgba(theme.GOLD_DARK, 220), True, pts, 2)
        return surf

    def slider_track(self, w, h):
        return self.get(("track", w, h), self.inset, w, h)

    def slider_fill(self, w, h, accent):
        return self.get(("fill", w, h, accent), self._slider_fill, w, h, accent)

    def _slider_fill(self, w, h, accent):
        return h_gradient(w, h, [(0, rgba(scaled(accent, .45))), (.7, rgba(accent)), (1, rgba(mix(accent, (255, 236, 190), .55)))])

    # ---------- Frame for pictures ----------

    def frame(self, w, h, hover):
        return self.get(("frame", w, h, hover), self._frame, w, h, hover)

    def _frame(self, w, h, hover):
        margin = 20
        out = blank(w + 2 * margin, h + 2 * margin)
        shadow = blank(w + 2 * margin, h + 2 * margin)
        pygame.draw.rect(shadow, (0, 0, 0, 180), (margin, margin + 7, w, h))
        out.blit(blur(shadow, 5), (0, 0))
        if hover:
            halo = blank(w + 2 * margin, h + 2 * margin)
            pygame.draw.rect(halo, rgba(theme.EMBER), (margin - 3, margin - 3, w + 6, h + 6))
            out.blit(blur(blur(halo, 5), 2), (0, 0))
        rim = theme.GOLD_BRIGHT if hover else theme.GOLD
        pygame.draw.rect(out, theme.GOLD_DARK, (margin - 5, margin - 5, w + 10, h + 10), 3)
        pygame.draw.rect(out, rim, (margin - 3, margin - 3, w + 6, h + 6), 2)
        return out

    # ---------- Arena ----------

    def rail(self, w, flowers=True):
        return self.get(("rail", w, flowers), self._rail, w, flowers)

    def _rail(self, w, flowers):
        h = 14
        surf = blank(w + 44, h + 30)
        rod = v_gradient(w, h, [(0, rgba(theme.GOLD_DARK)), (.35, rgba(theme.GOLD_BRIGHT)), (1, rgba(scaled(theme.GOLD_DARK, .6)))])
        surf.blit(rod, (22, 15))
        if flowers:
            flower = self.blossom(44, theme.GOLD, (120, 20, 20))
            surf.blit(flower, (0, 0))
            surf.blit(flower, (w, 0))
        return surf

    def cord(self, h, faint=False):
        if faint:   # the Middle Wall is off: the net is only a marking
            return self.get(("cord_faint", h), self._faint, self.cord(h), 80)
        return self.get(("cord", h), self._cord, h)

    def _faint(self, sprite, alpha):
        surf = sprite.copy()
        surf.fill((255, 255, 255, alpha), special_flags=MULT)
        return surf

    def _cord(self, h):
        """The net: a red cord with knots and gold beads, tiled down the screen."""
        surf = blank(30, h)
        pygame.draw.line(surf, (150, 22, 26), (15, 0), (15, h), 3)
        pygame.draw.line(surf, (226, 70, 56), (14, 0), (14, h), 1)
        for y in range(40, h, 92):
            pygame.draw.circle(surf, theme.GOLD, (15, y), 6)
            pygame.draw.circle(surf, theme.GOLD_BRIGHT, (14, y - 1), 3)
            pygame.draw.polygon(surf, (178, 28, 36), [(15, y + 12), (25, y + 24), (15, y + 36), (5, y + 24)])
            pygame.draw.polygon(surf, (250, 120, 90), [(15, y + 17), (20, y + 24), (15, y + 31), (10, y + 24)], 1)
        return surf

    def goal_glow(self, side, tint, level):
        return self.get(("goal", side, tint, level), self._goal_glow, side, tint, level)

    def _goal_glow(self, side, tint, level):
        hot, dark = rgba(scaled(tint, level / 6)), (0, 0, 0, 255)
        ends = (hot, dark) if side == "left" else (dark, hot)
        strip = pygame.Surface((120, 1080))
        strip.blit(h_gradient(120, 1080, [(0, ends[0]), (1, ends[1])]), (0, 0))
        return strip

    def paddle_glow(self, w, h, finish):
        return self.get(("paddle_glow", w, h, finish), self._paddle_glow, w, h, finish)

    PADDLE_GLOWS = {"red": (140, 42, 22), "blue": (30, 74, 170), "gold": (150, 108, 26),
                    "violet": (104, 40, 170), "jade": (28, 134, 84), "ice": (96, 160, 214)}

    def _paddle_glow(self, w, h, finish):
        pad = 44
        tint = self.PADDLE_GLOWS[finish]
        surf = pygame.Surface((w + 2 * pad, h + 2 * pad))
        pygame.draw.rect(surf, tint, (pad - 6, pad - 6, w + 12, h + 12), border_radius=14)
        return blur(blur(surf, 8), 3)

    def charm(self, size, glyph, tint):
        """A round talisman coin for a power-up: its character inked on a glowing disc."""
        return self.get(("charm", size, glyph, tint), self._charm, size, glyph, tint)

    def _charm(self, size, glyph, tint):
        s = size * 2
        c = s / 2
        surf = blank(s, s)
        pygame.draw.circle(surf, rgba(mix(tint, (0, 0, 0), .78), 238), (c, c), s * .47)
        pygame.draw.circle(surf, rgba(tint, 255), (c, c), s * .47, max(2, s // 16))
        pygame.draw.circle(surf, rgba(theme.GOLD, 190), (c, c), s * .37, max(1, s // 44))
        mark = self.brush(s * .52).render(glyph, True, mix(tint, (255, 255, 255), .6))
        surf.blit(mark, mark.get_rect(center=(c, c + s * .02)))
        return shrink(surf, size, size)

    # ---------- Game pieces ----------

    def paddle(self, w, h, finish):
        return self.get(("paddle", w, h, finish), self._paddle, w, h, finish)

    def _paddle(self, w, h, finish):
        """A lacquered staff that exactly fills the paddle's collision rect."""
        s = 3
        W, H = w * s, h * s
        if finish == "red":
            stops = [(0, (92, 8, 14, 255)), (.3, (214, 38, 40, 255)), (.48, (255, 136, 96, 255)),
                     (.66, (196, 28, 34, 255)), (1, (72, 6, 12, 255))]
            trim, inlay = theme.GOLD, theme.GOLD_BRIGHT
        else:
            stops = [(0, (12, 28, 84, 255)), (.3, (44, 104, 214, 255)), (.48, (150, 208, 255, 255)),
                     (.66, (36, 90, 196, 255)), (1, (10, 22, 72, 255))]
            trim, inlay = (178, 200, 226), (236, 246, 255)

        body = h_gradient(W, H, stops)
        mask = blank(W, H)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=int(W * .32))
        body.blit(mask, (0, 0), special_flags=CUT)

        cap = max(s * 8, int(W * .62))
        for y in (0, H - cap):
            band = h_gradient(W, cap, [(0, rgba(scaled(trim, .45))), (.45, rgba(inlay)), (1, rgba(scaled(trim, .4)))])
            cut = blank(W, cap)
            pygame.draw.rect(cut, (255, 255, 255, 255), cut.get_rect(), border_radius=int(W * .32))
            band.blit(cut, (0, 0), special_flags=CUT)
            body.blit(band, (0, y))

        for y in (cap + s * 3, H - cap - s * 3 - s, H // 2 - int(W * .34), H // 2 + int(W * .34)):
            pygame.draw.rect(body, trim, (W * .06, y, W * .88, s))

        cy = H // 2
        d = W * .3
        pygame.draw.polygon(body, inlay, [(W / 2, cy - d), (W / 2 + d, cy), (W / 2, cy + d), (W / 2 - d, cy)])
        d *= .55
        pygame.draw.polygon(body, scaled(trim, .5), [(W / 2, cy - d), (W / 2 + d, cy), (W / 2, cy + d), (W / 2 - d, cy)])
        pygame.draw.rect(body, (10, 4, 4, 255), body.get_rect(), s, border_radius=int(W * .32))
        return shrink(body, w, h)

    def paddle_flash(self, w, h, finish, level):
        """The paddle lit up after a hit; level runs from 1 to 4."""
        return self.get(("paddle_flash", w, h, finish, level), self._paddle_flash, w, h, finish, level)

    def _paddle_flash(self, w, h, finish, level):
        lit = self.paddle(w, h, finish).copy()
        lift = level * 36
        lit.fill((lift, lift, lift, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return lit

    def ball(self, d):
        return self.get(("ball", d), self._ball, d)

    def _ball(self, d):
        """Boo Tao curled into a ball: pale spirit, flame-red face."""
        s = d * 4
        c = s / 2
        surf = blank(s, s)
        pygame.draw.circle(surf, (120, 14, 18), (c, c), c)
        # The shading is scaled from one master, as every ball size needs it
        shade = self.get(("ball_shade",), radial, 48, (255, 255, 255, 255), (226, 214, 214, 255), 2.2)
        fill = pygame.transform.smoothscale(shade, (s, s))
        mask = blank(s, s)
        pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), c * .93)
        fill.blit(mask, (0, 0), special_flags=CUT)
        surf.blit(fill, (0, 0))

        red = (204, 34, 36)
        for x, tilt in ((.34, 16), (.66, -16)):
            eye = blank(s * .2, s * .12)
            pygame.draw.ellipse(eye, red, eye.get_rect())
            eye = pygame.transform.rotate(eye, tilt)
            surf.blit(eye, eye.get_rect(center=(s * x, s * .4)))
        pygame.draw.polygon(surf, red, [(s * .38, s * .56), (s * .62, s * .56), (s * .57, s * .68), (s * .5, s * .72), (s * .43, s * .68)])
        return shrink(surf, d, d)

    # ---------- Power-up icons ----------
    # Each power-up has a picture of its own, on a badge whose shape says what kind it is:
    # boons are round, curses are diamonds, the wild ones hexagons.

    FAMILY_TINTS = {"Boon": (240, 176, 64), "Curse": (178, 96, 255), "Wild": (90, 220, 150)}

    def power_icon(self, size, key, family):
        return self.get(("power_icon", size, key, family), self._power_icon, size, key, family)

    def _power_icon(self, size, key, family):
        s = size * 4
        c = s / 2
        tint = self.FAMILY_TINTS[family]
        surf = blank(s, s)

        def badge(r):
            if family == "Boon":
                return [(c + r * math.cos(a / 40 * math.tau), c + r * math.sin(a / 40 * math.tau)) for a in range(40)]
            if family == "Curse":
                return [(c, c - r * 1.06), (c + r * 1.06, c), (c, c + r * 1.06), (c - r * 1.06, c)]
            return [(c + r * math.cos(math.radians(a)), c + r * math.sin(math.radians(a))) for a in range(0, 360, 60)]

        R = s * .47 if family != "Curse" else s * .45
        pygame.draw.polygon(surf, rgba((0, 0, 0), 150), [(x + s * .015, y + s * .03) for x, y in badge(R)])
        pygame.draw.polygon(surf, rgba(mix(tint, (0, 0, 0), .74), 245), badge(R))
        pygame.draw.polygon(surf, rgba(tint), badge(R), max(3, s // 15))
        pygame.draw.polygon(surf, rgba(theme.GOLD, 170), badge(R * .8), max(1, s // 60))

        u = s * (.27 if family != "Curse" else .24)      # the picture's half-size
        P = lambda x, y: (c + x * u, c + y * u)
        pale = mix(tint, (255, 255, 255), .78)
        line = max(2, int(s * .045))
        getattr(self, "_icon_" + key)(surf, P, u, pale, line)
        return shrink(surf, size, size)

    @staticmethod
    def _arrow(surf, colour, P, tip, back, width):
        """A straight arrow from `back` to `tip`, in picture units."""
        (tx, ty), (bx, by) = tip, back
        dx, dy = tx - bx, ty - by
        n = math.hypot(dx, dy) or 1
        dx, dy = dx / n, dy / n
        head = .42
        pygame.draw.line(surf, colour, P(bx, by), P(tx - dx * head * .6, ty - dy * head * .6), width)
        left = (tx - dx * head - dy * head * .7, ty - dy * head + dx * head * .7)
        right = (tx - dx * head + dy * head * .7, ty - dy * head - dx * head * .7)
        pygame.draw.polygon(surf, colour, [P(tx + dx * .08, ty + dy * .08), P(*left), P(*right)])

    def _icon_teleport(self, surf, P, u, pale, line):
        # a shield with a spark of light in it: one save
        shield = [P(-.8, -.85), P(.8, -.85), P(.8, -.1), P(.45, .55), P(0, .95), P(-.45, .55), P(-.8, -.1)]
        pygame.draw.polygon(surf, (250, 210, 120), shield)
        pygame.draw.polygon(surf, (120, 70, 20), shield, line)
        star = [P(0, -.55), P(.14, -.12), P(.55, 0), P(.14, .12), P(0, .55), P(-.14, .12), P(-.55, 0), P(-.14, -.12)]
        pygame.draw.polygon(surf, (255, 255, 240), star)

    def _icon_giant(self, surf, P, u, pale, line):
        pygame.draw.rect(surf, (236, 90, 70), (*P(-.24, -.5), .48 * u, 1.0 * u), border_radius=int(.15 * u))
        for sign in (-1, 1):
            self._arrow(surf, pale, P, (0, sign * 1.05), (0, sign * .55), line)

    def _icon_swift(self, surf, P, u, pale, line):
        bolt = [P(.2, -1.0), P(-.55, .12), P(-.05, .12), P(-.25, 1.0), P(.6, -.2), P(.08, -.2), P(.35, -1.0)]
        pygame.draw.polygon(surf, (255, 226, 90), bolt)
        pygame.draw.polygon(surf, (150, 96, 10), bolt, max(1, line // 2))

    def _icon_fire(self, surf, P, u, pale, line):
        outer = bezier(P(0, -1.05), P(.35, -.5), P(.95, -.1), P(.6, .6)) + \
                bezier(P(.6, .6), P(.35, 1.05), P(-.35, 1.05), P(-.6, .6)) + \
                bezier(P(-.6, .6), P(-.95, -.1), P(-.2, -.3), P(0, -1.05))
        pygame.draw.polygon(surf, (255, 110, 30), outer)
        inner = bezier(P(0, -.35), P(.2, 0), P(.5, .25), P(.3, .62)) + \
                bezier(P(.3, .62), P(.15, .85), P(-.15, .85), P(-.3, .62)) + \
                bezier(P(-.3, .62), P(-.5, .25), P(-.1, .1), P(0, -.35))
        pygame.draw.polygon(surf, (255, 222, 110), inner)

    def _icon_frost(self, surf, P, u, pale, line):
        ice = (190, 236, 255)
        for a in range(0, 180, 60):
            dx, dy = math.cos(math.radians(a + 90)), math.sin(math.radians(a + 90))
            pygame.draw.line(surf, ice, P(-dx, -dy), P(dx, dy), line)
            for sign in (-1, 1):
                bx, by = sign * dx * .6, sign * dy * .6
                for turn in (-1, 1):
                    ang = math.atan2(sign * dy, sign * dx) + turn * 2.4
                    pygame.draw.line(surf, ice, P(bx, by), P(bx + math.cos(ang) * .35, by + math.sin(ang) * .35),
                                     max(1, line * 3 // 4))
        pygame.draw.circle(surf, (255, 255, 255), P(0, 0), u * .14)

    def _icon_shrink(self, surf, P, u, pale, line):
        pygame.draw.rect(surf, (150, 120, 220), (*P(-.24, -.26), .48 * u, .52 * u), border_radius=int(.12 * u))
        for sign in (-1, 1):
            self._arrow(surf, pale, P, (0, sign * .36), (0, sign * 1.05), line)

    def _icon_hex(self, surf, P, u, pale, line):
        # a jiangshi's paper talisman, slapped on askew
        strip = blank(u * .9, u * 2.0)
        w, h = strip.get_size()
        pygame.draw.rect(strip, (248, 214, 96), strip.get_rect(), border_radius=max(2, int(u * .06)))
        pygame.draw.rect(strip, (150, 30, 24), strip.get_rect(), max(2, line // 2), border_radius=max(2, int(u * .06)))
        red = (196, 30, 28)
        pts = [(w * .5, h * .12), (w * .25, h * .3), (w * .72, h * .45), (w * .28, h * .62), (w * .7, h * .78), (w * .5, h * .9)]
        pygame.draw.lines(strip, red, False, pts, max(2, line * 3 // 4))
        pygame.draw.circle(strip, red, (w * .5, h * .12), w * .1)
        strip = pygame.transform.rotate(strip, -16)
        surf.blit(strip, strip.get_rect(center=P(0, 0)))

    def _icon_ghost(self, surf, P, u, pale, line):
        sprite = self.ghost(int(u * 1.9))
        surf.blit(sprite, sprite.get_rect(center=P(0, .05)))

    def _icon_sticky(self, surf, P, u, pale, line):
        goo = (196, 222, 70)
        dark = (96, 120, 20)
        blob = bezier(P(-.85, -.2), P(-.85, -.95), P(.85, -.95), P(.85, -.2))
        drips = [P(.85, -.2), P(.6, .15), P(.55, .7), P(.4, .72), P(.35, .1), P(.05, 0),
                 P(0, .95), P(-.2, .97), P(-.25, .05), P(-.5, .1), P(-.55, .45), P(-.72, .45), P(-.85, -.2)]
        pygame.draw.polygon(surf, goo, blob + drips)
        pygame.draw.polygon(surf, dark, blob + drips, max(1, line // 2))
        for x, y in ((.475, .72), (-.1, .97), (-.635, .45)):
            pygame.draw.circle(surf, goo, P(x, y), u * .1)
        pygame.draw.circle(surf, (240, 255, 200), P(-.35, -.5), u * .12)

    def _icon_gravity(self, surf, P, u, pale, line):
        pygame.draw.line(surf, pale, P(-.95, .92), P(.95, .92), line)
        pygame.draw.circle(surf, (120, 236, 170), P(0, .55), u * .3)
        self._arrow(surf, pale, P, (0, .1), (0, -1.0), line + 1)

    def _icon_wall(self, surf, P, u, pale, line):
        stone = (196, 176, 150)
        pygame.draw.rect(surf, stone, (*P(-.2, -1.0), .4 * u, .62 * u))
        pygame.draw.rect(surf, stone, (*P(-.2, .38), .4 * u, .62 * u))
        crack = (90, 70, 56)
        pygame.draw.lines(surf, crack, False, [P(-.2, -.45), P(0, -.6), P(.2, -.45)], max(1, line // 2))
        pygame.draw.lines(surf, crack, False, [P(-.2, .45), P(0, .6), P(.2, .45)], max(1, line // 2))
        self._arrow(surf, (255, 240, 200), P, (1.05, 0), (-1.0, 0), line)

    def _icon_swap(self, surf, P, u, pale, line):
        self._arrow(surf, (255, 120, 100), P, (1.0, -.4), (-.8, -.4), line + 1)
        self._arrow(surf, (120, 170, 255), P, (-1.0, .4), (.8, .4), line + 1)

    def _icon_blink(self, surf, P, u, pale, line):
        for x, a in ((-.75, 80), (-.35, 150)):
            ring = blank(u * .9, u * .9)
            pygame.draw.circle(ring, (210, 236, 255, a), (u * .45, u * .45), u * .4, max(1, line // 2))
            surf.blit(ring, ring.get_rect(center=P(x, .25)))
        pygame.draw.circle(surf, (240, 248, 255), P(.35, .25), u * .42)
        pygame.draw.circle(surf, (110, 170, 230), P(.35, .25), u * .42, max(1, line // 2))
        star = [P(.35, -1.0), P(.48, -.62), P(.85, -.5), P(.48, -.38), P(.35, 0), P(.22, -.38), P(-.15, -.5), P(.22, -.62)]
        pygame.draw.polygon(surf, (255, 250, 200), star)

    def _icon_tomb(self, surf, P, u, pale, line):
        stone = (176, 170, 160)
        body = [P(-.62, 1.0), P(-.62, -.35)] + bezier(P(-.62, -.35), P(-.62, -1.05), P(.62, -1.05), P(.62, -.35)) + [P(.62, 1.0)]
        pygame.draw.polygon(surf, stone, body)
        pygame.draw.polygon(surf, (80, 74, 70), body, max(1, line // 2))
        pygame.draw.line(surf, (96, 88, 82), P(0, -.6), P(0, .45), line)
        pygame.draw.line(surf, (96, 88, 82), P(-.3, -.25), P(.3, -.25), line)
        pygame.draw.line(surf, (120, 160, 90), P(-.9, 1.0), P(.9, 1.0), line)

    def _icon_twin(self, surf, P, u, pale, line):
        # a red ball and a blue ball splitting apart from one spot
        pygame.draw.line(surf, pale, P(-.1, .05), P(-.55, -.45), max(1, line // 2))
        pygame.draw.line(surf, pale, P(-.1, .05), P(.45, .5), max(1, line // 2))
        for (x, y), tint in (((-.5, -.4), (236, 84, 52)), ((.45, .42), (70, 140, 255))):
            pygame.draw.circle(surf, tint, P(x, y), u * .42)
            pygame.draw.circle(surf, (255, 255, 255), P(x - .13, y - .13), u * .12)

    def _icon_chaos(self, surf, P, u, pale, line):
        # a big and a small paddle, and a ball, with drift arrows between them
        pygame.draw.rect(surf, (236, 170, 90), (*P(-.85, -.75), .28 * u, 1.5 * u), border_radius=int(.1 * u))
        pygame.draw.rect(surf, (236, 170, 90), (*P(.55, -.3), .28 * u, .6 * u), border_radius=int(.1 * u))
        pygame.draw.circle(surf, (255, 255, 255), P(0, .35), u * .2)
        self._arrow(surf, pale, P, (.1, -.75), (-.35, -.4), line)
        self._arrow(surf, pale, P, (.45, .75), (.0, .55), line)

    def _icon_curve(self, surf, P, u, pale, line):
        # a ball bending along a curved path
        pts = [P(-.9 + .18 * i, .7 - .9 * math.sin(i / 9 * math.pi * .9)) for i in range(10)]
        pygame.draw.lines(surf, pale, False, pts, line)
        pygame.draw.circle(surf, (255, 255, 255), P(.75, .05), u * .24)
        pygame.draw.arc(surf, (120, 236, 170), (*P(.5, -.2), .5 * u, .5 * u), 0.5, 4.2, max(2, line // 2))

    def _icon_double(self, surf, P, u, pale, line):
        # a gold coin marked x2
        pygame.draw.circle(surf, (226, 176, 52), P(0, 0), u * .85)
        pygame.draw.circle(surf, (255, 222, 110), P(0, 0), u * .85, max(2, line // 2))
        pygame.draw.circle(surf, (170, 120, 30), P(0, 0), u * .6, max(1, line // 3))
        pygame.draw.line(surf, (120, 70, 10), P(-.45, -.25), P(-.05, .25), line)
        pygame.draw.line(surf, (120, 70, 10), P(-.45, .25), P(-.05, -.25), line)
        pygame.draw.lines(surf, (120, 70, 10), False, [P(.08, -.2), P(.3, -.32), P(.45, -.15), P(.1, .28), P(.48, .28)], line)

    def _icon_wind(self, surf, P, u, pale, line):
        # swirling gusts and a leaf
        for y, length in ((-.45, 1.3), (0.05, 1.6), (.5, 1.1)):
            x0 = -.85
            pygame.draw.line(surf, pale, P(x0, y), P(x0 + length, y), line)
            pygame.draw.arc(surf, pale, (*P(x0 + length - .2, y - .32), .32 * u, .32 * u), -1.6, 1.6, line)
        leaf = [P(.45, .62), P(.75, .45), P(.95, .7), P(.65, .9)]
        pygame.draw.polygon(surf, (236, 150, 40), leaf)

    def _icon_cracker(self, surf, P, u, pale, line):
        # a red firecracker with a fizzing fuse
        pygame.draw.rect(surf, (200, 34, 38), (*P(-.32, -.35), .64 * u, 1.25 * u), border_radius=int(.12 * u))
        pygame.draw.rect(surf, (250, 200, 80), (*P(-.32, -.15), .64 * u, .14 * u))
        pygame.draw.rect(surf, (250, 200, 80), (*P(-.32, .55), .64 * u, .14 * u))
        pygame.draw.line(surf, (70, 50, 40), P(0, -.35), P(.3, -.75), max(2, line // 2))
        for a in range(0, 360, 45):
            dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
            pygame.draw.line(surf, (255, 220, 120), P(.3, -.75), P(.3 + dx * .22, -.75 + dy * .22), max(1, line // 3))

    def _icon_lantern(self, surf, P, u, pale, line):
        # a glowing paper lantern on a dark sky
        pygame.draw.circle(surf, (30, 26, 60), P(0, 0), u * .95)
        pygame.draw.ellipse(surf, (230, 70, 40), (*P(-.5, -.55), 1.0 * u, 1.1 * u))
        pygame.draw.ellipse(surf, (255, 180, 90), (*P(-.28, -.4), .56 * u, .8 * u))
        pygame.draw.rect(surf, (226, 176, 52), (*P(-.3, -.7), .6 * u, .18 * u))
        pygame.draw.rect(surf, (226, 176, 52), (*P(-.3, .52), .6 * u, .18 * u))
        pygame.draw.line(surf, (226, 176, 52), P(0, .7), P(0, .92), max(2, line // 2))

    def _icon_portal(self, surf, P, u, pale, line):
        # two linked swirling rings, an arrow from one to the other
        for x, tint in ((-.5, (170, 120, 255)), (.5, (120, 220, 255))):
            pygame.draw.circle(surf, (24, 12, 50), P(x, 0), u * .42)
            pygame.draw.circle(surf, tint, P(x, 0), u * .42, max(2, line // 2))
            pygame.draw.circle(surf, tint, P(x, 0), u * .22, max(1, line // 3))
        pygame.draw.arc(surf, pale, (*P(-.5, -.75), 1.0 * u, .6 * u), 0.3, 2.84, max(2, line // 2))
        self._arrow(surf, pale, P, (.5, -.38), (.35, -.62), max(2, line // 2))

    def _icon_snowball(self, surf, P, u, pale, line):
        # a big snowball rolling right, a small one behind it, and the track it left
        pygame.draw.line(surf, pale, P(-1.0, .95), P(.95, .95), line)
        pygame.draw.circle(surf, (226, 238, 255), P(-.72, .7), u * .24)
        pygame.draw.circle(surf, (236, 244, 255), P(.18, .2), u * .74)
        pygame.draw.circle(surf, (255, 255, 255), P(-.08, -.08), u * .26)
        for x, y in ((.45, .05), (.05, .55), (.5, .55), (-.25, .3)):
            pygame.draw.circle(surf, (170, 192, 220), P(x, y), max(1, u * .08))
        pygame.draw.circle(surf, (150, 176, 210), P(.18, .2), u * .74, max(1, line // 2))

    # ---------- Stones on the court ----------

    def stone(self, w, h, style):
        return self.get(("stone", int(w), int(h), style), self._stone, int(w), int(h), style)

    def _stone(self, w, h, style):
        s = 3
        W, H = w * s, h * s
        surf = blank(W, H)
        if style == "pillar":
            body = h_gradient(W, H, [(0, (70, 8, 12, 255)), (.35, (186, 34, 36, 255)), (.5, (236, 104, 80, 255)),
                                     (.68, (170, 26, 30, 255)), (1, (60, 6, 10, 255))])
            mask = blank(W, H)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=int(W * .18))
            body.blit(mask, (0, 0), special_flags=CUT)
            band = int(min(H * .12, W * .7))
            for y in (0, H - band):
                gold = h_gradient(W, band, [(0, rgba(theme.GOLD_DARK)), (.5, rgba(theme.GOLD_BRIGHT)), (1, rgba(theme.GOLD_DARK))])
                cut = blank(W, band)
                pygame.draw.rect(cut, (255, 255, 255, 255), cut.get_rect(), border_radius=int(W * .18))
                gold.blit(cut, (0, 0), special_flags=CUT)
                body.blit(gold, (0, y))
            for y in range(band + s * 18, H - band - s * 10, s * 40):
                pygame.draw.rect(body, rgba(theme.GOLD, 150), (W * .12, y, W * .76, s * 2))
            pygame.draw.rect(body, (10, 4, 4, 255), body.get_rect(), s * 2, border_radius=int(W * .18))
            surf.blit(body, (0, 0))
        else:
            top = int(min(W * .5, H * .4))
            shape = blank(W, H)
            pygame.draw.rect(shape, (255, 255, 255, 255), (0, top, W, H - top))
            pygame.draw.ellipse(shape, (255, 255, 255, 255), (0, 0, W, top * 2))
            body = v_gradient(W, H, [(0, (176, 172, 164, 255)), (.5, (138, 132, 126, 255)), (1, (92, 86, 82, 255))])
            body.blit(speckle(W, H, 200, 255, seed=W + H), (0, 0), special_flags=MULT)
            body.blit(shape, (0, 0), special_flags=CUT)
            surf.blit(body, (0, 0))
            edge = blank(W, H)
            pygame.draw.ellipse(edge, (40, 34, 32, 255), (0, 0, W, top * 2), s * 2)
            pygame.draw.rect(edge, (0, 0, 0, 0), (0, top, W, top))
            pygame.draw.line(edge, (40, 34, 32, 255), (s, top), (s, H), s * 2)
            pygame.draw.line(edge, (40, 34, 32, 255), (W - s - 1, top), (W - s - 1, H), s * 2)
            surf.blit(edge, (0, 0))
            mark = self.brush(min(W * .55, H * .3)).render("奠", True, (70, 62, 58))
            surf.blit(mark, mark.get_rect(center=(W / 2, top + (H - top) * .32)))
            pygame.draw.rect(surf, (84, 120, 60, 255), (0, H - s * 4, W, s * 4))
        return shrink(surf, w, h)
