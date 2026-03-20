import pygame

from render import theme
from core.states.base_state import State
from core.state_registry import StateRegistry

@StateRegistry.register_state("win")
class WinState(State):
    is_overlay = True
    
    def __init__(self, app, p1, p2, winner, loser):
        super().__init__(app)

        audio = self.app.settings.audio
        sound = self.app.sound
        if not winner.ai_enabled and loser.ai_enabled:
            sound.play("you_win.wav")
            music = audio.win_track[audio.win_music]
            sound.play_music(music, music_type = "win")
            
        elif not loser.ai_enabled and winner.ai_enabled:
            sound.play("you_lose.wav")
            music = audio.lose_track[audio.lose_music]
            sound.play_music(music, music_type = "lose")
            
        else:
            snd = "red_wins.wav" if winner == p1 else "blue_wins.wav"
            sound.play(snd)
            music = audio.win_track[audio.win_music]
            sound.play_music(music, music_type = "win")

        self.p1 = p1
        self.p2 = p2
        self.winner = winner
        self.loser = loser
        self.ui_cols = 2

    def draw(self, screen):
        super().draw(screen)
        W, H = self.app.base_w, self.app.base_h
        
        panel_w = int(W * 0.4)
        panel_h = int(H * 0.6)
        panel_rect = pygame.Rect(W // 2 - panel_w // 2,
                                 H // 2 - panel_h // 2,
                                 panel_w, panel_h)

        title = f"{self.winner.color1} Wins!"
        
        header = [{"word": f"{self.p1.color1}: ", "color": self.p1.color1},
                  {"word": f"{self.p1.score}      ", "color": theme.WHITE},
                  {"word": f"{self.p2.color1}: ", "color": self.p2.color1},
                  {"word": f"{self.p2.score}", "color": theme.WHITE}]
        
        buttons = [("play_again", "Play Again?", theme.GREEN, theme.GREEN_HOVER),
                   ("continue", "Endless Mode...", theme.BLUE, theme.BLUE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]

        self.app.renderer.draw_overlay(
            self,
            screen,
            title=title, header=header, buttons=buttons,
            title_size=0.3, header_size=0.06, btn_size=0.055,
            header_y=0.45, btn_y=0.8,
            title_color=self.winner.color1,
            panel_rect=panel_rect)
        
    def handle_event(self, event):
        super().handle_event(event)

        gameplay = self.app.settings.gameplay
        audio = self.app.settings.audio
        sound = self.app.sound
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
            mx, my = mouse_pos
            
            for key, rect in self.ui_hitboxes.items():
                if rect.collidepoint(mouse_pos):
                    if key == "play_again":
                        from core.states.game_state import GameState
                        game_state = self.app.state_manager.get_state(GameState)
                        
                        if game_state:
                            music = audio.game_track[audio.game_music]
                            action = lambda: (game_state.restart(),
                                              self.pop_state(mute = True),
                                              self.pop_state(mute = True),
                                              sound.play("enter_state.wav"),
                                              sound.play_music(music, music_type = "game"))
                            
                            self.push_state("confirm_choice", action = action, header = "Reset Game?", mute = True)
                            
                    if key == "continue":
                        from core.states.game_state import GameState
                        game_state = self.app.state_manager.get_state(GameState)
                        
                        def enter_endless_mode():
                            gameplay.winning_score_index = gameplay.winning_scores.index("Endless Mode")
                            
                        if game_state:
                            music = audio.game_track[audio.game_music]
                            action = lambda: (enter_endless_mode(),
                                              self.pop_state(mute = True),
                                              self.pop_state(mute = True),
                                              game_state.game.reset_round(),
                                              sound.play("enter_state.wav"),
                                              sound.play_music(music, music_type = "game"))

                            self.push_state("confirm_choice", action = action, header = "Enter Endless Mode?", mute = True)
                        
                    if key == "settings":
                        self.push_state("settings")
                        
                    if key == "main_menu":
                        action = lambda: (self.app.sound.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                        self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
