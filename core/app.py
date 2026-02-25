from __future__ import annotations

import os, pygame

from config import FPS, BASE_W, BASE_H, RESOLUTIONS, IMAGE_DIR
from render.pygame_renderer import PygameRenderer
from render.hud import Hud
from core.states import State, MainMenuState
from core.sound import SoundManager


class App:
    def __init__(self):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.init()

        info = pygame.display.Info()
        self.native = info.current_w, info.current_h
        native_w, native_h = self.native
        
        self.resolutions = list(RESOLUTIONS)
        
        if self.native not in self.resolutions:
            self.resolutions.append(self.native)

        self.resolutions = [(w, h) for (w, h) in self.resolutions
                       if w <= native_w and h <= native_h]
        self.resolutions = sorted(self.resolutions, key=lambda r: r[0])
        
        self.current_resolution = self.native
        self.res_index = self.resolutions.index(self.current_resolution)

        self.display_modes = ["windowed", "borderless", "fullscreen"]
        self.display_mode_index = 1
        self.apply_display_mode()
        
        self.display = pygame.display.set_mode(self.current_resolution, pygame.RESIZABLE)
        self.virtual = pygame.Surface((BASE_W, BASE_H)).convert_alpha()
        pygame.display.set_caption("Hu Taong")
        self.set_icon()

        pygame.mixer.init()
        self.sound = SoundManager()
        self.dragging_volume = False

        self.clock = pygame.time.Clock()
        self.running = True

        self.keys_down = set()
        self.ui_hitboxes = {}

        self.renderer = PygameRenderer(self)
        self.hud = Hud(self)

        self.states = []
        self.set_state(MainMenuState(self))

        self.difficulties = ["Baby", "Easy", "Medium", "Hard", "Insane"]
        self.difficulty_index = 2  # Default to Medium

    def set_icon(self):
        try:
            icon_path = IMAGE_DIR / "icon.png"
            icon = pygame.image.load(str(icon_path)).convert_alpha()
            pygame.display.set_icon(icon)
        except Exception:
            return

    def set_state(self, state: State):
        # Exit everything currently on the stack
        while self.states:
            old = self.states.pop()
            old.exit()

        # Enter the new root
        self.states.append(state)
        state.enter()

    def push_state(self, state: State):
        self.states.append(state)
        state.enter()

    def pop_state(self):
        if self.states:
            old = self.states.pop()
            old.exit()

    def window_to_base(self, pos):
        mx, my = pos
        win_w, win_h = self.display.get_size()
        sx = BASE_W / win_w
        sy = BASE_H / win_h
        return mx * sx, my * sy

    def apply_display_mode(self):
        mode = self.display_modes[self.display_mode_index]
        self.display_mode = mode

        if mode == "windowed":
            self.display = pygame.display.set_mode(self.current_resolution, pygame.RESIZABLE)

        elif mode == "borderless":
            self.display = pygame.display.set_mode(self.current_resolution, pygame.NOFRAME)

        elif mode == "fullscreen":
            self.display = pygame.display.set_mode(self.native, pygame.FULLSCREEN)
    
    def hit_test(self, pos):
        for key, rect in self.ui_hitboxes.items():
            if rect.collidepoint(pos):
                return key
        return None

    # ---------------- Main loop ----------------

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            top = self.states[-1] if self.states else None
            
            mx, my = self.window_to_base(pygame.mouse.get_pos())
            
            for event in pygame.event.get():                
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = self.window_to_base(event.pos)

                if event.type == pygame.KEYDOWN:
                    self.keys_down.add(event.key)
                    
                if event.type == pygame.KEYUP:
                    self.keys_down.discard(event.key)
    
                if top:
                    top.handle_event(event)
            
            if top:
                top.update(dt)

            self.virtual.fill((12, 14, 18))
            self.ui_hitboxes.clear()
            
            for state in self.states:
                state.draw(self.virtual)

            scaled = pygame.transform.smoothscale(self.virtual, self.display.get_size())
            self.display.blit(scaled, (0, 0))
            pygame.display.flip()

        pygame.quit()
