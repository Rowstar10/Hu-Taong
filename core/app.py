import os, pygame
import pygame._sdl2 as pg_sdl2

from config import BASE_W, BASE_H, RESOLUTIONS, IMAGE_DIR
from core.settings import Settings
from render.renderer import Renderer
from render.hud import Hud
from render.ui.layout import UILayout
from core.fonts import FontManager
from render import theme
from core.state_manager import StateManager
from core.sound import SoundManager

class App:
    def __init__(self):
        pygame.init()
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.display.set_caption("Hu Taong")
        self.set_icon()
        
        info = pygame.display.Info()
        self.native = info.current_w, info.current_h
        self.native_w, self.native_h = self.native

        self.base_res = BASE_W, BASE_H
        self.base_w, self.base_h = self.base_res
        
        self.resolutions = list(RESOLUTIONS)
        
        if self.native not in self.resolutions:
            self.resolutions.append(self.native)

        self.resolutions = [(w, h) for (w, h) in self.resolutions
                       if w <= self.native_w and h <= self.native_h]
        self.resolutions = sorted(self.resolutions, key=lambda r: r[0])
        
        self.current_resolution = self.native
        self.res_index = self.resolutions.index(self.current_resolution)

        self.display_modes = ["windowed", "borderless", "fullscreen"]
        self.display_mode_index = 1
        self.display_mode = self.display_modes[self.display_mode_index]
        
        self.display = pygame.display.set_mode(self.current_resolution, pygame.SCALED | pygame.NOFRAME)
        self.virtual = pygame.Surface(self.base_res).convert()

        self.dim_overlay = pygame.Surface(self.base_res, pygame.SRCALPHA)
        self.dim_overlay.fill((0, 0, 0, 180))
        
        pygame.mixer.init()

        self.keys_down = set()
        self.settings = Settings()
        self.state_manager = StateManager(self)
        self.renderer = Renderer(self)
        self.hud = Hud(self)
        self.ui_layout = UILayout(self)
        self.fonts = FontManager()
        self.sound = SoundManager()
 
        self.background_cache = {}
        self.thumbnail_cache = {}

        THUMB_SIZE = (256, 144)

        for name in self.settings.display.backgrounds:
            img = pygame.image.load(IMAGE_DIR / name).convert()
            
            self.background_cache[name] = pygame.transform.smoothscale(
                img, self.base_res)
            
            self.thumbnail_cache[name] = pygame.transform.smoothscale(
                img, THUMB_SIZE)

        self.state_manager.set_state("main_menu", mute = True)
        self.sound.play("startup.wav")

        self.timer = 0
        self.clock = pygame.time.Clock()
        self.running = True

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
            self.current_resolution = self.native
            self.res_index = self.resolutions.index(self.current_resolution)
            flags = pygame.FULLSCREEN

        self.display = pygame.display.set_mode(self.current_resolution, flags)
        
    def window_to_base(self, pos):
        mx, my = pos
        win_w, win_h = self.display.get_size()
        sx = BASE_W / win_w
        sy = BASE_H / win_h
        return mx * sx, my * sy

    def quit(self):
        self.running = False
        
    # ---------------- Main loop ----------------

    def run(self):
        while self.running:
            settings = self.settings.display
            
            max_fps = settings.max_fps_options[settings.max_fps]
            
            if max_fps == "Unlimited":
                self.dt = self.clock.tick() / 1000
            else:
                self.dt = self.clock.tick(max_fps) / 1000
                
            self.timer -= self.dt
            
            if settings.show_fps and self.timer <= 0:
                self.fps = round(1 / self.dt, 1)
                self.timer = 0.1
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                if event.type == pygame.KEYDOWN:
                    self.keys_down.add(event.key)
                    
                if event.type == pygame.KEYUP:
                    self.keys_down.discard(event.key)   
    
                self.state_manager.handle_event(event)
                
            self.state_manager.update(self.dt)

            current_state = self.state_manager.current()
            if current_state and current_state.is_overlay:
                for state in self.state_manager.stack[:-1]:
                    if getattr(state, "background_img", False):
                        self.virtual.blit(self.background_cache[state.background_img], (0, 0))
                    state.draw(self.virtual)
                self.virtual.blit(self.dim_overlay, (0, 0))
                
            if getattr(current_state, "background_img", False):
                self.virtual.blit(self.background_cache[current_state.background_img], (0, 0))

            dim = pygame.Surface(self.base_res, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 255 * settings.dim))
            self.virtual.blit(dim, (0, 0))
            
            self.state_manager.draw(self.virtual)

            if settings.show_fps:
                font = pygame.font.SysFont("Helvetica", int(BASE_H * 0.02), bold = True)
                fps_surf = font.render(f"{self.fps} FPS", True, theme.WHITE)
                self.virtual.blit(fps_surf, (BASE_W - 3 * fps_surf.get_width() // 2, BASE_H - 2 * fps_surf.get_height()))
            
            pygame.transform.scale(self.virtual, self.current_resolution, self.display)            
            pygame.display.flip()
            
        pygame.quit()      
