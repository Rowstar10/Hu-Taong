import math
from config import DYNAMIC, KINEMATIC, MAX_BOUNCE_ANGLE
from helpers import clamp, clamp01, reflect_in_range, lerp
from objects.game_object import GameObject

class Paddle(GameObject):
    body_type = KINEMATIC
    is_paddle = True
    has_inputs = True
        
    def __init__(self, game, width, height, x, y,
                 up, down, left, right, color1, color2,
                 sound, speed = 1400):
    
        super().__init__(game, width, height, x, y,
                         inv_mass = 0,
                         restitution = 1,
                         linear_drag = 1)
        
        self.up = up
        self.down = down
        self.left = left
        self.right = right
        self.speed = speed

        self.is_left = self.home_x < self.game.width / 2
        
        self.color1 = color1
        self.color2 = color2
        self.sound = sound
        self.score = 0

        self.id = self.canvas.create_rectangle(self.x0, self.y0, self.x1, self.y1, fill = color1)

        # ------------------ AI Settings ------------------
        self.ai_enabled = False
        self.ai_difficulty = 5
        
        d = clamp(int(self.ai_difficulty), 1, 10)
        W = self.game.width
        self.reaction_time      = lerp(0.15, 0.05, (d - 1) / 9)
        self.foresight_dist     = lerp(W / 3, W, (d - 1) / 9) # Only reacts to incoming ball within this distance
        self.max_pred_bounces   = int(lerp(0, 2, (d - 1) / 9))
        self.strike_dist        = lerp(100, 300, (d - 1) / 9) # dvx = 50% of maximum speed at strike distance
        self.arrive_dist        = lerp(300, 100, (d - 1) / 9) # dvy begins to decrease at arrive distance

        self.ai_timer = 0
        self.target = None
        self.ai_tar_x = self.home_x
        self.ai_tar_y = self.home_y

    def can_collide_with(self, other):
        return True

    def on_contact(self, other, data):
        if other.body_type != DYNAMIC:
            return

        nx, ny = data["normal"]
        speed = math.hypot(other.vx, other.vy)
        
        if speed == 0:
            return

        if nx != 0:

            center = (self.y0 + self.y1) / 2
            other_center = (other.y0 + other.y1) / 2
            offset = (other_center - center) / (self.height / 2)
            offset = max(-1, min(1, offset))

            angle = offset * MAX_BOUNCE_ANGLE

            dir_x = -nx * math.cos(angle)
            dir_y = math.sin(angle)

        elif ny != 0:

            center = (self.x0 + self.x1) / 2
            other_center = (other.x0 + other.x1) / 2
            offset = (other_center - center) / (self.width / 2)
            offset = max(-1, min(1, offset))

            angle = offset * MAX_BOUNCE_ANGLE

            dir_x = math.sin(angle)
            dir_y = -ny * math.cos(angle)

        else:
            return

        mag = math.hypot(dir_x, dir_y)
        if mag == 0:
            return

        dir_x /= mag
        dir_y /= mag

        other.vx = dir_x * speed
        other.vy = dir_y * speed

    # ------------------------ AI Logic ------------------------
    def ai_input(self, dt):
        W, H = self.game.width, self.game.height
        pad_cx  = (self.x0 + self.x1) / 2
        pad_cy  = (self.y0 + self.y1) / 2
        
        # -------------- Reaction Time --------------
        self.ai_timer -= dt
                
        if self.ai_timer <= 0.0:
            self.ai_timer = self.reaction_time

            # ---------- Determine the best ball to target ----------
            balls = [obj for obj in self.game.objects if obj.is_ball]
            
            self.target = None
            best_t = None
            
            for ball in balls:
                ball_cx = (ball.x0 + ball.x1) / 2
                r = ball.diameter / 2

                if self.is_left:
                    defend_x = self.x1 + ball.width / 2
                    ball_far = ball_cx > self.home_x + self.foresight_dist
                    ball_behind = ball_cx < (self.x0 - r - 10)
                else:
                    defend_x = self.x0 - ball.width / 2
                    ball_far = ball_cx < self.home_x - self.foresight_dist
                    ball_behind = ball_cx > (self.x1 + r + 10)
                    
                t = (defend_x - ball_cx) / ball.vx if ball.vx != 0 else (defend_x - ball_cx) * float('inf')
                incoming = t > 0
                
                if ball_behind:
                    self.target, best_t = ball, t
                    break
                    
                if (not incoming and abs(ball.vx) > 400) or ball_far:
                    continue

                if self.target is None or t < best_t:
                    self.target, best_t = ball, t
            
            # ------------ Update Target (tar_x / tar_y) ------------
            tar_x = self.home_x
            tar_y = self.home_y
            
            if self.target is not None:
                ball, t = self.target, best_t
                
                r = ball.diameter / 2
                ball_cx = (ball.x0 + ball.x1) / 2
                ball_cy = (ball.y0 + ball.y1) / 2

                if self.is_left:
                    defend_x = self.x1 + ball.width / 2
                    strike_x = W/2
                    ball_behind = ball_cx < (self.x0 - r - 10)
                else:
                    defend_x = self.x0 - ball.width / 2
                    strike_x = W/2
                    ball_behind = ball_cx > (self.x1 + r + 10)
                    
                self.contact_dist_x = abs(defend_x - ball_cx)
                
                if ball_behind:
                    want_dir = +1 if ball_cy < H / 2 else -1
                    safety_dist = (self.height * 0.6 + r + 12)
                    too_close = abs(ball_cy - pad_cy) < safety_dist
                    
                    if too_close:
                        tar_x = pad_cx
                        tar_y = clamp(ball_cy + want_dir * safety_dist,
                                      self.height / 2, H - self.height / 2)
                    
                elif ball.vx != 0:
                    pred_cy = ball_cy + ball.vy * t
                    pred_cy, pred_bounces = reflect_in_range(pred_cy, r, H - r)
                    can_predict = pred_bounces <= self.max_pred_bounces
                    y_aligned = abs(ball_cy - pad_cy) < self.height / 2

                    if y_aligned:
                        tar_x = strike_x
                        
                    if can_predict:
                        tar_y = pred_cy
                    else:
                        tar_y = clamp(ball_cy, H/2 - self.height/2, H/2 + self.height/2)
                        
                elif (ball_cx < W/2 and self.is_left) or (ball_cx > W/2 and not self.is_left):
                    tar_x = strike_x
                    tar_y = ball_cy
                
            self.ai_tar_x, self.ai_tar_y = tar_x, tar_y

        # ------------ Desired Velocity ------------
        error_x = self.ai_tar_x - pad_cx
        error_y = self.ai_tar_y - pad_cy
        
        want_dir_x = 1 if error_x > 0 else -1 if error_x < 0 else 0
        want_dir_y = 1 if error_y > 0 else -1 if error_y < 0 else 0

        if self.target is None:
            arrive_drag_x = clamp01(abs(error_x) / self.arrive_dist)
            dvx = want_dir_x * self.speed * arrive_drag_x if abs(error_x) > 10 else 0
        else:
            strike_factor = 1 / (1 + (self.contact_dist_x / self.strike_dist) ** 2)
            dvx = want_dir_x * self.speed * strike_factor if abs(error_x) > 10 else 0

        arrive_drag_y = clamp01(abs(error_y) / self.arrive_dist)
        dvy = want_dir_y * self.speed * arrive_drag_y if abs(error_y) > 10 else 0
        
        return dvx, dvy

    def toggle_ai_state(self):
        self.ai_enabled = not self.ai_enabled
