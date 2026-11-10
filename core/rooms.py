"""Public rooms: a host can list its game so anyone running Hu Taong can find it and join.

There is no Hu Taong server, so rooms are posted on free public MQTT message brokers, the kind
made for small projects and testing, or on a server of your own (Online > Server: any MQTT broker,
such as the one in server/hutaong_server.py).  A listed host posts a short note ("retained", so newcomers
get it at once) under one topic and refreshes it every few seconds; the room list reads every
note under that topic and shows the live ones.  Joining still goes straight to the host, just
as with a code: the brokers only carry the notes.

A note says the room's name, its rules, whether it's full, whether it has a password, and its
code, which is the host's internet address.  Anyone reading the topic can see these, so listing
a room is something the host chooses.  A password is never posted: the guest sends a hash of it
when joining, and the host checks it.

Anyone can post under the topic, so every note read is checked and trimmed before it's shown.
A host that vanishes without taking its note down is handled twice over: its "will" (a blank
note the broker posts when the connection drops) clears it, and a note that stops being
refreshed drops off the list.

MQTT here is the bare minimum of version 3.1.1 (connect, subscribe, publish, ping) over a plain
TCP socket, one worker thread per broker, so the game never waits on the network.
"""
import hashlib, json, random, socket, struct, threading, time

BROKERS = [("broker.emqx.io", 1883), ("broker.hivemq.com", 1883), ("test.mosquitto.org", 1883)]
OWN = None          # your own server, when chosen: (host, port, username, password)
TOPIC = "hutaong/v3/rooms"
DOORS = "hutaong/v3"      # where a game's sealed notes go, under a hash of its code (see Door)
FRESH = 40          # seconds a room stays on the list without its note being refreshed
REFRESH = 10        # how often a host refreshes its note
RETRY = 15          # seconds between tries at a broker that couldn't be reached
MOST_ROOMS = 200    # notes kept at once, however many get posted
CODE_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.:-")
ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789")


class LoginRefused(OSError):
    """The server turned the username or password away."""


