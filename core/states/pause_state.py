import pygame

from core.states.game_state import GameState
from core.states.base_state import State
from render import theme

class PauseState(State):
    NAME = "pause"
    is_menu = True
    is_overlay = True

    def __init__(self, app):
        super().__init__(app)
        self.game_state = self.app.state_manager.get_state(GameState)
        self.ui_cols = 2

    def enter(self, **kwargs):
        sound_manager = self.app.sound_manager
        sound_manager.play("startup2.wav")
        sound_manager.multiplier = 0.1
        sound_manager.update_music_volume()
    
    def exit(self, **kwargs):
        super().exit(**kwargs)
        sound_manager = self.app.sound_manager
        sound_manager.multiplier = 1
        sound_manager.update_music_volume()
        
    def update(self, dt):
        pass

    def draw(self, screen):
        super().draw(screen)
        W, H = self.app.base_w, self.app.base_h
        
        panel_w = int(W * 0.45)
        panel_h = int(H * 0.25)
        panel_rect = pygame.Rect(W // 2 - panel_w // 2,
                                 H // 2 - panel_h // 2,
                                 panel_w, panel_h)
        
        buttons = [("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                   ("reset", "Reset", theme.BLUE, theme.BLUE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]
        
        self.app.renderer.draw_overlay(self, screen,
                                       title = "Paused", buttons = buttons,
                                       title_size = 0.35,
                                       title_y = 0.25, btn_y = 0.8,
                                       panel_rect = panel_rect)

        
        if self.game_state:
            self.app.hud.draw_ai_button(self, self.app.virtual, self.game_state.game.p1, left=True)
            self.app.hud.draw_ai_button(self, self.app.virtual, self.game_state.game.p2, left=False)

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.pop_state(mute = True)
            self.app.sound_manager.play("shutdown.wav")
            
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state(mute = True)
            self.app.sound_manager.play("shutdown.wav")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sound_manager = self.app.sound_manager
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "p1_ai":
                self.game_state.game.p1.ai_enabled = not self.game_state.game.p1.ai_enabled
                    
            if key == "p2_ai":
                self.game_state.game.p2.ai_enabled = not self.game_state.game.p2.ai_enabled

            if key == "resume":
                self.pop_state(mute = True)
                self.app.sound_manager.play("shutdown.wav")
                
            if key == "reset":                                
                if self.game_state:
                    action = lambda: (self.game_state.restart(),
                                      self.pop_state(mute = True),
                                      self.pop_state(mute = True),
                                      sound_manager.play("enter_state.wav"))
                    
                    self.push_state("confirm_choice", action = action, header = "Reset Game?", mute = True)
                    
            if key == "settings":
                self.push_state("settings")
                
            if key == "main_menu":
                action = lambda: (sound_manager.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
