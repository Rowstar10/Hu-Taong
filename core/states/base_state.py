import pygame

class State:
    is_overlay = False
    is_menu = False
    is_game = False
    
    def __init__(self, app):
        self.app = app
        self.ui_hitboxes = {}
        
        if not self.is_overlay:
            settings = app.settings.display
            if self.is_game:
                self.background_img = settings.backgrounds[settings.game_background]
            else:
                self.background_img = settings.backgrounds[settings.menu_background]


    def enter(self, mute = False, **kwargs):
        if not mute:
            self.app.sound.play("enter_state.wav")

    def exit(self, mute = False, **kwargs):
        if not mute:
            self.app.sound.play("exit_state.wav")
        
    def update(self, dt):
        pass

    def draw(self, screen):
        self.ui_hitboxes.clear
        if not self.is_overlay:
            settings = self.app.settings.display
            if self.is_game:
                self.background_img = settings.backgrounds[settings.game_background]
            else:
                self.background_img = settings.backgrounds[settings.menu_background]

    def handle_event(self, event):        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            mx, my = mouse_pos
            key = self.hit_test(mouse_pos)

            if key in self.ui_hitboxes:
                self.app.sound.play("click.wav")

    def hit_test(self, pos):
        for key, rect in reversed(list(self.ui_hitboxes.items())):
            if rect.collidepoint(pos):
                return key
        return None

    def set_state(self, state, **kwargs):
        self.app.state_manager.set_state(state, **kwargs)

    def push_state(self, state, **kwargs):
        self.app.state_manager.push_state(state, **kwargs)

    def pop_state(self, **kwargs):
        self.app.state_manager.pop_state(**kwargs)
        

    def update_slider_from_mouse(self, slider, event):
        mx, my = self.app.window_to_base(event.pos)
        slider_rect = self.ui_hitboxes[slider]
        relative_x = mx - slider_rect.left
        percent = relative_x / slider_rect.width
        percent = max(0, min(1, percent))
        return percent
