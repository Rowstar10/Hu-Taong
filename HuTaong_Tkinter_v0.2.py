import tkinter as tk
import sys, time, random, math, winsound
from pathlib import Path

# ------------------ Directory ------------------

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent
    
RESOURCE_DIR = BASE_DIR / "Resources"
SOUND_DIR = RESOURCE_DIR / "Sounds"
IMAGE_DIR = RESOURCE_DIR / "Images"

# ------------------ Constants ------------------

FPS = 100

menu_width = 500
menu_height = 600

app_width = 1500
app_height = 800

pause_width = 500
pause_height = 200

epsilon = 0.001
half_pi = math.pi/2
max_bounce_angle = math.radians(60)
max_cpf = 5 # (Maximum collisions per frame)

# Body Types
DYNAMIC = 0
KINEMATIC = 1
STATIC = 2

# ------------------- Helpers -------------------

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

def play_sound(name):
    winsound.PlaySound(
        str(SOUND_DIR / name),
        winsound.SND_FILENAME | winsound.SND_ASYNC)
    
def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def reflect_in_range(y, lo, hi):
    i = 0
    while y < lo or y > hi:
        if y < lo:
            y = lo + (lo - y)
        else:
            y = hi - (y - hi)
        i += 1
    return y, i

def lerp(a, b, t):
    return a + (b - a) * t

# ------------------ The App ------------------

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hu Taong")
        icon = tk.PhotoImage(file = IMAGE_DIR / "icon.png")
        self.root.iconphoto(True, icon)

        self.keys_down = set()
        self.root.bind_all("<KeyPress>", self.key_press)
        self.root.bind_all("<KeyRelease>", self.key_release)

        self.screen_manager = Screen_Manager(self.root)

        self.show_main_menu()

        self.root.mainloop()
        
    # -------------- Inputs --------------
    def key_press(self, event):
        self.keys_down.add(event.keysym)

    def key_release(self, event):
        self.keys_down.discard(event.keysym)

    # --------- Screen switching ----------
    def show_main_menu(self):
        self.screen_manager.set(Main_Menu(self))

    def show_settings_menu(self):
        self.screen_manager.set(Settings_Menu(self))

    def start_hu_taong(self):
        game = Hu_Taong(self)
        self.screen_manager.set(Game_Screen(self, game))

    def clear_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def quit(self):
        self.root.destroy()
        
# ------------------ Screen Manager ------------------

class Screen_Manager:
    def __init__(self, root):
        self.root = root
        self.current = None

    def set(self, screen):
        if self.current:
            self.current.hide()
        self.current = screen
        self.current.show()

# -------------- Generic Screen Template --------------

class Screen:
    def __init__(self, app, width = menu_width, height = menu_height):
        self.app = app
        self.root = app.root
        self.width = width
        self.height = height

    def show(self):
        center_window(self.root, self.width, self.height)
        self.app.clear_ui()

    def hide(self):
        self.app.clear_ui()

# ------------------ Main Menu Screen ------------------

class Main_Menu(Screen):
    def show(self):
        super().show()

        canvas = tk.Canvas(self.root, width = self.width, height = self.height, bg = "black")
        self.canvas = canvas
        canvas.pack()

        canvas.create_text(self.width/2, self.height/6, text = "Hu Taong!",
                           font = ("Helvetica", 60, "bold"), fill = "red")

        canvas.create_text(self.width/2, (self.height - 140)/2, text = "Main Menu",
                           font = ("Helvetica", 40, "bold"), fill = "white")

        tk.Button(self.root, text = "Play Game", font = ("Helvetica", 20, "bold"), width = 10, height = 1, bg = "green",
                  command = self.app.start_hu_taong).place(relx = 0.5, y = (self.height + 50) / 2, anchor = "center")

        tk.Button(self.root, text = "Settings", font = ("Helvetica", 20, "bold"), width = 10, height = 1, bg = "orange",
                  command = self.app.show_settings_menu).place(relx = 0.5, y = (self.height + 200) / 2, anchor = "center")
 
        tk.Button(self.root, text = "Quit Game", font = ("Helvetica", 20, "bold"), width = 10, height = 1, bg = "red",
                  command = self.app.quit).place(relx = 0.5, y = (self.height + 350) / 2, anchor = "center")

        self.root.bind("<Escape>", lambda e: self.app.quit())

# ------------------ Settings Menu Screen ------------------

