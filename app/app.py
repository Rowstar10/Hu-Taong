import tkinter as tk
from config import IMAGE_DIR
from app.screen_manager import Screen_Manager
from app.screens import Main_Menu, Settings_Menu, Game_Screen
from game.hu_taong import Hu_Taong

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
