"""The living world behind and in front of the UI: butterflies, embers, petals,
mist, hanging lanterns and talismans, Boo Tao, and one-off bursts."""
import math, random, pygame

from config import BASE_W, BASE_H
from render import theme
from render.art import Art, ADD, scaled


class Butterfly:
    __slots__ = ("x", "y", "size", "tint", "heading", "speed", "steer", "flap", "flap_rate", "life", "max_life")

    def __init__(self, x, y, size, tint="red", heading=None, speed=None, life=None):
        self.x, self.y = x, y
        self.size = size
        self.tint = tint
        self.heading = random.uniform(0, math.tau) if heading is None else heading
        self.speed = random.uniform(45, 115) if speed is None else speed
        self.steer = 0.0
        self.flap = random.uniform(0, Art.FLAP_FRAMES)
        self.flap_rate = random.uniform(11, 17)
        self.life = self.max_life = life

    def update(self, dt, mouse):
        self.steer += random.uniform(-9, 9) * dt
        self.steer *= math.exp(-2.2 * dt)
        self.heading += self.steer * dt * 2

        # Shy of the cursor, like the real thing
        dx, dy = self.x - mouse[0], self.y - mouse[1]
        d2 = dx * dx + dy * dy
        if self.life is None and d2 < 32000:
            away = math.atan2(dy, dx)
            gap = (away - self.heading + math.pi) % math.tau - math.pi
            self.heading += gap * min(1, 5 * dt)

        pace = self.speed * (1.7 if d2 < 32000 else 1)
        self.flap = (self.flap + self.flap_rate * dt * (1.6 if d2 < 32000 else 1)) % Art.FLAP_FRAMES
        self.x += math.cos(self.heading) * pace * dt
        self.y += math.sin(self.heading) * pace * dt + math.sin(self.flap * .63) * 26 * dt

        if self.life is not None:
            self.life -= dt
        else:
            m = 80
            if self.x < -m: self.x = BASE_W + m
            if self.x > BASE_W + m: self.x = -m
            if self.y < -m: self.y = BASE_H + m
            if self.y > BASE_H + m: self.y = -m

    def draw(self, screen, art):
        turn = round((math.degrees(self.heading) + 90) / 15) % Art.TURN_STEPS
        sprite = art.butterfly(self.size, int(self.flap), turn, self.tint)
        rect = sprite.get_rect(center=(self.x, self.y))

        if self.life is not None and self.life < .5:
            # Sprites are shared, so restore it; set_alpha(None) would stop it blending at all
            sprite.set_alpha(int(255 * max(0, self.life) / .5))
            screen.blit(sprite, rect)
            sprite.set_alpha(255, pygame.RLEACCEL)
        else:
            screen.blit(sprite, rect)


