import pygame

from core.states.base_state import State
from game.hu_taong import Hu_Taong

class GameState(State):
    NAME = "game"
    is_game = True
    
    def __init__(self, app):
        super().__init__(app)
        self.game = None

    def enter(self, **kwargs):
        super().enter(**kwargs)
        self.app.sound_manager.play("startup2.wav")
        if not self.game:
            self.game = Hu_Taong(self.app)
            self.game.start()

    def exit(self, **kwargs):
        if self.game:
            self.game.stop()
            self.game = None
        super().exit(**kwargs)

    def restart(self):
        self.game.reset_game()
        
    def update(self, dt):
        super().update(dt)
        if self.game:
            self.game.update(dt)
            
    def draw(self, screen):
        super().draw(screen)
        if not self.game:
            return

        self.app.renderer.draw_world(screen, self.game)
        self.app.hud.draw(self, screen, self.game)
        
    def handle_event(self, event):
        super().handle_event(event)
        
        if not self.game:
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.push_state("pause", mute = True)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            mx, my = mouse_pos
            key = self.hit_test(mouse_pos)

            if key == "p1_ai":
                self.game.p1.ai_enabled = not self.game.p1.ai_enabled
                    
            elif key == "p2_ai":
                self.game.p2.ai_enabled = not self.game.p2.ai_enabled
                    
            elif key == "pause":
                self.push_state("pause", mute = True)
