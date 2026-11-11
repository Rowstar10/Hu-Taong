import os, pygame, random, time

from config import BASE_W, BASE_H, RESOLUTIONS, IMAGE_DIR, DEFAULT_DISPLAY_MODE, BG_OVERSCAN
from core import files, save_data
from core.backgrounds import Backgrounds
from core.settings import Settings
from core.stats import Stats
from core.sound_manager import SoundManager
from core.state_manager import StateManager
from core.states.base_state import State
from render import theme
from render.art import Art
from render.font_manager import FontManager
from render.fx import Ambience
from render.renderer import Renderer
from render.hud import Hud
from render.ui.layout import UILayout


class App:
    def __init__(self):
        # ---------- Initialise Pygame ----------
        pygame.init()
        pygame.mixer.init()
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.display.set_caption("Hu Taong")
        self.set_icon()

        # ---------- Core Systems ----------
        self.settings = Settings(self)
        self.sound_manager = SoundManager(self)
        self.state_manager = StateManager(self)
        self.font_manager = FontManager()
        self.art = Art(self)
        self.ui_layout = UILayout(self)
        self.renderer = Renderer(self)
        self.hud = Hud(self)
        self.fx = Ambience(self)
        self.stats = Stats()
        self.choose_file = files.ask      # the Save / Open dialog (tests swap in their own)
        self.net = None                   # an online session (core/net.py) while hosting or joining
        save_data.load(self)
        self.settings.online.apply()          # which server online games meet through
        
        self.state_manager.auto_register("core.states", State)
        
        # ---------- Resolutions ----------
        self.resolutions = list(RESOLUTIONS)

        info = pygame.display.Info()
        self.native_res = info.current_w, info.current_h
        self.native_w, self.native_h = self.native_res
        
        if self.native_res not in self.resolutions:
            self.resolutions.append(self.native_res)
            
        self.resolutions = [(w, h) for (w, h) in self.resolutions
                            if w <= self.native_w and h <= self.native_h]
        self.resolutions = sorted(self.resolutions, key=lambda r: r[0])

        self.base_res = BASE_W, BASE_H
        self.base_w, self.base_h = self.base_res
        
        self.current_resolution = self.native_res
        self.res_index = self.resolutions.index(self.current_resolution)

        # ---------- Display & Surfaces ----------
        self.display_modes = ["windowed", "borderless", "fullscreen"]
        self.display_mode_index = DEFAULT_DISPLAY_MODE
        self.display_mode = self.display_modes[self.display_mode_index]
        self.canvas = None
        self.apply_display_mode()

        # ---------- Backgrounds (loaded on a worker thread as they are needed) ----------
        display = self.settings.display
        self.backgrounds = Backgrounds(self, display.backgrounds)
        self.bg_offset = [0.0, 0.0]

        jobs = self.renderer.prewarm_jobs()
        for i, job in enumerate(jobs):
            job()
            if i % 12 == 0:
                self.renderer.draw_loading_screen(self.virtual, i / len(jobs))
                self.present()
                pygame.event.pump()

        self.idle_jobs = self.renderer.idle_jobs()

        self.bg_current = display.backgrounds[display.background]   # background names
        self.backgrounds.picture(self.bg_current)
        
        # ---------- Events ----------
        self.keys_down = set()
        self.BG_FADE = pygame.USEREVENT
        self.restart_bg_timer()
        
        self.bg_next = None
        self.bg_transition_active = False
        self.bg_transition_time = 0
        self.bg_transition_duration = 5

        # ---------- Timing + Main Menu ----------
        self.clock = pygame.time.Clock()
        self.clock_tick()
        self.timer = 0
        self.fps = 0.0
        self.cursor_idle = 0.0
        self.cursor_shown = True
        self.running = True
        
        self.state_manager.set_state("main_menu", mute = True)

    # ---------- Helper Methods ----------
    def set_icon(self):
        try:
            icon_path = IMAGE_DIR / "icon.png"
            icon = pygame.image.load(str(icon_path))
            pygame.display.set_icon(icon)
        except Exception:
            return

    def apply_display_mode(self):
        if self.display_mode == "windowed":
            flags = pygame.RESIZABLE

        elif self.display_mode == "borderless":
            flags = pygame.NOFRAME

        elif self.display_mode == "fullscreen":
            self.current_resolution = self.native_res
            self.res_index = self.resolutions.index(self.current_resolution)
            flags = pygame.FULLSCREEN

        self.display = pygame.display.set_mode(self.current_resolution, flags)
        self.update_scale()

    def update_scale(self):
        w, h = self.display.get_size()
        self.sx = BASE_W / w
        self.sy = BASE_H / h

        # At the game's own resolution everything is drawn straight onto the window,
        # which skips a full-screen scaling copy every frame
        if (w, h) == self.base_res:
            self.virtual = self.display
        else:
            if self.canvas is None:
                self.canvas = pygame.Surface(self.base_res).convert()
            self.virtual = self.canvas

    def window_to_base(self, pos):
        mx = pos[0] * self.sx
        my = pos[1] * self.sy
        return mx, my

    def reset_gameplay_settings(self):
        self.settings.gameplay.reset()

    def reset_display_settings(self):
        self.settings.display.reset()

        # Only rebuild the window if it actually changes, to avoid a flicker
        if (self.display_mode_index != DEFAULT_DISPLAY_MODE
                or self.current_resolution != self.native_res):
            self.display_mode_index = DEFAULT_DISPLAY_MODE
            self.display_mode = self.display_modes[self.display_mode_index]
            self.current_resolution = self.native_res
            self.res_index = self.resolutions.index(self.current_resolution)
            self.apply_display_mode()

    def restart_bg_timer(self):
        """Wait a while, as long as the Rotate setting asks, before the next background."""
        display = self.settings.display
        shortest, longest = display.rotate_waits[display.rotate_every]
        pygame.time.set_timer(self.BG_FADE, random.randint(shortest * 1000, longest * 1000))

    def reset_audio_settings(self):
        self.settings.audio.reset()
        self.sound_manager.reset()

    def reset_interface_settings(self):
        self.settings.interface.reset()

    def reset_all_settings(self):
        self.reset_gameplay_settings()
        self.reset_display_settings()
        self.reset_audio_settings()
        self.reset_interface_settings()

    def leave_online(self):
        """Close the online session, telling the other side."""
        if self.net:
            self.net.close()
            self.net = None

    def match_left(self, reason, match, result):
        """Online, the other player left (or went quiet) mid-match.  Say so, close whatever is open
        over the match (pause, settings, a replay), and show the end-of-match screen: no Play Again
        with nobody to play, but the replay and highlights are there to watch and save before
        leaving.  If the match had already ended, its result screen is up and just loses its
        rematch buttons."""
        self.renderer.show_toast(reason, important = True)
        sm = self.state_manager
        names = [getattr(s, "NAME", "") for s in sm.stack]
        if result in names or match not in names:
            return
        for _ in names[names.index(match) + 1:]:
            sm.pop_state(mute = True)
        if result == "win":
            game = sm.stack[names.index(match)].game
            you, friend = (game.p2, game.p1) if getattr(game.p1, "remote", False) else (game.p1, game.p2)
            sm.push_state("win", p1 = game.p1, p2 = game.p2, winner = you, loser = friend, left = reason, mute = True)
        else:
            sm.push_state("guest_result", left = reason, mute = True)

    def online_requests(self):
        """Hosting: the friend can pause the match for both, and resume it."""
        net = self.net
        if net.role == "guest":
            # tell the host what's open here, so the match waits while either of us is in a menu
            stack = self.state_manager.stack
            names = [getattr(s, "NAME", "") for s in stack]
            if "guest_match" in names:
                above = names[names.index("guest_match") + 1:]
                # only the pause screen, and what's opened from it (settings), hold the match
                net.menu = 0 if "guest_pause" not in above else 1 if above[-1] == "guest_pause" else 2
            # the host went back to the lobby: follow them there, still connected
            if net.status == "waiting" and "guest_match" in names:
                stack[names.index("guest_match")].back_to_lobby()
                return
            # the host has gone mid-match: say so, and end the match here (see match_left)
            if net.status == "lost" and "guest_match" in names and net.snaps:
                if not getattr(net, "left_shown", False):
                    net.left_shown = True
                    reason = ("Lost touch with your friend." if "Lost touch" in (net.reason or "")
                              else "Your friend left the match.")
                    self.match_left(reason, "guest_match", "guest_result")
                return
            # the host has gone: from any of the match's screens, back to the menu
            if net.status in ("lost", "refused"):
                name = getattr(self.state_manager.current(), "NAME", "")
                if name in ("guest_match", "guest_pause", "guest_result", "replay", "confirm_choice"):
                    self.renderer.show_toast(net.reason or "The online game ended.", important = True)
                    self.state_manager.set_state("main_menu", mute = True)
                    self.leave_online()
            return
        if net.game is None:
            return
        if net.friend_left:
            reason, net.friend_left, net.notice = net.friend_left, None, None
            self.match_left(reason, "game", "win")
            return
        top = self.state_manager.current()
        name = getattr(top, "NAME", "")
        if net.request("pause") and name == "game":
            self.state_manager.push_state("pause", mute = True, by_friend = True)
        if net.request("resume") and name == "pause":
            self.state_manager.pop_state(mute = True)
        if net.guest_menu == 2 and name == "game" and net.connected():
            self.state_manager.push_state("pause", mute = True, by_friend = True)
        if net.request("restart"):
            self.renderer.show_toast("Your friend asks to restart the match from 0-0: Reset Scores, on the pause screen, does it",
                                     important = True)
        if net.notice:
            self.renderer.show_toast(net.notice, important = True)
            net.notice = None

    def background_dim(self):
        """How dark the background picture is.  Behind a match (live, a replay, or online) the
        Court Dim setting darkens it too; it is baked into the picture, so it costs nothing a frame."""
        display = self.settings.display
        dim = display.dim
        stack = self.state_manager.stack
        if stack and getattr(stack[self.state_manager.screen_index()], "dims_court", False):
            court = display.court_dim_levels[display.court_dim] / 255
            dim = 1 - (1 - dim) * (1 - court)
        return round(dim, 3)

    def in_match(self):
        """True while a match is on screen with nothing laid over it."""
        return getattr(self.state_manager.current(), "is_game", False)

    def update_cursor(self, moved):
        # Out of the way during play; back as soon as the mouse moves
        if moved or not self.in_match():
            self.cursor_idle = 0.0
        else:
            self.cursor_idle += self.dt
        show = not (self.settings.interface.hide_cursor and self.in_match() and self.cursor_idle > 1.5)
        if show != self.cursor_shown:
            pygame.mouse.set_visible(show)
            self.cursor_shown = show

    def start_bg_transition(self):
        display = self.settings.display
        new_bg = random.choice(display.backgrounds)

        if self.bg_current == new_bg or self.bg_next:
            return

        # The fade starts once the worker thread has the picture ready
        self.bg_next = new_bg
        self.backgrounds.request(new_bg)
        display.background = display.backgrounds.index(new_bg)
        self.bg_transition_active = False
        self.bg_transition_time = 0

    def show_background(self, name):
        """Switch straight to a background, dropping any fade in progress."""
        if self.bg_next:
            self.backgrounds.get(self.bg_next, self.settings.display.dim).set_alpha(None)
        self.bg_current = name
        self.bg_next = None
        self.bg_transition_active = False

    def update_parallax(self):
        # The picture drifts against the cursor in menus and settles during play
        target = (0, 0)
        if self.fx.scene != "game":
            display = self.settings.display
            strength = display.parallax_strength[display.parallax]
            mx, my = self.window_to_base(pygame.mouse.get_pos())
            target = ((1 - 2 * mx / BASE_W) * BG_OVERSCAN[0] * strength,
                      (1 - 2 * my / BASE_H) * BG_OVERSCAN[1] * strength)

        ease = min(1, 3 * self.dt)
        self.bg_offset[0] += (target[0] - self.bg_offset[0]) * ease
        self.bg_offset[1] += (target[1] - self.bg_offset[1]) * ease

    def draw_background(self):
        self.update_parallax()
        pos = (self.bg_offset[0] - BG_OVERSCAN[0], self.bg_offset[1] - BG_OVERSCAN[1])
        dim = self.background_dim()
        self.virtual.blit(self.backgrounds.get(self.bg_current, dim), pos)

        if self.bg_next and not self.bg_transition_active and self.backgrounds.ready(self.bg_next):
            self.bg_transition_active = True

        if self.bg_transition_active:
            self.bg_transition_time += self.dt
            t = self.bg_transition_time / self.bg_transition_duration
            t = max(0, min(t, 1))
            t = t * t * (3 - 2 * t)

            alpha = int(255 * t)
            bg_next = self.backgrounds.get(self.bg_next, dim)
            bg_next.set_alpha(alpha)
            self.virtual.blit(bg_next, pos)

            if t >= 1:
                bg_next.set_alpha(None)
                self.bg_current = self.bg_next
                self.bg_next = None
                self.bg_transition_active = False

    # ---------------- Run / Main Loop / Clock Tick / Quit ----------------

    def run(self):
        while self.running:
            self.state_manager.process_changes()
            self.loop()
            self.clock_tick()

        # The worker threads stop only now: the frame that called quit() still draws with them
        self.backgrounds.close()
        self.renderer.close()
        self.sound_manager.close()
        pygame.quit()
            
    def loop(self):
        settings = self.settings.display
        self.timer -= self.dt

        # ---------- Calculate FPS ----------
        if settings.show_fps and self.timer <= 0:
            self.fps = round(self.clock.get_fps(), 1)  # not 1 / dt: dt can be 0 at Unlimited FPS
            self.timer = 0.1

        # ---------- Handle Events ----------
        moved = False
        for event in pygame.event.get():
            
            # ---------- Essential Events ----------
            if event.type == pygame.QUIT:
                self.quit()
                break
            
            if event.type == pygame.VIDEORESIZE:
                self.current_resolution = event.w, event.h
                self.settings.display.resolution = self.current_resolution
                self.apply_display_mode()
                
            if event.type == pygame.KEYDOWN:
                self.keys_down.add(event.key)

            if event.type == pygame.KEYUP:
                self.keys_down.discard(event.key)

            if event.type == pygame.MOUSEMOTION:
                moved = True

            # ---------- Auto-Pause ----------
            if event.type == pygame.WINDOWFOCUSLOST:
                self.keys_down.clear()
                # online, clicking away (to chat, say) mustn't stop the match for both players
                if self.settings.interface.auto_pause and self.in_match() and not self.net:
                    self.state_manager.push_state("pause", mute = True)

            # ---------- Background Rotation ----------
            if event.type == self.BG_FADE:
                if settings.rotate_backgrounds:
                    self.start_bg_transition()
                self.restart_bg_timer()

            # ---------- State-Specific Events ----------
            self.state_manager.handle_event(event)

        # ---------- Warm sprites while nobody is playing ----------
        if self.idle_jobs and not self.in_match():
            budget = time.perf_counter() + 0.0015
            while self.idle_jobs and time.perf_counter() < budget:
                self.idle_jobs.pop()()

        # ---------- Update ----------
        self.update_cursor(moved)
        self.sound_manager.update()
        if self.net:
            self.net.update(self.dt)
            self.online_requests()
        self.state_manager.update(self.dt)
        if self.net:
            self.net.send_due()               # online: this frame's news goes out now, not next frame

        # ---------- Draw Background (it covers the whole frame, and has the dim baked in) ----------
        self.draw_background()

        self.fx.update(self.dt)
        self.fx.draw_back(self.virtual)
        quiet_menus = self.fx.scene == "menu"     # in settings screens nothing drifts over the text
        if quiet_menus:
            self.fx.draw_front(self.virtual)

        # ---------- Draw States ----------
        stack = self.state_manager.stack

        for state in stack[self.state_manager.screen_index():]:
            state.draw(self.virtual)

        if not quiet_menus:
            self.fx.draw_front(self.virtual)
        self.fx.draw_overlays(self.virtual)

        # ---------- Now-playing toast, then tooltips over everything ----------
        self.renderer.draw_toast(self.virtual, self.dt)
        self.renderer.tips.draw(self.virtual, self.dt)

        # ---------- Show FPS ----------
        if settings.show_fps:
            if getattr(self, "fps_shown", None) != self.fps:
                font = self.font_manager.get("ui", int(BASE_H * 0.02), bold=True)
                self.fps_surf = font.render(f"{self.fps} FPS", True, theme.GOLD)
                self.fps_shown = self.fps
            fps_surf = self.fps_surf
            self.virtual.blit(fps_surf, (BASE_W - 3 * fps_surf.get_width() // 2, BASE_H - 2 * fps_surf.get_height()))

        self.present()

    def present(self):
        # ---------- Scale + Flip ----------
        if self.virtual is not self.display:
            pygame.transform.scale(self.virtual, self.display.get_size(), self.display)
        pygame.display.flip()

    def clock_tick(self):
        settings = self.settings.display
        max_fps = settings.max_fps_options[settings.max_fps]
        self.dt = (self.clock.tick() if max_fps == "Unlimited"
                   else self.clock.tick(max_fps)) / 1000

    def quit(self):
        save_data.save(self)
        self.leave_online()
        self.running = False

        # Let the goodbye sound finish.  The music and ambience would play on forever, so they
        # stop first, and the wait is capped so nothing still playing can hold the game open.
        self.sound_manager.stop_ambience()
        self.sound_manager.stop_music()
        channel = self.sound_manager.play("exit_state.wav")
        deadline = time.perf_counter() + 1.5
        while channel and channel.get_busy() and time.perf_counter() < deadline:
            pygame.event.poll()
            pygame.time.wait(10)