class Settings_Menu(Screen):
    def show(self):
        super().show()

        canvas = tk.Canvas(self.root, width = self.width, height = self.height, bg = "black")
        self.canvas = canvas
        canvas.pack()
        
        canvas.create_text(self.width/2, self.height/4, text = "Settings",
                           font = ("Helvetica", 60, "bold"), fill = "white")

        tk.Button(self.root, text = "Back to Main Menu", font = ("Helvetica", 15, "bold"),
                  width = 18, height = 1, bg = "red",
                  command = self.app.show_main_menu).place(relx = 0.5, rely = 0.5, anchor = "center")

        self.root.bind("<Escape>", lambda e: self.app.show_main_menu())

# ------------------ Game Screen ------------------

class Game_Screen(Screen):
    def __init__(self, app, game, width = app_width, height = app_height):
        super().__init__(app, width, height)
        self.game = game
        self.pause_overlay = None

    def show(self):
        super().show()
        self.game.start()
        self.root.bind("<Escape>", self.toggle_pause_overlay)   

    def hide(self):
        self.game.stop()
        super().hide()

    def toggle_pause_overlay(self, event = None):
        if self.pause_overlay is None:
            self.pause_overlay = PauseOverlay(self.app, self, on_resume = self.resume,
                                              on_reset = self.reset,
                                              on_main_menu = self.main_menu)
            self.pause()
            self.pause_overlay.show()
        else:
            self.resume()

    def pause(self):
        self.game.pause()   
        
    def resume(self):
        if self.pause_overlay:
            self.pause_overlay.hide()
            self.pause_overlay = None
        self.game.paused = False
        self.game.resume()

    def reset(self):
        if self.pause_overlay:
            self.pause_overlay.hide()
            self.pause_overlay = None
        self.game.reset_game()

    def main_menu(self):
        self.game.stop()
        self.app.show_main_menu()

# ------------------ HUD Overlay ------------------

class HUDOverlay:
    def __init__(self, app, game):
        self.app = app
        self.game = game
        self.root = app.root
        self.canvas = game.canvas

        self.widgets = []
        self.items = []
        self.last = {}

    def show(self):
        # --- Buttons ---
        self.p1_btn = tk.Button(self.root, font=("Helvetica", 20, "bold"),
                                command=lambda: self.toggle_ai(self.game.p1))
        self.p2_btn = tk.Button(self.root, font=("Helvetica", 20, "bold"),
                                command=lambda: self.toggle_ai(self.game.p2))

        self.widgets += [self.p1_btn, self.p2_btn]

        self.p1_btn.place(x=40, y=50, anchor="w")
        self.p2_btn.place(x=app_width-40, y=50, anchor="e")

        self.refresh_button(self.p1_btn, self.game.p1)
        self.refresh_button(self.p2_btn, self.game.p2)

        self.p1_score_id = self.canvas.create_text(
            250, 50, text=f"{self.game.p1.color1}: {self.game.p1.score}",
            font=("Helvetica", 40, "bold"),
            fill=self.game.p1.color1, anchor="w")

        self.p2_score_id = self.canvas.create_text(
            app_width - 250, 50, text=f"{self.game.p2.color1}: {self.game.p2.score}",
            font=("Helvetica", 40, "bold"),
            fill=self.game.p2.color1, anchor="e")

        self.rally_id = self.canvas.create_text(
            app_width / 2, 50, text="Rally: 0",
            font=("Helvetica", 30, "bold"),
            fill="white", anchor="center")

        self.speed_id = self.canvas.create_text(
            app_width / 2, 85, text="Ball Speed: 0 pps",
            font=("Helvetica", 10),
            fill="white", anchor="center")

        self.items += [self.p1_score_id, self.p2_score_id, self.rally_id, self.speed_id]

        self.last = {
            "p1_score": self.game.p1.score,
            "p2_score": self.game.p2.score,
            "rally": getattr(self.game.ball, "rally_value", 0),
            "speed": 0}

    def hide(self):
        for w in self.widgets:
            try:
                w.destroy()
            except tk.TclError:
                pass
        self.widgets.clear()

        for item in self.items:
            try:
                self.canvas.delete(item)
            except tk.TclError:
                pass
        self.items.clear()

    def toggle_ai(self, paddle):
        paddle.toggle_ai_state()
        self.refresh_buttons()

    def refresh_buttons(self):
        self.refresh_button(self.p1_btn, self.game.p1)
        self.refresh_button(self.p2_btn, self.game.p2)

    def refresh_button(self, btn, paddle):
        if paddle.ai_enabled:
            btn.config(text="AI Enabled", fg="black", bg=paddle.color1)
        else:
            btn.config(text="AI Disabled", fg="gray", bg=paddle.color2)

    def update(self):
        p1s = self.game.p1.score
        p2s = self.game.p2.score
        rally = getattr(self.game.ball, "rally_value", 0) # try changing to rally = self.game.ball.rally_value

        speed = int(math.hypot(self.game.ball.vx, self.game.ball.vy))

        if p1s != self.last["p1_score"]:
            self.canvas.itemconfigure(self.p1_score_id, text=f"{self.game.p1.color1}: {p1s}")
            self.last["p1_score"] = p1s

        if p2s != self.last["p2_score"]:
            self.canvas.itemconfigure(self.p2_score_id, text=f"{self.game.p2.color1}: {p2s}")
            self.last["p2_score"] = p2s

        if rally != self.last["rally"]:
            self.canvas.itemconfigure(self.rally_id, text=f"Rally: {rally}")
            self.last["rally"] = rally

        if speed != self.last["speed"]:
            self.canvas.itemconfigure(self.speed_id, text=f"Ball Speed: {speed} pps")
            self.last["speed"] = speed

