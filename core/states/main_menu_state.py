import pygame

from core.states.base_state import State

class MainMenuState(State):
    NAME = "main_menu"
    is_menu = True

    def enter(self, **kwargs):
        audio = self.app.settings.audio
        sound_manager = self.app.sound_manager
        music = audio.menu_track[audio.menu_music]
        sound_manager.play("startup.wav")
        sound_manager.play_music(music, music_type = "menu")
    
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
