import json, os
from pathlib import Path

from core.platform import ANDROID, data_dir
from game.powerups import KINDS as POWERUP_KINDS

# Which attributes are written to disk.  Anything not listed here (resolution,
# window mode...) is deliberately left at its default on every launch.
#
# The file keeps 1.6's sections, whichever settings group (core/settings.py) a value belongs to
# now: "gameplay" holds the Match rules, "interface" the keys, the countdown and the effects as
# well.  Every version shares the one save, so 1.6 still reads what 1.7 writes, and the other way.
MODES = ["mode_chaos", "chaos_timing", "mode_switch", "switch_timing", "mode_curveball",
         "mode_lantern_night", "mode_twin_ball", "mode_talisman_rush", "mode_portal_pair"]
GAMEPLAY = ["paddle_width", "paddle_height", "paddle_speed", "ball_diameter", "ball_speed",
            "winning_score_index", "win_by_two", "ai_difficulty", "adaptive_ai",
            "vs_ai", "play_as_blue", "middle_wall", "ai_style", "pace",
            "powerups", "powerup_rate", "court", "online_host_blue"] + MODES + ["pu_" + kind.key for kind in POWERUP_KINDS]
DISPLAY = ["max_fps", "show_fps", "dim", "rotate_backgrounds", "background", "rotate_every", "parallax", "court_dim_level"]
OLD_COURT_DIM = [0, 60, 100, 150]     # before the Court Dim slider: Off, Light, Medium, Strong (out of 255)
AUDIO = ["play_mode", "even_volume", "fade", "menu_sounds", "ambience"]
INTERFACE = ["tooltips", "ai_banter", "screen_shake", "ball_trail", "auto_pause", "hide_cursor",
             "hud", "effects", "countdown", "instant_replay",
             "p1_up", "p1_down", "p1_left", "p1_right", "p2_up", "p2_down", "p2_left", "p2_right"]
if ANDROID:
    INTERFACE += ["touch_steer", "touch_sensitivity", "vibration"]
INDEX_FIELDS = {"winning_score_index", "ai_difficulty", "max_fps", "background",
                "ai_style", "chaos_timing", "switch_timing", "hud", "effects", "countdown", "fade", "ambience",
                "instant_replay",
                "rotate_every", "parallax", "powerup_rate", "play_mode", "court",
                "p1_up", "p1_down", "p1_left", "p1_right", "p2_up", "p2_down", "p2_left", "p2_right",
                "touch_steer", "touch_sensitivity"}  # whole numbers only
SOUND = ["master_volume", "sfx_volume", "music_volume", "paddle_hit_sound", "score_sound",
         "master_muted", "sfx_muted", "music_muted"]
ONLINE = ["own_server", "server_address", "server_user", "server_password"]


def save_path():
    return data_dir() / "save.json"


def _limits(app):
    m, g, d, i, a = (app.settings.match, app.settings.gameplay, app.settings.display,
                     app.settings.interface, app.settings.audio)
    limits = {name: (getattr(m, name + "_min"), getattr(m, name + "_max"))
              for name in ("paddle_width", "paddle_height", "paddle_speed", "ball_diameter", "ball_speed", "pace")}
    limits.update(winning_score_index = (0, len(m.winning_scores) - 1),
                  ai_difficulty = (0, len(m.ai_difficulties) - 1),
                  ai_style = (0, len(m.ai_styles) - 1),
                  chaos_timing = (0, len(m.CHAOS_TIMINGS) - 1), switch_timing = (0, len(m.SWITCH_TIMINGS) - 1),
                  powerup_rate = (0, len(m.powerup_rate_options) - 1),
                  court = (0, len(m.court_options) - 1),
                  hud = (0, len(i.hud_options) - 1),
                  instant_replay = (0, len(i.instant_replay_options) - 1),
                  effects = (0, len(d.effects_options) - 1),
                  countdown = (0, len(m.countdown_options) - 1),
                  touch_steer = (0, len(g.touch_steer_options) - 1),
                  touch_sensitivity = (0, len(g.touch_sensitivity_options) - 1),
                  fade = (0, len(a.fade_options) - 1),
                  play_mode = (0, 2),
                  ambience = (0, len(a.ambience_options) - 1),
                  max_fps = (0, len(d.max_fps_options) - 1),
                  rotate_every = (0, len(d.rotate_options) - 1),
                  parallax = (0, len(d.parallax_options) - 1),
                  background = (0, len(d.backgrounds) - 1),
                  dim = (0, 1), court_dim_level = (0, 1),
                  master_volume = (0, 1), sfx_volume = (0, 1), music_volume = (0, 1))
    return limits


