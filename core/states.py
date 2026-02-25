import pygame

from config import BASE_W, BASE_H
from render import theme
from game.hu_taong import Hu_Taong

class State:
    is_overlay = False
    
    def __init__(self, app):
        self.app = app

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass


class MainMenuState(State):
    def draw(self, screen):
        screen_w, screen_h = screen.get_size()
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        title_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.18), bold=True)
        subtitle_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.05), bold=True)
        font = pygame.font.SysFont("Helvetica", int(screen_h * 0.04), bold=True)
        small_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.02), bold=True)

        btn_w = 240
        gap_x = int(screen_w * 0.03)
        gap_y = int(screen_h * 0.03)
        
        # --------- Title ---------        
        title_surf = title_font.render("Hu Taong!", True, theme.RED)

        title_x = screen_w // 2
        title_y = int(screen_h * 0.35)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)
        
        # --------- Play Button ---------
        play_surf = subtitle_font.render("Play Game", True, theme.BLACK)

        play_w = btn_w
        play_h = play_surf.get_height() + gap_y
        play_x = (screen_w - play_w) // 2
        play_y = int(screen_h * 0.6)
        
        play_rect = pygame.Rect(play_x, play_y, play_w, play_h)
        play_color = theme.GREEN_HOVER if play_rect.collidepoint(mouse_pos) else theme.GREEN
        pygame.draw.rect(screen, play_color, play_rect, border_radius=12)
        screen.blit(play_surf, play_surf.get_rect(center=play_rect.center))

        current_y = play_rect.bottom + 2 * gap_y
        
        # --------- Settings Button ---------
        settings_surf = subtitle_font.render("Settings", True, theme.BLACK)

        settings_w = btn_w
        settings_h = settings_surf.get_height() + gap_y
        settings_x = screen_w // 2 + gap_x
        settings_y = current_y
        
        settings_rect = pygame.Rect(settings_x, settings_y, settings_w, settings_h)
        settings_color = theme.ORANGE_HOVER if settings_rect.collidepoint(mouse_pos) else theme.ORANGE
        pygame.draw.rect(screen, settings_color, settings_rect, border_radius=12)
        screen.blit(settings_surf, settings_surf.get_rect(center=settings_rect.center))

        # --------- Quit Button ---------
        quit_surf = subtitle_font.render("Quit Game", True, theme.BLACK)

        quit_w = btn_w
        quit_h = quit_surf.get_height() + gap_y
        quit_x = screen_w // 2 - quit_w - gap_x
        quit_y = current_y
        
        quit_rect = pygame.Rect(quit_x, quit_y, quit_w, quit_h)
        quit_color = theme.RED_HOVER if quit_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, quit_color, quit_rect, border_radius=12)
        screen.blit(quit_surf, quit_surf.get_rect(center=quit_rect.center))

        # -------- Assign Button Hitboxes ---------
        self.app.ui_hitboxes["play"] = play_rect
        self.app.ui_hitboxes["settings"] = settings_rect
        self.app.ui_hitboxes["quit"] = quit_rect

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))
            if key == "play":
                self.app.set_state(GameState(self.app))
            elif key == "settings":
                self.app.set_state(SettingsState(self.app))
            elif key == "quit":
                self.app.running = False


