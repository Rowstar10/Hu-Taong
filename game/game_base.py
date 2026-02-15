import tkinter as tk
import time
from config import FPS, APP_WIDTH, APP_HEIGHT
from game.physics import Physics
from game.hud import HUDOverlay

# ------------------ Game Template ------------------

class GameBase:
    def __init__(self, app, width = APP_WIDTH, height = APP_HEIGHT):
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

    def countdown(self, seconds, pause_gameplay = True, on_finish = None, overlay = True,
                  x = None, y = None, size = None):
        self.cancel_after(self.countdown_after_id)
        self.countdown_after_id = None

        self.in_countdown = True
        self.countdown_seconds = int(seconds)
        self.countdown_pause_gameplay = pause_gameplay
        self.countdown_on_finish = on_finish
        self.countdown_overlay = overlay
        
        if pause_gameplay:
            self.pause()
            
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
        if self.countdown_pause_gameplay:
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
