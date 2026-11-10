import json, os
from pathlib import Path

from game.powerups import KINDS as POWERUP_KINDS

# Which attributes are written to disk.  Anything not listed here (resolution,
# window mode...) is deliberately left at its default on every launch.
GAMEPLAY = ["paddle_width", "paddle_height", "paddle_speed", "ball_diameter", "ball_speed",
            "winning_score_index", "win_by_two", "ai_difficulty", "adaptive_ai", "chaos_mode",
            "vs_ai", "play_as_blue", "middle_wall", "ai_style", "chaos_switch", "pace",
            "powerups", "powerup_rate", "court", "online_host_blue", "curveball", "lantern_night"] + ["pu_" + kind.key for kind in POWERUP_KINDS]
DISPLAY = ["max_fps", "show_fps", "dim", "rotate_backgrounds", "background", "rotate_every", "parallax", "court_dim"]
AUDIO = ["play_mode", "even_volume", "fade", "menu_sounds", "ambience"]
INTERFACE = ["tooltips", "ai_banter", "screen_shake", "ball_trail", "auto_pause", "hide_cursor",
             "hud", "effects", "countdown", "instant_replay",
             "p1_up", "p1_down", "p1_left", "p1_right", "p2_up", "p2_down", "p2_left", "p2_right"]
INDEX_FIELDS = {"winning_score_index", "ai_difficulty", "max_fps", "background",
                "ai_style", "chaos_mode", "chaos_switch", "hud", "effects", "countdown", "fade", "ambience",
                "instant_replay",
                "rotate_every", "parallax", "powerup_rate", "play_mode", "court", "court_dim",
                "p1_up", "p1_down", "p1_left", "p1_right", "p2_up", "p2_down", "p2_left", "p2_right"}  # whole numbers only
SOUND = ["master_volume", "sfx_volume", "music_volume", "paddle_hit_sound", "score_sound"]
ONLINE = ["own_server", "server_address", "server_user", "server_password"]


def save_path():
    base = os.environ.get("APPDATA") or (Path.home() / ".local" / "share")
    return Path(base) / "HuTaong" / "save.json"


def _limits(app):
    g, d, i, a = app.settings.gameplay, app.settings.display, app.settings.interface, app.settings.audio
    limits = {name: (getattr(g, name + "_min"), getattr(g, name + "_max"))
              for name in ("paddle_width", "paddle_height", "paddle_speed", "ball_diameter", "ball_speed", "pace")}
    limits.update(winning_score_index = (0, len(g.winning_scores) - 1),
                  ai_difficulty = (0, len(g.ai_difficulties) - 1),
                  ai_style = (0, len(g.ai_styles) - 1),
                  chaos_mode = (0, 2), chaos_switch = (0, 3),
                  powerup_rate = (0, len(g.powerup_rate_options) - 1),
                  court = (0, len(g.court_options) - 1),
                  hud = (0, len(i.hud_options) - 1),
                  instant_replay = (0, len(i.instant_replay_options) - 1),
                  effects = (0, len(i.effects_options) - 1),
                  countdown = (0, len(i.countdown_options) - 1),
                  fade = (0, len(a.fade_options) - 1),
                  play_mode = (0, 2),
                  ambience = (0, len(a.ambience_options) - 1),
                  max_fps = (0, len(d.max_fps_options) - 1),
                  rotate_every = (0, len(d.rotate_options) - 1),
                  parallax = (0, len(d.parallax_options) - 1),
                  court_dim = (0, len(d.court_dim_options) - 1),
                  background = (0, len(d.backgrounds) - 1),
                  dim = (0, 1),
                  master_volume = (0, 1), sfx_volume = (0, 1), music_volume = (0, 1))
    return limits


def collect(app):
    s = app.settings
    return {"version": 1,
            "gameplay": {key: s.gameplay.stored(key) for key in GAMEPLAY},
            "display": {key: getattr(s.display, key) for key in DISPLAY},
            "audio": {key: getattr(s.audio, key) for key in AUDIO},
            "interface": {key: getattr(s.interface, key) for key in INTERFACE},
            "sound": {key: getattr(app.sound_manager, key) for key in SOUND},
            "online": {key: getattr(s.online, key) for key in ONLINE},
            "stats": app.stats.to_dict()}


def _restore(obj, saved, limits):
    """Copy values onto `obj`, ignoring anything unknown, mistyped or out of range."""
    if not isinstance(saved, dict):
        return
    for name, value in saved.items():
        if not hasattr(obj, name):
            continue
        current = getattr(obj, name)
        if isinstance(current, bool):
            if isinstance(value, bool):
                setattr(obj, name, value)
        elif isinstance(current, str):
            if isinstance(value, str):
                setattr(obj, name, "".join(c for c in value if c.isprintable())[:120])
        elif isinstance(current, (int, float)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            lo, hi = limits.get(name, (value, value))
            value = max(lo, min(hi, value))
            setattr(obj, name, int(round(value)) if name in INDEX_FIELDS else value)


def save(app):
    path = save_path()
    try:
        path.parent.mkdir(parents = True, exist_ok = True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(collect(app), indent = 2))
        tmp.replace(path)          # never leave a half-written save behind
    except OSError as e:
        print(f"[save_data] could not save: {e}")


def load(app):
    try:
        data = json.loads(save_path().read_text())
    except (OSError, ValueError):
        return                     # first launch, or a damaged file: keep defaults

    if not isinstance(data, dict):
        return

    limits = _limits(app)
    s = app.settings
    _restore(s.gameplay, data.get("gameplay"), limits)
    if s.gameplay.middle_wall and s.gameplay.switch_mid_rally:
        s.gameplay.chaos_switch -= 2     # Chaos Switch + only works with the Middle Wall off
    _restore(s.display, data.get("display"), limits)
    _restore(s.audio, data.get("audio"), limits)
    old = data.get("audio") or {}
    if isinstance(old, dict) and "play_mode" not in old and old.get("loop_music") is True:
        s.audio.play_mode = 2        # an older save's Loop
    _restore(s.interface, data.get("interface"), limits)
    if not s.interface.keys_valid():
        s.interface.reset_keys()   # a missing or doubled-up key would leave a paddle uncontrollable
    _restore(app.sound_manager, data.get("sound"), limits)
    _restore(s.online, data.get("online"), limits)
    app.stats.load_dict(data.get("stats"))
