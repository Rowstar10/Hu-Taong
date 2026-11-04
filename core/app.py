import os, pygame, random, time

from config import BASE_W, BASE_H, RESOLUTIONS, IMAGE_DIR, DEFAULT_DISPLAY_MODE, BG_OVERSCAN
from core import save_data
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
        save_data.load(self)
        
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
        dim = self.settings.display.dim
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
                if self.settings.interface.auto_pause and self.in_match():
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
        self.state_manager.update(self.dt)

        # ---------- Draw Background (it covers the whole frame, and has the dim baked in) ----------
        self.draw_background()

        self.fx.update(self.dt)
        self.fx.draw_back(self.virtual)

        # ---------- Draw States ----------
        stack = self.state_manager.stack

        for state in stack[self.state_manager.screen_index():]:
            state.draw(self.virtual)

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
        self.running = False

        # Let the goodbye sound finish.  The ambience loops forever, so it stops first,
        # and the wait is capped so nothing still playing can hold the game open.
        self.sound_manager.stop_ambience()
        self.sound_manager.play("exit_state.wav")
        deadline = time.perf_counter() + 1.5
        while pygame.mixer.get_busy() and time.perf_counter() < deadline:
            pygame.event.poll()
            pygame.time.wait(10)
