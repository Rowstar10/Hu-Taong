import tkinter as tk
import sys, time, random, math

# ------------------ Constants ------------------

FPS = 100

menu_width = 500
menu_height = 600

app_width = 1500
app_height = 800

pause_width = 500
pause_height = 200

max_bounce_angle = math.radians(60)
spin_factor = 0.6
max_spin = 600
min_speed = 500
half_pi = math.pi/2

# ------------------ Helpers ------------------

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

def clear_ui(root):
    for widget in root.winfo_children():
        widget.destroy()

# ------------------ Game Class ------------------

class Game:

    List = []
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Hu Taong')
        center_window(self.root, menu_width, menu_height)

        self.objects = []
        self.resettable = []

        self.running = False
        self.keys_down = set()
        self.root.bind_all("<KeyPress>", self.key_press)
        self.root.bind_all("<KeyRelease>", self.key_release)

        self.main_menu()

        self.root.mainloop()

    # ---------------- Main Menu ----------------
    
    def main_menu(self):
        self.root.bind("<Escape>", lambda e: self.quit_game())
        center_window(self.root, menu_width, menu_height)
        clear_ui(self.root)
        self.clear_game_objects()

        self.canvas = tk.Canvas(self.root, width=menu_width, height=menu_height, bg="black")
        self.canvas.pack()

        self.canvas.create_text(menu_width/2, menu_height/6, text="Hu Taong!",
                                font=("Helvetica", 60, "bold"), fill="red")

        self.canvas.create_text(menu_width/2, (menu_height - 140) / 2, text="Main Menu",
                                font=("Helvetica", 40, "bold"), fill="white")

        play_btn = tk.Button(self.root, text="Play Game", font=("Helvetica", 20, "bold"),
                             width=10, height=1, bg="green", command=self.start_game)

        settings_btn = tk.Button(self.root, text="Settings", font=("Helvetica", 20, "bold"),
                                 width=10, height=1, bg="orange", command=self.settings_menu)

        quit_btn = tk.Button(self.root, text="Quit Game", font=("Helvetica", 20, "bold"),
                             width=10, height=1, bg="red", command=self.quit_game)

        play_btn.place(relx=0.5, y = (menu_height + 50) / 2, anchor="center")
        settings_btn.place(relx=0.5, y = (menu_height + 200) / 2, anchor="center")
        quit_btn.place(relx=0.5, y = (menu_height + 350) / 2, anchor="center")

    def start_game(self):
        self.running = False
        self.root.unbind("<Escape>")
        center_window(self.root, app_width, app_height)
        clear_ui(self.root)
        self.clear_game_objects()
        
        self.canvas = tk.Canvas(self.root, width=app_width, height=app_height, bg="black")
        self.canvas.pack()

        self.ball = Ball(self, diameter=50, speed=400, color="white")
        self.objects.append(self.ball)
        self.resettable.append(self.ball)

        self.p1 = Paddle(self, width=30, height=180, x=30, up="w", down="s", left="a", right="d",
                         color1="Red", color2="Orange Red")
        self.p2 = Paddle(self, width=30, height=180, x=app_width-60, up="Up", down="Down", left="Left", right="Right",
                         color1="Blue", color2="Royal Blue")
        self.objects += [self.p1, self.p2]
        self.resettable += [self.p1, self.p2]

        self.rally_value = 0
        self.rally_text = self.canvas.create_text(app_width / 2, 50,
                                                  text="Rally: 0",
                                                  font=("Helvetica", 30, "bold"),
                                                  fill="white")
        
        self.countdown(3, self.begin_round)
        
    def quit_game(self):
        self.root.destroy()

    # ---------------- Settings Menu ----------------
    
    def settings_menu(self):
        self.root.bind("<Escape>", lambda e: self.main_menu())
        clear_ui(self.root)
        self.clear_game_objects()

        self.canvas = tk.Canvas(self.root, width=menu_width, height=menu_height, bg="black")
        self.canvas.pack()

        self.canvas.create_text(menu_width/2, menu_height/4, text="Settings",
                                font=("Helvetica", 60, "bold"), fill="white")

        back_btn = tk.Button(self.root, text="Back to Main Menu", font=("Helvetica", 15, "bold"),
                             width=18, height=1, bg="red", command=self.main_menu)
        back_btn.place(relx=0.5, rely=0.5, anchor="center")

    # ---------------- Pause Menu ----------------
    
    def pause_menu(self, event=None):
        self.running = False
        self.root.bind("<Escape>", lambda e: self.resume_game())

        self.pause_overlay = tk.Canvas(self.root, width=pause_width, height=pause_height, bg="grey5", highlightthickness=0)
        self.pause_overlay.place(relx = 0.5, rely = 0.5, anchor = "center")

        self.pause_overlay.create_text(pause_width/2, (pause_height - 90) / 2,
                                       text="Game Paused",
                                       font=("Helvetica", 40, "bold"),
                                       fill="white")
        
        resume_btn = tk.Button(self.pause_overlay, text="Resume",
                               font=("Helvetica", 15, "bold"),
                               width=10, height=1, bg="green",
                               command=self.resume_game)

        reset_btn = tk.Button(self.pause_overlay, text="Reset",
                              font=("Helvetica", 15, "bold"),
                              width=10, height=1, bg="orange",
                              command=self.start_game)

        main_menu_btn = tk.Button(self.pause_overlay, text="Main Menu",
                                  font=("Helvetica", 15, "bold"),
                                  width=10, height=1, bg="red",
                                  command=self.main_menu)

        resume_btn.place(relx=0.2, rely=0.7, anchor="center")
        reset_btn.place(relx=0.5, rely=0.7, anchor="center")
        main_menu_btn.place(relx=0.8, rely=0.7, anchor="center")

    def resume_game(self):
        self.root.bind("<Escape>", lambda e: self.pause_menu())
        self.pause_overlay.destroy()
        del self.pause_overlay            
        
        self.running = True
        self.last_time = time.perf_counter()
        self.loop()

    # ---------------- Main Game Loop ----------------
    
    def begin_round(self):
        self.running = True
        self.last_time = time.perf_counter()
        self.root.bind("<Escape>", lambda e: self.pause_menu())
        self.loop()
        
    def loop(self):
        if not hasattr(self, 'canvas') or not self.canvas.winfo_exists():
            self.running = False
            
        if not self.running:
            return
    
        now = time.perf_counter()
        self.dt = now - self.last_time
        self.last_time = now
            
        for paddle in Paddle.List:
            if paddle.ai_enabled:
                paddle.update_ai()
            else:
                x = y = 0
                if paddle.up in self.keys_down:
                    y -= 1
                if paddle.down in self.keys_down:
                    y += 1
                if paddle.left in self.keys_down:
                    x -= 1
                if paddle.right in self.keys_down:
                    x += 1
                paddle.update(x, y)
                
        self.ball.update()
        self.root.after(int(1000/FPS), self.loop)

    def move_object(self, obj, next_x0, next_y0):
        # ---------- Top / Bottom Walls (Clamp) ---------
        if next_y0 < 0:
            next_y0 = 0
            
        if next_y0 + obj.height > app_height:
            next_y0 = app_height - obj.height
        
        # ---------- Left / Right Walls (Ball: Score, Paddle: Clamp) ---------
        if next_x0 < 0:
            if obj == self.ball:
                self.direction = 1
                self.on_score(self.p2)
                return
            else:
                next_x0 = 0
            
        if next_x0 + obj.width > app_width:
            if obj == self.ball:
                self.direction = -1
                self.on_score(self.p1)
                return
            else:
                next_x0 = app_width - obj.width

        # --------------- Move Object --------------
        obj.x0, obj.y0, obj.x1, obj.y1 = next_x0, next_y0, next_x0 + obj.width, next_y0 + obj.height
        self.canvas.coords(obj.id, obj.x0, obj.y0, obj.x1, obj.y1)

    def detect_collisions(self, item1, item2):
        return
        
    def on_score(self, paddle):
        self.running = False
        self.on_score_text = self.canvas.create_text(app_width/2, app_height/2,
                                       text=f"{paddle.color1} scored!",
                                       font=("Helvetica", 60, "bold"),
                                       fill=f"{paddle.color1}")
        paddle.score += 1
        paddle.canvas.itemconfigure(paddle.score_text, text=f"{paddle.color1}: {paddle.score}")
        self.rally_value = 0
        self.pause(2, self.reset_round)

    def reset_round(self):
        self.canvas.delete(self.on_score_text)
        for obj in self.resettable:
            obj.reset()
            
        self.rally_value = 0
        self.canvas.itemconfigure(self.rally_text, text=f"Rally: {self.rally_value}")

        self.countdown(3, self.begin_round)

    # ---------------- Input ----------------
    
    def key_press(self, event):
        self.keys_down.add(event.keysym)

    def key_release(self, event):
        self.keys_down.discard(event.keysym)

    # ---------------- Game Utilities ----------------
    
    def countdown(self, seconds, on_finish=None):
        self.countdown_value = seconds
        self.on_finish = on_finish
        self.countdown_text = self.canvas.create_text(
            app_width / 2,
            app_height / 2,
            text=f"{self.countdown_value}",
            font=("Helvetica", 80, "bold"),
            fill="red")

        self.root.after(1000, self.countdown_step)

    def countdown_step(self):
        if self.countdown_value > 1:
            self.countdown_value -= 1
            self.canvas.itemconfigure(self.countdown_text, text=f"{self.countdown_value}")
            self.root.after(1000, self.countdown_step)

        elif self.countdown_value == 1:
            self.countdown_value = 0
            self.canvas.itemconfigure(self.countdown_text, text="GO!", fill="green")
            self.root.after(1000, self.countdown_step)

        else:
            self.canvas.delete(self.countdown_text)
            if self.on_finish:
                self.on_finish()
                
    def pause(self, seconds, on_finish=None):
        self.running = False
        self.root.after(int(seconds * 1000), on_finish)

    def clear_game_objects(self):
        Ball.List.clear()
        Paddle.List.clear()
        self.objects.clear()
        self.resettable.clear()


