import tkinter as tk
from config import MENU_WIDTH, MENU_HEIGHT, APP_WIDTH, APP_HEIGHT, PAUSE_WIDTH, PAUSE_HEIGHT
from helpers import center_window

# -------------- Generic Screen Template --------------

class Screen:
    def __init__(self, app, width = MENU_WIDTH, height = MENU_HEIGHT):
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

        canvas = tk.    Canvas(self.root, width = self.width, height = self.height, bg = "black")
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
    def __init__(self, app, game, width = APP_WIDTH, height = APP_HEIGHT):
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
        self.game.paused = True
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

    def show(self, width = PAUSE_WIDTH, height = PAUSE_HEIGHT):
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
