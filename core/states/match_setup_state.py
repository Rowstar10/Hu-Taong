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

            if gameplay.vs_ai:      # the paddle choice only matters against the AI
                if key == "side_red":
                    gameplay.play_as_blue = False
                if key == "side_blue":
                    gameplay.play_as_blue = True

            self.handle_match_key(key)          # the modes, their timings and the court
            if key == "open_match_settings":
                self.push_state("match")

            if key == "start_match":
                self.start_match()
            if key == "back":
                self.pop_state()
