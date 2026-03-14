import pygame

from config import BASE_W, BASE_H
from core.state_registry import StateRegistry
from render.ui.background_thumbnail import BackgroundThumbnail
from core.states.base_state import State
from core.states.background_selection_state import BackgroundSelectionState

@StateRegistry.register_state("display")
class DisplaySettingsState(State):
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        settings = self.app.settings.display
        self.menu_name = settings.backgrounds[settings.menu_background]
        self.game_name = settings.backgrounds[settings.game_background]
        self.dragging_dim = False

        menu_x = BASE_W // 2 - 256 - 50
        menu_y = BASE_H - 280

        self.res_index = self.app.res_index
        self.display_mode_index = self.app.display_mode_index
        
        self.menu_thumb = BackgroundThumbnail(
            rect=(menu_x, menu_y, 256, 144),
            image=self.app.thumbnail_cache[self.menu_name],
            action=lambda: self.open_background_selector("menu"))
        
        game_x = BASE_W // 2 + 50
        game_y = BASE_H - 280
        
        self.game_thumb = BackgroundThumbnail(
            rect=(game_x, game_y, 256, 144),
            image=self.app.thumbnail_cache[self.game_name],
            action=lambda: self.open_background_selector("game"))

        self.thumbnails = [self.menu_thumb, self.game_thumb]
        
    def draw(self, screen):
        super().draw(screen)
        settings = self.app.settings.display
        
        self.app.renderer.draw_display_settings_menu(self, screen)
        
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        self.menu_name = settings.backgrounds[settings.menu_background]
        self.game_name = settings.backgrounds[settings.game_background]
        
        self.menu_thumb.image = self.app.thumbnail_cache[self.menu_name]
        self.game_thumb.image = self.app.thumbnail_cache[self.game_name]
        
        for thumb in self.thumbnails:
            thumb.update(mouse_pos)
            thumb.draw(screen)

    def handle_event(self, event):
        super().handle_event(event)
        
        settings = self.app.settings.display
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            settings = self.app.settings.display
            mouse_pos = self.app.window_to_base(event.pos)
            mx, my = mouse_pos
            
            for thumb in self.thumbnails:
                if thumb.rect.collidepoint(mouse_pos):
                    thumb.action()

            key = self.hit_test(mouse_pos)

            if key == "cycle_res_left":
                if self.app.display_mode != "fullscreen":
                    self.res_index = (self.res_index - 1) % len(self.app.resolutions)
            if key == "cycle_res_right":
                if self.app.display_mode != "fullscreen":
                    self.res_index = (self.res_index + 1) % len(self.app.resolutions)
                    
            if key == "cycle_mode_left":
                self.display_mode_index = (self.display_mode_index - 1) % len(self.app.display_modes)
            if key == "cycle_mode_right":
                self.display_mode_index = (self.display_mode_index + 1) % len(self.app.display_modes)
                
            if key == "apply":
                self.app.res_index = self.res_index
                self.app.display_mode_index = self.display_mode_index
                
                self.app.current_resolution = self.app.resolutions[self.res_index]
                self.app.display_mode = self.app.display_modes[self.display_mode_index]
                
                self.app.apply_display_mode()
                
            if key == "cycle_max_fps_left":
                settings.max_fps = (settings.max_fps - 1) % len(settings.max_fps_options)
            if key == "cycle_max_fps_right":
                settings.max_fps = (settings.max_fps + 1) % len(settings.max_fps_options)
            if key == "toggle_show_fps":
                settings.show_fps = not settings.show_fps
                
            if key == "dim_slider":
                self.dragging_dim = True
                settings.dim = self.update_slider_from_mouse("dim_slider", event)
                
            if key == "back":
                self.pop_state()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_dim:
            self.dragging_dim = False
            
        if event.type == pygame.MOUSEMOTION and self.dragging_dim:
            settings.dim = self.update_slider_from_mouse("dim_slider", event)

    def open_background_selector(self, target):
        self.app.state_manager.push_state("background_selection", target=target)
