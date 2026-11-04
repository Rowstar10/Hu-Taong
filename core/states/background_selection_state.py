import pygame, math

from config import BASE_W, BASE_H
from helpers import clamp
from render.ui.background_thumbnail import BackgroundThumbnail
from core.states.base_state import State


class BackgroundSelectionState(State):
    NAME = "background_selection"
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        self.buttons = []

        # Thumbnails scroll inside this area, between the title and Back button
        self.view = pygame.Rect(0, int(BASE_H * 0.18), BASE_W, int(BASE_H * 0.72))
        self.track = pygame.Rect(0, self.view.top, 16, self.view.height)
        self.row_h = 0
        self.scroll = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.dragging_scrollbar = False

    def enter(self, **kwargs):
        super().enter(**kwargs)
        display = self.app.settings.display
        cols = 6
        rows = math.ceil(len(display.backgrounds) / cols)
        spacing = 30
        thumb_w, thumb_h = 256, 144

        grid_w  = cols * thumb_w + (cols - 1) * spacing
        grid_h = rows * thumb_h + (rows - 1) * spacing

        self.row_h = thumb_h + spacing
        self.max_scroll = max(0, grid_h - self.view.height)

        start_x = (BASE_W - grid_w) // 2
        start_y = self.view.top + max(0, (self.view.height - grid_h) // 2)
        self.track.left = start_x + grid_w + spacing

        for i, name in enumerate(display.backgrounds):

            col = i % cols
            row = i // cols

            x = start_x + col*(thumb_w + spacing)
            y = start_y + row*(thumb_h + spacing)

            rect = (x,y,thumb_w,thumb_h)

            image = self.app.backgrounds.thumb(name)

            button = BackgroundThumbnail(rect, image,
                action = lambda n=i: self.select_background(n), art = self.app.art)
            button.grid_y = y

            self.buttons.append(button)

        # Open with the current background in view
        current_y = (display.background // cols) * self.row_h
        self.scroll_to(current_y - (self.view.height - thumb_h) // 2)
        self.scroll = self.scroll_target

    def update(self, dt):
        super().update(dt)
        display = self.app.settings.display
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        in_view = self.view.collidepoint(mouse_pos)

        self.scroll += (self.scroll_target - self.scroll) * min(1, 16 * dt)

        for i, button in enumerate(self.buttons):
            button.rect.y = button.grid_y - int(self.scroll)
            button.selected = i == display.background
            button.update(mouse_pos)
            button.hovered = button.hovered and in_view

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_background_selection(self, screen)

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.pop_state()
            if event.key == pygame.K_UP:
                self.scroll_to(self.scroll_target - self.row_h)
            if event.key == pygame.K_DOWN:
                self.scroll_to(self.scroll_target + self.row_h)
            if event.key == pygame.K_PAGEUP:
                self.scroll_to(self.scroll_target - self.view.height)
            if event.key == pygame.K_PAGEDOWN:
                self.scroll_to(self.scroll_target + self.view.height)

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_to(self.scroll_target - event.y * self.row_h)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)
            if key == "back":
                self.pop_state()
            if key == "scrollbar":
                self.dragging_scrollbar = True
                self.scroll_from_mouse(mouse_pos[1])

            for button in self.buttons:
                if button.hovered:
                    button.action()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scrollbar = False

        if event.type == pygame.MOUSEMOTION and self.dragging_scrollbar:
            self.scroll_from_mouse(self.app.window_to_base(event.pos)[1])

    def scroll_to(self, y):
        self.scroll_target = clamp(y, 0, self.max_scroll)

    def scrollbar_handle(self):
        content_h = self.max_scroll + self.view.height
        h = max(60, self.track.height * self.view.height // content_h)
        y = self.track.top + (self.track.height - h) * self.scroll / self.max_scroll
        return pygame.Rect(self.track.left, int(y), self.track.width, h)

    def scroll_from_mouse(self, my):
        handle_h = self.scrollbar_handle().height
        percent = (my - self.track.top - handle_h / 2) / (self.track.height - handle_h)
        self.scroll_to(percent * self.max_scroll)
        self.scroll = self.scroll_target

    def select_background(self, index):
        settings = self.app.settings.display
        settings.background = index
        new_bg_name = settings.backgrounds[index]
        self.app.show_background(new_bg_name)

        self.app.state_manager.pop_state(mute = True)
        self.app.sound_manager.play("enter_state.wav")