# ------------------ Pause Overlay ------------------

class PauseOverlay:
    def __init__(self, app, game_screen, on_resume, on_reset, on_main_menu):
        self.app = app
        self.game_screen = game_screen
        self.root = app.root
        self.on_resume = on_resume
        self.on_reset = on_reset
        self.on_main_menu = on_main_menu
        self.canvas = None

    def show(self, width = pause_width, height = pause_height):
        canvas = tk.Canvas(self.root, width = width, height = height,
                                bg = "grey5", highlightthickness = 0)
        self.canvas = canvas
        canvas.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        canvas.create_text(width/2, (height - 90)/2,
                                text = "Game Paused",
                                font = ("Helvetica", 40, "bold"),
                                fill = "white")

        tk.Button(canvas, text = "Resume", font = ("Helvetica", 15, "bold"),
                  width = 10, height = 1, bg = "green",
                  command = self.on_resume).place(relx = 0.2, rely = 0.7, anchor = "center")

        tk.Button(canvas, text = "Reset", font = ("Helvetica", 15, "bold"),
                  width = 10, height = 1, bg = "orange",
                  command = self.on_reset).place(relx = 0.5, rely = 0.7, anchor = "center")

        tk.Button(canvas, text = "Main Menu", font = ("Helvetica", 15, "bold"),
                  width = 10, height = 1, bg = "red",
                  command = self.on_main_menu).place(relx = 0.8, rely = 0.7, anchor = "center")

    def hide(self):
        if self.canvas and self.canvas.winfo_exists():
            self.canvas.destroy()
        self.canvas = None

# ------------------ Game Template ------------------

