import os, pygame, random, time
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
        
        self.FADE_BG_TIMER = pygame.USEREVENT
        self.FADE_DELAY = pygame.USEREVENT + 2
        self.bg_fader = pygame.time.set_timer(self.FADE_BG_TIMER, 30000)
        self.fading_bg = False
        
        self.MUSIC_END = pygame.USEREVENT + 1
        pygame.mixer.init()
        pygame.mixer.music.set_endevent(self.MUSIC_END)
        self.ignore_music_end = False

        self.keys_down = set()
        self.settings = Settings(self)
        self.state_manager = StateManager(self)
        self.renderer = Renderer(self)
        self.hud = Hud(self)
        self.ui_layout = UILayout(self)
        self.fonts = FontManager(self)
        self.sound = SoundManager(self)
 
        self.background_cache = {}
        self.thumbnail_cache = {}

        THUMB_SIZE = (256, 144)

        for name in self.settings.display.backgrounds:
            img = pygame.image.load(IMAGE_DIR / name).convert()
            
            self.background_cache[name] = pygame.transform.smoothscale(
                img, self.base_res)
            
            self.thumbnail_cache[name] = pygame.transform.smoothscale(
                img, THUMB_SIZE)
            
        self.clock = pygame.time.Clock()
        self.dt = 0.1
        self.timer = 0
        self.running = True

        self.state_manager.set_state("main_menu", mute = True)

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

    def run(self):
        while self.running:
            self.state_manager.process_changes()
            self.loop()
            self.clock_tick()
            
        pygame.quit()

    def clock_tick(self):
        settings = self.settings.display
        max_fps = settings.max_fps_options[settings.max_fps]

        if max_fps == "Unlimited":
            self.dt = self.clock.tick() / 1000
        else:
            self.dt = self.clock.tick(max_fps) / 1000
        
    def quit(self):
        self.sound.play("exit_state.wav")
        while pygame.mixer.get_busy():
            pygame.event.poll() 
        self.running = False

    def fade_backgrounds(self):
        self.fade_timer += self.dt
        progress = self.fade_timer / self.fade_duration
        progress = max(0, min(progress, 1))

        old_alpha = int(255 * (1 - progress))
        new_alpha = int(255 * progress)

        self.old_background.set_alpha(old_alpha)
        self.new_background.set_alpha(new_alpha)

        self.virtual.blit(self.old_background, (0, 0))
        self.virtual.blit(self.new_background, (0, 0))
        
        current_state = self.state_manager.current()
        if current_state and current_state.is_overlay:
            for state in self.state_manager.stack[:-1]:
                if getattr(state, "background_img", False):
                    self.virtual.blit(self.old_background, (0, 0))
                    self.virtual.blit(self.new_background, (0, 0))
                state.draw(self.virtual)
                
        if getattr(current_state, "background_img", False):
            self.virtual.blit(self.background_cache[current_state.background_img], (0, 0))

        if progress >= 1:
            self.fading_bg = False
        
    # ---------------- Main loop ----------------

    def loop(self):
        settings = self.settings.display
        self.timer -= self.dt
        
        if settings.show_fps and self.timer <= 0:
            self.fps = round(1 / self.dt, 1)
            self.timer = 0.1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                break

            if event.type == pygame.VIDEORESIZE:
                self.current_resolution = event.w, event.h
                self.settings.display.resolution = self.current_resolution
                self.apply_display_mode()

            if event.type == self.FADE_DELAY:
                current_state = self.state_manager.current()
                display = self.settings.display
                
                if current_state:
                    for state in self.state_manager.stack:
                        if getattr(state, "background_img", False):
                            self.old_background = self.background_cache[state.background_img]
                            state.background_img = random.choice(display.backgrounds)
                            self.new_background = self.background_cache[state.background_img]

                            from core.states.game_state import GameState
                            if isinstance(state, GameState):
                                display.game_background = display.backgrounds.index(state.background_img)
                            else:
                                display.menu_background = display.backgrounds.index(state.background_img)
                                
                            break
                
                self.fading_bg = True
                self.fade_duration = 5
                self.fade_timer = 0
                
                pygame.time.set_timer(self.FADE_BG_TIMER, 30000)
                
            elif event.type == self.FADE_BG_TIMER and self.settings.display.rotate_backgrounds:
                delay = random.randint(0, 30000)
                pygame.time.set_timer(self.FADE_DELAY, delay, 1)
                
            if event.type == self.MUSIC_END:
                if self.ignore_music_end:
                    self.ignore_music_end = False
                    continue
                
                audio = self.settings.audio                
                if audio.loop_music:
                    if self.sound.music_type == "menu":
                        music = audio.menu_track[audio.menu_music]
                    elif self.sound.music_type == "game":
                        music = audio.game_track[audio.game_music]
                    elif self.sound.music_type == "win":
                        music = audio.win_track[audio.win_music]
                    elif self.sound.music_type == "lose":
                        music = audio.lose_track[audio.lose_music]
                else:
                    if self.sound.music_type == "menu":
                        music = random.choice(audio.menu_track)
                        audio.menu_music = audio.menu_track.index(music)
                    elif self.sound.music_type == "game":
                        music = random.choice(audio.game_track)
                        audio.game_music = audio.game_track.index(music)
                    elif self.sound.music_type == "win":
                        music = random.choice(audio.win_track)
                        audio.win_music = audio.win_track.index(music)
                    elif self.sound.music_type == "lose":
                        music = random.choice(audio.lose_track)
                        audio.lose_music = audio.lose_track.index(music)
                    
                self.sound.play_music(music)
                                
            if event.type == pygame.KEYDOWN:
                self.keys_down.add(event.key)
                
            if event.type == pygame.KEYUP:
                self.keys_down.discard(event.key)   

            self.state_manager.handle_event(event)
            
        self.state_manager.update(self.dt)

        if self.fading_bg:
            self.fade_backgrounds()
            
        else:
            current_state = self.state_manager.current()
            if current_state and current_state.is_overlay:
                for state in self.state_manager.stack[:-1]:
                    if getattr(state, "background_img", False):
                        self.virtual.blit(self.background_cache[state.background_img], (0, 0))
                    state.draw(self.virtual)
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