# ------------------ Ball ------------------

class Ball:

    List = []
    
    def __init__(self, game, diameter, speed, color):
        Ball.List.append(self)
        self.game = game
        self.canvas = game.canvas
        
        self.diameter = self.width = self.height = diameter
        self.speed = speed
        self.color = color
        
        self.max_x = app_width - self.diameter
        self.max_y = app_height - self.diameter
        self.init_x0 = self.max_x / 2
        self.init_y0 = self.max_y / 2
        self.init_x1 = self.init_x0 + self.diameter
        self.init_y1 = self.init_y0 + self.diameter
        
        self.vx = random.choice([1, -1]) * self.speed
        self.vy = random.choice([1, -1]) * self.speed
        
        self.id = self.canvas.create_oval(self.init_x0, self.init_y0, self.init_x1, self.init_y1, fill=color)
        self.x0, self.y0, self.x1, self.y1 = self.canvas.coords(self.id)
        
        self.last_paddle = None

        self.speed_text = self.canvas.create_text(app_width / 2, 85,
                                                  text="Ball Speed: 0 pps",
                                                  font=("Helvetica", 10),
                                                  fill=color)
        
    def update(self):
        # ---------------- Current Position ----------------
        x0, y0, x1, y1 = self.canvas.coords(self.id)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

        # ---------------- Predict Movement ----------------
        dt = self.game.dt
        next_x0 = x0 + self.vx * dt
        next_y0 = y0 + self.vy * dt
        next_x1 = next_x0 + self.diameter
        next_y1 = next_y0 + self.diameter
        
        if abs(self.vx) < min_speed:
            ratio = min_speed / abs(self.vx)
            self.vx *= ratio
            self.vy *= ratio
            
        # ------------------ Collisions ------------------
        
        # -------------------- Paddles --------------------
        for paddle in Paddle.List:
            if (next_x1 > paddle.x0 and
                next_x0 < paddle.x1 and
                next_y1 > paddle.y0 and
                next_y0 < paddle.y1):

                if self.last_paddle is not paddle:
                    self.game.rally_value += 1
                    self.canvas.itemconfigure(self.game.rally_text, text=f"Rally: {self.game.rally_value}")
                    
                self.last_paddle = paddle
                
                # -------- Penetration Depths & Direction --------
                overlap_left   = next_x1 - paddle.x0
                overlap_right  = paddle.x1 - next_x0
                overlap_top    = next_y1 - paddle.y0
                overlap_bottom = paddle.y1 - next_y0
                
                min_x = min(overlap_left, overlap_right)
                min_y = min(overlap_top, overlap_bottom)

                # ------------- Left / Right Edges -------------
                if min_x < min_y:

                    if self.vx < 0:
                        next_x0 = paddle.x1 + overlap_right
                        next_x1 = next_x0 + self.diameter
                        direction = 1
                        
                    elif self.vx > 0:
                        next_x0 = paddle.x0 - overlap_left - self.diameter
                        next_x1 = next_x0 + self.diameter
                        direction = -1

                    # --------------- Angle ---------------
                    paddle_center = paddle.y0 + paddle.height / 2
                    ball_center = (next_y0 + next_y1) / 2

                    offset = (ball_center - paddle_center) / (paddle.height / 2)
                    offset = max(-1, min(1, offset))

                    angle = math.sin(offset * half_pi) * max_bounce_angle
                    speed = math.hypot(self.vx, self.vy) + self.speed / 20

                    self.vx = speed * math.cos(angle) * direction
                    self.vy = speed * math.sin(angle)

                    # --------------- SPIN ---------------                    
                    spin = paddle.vy * spin_factor
                    spin = max(-max_spin, min(max_spin, spin))
                    
                    self.vy += spin
                    
                # ------------- Top / Bottom Edges -------------
                elif min_y < min_x:
                    
                    if self.vy < 0:
                        next_y0 = paddle.y1 + overlap_bottom
                        next_y1 = next_y0 + self.diameter
                        direction = 1
                        
                    elif self.vy > 0:
                        next_y0 = paddle.y0 - overlap_top - self.diameter
                        next_y1 = next_y0 + self.diameter
                        direction = -1

                    # --------------- Angle ---------------
                    paddle_center = paddle.x0 + paddle.width / 2
                    ball_center = (next_x0 + next_x1) / 2

                    offset = (ball_center - paddle_center) / (paddle.width / 2)
                    offset = max(-1, min(1, offset))

                    angle = math.sin(offset * half_pi) * max_bounce_angle
                    speed = math.hypot(self.vx, self.vy) + self.speed / 20

                    self.vx = speed * math.cos(angle) * direction
                    self.vy = speed * math.sin(angle)

                    # --------------- SPIN ---------------                    
                    spin = paddle.vx * spin_factor
                    spin = max(-max_spin, min(max_spin, spin))
                    
                    self.vx += spin
                    
                # ----------------- Corners ------------------
                else:
                    if overlap_left < overlap_right:
                        next_x0 = paddle.x0 - overlap_left - self.diameter
                    elif overlap_right < overlap_left:
                        next_x0 = paddle.x1 + overlap_right
                        
                    if overlap_top < overlap_bottom:
                        next_y0 = paddle.y0 - overlap_top - self.diameter
                    elif overlap_bottom < overlap_top:
                        next_y0 = paddle.y1 + overlap_bottom
                        
                    next_x1 = next_x0 + self.diameter
                    next_y1 = next_y0 + self.diameter
                    
                    self.vx *=  1
                    self.vy *= 1

        # ----------- Top / Bottom Walls (Bounce) -----------
        if next_y0 < 0:
            next_y0 = -next_y0
            next_y1 = next_y0 + self.diameter
            self.vy *= -1

        elif next_y1 > app_height:
            next_y0 = 2 * self.max_y - next_y0
            next_y1 = next_y0 + self.diameter
            self.vy *= -1

        # ----------- Left / Right Walls (Score) -----------
        if next_x0 < 0:
            self.game.direction = 1
            self.game.on_score(self.game.p2)
            return

        elif next_x0 > self.max_x:
            self.game.direction = -1
            self.game.on_score(self.game.p1)
            return
                
        # ------------------ Commit final position ------------------
        self.x0 = next_x0
        self.y0 = next_y0
        self.x1 = next_x0 + self.diameter
        self.y1 = next_y0 + self.diameter
        self.canvas.coords(self.id, self.x0, self.y0, self.x1, self.y1)

        speed = math.hypot(self.vx, self.vy)
        self.canvas.itemconfigure(
            self.speed_text,
            text=f"Ball Speed: {abs(int(speed))} pps")
        
    def reset(self):
        self.canvas.coords(self.id, self.init_x0, self.init_y0, self.init_x1, self.init_y1)        
        self.vx = self.game.direction * self.speed
        self.vy = random.choice([1, -1]) * self.speed
        self.last_paddle = None
        self.canvas.itemconfigure(self.speed_text, text="Ball Speed: 0 pps")
        
