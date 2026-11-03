import pygame

from core.states.base_state import State

class InterfaceSettingsState(State):
    NAME = "interface"
    is_menu = True

    TOGGLES = ("tooltips", "ai_banter", "screen_shake", "ball_trail", "auto_pause", "hide_cursor")
    CYCLES = {"hud": "hud_options", "effects": "effects_options", "countdown": "countdown_options"}

    def __init__(self, app):
        super().__init__(app)
        self.listening = None        # the key binding waiting for a new key, e.g. "p1_up"

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_interface_settings_menu(self, screen)

    def handle_event(self, event):
        settings = self.app.settings.interface

        # While a binding is waiting, the next key press is the new key (Esc cancels)
        if self.listening and event.type == pygame.KEYDOWN:
            if event.key != pygame.K_ESCAPE:
                settings.bind(self.listening, event.key)
                self.app.sound_manager.play("click.wav")
            self.listening = None
            return

        super().handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            listening, self.listening = self.listening, None

            if key and key.startswith("toggle_") and key[7:] in self.TOGGLES:
                name = key[7:]
                setattr(settings, name, not getattr(settings, name))

            for name, options in self.CYCLES.items():
                count = len(getattr(settings, options))
                if key == f"cycle_{name}_left":
                    setattr(settings, name, (getattr(settings, name) - 1) % count)
                if key == f"cycle_{name}_right":
                    setattr(settings, name, (getattr(settings, name) + 1) % count)

            if key and key.startswith("key_"):
                field = key[4:]
                self.listening = None if listening == field else field

            if key == "reset_defaults":
                self.confirm_reset("Reset interface settings?", self.app.reset_interface_settings)

            if key == "back":
                self.pop_state()