class SettingsState(State):
    def draw(self, screen):
        screen_w, screen_h = screen.get_size()
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        title_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.15), bold=True)
        subtitle_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.05), bold=True)
        font = pygame.font.SysFont("Helvetica", int(screen_h * 0.04), bold=True)
        small_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.02), bold=True)

        btn_w = 200
        gap_x = int(screen_w * 0.02)
        gap_y = int(screen_h * 0.02)

        # --------- Title ---------
        title_surf = title_font.render("Settings", True, theme.ORANGE)
        title_rect = title_surf.get_rect(center=(screen_w // 2, int(screen_h * 0.35)))
        screen.blit(title_surf, title_rect)

        # -------- Gameplay Settings Button --------
        gameplay_settings_surf = subtitle_font.render("Gameplay", True, theme.BLACK)
        gameplay_settings_w = btn_w
        gameplay_settings_h = gameplay_settings_surf.get_height() + gap_y
        gameplay_settings_x = screen_w // 2 - 3 * btn_w // 2 - gap_x
        gameplay_settings_y = int(screen_h * 0.6)

        gameplay_settings_rect = pygame.Rect(gameplay_settings_x, gameplay_settings_y, gameplay_settings_w, gameplay_settings_h)
        gameplay_settings_color = theme.GREEN_HOVER if gameplay_settings_rect.collidepoint(mouse_pos) else theme.GREEN
        pygame.draw.rect(screen, gameplay_settings_color, gameplay_settings_rect, border_radius=12)
        screen.blit(gameplay_settings_surf, gameplay_settings_surf.get_rect(center=gameplay_settings_rect.center))

        # -------- Display Settings Button --------
        display_settings_surf = subtitle_font.render("Display", True, theme.BLACK)
        display_settings_w = btn_w
        display_settings_h = display_settings_surf.get_height() + gap_y
        display_settings_x = (screen_w - btn_w) // 2
        display_settings_y = int(screen_h * 0.6)

        display_settings_rect = pygame.Rect(display_settings_x, display_settings_y, display_settings_w, display_settings_h)
        display_settings_color = theme.ORANGE_HOVER if display_settings_rect.collidepoint(mouse_pos) else theme.ORANGE
        pygame.draw.rect(screen, display_settings_color, display_settings_rect, border_radius=12)
        screen.blit(display_settings_surf, display_settings_surf.get_rect(center=display_settings_rect.center))

        current_y = display_settings_rect.bottom + 2 * gap_y

        # -------- Audio Settings Button --------
        audio_settings_surf = subtitle_font.render("Audio ", True, theme.BLACK)
        audio_settings_w = btn_w
        audio_settings_h = audio_settings_surf.get_height() + gap_y
        audio_settings_x = screen_w // 2 + btn_w // 2 + gap_x
        audio_settings_y = int(screen_h * 0.6)

        audio_settings_rect = pygame.Rect(audio_settings_x, audio_settings_y, audio_settings_w, audio_settings_h)
        audio_settings_color = theme.BLUE_HOVER if audio_settings_rect.collidepoint(mouse_pos) else theme.BLUE
        pygame.draw.rect(screen, audio_settings_color, audio_settings_rect, border_radius=12)
        screen.blit(audio_settings_surf, audio_settings_surf.get_rect(center=audio_settings_rect.center))

        current_y = audio_settings_rect.bottom + 2 * gap_y
        
        # -------- Back to Main Menu Button --------
        back_surf = subtitle_font.render("Back to Main Menu", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (screen_w - back_w) // 2
        back_y = screen_h - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        # -------- Hitboxes --------
        self.app.ui_hitboxes["gameplay"] = gameplay_settings_rect
        self.app.ui_hitboxes["display"] = display_settings_rect
        self.app.ui_hitboxes["audio"] = audio_settings_rect
        self.app.ui_hitboxes["main_menu"] = back_rect

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_state(MainMenuState(self.app))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))
            if key == "gameplay":
                self.app.set_state(GameplaySettingsState(self.app))
            if key == "display":
                self.app.set_state(DisplaySettingsState(self.app))
            if key == "audio":
                self.app.set_state(AudioSettingsState(self.app))
            if key == "main_menu":
                self.app.set_state(MainMenuState(self.app))

class GameplaySettingsState(State):
    def draw(self, screen):
        screen_w, screen_h = screen.get_size()
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        title_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.18), bold=True)
        subtitle_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.08), bold=True)
        font = pygame.font.SysFont("Helvetica", int(screen_h * 0.04), bold=True)
        small_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.02), bold=True)

        gap_x = int(screen_w * 0.02)
        gap_y = int(screen_h * 0.02)
        
        # --------- Title ---------        
        title_surf = title_font.render("Gameplay", True, theme.GREEN)

        title_x = screen_w // 2
        title_y = int(screen_h * 0.1)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)

        current_y = title_rect.bottom + 3 * gap_y

        # -------- Back to Settings Menu Button --------
        back_surf = font.render("Back to Settings Menu", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (screen_w - back_w) // 2
        back_y = screen_h - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        
        # -------- Hitboxes --------
        self.app.ui_hitboxes["settings"] = back_rect
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_state(SettingsState(self.app))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))
                
            if key == "settings":
                self.app.set_state(SettingsState(self.app))

