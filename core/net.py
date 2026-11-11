"""Online play: one player hosts, a friend joins with a code.

The host's game runs the match: physics, power-ups, scoring, everything.  The guest sends its
keys sixty times a second and the host sends back what is on court, in the same rows of numbers
the replays use (see game/replay.py), so the guest simply draws what the host sees.  The guest's
own paddle is predicted from its own keys, so it answers at once, and quietly corrected.

Everything travels over UDP: a packet that's lost is simply replaced by the next one, which is
always the latest news.  Anything that must arrive (a pause, a rematch, leaving) is repeated in
every packet until the other side shows it saw it.

Getting through home routers: each game asks a public STUN server what internet address and port
its socket is seen from.  The host posts a sealed note of where it can be reached, under a hash of
its game's code, on the message servers the room list uses (core/rooms.py); a friend with the
code reads it and posts a knock with their own address.  Then both games send packets to each other
at once, and each router, seeing its own player's packet go out to the other, lets the reply in
("hole punching").  The host also asks its router to open the port (UPnP), and both try the local
network, so whichever way works, wins.  An address typed as 1.2.3.4:5678 is tried directly.
"""
import ipaddress, json, os, random, re, socket, struct, threading, time
import urllib.request
from collections import deque
from array import array
from xml.etree import ElementTree

from core import rooms

PORT = 47620
PROTOCOL = 8                  # raised whenever the messages change, so old and new builds turn each other away clearly
MAGIC = b"HT"
TIMEOUT = 6.0                 # seconds of silence before the other side is taken as gone
SEND_RATE = 60                # packets a second each way

# Packet kinds (PUNCH only opens the way through a router; nobody reads it)
HELLO, WELCOME, REFUSE, INPUT, SNAP, BYE, PUNCH = range(1, 8)

# Public STUN servers: they answer "your address is ..." and nothing else
STUN_SERVERS = [("stun.l.google.com", 19302), ("stun1.l.google.com", 19302), ("stun.cloudflare.com", 3478)]
STUN_COOKIE = 0x2112A442

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"     # no 0/O or 1/I to misread


# ---------------------------------------------------------------- Codes

def make_code(ip, port):
    """An IPv4 address and port as a short code, e.g. 'K7Q2-9FHD-AB'."""
    n = int(ipaddress.IPv4Address(ip)) << 16 | port
    chars = []
    for _ in range(10):
        chars.append(ALPHABET[n % 32])
        n //= 32
    text = "".join(reversed(chars))
    return f"{text[:4]}-{text[4:8]}-{text[8:]}"


def make_room_code():
    """A game's code: eight letters and numbers, like 'K7Q2-9FHD'."""
    text = "".join(random.choice(ALPHABET) for _ in range(8))
    return f"{text[:4]}-{text[4:]}"


def read_room_code(text):
    """A game's code as typed (any case, with or without the dash, O for 0...), or None."""
    clean = re.sub(r"[\s-]", "", text.strip().upper()).replace("O", "0").replace("I", "1")
    if len(clean) != 8 or any(c not in ALPHABET for c in clean):
        return None
    return f"{clean[:4]}-{clean[4:]}"


def read_code(text):
    """(ip, port) from a code, or from an address typed as 1.2.3.4 or 1.2.3.4:5678; None if neither."""
    text = text.strip()
    m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?", text)
    if m:
        try:
            ip = str(ipaddress.IPv4Address(m.group(1)))
        except ValueError:
            return None
        port = int(m.group(2) or PORT)
        return (ip, port) if 0 < port < 65536 else None
    clean = re.sub(r"[\s-]", "", text.upper()).replace("O", "0").replace("I", "1")
    if len(clean) != 10 or any(c not in ALPHABET for c in clean):
        return None
    n = 0
    for c in clean:
        n = n * 32 + ALPHABET.index(c)
    ip, port = n >> 16, n & 0xFFFF
    if ip >= 2 ** 32 or not port:
        return None
    return str(ipaddress.IPv4Address(ip)), port