def _old_modes(m):
    """The modes as 1.6 saved them, written alongside so 1.6 still reads a 1.7 save."""
    return {"chaos_mode": m.chaos_timing + 1 if m.mode_chaos else 0,
            "chaos_switch": m.switch_timing + 1 if m.mode_switch else 0,
            "curveball": m.mode_curveball, "lantern_night": m.mode_lantern_night}


def _section(s, keys):
    return {key: getattr(s.group_of(key), key) for key in keys}


def collect(app):
    s = app.settings
    return {"version": 1,
            "gameplay": dict(_section(s, GAMEPLAY), **_old_modes(s.match)),
            "display": _section(s, DISPLAY),
            "audio": _section(s, AUDIO),
            "interface": _section(s, INTERFACE),
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


def _restore_section(s, saved, limits):
    """A section of the file, each value onto whichever group it belongs to now."""
    if not isinstance(saved, dict):
        return
    for name, value in saved.items():
        owner = s.group_of(name)
        if owner is not None:
            _restore(owner, {name: value}, limits)


def _whole(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _migrate_modes(m, saved):
    """A save from before game modes (1.6 and earlier): its Chaos Mode, Chaos Switch, Curveball and
    Lantern Night settings become the modes.  (Chaos Mode + drifted speeds as well as sizes;
    Constant drift is sizes only now.)"""
    if not isinstance(saved, dict) or "mode_chaos" in saved:
        return
    chaos, switch = saved.get("chaos_mode"), saved.get("chaos_switch")
    if _whole(chaos) and 1 <= chaos <= 2:
        m.mode_chaos, m.chaos_timing = True, chaos - 1
    if _whole(switch) and 1 <= switch <= 3:
        m.mode_switch, m.switch_timing = True, min(switch - 1, 1)     # 1.6's Chaos Switch & +: Mid-rally
    m.mode_curveball = saved.get("curveball") is True
    m.mode_lantern_night = saved.get("lantern_night") is True


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
    _restore_section(s, data.get("gameplay"), limits)
    old = data.get("gameplay") or {}
    if isinstance(old, dict) and "pu_shape" not in old and isinstance(old.get("pu_chaos"), bool):
        s.match.pu_shape = old["pu_chaos"]          # Shape Shift was the Chaos Mode + talisman
    _migrate_modes(s.match, old)
    _restore_section(s, data.get("display"), limits)
    shown = data.get("display") or {}
    if isinstance(shown, dict) and "court_dim_level" not in shown:
        old = shown.get("court_dim")     # a save from before the slider: Off / Light / Medium / Strong
        if isinstance(old, int) and not isinstance(old, bool) and 0 <= old < len(OLD_COURT_DIM):
            s.display.court_dim_level = OLD_COURT_DIM[old] / 255
    _restore_section(s, data.get("audio"), limits)
    old = data.get("audio") or {}
    if isinstance(old, dict) and "play_mode" not in old and old.get("loop_music") is True:
        s.audio.play_mode = 2        # an older save's Loop
    _restore_section(s, data.get("interface"), limits)
    if not s.gameplay.keys_valid():
        s.gameplay.reset_keys()    # a missing or doubled-up key would leave a paddle uncontrollable
    _restore(app.sound_manager, data.get("sound"), limits)
    _restore(s.online, data.get("online"), limits)
    app.stats.load_dict(data.get("stats"))