class DisplaySettingsState(State):
    def draw(self, screen):
        screen_w, screen_h = screen.get_size()
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        title_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.18), bold=True)
        subtitle_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.08), bold=True)
        font = pygame.font.SysFont("Helvetica", int(screen_h * 0.04), bold=True)
        small_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.02), bold=True)

        gap_x = int(screen_w * 0.02)
        gap_y = int(screen_h * 0.02)
        
        # --------- Title ---------        
        title_surf = title_font.render("Display", True, theme.ORANGE)

        title_x = screen_w // 2
        title_y = int(screen_h * 0.1)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)

        current_y = title_rect.bottom + 11 * gap_y

        # ------ Display & Resolution ------
        res_settings_surf = subtitle_font.render("Resolution", True, theme.ORANGE)
        res_settings_rect = res_settings_surf.get_rect(center=(screen_w // 2, current_y))
        screen.blit(res_settings_surf, res_settings_rect)

        current_y = res_settings_rect.bottom + 3 * gap_y

        # ------- Resolution Cycle -------
        res = self.app.resolutions[self.app.res_index]
        res_surf = font.render(f"{res[0]} x {res[1]}", True, theme.WHITE)
        res_rect = res_surf.get_rect(center=(screen_w // 2, current_y))
        screen.blit(res_surf, res_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y
        
        left_rect = pygame.Rect(res_rect.left - btn_w - gap_x,
                                current_y - btn_h // 2,
                                btn_w, btn_h)
        
        left_color = theme.GRAY_HOVER if left_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, left_color, left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=left_rect.center))

        right_rect = pygame.Rect(res_rect.right + gap_x,
                                 current_y - btn_h // 2,
                                 btn_w, btn_h)
        
        right_color = theme.GRAY_HOVER if right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, right_color, right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=right_rect.center))

        current_y = right_rect.bottom + 2 * gap_y

        # ------ Display Mode Cycle ------
        mode_text = self.app.display_modes[self.app.display_mode_index].capitalize()
        mode_surf = font.render(mode_text, True, theme.WHITE)
        mode_rect = mode_surf.get_rect(center=(screen_w // 2, current_y))
        screen.blit(mode_surf, mode_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y

        mode_left_rect = pygame.Rect(mode_rect.left - btn_w - gap_x,
                                     current_y - btn_h // 2,
                                     btn_w, btn_h)
        
        mode_right_rect = pygame.Rect(mode_rect.right + gap_x,
                                      current_y - btn_h // 2,
                                      btn_w, btn_h)
        
        mode_left_color = theme.GRAY_HOVER if mode_left_rect.collidepoint(mouse_pos) else theme.GRAY
        mode_right_color = theme.GRAY_HOVER if mode_right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, mode_left_color, mode_left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=mode_left_rect.center))
        pygame.draw.rect(screen, mode_right_color, mode_right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=mode_right_rect.center))

        current_y = mode_right_rect.bottom + gap_y

        # -------- Apply Button --------
        apply_surf = font.render("Apply", True, theme.BLACK)
        apply_w = apply_surf.get_width() + gap_x
        apply_h = apply_surf.get_height() + gap_y
        apply_x = (screen_w - apply_w) // 2
        apply_y = current_y 

        apply_rect = pygame.Rect(apply_x, apply_y, apply_w, apply_h)
        apply_color = theme.ORANGE_HOVER if apply_rect.collidepoint(mouse_pos) else theme.ORANGE
        pygame.draw.rect(screen, apply_color, apply_rect, border_radius=12)
        screen.blit(apply_surf, apply_surf.get_rect(center=apply_rect.center))

        current_y = apply_rect.bottom + gap_y
        
        # -------- Back to Settings Menu Button --------
        back_surf = font.render("Back to Settings Menu", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (screen_w - back_w) // 2
        back_y = screen_h - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        
        # -------- Hitboxes --------
        self.app.ui_hitboxes["cycle_res_left"] = left_rect
        self.app.ui_hitboxes["cycle_res_right"] = right_rect
        self.app.ui_hitboxes["cycle_mode_left"] = mode_left_rect
        self.app.ui_hitboxes["cycle_mode_right"] = mode_right_rect
        self.app.ui_hitboxes["apply"] = apply_rect
        self.app.ui_hitboxes["settings"] = back_rect

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_state(SettingsState(self.app))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))
            
            if key == "cycle_res_left":
                if self.app.display_mode != "fullscreen":
                    self.app.res_index = (self.app.res_index - 1) % len(self.app.resolutions)
            if key == "cycle_res_right":
                if self.app.display_mode != "fullscreen":
                    self.app.res_index = (self.app.res_index + 1) % len(self.app.resolutions)
                    
            if key == "cycle_mode_left":
                self.app.display_mode_index = (self.app.display_mode_index - 1) % len(self.app.display_modes)
            if key == "cycle_mode_right":
                self.app.display_mode_index = (self.app.display_mode_index + 1) % len(self.app.display_modes)
                
            if key == "apply":
                self.app.current_resolution = self.app.resolutions[self.app.res_index]
                self.app.apply_display_mode()
                
            if key == "settings":
                self.app.set_state(SettingsState(self.app))

