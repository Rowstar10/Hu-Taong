"""The music line-up, 1.9 (Rowan's 1.9 plan, phase 1).

Rowan: the circus-sounding track goes (Waltz of the Carnies), and ten spooky-playful Kevin MacLeod
tracks come in (CC BY 4.0, from incompetech.com), plus Rowan's two picks from Pixabay ("Chinese Game"
and "Halloween Playful"), played once their files are in the music folder.  Every track the jukebox
plays is credited, has its loudness measured for Even Out Volume, and is in the folder.
"""
import json
import unittest

from tests import harness

app = harness.app()

from config import BASE_DIR, MUSIC_DIR                          # noqa: E402

pools = app.settings.audio.pools
listed = [t for mood in pools.values() for t in mood]
PICKS = ("Chinese Game.mp3", "Halloween Playful.mp3")          # (Rowan downloads these)
NEW = ("Sneaky Snitch.mp3", "Investigations.mp3", "Moonlight Hall.mp3", "Netherworld Shanty.mp3",
       "Professor and the Plant.mp3", "Marty Gots a Plan.mp3", "Thinking Music.mp3", "Brittle Rille.mp3",
       "Comic Hero.mp3", "Laconic Granny.mp3")


class LineUp(unittest.TestCase):
    def test_no_circus(self):
        self.assertNotIn("Waltz of the Carnies.mp3", listed)
        self.assertFalse((MUSIC_DIR / "Waltz of the Carnies.mp3").exists())

    def test_the_new_tracks_and_the_picks(self):
        for track in NEW + PICKS:
            self.assertIn(track, listed)
        for track in NEW:
            self.assertTrue((MUSIC_DIR / track).exists(), track)
        self.assertEqual([t for t in PICKS if t in pools["game"]], list(PICKS), "the picks play in matches")

    def test_every_track_is_there_measured_and_credited(self):
        loudness = json.loads((MUSIC_DIR / "loudness.json").read_text())
        credits = (BASE_DIR / "CREDITS.md").read_text(encoding = "utf-8")
        for track in listed:
            if track in PICKS and not (MUSIC_DIR / track).exists():
                continue
            with self.subTest(track = track):
                self.assertTrue((MUSIC_DIR / track).exists())
                self.assertIn(track, loudness)
        for track in NEW + PICKS:
            self.assertIn(f"| {track} |", credits)

    def test_a_track_not_downloaded_yet_is_skipped(self):
        sound = app.sound_manager
        mood = sound.mood
        try:
            sound.mood = "game"
            here = sound.pool
            for track in PICKS:
                self.assertEqual(track in here, (MUSIC_DIR / track).exists())
            self.assertIn("Sneaky Snitch.mp3", here)
        finally:
            sound.mood = mood


if __name__ == "__main__":
    unittest.main()
