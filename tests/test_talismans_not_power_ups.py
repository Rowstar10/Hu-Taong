"""Power-ups are talismans, 1.9 (Rowan, 2026-11-21).

"Basically, everywhere in the game where it says power up, change it to talisman": the Match
settings switch, the Choose Talismans page's title and its hint ("Point at a talisman to see what it
does"), the tips, the Tab hint in a match and the line of rules a friend sees online.  (The code's
own names, `powerups`, `pu_*` and the saved settings, stay as they are, so old saves still load.)
"""
import re
import unittest

from tests import harness

app = harness.app()

import core.net as netcode                                      # noqa: E402
import core.rooms as rooms                                      # noqa: E402
from core.net import HostSession                                # noqa: E402
from game.powerups import KINDS                                 # noqa: E402
from render.renderer import TIPS, Renderer                      # noqa: E402
from tests.test_settings_menus import open_screen               # noqa: E402

POWER_UP = re.compile(r"power[- ]?ups?\b", re.IGNORECASE)


def texts(screen):
    """Every piece of text a screen draws (through the renderer, or the layout's own text calls)."""
    seen = []
    ui = app.renderer.ui
    real_r, real_u = app.renderer.text, ui.text

    def spy_r(surface, text, *a, **k):
        seen.append(text)
        return real_r(surface, text, *a, **k)

    def spy_u(font, text, *a, **k):
        seen.append(text)
        return real_u(font, text, *a, **k)
    app.renderer.text, ui.text = spy_r, spy_u
    try:
        screen.draw(app.virtual)
    finally:
        del app.renderer.text
        del ui.text
    return [t for t in seen if isinstance(t, str)]


class NoPowerUps(unittest.TestCase):
    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_the_tips_and_descriptions(self):
        words = [*TIPS.values(), *Renderer.MODE_TIPS.values(), *(k.about for k in KINDS), *(k.blurb for k in KINDS)]
        self.assertEqual([w for w in words if POWER_UP.search(w)], [])

    def test_the_pages(self):
        for name in ("powerups", "match", "match_setup"):
            drawn = texts(open_screen(name))
            self.assertEqual([t for t in drawn if POWER_UP.search(t)], [], name)

    def test_the_hint_on_the_talismans_page(self):
        drawn = texts(open_screen("powerups"))
        self.assertTrue(any("Point at a talisman" in t for t in drawn), drawn)

    def test_the_rules_a_friend_sees(self):
        stun, brokers = netcode.STUN_SERVERS, rooms.BROKERS
        netcode.STUN_SERVERS, rooms.BROKERS = [("127.0.0.1", 9)], []
        app.net = HostSession(app, port = 0, upnp = False)
        try:
            self.assertIn("Talismans on", app.net.settings_summary())
            self.assertNotRegex(app.net.settings_summary(), POWER_UP)
        finally:
            app.net.close()
            app.net = None
            netcode.STUN_SERVERS, rooms.BROKERS = stun, brokers


if __name__ == "__main__":
    unittest.main()
