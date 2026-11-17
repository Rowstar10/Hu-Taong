import pygame

from core.settings import MatchSettings
from core.states.base_state import State
from core.states.game_state import GameState
from core.states.match_controls import MatchControls

class MatchSettingsState(MatchControls, State):
    """Settings > Match: the rules of a match, the same for both players (online, the host's).

    Opened from Pause it changes the match being played, from its next serve.  Online, the friend
    who joined sees the host's rules here, read only (`read_only`): their own Match settings don't
    play any part in it."""
    NAME = "match"
    is_menu = True

    READ_ONLY_NOTE = "Your friend is hosting: these are their rules, and only they can change them"
    IN_MATCH_NOTE = "Changes come in at the next serve"

    def __init__(self, app, read_only = False):
        super().__init__(app)
        self.read_only = read_only
        self.shown = MatchSettings(app) if read_only else None     # the host's rules, as last heard
        if read_only:
            self.note = self.READ_ONLY_NOTE
        elif app.state_manager.get_state(GameState):
            self.note = self.IN_MATCH_NOTE
        else:
            self.note = None

    def update(self, dt):
        net = self.app.net
        if self.read_only and net is not None and getattr(net, "rules", None):
            self.shown.take_rules(net.rules)

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_match_settings_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        m = self.app.settings.match

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            if key == "back":
                self.pop_state()
                return
            if self.read_only:
                if key:
                    self.app.renderer.show_toast("Only your friend, who's hosting, can change the rules")
                return

            self.handle_match_key(key)          # the modes, their timings and the court

            cycles = {"ai": ("ai_difficulty", m.ai_difficulties), "ai_style": ("ai_style", m.ai_styles),
                      "win_score": ("winning_score_index", m.winning_scores),
                      "countdown": ("countdown", m.countdown_options),
                      "powerup_rate": ("powerup_rate", m.powerup_rate_options)}
            for name, (field, options) in cycles.items():
                for suffix, step in (("_left", -1), ("_right", 1)):
                    if key == f"cycle_{name}{suffix}":
                        setattr(m, field, (getattr(m, field) + step) % len(options))

            toggles = {"toggle_win_by_two": "win_by_two", "toggle_middle_wall": "middle_wall",
                       "toggle_adaptive_ai": "adaptive_ai", "toggle_powerups": "powerups"}
            if key in toggles:
                setattr(m, toggles[key], not getattr(m, toggles[key]))

            if key == "open_powerups":
                self.push_state("powerups")
            if key == "open_ball_paddles":
                self.push_state("ball_paddles")
            if key == "reset_defaults":
                self.confirm_reset("Reset match settings?", self.app.reset_match_settings)
