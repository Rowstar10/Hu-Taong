import math
from config import DYNAMIC, KINEMATIC, STATIC, MAX_CPF, BASE_W, BASE_H

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

        Physics.resolve_overlaps(objects)

        # Collision Loop
        while remaining > 0 and cpf < MAX_CPF:
            collisions = Physics.detect_collisions(game, objects, remaining)
                                        
            if not collisions: # Move everything normally
                for obj in movers:
                    obj.commit_position(remaining)
                    Physics.clamp_to_world(obj)
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

    @staticmethod
    def resolve_overlaps(objects):
        """A paddle that grew (Chaos Mode +, Giant Paddle), or a ball that swelled, can begin a step
        already overlapping the other.  A sweep only sees things that are about to touch, so it
        would let the ball pass straight through: push the ball out the shallow way instead and
        let the paddle play it like any other hit."""
        balls = [obj for obj in objects if obj.is_ball and not getattr(obj, "stuck", None)]
        only_paddles = [obj for obj in objects if obj.is_paddle
                        and not (getattr(obj, "remote", False) and getattr(obj.game, "net", None))]
        stones = [obj for obj in objects if getattr(obj, "is_obstacle", False) and obj.solid]
        for ball in balls:
            for stone in stones:
                if ball.can_collide_with(stone):         # a Ghost Ball is let pass through
                    Physics.free_from_stone(ball, stone, only_paddles + stones)
        paddles = only_paddles
        for ball in balls:
            for paddle in paddles:
                ox = min(ball.x1, paddle.x1) - max(ball.x0, paddle.x0)
                oy = min(ball.y1, paddle.y1) - max(ball.y0, paddle.y0)
                if ox <= 0 or oy <= 0:
                    continue
                # out the shallow way, unless that is into the top or bottom wall (a pinch): then sideways
                up = ball.y0 + ball.y1 < paddle.y0 + paddle.y1
                room = paddle.y0 if up else BASE_H - paddle.y1
                if ox < oy or room < ball.height + 1:
                    side = 1 if ball.x0 + ball.x1 > paddle.x0 + paddle.x1 else -1
                    ball.x0 += side * (ox + 0.5)
                    ball.x1 += side * (ox + 0.5)
                    normal = (-side, 0)
                else:
                    side = 1 if ball.y0 + ball.y1 > paddle.y0 + paddle.y1 else -1
                    ball.y0 += side * (oy + 0.5)
                    ball.y1 += side * (oy + 0.5)
                    normal = (0, -side)
                Physics.clamp_to_world(ball)
                Physics.resolve_collision(paddle, ball, {"t": 0.0, "normal": normal})

    @staticmethod
    def free_from_stone(ball, stone, others):
        """A stone that rose or drifted onto the ball, or a paddle that pushed the ball into one:
        move the ball out by the shortest way that doesn't land it in a paddle or another stone,
        and bounce it off that face."""
        ox = min(ball.x1, stone.x1) - max(ball.x0, stone.x0)
        oy = min(ball.y1, stone.y1) - max(ball.y0, stone.y0)
        if ox <= 0 or oy <= 0:
            return
        exits = [(stone.x1 - ball.x0 + 0.5, 0, (1, 0)), (ball.x1 - stone.x0 + 0.5, 0, (-1, 0)),
                 (stone.y1 - ball.y0 + 0.5, 1, (0, 1)), (ball.y1 - stone.y0 + 0.5, 1, (0, -1))]
        exits.sort(key = lambda e: e[0])
        for push, axis, (dx, dy) in exits:
            x0, y0 = ball.x0 + dx * push, ball.y0 + dy * push
            x1, y1 = x0 + ball.width, y0 + ball.height
            if y0 < 0 or y1 > BASE_H:
                continue
            if any(o is not stone and min(x1, o.x1) - max(x0, o.x0) > 0 and min(y1, o.y1) - max(y0, o.y0) > 0
                   for o in others):
                continue
            break
        else:
            push, axis, (dx, dy) = exits[0]
        ball.x0 += dx * push
        ball.x1 += dx * push
        ball.y0 += dy * push
        ball.y1 += dy * push
        Physics.clamp_to_world(ball)
        Physics.resolve_collision(stone, ball, {"t": 0.0, "normal": (-dx, -dy)})

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

            step = rvx * dt     # can round to 0 for a crawling ball even when rvx isn't 0
            tx_entry = x_entry / step if step != 0 else -float('inf')
            tx_exit  = x_exit  / step if step != 0 else float('inf')

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

            step = rvy * dt
            ty_entry = y_entry / step if step != 0 else -float('inf')
            ty_exit  = y_exit  / step if step != 0 else float('inf')

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

        def call_contacts(a_obj, b_obj):
            """Deterministic callback ordering.

            For ball+paddle collisions, let the paddle shape the bounce first,
            then let the ball apply rally/sfx (which may rescale velocity).
            """
            if a_obj.is_paddle and b_obj.is_ball:
                a_obj.on_contact(b_obj, data)
                b_obj.on_contact(a_obj, data)
                return
            if b_obj.is_paddle and a_obj.is_ball:
                b_obj.on_contact(a_obj, data)
                a_obj.on_contact(b_obj, data)
                return
            a_obj.on_contact(b_obj, data)
            b_obj.on_contact(a_obj, data)
        
        if im_total  ==  0 or (a.body_type  ==  KINEMATIC and b.body_type !=  DYNAMIC):
            if a.body_type !=  STATIC:
                vn = a.vx * nx + a.vy * ny
                if vn < 0:
                    a.vx -=  vn * nx
                    a.vy -=  vn * ny
                    
            if b.body_type !=  STATIC:
                vn = b.vx * (-nx) + b.vy * (-ny)
                if vn < 0:
                    b.vx -=  vn * (-nx)
                    b.vy -=  vn * (-ny)

            Physics.positional_shove(a, b, nx, ny)
            call_contacts(a, b)
            return

        impulse_total = -(1 + res) * rvn / im_total
        impulse_x, impulse_y = impulse_total * nx, impulse_total * ny
        
        if a.body_type !=  STATIC:
            a.vx +=  impulse_x * im_a
            a.vy +=  impulse_y * im_a

        if b.body_type !=  STATIC:
            b.vx -=  impulse_x * im_b
            b.vy -=  impulse_y * im_b
         
        # Separate first so callbacks see resolved (non-overlapping) positions.
        Physics.positional_shove(a, b, nx, ny)
        call_contacts(a, b)
        
    @staticmethod
    def clamp_to_world(obj):
        if obj.is_ball:
            # A ball squeezed against the top or bottom (say, pinched by a paddle's end) is
            # put back inside and bounced away, so it can never slip out through a wall
            if obj.y0 < 0:
                (obj.y0, obj.y1, obj.vy) = (0, obj.height, abs(obj.vy))
            if obj.y1 > BASE_H:
                (obj.y1, obj.y0, obj.vy) = (BASE_H, BASE_H - obj.height, -abs(obj.vy))
            return
        if obj.body_type !=  KINEMATIC:
            return
        
        if obj.x0 < 0:
            (obj.x0, obj.x1, obj.vx) = (0, obj.width, 0)
        if obj.x1 > BASE_W:
            (obj.x1, obj.x0, obj.vx) = (BASE_W, BASE_W-obj.width, 0)
        if obj.y0 < 0:
            (obj.y0, obj.y1, obj.vy) = (0, obj.height, 0)
        if obj.y1 > BASE_H:
            (obj.y1, obj.y0, obj.vy) = (BASE_H, BASE_H-obj.height, 0)

    @staticmethod
    def positional_shove(a, b, nx, ny):
        shove = 0.01
        if a.body_type !=  STATIC:
            a.x0 +=  nx * shove
            a.x1 +=  nx * shove
            a.y0 +=  ny * shove
            a.y1 +=  ny * shove
        if b.body_type !=  STATIC:
            b.x0 -=  nx * shove
            b.x1 -=  nx * shove
            b.y0 -=  ny * shove
            b.y1 -=  ny * shove
