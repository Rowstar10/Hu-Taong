import pygame

from config import BASE_W, BASE_H
from render import theme
from render.theme import color

class Renderer:
    def __init__(self, app):
        self.app = app
        self.title_font = pygame.font.SysFont("Helvetica", 100, bold = True)
        self.subtitle_font = pygame.font.SysFont("Helvetica", 40, bold = True)
        self.button_font = pygame.font.SysFont("Helvetica", 20, bold = True)
        self.countdown_font = pygame.font.SysFont("Helvetica", 80, bold = True)

    def draw_main_menu(self, state, screen):
        width, height = BASE_W, BASE_H
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())

        title_font = self.app.fonts.get("helvetica", int(height * 0.18), bold=True)
        subtitle_font = self.app.fonts.get("helvetica", int(height * 0.06), bold=True)
        font = self.app.fonts.get("helvetica", int(height * 0.04), bold=True)
        small_font = self.app.fonts.get("helvetica", int(height * 0.02), bold=True)

        btn_w = 360
        gap_x = int(width * 0.03)
        gap_y = int(height * 0.03)
        
        # --------- Title ---------        
        title_surf = title_font.render("Hu Taong!", True, theme.RED)

        title_x = width // 2
        title_y = int(height * 0.125)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)
        
        # --------- Play Button ---------
        play_surf = subtitle_font.render("Play Game", True, theme.BLACK)

        play_w = play_surf.get_width() + gap_x
        play_h = play_surf.get_height() + gap_y
        play_x = (width - play_w) // 2
        play_y = int(height * 0.45)
        
        play_rect = pygame.Rect(play_x, play_y, play_w, play_h)
        play_color = theme.GREEN_HOVER if play_rect.collidepoint(mouse_pos) else theme.GREEN
        pygame.draw.rect(screen, play_color, play_rect, border_radius=12)
        screen.blit(play_surf, play_surf.get_rect(center=play_rect.center))

        current_y = play_rect.bottom + 2 * gap_y
        
        # --------- Settings Button ---------
        settings_surf = subtitle_font.render("Settings", True, theme.BLACK)

        settings_w = settings_surf.get_width() + gap_x
        settings_h = settings_surf.get_height() + gap_y
        settings_x = (width - settings_w) // 2
        settings_y = current_y
        
        settings_rect = pygame.Rect(settings_x, settings_y, settings_w, settings_h)
        settings_color = theme.ORANGE_HOVER if settings_rect.collidepoint(mouse_pos) else theme.ORANGE
        pygame.draw.rect(screen, settings_color, settings_rect, border_radius=12)
        screen.blit(settings_surf, settings_surf.get_rect(center=settings_rect.center))

        current_y = settings_rect.bottom + 2 * gap_y

        # --------- Quit Button ---------
        quit_surf = subtitle_font.render("Quit Game", True, theme.BLACK)

        quit_w = quit_surf.get_width() + gap_x
        quit_h = quit_surf.get_height() + gap_y
        quit_x = (width - quit_w) // 2
        quit_y = current_y
        
        quit_rect = pygame.Rect(quit_x, quit_y, quit_w, quit_h)
        quit_color = theme.RED_HOVER if quit_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, quit_color, quit_rect, border_radius=12)
        screen.blit(quit_surf, quit_surf.get_rect(center=quit_rect.center))

        # -------- Assign Button Hitboxes ---------
        state.ui_hitboxes["play"] = play_rect
        state.ui_hitboxes["settings"] = settings_rect
        state.ui_hitboxes["prompt_quit"] = quit_rect
        
    def draw_settings_menu(self, state, screen):
        width, height = BASE_W, BASE_H       
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        
        title_font = self.app.fonts.get("helvetica", int(height * 0.18), bold=True)
        subtitle_font = self.app.fonts.get("helvetica", int(height * 0.06), bold=True)
        font = self.app.fonts.get("helvetica", int(height * 0.04), bold=True)
        small_font = self.app.fonts.get("helvetica", int(height * 0.02), bold=True)

        btn_w = 200
        gap_x = int(width * 0.02)
        gap_y = int(height * 0.02)

        # --------- Title ---------
        title_surf = title_font.render("Settings", True, theme.ORANGE)

        title_x = width // 2
        title_y = int(height * 0.1)
        
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)

        # -------- Gameplay Settings Button --------
        gameplay_settings_surf = subtitle_font.render("Gameplay", True, theme.BLACK)
        gameplay_settings_w = gameplay_settings_surf.get_width() + gap_x
        gameplay_settings_h = gameplay_settings_surf.get_height() + gap_y
        gameplay_settings_x = (width - gameplay_settings_w) // 2
        gameplay_settings_y = int(height * 0.55)

        gameplay_settings_rect = pygame.Rect(gameplay_settings_x, gameplay_settings_y, gameplay_settings_w, gameplay_settings_h)
        gameplay_settings_color = theme.GREEN_HOVER if gameplay_settings_rect.collidepoint(mouse_pos) else theme.GREEN
        pygame.draw.rect(screen, gameplay_settings_color, gameplay_settings_rect, border_radius=12)
        screen.blit(gameplay_settings_surf, gameplay_settings_surf.get_rect(center=gameplay_settings_rect.center))

        # -------- Display Settings Button --------
        display_settings_surf = subtitle_font.render("Display", True, theme.BLACK)
        display_settings_w = display_settings_surf.get_width() + gap_x
        display_settings_h = display_settings_surf.get_height() + gap_y
        display_settings_x = (width - gameplay_settings_w) // 2 - display_settings_w - gap_x
        display_settings_y = int(height * 0.55)

        display_settings_rect = pygame.Rect(display_settings_x, display_settings_y, display_settings_w, display_settings_h)
        display_settings_color = theme.ORANGE_HOVER if display_settings_rect.collidepoint(mouse_pos) else theme.ORANGE
        pygame.draw.rect(screen, display_settings_color, display_settings_rect, border_radius=12)
        screen.blit(display_settings_surf, display_settings_surf.get_rect(center=display_settings_rect.center))

        current_y = display_settings_rect.bottom + 2 * gap_y

        # -------- Audio Settings Button --------
        audio_settings_surf = subtitle_font.render("Audio ", True, theme.BLACK)
        audio_settings_w = audio_settings_surf.get_width() + gap_x
        audio_settings_h = audio_settings_surf.get_height() + gap_y
        audio_settings_x = (width + gameplay_settings_w) // 2 + gap_x
        audio_settings_y = int(height * 0.55)
        
        audio_settings_rect = pygame.Rect(audio_settings_x, audio_settings_y, audio_settings_w, audio_settings_h)
        audio_settings_color = theme.BLUE_HOVER if audio_settings_rect.collidepoint(mouse_pos) else theme.BLUE
        pygame.draw.rect(screen, audio_settings_color, audio_settings_rect, border_radius=12)
        screen.blit(audio_settings_surf, audio_settings_surf.get_rect(center=audio_settings_rect.center))

        current_y = audio_settings_rect.bottom + 2 * gap_y
        
        # -------- Back Button --------
        back_surf = font.render("Back", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (width - back_w) // 2
        back_y = height - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        # -------- Hitboxes --------
        state.ui_hitboxes["gameplay"] = gameplay_settings_rect
        state.ui_hitboxes["display"] = display_settings_rect
        state.ui_hitboxes["audio"] = audio_settings_rect
        state.ui_hitboxes["back"] = back_rect
        
    def draw_gameplay_settings_menu(self, state, screen):
        width, height = BASE_W, BASE_H
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        settings = self.app.settings.gameplay
        
        title_font = self.app.fonts.get("helvetica", int(height * 0.18), bold=True)
        subtitle_font = self.app.fonts.get("helvetica", int(height * 0.06), bold=True)
        font = self.app.fonts.get("helvetica", int(height * 0.04), bold=True)
        small_font = self.app.fonts.get("helvetica", int(height * 0.03), bold=True)
        tiny_font = self.app.fonts.get("helvetica", int(height * 0.02), bold=True)

        gap_x = int(width * 0.02)
        gap_y = int(height * 0.02)
        
        # --------- Title ---------        
        title_surf = title_font.render("Gameplay", True, theme.GREEN)

        title_x = width // 2
        title_y = int(height * 0.1)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)
        current_y = title_rect.bottom + 6 * gap_y

        # ------ AI Difficulty ------
        ai_surf = subtitle_font.render("AI Difficulty", True, theme.GREEN)
        x = width // 2 - 180
        y = current_y
        ai_rect = ai_surf.get_rect(midright=(x, y))
        screen.blit(ai_surf, ai_rect)

        # ------ Score to win ------
        win_surf = subtitle_font.render("Winning Score", True, theme.GREEN)
        x = width // 2 + 180
        y = current_y
        win_rect = win_surf.get_rect(midleft=(x, y))
        screen.blit(win_surf, win_rect)

        current_y = win_rect.bottom + 2 * gap_y

        # ------- Difficulty Cycle -------
        ai_diff = settings.ai_difficulties[settings.ai_difficulty]
        ai_color = theme.GREEN if settings.ai_difficulty == 0 else (theme.WHITE if settings.ai_difficulty in [1, 2, 3] else theme.RED)
        ai_diff_surf = font.render(ai_diff, True, ai_color)
        x = ai_rect.centerx
        y = current_y
        ai_diff_rect = ai_diff_surf.get_rect(center=(x, y))
        screen.blit(ai_diff_surf, ai_diff_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y
        
        left_ai_rect = pygame.Rect(ai_diff_rect.left - btn_w - gap_x,
                                current_y - btn_h // 2,
                                btn_w, btn_h)
        
        left_color = theme.GRAY_HOVER if left_ai_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, left_color, left_ai_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=left_ai_rect.center))

        right_ai_rect = pygame.Rect(ai_diff_rect.right + gap_x,
                                 current_y - btn_h // 2,
                                 btn_w, btn_h)
        
        right_color = theme.GRAY_HOVER if right_ai_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, right_color, right_ai_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=right_ai_rect.center))

        # ------- Score to win cycle -------
        win_score = settings.winning_scores[settings.winning_score_index]
        
        if win_score == "Endless Mode":
            win_score_color = theme.ORANGE
        else:
            win_score = f"Score {win_score} to win"
            win_score_color = theme.WHITE            
            
        win_score_surf = font.render(win_score, True, win_score_color)
        x = win_rect.centerx
        y = current_y
        win_score_rect = win_score_surf.get_rect(center=(x, y))
        screen.blit(win_score_surf, win_score_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y
        
        left_win_rect = pygame.Rect(win_score_rect.left - btn_w - gap_x,
                                current_y - btn_h // 2,
                                btn_w, btn_h)
        
        left_color = theme.GRAY_HOVER if left_win_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, left_color, left_win_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=left_win_rect.center))

        right_win_rect = pygame.Rect(win_score_rect.right + gap_x,
                                 current_y - btn_h // 2,
                                 btn_w, btn_h)
        
        right_color = theme.GRAY_HOVER if right_win_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, right_color, right_win_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=right_win_rect.center))

        current_y = right_win_rect.bottom + gap_y

        # -------- Win by Two Toggle --------
        win_by_two_text = "Win by Two: ON" if settings.win_by_two else "Win by Two: OFF"
        win_by_two_surf = small_font.render(win_by_two_text, True, theme.BLACK)

        win_by_two_w = win_by_two_surf.get_width() + gap_x
        win_by_two_h = win_by_two_surf.get_height() + gap_y
        win_by_two_x = win_rect.centerx - win_by_two_w // 2
        win_by_two_y = current_y

        win_by_two_rect = pygame.Rect(win_by_two_x, win_by_two_y, win_by_two_w, win_by_two_h)
        
        if settings.win_by_two:
            win_by_two_color = theme.GREEN_HOVER if win_by_two_rect.collidepoint(mouse_pos) else theme.GREEN
        else:
            win_by_two_color = theme.RED_HOVER if win_by_two_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, win_by_two_color, win_by_two_rect, border_radius=12)
        screen.blit(win_by_two_surf, win_by_two_surf.get_rect(center=win_by_two_rect.center))

        current_y = win_by_two_rect.bottom + 6 * gap_y

        # -------- Ball Speed --------
        ball_speed_surf = subtitle_font.render("Ball Speed", True, theme.GREEN)
        x = ai_rect.centerx
        y = current_y
        ball_speed_rect = ball_speed_surf.get_rect(center=(x, y))
        screen.blit(ball_speed_surf, ball_speed_rect)

        # -------- Paddle Speed --------
        paddle_speed_surf = subtitle_font.render("Paddle Speed", True, theme.GREEN)
        x = win_rect.centerx
        y = current_y
        paddle_speed_rect = paddle_speed_surf.get_rect(center=(x, y))
        screen.blit(paddle_speed_surf, paddle_speed_rect)

        current_y = paddle_speed_rect.bottom + 2 * gap_y

        # -------- Ball Speed Slider --------
        slider_w = int(width * 0.25)
        slider_h = int(height * 0.02)
        slider_x = ai_rect.centerx - slider_w // 2
        slider_y = current_y

        ball_speed_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, ball_speed_slider_rect, border_radius=6)

        ratio = (settings.ball_speed - 200) / 600
        fill_w = int(slider_w * ratio)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.GREEN, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        ball_speed_surf = font.render(f"{int(settings.ball_speed)}", True, theme.WHITE)
        x = ball_speed_slider_rect.right + gap_x
        y = ball_speed_slider_rect.centery
        ball_speed_rect = ball_speed_surf.get_rect(midleft=(x, y))
        screen.blit(ball_speed_surf, ball_speed_rect)

        # -------- Paddle Speed Slider --------
        slider_w = int(width * 0.25)
        slider_h = int(height * 0.02)
        slider_x = win_rect.centerx - slider_w // 2
        slider_y = current_y

        paddle_speed_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, paddle_speed_slider_rect, border_radius=6)

        ratio = (settings.paddle_speed - 1000) / 1000
        fill_w = int(slider_w * ratio)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.GREEN, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        paddle_speed_surf = font.render(f"{int(settings.paddle_speed)}", True, theme.WHITE)
        x = paddle_speed_slider_rect.right + gap_x
        y = paddle_speed_slider_rect.centery
        paddle_speed_rect = paddle_speed_surf.get_rect(midleft=(x, y))
        screen.blit(paddle_speed_surf, paddle_speed_rect)

        current_y = paddle_speed_slider_rect.bottom + 4 * gap_y

        # -------- Ball Diameter --------
        ball_diameter_surf = subtitle_font.render("Ball Diameter", True, theme.GREEN)
        x = ai_rect.centerx
        y = current_y
        ball_diamater_rect = ball_diameter_surf.get_rect(center=(x, y))
        screen.blit(ball_diameter_surf, ball_diamater_rect)

        # -------- Paddle Size --------
        paddle_size_surf = subtitle_font.render("Paddle Size", True, theme.GREEN)
        x = win_rect.centerx
        y = current_y
        paddle_size_rect = paddle_size_surf.get_rect(center=(x, y))
        screen.blit(paddle_size_surf, paddle_size_rect)

        current_y = paddle_size_rect.bottom + 2 * gap_y

        # -------- Ball Diameter Slider --------
        slider_w = int(width * 0.25)
        slider_h = int(height * 0.02)
        slider_x = ai_rect.centerx - slider_w // 2
        slider_y = current_y

        ball_diameter_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, ball_diameter_slider_rect, border_radius=6)

        ratio = (settings.ball_diameter - 20) / 80
        fill_w = int(slider_w * ratio)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.GREEN, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        ball_diameter_surf = font.render(f"{int(settings.ball_diameter)}", True, theme.WHITE)
        x = ball_diameter_slider_rect.right + gap_x
        y = ball_diameter_slider_rect.centery
        ball_diameter_rect = ball_diameter_surf.get_rect(midleft=(x, y))
        screen.blit(ball_diameter_surf, ball_diameter_rect)

        # -------- Paddle Size Slider --------
        slider_w = int(width * 0.25)
        slider_h = int(height * 0.02)
        slider_x = win_rect.centerx - slider_w // 2
        slider_y = current_y

        paddle_size_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, paddle_size_slider_rect, border_radius=6)

        ratio = (settings.paddle_height - 100) / 200
        fill_w = int(slider_w * ratio)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.GREEN, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        paddle_size_surf = font.render(f"{int(settings.paddle_height)} x {int(settings.paddle_width)}", True, theme.WHITE)
        x = paddle_size_slider_rect.right + gap_x
        y = paddle_size_slider_rect.centery
        paddle_size_rect = paddle_size_surf.get_rect(midleft=(x, y))
        screen.blit(paddle_size_surf, paddle_size_rect)

        current_y = paddle_size_rect.bottom + 2 * gap_y

        # -------- Randomise --------
        randomise_text = "Randomise All"
        randomise_surf = small_font.render(randomise_text, True, theme.BLACK)

        randomise_w = randomise_surf.get_width() + gap_x
        randomise_h = randomise_surf.get_height() + gap_y
        randomise_x = ai_rect.centerx - randomise_w // 2
        randomise_y = current_y

        randomise_rect = pygame.Rect(randomise_x, randomise_y, randomise_w, randomise_h)
        
        randomise_color = theme.GREEN_HOVER if randomise_rect.collidepoint(mouse_pos) else theme.GREEN
            
        pygame.draw.rect(screen, randomise_color, randomise_rect, border_radius=12)
        screen.blit(randomise_surf, randomise_surf.get_rect(center=randomise_rect.center))

        # -------- Reset to defaults --------
        default_text = "Reset All"
        default_surf = small_font.render(default_text, True, theme.BLACK)

        default_w = default_surf.get_width() + gap_x
        default_h = default_surf.get_height() + gap_y
        default_x = win_rect.centerx - default_w // 2
        default_y = current_y

        default_rect = pygame.Rect(default_x, default_y, default_w, default_h)
        
        default_color = theme.GREEN_HOVER if default_rect.collidepoint(mouse_pos) else theme.GREEN
            
        pygame.draw.rect(screen, default_color, default_rect, border_radius=12)
        screen.blit(default_surf, default_surf.get_rect(center=default_rect.center))

        # -------- Reset Buttons --------
        reset_surf = tiny_font.render("Reset", True, theme.BLACK)
        reset_w = reset_surf.get_width() + gap_x
        reset_h = reset_surf.get_height() + gap_y
        
        reset_x1 = ball_speed_slider_rect.left - reset_w - gap_x // 2
        reset_y1 = ball_speed_slider_rect.centery - reset_h // 2
        reset_x2 = paddle_speed_slider_rect.left - reset_w - gap_x // 2
        reset_y2 = ball_diameter_slider_rect.centery - reset_h // 2

        reset_ball_speed_rect = pygame.Rect(reset_x1, reset_y1, reset_w, reset_h)
        reset_paddle_speed_rect = pygame.Rect(reset_x2, reset_y1, reset_w, reset_h)
        reset_ball_diameter_rect = pygame.Rect(reset_x1, reset_y2, reset_w, reset_h)
        reset_paddle_size_rect = pygame.Rect(reset_x2, reset_y2, reset_w, reset_h)

        reset_ball_speed_color = theme.WHITE_HOVER if reset_ball_speed_rect.collidepoint(mouse_pos) else theme.WHITE
        reset_paddle_speed_color = theme.WHITE_HOVER if reset_paddle_speed_rect.collidepoint(mouse_pos) else theme.WHITE
        reset_ball_diameter_color = theme.WHITE_HOVER if reset_ball_diameter_rect.collidepoint(mouse_pos) else theme.WHITE
        reset_paddle_size_color = theme.WHITE_HOVER if reset_paddle_size_rect.collidepoint(mouse_pos) else theme.WHITE
        
        pygame.draw.rect(screen, reset_ball_speed_color, reset_ball_speed_rect, border_radius=12)
        pygame.draw.rect(screen, reset_paddle_speed_color, reset_paddle_speed_rect, border_radius=12)
        pygame.draw.rect(screen, reset_ball_diameter_color, reset_ball_diameter_rect, border_radius=12)
        pygame.draw.rect(screen, reset_paddle_size_color, reset_paddle_size_rect, border_radius=12)
        
        screen.blit(reset_surf, reset_surf.get_rect(center=reset_ball_speed_rect.center))
        screen.blit(reset_surf, reset_surf.get_rect(center=reset_paddle_speed_rect.center))
        screen.blit(reset_surf, reset_surf.get_rect(center=reset_ball_diameter_rect.center))
        screen.blit(reset_surf, reset_surf.get_rect(center=reset_paddle_size_rect.center))
        
        # -------- Back to Settings Menu Button --------
        back_surf = font.render("Back", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (width - back_w) // 2
        back_y = height - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        
        # -------- Hitboxes --------
        state.ui_hitboxes["cycle_ai_left"] = left_ai_rect
        state.ui_hitboxes["cycle_ai_right"] = right_ai_rect
        
        state.ui_hitboxes["cycle_win_score_left"] = left_win_rect
        state.ui_hitboxes["cycle_win_score_right"] = right_win_rect
        state.ui_hitboxes["toggle_win_by_two"] = win_by_two_rect
        
        state.ui_hitboxes["ball_speed_slider"] = ball_speed_slider_rect
        state.ui_hitboxes["paddle_speed_slider"] = paddle_speed_slider_rect
        state.ui_hitboxes["ball_diameter_slider"] = ball_diameter_slider_rect
        state.ui_hitboxes["paddle_size_slider"] = paddle_size_slider_rect

        state.ui_hitboxes["randomise_all"] = randomise_rect
        state.ui_hitboxes["reset_all"] = default_rect
        
        state.ui_hitboxes["reset_ball_speed"] = reset_ball_speed_rect
        state.ui_hitboxes["reset_paddle_speed"] = reset_paddle_speed_rect
        state.ui_hitboxes["reset_ball_diameter"] = reset_ball_diameter_rect
        state.ui_hitboxes["reset_paddle_size"] = reset_paddle_size_rect
        
        state.ui_hitboxes["back"] = back_rect
        
    def draw_display_settings_menu(self, state, screen):
        width, height = BASE_W, BASE_H
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        settings = self.app.settings.display
        
        title_font = self.app.fonts.get("helvetica", int(height * 0.18), bold=True)
        subtitle_font = self.app.fonts.get("helvetica", int(height * 0.06), bold=True)
        font = self.app.fonts.get("helvetica", int(height * 0.04), bold=True)
        small_font = self.app.fonts.get("helvetica", int(height * 0.03), bold=True)
        tiny_font = self.app.fonts.get("helvetica", int(height * 0.02), bold=True)

        gap_x = int(width * 0.02)
        gap_y = int(height * 0.02)
        
        # --------- Title ---------        
        title_surf = title_font.render("Display", True, theme.ORANGE)

        title_x = width // 2
        title_y = int(height * 0.1)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)

        current_y = title_rect.bottom + 3 * gap_y

        # ------ Resolution Settings ------
        res_settings_surf = subtitle_font.render("Resolution", True, theme.ORANGE)
        res_settings_rect = res_settings_surf.get_rect(center=(width // 2, current_y))
        screen.blit(res_settings_surf, res_settings_rect)

        current_y = res_settings_rect.bottom + 3 * gap_y

        # ------- Resolution Cycle -------
        res = self.app.resolutions[state.res_index]
        res_surf = font.render(f"{res[0]} x {res[1]}", True, theme.WHITE)
        res_rect = res_surf.get_rect(center=(width // 2, current_y))
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

        current_y = right_rect.bottom + 3 * gap_y

        # ------ Display Mode Cycle ------
        mode_text = self.app.display_modes[state.display_mode_index].capitalize()
        mode_surf = font.render(mode_text, True, theme.WHITE)
        mode_rect = mode_surf.get_rect(center=(width // 2, current_y))
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
        apply_surf = small_font.render("Apply", True, theme.BLACK)
        apply_w = apply_surf.get_width() + gap_x
        apply_h = apply_surf.get_height() + gap_y
        apply_x = (width - apply_w) // 2
        apply_y = current_y 

        apply_rect = pygame.Rect(apply_x, apply_y, apply_w, apply_h)
        apply_color = theme.ORANGE_HOVER if apply_rect.collidepoint(mouse_pos) else theme.ORANGE
        pygame.draw.rect(screen, apply_color, apply_rect, border_radius=12)
        screen.blit(apply_surf, apply_surf.get_rect(center=apply_rect.center))

        current_y = apply_rect.bottom + 4 * gap_y
        
        # ------ Backgrounds ------
        bg_surf = subtitle_font.render("Backgrounds", True, theme.ORANGE)
        bg_w = bg_surf.get_width() + gap_x
        bg_h = bg_surf.get_height() + gap_y
        bg_x = width // 2
        bg_y = current_y
        bg_rect = bg_surf.get_rect(center=(bg_x, bg_y))
        screen.blit(bg_surf, bg_rect)

        current_y = bg_rect.bottom + 2 * gap_y
        
        menu_bg_surf = font.render("Menu", True, theme.ORANGE)
        menu_bg_w = menu_bg_surf.get_width() + gap_x
        menu_bg_h = menu_bg_surf.get_height() + gap_y
        menu_bg_x = width // 2 - 178
        menu_bg_y = current_y
        menu_bg_rect = menu_bg_surf.get_rect(center=(menu_bg_x, menu_bg_y))
        screen.blit(menu_bg_surf, menu_bg_rect)

        game_bg_surf = font.render("Game", True, theme.ORANGE)
        game_bg_w = game_bg_surf.get_width() + gap_x
        game_bg_h = game_bg_surf.get_height() + gap_y
        game_bg_x = width // 2 + 178
        game_bg_y = current_y
        game_bg_rect = game_bg_surf.get_rect(center=(game_bg_x, game_bg_y))
        screen.blit(game_bg_surf, game_bg_rect)

        # -------- Rotate Backgrounds Toggle --------
        rotate_bg_text = "Rotate: ON" if self.app.settings.display.rotate_backgrounds else "Rotate: OFF"
        rotate_bg_surf = small_font.render(rotate_bg_text, True, theme.BLACK)

        rotate_bg_w = rotate_bg_surf.get_width() + gap_x
        rotate_bg_h = rotate_bg_surf.get_height() + gap_y
        rotate_bg_x = bg_rect.right + 30
        rotate_bg_y = bg_rect.centery - rotate_bg_h // 2

        rotate_bg_rect = pygame.Rect(rotate_bg_x, rotate_bg_y, rotate_bg_w, rotate_bg_h)
        
        if settings.rotate_backgrounds:
            rotate_bg_color = theme.ORANGE_HOVER if rotate_bg_rect.collidepoint(mouse_pos) else theme.ORANGE
        else:
            rotate_bg_color = theme.RED_HOVER if rotate_bg_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, rotate_bg_color, rotate_bg_rect, border_radius=12)
        screen.blit(rotate_bg_surf, rotate_bg_surf.get_rect(center=rotate_bg_rect.center))

        # ------ FPS Settings ------
        fps_settings_surf = subtitle_font.render("Maximum FPS", True, theme.ORANGE)
        x = width // 2 + fps_settings_surf.get_width() // 2 + 400
        y = res_settings_rect.centery + 100
        fps_settings_rect = fps_settings_surf.get_rect(center=(x, y))
        screen.blit(fps_settings_surf, fps_settings_rect)

        current_y = fps_settings_rect.bottom + 3 * gap_y
        
        # -------- Max FPS Cycle --------
        max_fps_text = settings.max_fps_options[settings.max_fps]
        max_fps_surf = font.render(f"{max_fps_text}", True, theme.WHITE)
        x = fps_settings_rect.centerx
        y = current_y
        max_fps_rect = max_fps_surf.get_rect(center=(x, y))
        screen.blit(max_fps_surf, max_fps_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y

        max_fps_left_rect = pygame.Rect(max_fps_rect.left - btn_w - gap_x,
                                        current_y - btn_h // 2,
                                        btn_w, btn_h)
        
        max_fps_right_rect = pygame.Rect(max_fps_rect.right + gap_x,
                                         current_y - btn_h // 2,
                                         btn_w, btn_h)
        
        max_fps_left_color = theme.GRAY_HOVER if max_fps_left_rect.collidepoint(mouse_pos) else theme.GRAY
        max_fps_right_color = theme.GRAY_HOVER if max_fps_right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, max_fps_left_color, max_fps_left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=max_fps_left_rect.center))
        pygame.draw.rect(screen, max_fps_right_color, max_fps_right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=max_fps_right_rect.center))

        current_y = max_fps_right_rect.bottom + gap_y

        # -------- Show FPS Toggle --------
        show_fps_text = "Show FPS: ON" if self.app.settings.display.show_fps else "Show FPS: OFF"
        show_fps_surf = tiny_font.render(show_fps_text, True, theme.BLACK)

        show_fps_w = show_fps_surf.get_width() + gap_x
        show_fps_h = show_fps_surf.get_height() + gap_y
        show_fps_x = max_fps_rect.centerx - show_fps_w // 2
        show_fps_y = max_fps_right_rect.bottom + gap_y

        show_fps_rect = pygame.Rect(show_fps_x, show_fps_y, show_fps_w, show_fps_h)
        
        if settings.show_fps:
            show_fps_color = theme.ORANGE_HOVER if show_fps_rect.collidepoint(mouse_pos) else theme.ORANGE
        else:
            show_fps_color = theme.RED_HOVER if show_fps_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, show_fps_color, show_fps_rect, border_radius=12)
        screen.blit(show_fps_surf, show_fps_surf.get_rect(center=show_fps_rect.center))

        # -------- Dim Overlay --------
        dim_overlay_surf = subtitle_font.render("Dim Overlay", True, theme.ORANGE)
        x = width // 2 - dim_overlay_surf.get_width() // 2 - 400
        y = res_settings_rect.centery + 100
        dim_overlay_rect = dim_overlay_surf.get_rect(center=(x, y))
        screen.blit(dim_overlay_surf, dim_overlay_rect)

        current_y = dim_overlay_rect.bottom + 3 * gap_y

        # -------- Dim Overlay Slider --------
        slider_w = int(width * 0.2)
        slider_h = int(height * 0.02)
        slider_x = dim_overlay_rect.centerx - slider_w // 2
        slider_y = current_y

        dim_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, dim_rect, border_radius=6)

        fill_w = int(slider_w * settings.dim)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.ORANGE, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        dim_value_surf = font.render(f"{int(100 * settings.dim)}%", True, theme.WHITE)
        x = dim_rect.right + 30
        y = dim_rect.centery
        dim_value_rect = dim_value_surf.get_rect(midleft=(x, y))
        screen.blit(dim_value_surf, dim_value_rect)

        # -------- Back Button --------
        back_surf = font.render("Back", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (width - back_w) // 2
        back_y = height - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        
        # -------- Hitboxes --------
        state.ui_hitboxes["cycle_res_left"] = left_rect
        state.ui_hitboxes["cycle_res_right"] = right_rect
        state.ui_hitboxes["cycle_mode_left"] = mode_left_rect
        state.ui_hitboxes["cycle_mode_right"] = mode_right_rect
        state.ui_hitboxes["apply"] = apply_rect

        state.ui_hitboxes["toggle_rotate_bg"] = rotate_bg_rect
        state.ui_hitboxes["cycle_max_fps_left"] = max_fps_left_rect
        state.ui_hitboxes["cycle_max_fps_right"] = max_fps_right_rect
        state.ui_hitboxes["toggle_show_fps"] = show_fps_rect
        
        state.ui_hitboxes["dim_slider"] = dim_rect
        
        state.ui_hitboxes["back"] = back_rect
        
    def draw_audio_settings_menu(self, state, screen):
        width, height = BASE_W, BASE_H
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())
        sound = self.app.sound
        s = self.app.settings.audio
        
        title_font = self.app.fonts.get("helvetica", int(height * 0.18), bold=True)
        subtitle_font = self.app.fonts.get("helvetica", int(height * 0.06), bold=True)
        font = self.app.fonts.get("helvetica", int(height * 0.04), bold=True)
        small_font = self.app.fonts.get("helvetica", int(height * 0.03), bold=True)
        tiny_font = self.app.fonts.get("helvetica", int(height * 0.02), bold=True)

        gap_x = int(width * 0.02)
        gap_y = int(height * 0.02)
        
        # --------- Title ---------        
        title_surf = title_font.render("Audio", True, theme.BLUE)

        title_x = width // 2
        title_y = int(height * 0.1)
                      
        title_rect = title_surf.get_rect(center=(title_x, title_y))
        screen.blit(title_surf, title_rect)

        current_y = title_rect.bottom + 4 * gap_y

        # -------- Master Volume --------
        master_surf = subtitle_font.render("Master Volume", True, theme.BLUE)
        x = width // 2 - 400
        y = current_y
        master_rect = master_surf.get_rect(center=(x, y))
        screen.blit(master_surf, master_rect)

        current_y = master_rect.bottom + 2 * gap_y

        # -------- Master Volume Slider --------
        slider_w = int(width * 0.3)
        slider_h = int(height * 0.02)
        slider_x = master_rect.centerx - slider_w // 2
        slider_y = current_y

        master_volume_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, master_volume_slider_rect, border_radius=6)

        fill_w = int(slider_w * sound.master_volume)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.BLUE, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        master_volume_surf = subtitle_font.render(f"{int(100 * sound.master_volume)}%", True, theme.WHITE)
        x = master_volume_slider_rect.right + 30
        y = master_volume_slider_rect.centery
        master_volume_rect = master_volume_surf.get_rect(midleft=(x, y))
        screen.blit(master_volume_surf, master_volume_rect)

        current_y = master_volume_rect.bottom + 3 * gap_y

        # -------- Music Volume --------
        music_surf = subtitle_font.render("Music Volume", True, theme.BLUE)
        x = master_rect.centerx
        y = current_y
        music_rect = music_surf.get_rect(center=(x, y))
        screen.blit(music_surf, music_rect)

        current_y = music_rect.bottom + 2 * gap_y

        # -------- Music Volume Slider --------
        slider_w = int(width * 0.3)
        slider_h = int(height * 0.02)
        slider_x = master_rect.centerx - slider_w // 2
        slider_y = current_y

        music_volume_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, music_volume_slider_rect, border_radius=6)

        fill_w = int(slider_w * sound.music_volume)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.BLUE, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        music_volume_surf = subtitle_font.render(f"{int(100 * sound.music_volume)}%", True, theme.WHITE)
        x = music_volume_slider_rect.right + 30
        y = music_volume_slider_rect.centery
        music_volume_rect = music_volume_surf.get_rect(midleft=(x, y))
        screen.blit(music_volume_surf, music_volume_rect)

        current_y = music_volume_rect.bottom + 3 * gap_y

        # -------- SFX Volume --------
        sfx_surf = subtitle_font.render("SFX Volume", True, theme.BLUE)
        x = master_rect.centerx
        y = current_y
        sfx_rect = sfx_surf.get_rect(center=(x, y))
        screen.blit(sfx_surf, sfx_rect)

        current_y = sfx_rect.bottom + 2 * gap_y

        # -------- SFX Volume Slider --------
        slider_w = int(width * 0.3)
        slider_h = int(height * 0.02)
        slider_x = master_rect.centerx - slider_w // 2
        slider_y = current_y

        sfx_volume_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(screen, theme.DARK_GRAY, sfx_volume_slider_rect, border_radius=6)

        fill_w = int(slider_w * sound.sfx_volume)
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(screen, theme.BLUE, fill_rect, border_radius=6)

        knob_radius = slider_h * 1.2
        knob_x = slider_x + fill_w
        knob_y = slider_y + slider_h // 2
        
        dx = mouse_pos[0] - knob_x
        dy = mouse_pos[1] - knob_y
        is_hovering = dx ** 2 + dy ** 2 <= knob_radius ** 2
        knob_color = theme.WHITE_HOVER if is_hovering else theme.WHITE
        pygame.draw.circle(screen, knob_color, (knob_x, knob_y), knob_radius)

        sfx_volume_surf = subtitle_font.render(f"{int(100 * sound.sfx_volume)}%", True, theme.WHITE)
        x = sfx_volume_slider_rect.right + 30
        y = sfx_volume_slider_rect.centery
        sfx_volume_rect = sfx_volume_surf.get_rect(midleft=(x, y))
        screen.blit(sfx_volume_surf, sfx_volume_rect)

        current_y = sfx_volume_rect.bottom + 3 * gap_y

        # -------- Reset Volume --------
        reset_volume_surf = small_font.render("Reset", True, theme.BLACK)
        reset_volume_w = reset_volume_surf.get_width() + gap_x
        reset_volume_h = reset_volume_surf.get_height() + gap_y
        
        reset_master_volume_x = master_volume_slider_rect.left - reset_volume_w - gap_x // 2
        reset_master_volume_y = master_volume_slider_rect.centery - reset_volume_h // 2
        
        reset_music_volume_x = music_volume_slider_rect.left - reset_volume_w - gap_x // 2
        reset_music_volume_y = music_volume_slider_rect.centery - reset_volume_h // 2
        
        reset_sfx_volume_x = sfx_volume_slider_rect.left - reset_volume_w - gap_x // 2
        reset_sfx_volume_y = sfx_volume_slider_rect.centery - reset_volume_h // 2

        reset_master_volume_rect = pygame.Rect(reset_master_volume_x, reset_master_volume_y, reset_volume_w, reset_volume_h)
        reset_music_volume_rect = pygame.Rect(reset_music_volume_x, reset_music_volume_y, reset_volume_w, reset_volume_h)
        reset_sfx_volume_rect = pygame.Rect(reset_sfx_volume_x, reset_sfx_volume_y, reset_volume_w, reset_volume_h)
        
        reset_master_color = theme.WHITE_HOVER if reset_master_volume_rect.collidepoint(mouse_pos) else theme.WHITE
        reset_music_color = theme.WHITE_HOVER if reset_music_volume_rect.collidepoint(mouse_pos) else theme.WHITE
        reset_sfx_color = theme.WHITE_HOVER if reset_sfx_volume_rect.collidepoint(mouse_pos) else theme.WHITE
        
        pygame.draw.rect(screen, reset_master_color, reset_master_volume_rect, border_radius=12)
        pygame.draw.rect(screen, reset_music_color, reset_music_volume_rect, border_radius=12)
        pygame.draw.rect(screen, reset_sfx_color, reset_sfx_volume_rect, border_radius=12)
        
        screen.blit(reset_volume_surf, reset_volume_surf.get_rect(center=reset_master_volume_rect.center))
        screen.blit(reset_volume_surf, reset_volume_surf.get_rect(center=reset_music_volume_rect.center))
        screen.blit(reset_volume_surf, reset_volume_surf.get_rect(center=reset_sfx_volume_rect.center))

        # -------- Paddle Sound Toggle --------
        paddle_text = "Paddle Sounds: ON" if sound.paddle_hit_sound else "Paddle Sounds: OFF"
        paddle_surf = small_font.render(paddle_text, True, theme.BLACK)

        paddle_w = paddle_surf.get_width() + gap_x
        paddle_h = paddle_surf.get_height() + gap_y
        paddle_x = master_rect.centerx - paddle_w - gap_x // 2
        paddle_y = current_y

        paddle_rect = pygame.Rect(paddle_x, paddle_y, paddle_w, paddle_h)
        
        if sound.paddle_hit_sound:
            paddle_color = theme.BLUE_HOVER if paddle_rect.collidepoint(mouse_pos) else theme.BLUE
        else:
            paddle_color = theme.RED_HOVER if paddle_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, paddle_color, paddle_rect, border_radius=12)
        screen.blit(paddle_surf, paddle_surf.get_rect(center=paddle_rect.center))
        
        # -------- Score Sound Toggles --------
        score_text = "Score Sound: ON" if sound.score_sound else "Score Sound: OFF"
        score_surf = small_font.render(score_text, True, theme.BLACK)

        score_w = score_surf.get_width() + gap_x
        score_h = score_surf.get_height() + gap_y
        score_x = master_rect.centerx + gap_x // 2
        score_y = current_y

        score_rect = pygame.Rect(score_x, score_y, score_w, score_h)
        
        if sound.score_sound:
            score_color = theme.BLUE_HOVER if score_rect.collidepoint(mouse_pos) else theme.BLUE
        else:
            score_color = theme.RED_HOVER if score_rect.collidepoint(mouse_pos) else theme.RED
            
        pygame.draw.rect(screen, score_color, score_rect, border_radius=12)
        screen.blit(score_surf, score_surf.get_rect(center=score_rect.center))

        current_y = paddle_rect.bottom + 4 * gap_y

        # ------ Menu BG Music ------
        menu_bg_music_surf = subtitle_font.render("Menu Music", True, theme.BLUE)
        x = width // 2 + 500
        y = master_rect.centery
        menu_bg_music_rect = menu_bg_music_surf.get_rect(center=(x, y))
        screen.blit(menu_bg_music_surf, menu_bg_music_rect)

        current_y = menu_bg_music_rect.bottom + 2 * gap_y
        
        # -------- Menu BG Music Cycle --------
        menu_music_text = s.menu_track[s.menu_music].rstrip(".mp3")
        menu_music_surf = font.render(f"{menu_music_text}", True, theme.WHITE)
        x = menu_bg_music_rect.centerx
        y = current_y
        menu_music_rect = menu_music_surf.get_rect(center=(x, y))
        screen.blit(menu_music_surf, menu_music_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y

        menu_music_left_rect = pygame.Rect(menu_music_rect.left - btn_w - gap_x,
                                        current_y - btn_h // 2,
                                        btn_w, btn_h)
        
        menu_music_right_rect = pygame.Rect(menu_music_rect.right + gap_x,
                                         current_y - btn_h // 2,
                                         btn_w, btn_h)
        
        menu_music_left_color = theme.GRAY_HOVER if menu_music_left_rect.collidepoint(mouse_pos) else theme.GRAY
        menu_music_right_color = theme.GRAY_HOVER if menu_music_right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, menu_music_left_color, menu_music_left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=menu_music_left_rect.center))
        pygame.draw.rect(screen, menu_music_right_color, menu_music_right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=menu_music_right_rect.center))

        current_y = menu_music_rect.bottom + 3 * gap_y

        # ------ Game BG Music ------
        game_bg_music_surf = subtitle_font.render("Game Music", True, theme.BLUE)
        x = menu_bg_music_rect.centerx
        y = current_y
        game_bg_music_rect = game_bg_music_surf.get_rect(center=(x, y))
        screen.blit(game_bg_music_surf, game_bg_music_rect)

        current_y = game_bg_music_rect.bottom + 2 * gap_y
        
        # -------- Game BG Music Cycle --------
        game_music_text = s.game_track[s.game_music].rstrip(".mp3")
        game_music_surf = font.render(f"{game_music_text}", True, theme.WHITE)
        x = menu_bg_music_rect.centerx
        y = current_y
        game_music_rect = game_music_surf.get_rect(center=(x, y))
        screen.blit(game_music_surf, game_music_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y

        game_music_left_rect = pygame.Rect(game_music_rect.left - btn_w - gap_x,
                                        current_y - btn_h // 2,
                                        btn_w, btn_h)
        
        game_music_right_rect = pygame.Rect(game_music_rect.right + gap_x,
                                         current_y - btn_h // 2,
                                         btn_w, btn_h)
        
        game_music_left_color = theme.GRAY_HOVER if game_music_left_rect.collidepoint(mouse_pos) else theme.GRAY
        game_music_right_color = theme.GRAY_HOVER if game_music_right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, game_music_left_color, game_music_left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=game_music_left_rect.center))
        pygame.draw.rect(screen, game_music_right_color, game_music_right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=game_music_right_rect.center))

        current_y = game_music_rect.bottom + 3 * gap_y

        # ------ Win BG Music ------
        win_bg_music_surf = subtitle_font.render("Win Music", True, theme.BLUE)
        x = menu_bg_music_rect.centerx
        y = current_y
        win_bg_music_rect = win_bg_music_surf.get_rect(center=(x, y))
        screen.blit(win_bg_music_surf, win_bg_music_rect)

        current_y = win_bg_music_rect.bottom + 2 * gap_y
        
        # -------- Win BG Music Cycle --------
        win_music_text = s.win_track[s.win_music].rstrip(".mp3")
        win_music_surf = font.render(f"{win_music_text}", True, theme.WHITE)
        x = menu_bg_music_rect.centerx
        y = current_y
        win_music_rect = win_music_surf.get_rect(center=(x, y))
        screen.blit(win_music_surf, win_music_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y

        win_music_left_rect = pygame.Rect(win_music_rect.left - btn_w - gap_x,
                                        current_y - btn_h // 2,
                                        btn_w, btn_h)
        
        win_music_right_rect = pygame.Rect(win_music_rect.right + gap_x,
                                         current_y - btn_h // 2,
                                         btn_w, btn_h)
        
        win_music_left_color = theme.GRAY_HOVER if win_music_left_rect.collidepoint(mouse_pos) else theme.GRAY
        win_music_right_color = theme.GRAY_HOVER if win_music_right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, win_music_left_color, win_music_left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=win_music_left_rect.center))
        pygame.draw.rect(screen, win_music_right_color, win_music_right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=win_music_right_rect.center))

        current_y = win_music_rect.bottom + 3 * gap_y

        # ------ Lose BG Music ------
        lose_bg_music_surf = subtitle_font.render("Lose Music", True, theme.BLUE)
        x = menu_bg_music_rect.centerx
        y = current_y
        lose_bg_music_rect = lose_bg_music_surf.get_rect(center=(x, y))
        screen.blit(lose_bg_music_surf, lose_bg_music_rect)

        current_y = lose_bg_music_rect.bottom + 2 * gap_y
        
        # -------- Lose BG Music Cycle --------
        lose_music_text = s.lose_track[s.lose_music].rstrip(".mp3")
        lose_music_surf = font.render(f"{lose_music_text}", True, theme.WHITE)
        x = menu_bg_music_rect.centerx
        y = current_y
        lose_music_rect = lose_music_surf.get_rect(center=(x, y))
        screen.blit(lose_music_surf, lose_music_rect)

        btn_w = font.size("<")[0] + gap_x
        btn_h = font.size("<")[1] + gap_y

        lose_music_left_rect = pygame.Rect(lose_music_rect.left - btn_w - gap_x,
                                        current_y - btn_h // 2,
                                        btn_w, btn_h)
        
        lose_music_right_rect = pygame.Rect(lose_music_rect.right + gap_x,
                                         current_y - btn_h // 2,
                                         btn_w, btn_h)
        
        lose_music_left_color = theme.GRAY_HOVER if lose_music_left_rect.collidepoint(mouse_pos) else theme.GRAY
        lose_music_right_color = theme.GRAY_HOVER if lose_music_right_rect.collidepoint(mouse_pos) else theme.GRAY
        pygame.draw.rect(screen, lose_music_left_color, lose_music_left_rect, border_radius=12)
        screen.blit(font.render("<", True, theme.BLACK),
                    font.render("<", True, theme.BLACK).get_rect(center=lose_music_left_rect.center))
        pygame.draw.rect(screen, lose_music_right_color, lose_music_right_rect, border_radius=12)
        screen.blit(font.render(">", True, theme.BLACK),
                    font.render(">", True, theme.BLACK).get_rect(center=lose_music_right_rect.center))

        current_y = lose_music_rect.bottom + 2 * gap_y

        # -------- Randomise Music --------
        randomise_music_text = "Randomise Music"
        randomise_music_surf = small_font.render(randomise_music_text, True, theme.BLACK)

        randomise_music_w = randomise_music_surf.get_width() + gap_x
        randomise_music_h = randomise_music_surf.get_height() + gap_y
        randomise_music_x = menu_bg_music_rect.centerx - randomise_music_w // 2 - 100
        randomise_music_y = current_y

        randomise_music_rect = pygame.Rect(randomise_music_x, randomise_music_y, randomise_music_w, randomise_music_h)
        
        randomise_music_color = theme.BLUE_HOVER if randomise_music_rect.collidepoint(mouse_pos) else theme.BLUE
            
        pygame.draw.rect(screen, randomise_music_color, randomise_music_rect, border_radius=12)
        screen.blit(randomise_music_surf, randomise_music_surf.get_rect(center=randomise_music_rect.center))

        # -------- Loop/Shuffle Music --------
        loop_music_text = "Loop" if s.loop_music else "Shuffle"
        loop_music_surf = small_font.render(loop_music_text, True, theme.BLACK)

        loop_music_w = loop_music_surf.get_width() + gap_x
        loop_music_h = loop_music_surf.get_height() + gap_y
        loop_music_x = menu_bg_music_rect.centerx - loop_music_w // 2 + 180
        loop_music_y = current_y

        loop_music_rect = pygame.Rect(loop_music_x, loop_music_y, loop_music_w, loop_music_h)
        
        loop_music_color = theme.BLUE_HOVER if loop_music_rect.collidepoint(mouse_pos) else theme.BLUE            
        pygame.draw.rect(screen, loop_music_color, loop_music_rect, border_radius=12)
        screen.blit(loop_music_surf, loop_music_surf.get_rect(center=loop_music_rect.center))
        
        # -------- Back Button --------
        back_surf = font.render("Back", True, theme.BLACK)
        back_w = back_surf.get_width() + gap_x
        back_h = back_surf.get_height() + gap_y
        back_x = (width - back_w) // 2
        back_y = height - back_h - gap_y

        back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        back_color = theme.RED_HOVER if back_rect.collidepoint(mouse_pos) else theme.RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=12)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        # -------- Hitboxes --------
        state.ui_hitboxes["master_volume_slider"] = master_volume_slider_rect
        state.ui_hitboxes["music_volume_slider"] = music_volume_slider_rect
        state.ui_hitboxes["sfx_volume_slider"] = sfx_volume_slider_rect
        
        state.ui_hitboxes["reset_master_volume"] = reset_master_volume_rect
        state.ui_hitboxes["reset_music_volume"] = reset_music_volume_rect
        state.ui_hitboxes["reset_sfx_volume"] = reset_sfx_volume_rect

        state.ui_hitboxes["cycle_menu_music_left"] = menu_music_left_rect
        state.ui_hitboxes["cycle_menu_music_right"] = menu_music_right_rect
        
        state.ui_hitboxes["cycle_game_music_left"] = game_music_left_rect
        state.ui_hitboxes["cycle_game_music_right"] = game_music_right_rect
                    
        state.ui_hitboxes["cycle_win_music_left"] = win_music_left_rect
        state.ui_hitboxes["cycle_win_music_right"] = win_music_right_rect

        state.ui_hitboxes["cycle_lose_music_left"] = lose_music_left_rect
        state.ui_hitboxes["cycle_lose_music_right"] = lose_music_right_rect

        state.ui_hitboxes["randomise_music"] = randomise_music_rect
        state.ui_hitboxes["toggle_loop_music"] = loop_music_rect
        state.ui_hitboxes["toggle_paddle_sounds"] = paddle_rect
        state.ui_hitboxes["toggle_score_sounds"] = score_rect
        
        state.ui_hitboxes["back"] = back_rect

    def draw_world(self, screen, game):
        # Separator
        width, height = BASE_W, BASE_H
        pygame.draw.line(screen, (160, 160, 160), (width // 2, 0), (width // 2, height), 2)

        # Draw objects (rectangles/circles)
        for obj in game.objects:
            if obj.is_ball:
                pygame.draw.ellipse(screen, color(getattr(obj, "color", "white")),
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)))
                pygame.draw.ellipse(screen, theme.BLACK,
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)), width = 2)
                
            elif obj.is_paddle:
                pygame.draw.rect(screen, color(getattr(obj, "color1", "white")),
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)))
                pygame.draw.rect(screen, theme.BLACK,
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)), width = 2)

            elif obj.is_wall:
                pygame.draw.rect(screen, theme.BLACK,
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)))
                pygame.draw.rect(screen, theme.BLACK,
                    pygame.Rect(int(obj.x0), int(obj.y0), int(obj.width), int(obj.height)), width = 2)
                
        # Score message
        if getattr(game, "message_text", ""):
            surf = self.title_font.render(game.message_text, True, getattr(game, "message_color", (255, 255, 255)))
            screen.blit(surf, (width // 2 - surf.get_width() // 2, height // 2 - surf.get_height() // 2))

        # Countdown overlay
        if game.countdown is not None:
            v = game.countdown.shown_value
            txt = "GO!" if v == 0 else str(v)
            col = (60, 220, 120) if v == 0 else (255, 60, 60)
            surf = self.countdown_font.render(txt, True, col)
            screen.blit(surf, (width // 2 - surf.get_width() // 2, height // 2 - surf.get_height() // 2))
        
    def draw_overlay(self, state, screen, *,
                     title=None, header=None, buttons=None,
                     title_size = 0.3, header_size = 0.3, btn_size = 0.14,
                     title_y = 0.2, header_y = 0.4, btn_y = 0.75,
                     title_color=theme.WHITE,
                     panel_rect=None,
                     dim=True):
        
        W, H = BASE_W, BASE_H
        mouse_pos = self.app.window_to_base(pygame.mouse.get_pos())       

        # ---------- Panel ----------
        if panel_rect is None:
            panel_w = int(W * 0.1)
            panel_h = int(H * 0.2)
            panel_rect = pygame.Rect(W // 2 - panel_w // 2,
                                     H // 2 - panel_h // 2,
                                     panel_w, panel_h)
        x, y, w, h = panel_rect

        # ---------- Dim background ----------
        if dim: 
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

        # ---------- Transparent Panel ----------
        panel_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 0))  # fully transparent surface

        pygame.draw.rect(panel_surface, # slightly transparent panel
                         (30, 30, 30, 230),
                         panel_surface.get_rect(),
                         border_radius=18)

        pygame.draw.rect(panel_surface,  # fully opaque border
                         (90, 90, 90, 255),
                         panel_surface.get_rect(),
                         width=2, border_radius=18)

        screen.blit(panel_surface, (x, y))

        from helpers import fit_text, draw_multicolor_text
        
        # ---------- Title ----------
        if title is not None:
            title_font = fit_text(title, int(w * 0.9), int(h * title_size), bold=True)
            title_surf = title_font.render(title, True, title_color)
            title_rect = title_surf.get_rect(center=(x + w // 2, y + int(h * title_y)))
            screen.blit(title_surf, title_rect)

        # ---------- Header ----------
        if header is not None:
            header_font = fit_text(header, int(w * 0.9), int(h * header_size), bold=True)
            if isinstance(header, list):
                draw_multicolor_text(screen, header_font, header, (x + w // 2, y + int(h * header_y)))
            else:
                header_surf = header_font.render(header, True, theme.WHITE)
                header_rect = header_surf.get_rect(center=(x + w // 2, y + int(h * header_y)))
                screen.blit(header_surf, header_rect)

        # ---------- Button row ----------
        if buttons is not None:
            button_font = self.app.fonts.get("helvetica", int(h * btn_size), bold=True)
            button_rect = (x, y + int(h * 0.25), w, int(h * btn_y))
            cols = getattr(state, "ui_cols", len(buttons))

            self.app.ui_layout.draw_button_grid(
                state,
                screen,
                button_rect,
                buttons,
                cols=cols,
                btn_font=button_font)
