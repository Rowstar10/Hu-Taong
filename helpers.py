import pygame, math

from config import MIXER_STEPS

# ------------------ Math helpers ------------------

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def reflect_in_range(y, lo, hi):
    i = 0
    while y < lo or y > hi:
        if y < lo:
            y = lo + (lo - y)
        else:
            y = hi - (y - hi)
        i += 1
    return y, i

def lerp(a, b, t):
    return a + (b - a) * t

def split_volume(gain):
    """A 0-1 gain as (sound volume, channel balance level) for the mixer.

    SDL_mixer keeps a volume as a whole number from 0 to MIXER_STEPS and truncates anything
    between, so master x music on their own could only ever land on 128 levels: quiet settings
    snapped to the quietest one, or to silence.  The sound's volume (MIXER_STEPS levels) and the
    channel's balance (255 levels) multiply, so together they reach any gain to within about 1%,
    down to roughly -90 dB.  Only a gain of exactly 0 is silent.
    """
    if gain <= 0:
        return 0.0, 0
    gain = min(1.0, gain)
    chunk = max(1, math.ceil(gain * MIXER_STEPS - 1e-9))       # the smallest sound volume that reaches it
    pan = max(1, min(255, round(gain * MIXER_STEPS / chunk * 255)))
    return chunk / MIXER_STEPS, pan

_FIT_CACHE = {}

def fit_text(text, max_width, start_size, bold=False):
    if isinstance(text, list):
        key = ("".join(d["word"] for d in text if isinstance(d, dict) and "word" in d),
               max_width, start_size, bold)
    else:
        key = (str(text), max_width, start_size, bold)
    if key not in _FIT_CACHE:
        _FIT_CACHE[key] = _fit_text(text, max_width, start_size, bold)
    return _FIT_CACHE[key]

def _fit_text(text, max_width, start_size, bold=False):
    size = start_size
    
    if isinstance(text, list):
        text_list = text
        text = ""
        for data in text_list:
            if isinstance(data, dict) and "word" in data:
                text += data["word"]

    while size > 10:
        font = pygame.font.SysFont("Helvetica", size, bold=bold)
        if font.size(str(text))[0] <= max_width:
            return font
        size -= 2

    return pygame.font.SysFont("Helvetica", 10, bold=bold)

def draw_multicolor_text(screen, font, text_parts, center):
    if not isinstance(text_parts, list):
        return
    
    text = ""
    for data in text_parts:
        if isinstance(data, dict) and "word" in data:
            text += data["word"]
        
    width = font.size(text)[0]
    height = font.size(text)[1]
    x = center[0] - width // 2
    y = center[1] - height // 2

    for data in text_parts:
        if isinstance(data, dict) and "word" in data and "color" in data:
            word = data["word"]
            color = data["color"]
            word_surf = font.render(word, True, color)
            screen.blit(word_surf, (x, y))
            x += word_surf.get_width()


