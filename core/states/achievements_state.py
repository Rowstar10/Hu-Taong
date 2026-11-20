import pygame

from core.states.base_state import State


class AchievementsState(State):
    """The achievements (1.9): each one earned, and how to earn the rest.  From the Stats screen."""
    NAME = "achievements"
    is_menu = True

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_achievements_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            if key == "reset_defaults":
                self.confirm_reset("Reset all achievements?", self.app.achievements.reset)
            if key == "back":
                self.pop_state()
