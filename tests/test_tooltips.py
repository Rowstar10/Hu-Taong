"""Tooltips that quote a number from the game's settings (1.4 fix).

1.3 raised the hard-hit speed limit from 2.4 to 4.5 times serve speed, but the Ball Speed
tooltip still said 2.4.
"""
import re
import unittest

from tests import harness

harness.app()

from config import MAX_BALL_SPEEDUP            # noqa: E402  (after the harness has set things up)
from render.renderer import TIPS               # noqa: E402


class TooltipNumbers(unittest.TestCase):
    def test_ball_speed_tip_matches_the_speed_limit(self):
        times = re.findall(r"([\d.]+) times", TIPS["ball_speed_slider"])
        self.assertEqual([float(t) for t in times], [MAX_BALL_SPEEDUP])


if __name__ == "__main__":
    unittest.main()
