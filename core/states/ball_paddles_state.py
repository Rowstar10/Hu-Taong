import pygame, random

from core.states.base_state import State
from core.states.game_state import GameState

class BallPaddlesState(State):
    """Settings > Match > Ball & Paddles: the ball's and paddles' sizes and speeds, and the pace."""
    NAME = "ball_paddles"
    is_menu = True

    # slider key -> what dragging it sets
    SLIDERS = ("ball_speed_slider", "paddle_speed_slider", "ball_diameter_slider", "paddle_size_slider", "pace_slider")

    def __init__(self, app):
        super().__init__(app)
        self.dragging = None         # the slider being dragged, if any

    @staticmethod
    def pace_from(percent, settings):
        """Game pace for a slider position, in steps of 0.05 so it reads cleanly."""
        return round((settings.pace_min + percent * settings.pace_range) * 20) / 20

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_ball_paddles_menu(self, screen)

    def set_from_slider(self, key, event):
        m = self.app.settings.match
        percent = self.update_slider_from_mouse(key, event)
        if key == "ball_speed_slider":
            m.ball_speed = m.ball_speed_min + percent * m.ball_speed_range
        if key == "paddle_speed_slider":
            m.paddle_speed = m.paddle_speed_min + percent * m.paddle_speed_range
        if key == "ball_diameter_slider":
            m.ball_diameter = m.ball_diameter_min + percent * m.ball_diameter_range
        if key == "pace_slider":
            m.pace = self.pace_from(percent, m)
        if key == "paddle_size_slider":
            m.paddle_height = m.paddle_height_min + percent * m.paddle_height_range
            m.paddle_width = m.paddle_width_min + percent * m.paddle_width_range

    def reset_defaults(self):
        m = self.app.settings.match
        m.reset_ball_and_paddles()
        m.pace = 1.0

    def handle_event(self, event):
        super().handle_event(event)
        m = self.app.settings.match

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))

            if key in self.SLIDERS:
                self.dragging = key
                self.set_from_slider(key, event)

            if key == "randomise_all":
                m.ball_speed = m.ball_speed_min + random.random() * m.ball_speed_range
                m.paddle_speed = m.paddle_speed_min + random.random() * m.paddle_speed_range
                m.ball_diameter = m.ball_diameter_min + random.random() * m.ball_diameter_range
                m.paddle_height = m.paddle_height_min + random.random() * m.paddle_height_range
                m.paddle_width = m.paddle_width_min + random.random() * m.paddle_width_range
            if key == "reset_ball_and_paddles":
                m.reset_ball_and_paddles()

            if key == "reset_ball_speed":
                m.ball_speed = m.ball_speed_min + 0.5 * m.ball_speed_range
            if key == "reset_paddle_speed":
                m.paddle_speed = m.paddle_speed_min + 0.5 * m.paddle_speed_range
            if key == "reset_ball_diameter":
                m.ball_diameter = m.ball_diameter_min + 0.5 * m.ball_diameter_range
            if key == "reset_pace":
                m.pace = 1.0
            if key == "reset_paddle_size":
                m.paddle_height = m.paddle_height_min + 0.5 * m.paddle_height_range
                m.paddle_width = m.paddle_width_min + 0.5 * m.paddle_width_range

            if key == "reset_defaults":
                self.confirm_reset("Reset the ball and paddles?", self.reset_defaults)
            if key == "back":
                self.pop_state()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = None
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_slider(self.dragging, event)

        game_state = self.app.state_manager.get_state(GameState)
        if game_state:
            game_state.game.apply_gameplay_settings()