# ------------------ Paddle ------------------

class Paddle:

    List = []
    
    def __init__(self, game, width, height, up, down, left, right, color1, color2, x=None, y=None):
        Paddle.List.append(self)
        self.game = game
        self.canvas = game.canvas
        
        self.width = width
        self.height = height
        self.speed = 600
        self.vx = self.vy = 0

        self.up = up
        self.down = down
        self.left = left
        self.right = right
        self.color1 = color1
        self.color2 = color2

        if x:
            self.init_x0 = x
        else:
            self.init_x0 = (app_width - self.width) / 2
            
        if y:
            self.init_y0 = y
        else:
            self.init_y0 = (app_height - self.height) / 2
            
        self.init_x1 = self.init_x0 + self.width
        self.init_y1 = self.init_y0 + self.height

        self.id = self.canvas.create_rectangle(self.init_x0, self.init_y0, self.init_x1, self.init_y1, fill=color1)
        self.x0, self.y0, self.x1, self.y1 = self.canvas.coords(self.id)
        
        self.score = 0
        self.score_text = self.canvas.create_text(app_width/2 - 0.5*(app_width/2 - x), 50,
                                                  text=f"{color1}: 0",
                                                  font=("Helvetica", 50, "bold"),
                                                  fill=f"{color1}")

        # ------------------ AI Settings ------------------
        self.ai_enabled = True
        self.ai_difficulty = 1.5
        self.ai_timer = 0
        
        self.toggle_ai = tk.Button(text = "AI Enabled" if self.ai_enabled else "AI Disabled",
                                      font = ("Helvetica", 20, "bold"),
                                      fg="black" if self.ai_enabled else "gray",
                                      bg=self.color1 if self.ai_enabled else self.color2,
                                      command = self.toggle_ai_state)

        self.toggle_ai.place(x = app_width/2 - 0.9*(app_width/2 - x), y=50, anchor="center")
        
    def update(self, x, y):
        # ---------------- Previous Position ----------------
        prev_x0, prev_y0, prev_x1, prev_y1 = self.canvas.coords(self.id)
        
        # ---------------- Predict Movement ----------------
        self.vx = x * self.speed
        self.vy = y * self.speed
          
        dt = self.game.dt
        dx = self.vx * dt
        dy = self.vy * dt
        
        next_x0 = prev_x0 + dx
        next_y0 = prev_y0 + dy

        self.game.move_object(self, next_x0, next_y0)
        
    def reset(self):
        self.canvas.coords(self.id, self.init_x0, self.init_y0, self.init_x1, self.init_y1)
        self.canvas.itemconfigure(self.score_text, text=f"{self.color1}: {self.score}")

    # ---------------- AI Logic ----------------
    def update_ai(self):
        # ------------ Reaction Time ------------
        self.ai_timer -= self.game.dt
        if self.ai_timer > 0:
            return
        self.ai_timer = random.uniform(0.01, 0.05)           
        
        # ------------ Previous Position ------------
        prev_x0, prev_y0, prev_x1, prev_y1 = self.canvas.coords(self.id)

        # ----------- Predict Ball Movement -----------
        ball = self.game.ball
        predicted_ball_y = self.predict_ball_y(ball, prev_x1)
        predicted_ball_center = predicted_ball_y + ball.diameter / 2
        paddle_center = (prev_y0 + prev_y1) / 2
        error = predicted_ball_center - paddle_center

        self.vx = 0
        self.vy = max(-1, min(1, error / 100)) * self.speed * self.ai_difficulty
        
        dt = self.game.dt
        dx = self.vx * dt
        dy = self.vy * dt
        
        next_x0 = prev_x0 + dx
        next_y0 = prev_y0 + dy

        # -------------- Add Spin --------------
        if abs(error) < 50:
            self.vy += random.choice([-1, 1]) * self.speed

        self.game.move_object(self, next_x0, next_y0)

    def predict_ball_y(self, ball, prev_x1):
        if ball.vx == 0:
            return ball.y0
        
        time_to_reach = (prev_x1 - ball.x0) / ball.vx

        if time_to_reach < 0 or time_to_reach > 1.5:
            return ball.y0

        predicted_ball_y = ball.y0 + ball.vy * time_to_reach

        while predicted_ball_y < 0 or predicted_ball_y > app_height - ball.diameter:
            if predicted_ball_y < 0:
                predicted_ball_y *= -1
            else:
                predicted_ball_y = 2 * ball.max_y - predicted_ball_y

        return predicted_ball_y

    def toggle_ai_state(self):
        self.ai_enabled = not self.ai_enabled
        self.toggle_ai.config(text = "AI Enabled" if self.ai_enabled else "AI Disabled",
                                      fg="black" if self.ai_enabled else "gray",
                                      bg=self.color1 if self.ai_enabled else self.color2)
        
# ------------------ Run Game ------------------
if __name__ == "__main__":
    game = Game()
