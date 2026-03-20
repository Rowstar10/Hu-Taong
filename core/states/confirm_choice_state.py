import pygame

from core.state_registry import StateRegistry
from core.states.base_state import State
from render import theme

@StateRegistry.register_state("confirm_choice")
class ConfirmChoiceState(State):
    is_overlay = True
    is_menu = True

    def __init__(self, app, action = None, header = ""):
        super().__init__(app)
        self.action = action
        self.header = header
    
    def draw(self, screen):
        super().draw(screen)
        W, H = self.app.base_w, self.app.base_h
        
        panel_w = int(W * 0.2)
        panel_h = int(H * 0.15)
        panel_rect = pygame.Rect(W // 2 - panel_w // 2,
                                 H // 2 - panel_h // 2,
                                 panel_w, panel_h)
        
        buttons = [("confirm", "Yes", theme.GREEN, theme.GREEN_HOVER),
                   ("cancel", "No", theme.RED, theme.RED_HOVER)]

        self.app.renderer.draw_overlay(self, screen,
                                       title = self.header,
                                       buttons = buttons,
                                       title_size = 0.3,
                                       btn_size = 0.2,
                                       title_y = 0.3,
                                       panel_rect = panel_rect)

    def handle_event(self, event):
        super().handle_event(event)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.action()
            
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state(mute = True)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            
            if key == "confirm":
                self.action()
            if key == "cancel":
                self.pop_state(mute = True)