def lan_address():
    """This computer's address on the local network (no packet is sent to find it)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def reachable_from_internet(ip):
    """False for addresses only a local network (or a provider's shared network) can reach."""
    try:
        a = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return not (a.is_private or a.is_loopback or a in ipaddress.IPv4Network("100.64.0.0/10"))


# ---------------------------------------------------------------- UPnP

class PortOpener:
    """Asks the router, on a worker thread, to forward the game's port here, and for the router's
    internet address.  `status` is "working", "open", or "failed" (with `reason`)."""

    def __init__(self, port):
        self.port = port
        self.status = "working"
        self.reason = ""
        self.external = None
        self.control = None
        self.service = None
        threading.Thread(target=self.run, daemon=True, name="upnp").start()

    def run(self):
        try:
            location = self.discover()
            if not location:
                raise OSError("the router didn't answer (UPnP may be switched off)")
            self.control, self.service = self.find_service(location)
            self.soap("AddPortMapping", [("NewRemoteHost", ""), ("NewExternalPort", self.port),
                                         ("NewProtocol", "UDP"), ("NewInternalPort", self.port),
                                         ("NewInternalClient", lan_address()), ("NewEnabled", 1),
                                         ("NewPortMappingDescription", "Hu Taong"), ("NewLeaseDuration", 0)])
            reply = self.soap("GetExternalIPAddress", [])
            m = re.search(rb"<NewExternalIPAddress>([^<]*)</NewExternalIPAddress>", reply)
            self.external = m.group(1).decode() if m else None
            self.status = "open"
        except Exception as e:
            self.status, self.reason = "failed", str(e) or e.__class__.__name__

    @staticmethod
    def discover():
        msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\n"
               "MX: 2\r\nST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n").encode()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.5)
        try:
            s.sendto(msg, ("239.255.255.250", 1900))
            while True:
                data, _ = s.recvfrom(4096)
                m = re.search(rb"(?im)^location:\s*(\S+)", data)
                if m:
                    return m.group(1).decode()
        except OSError:
            return None
        finally:
            s.close()

    @staticmethod
    def find_service(location):
        xml = urllib.request.urlopen(location, timeout=3).read()
        root = ElementTree.fromstring(xml)
        ns = {"d": "urn:schemas-upnp-org:device-1-0"}
        base = location[:location.index("/", 8)]
        for service in root.iter("{urn:schemas-upnp-org:device-1-0}service"):
            kind = service.findtext("d:serviceType", default="", namespaces=ns)
            if "WANIPConnection" in kind or "WANPPPConnection" in kind:
                url = service.findtext("d:controlURL", default="", namespaces=ns)
                return (url if url.startswith("http") else base + ("" if url.startswith("/") else "/") + url), kind
        raise OSError("the router doesn't offer port forwarding by UPnP")

    def soap(self, action, args):
        body = "".join(f"<{k}>{v}</{k}>" for k, v in args)
        envelope = ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
                    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
                    f'<u:{action} xmlns:u="{self.service}">{body}</u:{action}></s:Body></s:Envelope>')
        request = urllib.request.Request(self.control, data=envelope.encode(), method="POST", headers={
            "Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": f'"{self.service}#{action}"'})
        return urllib.request.urlopen(request, timeout=3).read()

    def close(self):
        """Take the forwarding down again (in the background; it doesn't matter if it fails)."""
        if self.status != "open":
            return
        def run():
            try:
                self.soap("DeletePortMapping", [("NewRemoteHost", ""), ("NewExternalPort", self.port),
                                                ("NewProtocol", "UDP")])
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- The link

