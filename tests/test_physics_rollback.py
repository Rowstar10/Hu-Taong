"""One physics again, 1.8 (Rowan's fourth 1.8 playtest, 2026-11-18).

"I want to roll back the physics engine update from v1.8.  I only want one physics engine, and I want
it to work the same way it did before v1.8."  So the Physics choice (Current, Classic, v0.9) and the
Speed Cap are gone, and a ball comes off a paddle as in 1.7 (objects/paddle.py is 1.7's again).  A
save that has them still loads; they're just left out.  The friend's screen online plays hits by
1.7's rule too.  (The one change Rowan asked for alongside is test_paddle_sandwich.)
"""
import inspect
import json
import unittest

from tests import harness

app = harness.app()

from core import save_data                                      # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from objects.paddle import Paddle                               # noqa: E402

m = app.settings.match


class OnePhysics(unittest.TestCase):
    def test_no_physics_choice_and_no_speed_cap(self):
        for name in ("physics", "speed_cap", "PHYSICS", "classic_physics", "v09_physics"):
            self.assertFalse(hasattr(m, name), name)
        gameplay = save_data.collect(app)["gameplay"]
        self.assertNotIn("physics", gameplay)
        self.assertNotIn("speed_cap", gameplay)

    def test_the_paddle_hits_as_in_1_7(self):
        for name in ("keep_behind", "give_way", "classic_return", "v09_return"):
            self.assertFalse(hasattr(Paddle, name), name)
        self.assertNotIn("physics", inspect.signature(GuestMatchState.bounce_off).parameters)

    def test_a_save_with_them_still_loads(self):
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            data = save_data.collect(app)
            data["gameplay"].update(physics = 2, speed_cap = True, ball_speed = 610)
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(json.dumps(data))
            m.reset()
            save_data.load(app)
            self.assertEqual(m.ball_speed, 610, "the rest of it loaded")
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)
            m.reset()


if __name__ == "__main__":
    unittest.main()