class Mote:
    """An ember, spark or falling petal."""
    __slots__ = ("x", "y", "vx", "vy", "gravity", "life", "max_life", "size", "color", "spin", "angle", "sway")

    def __init__(self, x, y, vx, vy, life, size, color=None, gravity=0.0, spin=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity
        self.spin = spin
        self.angle = random.uniform(0, 16)
        self.sway = random.uniform(0, math.tau)

    def update(self, dt):
        self.life -= dt
        self.sway += dt * 2.4
        self.vy += self.gravity * dt
        self.x += (self.vx + math.sin(self.sway) * 22) * dt
        self.y += self.vy * dt
        self.angle = (self.angle + self.spin * dt) % 16


class Ambience:
    # Big butterflies stay behind the UI; only small ones may drift across it
    SCENES = {"title": {"flies": 10, "front": 6, "sizes": (48, 64, 88), "front_sizes": (40, 48, 64),
                        "embers": 44, "petals": 22, "mist": 340, "ghost": True,
                        "lanterns": ((1180, 150), (1472, 70), (1760, 190)), "talismans": ()},
              "menu":  {"flies": 7, "front": 4, "sizes": (48, 64, 88), "front_sizes": (32, 40),
                        "embers": 28, "petals": 12, "mist": 170, "ghost": False,
                        "lanterns": ((262, 18), (1658, 18)), "talismans": ((62, 22, "镇魂"), (1858, 40, "往生"))},
              "game":  {"flies": 4, "front": 0, "sizes": (32, 48), "front_sizes": (32,),
                        "embers": 12, "petals": 0, "mist": 0, "ghost": False,
                        "lanterns": (), "talismans": ()}}

    MAX_MOTES = 420

    def __init__(self, app):
        self.app = app
        self.art = app.art
        self.time = 0.0
        self.scene = None
        self.flies = []
        self.front_flies = []
        self.burst_flies = []
        self.embers = []
        self.petals = []
        self.sparks = []
        self.fade_left = 0.0
        self.fade_total = 1.0
        self.fade_surf = pygame.Surface((BASE_W, BASE_H))
        self.fade_surf.fill((22, 4, 6))
        self.level = 0          # Settings > Interface > Effects: Full, Reduced, Off
        self.amount = 1.0
        self.set_scene("title")

    # ---------- One-off effects ----------

    def burst(self, x, y, count, size=64, tint="red", speed=(180, 460), life=(1.1, 2.2), arc=(0, math.tau)):
        """Butterflies scatter outward from a point."""
        for _ in range(round(count * self.amount)):
            self.burst_flies.append(Butterfly(x, y, size, tint, random.uniform(*arc),
                                              random.uniform(*speed), random.uniform(*life)))

    def spark(self, x, y, count, color=theme.EMBER, speed=420, life=.7, arc=(0, math.tau), gravity=260):
        if len(self.sparks) > self.MAX_MOTES:
            return
        for _ in range(round(count * self.amount)):
            a, v = random.uniform(*arc), random.uniform(.25, 1) * speed
            self.sparks.append(Mote(x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(.4, 1) * life,
                                    random.choice((3, 4, 6)), color, gravity))

    def swarm(self):
        """A wall of butterflies crosses the screen."""
        for i in range(round(46 * self.amount)):
            self.burst_flies.append(Butterfly(random.uniform(-520, -40), random.uniform(0, BASE_H), random.choice((48, 64, 88)),
                                              heading=random.uniform(-.25, .25), speed=random.uniform(900, 1500), life=2.2))

    def fade(self, duration=.4):
        self.fade_left = self.fade_total = duration

    # ---------- Scene ----------

    def current_scene(self):
        stack = self.app.state_manager.stack
        if not stack:
            return self.scene
        base = stack[self.app.state_manager.screen_index()]
        if base.is_game:
            return "game"
        return "title" if base.NAME == "main_menu" else "menu"

    def stock(self, flies, count, sizes, tints):
        del flies[count:]
        for fly in flies:
            if fly.size not in sizes:
                fly.size = random.choice(sizes)
        while len(flies) < count:
            flies.append(Butterfly(random.uniform(0, BASE_W), random.uniform(0, BASE_H),
                                   random.choice(sizes), random.choice(tints)))

    def set_scene(self, name):
        self.scene = name
        self.amount = (1.0, 0.5, 0.0)[self.level]
        base = self.SCENES[name]
        self.config = dict(base, **{key: round(base[key] * self.amount) for key in ("flies", "front", "embers", "petals")})
        if self.level == 2:
            self.config.update(mist=0, lanterns=(), talismans=(), ghost=False)
            self.burst_flies.clear()
            self.sparks.clear()
        tints = ("red", "red", "red", "red", "blue") if name == "title" else ("red",)

        self.stock(self.flies, self.config["flies"], self.config["sizes"], tints)
        self.stock(self.front_flies, self.config["front"], self.config["front_sizes"], tints)

        del self.embers[self.config["embers"]:]
        del self.petals[self.config["petals"]:]

    def spawn_ember(self, anywhere=False):
        y = random.uniform(0, BASE_H) if anywhere else BASE_H + 10
        life = random.uniform(5, 11)
        color = random.choice((theme.EMBER, theme.FLAME, theme.CRIMSON_BRIGHT))
        self.embers.append(Mote(random.uniform(0, BASE_W), y, random.uniform(-14, 14), random.uniform(-120, -44),
                                life, random.choice((3, 4, 6)), color))

    def spawn_petal(self, anywhere=False):
        y = random.uniform(-40, BASE_H) if anywhere else -30
        self.petals.append(Mote(random.uniform(-200, BASE_W), y, random.uniform(18, 60), random.uniform(38, 96),
                                30, random.choice((18, 24, 30)), spin=random.uniform(-7, 7)))

    # ---------- Update ----------

    def update(self, dt):
        dt = min(dt, .05)
        self.time += dt

        scene = self.current_scene()
        level = self.app.settings.interface.effects
        if scene != self.scene or level != self.level:
            self.level = level
            self.set_scene(scene)

        mouse = self.app.pointer()
        for fly in self.flies + self.front_flies:
            fly.update(dt, mouse)

        for fly in self.burst_flies:
            fly.update(dt, mouse)
        self.burst_flies = [f for f in self.burst_flies if f.life > 0]

        while len(self.embers) < self.config["embers"]:
            self.spawn_ember(anywhere=self.time < .1)
        while len(self.petals) < self.config["petals"]:
            self.spawn_petal(anywhere=self.time < .1)

        for mote in self.embers:
            mote.update(dt)
        for mote in self.petals:
            mote.update(dt)
        for mote in self.sparks:
            mote.update(dt)

        self.embers = [m for m in self.embers if m.life > 0 and m.y > -20]
        self.petals = [m for m in self.petals if m.y < BASE_H + 40 and m.x < BASE_W + 40]
        self.sparks = [m for m in self.sparks if m.life > 0]

        if self.fade_left > 0:
            self.fade_left -= dt

    # ---------- Draw ----------

    def draw_mist(self, screen, tile, speed, y):
        x = -(self.time * speed) % BASE_W
        screen.blit(tile, (x - BASE_W, y))
        screen.blit(tile, (x, y))

    def draw_hanging(self, screen, sprite, name, x, drop, phase, swing=3.0):
        """Hang a sprite from the top of the screen and let it sway."""
        angle = math.sin(self.time * .9 + phase) * swing
        step = round(angle / .5)
        turned = self.art.turned(name, sprite, step, .5)
        length = drop + sprite.get_height() / 2
        a = math.radians(step * .5)
        cx, cy = x + math.sin(a) * length, math.cos(a) * length
        tip = (x + math.sin(a) * drop, math.cos(a) * drop)
        pygame.draw.aaline(screen, theme.CINNABAR, (x, 0), tip)
        screen.blit(turned, turned.get_rect(center=(cx, cy)))
        return cx, cy

    def draw_lanterns(self, screen):
        for i, (x, drop) in enumerate(self.config["lanterns"]):
            width = 132 if i % 2 == 0 else 104
            sprite = self.art.lantern(width)
            cx, cy = self.draw_hanging(screen, sprite, f"lantern{width}", x, drop, i * 1.7, 2.5)

            level = 4 + round(1.6 * (math.sin(self.time * 7.3 + i) * .5 + .5))
            glow = self.art.glow(width + 60, scaled((132, 44, 20), level / 6))
            screen.blit(glow, glow.get_rect(center=(cx, cy - sprite.get_height() * .12)), special_flags=ADD)

    def draw_talismans(self, screen):
        for i, (x, drop, text) in enumerate(self.config["talismans"]):
            sprite = self.art.talisman(84, 236, text)
            self.draw_hanging(screen, sprite, text, x, drop, i * 2.1, 3.5)

    def draw_ghost(self, screen):
        sprite = self.art.ghost(190)
        x = 1590 + math.sin(self.time * .37) * 90
        y = 700 + math.sin(self.time * 1.3) * 26
        if math.cos(self.time * .37) < 0:
            sprite = self.art.get(("ghost_flip",), pygame.transform.flip, sprite, True, False)

        glow = self.art.glow(190, (48, 22, 26))
        screen.blit(glow, glow.get_rect(center=(x, y)), special_flags=ADD)
        screen.blit(sprite, sprite.get_rect(center=(x, y)))

    def draw_back(self, screen):
        if self.config["lanterns"]:
            self.draw_lanterns(screen)
        if self.config["talismans"]:
            self.draw_talismans(screen)
        if self.config["ghost"]:
            self.draw_ghost(screen)
        if self.config["mist"]:
            self.draw_mist(screen, self.art.mist(BASE_W, self.config["mist"], (190, 90, 90), 3), 22,
                           BASE_H - self.config["mist"] + 20)
        for fly in self.flies:
            fly.draw(screen, self.art)

    def draw_motes(self, screen, motes, fade_in=False):
        for m in motes:
            k = m.life / m.max_life
            level = max(1, round(k * 5)) if not fade_in else max(1, round(min(k, (1 - k) * 6, 1) * 5))
            glow = self.art.glow(m.size * 3, scaled(m.color, level / 5))
            screen.blit(glow, (m.x - m.size * 3, m.y - m.size * 3), special_flags=ADD)

    def draw_front(self, screen):
        for fly in self.front_flies:
            fly.draw(screen, self.art)
        for m in self.petals:
            screen.blit(self.art.petal(m.size, int(m.angle)), (m.x, m.y))
        self.draw_motes(screen, self.embers, fade_in=True)

    def draw_overlays(self, screen):
        """Bursts always sit above the UI."""
        self.draw_motes(screen, self.sparks)
        for fly in self.burst_flies:
            fly.draw(screen, self.art)

        if self.fade_left > 0:
            self.fade_surf.set_alpha(int(255 * max(0, self.fade_left) / self.fade_total))
            screen.blit(self.fade_surf, (0, 0))
