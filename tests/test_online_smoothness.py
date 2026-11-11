"""Online play feeling laggy and glitchy (1.5 fixes).

Measured with two copies of the game on a fake internet link in November 2026, 1.4 had these
problems.  Each test below checks one of them stays fixed.
  - Pictures and keys went out 39-51 times a second instead of 60, and a frame late.
  - The guest's picture froze whenever a picture came late, and then jumped.
  - The guest's picture was held back the same 0.05 s on every link, good or bad.
  - The host's ping subtracted the guest's clock from its own (0, or hours, between two PCs).
  - The guest's paddle record was a frame ahead of the host's, so it was nudged back as it
    moved and on again when it stopped.
Nothing goes over the internet: the "friend" is a socket on this computer, and time is faked.
"""
import random
import struct
import unittest
from array import array

from unittest import mock

from tests import harness

app = harness.app()

import core.net as netcode                                   # noqa: E402
from core.net import GuestSession, HostSession, Link, SEND_RATE, pack_json, unpack_json     # noqa: E402
from core.states import guest_state                          # noqa: E402


class FakeClock:
    """Stands in for core.net's time module, so the tests choose the time."""
    def __init__(self, now = 100.0):
        self.now = now

    def perf_counter(self):
        return self.now


def host_with_friend():
    net = HostSession(app, port = 0, upnp = False)
    net.guest = net.last_guest = ("127.0.0.1", 9)
    net.link.peer = net.guest
    return net


class SendRate(unittest.TestCase):
    def setUp(self):
        self.net = host_with_friend()
        self.net.game = object()                       # a match is on (send_snapshot is counted, not run)
        self.sent = []
        self.net.send_snapshot = lambda: self.sent.append(self.clock.now)
        self.clock = FakeClock()
        patcher = mock.patch.object(netcode, "time", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.net.close)
        # the friend was last heard from on the fake clock too (on the real one, a computer that
        # started less than a minute and a half ago had them silent for longer than TIMEOUT)
        self.net.link.heard = self.clock.now

    def run_frames(self, seconds, fps, jitter = 0.0):
        rng = random.Random(5)
        end = self.clock.now + seconds
        while self.clock.now < end:
            self.clock.now += 1 / fps + rng.uniform(-jitter, jitter)
            self.net.send_due()

    def test_sixty_a_second_at_sixty_fps(self):
        # 1.4 restarted its timer from "now" after each send, so a frame a hair early skipped a send
        self.run_frames(5, 60, jitter = 0.003)
        self.assertGreaterEqual(len(self.sent), 5 * SEND_RATE - 5)

    def test_sixty_a_second_at_a_faster_frame_rate(self):
        self.run_frames(5, 144, jitter = 0.002)
        self.assertAlmostEqual(len(self.sent), 5 * SEND_RATE, delta = 3)

    def test_a_hitch_does_not_bank_up_a_burst(self):
        self.run_frames(1, 60)
        self.clock.now += 0.5                          # half a second stuck (loading a song, say)
        before = len(self.sent)
        self.net.send_due()
        self.net.send_due()                            # the same moment again: nothing more to send
        self.assertEqual(len(self.sent), before + 1)
        self.run_frames(1, 60)
        self.assertLessEqual(len(self.sent), before + 1 + SEND_RATE + 1)

    def test_pictures_go_out_after_the_frame_is_worked_out(self):
        # update() reads the friend's keys at the start of the frame; it no longer sends the picture,
        # which would have shown the frame before
        self.clock.now += 1
        self.net.update(1 / 60)
        self.assertEqual(self.sent, [])
        self.net.send_due()
        self.assertEqual(len(self.sent), 1)


class FrameOrder(unittest.TestCase):
    def test_the_app_sends_after_updating_the_match(self):
        net = host_with_friend()
        self.addCleanup(net.close)
        calls = []
        with mock.patch.object(app, "net", net), \
                mock.patch.object(net, "update", lambda dt: calls.append("read")), \
                mock.patch.object(net, "send_due", lambda: calls.append("send")), \
                mock.patch.object(app.state_manager, "update", lambda dt: calls.append("match")):
            app.loop()
        self.assertEqual(calls, ["read", "match", "send"])

class Ping(unittest.TestCase):
    def test_host_ping_uses_its_own_clock(self):
        net = host_with_friend()
        self.addCleanup(net.close)
        clock = FakeClock(100.0)
        with mock.patch.object(netcode, "time", clock):
            guest_clock = 3700.5                       # another PC's clock: nothing to do with this one's
            extra = {"echo": guest_clock - 0.2, "hecho": 100.0 - 0.08}
            net.read_input(struct.pack("<IBd", 1, 0, guest_clock) + pack_json(extra))
        self.assertAlmostEqual(net.ping, 0.08, places = 6)

    def test_old_guests_echo_is_not_read_as_a_ping(self):
        net = host_with_friend()
        self.addCleanup(net.close)
        with mock.patch.object(netcode, "time", FakeClock(100.0)):
            net.read_input(struct.pack("<IBd", 1, 0, 3700.5) + pack_json({"echo": 3700.0}))
        self.assertIsNone(net.ping)                    # no ping shown, rather than a wrong one

    def test_guest_sends_the_hosts_time_back(self):
        guest = GuestSession(app, address = ("127.0.0.1", 9))
        self.addCleanup(guest.close)
        guest.snaps = [(1.0, b"", {"echo": 5.0, "hclock": 123.25}, None)]
        sent = []
        with mock.patch.object(guest.link, "send", lambda kind, payload, *a: sent.append(payload)):
            guest.send_input()
        extra = unpack_json(sent[0][13:])
        self.assertEqual(extra["hecho"], 123.25)


