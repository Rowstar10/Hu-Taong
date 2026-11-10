import pygame

from core import files, save_data
from core.stats import Stats
from core.states.base_state import State

class StatsState(State):
    NAME = "stats"
    is_menu = True

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_stats_menu(self, screen)

    # ---------------- Export and import ----------------

    def toast(self, text):
        self.app.renderer.show_toast(text)

    def export_stats(self):
        name = "Hu Taong stats.json"
        path = self.app.choose_file(True, "Export stats", name, [("Hu Taong stats", "*.json")])
        if path is None:
            return                                  # cancelled
        fallback = path is False
        if fallback:
            path = files.fallback_path(name)
        try:
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(self.app.stats.export_text(), encoding = "utf-8")
        except OSError as e:
            self.toast(f"Couldn't export: {e.strerror or e}")
            return
        self.toast(f"Stats exported to {'Documents/Hu Taong/' if fallback else ''}{path.name}")

    def import_stats(self):
        path = self.app.choose_file(False, "Import stats", "", [("Hu Taong stats", "*.json")])
        if path is None:
            return
        if path is False:
            path = files.newest("*.json")
            if path is None:
                self.toast("No stats file found in Documents/Hu Taong")
                return
        try:
            stats = Stats.read_export(path.read_text(encoding = "utf-8"))
        except (OSError, UnicodeDecodeError):
            stats = None
        if stats is None:
            self.toast(f"{path.name} isn't a Hu Taong stats file")
            return

        def replace():
            self.app.stats.reset()
            self.app.stats.load_dict(stats)
            save_data.save(self.app)
            self.pop_state(mute = True)
            self.toast(f"Stats imported from {path.name}")
        games = stats.get("matches", 0)
        self.push_state("confirm_choice", action = replace, mute = True,
                        header = f"Replace your stats with these ({games} match{'es' if games != 1 else ''})?")

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "export_stats":
                self.export_stats()
            if key == "import_stats":
                self.import_stats()
            if key == "open_replays":
                self.push_state("replays")
            if key == "reset_stats":
                action = lambda: (self.app.stats.reset(),
                                  save_data.save(self.app),
                                  self.pop_state(mute = True))
                self.push_state("confirm_choice", action = action, header = "Reset all stats?", mute = True)
            if key == "back":
                self.pop_state()
