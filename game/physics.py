import math
from config import DYNAMIC, KINEMATIC, STATIC, MAX_CPF, APP_WIDTH, APP_HEIGHT

class Physics:
    @staticmethod
    def step(game, dt):
        objects = game.objects
        movers = [obj for obj in objects if obj.body_type !=  STATIC]
        remaining = dt
        cpf = 0

        # Apply drags & inputs
        for obj in movers:
            drag = math.exp(-obj.linear_drag * dt)
            a_drag = math.exp(-obj.angular_drag * dt)
            obj.vx *=  drag
            obj.vy *=  drag
            obj.spin *=  a_drag
            if obj.has_inputs:
                obj.apply_inputs(dt)
                
        # Collision Loop
        while remaining > 0 and cpf < MAX_CPF:
            collisions = Physics.detect_collisions(game, objects, remaining)
                                        
            if not collisions: # Move everything normally
                for obj in movers:
                    obj.commit_position(remaining)
                    Physics.clamp_to_world(obj)
                    obj.sync_canvas()
                break

            # Find the earliest collision
            (obj1, obj2, data) = min(collisions, key = lambda c: c[2]["t"])
            t_entry = remaining * data["t"]

            # Move everything up to earliest collision
            for obj in movers:
                obj.commit_position(t_entry)
                Physics.clamp_to_world(obj)

            # Loop through with remaining time
            remaining -=  t_entry
            cpf +=  1
    
            Physics.resolve_collision(obj1, obj2, data)

            # Show all changes on canvas
            for obj in movers:
                obj.sync_canvas()

    @staticmethod
    def detect_collisions(game, objects, remaining):
        collisions = []

        # All object pairs
        for i, obj1 in enumerate(objects):
            for obj2 in objects[i+1:]:

                # Skip pairs that can't collide
                if obj1.body_type  ==  STATIC and obj2.body_type  ==  STATIC:
                    continue
                if not obj1.can_collide_with(obj2):
                    continue
                if not obj2.can_collide_with(obj1):
                    continue

                # Check pairs that can collide
                if obj1.body_type !=  STATIC: # First object is a mover
                    result = Physics.swept_aabb(obj1, obj2, remaining)
                    if result:
                        collisions.append((obj1, obj2, result))

                elif obj2.body_type !=  STATIC: # First object is a mover
                    result = Physics.swept_aabb(obj2, obj1, remaining)
                    if result:
                        collisions.append((obj2, obj1, result))

        return collisions
    
    @staticmethod
    def swept_aabb(a, b, dt):
        if dt <= 0:
            return None
        
        rvx = a.vx - b.vx
        rvy = a.vy - b.vy

        # ---------------- X axis ----------------
        if rvx  ==  0:
            if a.x1 <= b.x0 or a.x0 >= b.x1:
                return None
            tx_entry = -float("inf")
            tx_exit  = float("inf")
            
        else:
            if rvx > 0:
                x_entry = b.x0 - a.x1
                x_exit  = b.x1 - a.x0
            else:
                x_entry = b.x1 - a.x0
                x_exit  = b.x0 - a.x1

            tx_entry = x_entry / (rvx * dt) if rvx != 0 and dt != 0 else -float('inf')
            tx_exit  = x_exit  / (rvx * dt) if rvx != 0 and dt != 0 else float('inf')

        # ---------------- Y axis ----------------
        if rvy  ==  0:
            if a.y1 <= b.y0 or a.y0 >= b.y1:
                return None
            ty_entry = -float("inf")
            ty_exit  = float("inf")
            
        else:
            if rvy > 0:
                y_entry = b.y0 - a.y1
                y_exit  = b.y1 - a.y0
            else:
                y_entry = b.y1 - a.y0
                y_exit  = b.y0 - a.y1

            ty_entry = y_entry / (rvy * dt) if rvy != 0 and dt != 0 else -float('inf')
            ty_exit  = y_exit  / (rvy * dt) if rvy != 0 and dt != 0 else float('inf')

        # ---------------- Combine ----------------
        t_entry = max(tx_entry, ty_entry)
        t_exit  = min(tx_exit, ty_exit)

        if t_entry > t_exit or t_entry < 0 or t_entry > 1:
            return None

        # ---------------- Normal ----------------
        if tx_entry > ty_entry:
            normal = (-1, 0) if rvx > 0 else (1, 0)
        else:
            normal = (0, -1) if rvy > 0 else (0, 1)

        return {"t": t_entry, "normal": normal}
    
    @staticmethod
    def resolve_collision(a, b, data):        
        nx, ny = data["normal"]        
        rvx = a.vx - b.vx
        rvy = a.vy - b.vy
        rvn = rvx * nx + rvy * ny

        if rvn > 0:
            return
        
        # Restitution & Impulse
        res = (a.restitution + b.restitution) / 2
        im_a, im_b = a.inv_mass, b.inv_mass
        im_total = im_a + im_b
        
        if im_total == 0 or (a.body_type == KINEMATIC and b.body_type != DYNAMIC):
            if a.body_type != STATIC:
                vn = a.vx * nx + a.vy * ny
                if vn < 0:
                    a.vx -=  vn * nx
                    a.vy -=  vn * ny
                    
            if b.body_type != STATIC:
                vn = b.vx * (-nx) + b.vy * (-ny)
                if vn < 0:
                    b.vx -=  vn * (-nx)
                    b.vy -=  vn * (-ny)

            Physics.positional_shove(a, b, nx, ny)
            Physics.collision_dispatcher(a, b, data)
            return

        impulse_total = -(1 + res) * rvn / im_total
        impulse_x, impulse_y = impulse_total * nx, impulse_total * ny
        
        if a.body_type != STATIC:
            a.vx +=  impulse_x * im_a
            a.vy +=  impulse_y * im_a

        if b.body_type != STATIC:
            b.vx -=  impulse_x * im_b
            b.vy -=  impulse_y * im_b

        Physics.positional_shove(a, b, nx, ny)
        Physics.collision_dispatcher(a, b, data)

    @staticmethod
    def collision_dispatcher(a, b, data):
        # Ensure paddle sets bounce first, ball scales speed last
        if getattr(a, "is_ball", False) and getattr(b, "is_paddle", False):
            b.on_contact(a, data)
            a.on_contact(b, data)
        elif getattr(b, "is_ball", False) and getattr(a, "is_paddle", False):
            a.on_contact(b, data)
            b.on_contact(a, data)
        else:
            a.on_contact(b, data)
            b.on_contact(a, data)

    @staticmethod
    def clamp_to_world(obj):               
        if obj.body_type != KINEMATIC:
            return
        
        if obj.x0 < 0:
            (obj.x0, obj.x1, obj.vx) = (0, obj.width, 0)
        if obj.x1 > APP_WIDTH:
            (obj.x1, obj.x0, obj.vx) = (APP_WIDTH, APP_WIDTH-obj.width, 0)
        if obj.y0 < 0:
            (obj.y0, obj.y1, obj.vy) = (0, obj.height, 0)
        if obj.y1 > APP_HEIGHT:
            (obj.y1, obj.y0, obj.vy) = (APP_HEIGHT, APP_HEIGHT-obj.height, 0)

    @staticmethod
    def positional_shove(a, b, nx, ny):
        shove = 0.01
        if a.body_type != STATIC:
            a.x0 +=  nx * shove
            a.x1 +=  nx * shove
            a.y0 +=  ny * shove
            a.y1 +=  ny * shove
        if b.body_type != STATIC:
            b.x0 -=  nx * shove
            b.x1 -=  nx * shove
            b.y0 -=  ny * shove
            b.y1 -=  ny * shove
