import pygame

from core import save_data
from core.states.base_state import State

class StatsState(State):
    NAME = "stats"
    is_menu = True

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_stats_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "reset_stats":
                action = lambda: (self.app.stats.reset(),
                                  save_data.save(self.app),
                                  self.pop_state(mute = True))
                self.push_state("confirm_choice", action = action, header = "Reset all stats?", mute = True)
            if key == "back":
                self.pop_state()
