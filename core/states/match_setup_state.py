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
        """Practice's choices (1.9): against the wall or the AI, scoring on or off, and a talisman."""
        m = self.app.settings.match
        if key in ("practice_wall", "practice_ai"):
            m.practice_wall = key == "practice_wall"
            if m.practice_talisman not in m.practice_talismans():
                m.practice_talisman = 0             # (Soul Swap, against the wall)
        if key in ("practice_scoring_on", "practice_scoring_off"):
            m.practice_scoring = key == "practice_scoring_on"
        for suffix, step in (("_left", -1), ("_right", 1)):
            if key == "cycle_practice_talisman" + suffix:
                offered = m.practice_talismans()
                here = offered.index(m.practice_talisman) if m.practice_talisman in offered else 0
                m.practice_talisman = offered[(here + step) % len(offered)]

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

            practising = gameplay.practice
            if key == "opponent_ai":
                gameplay.vs_ai, gameplay.practice = True, False
            if key == "opponent_human":
                gameplay.vs_ai, gameplay.practice = False, False
            if key == "opponent_practice":
                gameplay.practice = True
            if key == "opponent_online":
                self.push_state("online")
            self.handle_practice_key(key)
            if gameplay.practice != practising:
                self._laid = None                   # Practice's choices come or go: lay out again

            if gameplay.vs_ai or gameplay.practice:     # the paddle choice only matters against the AI (or alone)
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