class GameBase:
    def __init__(self, app, width = app_width, height = app_height):
        self.app = app
        self.root = app.root
        self.canvas = None

        self.width = width
        self.height = height
        
        self.objects = []
        self.running = False
        self.paused = False
        self.last_time = 0

        # countdown state
        self.in_countdown = False
        self.countdown_seconds = 0
        self.countdown_on_finish = None
        self.countdown_text = None

        # scheduling
        self.epoch = 0
        self.after_ids = set()
        self.loop_after_id = None
        self.countdown_after_id = None

    def start(self):        
        self.canvas = tk.Canvas(self.root, width = self.width, height = self.height, bg = "black")
        self.canvas.pack()
        
        self.objects.clear()
        self.build_world()
        self.hud = HUDOverlay(self.app, self)
        self.hud.show()
        
        self.running = False
        self.paused = False
        self.in_countdown = False
        
        self.countdown(seconds = 3)

    def stop(self):
        self.running = False
        self.paused = False
        self.in_countdown = False
        self.bump_epoch()
        self.hud.hide()
        self.app.clear_ui()

    def pause(self):
        self.paused = True
        self.running = False

    def resume(self):
        if not self.canvas or not self.canvas.winfo_exists():
            return
        if self.paused or self.in_countdown:
            return
        self.running = True
        self.last_time = time.perf_counter()
        self.loop()

    def reset_game(self):
        self.stop()
        self.start()

    def build_world(self):
        raise NotImplementedError

    def loop(self):
        # Emergency Stop
        if not self.running:
            return
        if not self.canvas or not self.canvas.winfo_exists():
            self.running = False
            return

        # Time since last frame
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now

        # Update game & loop
        self.update(dt)
        self.loop_after_id = self.after(int(1000 / FPS), self.loop)

    def update(self, dt):
        Physics.step(self, dt)
        self.hud.update()

    def countdown(self, seconds, stop_gameplay = True, on_finish = None, overlay = True,
                  x = None, y = None, size = None):
        self.cancel_after(self.countdown_after_id)
        self.countdown_after_id = None

        self.in_countdown = True
        self.countdown_seconds = int(seconds)
        self.countdown_stop_gameplay = stop_gameplay
        self.countdown_on_finish = on_finish
        self.countdown_overlay = overlay
        
        if stop_gameplay:
            self.running = False
            
        if overlay:
            x = self.width/2 if x is None else x
            y = self.height/2 if y is None else y
            size = 80 if size is None else size
            self.countdown_text = self.canvas.create_text(x, y, text = str(self.countdown_seconds),
                                                 font = ("Helvetica", size, "bold"),
                                                 fill = "red")
                
        self.countdown_after_id = self.after(1000, self.tick_countdown)

    def tick_countdown(self):
        if not self.canvas or not self.canvas.winfo_exists():
            return
        
        if self.paused:
            self.cancel_after(self.countdown_after_id)
            self.countdown_after_id = self.after(1000, self.tick_countdown)
            return

        s = self.countdown_seconds
        
        if s > 1:
            s -=  1
            self.countdown_seconds = s
            if self.countdown_overlay:
                self.canvas.itemconfigure(self.countdown_text, text = str(s))
            self.countdown_after_id = self.after(1000, self.tick_countdown)
            return
            
        if s == 1:
            self.countdown_seconds = 0
            if self.countdown_overlay:
                self.canvas.itemconfigure(self.countdown_text, text = "GO!", fill = "green")
            self.countdown_after_id = self.after(1000, self.tick_countdown)
            return

        self.in_countdown = False
        
        if self.countdown_overlay:
            try:
                self.canvas.delete(self.countdown_text)
            except tk.TclError:
                pass
        if self.countdown_on_finish:
            on_finish()
        if self.countdown_stop_gameplay and not self.paused:
            self.resume()

    def after(self, ms, fn):
        epoch = self.epoch

        def wrapped():
            if epoch != self.epoch:
                return
            fn()

        aid = self.root.after(ms, wrapped)
        self.after_ids.add(aid)
        return aid

    def cancel_after(self, aid):
        if not aid:
            return
        try:
            self.root.after_cancel(aid)
        except tk.TclError:
            pass
        self.after_ids.discard(aid)

    def cancel_all_afters(self):
        for aid in list(self.after_ids):
            try:
                self.root.after_cancel(aid)
            except tk.TclError:
                pass
            self.after_ids.discard(aid)
        self.loop_after_id = None
        self.countdown_after_id = None

    def bump_epoch(self):
        self.epoch += 1
        self.cancel_all_afters()
                
# ------------------ Hu Taong Game ------------------

class Hu_Taong(GameBase):                        
    def build_world(self):
        # Walls & Separator
        self.top_wall = Wall(self, -100, -100, app_width + 100, 0)
        self.bottom_wall = Wall(self, -100, app_height, app_width + 100, app_height + 100)
        self.left_wall = Wall(self, -100, -100, 0, app_height + 100, is_goal = False)
        self.right_wall = Wall(self, app_width, -100, app_width + 100, app_height + 100, is_goal = False)
        self.seperator = Wall(self, app_width/2, -100, app_width/2, app_height + 100)

        # Players & Ball
        self.p1 = Paddle(self, width = 30, height = 180,
                         x = 30, y = (app_height - 180)/2,
                         up = "w", down = "s", left = "a", right = "d",
                         color1 = "Red", color2 = "Orange Red", sound = "Hu.wav")

        self.p2 = Paddle(self, width = 30, height = 180,
                         x = app_width - 60, y = (app_height - 180)/2,
                         up = "Up", down = "Down", left = "Left", right = "Right",
                         color1 = "Blue", color2 = "Royal Blue", sound = "Tao.wav")
        
        self.ball = Ball(self, diameter = 50,
                         x = (app_width - 50)/2,
                         y = (app_height - 50)/2)

    def on_score(self, obj, data):
        self.pause()
        play_sound("euugh.wav")
        nx, ny = data["normal"]

        if nx  ==  1:
            self.p2.score +=  1
            self.canvas.itemconfigure(self.p2.score_text, text = f"{self.p2.color1}: {self.p2.score}")
            msg = f"{self.p2.color1} scored!"
            msg_color = self.p2.color1
        elif nx  ==  -1:
            self.p1.score +=  1
            self.canvas.itemconfigure(self.p1.score_text, text = f"{self.p1.color1}: {self.p1.score}")
            msg = f"{self.p1.color1} scored!"
            msg_color = self.p1.color1
        else:
            return

        text_id = self.canvas.create_text(app_width/2, app_height/2, text = msg,
                                          font = ("Helvetica", 60, "bold"),
                                          fill = msg_color)

        obj.spawn_vx = nx * obj.speed
        obj.spawn_vy = random.choice([1, -1]) * obj.speed

        self.root.after(2000, lambda: (self.canvas.delete(text_id), self.reset_round()))

    def reset_round(self):
        for obj in self.objects:
            obj.reset()
        self.hud.update()
        self.countdown(seconds = 3)

