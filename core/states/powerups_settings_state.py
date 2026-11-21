import pygame

from core.states.base_state import State
from core.states.match_controls import MatchControls, match_rules

class PowerUpsSettingsState(MatchControls, State):
    """The Talismans page (Power-Ups till 1.9), from Match settings' Choose Talismans, and its Modes
    view (Rowan, 1.9), from Choose Modes: the button at the bottom left switches between them."""
    NAME = "powerups"
    is_menu = True

    def __init__(self, app, view = "talismans"):
        super().__init__(app)
        self.view = view if view in ("talismans", "modes") else "talismans"

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_powerups_menu(self, screen)

    def switch_view(self):
        self.view = "modes" if self.view == "talismans" else "talismans"
        self._laid = None                   # (laid out afresh, for the other view)

    def handle_event(self, event):
        super().handle_event(event)
        settings = match_rules(self.app)     # (mid-match, this match's: 1.9)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))

            if key == "switch_view":
                self.switch_view()
                return

            if self.view == "modes":
                if key in ("all_modes_on", "all_modes_off"):
                    for mode in settings.MODES:
                        setattr(settings, "mode_" + mode, key == "all_modes_on")
                self.handle_match_key(key)          # each mode's switch, as in Match settings
                if key == "reset_defaults":
                    self.confirm_reset("Reset modes?", settings.reset_modes)
            else:
                # (The Talismans switch and the spawn rate are on the Match screen only: Rowan's playtest)
                if key in ("all_pu_on", "all_pu_off"):
                    for name in [attr for attr in vars(settings) if attr.startswith("pu_")]:
                        setattr(settings, name, key == "all_pu_on")

                # each talisman's own switch, e.g. "toggle_pu_fire"
                if key and key.startswith("toggle_pu_"):
                    name = key[len("toggle_"):]
                    setattr(settings, name, not getattr(settings, name))

                if key == "reset_defaults":
                    self.confirm_reset("Reset talismans?", settings.reset_powerups)

            if key == "back":
                self.pop_state()
