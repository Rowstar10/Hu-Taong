import pygame

from core.states.base_state import State

class GameplaySettingsState(State):
    """Settings > Controls ("Gameplay" till 1.9): your own controls.  The keys, a controller's
    buttons and stick, the mouse, and on a phone the touch steering and vibration.  (Auto-Pause
    moved to UI in 1.9, and the emotes' buttons to a page of their own: EmoteSettingsState.)"""
    NAME = "gameplay"
    is_menu = True

    TOGGLES = ("vibration", "mouse_steer")
    CYCLES = {"touch_steer": "touch_steer_options", "touch_sensitivity": "touch_sensitivity_options",  # (a phone's)
              "pad_stick": "PAD_STICKS", "pad_deadzone": "PAD_DEADZONES", "mouse_side": "SIDES"}

    def __init__(self, app):
        super().__init__(app)
        self.listening = None        # the key binding waiting for a new key, e.g. "p1_up"
        self.listening_pad = None    # the controller action waiting for a button (1.9), e.g. "pause"

    def stop_listening_pad(self):
        self.listening_pad = None
        self.app.gamepads.listen = None

    def exit(self, **kwargs):
        self.stop_listening_pad()
        super().exit(**kwargs)

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_gameplay_settings_menu(self, screen)

    def reset(self):
        self.confirm_reset("Reset controls?", self.app.reset_gameplay_settings)

    def handle_event(self, event):
        controls = self.app.settings.gameplay

        if self.listening_pad and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.stop_listening_pad()               # (Esc cancels a controller button too)
            return

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

            if key in ("cycle_pad_first_left", "cycle_pad_first_right"):
                controls.pad_first = 1 - controls.pad_first
            if key and key.startswith("pad_") and key[4:] in controls.PAD_ACTIONS:
                action = key[4:]
                if self.listening_pad == action:
                    self.stop_listening_pad()
                else:
                    def done(button, action = action):
                        controls.bind_pad(action, button)
                        self.listening_pad = None
                        self.app.sound_manager.play("click.wav")
                    self.listening_pad = action
                    self.app.gamepads.listen = (action, done)

            if key == "open_emotes":
                self.stop_listening_pad()
                self.push_state("emote_settings")

            if key == "reset_defaults":
                self.reset()

            if key == "back":
                self.pop_state()
