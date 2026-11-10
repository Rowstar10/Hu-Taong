import pygame

from core.states.base_state import State

class PowerUpsSettingsState(State):
    NAME = "powerups"
    is_menu = True

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_powerups_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        settings = self.app.settings.gameplay

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            count = len(settings.powerup_rate_options)

            if key == "toggle_powerups":
                settings.powerups = not settings.powerups
            if key == "cycle_powerup_rate_left":
                settings.powerup_rate = (settings.powerup_rate - 1) % count
            if key == "cycle_powerup_rate_right":
                settings.powerup_rate = (settings.powerup_rate + 1) % count

            if key in ("all_pu_on", "all_pu_off"):
                for name in [attr for attr in vars(settings) if attr.startswith("pu_")]:
                    setattr(settings, name, key == "all_pu_on")

            # each power-up's own switch, e.g. "toggle_pu_frost"
            if key and key.startswith("toggle_pu_"):
                name = key[len("toggle_"):]
                setattr(settings, name, not getattr(settings, name))

            if key == "reset_defaults":
                self.confirm_reset("Reset power-ups?", settings.reset_powerups)

            if key == "back":
                self.pop_state()