class Link:
    """A non-blocking UDP socket and the other side's address.  Tests can make it lose or
    delay packets, to play as if over a bad connection."""

    def __init__(self, port=0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        self.sock.bind(("0.0.0.0", port))
        self.sock.setblocking(False)
        self.port = self.sock.getsockname()[1]
        self.peer = None
        self.heard = time.perf_counter()
        self.loss = 0.0              # share of packets dropped (testing)
        self.delay = 0.0             # seconds each packet is held back (testing)
        self.held = []
        self.mapped = {}             # STUN server -> (ip, port) this socket is seen from on the internet
        self.asked = {}              # STUN request id -> the server it went to
        self.stun_servers = STUN_SERVERS

    # ---------------- STUN: what address are we seen from? ----------------

    def ask_stun(self):
        """Ask the STUN servers, from this socket, what address it is seen from (on a worker
        thread, as finding the servers can wait on the network)."""
        def run():
            for host, port in self.stun_servers:
                try:
                    ip = socket.gethostbyname(host)
                except (OSError, UnicodeError):
                    continue
                request = os.urandom(12)
                self.asked[request] = (ip, port)
                message = struct.pack("!HHI", 0x0001, 0, STUN_COOKIE) + request
                for _ in range(3):
                    try:
                        self.sock.sendto(message, (ip, port))
                    except OSError:
                        break
                    time.sleep(0.25)
        threading.Thread(target = run, daemon = True, name = "stun").start()

    def read_stun(self, data):
        server = self.asked.get(data[8:20])
        if server is None:
            return
        pos = 20
        while pos + 4 <= len(data):
            kind, size = struct.unpack_from("!HH", data, pos)
            value = data[pos + 4:pos + 4 + size]
            if kind in (0x0020, 0x0001) and len(value) >= 8 and value[1] == 1:      # (XOR-)MAPPED-ADDRESS, IPv4
                port = struct.unpack_from("!H", value, 2)[0]
                ip = struct.unpack_from("!I", value, 4)[0]
                if kind == 0x0020:
                    port ^= STUN_COOKIE >> 16
                    ip ^= STUN_COOKIE
                self.mapped[server] = (str(ipaddress.IPv4Address(ip)), port)
                if kind == 0x0020:
                    break
            pos += 4 + size + (-size % 4)

    def public(self):
        """The internet address and port this socket is seen from, once a STUN server has said."""
        for address in self.mapped.values():
            return address
        return None

    def symmetric(self):
        """Does the router give this socket a different port for every place it talks to?  (Then
        hole punching won't get through it.)"""
        return len(set(self.mapped.values())) > 1

    def send(self, kind, payload, to=None):
        to = to or self.peer
        if to is None:
            return
        data = MAGIC + bytes([PROTOCOL, kind]) + payload
        if self.loss and random.random() < self.loss:
            return
        if self.delay:
            self.held.append((time.perf_counter() + self.delay, data, to))
            return
        try:
            self.sock.sendto(data, to)
        except OSError:
            pass

    def flush(self):
        now = time.perf_counter()
        due = [h for h in self.held if h[0] <= now]
        self.held = [h for h in self.held if h[0] > now]
        for _, data, to in due:
            try:
                self.sock.sendto(data, to)
            except OSError:
                pass

    def receive(self):
        """Every packet waiting: [(kind, payload, address)]."""
        self.flush()
        got = []
        for _ in range(256):
            try:
                data, address = self.sock.recvfrom(65536)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:          # Windows reports an unreachable peer this way
                continue
            if len(data) >= 20 and data[:2] == b"\x01\x01" and struct.unpack_from("!I", data, 4)[0] == STUN_COOKIE:
                self.read_stun(data)
                continue
            if len(data) < 4 or data[:2] != MAGIC:
                continue
            got.append((data[3], data[4:], address, data[2]))
        return got

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def pack_json(data):
    return json.dumps(data, separators=(",", ":")).encode("utf-8")


def unpack_json(payload):
    if len(payload) > 60000:
        return None
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


# Inputs: the guest's held keys, as bits
UP, DOWN, LEFT, RIGHT = 1, 2, 4, 8


# ---------------------------------------------------------------- Host

class HostSession:
    """Waits for a friend, then runs the match for both."""
    role = "host"

    def __init__(self, app, port=PORT, upnp=True):
        self.app = app
        self.link = Link(port)
        self.port = self.link.port
        self.opener = PortOpener(self.port) if upnp else None
        self.lan = lan_address()
        self.guest = None            # the guest's address once it has said hello
        self.guest_keys = 0
        self.guest_seq = 0           # the last input it sent that the host has read
        self.applied_seq = 0         # the last input whose keys the match has moved the friend's paddle with
        self.guest_requests = {}     # request counters seen from the guest: pause, resume, rematch
        self.guest_menu = 0          # what the guest has open: 0 nothing, 1 the pause screen, 2 deeper (settings)
        self.claims = []             # saves the guest saw on its own screen, waiting to be checked
        self.claims_seen = set()
        self.acks = {}               # claim id -> the host time it was played at, or -1 if it didn't stand
        self.handled = {}
        self.ping = None
        self.guest_clock = 0.0
        self.last_send = 0.0
        self.snap_seq = 0
        self.game = None
        self.over = None             # the result, once the match is won: {"winner": 1 or 2, ...}
        self.rematch_asked = False
        self.events_sent = 0
        self.closed = False
        self.notice = None           # something to tell the player (the guest left...)
        self.friend_left = None      # why the guest went, if they went mid-match: the match ends there
        self.password = ""           # asked of anyone joining, if set
        self.room_name = ""
        self.ad = None               # a public listing of this game (core/rooms.py), while it's public
        self.last_guest = None       # the address of whoever joined last
        self.last_ad = 0.0
        self.room_code = make_room_code()
        self.door = rooms.Door(self.room_code) if upnp else None    # (tests without the internet leave it out)
        self.punching = {}           # address -> until when to keep sending it PUNCH packets
        self.last_stun = time.perf_counter()
        self.last_punch = 0.0
        if upnp:
            self.link.ask_stun()

    # what to show the player in the lobby
    def code(self):
        """The game's code, for a friend to type."""
        return self.room_code

    def addresses(self):
        """Every address this game might be reached at: from the internet (as STUN and the router
        see it) and on the local network."""
        found = []
        public = self.link.public()
        if public:
            found.append(public)
        if self.opener and self.opener.status == "open" and self.opener.external:
            found.append((self.opener.external, self.port))
        found.append((self.lan, self.port))
        return [a for i, a in enumerate(found) if a not in found[:i]]

    def internet_address(self):
        """How the internet sees this game, as text, or None if no one has said yet."""
        public = self.link.public()
        if public:
            return f"{public[0]}:{public[1]}"
        if self.opener and self.opener.status == "open" and self.opener.external:
            return f"{self.opener.external}:{self.port}"
        return None

    def connected(self):
        return self.guest is not None and time.perf_counter() - self.link.heard < TIMEOUT

    def settings_summary(self):
        g = self.app.settings.gameplay
        from game import courts
        win = g.winning_scores[g.winning_score_index]
        parts = ["Endless" if win == "Endless Mode" else f"First to {win}",
                 f"Court: {courts.NAMES[g.court]}",
                 "Power-ups on" if g.powerups else "Power-ups off"]
        if g.chaos_mode:
            parts.append(["", "Chaos Mode", "Chaos Mode +"][g.chaos_mode])
        return "  -  ".join(parts)

    def guest_side(self):
        """1 if the friend plays Red (the left paddle), 2 for Blue."""
        return 1 if self.app.settings.gameplay.online_host_blue else 2

    def welcome(self):
        return pack_json({"summary": self.settings_summary(), "started": self.game is not None,
                          "side": self.guest_side()})

    def update(self, dt):
        if self.closed:
            return
        now = time.perf_counter()
        for kind, payload, address, version in self.link.receive():
            if kind == HELLO:
                hello = unpack_json(payload) or {}
                if version != PROTOCOL or hello.get("game") != "Hu Taong":
                    self.link.send(REFUSE, pack_json({"why": "Your friend has a different version of Hu Taong."}), address)
                    continue
                if self.guest is not None and address != self.guest and self.connected():
                    self.link.send(REFUSE, pack_json({"why": "That game already has two players."}), address)
                    continue
                if self.game is not None and self.ad is not None and address != self.last_guest:
                    # a public room mid-match: only the player who dropped out can come back in
                    self.link.send(REFUSE, pack_json({"why": "That room is in the middle of a match."}), address)
                    continue
                if self.password and hello.get("pw") != rooms.password_hash(self.password):
                    why = "That room needs a password." if not hello.get("pw") else "That password isn't right."
                    self.link.send(REFUSE, pack_json({"why": why, "password": True}), address)
                    continue
                if self.guest != address:
                    self.guest = self.last_guest = address
                    self.link.peer = address
                    self.guest_requests, self.handled = {}, {}
                self.link.heard = now
                self.link.send(WELCOME, self.welcome())
            elif kind == PUNCH:
                continue
            elif address == self.guest:
                self.link.heard = now
                if kind == INPUT:
                    self.read_input(payload)
                elif kind == BYE:
                    self.drop_guest("Your friend left the game.", "Your friend left the match.")
        if self.guest is not None and now - self.link.heard > TIMEOUT:
            self.drop_guest("Lost touch with your friend.", "Lost touch with your friend.")
        if self.game is None and self.guest is not None and now - self.last_send >= 0.5:
            # waiting in the lobby: keep in touch, and keep the friend up to date with the rules
            self.last_send = now
            self.link.send(WELCOME, self.welcome())
        if now - self.last_ad > 1.0:
            self.last_ad = now
            if self.door:
                self.door.update({"v": PROTOCOL, "addrs": [list(a) for a in self.addresses()]})
            if self.ad:
                self.ad.update({"v": PROTOCOL, "name": self.room_name or "A Hu Taong room", "code": self.room_code,
                                "rules": self.settings_summary(), "locked": bool(self.password),
                                "players": 2 if self.connected() else 1, "playing": self.game is not None})
        # A friend knocking with the code: send packets their way for a few seconds, so this
        # router lets their hello in (and theirs lets the answer back)
        if self.door:
            for knock in self.door.take_knocks():
                if not self.connected():
                    for address in knock:
                        self.punching[address] = now + 6.0
        if self.door and not self.connected() and now - self.last_stun > 20:
            self.last_stun = now             # keeps the router's way in open, and its address current
            self.link.ask_stun()
        if self.punching and now - self.last_punch > 0.1:
            self.last_punch = now
            self.punching = {a: until for a, until in self.punching.items() if until > now and not self.connected()}
            for address in self.punching:
                self.link.send(PUNCH, b"", address)

    def send_due(self):
        """Called by App.loop after this frame's update: the snapshot goes out with what this frame
        worked out (sent from update(), at the start of the frame, it was a frame old)."""
        if self.closed:
            return
        now = time.perf_counter()
        if self.game is not None and self.guest is not None and now - self.last_send >= 1 / SEND_RATE:
            # a steady SEND_RATE: the schedule steps on by one period rather than restarting from
            # now (which lost the part of a frame past the period, every time), and never runs
            # more than one period behind, so a hitch doesn't bank up a burst
            self.last_send = max(self.last_send + 1 / SEND_RATE, now - 1 / SEND_RATE)
            self.send_snapshot()

    # ---------------- Public listing ----------------

    def set_public(self, public):
        if public and self.ad is None:
            self.ad = rooms.RoomAd()
            self.last_ad = 0.0
        elif not public and self.ad is not None:
            self.ad.close()
            self.ad = None

    def listing(self):
        """How the public listing is doing, in words, or "" when the game isn't public."""
        if self.ad is None:
            return ""
        status = self.ad.status
        if status == "refused":
            return "Your server turned the login away: check its username and password under Online > Server"
        if status == "failed":
            return f"Couldn't reach {rooms.where()} for the room list (the network may block it)"
        return ("Putting it on the room list..." if status == "connecting" else
                "Listed: anyone with Hu Taong using the same server can find it" if rooms.OWN else
                "Listed: anyone with Hu Taong can find it")

    def reach(self):
        """Whether friends can get in with the code, in words."""
        door = self.door
        if door is None:
            return ""
        if door.status == "connecting":
            return "Getting the code ready..."
        if door.status == "refused":
            return "Your server turned the login away: check its username and password under Online > Server"
        if door.status == "failed":
            return (f"Couldn't reach {rooms.where()}: switch servers under Online > Server, or use an address below"
                    if rooms.OWN else
                    "Couldn't reach the servers codes go through (the network may block them): use an address below")
        if self.link.symmetric() and not (self.opener and self.opener.status == "open"):
            return "Code ready, but your router may block friends: if they can't get in, let them host"
        return "Code ready: your friend types it under Join with a Code"

    def read_input(self, payload):
        if len(payload) < 13:
            return
        seq, keys, clock = struct.unpack_from("<IBd", payload, 0)
        if seq > self.guest_seq:
            self.guest_seq, self.guest_keys = seq, keys
        self.guest_clock = clock
        extra = unpack_json(payload[13:]) or {}
        # the round trip, by this game's own clock: the time it put in a snapshot, as the guest
        # sends it back.  (The guest's "echo" is the guest's own clock, which on another computer
        # has nothing to do with this one's: subtracting it read 0, or hours.)
        echo = extra.get("hecho")
        if isinstance(echo, (int, float)) and echo > 0:
            self.ping = max(0.0, time.perf_counter() - echo)
        menu = extra.get("menu")
        if isinstance(menu, int):
            self.guest_menu = menu
        for claim in extra.get("claims", []) if isinstance(extra.get("claims"), list) else []:
            if isinstance(claim, dict) and isinstance(claim.get("id"), int) and claim["id"] not in self.acks \
                    and claim["id"] not in self.claims_seen:
                self.claims_seen.add(claim["id"])
                self.claims.append(claim)
        for name in ("pause", "resume", "rematch", "restart"):
            count = extra.get(name)
            if isinstance(count, int) and count > self.guest_requests.get(name, 0):
                self.guest_requests[name] = count

    def request_seen(self, name):
        """Has the guest asked for this since it was last dealt with (without dealing with it)?"""
        return self.guest_requests.get(name, 0) > self.handled.get(name, 0)

    def request(self, name):
        """True once for every new pause / resume / rematch the guest asked for."""
        count = self.guest_requests.get(name, 0)
        if count > self.handled.get(name, 0):
            self.handled[name] = count
            return True
        return False

    def send_snapshot(self):
        game = self.game
        rec = game.recorder
        row = rec.row()
        events = rec.events[-12:]
        first = len(rec.events) - len(events)
        state = self.app.state_manager.current()
        name = getattr(state, "NAME", "")
        # anything over the match on the host (pause, settings...) holds it for both, but not the
        # win screen, which the guest has its own of
        paused = name not in ("game", "win") and self.over is None
        host_menu = 0 if not paused else 1 if name == "pause" else 2
        # "seq": the input the paddle in this picture has been moved with (one read this frame
        # hasn't moved it yet), so the guest compares like with like
        info = {"seq": self.applied_seq, "echo": self.guest_clock, "hclock": time.perf_counter(),
                "paused": paused, "host_menu": host_menu,
                "events": [[first + i, *e[1:]] for i, e in enumerate(events)],
                "speed": [game.p1.speed, game.p2.speed],
                "guest": 1 if getattr(game.p1, "remote", False) else 2,
                "over": self.over, "rematch": self.rematch_asked,
                "acks": [[k, v] for k, v in list(self.acks.items())[-8:]],
                "info": {"labels": [p.controls_label if not getattr(p, "remote", False) else "Friend"
                                    for p in (game.p1, game.p2)],
                         "pace": game.settings.pace, "switch_each_point": game.settings.switch_each_point,
                         "court": game.court.name}}
        head = pack_json(info)
        self.snap_seq += 1
        self.link.send(SNAP, struct.pack("<IH", self.snap_seq, len(head)) + head + row)

    def drop_guest(self, notice, mid_match):
        """The guest left, or went quiet for too long.  Whatever they had open (the pause screen,
        settings) went with them, and so did their keys; a match they were playing ends."""
        self.guest = None
        self.link.peer = None
        self.guest_menu = 0
        self.guest_keys = 0
        self.notice = notice
        if self.game is not None:
            self.friend_left = mid_match

    def take_claims(self):
        claims, self.claims = self.claims, []
        return claims

    def keys_for(self, paddle):
        """The guest's held keys as (dvx, dvy) for its paddle."""
        k = self.guest_keys
        self.applied_seq = self.guest_seq
        return (((k & RIGHT) > 0) - ((k & LEFT) > 0), ((k & DOWN) > 0) - ((k & UP) > 0))

    def close(self):
        if self.closed:
            return
        self.closed = True
        for _ in range(3):
            self.link.send(BYE, b"")
        if self.opener:
            self.opener.close()
        self.set_public(False)
        if self.door:
            self.door.close()
        self.link.close()


# ---------------------------------------------------------------- Guest

class GuestSession:
    """Joins a friend's game: sends keys, keeps the latest pictures of the court."""
    role = "guest"
    BUFFER = 0.05                # seconds the picture is held back, so it can be smoothed (to start with:
    BUFFER_MIN, BUFFER_MAX = 0.03, 0.10      # it then follows how unevenly the pictures arrive)

    def __init__(self, app, address = None, password = "", room = None):
        self.app = app
        self.password = password
        self.needs_password = False  # the host turned us away for want of the right password
        self.link = Link(0)
        self.link.peer = address
        self.address = address       # the host's address, once known
        self.candidates = [address] if address else []     # where the host might be, while connecting
        self.room = room             # the game's code, when joining with one
        self.knock = None
        if room:
            self.knock = rooms.Knock(room)
            self.link.ask_stun()
        self.status = "connecting"   # connecting, waiting, playing, refused, lost
        self.reason = ""
        self.summary = ""
        self.side = 2                # which paddle you'll play: 1 Red, 2 Blue
        self.started = time.perf_counter()
        self.last_hello = 0.0
        self.last_send = 0.0
        self.seq = 0
        self.keys = 0
        self.axis = None             # on a phone: a finger's share of full speed, (x, y) from -1 to 1
        self.owed = [0.0, 0.0]
        self.history = []            # (seq, x, y) the guest's paddle was predicted at
        self.requests = {"pause": 0, "resume": 0, "rematch": 0, "restart": 0}
        self.menu = 0                # what's open over the match here: 0 nothing, 1 pause, 2 deeper
        self.claims = []             # saves seen here, sent until the host answers
        self.claim_id = 0
        self.acks = {}
        self.snaps = []              # [(host clock, row bytes, info)], oldest first
        self.last_snap = 0
        self.played = -1             # the last event id played
        self.ping = None
        self.info = {}
        self.frames = []             # every row, for the highlights afterwards
        self.closed = False
        self.notice = None
        self.BUFFER = GuestSession.BUFFER
        self.lateness = deque(maxlen = 180)  # for the last pictures: when each got here, less the host time it shows
        self.gaps = deque(maxlen = 60)       # host time between pictures
        self.tuned = 0

    def update(self, dt):
        if self.closed:
            return
        now = time.perf_counter()
        if self.knock:
            # the host's addresses, from its sealed note; and ours, to knock with
            for address in self.knock.host:
                if address not in self.candidates:
                    self.candidates.append(address)
            mine = [a for a in (self.link.public(), (lan_address(), self.link.port)) if a]
            if mine != self.knock.mine:
                self.knock.set_mine(mine)
        for kind, payload, address, version in self.link.receive():
            if self.address is None and address in self.candidates and kind in (WELCOME, REFUSE):
                self.address = address           # this way through works: keep to it
                self.link.peer = address
            if address != self.address:
                continue
            self.link.heard = now
            if kind == WELCOME:
                hello = unpack_json(payload) or {}
                self.summary = str(hello.get("summary", ""))
                self.side = 1 if hello.get("side") == 1 else 2
                if self.status == "connecting":
                    self.status = "waiting"
                elif self.status == "playing" and not hello.get("started"):
                    self.status = "waiting"      # the host went back to the lobby
                    self.new_match()
            elif kind == REFUSE:
                refusal = unpack_json(payload) or {}
                self.status = "refused"
                self.reason = str(refusal.get("why", "The host said no."))
                self.needs_password = bool(refusal.get("password"))
            elif kind == SNAP:
                self.read_snapshot(payload)
            elif kind == BYE:
                self.status = "lost"
                self.reason = "The host left the game."
        if self.status == "connecting":
            if now - self.last_hello > 0.2:
                self.last_hello = now
                hello = {"game": "Hu Taong"}
                if self.password:
                    hello["pw"] = rooms.password_hash(self.password)
                for address in ([self.address] if self.address else self.candidates):
                    self.link.send(HELLO, pack_json(hello), address)
            if self.knock and not self.knock.host and now - self.started > 12:
                self.status = "lost"
                self.reason = ("Your server turned the login away: check its username and password under Server."
                               if self.knock.status == "refused" else
                               "Couldn't find a game with that code. Check it, that your friend is still hosting, and "
                               "that you both use the same server (under Server)."
                               if self.knock.status != "failed" else
                               f"Couldn't reach {rooms.where()}: switch servers under Server, or ask your friend for "
                               "their address instead.")
            elif now - self.started > 16:
                self.status = "lost"
                self.reason = ("Found your friend's game, but couldn't get through to it. One of your routers may be "
                               "blocking it: try the other of you hosting, or see How to connect."
                               if self.knock and self.knock.host else
                               "No answer from that address. Check it, and that your friend is hosting.")
        elif self.status in ("waiting", "playing"):
            if now - self.link.heard > TIMEOUT:
                self.status = "lost"
                self.reason = "Lost touch with the host."

    def send_due(self):
        """Called by App.loop after this frame's update: the keys go out as this frame read them
        (sent from update(), at the start of the frame, they were a frame old)."""
        if self.closed or self.status not in ("waiting", "playing"):
            return
        now = time.perf_counter()
        if now - self.last_send >= 1 / SEND_RATE:
            self.last_send = max(self.last_send + 1 / SEND_RATE, now - 1 / SEND_RATE)     # steady, as the host's
            self.send_input()

    def send_input(self):
        self.seq += 1
        extra = dict(self.requests)
        extra["menu"] = self.menu
        if self.claims:
            extra["claims"] = self.claims[-4:]
        if self.snaps:
            extra["echo"] = self.snaps[-1][2].get("echo")
            if "hclock" in self.snaps[-1][2]:
                extra["hecho"] = self.snaps[-1][2]["hclock"]      # the host's own time, back to it
        payload = struct.pack("<IBd", self.seq, self.sent_keys(), time.perf_counter()) + pack_json(extra)
        self.link.send(INPUT, payload)

    def sent_keys(self):
        """The keys this input carries.  A phone's finger asks for part of full speed, and every
        game reads only keys held or not: so the keys go out held for that share of the inputs,
        carrying what's left over to the next, and the host's paddle averages back to the finger's
        speed (any host, a PC's too)."""
        if self.axis is None:
            self.owed = [0.0, 0.0]
            return self.keys
        keys = 0
        for i, (minus, plus) in enumerate(((LEFT, RIGHT), (UP, DOWN))):
            owed = self.owed[i] + max(-1.0, min(1.0, self.axis[i]))
            step = 1 if owed >= 0.5 else -1 if owed <= -0.5 else 0
            self.owed[i] = owed - step
            keys |= plus if step > 0 else minus if step < 0 else 0
        return keys

    def read_snapshot(self, payload):
        try:
            seq, size = struct.unpack_from("<IH", payload, 0)
            info = unpack_json(payload[6:6 + size])
            row = payload[6 + size:]
        except struct.error:
            return
        if info is None or seq <= self.last_snap or len(row) % 4 or len(row) < 38 * 4:
            return
        self.last_snap = seq
        clock = struct.unpack_from("<f", row, 0)[0]
        self.status = "playing"
        echo = info.get("echo")
        if isinstance(echo, (int, float)) and echo > 0:
            self.ping = max(0.0, time.perf_counter() - echo)
        self.info = info
        for pair in info.get("acks", []):
            if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], int):
                self.acks[pair[0]] = pair[1]
        self.claims = [c for c in self.claims if c["id"] not in self.acks]
        prev = self.snaps[-1][0] if self.snaps else None
        self.snaps.append((clock, row, info, time.perf_counter()))
        del self.snaps[:-40]
        if prev is not None and 0 < clock - prev < 0.25:          # (not while the host's match stands paused)
            self.gaps.append(clock - prev)
            self.tune_buffer(time.perf_counter() - clock)
        if not self.frames or self.frames[-1] != row:
            self.frames.append(row)
            if len(self.frames) > 60 * 60 * 30:
                del self.frames[:60 * 60]

    def tune_buffer(self, late):
        """Hold the picture back by as much as the pictures' arrival varies (the trip, its jitter,
        either game's frames), so the picture rarely catches up with the newest one and stops:
        little on a steady link, more on a bad one.  It grows at once and eases back down."""
        if self.lateness and abs(late - sorted(self.lateness)[len(self.lateness) // 2]) > 0.3:
            self.lateness.clear()                  # the host paused (its clock stood still), or a new match
        self.lateness.append(late)
        self.tuned += 1
        if len(self.lateness) < 30 or self.tuned % 6:
            return
        d = sorted(self.lateness)
        mean = sum(d) / len(d)
        high = d[int(0.90 * (len(d) - 1))]       # (the rarer, longer holdups the guest's clock runs through)
        gap = sorted(self.gaps)[len(self.gaps) // 2]
        want = max(self.BUFFER_MIN, min(self.BUFFER_MAX, high - mean + gap / 2 + 0.005))
        self.BUFFER = want if want > self.BUFFER else self.BUFFER + (want - self.BUFFER) * 0.1

    def request(self, name):
        self.requests[name] += 1

    def new_match(self):
        """Back in the lobby: forget the last match's pictures, ready for the next."""
        self.snaps, self.frames, self.claims, self.acks = [], [], [], {}
        self.played, self.info, self.menu = -1, {}, 0
        self.__dict__.pop("event_log", None)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.address:
            for _ in range(3):
                self.link.send(BYE, b"")
        if self.knock:
            self.knock.close()
        self.link.close()
