import pygame

from core.state_registry import StateRegistry
from core.states.base_state import State

@StateRegistry.register_state("main_menu")
class MainMenuState(State):
    is_menu = True

    def enter(self, **kwargs):
        audio = self.app.settings.audio
        sound = self.app.sound
        music = audio.menu_track[audio.menu_music]
        sound.play("startup.wav")
        sound.play_music(music, music_type = "menu")
    
    def exit(self, **kwargs):
        super().exit(**kwargs)
        
    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_main_menu(self, screen)

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.set_state("game", mute = True)
            
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.push_state("confirm_choice", action = lambda: self.app.quit(), header = "Quit to desktop?", mute = True)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            if key == "play":
                self.set_state("game", mute = True)
            if key == "settings":
                self.push_state("settings")
            if key == "prompt_quit":
                self.push_state("confirm_choice", action = lambda: self.app.quit(), header = "Quit to desktop?", mute = True)
