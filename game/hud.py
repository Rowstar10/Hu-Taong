import tkinter as tk
import math
from config import APP_WIDTH, APP_HEIGHT

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
        self.p1_btn = tk.Button(self.root, font=("Helvetica", 20, "bold"),
                                command=lambda: self.toggle_ai(self.game.p1))
        self.p2_btn = tk.Button(self.root, font=("Helvetica", 20, "bold"),
                                command=lambda: self.toggle_ai(self.game.p2))

        self.widgets += [self.p1_btn, self.p2_btn]

        self.p1_btn.place(x=40, y=50, anchor="w")
        self.p2_btn.place(x=APP_WIDTH-40, y=50, anchor="e")

        self.refresh_button(self.p1_btn, self.game.p1)
        self.refresh_button(self.p2_btn, self.game.p2)

        self.p1_score_id = self.canvas.create_text(
            250, 50, text=f"{self.game.p1.color1}: {self.game.p1.score}",
            font=("Helvetica", 40, "bold"),
            fill=self.game.p1.color1, anchor="w")

        self.p2_score_id = self.canvas.create_text(
            APP_WIDTH - 250, 50, text=f"{self.game.p2.color1}: {self.game.p2.score}",
            font=("Helvetica", 40, "bold"),
            fill=self.game.p2.color1, anchor="e")

        self.rally_id = self.canvas.create_text(
            APP_WIDTH / 2, 50, text="Rally: 0",
            font=("Helvetica", 30, "bold"),
            fill="white", anchor="center")

        self.speed_id = self.canvas.create_text(
            APP_WIDTH / 2, 85, text="Ball Speed: 0 pps",
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
