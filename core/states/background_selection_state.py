import pygame, math

from config import BASE_W, BASE_H
from render import theme
from render.ui.background_thumbnail import BackgroundThumbnail
from core.states.base_state import State


class BackgroundSelectionState(State):
    NAME = "background_selection"
    is_menu = True
    
    def __init__(self, app):
        super().__init__(app)
        self.buttons = []

    def enter(self, **kwargs):
        super().enter(**kwargs)
        cols = 4
        rows = math.ceil(len(self.app.settings.display.backgrounds) / cols)
        spacing = 30
        thumb_w, thumb_h = 256, 144

        grid_w  = cols * thumb_w + (cols - 1) * spacing
        grid_h = rows * thumb_h + (rows - 1) * spacing

        start_x = (BASE_W - grid_w) // 2
        start_y = (BASE_H - grid_h) // 2

        for i, name in enumerate(self.app.settings.display.backgrounds):

            col = i % cols
            row = i // cols

            x = start_x + col*(thumb_w + spacing)
            y = start_y + row*(thumb_h + spacing)

            rect = (x,y,thumb_w,thumb_h)

            image = self.app.thumbnail_cache[name]

            button = BackgroundThumbnail(rect, image,
                action = lambda n=i: self.select_background(n))

            self.buttons.append(button)
            
    def update(self, dt):
        super().update(dt)
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        for button in self.buttons:
            button.update(mouse_pos)
            
    def draw(self, screen):
        super().draw(screen)
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        font = self.app.font_manager.get("helvetica", int(BASE_H * 0.1), bold=True)
        surf = font.render(f"Choose a background", True, theme.ORANGE)
        
        gap_x = int(BASE_W * 0.02)
        gap_y = int(BASE_H * 0.02)
        
        x = BASE_W // 2
        y = int(BASE_H * 0.1)
                      
        rect = surf.get_rect(center=(x, y))
        screen.blit(surf, rect)

        current_y = rect.bottom + 11 * gap_y
        
        for button in self.buttons:
            button.draw(screen)

        # -------- Back Button --------
        font = self.app.font_manager.get("helvetica", int(BASE_H * 0.05), bold=True)
        back_surf = font.render("Back", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (BASE_W - back_w) // 2
        back_y = BASE_H - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        self.ui_hitboxes["back"] = back_rect

    def handle_event(self, event):
        super().handle_event(event)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            if key == "back":
                self.pop_state()
            
            for button in self.buttons:
                if button.hovered:
                    button.action()

    def select_background(self, index):
        settings = self.app.settings.display
        settings.background = index
        new_bg_name = settings.backgrounds[index]
        self.app.bg_current = self.app.background_cache[new_bg_name]

        self.app.state_manager.pop_state(mute = True)
        self.app.sound_manager.play("enter_state.wav")
