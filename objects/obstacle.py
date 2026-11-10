from config import BASE_H, KINEMATIC, STATIC
from objects.game_object import GameObject


class Obstacle(GameObject):
    """A tombstone or stone pillar on the court.  The ball bounces off it cleanly; paddles pass
    through it, so it can never pin a paddle away from its goal.  It may patrol up and down.

    Map pieces stay for the whole match (`life` None); a Tombstone power-up rises for a while
    and then sinks away again."""

    is_obstacle = True
    RISE = 0.35          # seconds to rise out of the ground; it is solid once it's up
    SINK = 0.5           # seconds it takes to sink away at the end
    TOUGHNESS = {"tomb": 2, "gate": 3, "wall": 4}     # hits it takes from Spirit Fire or the Snowball

    def __init__(self, game, x, y, w, h, speed = 0.0, lo = None, hi = None, life = None, style = "tomb"):
        self.body_type = KINEMATIC if speed else STATIC
        super().__init__(game, w, h, x, y, inv_mass = 0, restitution = 1.6, linear_drag = 0)
        self.speed = speed                      # px/s along its patrol, 0 for one that stands still
        self.lo = 0 if lo is None else lo       # the patrol's top and bottom (its centre's y)
        self.hi = BASE_H if hi is None else hi
        self.vy = speed
        self.life = life
        self.age = 0.0 if life is not None else self.RISE
        self.armed = life is None    # a rising stone only turns solid once the ball isn't in its way
        self.style = style
        # What sort of stone it is, and how much it takes to break: a tombstone, a drifting ferry
        # gate, or a long wall (Spirit Fire shots and the Snowball chip at them; a Firecracker's
        # blast flattens them at once)
        self.kind = "tomb" if style == "tomb" else ("gate" if speed else ("wall" if h >= 300 else "gate"))
        self.max_hp = self.TOUGHNESS[self.kind]
        self.hp = self.max_hp
        self.broken = False

    @property
    def restitution(self):
        """Whatever the ball's own bounciness (Gravity raises it), a bounce off a stone keeps its speed."""
        return 2.0 - self.game.ball.restitution

    @restitution.setter
    def restitution(self, value):
        pass

    @property
    def solid(self):
        if not self.armed or self.broken:
            return False
        return self.life is None or self.life > 0.15

    def visibility(self):
        """0-1: how far it has risen (or sunk)."""
        k = min(1.0, self.age / self.RISE)
        if self.life is not None:
            k = min(k, max(0.0, self.life / self.SINK))
        return k

    def update(self, dt):
        self.age += dt
        if self.life is not None:
            self.life -= dt
        if not self.armed and self.age >= self.RISE:
            ball = self.game.ball
            clear = (ball.x1 < self.x0 - 4 or ball.x0 > self.x1 + 4 or ball.y1 < self.y0 - 4 or ball.y0 > self.y1 + 4)
            self.armed = clear
        if self.speed:
            cy = (self.y0 + self.y1) / 2
            if cy <= self.lo:
                self.vy = abs(self.speed)
            elif cy >= self.hi:
                self.vy = -abs(self.speed)
            elif abs(self.vy) != abs(self.speed):
                self.vy = abs(self.speed) if self.vy >= 0 else -abs(self.speed)
        else:
            self.vx = self.vy = 0.0

    def can_collide_with(self, other):
        return other.is_ball and self.solid

    def on_contact(self, other, data):
        if other.is_ball:
            cx, cy = (other.x0 + other.x1) / 2, (other.y0 + other.y1) / 2
            self.game.app.fx.spark(cx, cy, 10, (196, 186, 160), speed = 320, life = .45)
            # A blazing Spirit Fire shot, or the Snowball, knocks a chunk off it
            powerups = getattr(self.game, "powerups", None)
            snow = powerups and powerups.snowball() and other is self.game.ball
            if getattr(other, "blazing", False) or snow:
                self.damage()

    def damage(self, amount=1):
        """Chip it; with no strength left it crumbles.  Answers True if that broke it."""
        if self.broken or not self.solid:
            return False
        self.hp -= amount
        cx, cy = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2
        self.game.app.fx.spark(cx, cy, 16, (176, 160, 130), speed = 380, life = .6)
        if self.hp <= 0:
            self.crumble()
            return True
        self.game.app.sound_manager.play("countdown_tick.wav", multiplier = 0.6)
        return False

    def crumble(self):
        """Broken: it falls to pieces and sinks away, and the ball passes where it stood."""
        if self.broken:
            return
        self.broken = True
        self.hp = 0
        self.life = self.SINK if self.life is None else min(self.life, self.SINK)
        cx, cy = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2
        fx = self.game.app.fx
        fx.spark(cx, cy, 40, (180, 166, 140), speed = 520, life = .8)
        fx.spark(cx, cy, 16, (120, 104, 88), speed = 300, life = 1.0)
        self.game.app.sound_manager.play("euugh.wav", multiplier = 0.5)

    def restore(self):
        """A court stone broken (or chipped) during a point stands whole again for the next serve."""
        self.hp, self.broken = self.max_hp, False
        self.life, self.age, self.armed = None, 0.0, False
