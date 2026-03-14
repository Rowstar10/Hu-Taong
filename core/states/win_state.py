import pygame

from render import theme
from core.states.base_state import State
from core.state_registry import StateRegistry

@StateRegistry.register_state("win")
class WinState(State):
    is_overlay = True
    
    def __init__(self, app, p1, p2, winner):
        super().__init__(app)
        self.app.sound.play("you_win.wav")
        s = self.app.settings.audio
        music = s.win_track[s.win_music]
        self.app.sound.play_music(music, music_type = "win")
        
        self.p1 = p1
        self.p2 = p2
        self.winner = winner
        self.ui_cols = 2

    def exit(self, **kwargs):
        super().exit(**kwargs)
        

    def draw(self, screen):
        super().draw(screen)
        W, H = self.app.base_w, self.app.base_h
        
        panel_w = int(W * 0.4)
        panel_h = int(H * 0.6)
        panel_rect = pygame.Rect(W // 2 - panel_w // 2,
                                 H // 2 - panel_h // 2,
                                 panel_w, panel_h)

        title = f"{self.winner} Wins!"
        header = f"{self.p1.color1}: {self.p1.score} | {self.p2.color1}: {self.p2.score}"
        buttons = [("play_again", "Play Again?", theme.GREEN, theme.GREEN_HOVER),
                   ("continue", "Continue Match...", theme.BLUE, theme.BLUE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]

        self.app.renderer.draw_overlay(
            self,
            screen,
            title=title, header=header, buttons=buttons,
            title_size=0.3, header_size=0.06, btn_size=0.055,
            header_y=0.45, btn_y=0.8,
            title_color=self.winner,
            panel_rect=panel_rect)
        
    def handle_event(self, event):
        super().handle_event(event)

        s = self.app.settings.gameplay
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
            mx, my = mouse_pos
            
            for key, rect in self.ui_hitboxes.items():
                if rect.collidepoint(mouse_pos):
                    if key == "play_again":
                        self.push_state("confirm_choice", action = lambda: self.set_state("game"), header = "Play Again?")
                            
                    if key == "continue":
                        if s.winning_scores[s.winning_score_index] == max(s.winning_scores):
                            return
                        
                        s.winning_score_index = (s.winning_score_index + 1) % len(s.winning_scores)
                        
                        self.pop_state(mute = True)
                        self.app.sound.play("enter_state.wav")
                        
                        s = self.app.settings.audio
                        music = s.game_track[s.game_music]
                        self.app.sound.play_music(music, music_type = "game")
                        
                        from core.states.game_state import GameState
                        game_state = self.app.state_manager.get_state(GameState)

                        if game_state:
                            game_state.game.message_text = ""
                            game_state.game.reset_round()
                        
                    if key == "settings":
                        self.push_state("settings")
                        
                    if key == "main_menu":
                        action = lambda: (self.app.sound.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                        self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
                        self.app.sound.play("exit_state.wav")
