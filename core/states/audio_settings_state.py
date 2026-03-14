import pygame

from core.state_registry import StateRegistry
from core.states.base_state import State

@StateRegistry.register_state("audio")
class AudioSettingsState(State):
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        self.dragging_master_volume = False
        self.dragging_music_volume = False
        self.dragging_sfx_volume = False
        
    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_audio_settings_menu(self, screen)
        
    def handle_event(self, event):
        super().handle_event(event)

        s = self.app.settings.audio
        sound = self.app.sound
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            mx, my = mouse_pos
            key = self.hit_test(mouse_pos)
            
            if key == "master_volume_slider":
                self.dragging_master_volume = True
                sound.master_volume = self.update_slider_from_mouse("master_volume_slider", event)
                sound.update_music_volume()
            if key == "music_volume_slider":
                self.dragging_music_volume = True
                sound.music_volume = self.update_slider_from_mouse("music_volume_slider", event)
                sound.update_music_volume()
            if key == "sfx_volume_slider":
                self.dragging_sfx_volume = True
                sound.sfx_volume = self.update_slider_from_mouse("sfx_volume_slider", event)
                
            if key == "reset_master_volume":
                sound.master_volume = 0.5
                sound.update_music_volume()
            if key == "reset_music_volume":
                sound.music_volume = 0.5
                sound.update_music_volume()
            if key == "reset_sfx_volume":
                sound.sfx_volume = 0.5

            if key == "cycle_menu_music_left":
                s.menu_music = (s.menu_music - 1) % len(s.menu_track)
                if self.app.sound.music_type == "menu":
                    music = s.menu_track[s.menu_music]
                    sound.play_music(music)
            if key == "cycle_menu_music_right":
                s.menu_music = (s.menu_music + 1) % len(s.menu_track)
                if self.app.sound.music_type == "menu":
                    music = s.menu_track[s.menu_music]
                    sound.play_music(music)
                
            if key == "cycle_game_music_left":
                s.game_music = (s.game_music - 1) % len(s.game_track)
                if self.app.sound.music_type == "game":
                    music = s.game_track[s.game_music]
                    sound.play_music(music)
            if key == "cycle_game_music_right":
                s.game_music = (s.game_music + 1) % len(s.game_track)
                if self.app.sound.music_type == "game":
                    music = s.game_track[s.game_music]
                    sound.play_music(music)
                
            if key == "cycle_win_music_left":
                s.win_music = (s.win_music - 1) % len(s.win_track)
                if self.app.sound.music_type == "win":
                    music = s.win_track[s.win_music]
                    sound.play_music(music)
            if key == "cycle_win_music_right":
                s.win_music = (s.win_music + 1) % len(s.win_track)
                if self.app.sound.music_type == "win":
                    music = s.win_track[s.win_music]
                    sound.play_music(music)

            if key == "toggle_paddle_sounds":
                sound.paddle_hit_sound = not sound.paddle_hit_sound
            if key == "toggle_score_sounds":
                sound.score_sound = not sound.score_sound
                
            if key == "back":
                self.pop_state()
                
        if event.type == pygame.MOUSEMOTION and self.dragging_master_volume:
            sound.master_volume = self.update_slider_from_mouse("master_volume_slider", event)
            settings.update_music_volume()
        if event.type == pygame.MOUSEMOTION and self.dragging_music_volume:
            sound.music_volume = self.update_slider_from_mouse("music_volume_slider", event)
            sound.update_music_volume()
        if event.type == pygame.MOUSEMOTION and self.dragging_sfx_volume:
            sound.sfx_volume = self.update_slider_from_mouse("sfx_volume_slider", event)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_master_volume:
            self.dragging_master_volume = False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_music_volume:
            self.dragging_music_volume = False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_sfx_volume:
            self.dragging_sfx_volume = False
