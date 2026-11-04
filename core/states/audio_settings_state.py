import pygame

from core.sound_manager import DEFAULT_VOLUME
from core.states.base_state import State

class AudioSettingsState(State):
    NAME = "audio"
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        self.dragging_master_volume = False
        self.dragging_music_volume = False
        self.dragging_sfx_volume = False
        self.track_list = False      # the jukebox's list of tracks is open
        self.track_scroll = 0        # first track shown in it

    def exit(self, **kwargs):
        super().exit(**kwargs)
        self.track_list = False

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_audio_settings_menu(self, screen)
        if self.track_list:
            self.app.renderer.draw_track_list(self, screen)

    def scroll_tracks(self, rows):
        most = max(0, len(self.app.sound_manager.pool) - self.app.renderer.TRACK_ROWS)
        self.track_scroll = max(0, min(most, self.track_scroll + rows))

    def open_track_list(self):
        """Open the list with the playing track in view."""
        pool = self.app.sound_manager.pool
        playing = self.app.sound_manager.now_playing
        here = pool.index(playing) if playing in pool else 0
        self.track_scroll = 0
        self.scroll_tracks(here - self.app.renderer.TRACK_ROWS // 2)
        self.track_list = True

    def handle_track_list(self, event):
        """While the list is open it gets every event: pick a track, scroll, or close it."""
        sound = self.app.sound_manager
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.track_list = False             # closes the list only, not the Audio menu
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_tracks(-event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            if key and key.startswith("track_") and key != "track_list":
                track = sound.pool[int(key[6:])]
                sound.play("click.wav")
                if track != sound.now_playing:
                    sound.play_music(track)
                self.track_list = False
            elif key != "track_list":
                self.track_list = False         # a click anywhere else just closes it

    def handle_event(self, event):
        if self.track_list:
            self.handle_track_list(event)
            return

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
                sound.master_volume = DEFAULT_VOLUME
                sound.update_music_volume()
            if key == "reset_music_volume":
                sound.music_volume = DEFAULT_VOLUME
                sound.update_music_volume()
            if key == "reset_sfx_volume":
                sound.sfx_volume = DEFAULT_VOLUME
            if key == "reset_defaults":
                self.confirm_reset("Reset audio settings?", self.app.reset_audio_settings)

            if key == "cycle_music_value":
                self.open_track_list()
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
            if key == "toggle_menu_sounds":
                audio.menu_sounds = not audio.menu_sounds
            if key == "toggle_even_volume":
                audio.even_volume = not audio.even_volume
                sound.update_music_volume()

            for name, options in (("fade", audio.fade_options), ("ambience", audio.ambience_options)):
                if key == f"cycle_{name}_left":
                    setattr(audio, name, (getattr(audio, name) - 1) % len(options))
                if key == f"cycle_{name}_right":
                    setattr(audio, name, (getattr(audio, name) + 1) % len(options))
                
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
