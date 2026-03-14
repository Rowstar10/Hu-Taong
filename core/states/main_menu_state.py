import pygame

from core.state_registry import StateRegistry
from core.states.base_state import State

@StateRegistry.register_state("main_menu")
class MainMenuState(State):
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        s = self.app.settings.audio
        music = s.menu_track[s.menu_music]
        self.app.sound.play_music(music, music_type = "menu")
    
    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_main_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.push_state("confirm_choice", action = lambda: self.app.quit(), header = "Quit to desktop?", mute = True)
            self.app.sound.play("exit_state.wav")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            if key == "play":
                self.set_state("game", mute = True)
                self.app.sound.play("startup2.wav")
            if key == "settings":
                self.push_state("settings")
            if key == "prompt_quit":
                self.push_state("confirm_choice", action = lambda: self.app.quit(), header = "Quit to desktop?", mute = True)
                self.app.sound.play("exit_state.wav")
