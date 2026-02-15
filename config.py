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

MENU_WIDTH = 500
MENU_HEIGHT = 600

APP_WIDTH = 1500
APP_HEIGHT = 800

PAUSE_WIDTH = 500
PAUSE_HEIGHT = 200

EPSILON = 0.001
HALF_PI = math.pi / 2
MAX_BOUNCE_ANGLE = math.radians(60)
MAX_CPF = 5

# Body types
DYNAMIC = 0
KINEMATIC = 1
STATIC = 2
