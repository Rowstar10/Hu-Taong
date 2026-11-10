import pygame

from config import BASE_W, BASE_H
from core import save_data
from render import theme
from core.states.base_state import State
from core.states.jukebox import JukeboxControls

class WinState(JukeboxControls, State):
    NAME = "win"
    is_menu = True
    is_overlay = True

    def __init__(self, app, p1, p2, winner, loser, left = None):
        super().__init__(app)
        self.init_jukebox()

        self.p1 = p1
        self.p2 = p2
        self.winner = winner
        self.loser = loser
        self.ui_cols = 2
        # Online, the friend left (or went quiet) mid-match: the match ends where it was, with no
        # winner, and it doesn't count in the stats
        self.left = left
        self.net = getattr(winner.game, "net", None)
        self.lost = False
        if left:
            self.app.sound_manager.play("shutdown.wav")
            self.app.sound_manager.set_mood("menu")
            return

        sound_manager = self.app.sound_manager
        if getattr(winner.game, "net", None):          # online: counted as your own win or loss
            self.app.stats.record_online(not getattr(winner, "remote", False))
        else:
            self.app.stats.record_match(p1, winner, loser)
        save_data.save(self.app)
        if not winner.ai_enabled and loser.ai_enabled:
            sound_manager.play("you_win.wav")
        elif not loser.ai_enabled and winner.ai_enabled:
            sound_manager.play("you_lose.wav")
        else:
            sound_manager.play("red_wins.wav" if winner == p1 else "blue_wins.wav")
        net = getattr(winner.game, "net", None)
        self.net = net
        if net:                                    # tell the friend how it ended, and its highlights
            rec = winner.game.recorder
            def clock(frame):
                i = max(0, min(len(rec.frames) - 1, frame - rec.dropped))
                return round(__import__("struct").unpack_from("<f", rec.frames[i], 0)[0], 3) if rec.frames else 0
            net.over = {"winner": 1 if winner is p1 else 2, "score": [p1.score, winner.game.p2.score],
                        "moments": [[m.title, m.score, clock(m.at), clock(m.start), clock(m.end), m.side]
                                    for m in rec.reel()]}
        if not loser.ai_enabled and winner.ai_enabled:
            sound_manager.set_mood("defeat")
        else:
            sound_manager.set_mood("victory")

        self.lost = not loser.ai_enabled and winner.ai_enabled

        # Fan out from beside the panel, so the result stays readable
        tint = "red" if winner == p1 else "blue"
        count = 6 if self.lost else 22
        self.app.fx.burst(BASE_W / 2 - 430, BASE_H / 2, count, 64, tint, arc = (2.2, 4.1))
        self.app.fx.burst(BASE_W / 2 + 430, BASE_H / 2, count, 64, tint, arc = (-.95, .95))

    def friend_gone(self):
        """Online, and the friend has left: nobody to play again with, or to go to the lobby with."""
        return bool(self.left) or (self.net is not None and not self.net.connected())

    def draw(self, screen):
        super().draw(screen)
        title = f"{self.winner.color1} Wins!"
        if self.left:
            title = "Lost Touch" if "Lost touch" in self.left else "Your Friend Left"

        header = [(f"{self.p1.color1}: ", theme.color(self.p1.color1)),
                  (f"{self.p1.score}      ", theme.PARCHMENT),
                  (f"{self.p2.color1}: ", theme.color(self.p2.color1)),
                  (f"{self.p2.score}", theme.PARCHMENT)]
        
        buttons = [("play_again", "Play Again?", theme.GREEN, theme.GREEN_HOVER),
                   ("continue", "Endless Mode...", theme.BLUE, theme.BLUE_HOVER),
                   ("watch_replay", "Replay", theme.ORANGE, theme.ORANGE_HOVER),
                   ("highlights", "Highlights", theme.ORANGE, theme.ORANGE_HOVER),
                   ("settings", "Settings", theme.WHITE, theme.WHITE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]
        if not self.reel():
            buttons.remove(buttons[3])
        gone = self.friend_gone()
        if gone:                                   # the friend has left: watch, save, then go
            buttons = [b for b in buttons if b[0] not in ("play_again", "continue")]
        elif self.net:                             # online: back to the lobby together, or leave
            buttons.insert(len(buttons) - 1, ("lobby", "Lobby", theme.WHITE, theme.WHITE_HOVER))
            buttons[-1] = ("main_menu", "Leave", theme.RED, theme.RED_HOVER)
        # the layout is worked out once; redo it if the buttons change (the friend leaving)
        if getattr(self, "_gone_drawn", None) != gone:
            self._gone_drawn = gone
            self._laid = None

        self.app.renderer.draw_overlay(
            self,
            screen,
            title=title, header=header, buttons=buttons,
            title_size=0.1, header_size=0.05, btn_size=0.045,
            title_color=theme.PARCHMENT if self.left else theme.color(self.winner.color1),
            mark="离" if self.left else "败" if self.lost else "胜",
            tips={"play_again": "Play Again\nA new match with the same setup.",
                  "continue": "Endless Mode\nKeep playing this match with no score limit.",
                  "watch_replay": "Replay\nWatch this match again, and save all or part of it.",
                  "highlights": "Highlights\nThe best moments of this match.",
                  "settings": "Settings\nChange settings, then come back here.",
                  "lobby": "Lobby\nBack to the lobby with your friend, to change the court or sides.\n"
                           "• They stay connected",
                  "main_menu": ("Leave\nStop playing. Your friend goes back to their menu." if self.net and not gone
                                else "Main Menu\nLeave this match.")},
            jukebox=True)
        self.draw_jukebox_extras(screen)

    # ---------------- Replays ----------------

    def recorder(self):
        from core.states.game_state import GameState
        game_state = self.app.state_manager.get_state(GameState)
        return game_state.game.recorder if game_state and game_state.game else None

    def reel(self):
        recorder = self.recorder()
        if recorder is None:
            return []
        shift = recorder.dropped
        from game.replay import Moment
        return [Moment(m.title, m.score, m.at - shift, max(0, m.start - shift), m.end - shift, m.side)
                for m in recorder.reel() if m.start >= shift]

    def watch(self, mode):
        recorder = self.recorder()
        if recorder is None or not recorder.frames:
            return
        moments = self.reel() if mode == "reel" else None
        if mode == "reel" and not moments:
            return
        self.push_state("replay", clip = recorder.clip(), mode = mode, moments = moments, mute = True)

    def update(self, dt):
        if self.net and not self.friend_gone() and self.net.request("rematch"):
            self.app.renderer.show_toast("Your friend would like a rematch: Play Again starts it")
        # After the match, its highlights play once on their own (Settings > Interface > Instant Replay)
        # (not after a friend left: they're there under Highlights)
        if not getattr(self, "reel_shown", False) and not self.left:
            self.reel_shown = True
            if self.app.settings.interface.instant_replay in (2, 3) and self.reel():
                self.watch("reel")

    def handle_event(self, event):
        if self.track_list:
            self.handle_track_list(event)
            return
        super().handle_event(event)
        key = self.hit_test(self.app.window_to_base(event.pos)) if hasattr(event, "pos") else None
        if self.handle_jukebox(event, key if event.type == pygame.MOUSEBUTTONDOWN else None):
            return

        gameplay = self.app.settings.gameplay
        sound_manager = self.app.sound_manager
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
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
                                              setattr(self.net, "over", None) if self.net else None,
                                              self.pop_state(mute = True),
                                              self.pop_state(mute = True),
                                              game_state.game.reset_round(),
                                              sound_manager.play("enter_state.wav"),
                                              sound_manager.set_mood("game"))

                            self.push_state("confirm_choice", action = action, header = "Enter Endless Mode?", mute = True)
                        
                    if key == "watch_replay":
                        self.watch("viewer")
                    if key == "highlights":
                        self.watch("reel")

                    if key == "settings":
                        self.push_state("settings")

                    if key == "lobby":
                        from core.states.game_state import GameState
                        game_state = self.app.state_manager.get_state(GameState)
                        if game_state:
                            self.push_state("confirm_choice", action = game_state.back_to_lobby,
                                            header = "Back to the lobby?", mute = True)
                        
                    if key == "main_menu":
                        action = lambda: (self.app.sound_manager.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                        self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
