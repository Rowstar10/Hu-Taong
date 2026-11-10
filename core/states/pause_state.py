import pygame

from core.states.game_state import GameState
from core.states.base_state import State
from core.states.jukebox import JukeboxControls
from render import theme

class PauseState(JukeboxControls, State):
    NAME = "pause"
    is_menu = True
    is_overlay = True

    TIPS = {"resume": "Resume\nBack to the match.\n~ Esc",
            "reset": "Reset\nServe again from the middle.\n• Scores and everything else stay as they are",
            "reset_scores": "Reset Scores\nRestart this match from 0-0.",
            "settings": "Settings\nChange settings without leaving the match.",
            "main_menu": "Main Menu\nLeave this match.",
            "lobby": "Lobby\nBack to the lobby with your friend, to change the court or sides.\n"
                     "• They stay connected; the match so far ends",
            "leave": "Leave Match\nStop playing. Your friend goes back to their menu.",
            "watch_replay": "Replay\nWatch the match so far, and save all or part of it.",
            "p1_ai": "Red AI\nLet the AI play the red paddle, or take it back.",
            "p2_ai": "Blue AI\nLet the AI play the blue paddle, or take it back."}

    def __init__(self, app, by_friend = False):
        super().__init__(app)
        self.by_friend = by_friend
        self.game_state = self.app.state_manager.get_state(GameState)
        self.ui_cols = 2
        self.init_jukebox()

    def enter(self, **kwargs):
        sound_manager = self.app.sound_manager
        sound_manager.play("startup2.wav")
        sound_manager.multiplier = 0.3     # quieter behind the menu, but loud enough to pick a track
        sound_manager.update_music_volume()

    def exit(self, **kwargs):
        super().exit(**kwargs)
        sound_manager = self.app.sound_manager
        sound_manager.multiplier = 1
        sound_manager.update_music_volume()

    def update(self, dt):
        pass

    def draw(self, screen):
        super().draw(screen)
        buttons = [("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                   ("reset", "Reset", theme.BLUE, theme.BLUE_HOVER),
                   ("reset_scores", "Reset Scores", theme.BLUE, theme.BLUE_HOVER),
                   ("watch_replay", "Replay", theme.ORANGE, theme.ORANGE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]

        # The AI toggles live here only, so a match itself stays uncluttered
        toggles = None
        header = None
        online = self.game_state and self.game_state.game and self.game_state.game.net
        if self.game_state and self.game_state.game and not online:
            game = self.game_state.game
            toggles = [("p1_ai", "Red AI", lambda: game.p1.ai_enabled),
                       ("p2_ai", "Blue AI", lambda: game.p2.ai_enabled)]
        if online:
            # with a friend waiting: carry on, or leave; the match is paused for both
            buttons = [("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                       ("reset", "Reset", theme.BLUE, theme.BLUE_HOVER),
                       ("reset_scores", "Reset Scores", theme.BLUE, theme.BLUE_HOVER),
                       ("watch_replay", "Replay", theme.ORANGE, theme.ORANGE_HOVER),
                       ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                       ("lobby", "Lobby", theme.WHITE, theme.WHITE_HOVER),
                       ("main_menu", "Leave Match", theme.RED, theme.RED_HOVER)]
            net = self.game_state.game.net
            header = lambda: ("Your friend is in the settings..." if net.guest_menu == 2 and net.connected() else
                              "Your friend paused the match" if self.by_friend else "Paused for both of you")

        tips = dict(self.TIPS, main_menu = self.TIPS["leave"]) if online else self.TIPS
        self.app.renderer.draw_overlay(self, screen,
                                       title = "Paused", header = header, buttons = buttons, mark = "停",
                                       toggles = toggles, tips = tips, jukebox = True)
        self.draw_jukebox_extras(screen)

    def resume(self):
        """Back to the match; online, not while the friend is still in the settings."""
        game = self.game_state.game if self.game_state else None
        if game and game.net and game.net.guest_menu == 2 and game.net.connected():
            self.app.renderer.show_toast("Your friend is still in the settings", important = True)
            return
        self.pop_state(mute = True)
        self.app.sound_manager.play("shutdown.wav")

    def handle_event(self, event):
        if self.track_list:
            self.handle_track_list(event)
            return
        super().handle_event(event)
        key = self.hit_test(self.app.window_to_base(event.pos)) if hasattr(event, "pos") else None
        if self.handle_jukebox(event, key if event.type == pygame.MOUSEBUTTONDOWN else None):
            return

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.resume()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sound_manager = self.app.sound_manager
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "p1_ai":
                self.game_state.game.p1.ai_enabled = not self.game_state.game.p1.ai_enabled
                self.game_state.game.p1.ai.reset()

            if key == "p2_ai":
                self.game_state.game.p2.ai_enabled = not self.game_state.game.p2.ai_enabled
                self.game_state.game.p2.ai.reset()

            if key == "resume":
                self.resume()

            if key == "reset" and self.game_state:
                # just this moment, not the match: serve again and keep the scores
                game = self.game_state.game
                game.powerups.on_point()
                game.reset_round()
                self.pop_state(mute = True)
                sound_manager.play("enter_state.wav")

            if key == "reset_scores":
                if self.game_state:
                    action = lambda: (self.game_state.restart(),
                                      self.pop_state(mute = True),
                                      self.pop_state(mute = True),
                                      sound_manager.play("enter_state.wav"))

                    self.push_state("confirm_choice", action = action, header = "Reset Scores?", mute = True)

            if key == "watch_replay" and self.game_state and self.game_state.game:
                recorder = self.game_state.game.recorder
                if recorder.frames:
                    self.push_state("replay", clip = recorder.clip(), mode = "viewer", mute = True)

            if key == "settings":
                self.push_state("settings")

            if key == "lobby" and self.game_state:
                self.push_state("confirm_choice", action = self.game_state.back_to_lobby,
                                header = "Back to the lobby?", mute = True)

            if key == "main_menu":
                action = lambda: (sound_manager.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
