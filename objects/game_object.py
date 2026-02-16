import math
from config import STATIC

class GameObject:
    body_type = None
    has_inputs = False
    can_score = False

    is_wall = False
    is_ball = False
    is_paddle = False

    def __init__(self, game, width, height, x, y,
                 vx = 0, vy = 0, spin = 0,
                 mass = 1, inv_mass = None,
                 restitution = 0,
                 friction = 0,
                 linear_drag = 0,
                 angular_drag = 0):
    
        self.game = game
        self.canvas = game.canvas

        # Size & Position
        self.width = width
        self.height = height
        
        self.x0 = self.spawn_x = x
        self.y0 = self.spawn_y = y
        self.x1 = x + width
        self.y1 = y + height
        
        self.home_x = x + width / 2
        self.home_y = y + height / 2

        # Speed & Spin
        self.vx = self.spawn_vx = vx
        self.vy = self.spawn_vy = vy
        self.spin = self.spawn_spin = spin

        # Inverted Mass & Inertia
        if inv_mass is None:
            self.mass = mass
            self.inv_mass = 0 if self.body_type  ==  STATIC else (1/mass if mass > 0 else 0)
        else:
            self.inv_mass = inv_mass
            self.mass = 1/inv_mass if inv_mass !=  0 else float("inf")
            
        # Other Properties
        self.restitution = restitution
        self.friction = friction
        self.linear_drag = linear_drag
        self.angular_drag = angular_drag

        # Soft control strength for objects with inputs
        self.soft_control_k = 12

        game.objects.append(self)

    def apply_inputs(self, dt):
        if self.ai_enabled:
            dvx, dvy = self.ai_input(dt)
        else:
            dvx = dvy = 0
            if self.up in self.game.app.keys_down:
                dvy -=  self.speed
            if self.down in self.game.app.keys_down:
                dvy +=  self.speed
            if self.left in self.game.app.keys_down:
                dvx -=  self.speed
            if self.right in self.game.app.keys_down:
                dvx +=  self.speed

        a = 1 - math.exp(-self.soft_control_k * dt)
        self.vx +=  (dvx - self.vx) * a
        self.vy +=  (dvy - self.vy) * a

    def commit_position(self, dt):  
        self.x0 +=  self.vx * dt
        self.y0 +=  self.vy * dt
        self.x1 +=  self.vx * dt
        self.y1 +=  self.vy * dt

    def sync_canvas(self):
        item_id = getattr(self, "id", None)
        if item_id is None:
            return
        self.canvas.coords(item_id, self.x0, self.y0, self.x1, self.y1)

    def can_collide_with(self, other):
        if getattr(other, "is_separator", False):
            return False
        return True

    def on_contact(self, other, data):
        pass

    def reset(self):
        self.x0 = self.spawn_x
        self.y0 = self.spawn_y
        self.x1 = self.spawn_x + self.width
        self.y1 = self.spawn_y + self.height
        self.vx = self.spawn_vx
        self.vy = self.spawn_vy
        self.spin = self.spawn_spin
        self.sync_canvas()
