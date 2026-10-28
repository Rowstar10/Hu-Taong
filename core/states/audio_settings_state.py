import pygame, random

from core.states.base_state import State

class AudioSettingsState(State):
    NAME = "audio"
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

        audio = self.app.settings.audio
        sound = self.app.sound_manager
        
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
                audio.menu_music = (audio.menu_music - 1) % len(audio.menu_track)
                if sound.music_type == "menu":
                    music = audio.menu_track[audio.menu_music]
                    sound.play_music(music)
            if key == "cycle_menu_music_right":
                audio.menu_music = (audio.menu_music + 1) % len(audio.menu_track)
                if sound.music_type == "menu":
                    music = audio.menu_track[audio.menu_music]
                    sound.play_music(music)
                
            if key == "cycle_game_music_left":
                audio.game_music = (audio.game_music - 1) % len(audio.game_track)
                if sound.music_type == "game":
                    music = audio.game_track[audio.game_music]
                    sound.play_music(music)
            if key == "cycle_game_music_right":
                audio.game_music = (audio.game_music + 1) % len(audio.game_track)
                if sound.music_type == "game":
                    music = audio.game_track[audio.game_music]
                    sound.play_music(music)
                
            if key == "cycle_win_music_left":
                audio.win_music = (audio.win_music - 1) % len(audio.win_track)
                if sound.music_type == "win":
                    music = audio.win_track[audio.win_music]
                    sound.play_music(music)
            if key == "cycle_win_music_right":
                audio.win_music = (audio.win_music + 1) % len(audio.win_track)
                if sound.music_type == "win":
                    music = audio.win_track[audio.win_music]
                    sound.play_music(music)

            if key == "cycle_lose_music_left":
                audio.lose_music = (audio.lose_music - 1) % len(audio.lose_track)
                if sound.music_type == "lose":
                    music = audio.lose_track[audio.lose_music]
                    sound.play_music(music)
            if key == "cycle_lose_music_right":
                audio.lose_music = (audio.lose_music + 1) % len(audio.lose_track)
                if sound.music_type == "lose":
                    music = audio.lose_track[audio.lose_music]
                    sound.play_music(music)

            if key == "randomise_music":
                menu_music = random.choice(audio.menu_track)
                game_music = random.choice(audio.game_track)
                win_music = random.choice(audio.win_track)
                lose_music = random.choice(audio.lose_track)
                
                audio.menu_music = audio.menu_track.index(menu_music)
                audio.game_music = audio.game_track.index(game_music)
                audio.win_music = audio.win_track.index(win_music)
                audio.lose_music = audio.lose_track.index(lose_music)
                
                if sound.music_type == "menu":
                    sound.play_music(menu_music)
                if sound.music_type == "game":
                    sound.play_music(game_music)
                if sound.music_type == "win":
                    sound.play_music(win_music)
                if sound.music_type == "lose":
                    sound.play_music(lose_music)

            if key == "toggle_loop_music":
                audio.loop_music = not audio.loop_music
            if key == "toggle_paddle_sounds":
                sound.paddle_hit_sound = not sound.paddle_hit_sound
            if key == "toggle_score_sounds":
                sound.score_sound = not sound.score_sound
                
            if key == "back":
                self.pop_state()
                
        if event.type == pygame.MOUSEMOTION and self.dragging_master_volume:
            sound.master_volume = self.update_slider_from_mouse("master_volume_slider", event)
            sound.update_music_volume()
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
