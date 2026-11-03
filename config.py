import sys, math
from pathlib import Path

# -------- Paths --------
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

RESOURCE_DIR = BASE_DIR / "Resources"
SOUND_DIR = RESOURCE_DIR / "Sounds"
MUSIC_DIR = SOUND_DIR / "Music"
IMAGE_DIR = RESOURCE_DIR / "Images"
FONT_DIR = RESOURCE_DIR / "Fonts"

# -------- Constants --------
BASE_W, BASE_H = 1920, 1080

RESOLUTIONS = [(854, 480),
               (1024, 576),
               (1280, 720),
               (1600, 900),
               (1920, 1080),
               (2560, 1440),
               (3840, 2160),
               (7680, 4320)]

DEFAULT_DISPLAY_MODE = 1

# Backgrounds are scaled past the screen edges by this much, for parallax
BG_OVERSCAN = (30, 17)

EPSILON = 0.001
HALF_PI = math.pi / 2
MAX_BOUNCE_ANGLE = math.radians(60)
MAX_CPF = 5
MIXER_STEPS = 128  # SDL_mixer volumes are integers 0..128

# -------- Body types --------
DYNAMIC = 0
KINEMATIC = 1
STATIC = 2
