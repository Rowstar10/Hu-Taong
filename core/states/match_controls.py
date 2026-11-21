"""Clicks on the controls that set a match's rules, shared by Match Setup and the Match settings
screen (and the pause menu's, when it opens that screen): the game modes, Chaos's and Switch's
timings, and the court."""


def in_match(app):
    """The match under these screens (Pause > Settings), if there is one."""
    from core.states.game_state import GameState
    return app.state_manager.get_state(GameState)


def match_rules(app):
    """The rules these screens change (1.9, Rowan).  Opened mid-match (from Pause), the match's own:
    for that match only, from its next serve.  Otherwise Match settings, which every new match
    starts from (and which a match's changes never touch)."""
    game = getattr(in_match(app), "game", None)
    return getattr(game, "rules", None) or app.settings.match


class MatchControls:
    def handle_match_key(self, key):
        """Act on a click on one of the match controls.  Answers True if it was one."""
        m = match_rules(self.app)
        if not key:
            return False

        if key.startswith("toggle_mode_"):
            name = "mode_" + key[len("toggle_mode_"):]
            if name[5:] in m.MODES:
                setattr(m, name, not getattr(m, name))
                return True

        # Chaos and Switch: one button each, cycling Off, then each version in turn, then Off
        for mode, versions in (("chaos", m.CHAOS_TIMINGS), ("switch", m.SWITCH_TIMINGS)):
            if key == f"cycle_mode_{mode}":
                level = (getattr(m, "mode_" + mode) and getattr(m, mode + "_timing") + 1) or 0
                level = (level + 1) % (len(versions) + 1)
                setattr(m, "mode_" + mode, level > 0)
                if level:
                    setattr(m, mode + "_timing", level - 1)
                return True

        count = len(m.court_options)
        if key == "cycle_court_left":
            m.court = (m.court - 1) % count
            return True
        if key == "cycle_court_right":
            m.court = (m.court + 1) % count
            return True
        return False
