import sys, math
from pathlib import Path

# -------- Paths --------
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

RESOURCE_DIR = BASE_DIR / "Resources"
SOUND_DIR = RESOURCE_DIR / "Sounds"
IMAGE_DIR = RESOURCE_DIR / "Images"

# -------- Constants --------
FPS = 100

BASE_W, BASE_H = 1280, 720

RESOLUTIONS = [(960, 540),
               (1024, 576),
               (1280, 720),
               (1600, 900),
               (1920, 1080),
               (2560, 1440)]

EPSILON = 0.001
HALF_PI = math.pi / 2
MAX_BOUNCE_ANGLE = math.radians(60)
MAX_CPF = 5

# Body types
DYNAMIC = 0
KINEMATIC = 1
STATIC = 2
