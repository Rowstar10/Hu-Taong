"""The jukebox controls shared by the Audio menu and the pause screen: the track's arrows and its
list of tracks, play/pause, and the progress bar you can click or drag to jump through a track."""
import pygame


class JukeboxControls:
    def init_jukebox(self):
        self.track_list = False      # the list of tracks is open
        self.track_scroll = 0        # first track shown in it
        self.seek_drag = None        # 0-1 along the progress bar while it is being dragged

    # ---------------- The list of tracks ----------------

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
            self.track_list = False             # closes the list only, not the screen under it
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

    def draw_jukebox_extras(self, screen):
        if self.track_list:
            self.app.renderer.draw_track_list(self, screen)

    # ---------------- Clicks ----------------

    def seek_fraction(self, event):
        rect = self.ui_hitboxes.get("music_seek")
        if rect is None:
            return None
        x, _ = self.app.window_to_base(event.pos)
        return max(0.0, min(1.0, (x - rect.left) / max(1, rect.width)))

    def handle_jukebox(self, event, key):
        """Handle a jukebox control; True if the event was one."""
        sound = self.app.sound_manager
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if key == "cycle_music_value":
                self.open_track_list()
            elif key == "cycle_music_left":
                sound.step_track(-1)
            elif key == "cycle_music_right":
                sound.step_track(1)
            elif key == "music_pause":
                sound.toggle_music_pause()
            elif key == "music_mode":
                audio = self.app.settings.audio
                audio.play_mode = (audio.play_mode + 1) % 3
                self.app.renderer.show_toast("When a track ends: " + ("play the next one", "shuffle", "loop it")[audio.play_mode])
            elif key == "music_seek" and sound.music_length() > 0:
                self.seek_drag = self.seek_fraction(event)
            else:
                return False
            return True
        if event.type == pygame.MOUSEMOTION and self.seek_drag is not None:
            fraction = self.seek_fraction(event)
            if fraction is not None:
                self.seek_drag = fraction
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.seek_drag is not None:
            sound.seek_music(self.seek_drag * sound.music_length())
            self.seek_drag = None
            return True
        return False
