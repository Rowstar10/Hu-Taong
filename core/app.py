import os, pygame, random

from config import BASE_W, BASE_H, RESOLUTIONS, IMAGE_DIR
from core import save_data
from core.settings import Settings
from core.stats import Stats
from core.sound_manager import SoundManager
from core.state_manager import StateManager
from core.states.base_state import State
from render import theme
from render.font_manager import FontManager
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
        self.ui_layout = UILayout(self)
        self.renderer = Renderer(self)
        self.hud = Hud(self)
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
        self.display_mode_index = 1
        self.display_mode = self.display_modes[self.display_mode_index]
        self.apply_display_mode()
        
        self.virtual = pygame.Surface(self.base_res).convert()
        self.dim_surf: pygame.Surface | None = None
        self.dim_last: float = -1.0

        # ---------- Background Cache ----------
        self.background_cache = {}
        self.thumbnail_cache = {}
        
        display = self.settings.display
        for bg in display.backgrounds:
            img = pygame.image.load(IMAGE_DIR / bg).convert()  # opaque -> much faster full-screen blits
            self.background_cache[bg] = pygame.transform.smoothscale(img, self.base_res)
            self.thumbnail_cache[bg] = pygame.transform.smoothscale(img, (256, 144))

        bg_init = display.backgrounds[display.background]
        self.bg_current = self.background_cache[bg_init]
        
        # ---------- Events ----------
        self.keys_down = set()
        self.BG_FADE = pygame.USEREVENT
        
        delay = random.randint(30000, 60000)
        pygame.time.set_timer(self.BG_FADE, delay)
        
        self.bg_next = None
        self.bg_transition_active = False
        self.bg_transition_time = 0
        self.bg_transition_duration = 5

        # ---------- Timing + Main Menu ----------
        self.clock = pygame.time.Clock()
        self.clock_tick()
        self.timer = 0
        self.fps = 0.0
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

    def window_to_base(self, pos):
        mx = pos[0] * self.sx
        my = pos[1] * self.sy
        return mx, my

    def start_bg_transition(self):
        display = self.settings.display
        new_bg = random.choice(display.backgrounds)
        self.bg_next = self.background_cache[new_bg]
        
        if self.bg_current == self.bg_next:
            self.bg_next = None
            return

        display.background = display.backgrounds.index(new_bg)
        self.bg_transition_active = True
        self.bg_transition_time = 0

    def draw_background(self):
        self.virtual.blit(self.bg_current, (0, 0))
        
        if self.bg_transition_active:
            self.bg_transition_time += self.dt
            t = self.bg_transition_time / self.bg_transition_duration
            t = max(0, min(t, 1))
            t = t * t * (3 - 2 * t)
            
            alpha = int(255 * t)            
            self.bg_next.set_alpha(alpha)
            self.virtual.blit(self.bg_next, (0, 0))

            if t >= 1:
                self.bg_next.set_alpha(None)
                self.bg_current = self.bg_next
                self.bg_next = None
                self.bg_transition_active = False

    # ---------------- Run / Main Loop / Clock Tick / Quit ----------------

    def run(self):
        while self.running:
            self.state_manager.process_changes()
            self.loop()
            self.clock_tick()
            
        pygame.quit()
            
    def loop(self):
        settings = self.settings.display
        self.timer -= self.dt

        # ---------- Calculate FPS ----------
        if settings.show_fps and self.timer <= 0:
            self.fps = round(self.clock.get_fps(), 1)  # not 1 / dt: dt can be 0 at Unlimited FPS
            self.timer = 0.1

        # ---------- Handle Events ----------
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

            # ---------- Background Rotation ----------
            if event.type == self.BG_FADE:
                if settings.rotate_backgrounds:
                    self.start_bg_transition()
                delay = random.randint(30000, 60000)
                pygame.time.set_timer(self.BG_FADE, delay)

            # ---------- State-Specific Events ----------
            self.state_manager.handle_event(event)

        # ---------- Update ----------
        self.sound_manager.update()
        self.state_manager.update(self.dt)

        # ---------- Draw Background & Dim Overlay ----------
        self.virtual.fill((0, 0, 0))
        self.draw_background()

        dim = settings.dim
        if dim > 0:
            if self.dim_surf is None or self.dim_last != dim:
                self.dim_surf = pygame.Surface(self.base_res, pygame.SRCALPHA)
                self.dim_surf.fill((0, 0, 0, int(255 * dim)))
                self.dim_last = dim
            self.virtual.blit(self.dim_surf, (0, 0))

        # ---------- Draw States ----------
        current_state = self.state_manager.current()
        
        if getattr(current_state, "is_overlay", False):
            for state in self.state_manager.stack[:-1]:
                state.draw(self.virtual)
                
        current_state.draw(self.virtual)

        # ---------- Now-playing toast ----------
        self.renderer.draw_toast(self.virtual, self.dt)

        # ---------- Show FPS ----------
        if settings.show_fps:
            if not hasattr(self, "fps_font"):
                self.fps_font = self.font_manager.get("helvetica", int(BASE_H * 0.02), bold=True)
            fps_surf = self.fps_font.render(f"{self.fps} FPS", True, theme.WHITE)
            self.virtual.blit(fps_surf, (BASE_W - 3 * fps_surf.get_width() // 2, BASE_H - 2 * fps_surf.get_height()))

        # ---------- Scale + Flip ----------
        pygame.transform.scale(self.virtual, self.current_resolution, self.display)         
        pygame.display.flip()

    def clock_tick(self):
        settings = self.settings.display
        max_fps = settings.max_fps_options[settings.max_fps]
        self.dt = (self.clock.tick() if max_fps == "Unlimited"
                   else self.clock.tick(max_fps)) / 1000

    def quit(self):
        save_data.save(self)
        self.sound_manager.play("exit_state.wav")
        while pygame.mixer.get_busy():
            pygame.event.poll()
            pygame.time.wait(10)
        self.running = False
