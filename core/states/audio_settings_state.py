import pygame

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

            if key == "cycle_music_left":
                sound.step_track(-1)
            if key == "cycle_music_right":
                sound.step_track(1)
            if key == "randomise_music":
                sound.random_track()

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
