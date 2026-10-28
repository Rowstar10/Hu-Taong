import pygame, random

from core.states.base_state import State
from core.states.game_state import GameState

class GameplaySettingsState(State):
    NAME = "gameplay"
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
        
        audio = self.app.settings.gameplay
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            mx, my = mouse_pos
            key = self.hit_test(mouse_pos)
            
            if key == "cycle_ai_left":
                audio.ai_difficulty = (audio.ai_difficulty - 1) % len(audio.ai_difficulties)
            if key == "cycle_ai_right":
                audio.ai_difficulty = (audio.ai_difficulty + 1) % len(audio.ai_difficulties)
                
            if key == "cycle_win_score_left":
                audio.winning_score_index = (audio.winning_score_index - 1) % len(audio.winning_scores)
            if key == "cycle_win_score_right":
                audio.winning_score_index = (audio.winning_score_index + 1) % len(audio.winning_scores)
            if key == "toggle_win_by_two":
                audio.win_by_two = not audio.win_by_two
            
            if key == "ball_speed_slider":
                self.dragging_ball_speed = True
                percent = self.update_slider_from_mouse("ball_speed_slider", event)
                audio.ball_speed = audio.ball_speed_min + percent * audio.ball_speed_range
            if key == "paddle_speed_slider":
                self.dragging_paddle_speed = True
                percent = self.update_slider_from_mouse("paddle_speed_slider", event)
                audio.paddle_speed = audio.paddle_speed_min + percent * audio.paddle_speed_range
            if key == "ball_diameter_slider":
                self.dragging_ball_diameter = True
                percent = self.update_slider_from_mouse("ball_diameter_slider", event)
                audio.ball_diameter = audio.ball_diameter_min + percent * audio.ball_diameter_range
            if key == "paddle_size_slider":
                self.dragging_paddle_size = True
                percent = self.update_slider_from_mouse("paddle_size_slider", event)
                audio.paddle_height = audio.paddle_height_min + percent * audio.paddle_height_range

            if key == "randomise_all":
                audio.ball_speed = audio.ball_speed_min + random.random() * audio.ball_speed_range
                audio.paddle_speed = audio.paddle_speed_min + random.random() * audio.paddle_speed_range
                audio.ball_diameter = audio.ball_diameter_min + random.random() * audio.ball_diameter_range
                audio.paddle_height = audio.paddle_height_min + random.random() * audio.paddle_height_range
                audio.paddle_width = audio.paddle_width_min + random.random() * audio.paddle_width_range

            if key == "reset_all":
                audio.ball_speed = audio.ball_speed_min + 0.5 * audio.ball_speed_range
                audio.paddle_speed = audio.paddle_speed_min + 0.5 * audio.paddle_speed_range
                audio.ball_diameter = audio.ball_diameter_min + 0.5 * audio.ball_diameter_range
                audio.paddle_height = audio.paddle_height_min + 0.5 * audio.paddle_height_range
                audio.paddle_width = audio.paddle_width_min + 0.5 * audio.paddle_width_range
                
            if key == "reset_ball_speed":
                audio.ball_speed = audio.ball_speed_min + 0.5 * audio.ball_speed_range
            if key == "reset_paddle_speed":
                audio.paddle_speed = audio.paddle_speed_min + 0.5 * audio.paddle_speed_range
            if key == "reset_ball_diameter":
                audio.ball_diameter = audio.ball_diameter_min + 0.5 * audio.ball_diameter_range
            if key == "reset_paddle_size":
                audio.paddle_height = audio.paddle_height_min + 0.5 * audio.paddle_height_range
                audio.paddle_width = audio.paddle_width_min + 0.5 * audio.paddle_width_range
            
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
            audio.ball_speed = audio.ball_speed_min + percent * audio.ball_speed_range
        if event.type == pygame.MOUSEMOTION and self.dragging_paddle_speed:
            percent = self.update_slider_from_mouse("paddle_speed_slider", event)
            audio.paddle_speed = audio.paddle_speed_min + percent * audio.paddle_speed_range
        if event.type == pygame.MOUSEMOTION and self.dragging_ball_diameter:
            percent = self.update_slider_from_mouse("ball_diameter_slider", event)
            audio.ball_diameter = audio.ball_diameter_min + percent * audio.ball_diameter_range            
        if event.type == pygame.MOUSEMOTION and self.dragging_paddle_size:
            percent = self.update_slider_from_mouse("paddle_size_slider", event)
            audio.paddle_height = audio.paddle_height_min + percent * audio.paddle_height_range
            audio.paddle_width = audio.paddle_width_min + percent * audio.paddle_width_range
            
        game_state = self.app.state_manager.get_state(GameState)
        if game_state:
            game_state.game.apply_gameplay_settings()
