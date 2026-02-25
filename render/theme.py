NAME_TO_RGB = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 60, 60),
    "blue": (80, 140, 255),
    "orange red": (255, 120, 60),
    "royal blue": (65, 105, 225),
    "grey5": (13, 13, 13),
    "gray": (160, 160, 160),
    "grey": (160, 160, 160),
    "green": (60, 220, 120),
    "orange": (255, 170, 60),
}

# --- Background ---
BLACK_BLUE = (15, 15, 15)

# --- Text ---
WHITE = (235, 235, 235)
WHITE_HOVER = (255, 255, 255)
BLACK = (0, 0, 0)
BLACK_HOVER = (20, 20, 20)

# --- Positive ---
GREEN = (70, 205, 130)
GREEN_HOVER = (90, 225, 150)

# --- Negative ---
RED = (235, 75, 75)
RED_HOVER = (255, 95, 95)
ORANGE_RED = (235, 100, 40)
ORANGE_RED_HOVER = (255, 120, 60)

# --- Neutral ---
DARK_GRAY = (90, 90, 90)
GRAY = (150, 150, 160)
GRAY_HOVER = (180, 190, 210)

# --- Misc ---
BLUE = (80, 155, 235)
BLUE_HOVER = (100, 175, 255)
LIGHT_BLUE = (190, 215, 255)
ROYAL_BLUE = (65, 105, 225)
ROYAL_BLUE_HOVER = (85, 125, 245)

ORANGE = (235, 145, 40)
ORANGE_HOVER = (255, 165, 60)

# --- Color Roles ---
BACKGROUND = BLACK_BLUE
TEXT = WHITE
TEXT_DARK = BLACK
POSITIVE = GREEN
NEGATIVE = RED
NEUTRAL = GRAY

def color(name_or_rgb):
    if isinstance(name_or_rgb, tuple):
        return name_or_rgb
    if not isinstance(name_or_rgb, str):
        return (255, 255, 255)
    return NAME_TO_RGB.get(name_or_rgb.strip().lower(), (255, 255, 255))
