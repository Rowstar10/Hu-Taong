import pygame

from core.states.base_state import State
from core.states.game_state import GameState
from core.states.match_controls import MatchControls
from core.states.scrolling import Scrolling

class MatchSettingsState(Scrolling, MatchControls, State):
    """Settings > Match: the rules of a match, the same for both players.  Online only the host
    has it (its rules are the match's); opened mid-match, changes come in at the next serve.
    (1.9: it scrolls, where the screen is too small for it at a size that reads.)"""
    NAME = "match"
    is_menu = True

    IN_MATCH_NOTE = "Changes come in at the next serve"

    def __init__(self, app):
        super().__init__(app)
        self.note = self.IN_MATCH_NOTE if app.state_manager.get_state(GameState) else None

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_match_settings_menu(self, screen)

    def handle_event(self, event):
        if self.scroll_event(event):
            return
        super().handle_event(event)
        m = self.app.settings.match

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            self.handle_match_key(key)          # the modes, their timings and the court

            cycles = {"ai": ("ai_difficulty", m.ai_difficulties), "ai_style": ("ai_style", m.ai_styles),
                      "win_score": ("winning_score_index", m.winning_scores),
                      "countdown": ("countdown", m.countdown_options),
                      "powerup_rate": ("powerup_rate", m.powerup_rate_options),
                      "at_once": ("talismans_at_once", m.at_once_options)}
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
            if key == "back":
                self.pop_state()