class AudioSettingsState(State):
    def draw(self, screen):
        screen_w, screen_h = screen.get_size()
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        title_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.18), bold=True)
        subtitle_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.08), bold=True)
        font = pygame.font.SysFont("Helvetica", int(screen_h * 0.04), bold=True)
        small_font = pygame.font.SysFont("Helvetica", int(screen_h * 0.02), bold=True)

        gap_x = int(screen_w * 0.02)
        gap_y = int(screen_h * 0.02)
        
        # --------- Title ---------        
        title_surf = title_font.render("Audio", True, theme.BLUE)

        title_x = screen_w // 2
        title_y = int(screen_h * 0.1)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)

        current_y = title_rect.bottom + 11 * gap_y

        # -------- Master Volume --------
        audio_settings_surf = subtitle_font.render("Master Volume", True, theme.BLUE)
        audio_settings_rect = audio_settings_surf.get_rect(center=(screen_w // 2, current_y))
        screen.blit(audio_settings_surf, audio_settings_rect)

        current_y = audio_settings_rect.bottom + 2 * gap_y

        # -------- Volume Slider --------
        slider_w = int(screen_w * 0.4)
        slider_h = int(screen_h * 0.02)
        slider_x = (screen_w - slider_w) // 2
        slider_y = current_y

        slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, slider_rect, border_radius=6)

        fill_w = int(slider_w * self.app.sound.master_volume)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.BLUE, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.5
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        current_y = slider_rect.bottom + 2 * gap_y

        # -------- Reset Volume --------
        reset_volume_surf = small_font.render("Reset", True, theme.BLACK)
        reset_volume_w = reset_volume_surf.get_width() + gap_x
        reset_volume_h = reset_volume_surf.get_height() + gap_y
        reset_volume_x = screen_w // 2 - reset_volume_w // 2
        reset_volume_y = current_y

        reset_volume_rect = pygame.Rect(reset_volume_x, reset_volume_y, reset_volume_w, reset_volume_h)
        reset_color = theme.WHITE_HOVER if reset_volume_rect.collidepoint(mouse_pos) else theme.WHITE
        pygame.draw.rect(screen, reset_color, reset_volume_rect, border_radius=12)
        screen.blit(reset_volume_surf, reset_volume_surf.get_rect(center=reset_volume_rect.center))

        current_y = reset_volume_rect.bottom + 2 * gap_y

        # -------- Paddle Sound Toggle --------
        paddle_text = "Paddle Sounds: ON" if self.app.sound.paddle_enabled else "Paddle Sounds: OFF"
        paddle_surf = font.render(paddle_text, True, theme.BLACK)

        paddle_w = paddle_surf.get_width() + gap_x
        paddle_h = paddle_surf.get_height() + gap_y
        paddle_x = screen_w // 2 - paddle_w - gap_x // 2
        paddle_y = current_y

        paddle_rect = pygame.Rect(paddle_x, paddle_y, paddle_w, paddle_h)
        
        if self.app.sound.paddle_enabled:
            paddle_color = theme.BLUE_HOVER if paddle_rect.collidepoint(mouse_pos) else theme.BLUE
        else:
            paddle_color = theme.RED_HOVER if paddle_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, paddle_color, paddle_rect, border_radius=12)
        screen.blit(paddle_surf, paddle_surf.get_rect(center=paddle_rect.center))
        
        # -------- Score Sound Toggles --------
        score_text = "Score Sound: ON" if self.app.sound.score_enabled else "Score Sound: OFF"
        score_surf = font.render(score_text, True, theme.BLACK)

        score_w = score_surf.get_width() + gap_x
        score_h = score_surf.get_height() + gap_y
        score_x = screen_w // 2 + gap_x // 2
        score_y = current_y

        score_rect = pygame.Rect(score_x, score_y, score_w, score_h)
        
        if self.app.sound.score_enabled:
            score_color = theme.BLUE_HOVER if score_rect.collidepoint(mouse_pos) else theme.BLUE
        else:
            score_color = theme.RED_HOVER if score_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, score_color, score_rect, border_radius=12)
        screen.blit(score_surf, score_surf.get_rect(center=score_rect.center))

        current_y = paddle_rect.bottom + 4 * gap_y

        # -------- Back to Settings Menu Button --------
        back_surf = font.render("Back to Settings Menu", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (screen_w - back_w) // 2
        back_y = screen_h - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        # -------- Hitboxes --------
        self.app.ui_hitboxes["volume_slider"] = slider_rect
        self.app.ui_hitboxes["reset_volume"] = reset_volume_rect
        self.app.ui_hitboxes["toggle_paddle_sounds"] = paddle_rect
        self.app.ui_hitboxes["toggle_score_sound"] = score_rect
        self.app.ui_hitboxes["settings"] = back_rect
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_state(SettingsState(self.app))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))
            
            if key == "volume_slider":
                self.app.dragging_volume = True
                self.update_volume_from_mouse(mx)
            if key == "reset_volume":
                self.app.sound.master_volume = 0.5

            if key == "toggle_paddle_sounds":
                self.app.sound.paddle_enabled = not self.app.sound.paddle_enabled
            if key == "toggle_score_sound":
                self.app.sound.score_enabled = not self.app.sound.score_enabled
                
            if key == "settings":
                self.app.set_state(SettingsState(self.app))
                
        if event.type == pygame.MOUSEMOTION and self.app.dragging_volume:
            mx, my = self.app.window_to_base(event.pos)
            self.update_volume_from_mouse(mx)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.app.dragging_volume:
            self.app.dragging_volume = False

    def update_volume_from_mouse(self, mouse_x):
        slider_rect = self.app.ui_hitboxes["volume_slider"]

        relative_x = mouse_x - slider_rect.left
        percent = relative_x / slider_rect.width
        percent = max(0, min(1, percent))

        self.app.sound.master_volume = percent
    
