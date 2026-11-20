import pygame

from core.states.base_state import State

class InterfaceSettingsState(State):
    """Settings > UI: menus, the HUD, tooltips and (1.9, from Gameplay) Auto-Pause."""
    NAME = "interface"
    is_menu = True

    TOGGLES = ("tooltips", "ai_banter", "hide_cursor", "friend_emotes", "auto_pause")
    CYCLES = {"hud": "hud_options", "instant_replay": "instant_replay_options"}

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_interface_settings_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        settings = self.app.settings.interface

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))

            if key and key.startswith("toggle_") and key[7:] in self.TOGGLES:
                name = key[7:]
                setattr(settings, name, not getattr(settings, name))

            for name, options in self.CYCLES.items():
                count = len(getattr(settings, options))
                if key == f"cycle_{name}_left":
                    setattr(settings, name, (getattr(settings, name) - 1) % count)
                if key == f"cycle_{name}_right":
                    setattr(settings, name, (getattr(settings, name) + 1) % count)

            if key == "reset_defaults":
                self.confirm_reset("Reset UI settings?", self.app.reset_interface_settings)

            if key == "back":
                self.pop_state()
