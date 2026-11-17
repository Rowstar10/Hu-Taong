import pygame

from core.states.base_state import State

class GameplaySettingsState(State):
    """Settings > Gameplay: your own controls.  The keys, Auto-Pause, and on a phone the touch
    steering and vibration."""
    NAME = "gameplay"
    is_menu = True

    TOGGLES = ("auto_pause", "vibration")
    CYCLES = {"touch_steer": "touch_steer_options", "touch_sensitivity": "touch_sensitivity_options"}  # (a phone's)

    def __init__(self, app):
        super().__init__(app)
        self.listening = None        # the key binding waiting for a new key, e.g. "p1_up"

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_gameplay_settings_menu(self, screen)

    def handle_event(self, event):
        controls = self.app.settings.gameplay

        # While a binding is waiting, the next key press is the new key (Esc cancels)
        if self.listening and event.type == pygame.KEYDOWN:
            if event.key != pygame.K_ESCAPE:
                controls.bind(self.listening, event.key)
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
                setattr(controls, name, not getattr(controls, name))

            for name, options in self.CYCLES.items():
                count = len(getattr(controls, options))
                if key == f"cycle_{name}_left":
                    setattr(controls, name, (getattr(controls, name) - 1) % count)
                if key == f"cycle_{name}_right":
                    setattr(controls, name, (getattr(controls, name) + 1) % count)

            if key and key.startswith("key_"):
                field = key[4:]
                self.listening = None if listening == field else field

            if key == "reset_defaults":
                self.confirm_reset("Reset gameplay settings?", self.app.reset_gameplay_settings)

            if key == "back":
                self.pop_state()
