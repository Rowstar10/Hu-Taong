import pygame

from core.state_registry import StateRegistry
from core.states.base_state import State
from core.states.game_state import GameState

@StateRegistry.register_state("gameplay")
class GameplaySettingsState(State):
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        self.dragging_ball_speed = False
        self.dragging_ball_diameter = False
        self.dragging_paddle_speed = False
        self.dragging_paddle_size = False
        
    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_gameplay_settings_menu(self, screen)
        
    def handle_event(self, event):
        super().handle_event(event)
        
        s = self.app.settings.gameplay
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            mx, my = mouse_pos
            key = self.hit_test(mouse_pos)
            
            if key == "cycle_ai_left":
                s.ai_difficulty = (s.ai_difficulty - 1) % len(s.ai_difficulties)
            if key == "cycle_ai_right":
                s.ai_difficulty = (s.ai_difficulty + 1) % len(s.ai_difficulties)
                
            if key == "cycle_win_score_left":
                s.winning_score_index = (s.winning_score_index - 1) % len(s.winning_scores)
            if key == "cycle_win_score_right":
                s.winning_score_index = (s.winning_score_index + 1) % len(s.winning_scores)
            if key == "toggle_win_by_two":
                s.win_by_two = not s.win_by_two
            
            if key == "ball_speed_slider":
                self.dragging_ball_speed = True
                percent = self.update_slider_from_mouse("ball_speed_slider", event)
                s.ball_speed = s.ball_speed_min + percent * s.ball_speed_range
            if key == "paddle_speed_slider":
                self.dragging_paddle_speed = True
                percent = self.update_slider_from_mouse("paddle_speed_slider", event)
                s.paddle_speed = s.paddle_speed_min + percent * s.paddle_speed_range
            if key == "ball_diameter_slider":
                self.dragging_ball_diameter = True
                percent = self.update_slider_from_mouse("ball_diameter_slider", event)
                s.ball_diameter = s.ball_diameter_min + percent * s.ball_diameter_range
            if key == "paddle_size_slider":
                self.dragging_paddle_size = True
                percent = self.update_slider_from_mouse("paddle_size_slider", event)
                s.paddle_height = s.paddle_height_min + percent * s.paddle_height_range
                
            if key == "reset_ball_speed":
                s.ball_speed = s.ball_speed_min + 0.5 * s.ball_speed_range
            if key == "reset_paddle_speed":
                s.paddle_speed = s.paddle_speed_min + 0.5 * s.paddle_speed_range
            if key == "reset_ball_diameter":
                s.ball_diameter = s.ball_diameter_min + 0.5 * s.ball_diameter_range
            if key == "reset_paddle_size":
                s.paddle_height = s.paddle_height_min + 0.5 * s.paddle_height_range
                s.paddle_width = s.paddle_width_min + 0.5 * s.paddle_width_range
            
            if key == "back":
                self.pop_state()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_ball_speed:
            self.dragging_ball_speed = False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_ball_diameter:
            self.dragging_ball_diameter = False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_paddle_speed:
            self.dragging_paddle_speed = False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_paddle_size:
            self.dragging_paddle_size = False

        if event.type == pygame.MOUSEMOTION and self.dragging_ball_speed:
            percent = self.update_slider_from_mouse("ball_speed_slider", event)
            s.ball_speed = s.ball_speed_min + percent * s.ball_speed_range
        if event.type == pygame.MOUSEMOTION and self.dragging_paddle_speed:
            percent = self.update_slider_from_mouse("paddle_speed_slider", event)
            s.paddle_speed = s.paddle_speed_min + percent * s.paddle_speed_range
        if event.type == pygame.MOUSEMOTION and self.dragging_ball_diameter:
            percent = self.update_slider_from_mouse("ball_diameter_slider", event)
            s.ball_diameter = s.ball_diameter_min + percent * s.ball_diameter_range            
        if event.type == pygame.MOUSEMOTION and self.dragging_paddle_size:
            percent = self.update_slider_from_mouse("paddle_size_slider", event)
            s.paddle_height = s.paddle_height_min + percent * s.paddle_height_range
            s.paddle_width = s.paddle_width_min + percent * s.paddle_width_range
            
        game_state = self.app.state_manager.get_state(GameState)
        if game_state:
            game_state.game.apply_gameplay_settings()
