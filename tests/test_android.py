"""Runs tests/android_suite.py, the game as it plays on a phone, in its own Python (pygame allows
one window per Python, and the phone's game has a different one)."""
import os
import subprocess
import sys
import unittest

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Android(unittest.TestCase):
    def test_the_phone_version(self):
        env = dict(os.environ, HUTAONG_ANDROID = "1")
        result = subprocess.run([sys.executable, "-m", "unittest", "tests.android_suite"], cwd = GAME, env = env,
                                capture_output = True, text = True, timeout = 600)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-8000:])


if __name__ == "__main__":
    unittest.main()