def picture(seq, clock, info = None):
    """A snapshot packet as the host sends it, with an empty court."""
    info = pack_json(info or {"guest": 2})
    row = struct.pack("<f", clock) + bytes(37 * 4)
    return struct.pack("<IH", seq, len(info)) + info + row


class PictureBuffer(unittest.TestCase):
    def setUp(self):
        self.guest = GuestSession(app, address = ("127.0.0.1", 9))
        self.addCleanup(self.guest.close)
        self.clock = FakeClock(50.0)
        patcher = mock.patch.object(netcode, "time", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def feed(self, seconds, trip):
        """Pictures 60 a second, each arriving `trip()` seconds after the host made it."""
        arrivals = []
        for i in range(int(seconds * 60)):
            host_time = 10.0 + i / 60
            arrivals.append((host_time + trip(), host_time))
        arrivals.sort()                                # a late one can be overtaken
        for n, (arrive, host_time) in enumerate(arrivals, 1):
            self.clock.now = arrive
            self.guest.read_snapshot(picture(n, host_time))

    def buffer_after(self, jitter):
        rng = random.Random(3)
        self.feed(5, lambda: 0.03 + rng.uniform(0, jitter))
        return self.guest.BUFFER

    def test_holds_back_by_how_unevenly_pictures_arrive(self):
        steady = self.buffer_after(0.0)
        self.setUp()
        wifi = self.buffer_after(0.06)                 # Wi-Fi-like: up to 60 ms of jitter
        self.setUp()
        bad = self.buffer_after(0.15)                  # a bad link: up to 150 ms
        self.assertGreaterEqual(steady, GuestSession.BUFFER_MIN)
        self.assertLess(steady, 0.035)
        self.assertGreater(wifi, steady + 0.005)
        self.assertGreater(bad, wifi + 0.01)
        self.assertLessEqual(bad, GuestSession.BUFFER_MAX)


def guest_screen():
    """A guest's match screen, as if joined to a host whose rally is on.  Returns the session, the
    screen and a real picture row from a match on this computer."""
    sm = app.state_manager
    sm.set_state("main_menu", mute = True)
    sm.push_state("game", mute = True)
    harness.settle(app)
    row = array("f")
    row.frombytes(sm.current().game.recorder.row())
    row[20], row[22] = -1, 0                           # no countdown, no goal: the rally is on
    sm.set_state("main_menu", mute = True)
    sm.push_state("guest_match", mute = True)
    harness.settle(app)
    guest = GuestSession(app, address = ("127.0.0.1", 9))
    guest.status = "playing"
    app.net = guest
    return guest, sm.current(), row


def leave_guest_screen():
    app.state_manager.set_state("main_menu", mute = True)
    harness.settle(app)
    app.leave_online()


class Freeze(unittest.TestCase):
    """The guest's picture used to stop dead on the newest picture whenever the next was late."""
    def setUp(self):
        self.guest, self.screen, self.row = guest_screen()
        self.addCleanup(leave_guest_screen)
        self.info = {"guest": 2, "info": {}, "seq": 0}

    def add_picture(self, clock):
        self.row[0] = clock
        self.guest.snaps.append((clock, self.row.tobytes(), self.info, None))

    def test_picture_runs_on_when_pictures_are_late(self):
        clock = 5.0
        for _ in range(60):                            # a second of pictures arriving on time
            clock += 1 / 60
            self.add_picture(clock)
            self.screen.update(1 / 60)
        newest = clock
        for _ in range(30):                            # then half a second with none
            self.screen.update(1 / 60)
        self.assertGreater(self.screen.clock, newest + 0.09)
        self.assertLessEqual(self.screen.clock, newest + guest_state.RUN_ON + 1e-9)


class PaddleRecord(unittest.TestCase):
    def test_host_reports_the_input_its_paddle_has_moved_with(self):
        net = host_with_friend()
        self.addCleanup(net.close)
        net.read_input(struct.pack("<IBd", 7, netcode.RIGHT, 1.0) + pack_json({}))
        self.assertEqual(net.applied_seq, 0)           # read, but the match hasn't moved the paddle yet
        self.assertEqual(net.keys_for(None), (1, 0))
        self.assertEqual(net.applied_seq, 7)

    def test_guest_notes_where_the_paddle_was_when_the_keys_went_out(self):
        guest, screen, row = guest_screen()
        self.addCleanup(leave_guest_screen)
        info = {"guest": 2, "info": {}, "seq": 0}
        guest.snaps.append((row[0], row.tobytes(), info, None))
        screen.update(1 / 60)                          # the first picture sets up the court
        screen.pred = [row[5], row[6], 0.0, 0.0]
        guest.keys = netcode.DOWN
        for seq in range(1, 20):
            guest.seq = seq                            # a new input went out with these keys
            before = (screen.pred[0], screen.pred[1])
            screen.predict(1 / 60, row.tobytes(), info)
            noted = screen.history[-1]
            self.assertEqual(noted[0], seq)
            self.assertAlmostEqual(noted[1], before[0], places = 4)
            self.assertAlmostEqual(noted[2], before[1], places = 4)
        self.assertGreater(screen.pred[1], row[6])      # and the paddle did move


if __name__ == "__main__":
    unittest.main()