def parse_server(text):
    """(host, port) from a server address as typed ("example.com", "example.com:1883",
    "mqtt://203.0.113.7:1884"...), or None."""
    text = text.strip()
    for prefix in ("mqtt://", "tcp://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    text = text.rstrip("/")
    host, _, port = text.rpartition(":") if text.count(":") == 1 else (text, "", "")
    port = port or "1883"
    if not host or not port.isdigit() or not 0 < int(port) < 65536 or len(host) > 253:
        return None
    if not all(c.isalnum() or c in ".-_" for c in host):
        return None
    return host.lower(), int(port)


def use_server(address = None, username = "", password = ""):
    """Find rooms and codes through your own server (its address as typed), or through the free
    public ones (None).  Games already going keep the servers they started with."""
    global OWN
    found = parse_server(address) if address else None
    OWN = (found[0], found[1], username, password) if found else None


def active():
    """The servers rooms and codes go through: yours, or the free public ones."""
    return [OWN] if OWN else list(BROKERS)


def where():
    """Those servers, in words, for messages."""
    return f"your server ({OWN[0]})" if OWN else "the free public servers"


def check_server(address, username = "", password = "", timeout = 6):
    """Can we connect to (and log in to) a server?  Answers ("ok" | "refused" | "failed", detail)."""
    found = parse_server(address)
    if found is None:
        return "failed", "That doesn't look like a server address (like example.com or 203.0.113.7:1883)."
    try:
        Broker(found[0], found[1], timeout = timeout, login = (username, password) if username else None).close()
    except LoginRefused:
        return "refused", "It turned the username or password away."
    except OSError as e:
        return "failed", f"Couldn't reach it ({e.strerror or e})."
    return "ok", f"Connected to {found[0]}:{found[1]}."


def password_hash(password):
    """What a guest sends for a room's password: never the password itself."""
    return hashlib.sha256(f"hutaong-password:{password}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- MQTT

def _string(text):
    data = text.encode("utf-8") if isinstance(text, str) else text
    return struct.pack("!H", len(data)) + data


def _length(n):
    out = bytearray()
    while True:
        byte, n = n % 128, n // 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


class Broker:
    """One connection to one broker.  `will` is (topic, message): what the broker posts, retained,
    if this connection drops without saying goodbye."""

    def __init__(self, host, port, timeout = 6, will = None, login = None):
        self.sock = socket.create_connection((host, port), timeout = timeout)
        self.buffer = bytearray()
        self.packet_id = 0
        client = "hutaong-" + "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
        flags, payload = 0x02, _string(client)            # 0x02: a clean session
        if will is not None:
            flags |= 0x04 | 0x20                          # a will, retained
            payload += _string(will[0]) + _string(will[1])
        if login and login[0]:
            flags |= 0x80                                 # a username...
            payload += _string(login[0])
            if login[1]:
                flags |= 0x40                             # ...and a password
                payload += _string(login[1])
        try:
            self.send(0x10, _string("MQTT") + bytes([4, flags]) + struct.pack("!H", 60) + payload)
            deadline = time.time() + timeout
            while time.time() < deadline:
                for kind, body in self.packets():
                    if kind == 0x20 and len(body) >= 2 and body[1] == 0:
                        self.sock.settimeout(0.5)
                        return
                    if kind == 0x20 and len(body) >= 2 and body[1] in (4, 5):
                        raise LoginRefused("the server turned the login away")
                    raise OSError("the broker turned us away")
            raise OSError("the broker didn't answer")
        except OSError:
            self.sock.close()
            raise

    def send(self, header, body):
        self.sock.sendall(bytes([header]) + _length(len(body)) + body)

    def packets(self):
        """Every whole packet that has arrived, as (kind, body), after waiting up to the socket's
        timeout for more.  Half a packet waits in the buffer for the rest."""
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout:
            chunk = None
        else:
            if not chunk:
                raise OSError("the broker closed the connection")
            self.buffer += chunk
        out = []
        while True:
            packet = self.take_packet()
            if packet is None:
                return out
            out.append(packet)

    def take_packet(self):
        buf = self.buffer
        n, shift, i = 0, 0, 1
        while True:
            if i >= len(buf):
                return None
            byte = buf[i]
            i += 1
            n |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
            if shift > 21:
                raise OSError("garbled packet")
        if n > 256 * 1024:
            raise OSError("packet too big")
        if len(buf) < i + n:
            return None
        header, body = buf[0], bytes(buf[i:i + n])
        del buf[:i + n]
        return header & 0xF0, body

    def publish(self, topic, payload, retain = True):
        self.send(0x30 | (1 if retain else 0), _string(topic) + payload)

    def subscribe(self, topic):
        self.packet_id += 1
        self.send(0x82, struct.pack("!H", self.packet_id) + _string(topic) + bytes([0]))

    def ping(self):
        self.send(0xC0, b"")

    def close(self):
        try:
            self.send(0xE0, b"")
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


def _overall(states, good):
    """One word for how a set of brokers is doing."""
    states = list(states)
    if good in states:
        return good
    if "connecting" in states:
        return "connecting"
    if "refused" in states:
        return "refused"
    return "failed"


# ---------------------------------------------------------------- Listing a room

class RoomAd:
    """Hosting a public room: keep its note up to date on every broker that answers, and take it
    down when hosting stops."""

    def __init__(self, brokers = None):
        self.brokers_wanted = list(brokers or active())
        self.room_id = "".join(random.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(10))
        self.topic = f"{TOPIC}/{self.room_id}"
        self.note = None             # the latest note to post (a dict), or None to post nothing yet
        self.version = 0             # goes up whenever the note changes, so it's posted at once
        self.states = {}             # broker -> connecting, connected, listed, failed
        self.lock = threading.Lock()
        self.stop = threading.Event()
        for broker in self.brokers_wanted:
            self.states[broker] = "connecting"
            threading.Thread(target = self.post, args = (broker,), daemon = True, name = "room-ad").start()

    @property
    def status(self):
        """connecting, listed or failed."""
        return _overall(self.states.values(), "listed")

    def update(self, note):
        note = dict(note, id = self.room_id)
        with self.lock:
            if note != self.note:
                self.note = note
                self.version += 1

    def post(self, broker):
        key, (host, port), login = broker, broker[:2], broker[2:4] or None
        while not self.stop.is_set():
            try:
                broker = Broker(host, port, will = (self.topic, b""), login = login)
            except LoginRefused:
                self.states[key] = "refused"
                self.stop.wait(RETRY)
                continue
            except OSError:
                self.states[key] = "failed"
                self.stop.wait(RETRY)
                continue
            self.states[key] = "connected"
            posted, last = -1, 0.0
            try:
                while not self.stop.is_set():
                    with self.lock:
                        note, version = self.note, self.version
                    now = time.time()
                    if note is not None and (version != posted or now - last >= REFRESH):
                        data = json.dumps(dict(note, t = round(now)), separators = (",", ":")).encode("utf-8")
                        broker.publish(self.topic, data)
                        posted, last = version, now
                        self.states[key] = "listed"
                    elif now - last >= 30:
                        broker.ping()                       # nothing to post yet: stay connected
                        last = now
                    broker.packets()                        # waits half a second, and notices a dropped line
                broker.publish(self.topic, b"")             # take the note down: an empty retained note
            except OSError:
                pass
            finally:
                broker.close()
            if not self.stop.is_set():
                self.states[key] = "failed"
                self.stop.wait(RETRY)

    def close(self):
        self.stop.set()


# ---------------------------------------------------------------- Finding rooms

def clean_note(note, room_id):
    """A note read from a broker, checked and trimmed, or None if it isn't a real room's."""
    if not isinstance(note, dict) or note.get("id") != room_id:
        return None
    code = note.get("code")
    if not isinstance(code, str) or not 4 <= len(code) <= 32 or not set(code) <= CODE_CHARS:
        return None
    t = note.get("t")
    if isinstance(t, bool) or not isinstance(t, (int, float)) or t != t or abs(t) > 1e12:
        return None

    def text(value, most):
        words = "".join(c if c.isprintable() else " " for c in str(value)).split()
        return " ".join(words)[:most].strip()

    version = note.get("v")
    return {"id": room_id, "code": code, "t": float(t),
            "name": text(note.get("name", ""), 40) or "A Hu Taong room",
            "rules": text(note.get("rules", ""), 120),
            "locked": note.get("locked") is True,
            "players": 2 if note.get("players") == 2 else 1,
            "playing": note.get("playing") is True,
            "v": version if isinstance(version, int) and not isinstance(version, bool) else 0}


class RoomList:
    """Browsing: every live room, from every broker that answers."""

    def __init__(self, brokers = None):
        self.brokers_wanted = list(brokers or active())
        self.found = {}              # room id -> its note, plus when it was seen here
        self.states = {}             # broker -> connecting, open, failed
        self.lock = threading.Lock()
        self.stop = threading.Event()
        for broker in self.brokers_wanted:
            self.states[broker] = "connecting"
            threading.Thread(target = self.watch, args = (broker,), daemon = True, name = "room-list").start()

    @property
    def status(self):
        """connecting, open or failed."""
        return _overall(self.states.values(), "open")

    def rooms(self):
        """The rooms worth showing: open ones first, then in the order they were found, so the
        list doesn't shuffle under the mouse."""
        now = time.time()
        with self.lock:
            live = [n for n in self.found.values() if n["live"] and now - n["seen"] < FRESH]
        return sorted(live, key = lambda n: (n["players"] >= 2 or n["playing"], n["first"]))

    def watch(self, broker):
        key, (host, port), login = broker, broker[:2], broker[2:4] or None
        while not self.stop.is_set():
            try:
                broker = Broker(host, port, login = login)
            except LoginRefused:
                self.states[key] = "refused"
                self.stop.wait(RETRY)
                continue
            except OSError:
                self.states[key] = "failed"
                self.stop.wait(RETRY)
                continue
            try:
                broker.subscribe(f"{TOPIC}/+")
                self.states[key] = "open"
                last_ping = time.time()
                while not self.stop.is_set():
                    for kind, body in broker.packets():
                        if kind == 0x30 and len(body) >= 2:
                            size = struct.unpack_from("!H", body, 0)[0]
                            topic = body[2:2 + size].decode("utf-8", "replace")
                            self.take(topic, body[2 + size:])
                    if time.time() - last_ping > 25:
                        last_ping = time.time()
                        broker.ping()
            except OSError:
                pass
            finally:
                broker.close()
            if not self.stop.is_set():
                self.states[key] = "failed"
                self.stop.wait(RETRY)

    def take(self, topic, data):
        if not topic.startswith(TOPIC + "/"):
            return
        room_id = topic[len(TOPIC) + 1:]
        if not 1 <= len(room_id) <= 16 or not set(room_id) <= ID_CHARS:
            return
        now = time.time()
        with self.lock:
            if not data:
                self.found.pop(room_id, None)    # taken down
                return
            try:
                note = clean_note(json.loads(data.decode("utf-8")), room_id)
            except (ValueError, UnicodeDecodeError, RecursionError):
                return
            if note is None:
                return
            old = self.found.get(room_id)
            # A room counts as live once its note is recent by our clock, or has been refreshed
            # while we watched (the host's clock may be off).  A note left by a host that
            # vanished is never refreshed, so it never shows.
            note["live"] = (abs(now - note["t"]) < FRESH or
                            bool(old and (old["live"] or old["t"] != note["t"])))
            note["first"] = old["first"] if old else now
            note["seen"] = now
            self.found[room_id] = note
            if len(self.found) > MOST_ROOMS:
                for stale in sorted(self.found, key = lambda r: self.found[r]["seen"])[:len(self.found) - MOST_ROOMS]:
                    del self.found[stale]

    def close(self):
        self.stop.set()


# ---------------------------------------------------------------- Meeting through a code

def door_topic(code, kind):
    """The topic a game's notes go under: named by a hash of its code, so only someone who has
    the code can find them."""
    digest = hashlib.sha256(f"hutaong-door:{code}".encode("utf-8")).hexdigest()[:24]
    return f"{DOORS}/{kind}/{digest}"


def _keystream(key, n):
    out = bytearray()
    block = 0
    while len(out) < n:
        out += hashlib.sha256(key + block.to_bytes(4, "big")).digest()
        block += 1
    return bytes(out[:n])


def seal(code, data):
    """A note only someone with the code can read (the code is the key)."""
    nonce = bytes(random.getrandbits(8) for _ in range(8))
    plain = b"HT" + json.dumps(data, separators = (",", ":")).encode("utf-8")
    key = hashlib.sha256(b"hutaong-seal:" + code.encode("utf-8") + nonce).digest()
    mask = _keystream(key, len(plain))
    return nonce + (int.from_bytes(plain, "big") ^ int.from_bytes(mask, "big")).to_bytes(len(plain), "big")


def unseal(code, blob):
    if len(blob) < 11 or len(blob) > 4096:
        return None
    nonce, body = blob[:8], blob[8:]
    key = hashlib.sha256(b"hutaong-seal:" + code.encode("utf-8") + nonce).digest()
    mask = _keystream(key, len(body))
    plain = (int.from_bytes(body, "big") ^ int.from_bytes(mask, "big")).to_bytes(len(body), "big")
    if not plain.startswith(b"HT"):
        return None
    try:
        data = json.loads(plain[2:].decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def clean_addresses(items):
    """[(ip, port)] from a note's list of addresses, keeping only well-formed IPv4 ones."""
    found = []
    for item in items if isinstance(items, list) else []:
        if not (isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], int)):
            continue
        parts = item[0].split(".")
        if len(parts) == 4 and all(p.isdigit() and int(p) < 256 for p in parts) and 0 < item[1] < 65536:
            if (item[0], item[1]) not in found:
                found.append((item[0], item[1]))
    return found[:6]


class Door:
    """Hosting: a sealed note, under the game's code, of the addresses the host can be reached at,
    kept up to date on every broker that answers; and the knocks of friends who want in, with
    their own addresses, so the host's game can open the way to them too (hole punching)."""

    def __init__(self, code, brokers = None):
        self.code = code
        self.brokers_wanted = list(brokers or active())
        self.note = None
        self.version = 0
        self.knocks = []             # [[(ip, port), ...]] from friends knocking, newest last
        self.states = {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        for broker in self.brokers_wanted:
            self.states[broker] = "connecting"
            threading.Thread(target = self.post, args = (broker,), daemon = True, name = "door").start()

    @property
    def status(self):
        """connecting, open (the note is up) or failed."""
        return _overall(self.states.values(), "open")

    def update(self, note):
        with self.lock:
            if note != self.note:
                self.note = note
                self.version += 1

    def take_knocks(self):
        with self.lock:
            knocks, self.knocks = self.knocks, []
        return knocks

    def post(self, broker):
        key, (host, port), login = broker, broker[:2], broker[2:4] or None
        topic, knock_topic = door_topic(self.code, "door"), door_topic(self.code, "knock")
        while not self.stop.is_set():
            try:
                broker = Broker(host, port, will = (topic, b""), login = login)
            except LoginRefused:
                self.states[key] = "refused"
                self.stop.wait(RETRY)
                continue
            except OSError:
                self.states[key] = "failed"
                self.stop.wait(RETRY)
                continue
            posted, last = -1, 0.0
            try:
                broker.subscribe(knock_topic)
                self.states[key] = "connected"
                while not self.stop.is_set():
                    with self.lock:
                        note, version = self.note, self.version
                    now = time.time()
                    if note is not None and (version != posted or now - last >= REFRESH):
                        broker.publish(topic, seal(self.code, dict(note, t = round(now))))
                        posted, last = version, now
                        self.states[key] = "open"
                    elif now - last >= 30:
                        broker.ping()
                        last = now
                    for kind, body in broker.packets():
                        if kind == 0x30 and len(body) >= 2:
                            size = struct.unpack_from("!H", body, 0)[0]
                            knock = unseal(self.code, body[2 + size:])
                            if knock and isinstance(knock.get("t"), (int, float)) and abs(time.time() - knock["t"]) < 60:
                                addresses = clean_addresses(knock.get("addrs"))
                                if addresses:
                                    with self.lock:
                                        self.knocks.append(addresses)
                                        del self.knocks[:-8]
                broker.publish(topic, b"")
            except OSError:
                pass
            finally:
                broker.close()
            if not self.stop.is_set():
                self.states[key] = "failed"
                self.stop.wait(RETRY)

    def close(self):
        self.stop.set()


class Knock:
    """Joining with a code: read the host's sealed note for its addresses, and knock, with ours,
    so the host's game can open the way to us."""

    def __init__(self, code, brokers = None):
        self.code = code
        self.brokers_wanted = list(brokers or active())
        self.host = []               # [(ip, port)] the host can be reached at, once its note is read
        self.mine = None             # [(ip, port)] we can be reached at, to knock with
        self.version = None          # the host's game version, from its note
        self.states = {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        for broker in self.brokers_wanted:
            self.states[broker] = "connecting"
            threading.Thread(target = self.look, args = (broker,), daemon = True, name = "knock").start()

    @property
    def status(self):
        """connecting, found (the host's note is read), open (no note yet) or failed."""
        if self.host:
            return "found"
        return _overall(self.states.values(), "open")

    def set_mine(self, addresses):
        with self.lock:
            self.mine = list(addresses)

    def look(self, broker):
        key, (host, port), login = broker, broker[:2], broker[2:4] or None
        topic, knock_topic = door_topic(self.code, "door"), door_topic(self.code, "knock")
        while not self.stop.is_set():
            try:
                broker = Broker(host, port, login = login)
            except LoginRefused:
                self.states[key] = "refused"
                self.stop.wait(RETRY)
                continue
            except OSError:
                self.states[key] = "failed"
                self.stop.wait(RETRY)
                continue
            last_knock, sent = 0.0, None
            try:
                broker.subscribe(topic)
                self.states[key] = "open"
                last_ping = time.time()
                while not self.stop.is_set():
                    for kind, body in broker.packets():
                        if kind == 0x30 and len(body) >= 2:
                            size = struct.unpack_from("!H", body, 0)[0]
                            note = unseal(self.code, body[2 + size:])
                            if note:
                                addresses = clean_addresses(note.get("addrs"))
                                with self.lock:
                                    self.host = addresses
                                    self.version = note.get("v")
                    with self.lock:
                        mine = self.mine
                    now = time.time()
                    if mine and (mine != sent or now - last_knock > 1.5):
                        broker.publish(knock_topic, seal(self.code, {"addrs": [list(a) for a in mine],
                                                                     "t": round(now)}), retain = False)
                        last_knock, sent = now, mine
                    if now - last_ping > 25:
                        last_ping = now
                        broker.ping()
            except OSError:
                pass
            finally:
                broker.close()
            if not self.stop.is_set():
                self.states[key] = "failed"
                self.stop.wait(RETRY)

    def close(self):
        self.stop.set()
