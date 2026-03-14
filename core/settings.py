class Settings:
    def __init__(self):
        self.gameplay = GameplaySettings()
        self.display = DisplaySettings()
        self.audio = AudioSettings()

class GameplaySettings:
    def __init__(self):
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
        self.winning_scores = [1, 3, 5, 10, 15, 20]
        self.winning_score_index = 2
        self.win_by_two = True

        # AI
        self.ai_enabled = False
        self.ai_difficulties = ["Baby", "Easy", "Normal", "Hard", "Insane"]
        self.ai_difficulty = 2

class DisplaySettings:
    def __init__(self):
        self.max_fps_options = [30, 60, 120, 144, 165, 240, "Unlimited"]
        self.max_fps = 1
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

        self.menu_background = 0
        self.game_background = 1

class AudioSettings:
    def __init__(self):
        self.menu_track = ["Lofi Hiphop Tao.mp3",
                           "Lofi Vibe.mp3",
                           "Relaxed Tao.mp3",
                           "Retro Relax.mp3",
                           "Living Beware.mp3"]

        self.game_track = ["Living Beware.mp3",
                           "Hillichurl REMIX.mp3",
                           "Epic Conquest.mp3",
                           "Lofi Hiphop Tao.mp3",
                           "Lofi Vibe.mp3",
                           "Relaxed Tao.mp3",
                           "Relaxed Tao.mp3"]

        self.win_track = ["Triumphant Win.mp3",
                          "Retro Relax.mp3"]

        self.menu_music = 0
        self.game_music = 0
        self.win_music = 0