# ------------------ Game Object ------------------

class GameObject:
    body_type = None
    has_inputs = False
    soft_inputs = False
    can_score = False

    def __init__(self, game, width, height, x, y,
                 vx = 0, vy = 0, spin = 0,
                 mass = 1, inv_mass = None,
                 restitution = 0,
                 friction = 0,
                 linear_drag = 0.01,
                 angular_drag = 0.01):
    
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
        self.soft_control_k = 8

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

        a = 1 - math.exp(-self.soft_control_k * dt) if self.soft_controls else 1
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
        
# ------------------ World Walls ------------------

class Wall(GameObject):
    body_type = STATIC
    has_inputs = False

    def __init__(self, game, x0, y0, x1, y1, is_goal = False):
        width = x1 - x0
        height = y1 - y0
        super().__init__(game, width, height, x0, y0,
                         inv_mass = 0, restitution = 0.8)
        
        self.id = None
        self.is_goal = is_goal
        
# ------------------ Ball ------------------

class Ball(GameObject):
    body_type = DYNAMIC
    can_score = True
    
    def __init__(self, game, diameter, x, y,
                 speed = 500, color = "white"):
        
        super().__init__(game, diameter, diameter, x, y,
                         vx = random.choice([1, -1]) * speed,
                         vy = random.choice([1, -1]) * speed,
                         restitution = 0.4)
        
        self.diameter = diameter
        self.speed = speed
        self.color = color
        self.rally_value = 0
        self.last_paddle = None
        
        self.id = self.canvas.create_oval(self.x0, self.y0, self.x1, self.y1, fill = color)

    def on_contact(self, other, data):
        nx, ny = data["normal"]
        if isinstance(other, Paddle):
            paddle = other
            
            if self.last_paddle is not paddle:
                play_sound(paddle.sound)
                self.rally_value +=  1
                self.vx += nx * self.speed * lerp(0.1, 2, self.rally_value/100)
                self.vy += ny * self.speed * lerp(0.1, 2, self.rally_value/100)
                self.game.hud.update()

            self.last_paddle = paddle

        if isinstance(other, Wall) and other.is_goal:
            self.game.on_score(self, data)
            return

    def reset(self):
        super().reset()        
        self.last_paddle = None
        self.rally_value = 0
        
# ------------------ Paddle ------------------

