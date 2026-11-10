NAME_TO_RGB = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 60, 60),
    "blue": (80, 140, 255),
    "dark blue": (50, 125, 205),
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
OFF_TEXT = (196, 182, 166)      # a switch that's off: plainly readable, just not lit
GRAY_HOVER = (180, 190, 210)

# --- Misc ---
DARK_BLUE = (50, 125, 205)
BLUE = (80, 155, 235)
BLUE_HOVER = (100, 175, 255)
LIGHT_BLUE = (170, 195, 235)
LIGHT_BLUE_HOVER = (190, 215, 255)
ROYAL_BLUE = (65, 105, 225)
ROYAL_BLUE_HOVER = (85, 125, 245)

ORANGE = (235, 145, 40)
ORANGE_HOVER = (255, 165, 60)

# --- Hu Tao ---
INK = (16, 7, 9)
LACQUER_TOP = (58, 17, 19)
LACQUER_MID = (36, 11, 13)
LACQUER_BOTTOM = (21, 7, 9)

CRIMSON = (178, 28, 36)
CRIMSON_BRIGHT = (226, 52, 44)
EMBER = (255, 122, 44)
FLAME = (255, 186, 96)

GOLD_DARK = (128, 88, 42)
GOLD = (214, 170, 92)
GOLD_BRIGHT = (250, 220, 150)

PAPER = (238, 218, 170)
PAPER_DARK = (204, 172, 116)
CINNABAR = (176, 28, 26)
PARCHMENT = (240, 226, 200)

GHOST = (232, 240, 255)
SPIRIT_BLUE = (92, 168, 255)

# Lacquer finish for each accent: (face top, face bottom, lip, text)
LACQUER = {"crimson": ((182, 38, 40), (112, 16, 22), (58, 8, 12), GOLD_BRIGHT),
           "jade":    ((46, 128, 98), (18, 72, 56), (8, 38, 30), GOLD_BRIGHT),
           "amber":   ((192, 118, 40), (124, 64, 16), (66, 32, 8), PARCHMENT),
           "azure":   ((48, 98, 170), (20, 50, 106), (10, 24, 58), GOLD_BRIGHT),
           "ink":     ((66, 38, 34), (30, 15, 15), (12, 6, 6), GOLD),
           "paper":   ((242, 224, 180), (206, 176, 122), (120, 88, 50), CINNABAR)}

# --- Color Roles ---
BACKGROUND = BLACK_BLUE
TEXT = WHITE
TEXT_DARK = BLACK
POSITIVE = GREEN
NEGATIVE = RED
NEUTRAL = GRAY

def finish(accent):
    """The lacquer finish for one of the accent colours above."""
    return {GREEN: "jade", BLUE: "azure", ORANGE: "amber", WHITE: "paper",
            GRAY: "ink", DARK_GRAY: "ink"}.get(accent, "crimson")

def color(name_or_rgb):
    if isinstance(name_or_rgb, tuple):
        return name_or_rgb
    if not isinstance(name_or_rgb, str):
        return (255, 255, 255)
    return NAME_TO_RGB.get(name_or_rgb.strip().lower(), (255, 255, 255))
