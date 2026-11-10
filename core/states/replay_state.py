"""Watching a replay.

Three ways in:
  viewer   the whole match (from Pause or the win screen) or a saved replay: a timeline to scrub,
           play/pause, speed, and Mark In / Mark Out to save just part of it
  instant  straight after a great point, its best moment
  reel     the match's highlights one after another, each with its caption
"""
import pygame

from core.states.base_state import State
from game import replay
from game.replay import RATE, Clip, ReplayView

SPEEDS = (0.25, 0.5, 1.0, 2.0)


class ReplayState(State):
    NAME = "replay"
    is_menu = True
    dims_court = True

    def __init__(self, app, clip = None, mode = "viewer", moments = None, saved = None):
        super().__init__(app)
        self.clip = clip
        self.mode = mode
        self.saved = saved                       # the file a saved replay came from
        self.view = ReplayView(clip, app)
        self.moments = list(moments if moments is not None else clip.moments)
        self.playing = True
        self.speed = 2                           # index into SPEEDS
        self.mark_in = self.mark_out = None
        self.dragging = False
        self.idle = 0.0                          # seconds since the mouse last moved (the bar hides)
        self.reel_index = 0
        self.position = 0.0
        self.end = len(clip.frames) - 1
        self.flashes = {}
        self.popups = []
        self.age = 0.0                           # seconds on screen, for the opening flash
        if mode in ("instant", "reel"):
            self.start_moment(0)

    # ---------------- Moments ----------------

    @property
    def moment(self):
        if self.mode in ("instant", "reel") and self.reel_index < len(self.moments):
            return self.moments[self.reel_index]
        return None

    def start_moment(self, index):
        self.reel_index = index
        self.age = 0.0
        m = self.moment
        if m is None:
            return
        self.position = float(max(0, m.start))
        self.end = min(len(self.clip.frames) - 1, m.end)
        self.reset_effects()

    def caption(self):
        m = self.moment
        if m is None:
            return None
        if self.mode == "reel" and len(self.moments) > 1:
            return f"Highlight {self.reel_index + 1} of {len(self.moments)}:  {m.title}"
        return m.title

    def rate(self):
        """Playback speed: real time unless you pick another with the speed control (highlights
        included: they don't slow down by themselves)."""
        return SPEEDS[self.speed]

    def slowed(self):
        return self.rate() < 1.0

    # ---------------- Lifetime ----------------

    def enter(self, **kwargs):
        super().enter(mute = True)
        self.app.renderer._trail.clear(); self.app.renderer._twin_trail.clear()

    def exit(self, **kwargs):
        super().exit(mute = True)
        self.app.renderer._trail.clear(); self.app.renderer._twin_trail.clear()

    def reset_effects(self):
        self.app.renderer._trail.clear(); self.app.renderer._twin_trail.clear()
        self.view.powerups.popups = []

    def leave(self):
        """Back to whatever was underneath.  A match about to carry on says so, loudly."""
        from core.states.game_state import GameState
        game_state = self.app.state_manager.get_state(GameState)
        stack = self.app.state_manager.stack
        if game_state and game_state.game and len(stack) >= 2 and stack[-2] is game_state:
            game_state.game.live_banner = 1.8
        self.app.sound_manager.play("shutdown.wav")
        self.pop_state(mute = True)

    def finished(self):
        if self.mode == "instant":
            self.leave()
        elif self.mode == "reel":
            if self.reel_index + 1 < len(self.moments):
                self.start_moment(self.reel_index + 1)
            else:
                self.leave()
        else:
            self.playing = False

    def update(self, dt):
        self.idle += dt
        self.age += dt
        if not self.playing or self.dragging:
            return
        before = self.position
        self.position = min(self.end, self.position + dt * RATE * self.rate())
        self.play_events(before, self.position)
        for popup in self.view.powerups.popups:
            popup[3] += dt * self.rate()
        self.view.powerups.popups = [p for p in self.view.powerups.popups if p[3] < 1.4]
        for paddle in (self.view.p1, self.view.p2):
            paddle.flash = max(0.0, paddle.flash - dt * 5)
        if self.position >= self.end:
            self.finished()

    def play_events(self, before, after):
        """The sounds and sparks of whatever happened between two frames."""
        if after - before > RATE * 0.5:
            return                                      # a jump, not playback
        for event in self.clip.events:
            if before < event[0] <= after:
                play_event(self.app, self.view, event[1], event[2:])

    # ---------------- Drawing ----------------

    def draw(self, screen):
        super().draw(screen)
        self.view.show(self.position)
        self.app.renderer.draw_replay(self, screen)

    # ---------------- Saving ----------------

    def save(self, which):
        """Save the whole replay, the marked part of it, or the highlight on screen."""
        if which == "moment" and self.moment:
            m = self.moment
            clip, kind = self.clip.part(m.start, m.end, m.title), "Highlight"
        elif which == "part" and self.mark_in is not None:
            end = self.mark_out if self.mark_out is not None else len(self.clip.frames) - 1
            start, end = sorted((int(self.mark_in), int(end)))
            if end - start < RATE // 2:
                self.app.renderer.show_toast("Mark a longer part first (half a second at least)")
                return
            clip, kind = self.clip.part(start, end), "Clip"
        else:
            clip, kind = self.clip, "Match"
        try:
            path = clip.save(replay.replays_folder() / replay.file_name(clip, kind), kind.lower())
        except OSError as e:
            self.app.renderer.show_toast(f"Couldn't save: {e.strerror or e}")
            return
        self.app.sound_manager.play("countdown_go.wav")
        self.app.renderer.show_toast(f"{kind} saved to Replays ({clip.length:.0f} s)")
        return path

    # ---------------- Controls ----------------

    def seek(self, frame):
        self.position = float(max(0, min(len(self.clip.frames) - 1, frame)))
        self.end = len(self.clip.frames) - 1 if self.mode == "viewer" else self.end
        self.reset_effects()

    def jump_moment(self, step):
        """The previous or next highlight on the timeline."""
        if not self.moments:
            return
        here = self.position
        starts = sorted(m.start for m in self.moments)
        if step > 0:
            later = [s for s in starts if s > here + 2]
            self.seek(later[0] if later else starts[0])
        else:
            earlier = [s for s in starts if s < here - RATE]
            self.seek(earlier[-1] if earlier else starts[-1])
        self.playing = True

    def timeline_frame(self, pos):
        rect = self.ui_hitboxes.get("replay_timeline")
        if rect is None:
            return None
        k = max(0.0, min(1.0, (pos[0] - rect.left) / max(1, rect.width)))
        return k * (len(self.clip.frames) - 1)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self.idle = 0.0
            if self.dragging:
                frame = self.timeline_frame(self.app.window_to_base(event.pos))
                if frame is not None:
                    self.seek(frame)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        if event.type == pygame.KEYDOWN:
            self.idle = 0.0
            key = event.key
            if key == pygame.K_ESCAPE:
                self.leave()
            elif self.mode != "viewer":
                if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT):
                    self.finished() if self.mode == "reel" else self.leave()
                elif key == pygame.K_s:
                    self.save("moment")
            else:
                if key == pygame.K_SPACE:
                    self.toggle_play()
                elif key == pygame.K_LEFT:
                    self.seek(self.position - (1 if not self.playing else 5 * RATE))
                elif key == pygame.K_RIGHT:
                    self.seek(self.position + (1 if not self.playing else 5 * RATE))
                elif key == pygame.K_i:
                    self.mark_in = self.position
                elif key == pygame.K_o:
                    self.mark_out = self.position
                elif key == pygame.K_HOME:
                    self.seek(0)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.idle = 0.0
            pos = self.app.window_to_base(event.pos)
            key = self.hit_test(pos)
            if self.mode != "viewer":
                if key == "replay_save":
                    self.save("moment")
                elif key == "replay_back":
                    self.leave()
                else:
                    self.finished() if self.mode == "reel" else self.leave()
                return
            if key == "replay_timeline":
                self.dragging = True
                frame = self.timeline_frame(pos)
                if frame is not None:
                    self.seek(frame)
            elif key == "replay_play":
                self.toggle_play()
            elif key == "replay_prev":
                self.jump_moment(-1)
            elif key == "replay_next":
                self.jump_moment(1)
            elif key == "replay_speed":
                self.speed = (self.speed + 1) % len(SPEEDS)
            elif key == "replay_in":
                self.mark_in = self.position
                if self.mark_out is not None and self.mark_out < self.mark_in:
                    self.mark_out = None
            elif key == "replay_out":
                self.mark_out = self.position
                if self.mark_in is None:
                    self.mark_in = 0.0
                elif self.mark_out < self.mark_in:
                    self.mark_in, self.mark_out = self.mark_out, self.mark_in
            elif key == "replay_clear":
                self.mark_in = self.mark_out = None
            elif key == "replay_save_part":
                self.save("part")
            elif key == "replay_save_all":
                self.save("all")
            elif key == "replay_back":
                self.leave()

    def toggle_play(self):
        if not self.playing and self.position >= len(self.clip.frames) - 1:
            self.seek(0)
        self.playing = not self.playing


