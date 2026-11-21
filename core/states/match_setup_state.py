import pygame

from core import save_data
from core.states.base_state import State
from core.states.match_controls import MatchControls

class MatchSetupState(MatchControls, State):
    NAME = "match_setup"
    is_menu = True

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_match_setup_menu(self, screen)

    def start_match(self):
        save_data.save(self.app)
        self.app.fx.swarm()
        self.set_state("game", mute = True)

    def handle_practice_key(self, key):
        """Practice Mode's choice (1.9): against the AI or a wall."""
        m = self.app.settings.match
        if key in ("practice_wall", "practice_ai"):
            m.vs_wall = key == "practice_wall"

    def handle_event(self, event):
        super().handle_event(event)

        gameplay = self.app.settings.match

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.start_match()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "opponent_ai":
                gameplay.vs_ai = True
            if key == "opponent_human":
                gameplay.vs_ai = False
            if key == "opponent_online":
                self.push_state("online")

            if gameplay.vs_ai:      # the paddle choice and the wall only matter against the AI
                self.handle_practice_key(key)
                if key == "side_red":
                    gameplay.play_as_blue = False
                if key == "side_blue":
                    gameplay.play_as_blue = True

            # The rules most matches change (Rowan, 1.9), greyed out where they don't count: the
            # AI's level only against the AI, and Points to Win only where a match can be won
            if key in ("cycle_ai_left", "cycle_ai_right") and gameplay.vs_ai and not gameplay.vs_wall:
                step = 1 if key.endswith("right") else -1
                gameplay.ai_difficulty = (gameplay.ai_difficulty + step) % len(gameplay.ai_difficulties)
            if key in ("cycle_ai_style_left", "cycle_ai_style_right") and gameplay.vs_ai and not gameplay.vs_wall:
                step = 1 if key.endswith("right") else -1           # (AI Style, under AI Level: Rowan, 1.9)
                gameplay.ai_style = (gameplay.ai_style + step) % len(gameplay.ai_styles)
            if key in ("cycle_win_score_left", "cycle_win_score_right") and gameplay.scoring \
                    and not (gameplay.vs_ai and gameplay.vs_wall):
                step = 1 if key.endswith("right") else -1
                gameplay.winning_score_index = (gameplay.winning_score_index + step) % len(gameplay.winning_scores)

            self.handle_match_key(key)          # the court
            if key == "open_match_settings":
                self.push_state("match")
            if key == "open_powerups":                      # (Choose Talismans and Choose Modes, under
                self.push_state("powerups")                 # Points to Win: Rowan, 1.9)
            if key == "open_modes":
                self.push_state("powerups", view = "modes")

            if key == "start_match":
                self.start_match()
            if key == "back":
                self.pop_state()
