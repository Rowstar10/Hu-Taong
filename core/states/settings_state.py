import pygame

from core import save_data
from core.states.base_state import State

class SettingsState(State):
    NAME = "settings"
    is_menu = True

    def exit(self, **kwargs):
        super().exit(**kwargs)
        save_data.save(self.app)
        
    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_settings_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            
            if key == "gameplay":
                self.push_state("gameplay")
            if key == "display":
                self.push_state("display")
            if key == "audio":
                self.push_state("audio")
            if key == "back":
                self.pop_state()
