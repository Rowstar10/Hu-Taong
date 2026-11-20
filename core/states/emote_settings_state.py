from core.states.gameplay_settings_state import GameplaySettingsState

class EmoteSettingsState(GameplaySettingsState):
    """Settings > Controls > Emotes (1.9, Rowan: "Move the emotes section into its own settings
    menu inside control settings"): the controller button for each quick emote, beside the key
    that sends it.  Setting a button works as on Controls (and swaps with one already used)."""
    NAME = "emote_settings"

    def draw(self, screen):
        super(GameplaySettingsState, self).draw(screen)
        self.app.renderer.draw_emote_settings_menu(self, screen)

    def reset(self):
        self.confirm_reset("Reset the emotes' buttons?", self.app.settings.gameplay.reset_emotes)
