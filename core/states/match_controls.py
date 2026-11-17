"""Clicks on the controls that set a match's rules, shared by Match Setup and the Match settings
screen (and the pause menu's, when it opens that screen): the game modes, Chaos's and Switch's
timings, and the court."""


class MatchControls:
    def handle_match_key(self, key):
        """Act on a click on one of the match controls.  Answers True if it was one."""
        m = self.app.settings.match
        if not key:
            return False

        if key.startswith("toggle_mode_"):
            name = "mode_" + key[len("toggle_mode_"):]
            if name[5:] in m.MODES:
                setattr(m, name, not getattr(m, name))
                return True

        # A timing's arrows step through it, and turn its mode on (that's what picking one means)
        for mode, timings in (("chaos", m.CHAOS_TIMINGS), ("switch", m.SWITCH_TIMINGS)):
            for suffix, step in (("_left", -1), ("_right", 1)):
                if key == f"cycle_{mode}_timing{suffix}":
                    setattr(m, mode + "_timing", (getattr(m, mode + "_timing") + step) % len(timings))
                    setattr(m, "mode_" + mode, True)
                    return True

        count = len(m.court_options)
        if key == "cycle_court_left":
            m.court = (m.court - 1) % count
            return True
        if key == "cycle_court_right":
            m.court = (m.court + 1) % count
            return True
        return False