def play_event(app, view, kind, v):
    """The sound and sparks of one thing that happened in a match, for a replay or an online guest."""
    sound, fx = app.sound_manager, app.fx
    try:
        if kind == "hit":
            paddle = view.p1 if v[0] == 1 else view.p2
            paddle.flash = 1.0
            if sound.paddle_hit_sound:
                sound.play("Hu.wav" if v[0] == 1 else "Tao.wav")
            fx.spark(v[1], v[2], 22, (255, 122, 44) if v[0] == 1 else (120, 190, 255), speed = 520)
        elif kind == "score":
            if sound.score_sound:
                sound.play("euugh.wav")
            app.renderer.shake(14, 0.3)
        elif kind == "pickup":
            key = view.kind(v[0])
            if key:
                from game.powerups import BY_KEY, FAMILY_COLOURS
                k = BY_KEY[key]
                ball = view.ball
                view.powerups.popups.append([k.name, (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2, 0.0,
                                             FAMILY_COLOURS[k.family]])
                sound.play("countdown_go.wav")
        elif kind in ("teleport", "swap"):
            sound.play("hmyoop!.wav")
        elif kind in ("wall", "stone"):
            fx.spark(v[0], v[1], 8, (255, 186, 96), speed = 300, life = .45)
        elif kind == "blink":
            sound.play("countdown_tick.wav", multiplier = 0.35)
    except (IndexError, TypeError, ValueError):
        pass                  # a damaged or unknown event is skipped