class GameState(State):
    def __init__(self, app):
        super().__init__(app)
        self.game = None

    def enter(self):
        if not self.game:
            self.game = Hu_Taong(self.app)
            self.game.start()

    def exit(self):
        if self.game:
            self.game.stop()
            self.game = None

    def handle_event(self, event):
        if not self.game:
            return

        # Pause toggle
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.push_state(PauseState(self.app, self))


        # UI clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))

            if key == "p1_ai":
                self.game.p1.ai_enabled = not self.game.p1.ai_enabled
            elif key == "p2_ai":
                self.game.p2.ai_enabled = not self.game.p2.ai_enabled

    def update(self, dt):           
        if self.game:
            self.game.update(dt)

    def draw(self, screen):
        if not self.game:
            return

        self.app.ui_hitboxes.clear()
        self.app.renderer.draw_world(screen, self.game)
        self.app.hud.draw(screen, self.game)

class PauseState(State):
    is_overlay = True
    
    def __init__(self, app, game_state):
        super().__init__(app)
        game_state.game.pause()
        self.game_state = game_state

    def update(self, dt):
        # Do NOT update gameplay
        pass

    def draw(self, screen):
        self.game_state.draw(screen)
        self.app.renderer.draw_pause_panel(screen)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.pop_state()
            self.game_state.game.resume()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.app.window_to_base(event.pos)
            key = self.app.hit_test((mx, my))

            if key == "resume":
                self.app.pop_state()
                self.game_state.game.resume()
            elif key == "reset":
                self.app.set_state(self.game_state)
            elif key == "main_menu":
                self.app.set_state(MainMenuState(self.app))