class Paddle(GameObject):
    body_type = KINEMATIC
    has_inputs = True
    soft_controls = True
        
    def __init__(self, game, width, height, x, y,
                 up, down, left, right, color1, color2,
                 sound, speed = 1500):
    
        super().__init__(game, width, height, x, y,
                         inv_mass = 0.1,
                         restitution = 0.8,
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
        self.ai_difficulty = 10 # out of 10
        self.ai_mode = "OFFENSE" # OFFENSE / DEFENSE / CONTROL / PANIC / RECOVERY
        
        d = clamp(int(self.ai_difficulty), 1, 10)
        W = self.game.width
        self.reaction_time      = lerp(0.25, 0.05, (d - 1) / 9)
        self.foresight_dist     = lerp(W / 2, 5 * W / 8, (d - 1) / 9) # Only reacts to incoming ball within this distance
        self.max_pred_bounces   = 0 if d in [1, 2, 3, 4] else (1 if d in [5, 6, 7, 8] else 2)
        self.panic_dist         = lerp(100, 300, (d - 1) / 9)
        self.strike_dist        = lerp(200, 500, (d - 1) / 9) # dvx = 50% of maximum speed at strike distance
        self.arrive_dist        = lerp(500, 200, (d - 1) / 9) # dvy begins to decrease at arrive distance

        self.ai_timer = 0
        self.target = None
        self.ai_tar_x = self.home_x
        self.ai_tar_y = self.home_y
        
    def on_contact(self, other, data):
        if other.body_type !=  DYNAMIC:
            return

        nx, ny = data["normal"]
        speed = math.hypot(other.vx, other.vy)
        
        # -------------- Bouncy Center / Flat Edges --------------
        if nx !=  0:
            center = (self.y0 + self.y1) / 2
            other_center = (other.y0 + other.y1) / 2
            offset = (other_center - center) / (self.height / 2)
            offset = max(-1, min(1, offset))

            angle = offset * max_bounce_angle
            other.vx = -nx * speed * math.cos(angle)
            other.vy = speed * math.sin(angle)
            
        if ny !=  0:
            center = (self.x0 + self.x1) / 2
            other_center = (other.x0 + other.x1) / 2
            offset = (other_center - center) / (self.width / 2)
            offset = max(-1, min(1, offset))
            
            angle = offset * max_bounce_angle
            other.vx = speed * math.sin(angle)
            other.vy = -ny * speed * math.cos(angle)

    # ---------------- AI Logic (MINE) ----------------------------------------------------------------------------------------------------------------------------------------
    def ai_input(self, dt): # --------------------------------------------------------------------------------------------------------------------------------------------  
        W, H = self.game.width, self.game.height
        pad_cx  = (self.x0 + self.x1) / 2
        pad_cy  = (self.y0 + self.y1) / 2
        
        # -------------- Reaction Time --------------
        self.ai_timer -= dt
                
        if self.ai_timer <= 0.0:
            self.ai_timer = self.reaction_time

            # ---------- Determine the best ball to target ----------
            balls = [obj for obj in self.game.objects if isinstance(obj, Ball)]
            
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
                dx = ball_cx - pad_cx
                dy = ball_cy - pad_cy
                dist_to_ball = math.hypot(dx, dy)
                
                in_panic = dist_to_ball < self.panic_dist

                if self.is_left:
                    defend_x = self.x1 + ball.width / 2
                    ball_behind = ball_cx < (self.x0 - r - 10)
                else:
                    defend_x = self.x0 - ball.width / 2
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
                        tar_x = ball_cx
                    else:
                        tar_x = self.home_x + 120 if self.is_left else self.home_x - 120
                        
                    if can_predict:
                        tar_y = lerp(pad_cy, pred_cy, 0.8)
                    else:
                        tar_y = clamp(ball_cy, H/2 - self.height/2, H/2 + self.height/2)
                        
                elif (ball_cx < W/2 and self.is_left) or (ball_cx > W/2 and not self.is_left):
                    tar_x = ball_cx
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
        if self.ai_enabled:
            d = clamp(int(self.ai_difficulty), 1, 10)
            self.restitution = lerp(0.1, 0.5, (d - 1) / 9)
        else:
            self.restitution = 0.5

# -------------- Physics --------------

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
        while remaining > 0 and cpf < max_cpf:
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
                elif obj1  ==  game.seperator and not isinstance(obj2, Paddle):
                    continue
                elif obj2  ==  game.seperator and not isinstance(obj1, Paddle):
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
            a.on_contact(b, data)
            b.on_contact(a, data)
            return

        impulse_total = -(1 + res) * rvn / im_total
        impulse_x, impulse_y = impulse_total * nx, impulse_total * ny
        
        if a.body_type !=  STATIC:
            a.vx +=  impulse_x * im_a
            a.vy +=  impulse_y * im_a

        if b.body_type !=  STATIC:
            b.vx -=  impulse_x * im_b
            b.vy -=  impulse_y * im_b
         
        a.on_contact(b, data)
        b.on_contact(a, data)
        Physics.positional_shove(a, b, nx, ny)
        
    @staticmethod
    def clamp_to_world(obj):               
        if obj.body_type !=  KINEMATIC:
            return
        
        if obj.x0 < 0:
            (obj.x0, obj.x1, obj.vx) = (0, obj.width, 0)
        if obj.x1 > app_width:
            (obj.x1, obj.x0, obj.vx) = (app_width, app_width-obj.width, 0)
        if obj.y0 < 0:
            (obj.y0, obj.y1, obj.vy) = (0, obj.height, 0)
        if obj.y1 > app_height:
            (obj.y1, obj.y0, obj.vy) = (app_height, app_height-obj.height, 0)

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
        
# ------------------ Run Game ------------------
if __name__  ==  "__main__":
    app = App()
