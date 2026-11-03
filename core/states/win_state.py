import pygame

from config import BASE_W, BASE_H
from core import save_data
from render import theme
from core.states.base_state import State

class WinState(State):
    NAME = "win"
    is_menu = True
    is_overlay = True
    
    def __init__(self, app, p1, p2, winner, loser):
        super().__init__(app)

        sound_manager = self.app.sound_manager
        self.app.stats.record_match(p1, winner, loser)
        save_data.save(self.app)
        if not winner.ai_enabled and loser.ai_enabled:
            sound_manager.play("you_win.wav")
            sound_manager.set_mood("victory")
            
        elif not loser.ai_enabled and winner.ai_enabled:
            sound_manager.play("you_lose.wav")
            sound_manager.set_mood("defeat")
            
        else:
            snd = "red_wins.wav" if winner == p1 else "blue_wins.wav"
            sound_manager.play(snd)
            sound_manager.set_mood("victory")

        self.p1 = p1
        self.p2 = p2
        self.winner = winner
        self.loser = loser
        self.lost = not loser.ai_enabled and winner.ai_enabled
        self.ui_cols = 2

        # Fan out from beside the panel, so the result stays readable
        tint = "red" if winner == p1 else "blue"
        count = 6 if self.lost else 22
        self.app.fx.burst(BASE_W / 2 - 430, BASE_H / 2, count, 64, tint, arc = (2.2, 4.1))
        self.app.fx.burst(BASE_W / 2 + 430, BASE_H / 2, count, 64, tint, arc = (-.95, .95))

    def draw(self, screen):
        super().draw(screen)
        title = f"{self.winner.color1} Wins!"
        
        header = [(f"{self.p1.color1}: ", theme.color(self.p1.color1)),
                  (f"{self.p1.score}      ", theme.PARCHMENT),
                  (f"{self.p2.color1}: ", theme.color(self.p2.color1)),
                  (f"{self.p2.score}", theme.PARCHMENT)]
        
        buttons = [("play_again", "Play Again?", theme.GREEN, theme.GREEN_HOVER),
                   ("continue", "Endless Mode...", theme.BLUE, theme.BLUE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]

        self.app.renderer.draw_overlay(
            self,
            screen,
            title=title, header=header, buttons=buttons,
            title_size=0.1, header_size=0.05, btn_size=0.045,
            title_color=theme.color(self.winner.color1), mark="败" if self.lost else "胜")
        
    def handle_event(self, event):
        super().handle_event(event)

        gameplay = self.app.settings.gameplay
        sound_manager = self.app.sound_manager
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
            mx, my = mouse_pos
            
            for key, rect in self.ui_hitboxes.items():
                if rect.collidepoint(mouse_pos):
                    if key == "play_again":
                        from core.states.game_state import GameState
                        game_state = self.app.state_manager.get_state(GameState)
                        
                        if game_state:
                            action = lambda: (game_state.restart(),
                                              self.pop_state(mute = True),
                                              self.pop_state(mute = True),
                                              sound_manager.play("enter_state.wav"),
                                              sound_manager.set_mood("game"))
                            
                            self.push_state("confirm_choice", action = action, header = "Play Again?", mute = True)
                            
                    if key == "continue":
                        from core.states.game_state import GameState
                        game_state = self.app.state_manager.get_state(GameState)
                        
                        def enter_endless_mode():
                            gameplay.winning_score_index = gameplay.winning_scores.index("Endless Mode")
                            
                        if game_state:
                            action = lambda: (enter_endless_mode(),
                                              self.pop_state(mute = True),
                                              self.pop_state(mute = True),
                                              game_state.game.reset_round(),
                                              sound_manager.play("enter_state.wav"),
                                              sound_manager.set_mood("game"))

                            self.push_state("confirm_choice", action = action, header = "Enter Endless Mode?", mute = True)
                        
                    if key == "settings":
                        self.push_state("settings")
                        
                    if key == "main_menu":
                        action = lambda: (self.app.sound_manager.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                        self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
