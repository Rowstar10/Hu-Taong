import pygame

from core.states.base_state import State
from game.hu_taong import Hu_Taong

class GameState(State):
    NAME = "game"
    is_game = True
    dims_court = True
    
    def __init__(self, app):
        super().__init__(app)
        self.game = None
        self.last_total_score = 0

    def enter(self, **kwargs):
        super().enter(**kwargs)
        self.app.sound_manager.play("startup2.wav")
        self.app.sound_manager.set_mood("game")
        if not self.game:
            self.game = Hu_Taong(self.app)
            self.game.start()

    def exit(self, **kwargs):
        net = self.game.net if self.game else None
        if self.game:
            self.game.stop()
            self.game = None
        if net and getattr(self, "keep_session", False):
            net.game, net.over, net.rematch_asked = None, None, False      # in the lobby, still connected
        else:
            self.app.leave_online()
        self.app.settings.gameplay.chaos_restore()
        super().exit(**kwargs)

    def back_to_lobby(self):
        """Hosting: back to the lobby with your friend still connected, to change the court or
        sides; their game follows you there."""
        self.keep_session = True
        sm = self.app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("match_setup", mute = True)
        sm.push_state("online", mute = True, resume = "host")

    def restart(self):
        self.game.reset_game()
        self.last_total_score = 0
        if self.game.net:
            self.game.net.over = None
        
    def update(self, dt):
        super().update(dt)
        if self.game:
            self.game.update(dt)
            self.app.stats.track(self.game, dt)
            recorder = self.game.recorder
            recorder.capture(dt)
            if self.game.net:
                self.game.note_history()
                self.game.net_tick()
            if getattr(self.game, "live_banner", 0) > 0:
                self.game.live_banner -= dt

            # A great point gets its instant replay once its moment has played out
            moment = recorder.instant
            if moment is not None and recorder.now >= moment.end:
                recorder.instant = None
                if self.app.settings.interface.instant_replay in (1, 3) and self.game.running and not self.game.net:
                    clip = recorder.clip()
                    shift = recorder.dropped
                    from game.replay import Moment
                    here = Moment(moment.title, moment.score, moment.at - shift, moment.start - shift,
                                  moment.end - shift, moment.side)
                    self.push_state("replay", clip = clip, mode = "instant", moments = [here], mute = True)

            total = self.game.p1.score + self.game.p2.score
            if total > self.last_total_score:
                self.app.stats.points += total - self.last_total_score
                self.app.renderer.shake(14, 0.3)
            self.last_total_score = total
            
    def draw(self, screen):
        super().draw(screen)
        if not self.game:
            return

        game = self.game
        shown = game.shown_ball(self.app.dt) if game.net else None
        if shown:
            # hosting: the ball is drawn on a sliding clock near your friend's paddle (Hu_Taong.shown_ball)
            ball = game.ball
            kept = (ball.x0, ball.y0, ball.x1, ball.y1)
            ball.x0, ball.y0 = shown
            ball.x1, ball.y1 = shown[0] + ball.width, shown[1] + ball.height
        self.app.renderer.draw_world(screen, game)
        if shown:
            ball.x0, ball.y0, ball.x1, ball.y1 = kept
        self.app.hud.draw(self, screen, game)
        
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

            if key == "pause":
                self.push_state("pause", mute = True)
