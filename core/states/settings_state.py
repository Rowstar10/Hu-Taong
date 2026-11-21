import pygame

from core import files, save_data
from core.states.base_state import State

class SettingsState(State):
    NAME = "settings"
    is_menu = True

    def __init__(self, app, general = False):
        super().__init__(app)
        self.general = general        # opened by Match settings' More Settings: no Match card (after 1.9)

    # ---------------- Export and import (1.9) ----------------

    KINDS = [("Hu Taong settings", "*.json")]

    def toast(self, text):
        self.app.renderer.show_toast(text)

    def export_settings(self):
        name = "Hu Taong settings.json"
        path = self.app.choose_file(True, "Export settings", name, self.KINDS)
        if path is None:
            return                                  # cancelled
        fallback = path is False
        if fallback:
            path = files.fallback_path(name)
        try:
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(save_data.export_settings_text(self.app), encoding = "utf-8")
        except OSError as e:
            self.toast(f"Couldn't export: {e.strerror or e}")
            return
        self.toast(f"Settings exported to {'Documents/Hu Taong/' if fallback else ''}{path.name}")

    def import_settings(self):
        path = self.app.choose_file(False, "Import settings", "", self.KINDS)
        if path is None:
            return
        if path is False:
            path = files.newest("Hu Taong settings*.json")
            if path is None:
                self.toast("No settings file found in Documents/Hu Taong")
                return
        try:
            data = save_data.read_settings_export(path.read_text(encoding = "utf-8"))
        except (OSError, UnicodeDecodeError):
            data = None
        if data is None:
            self.toast(f"{path.name} isn't a Hu Taong settings file")
            return

        def replace():
            app = self.app
            background = app.settings.display.background
            save_data.apply_settings(app, data)
            app.settings.online.apply()
            app.sound_manager.update_music_volume()
            display = app.settings.display
            if display.background != background and 0 <= display.background < len(display.backgrounds):
                app.show_background(display.backgrounds[display.background])
            save_data.save(app)
            self.pop_state(mute = True)
            self.toast(f"Settings imported from {path.name}")
        self.push_state("confirm_choice", action = replace, mute = True, header = "Replace your settings with these?")

    def exit(self, **kwargs):
        super().exit(**kwargs)
        save_data.save(self.app)
        
    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_settings_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            
            if key == "match":                # (only in a match, and not for the friend who joined: 1.9)
                self.push_state("match")
            if key == "gameplay":
                self.push_state("gameplay")
            if key == "display":
                self.push_state("display")
            if key == "audio":
                self.push_state("audio")
            if key == "interface":
                self.push_state("interface")
            if key == "reset_all":
                self.confirm_reset("Reset ALL settings?", self.app.reset_all_settings)
            if key == "export_settings":
                self.export_settings()
            if key == "import_settings":
                self.import_settings()
            if key == "back":
                self.pop_state()
