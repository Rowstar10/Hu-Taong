import random

class Settings:
    def __init__(self, app):
        self.app = app
        self.gameplay = GameplaySettings(app)
        self.display = DisplaySettings(app)
        self.audio = AudioSettings(app)

class GameplaySettings:
    def __init__(self, app):
        self.app = app
        
        # Paddle
        self.paddle_width_min = 20
        self.paddle_width_max = 60
        self.paddle_width_range = self.paddle_width_max - self.paddle_width_min
        self.paddle_width = (self.paddle_width_min + self.paddle_width_max) // 2
        
        self.paddle_height_min = 100
        self.paddle_height_max = 300
        self.paddle_height_range = self.paddle_height_max - self.paddle_height_min
        self.paddle_height = (self.paddle_height_min + self.paddle_height_max) // 2
        
        self.paddle_speed_min = 1000
        self.paddle_speed_max = 2000
        self.paddle_speed_range = self.paddle_speed_max - self.paddle_speed_min
        self.paddle_speed = (self.paddle_speed_min + self.paddle_speed_max) // 2
        
        # Ball
        self.ball_diameter_min = 20
        self.ball_diameter_max = 100
        self.ball_diameter_range = self.ball_diameter_max - self.ball_diameter_min
        self.ball_diameter = (self.ball_diameter_min + self.ball_diameter_max) // 2
        
        self.ball_speed_min = 200
        self.ball_speed_max = 800
        self.ball_speed_range = self.ball_speed_max - self.ball_speed_min
        self.ball_speed = (self.ball_speed_min + self.ball_speed_max) // 2

        # Match rules
        self.winning_scores = [3, 5, 11, 15, 21, "Endless Mode"]
        self.winning_score_index = 2
        self.win_by_two = True

        # AI
        self.ai_difficulties = ["Baby", "Easy", "Normal", "Hard", "Insane"]
        self.ai_difficulty = 2

class DisplaySettings:
    def __init__(self, app):
        self.app = app
        
        self.max_fps_options = [30, 60, 120, 144, 165, 240, "Unlimited"]
        self.max_fps = 2
        self.show_fps = True
        
        self.dim = 0
        self.resolution = (1920, 1080)

        self.backgrounds = ["bg1.png",
                            "bg2.png",
                            "bg3.png",
                            "bg4.png",
                            "bg5.png",
                            "bg6.png",
                            "bg7.png",
                            "bg8.png",
                            "bg9.png",
                            "bg10.png",
                            "bg11.png",
                            "bg12.png"]

        self.background = self.backgrounds.index(random.choice(self.backgrounds))
        self.rotate_backgrounds = True

class AudioSettings:
    def __init__(self, app):
        self.app = app
        
        self.menu_track = ["Lofi Hiphop Tao.mp3",
                           "Lofi Vibe.mp3",
                           "Relaxed Tao 1.mp3",
                           "Relaxed Tao 2.mp3",
                           "Relaxed Tao 3.mp3",
                           "Retro Relax.mp3",
                           "Living Beware.mp3"]

        self.game_track = ["Living Beware.mp3",
                           "Hillichurl REMIX.mp3",
                           "Epic Conquest.mp3",
                           "Lofi Hiphop Tao.mp3",
                           "Lofi Vibe.mp3",
                           "Relaxed Tao 1.mp3",
                           "Relaxed Tao 2.mp3",
                           "Relaxed Tao 3.mp3",
                           "Arcade Retro.mp3",
                           "Operation Awesome.mp3"]

        self.win_track = ["Triumphant Win.mp3",
                          "Retro Relax.mp3",
                          "Epic Win.mp3",
                          "Sweet Melancholy.mp3"]

        self.lose_track = ["Sweet Melancholy.mp3",
                           "Grand Defeat.mp3",
                           "Retro Relax.mp3"]

        self.menu_music = self.menu_track.index(random.choice(self.menu_track))
        self.game_music = self.game_track.index(random.choice(self.game_track))
        self.win_music = self.win_track.index(random.choice(self.win_track))
        self.lose_music = self.lose_track.index(random.choice(self.lose_track))
        
        self.loop_music = False
