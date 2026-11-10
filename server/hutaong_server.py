#!/usr/bin/env python3
"""Hu Taong server: where online games find each other, on a machine of your own.

Hu Taong's codes and public room list travel as small notes through an MQTT message server.  By
default the game uses free public ones; run this on a server you control and pick it in the game
(Online > Server > Your Own Server) for something steadier.  Matches themselves still go straight
between the two players' computers: this only carries the notes they find each other with.

It is a small MQTT 3.1.1 server that does just what Hu Taong needs (connect with an optional
login, subscribe, publish with retained notes and wills, ping), with limits so strangers can't
make much use of it: only Hu Taong's topics, small notes, and a cap on connections and traffic.
Any other MQTT server (Mosquitto, say) works too; see SERVER.md.

Needs only Python 3.8 or newer.  Run it with:

    python3 hutaong_server.py                         # anyone may connect, on port 1883
    python3 hutaong_server.py --port 1884 --user rowan --password "something long"

and open that TCP port in the server's firewall.
"""
import argparse, asyncio, hmac, logging, struct, time

TOPIC_PREFIX = "hutaong/"     # the only topics carried, unless --any-topic
MOST_PACKET = 16 * 1024       # bytes: Hu Taong's notes are a few hundred
MOST_RETAINED = 20000         # notes kept for newcomers
MOST_SUBSCRIPTIONS = 32       # per connection
RATE = 40                     # packets a second a connection may send on average...
BURST = 200                   # ...and at most at once

log = logging.getLogger("hutaong-server")


def matches(pattern, topic):
    """Does an MQTT subscription pattern (with + and #) cover a topic?"""
    p, t = pattern.split("/"), topic.split("/")
    for i, part in enumerate(p):
        if part == "#":
            return True
        if i >= len(t) or (part != "+" and part != t[i]):
            return False
    return len(p) == len(t)


def encode_length(n):
    out = bytearray()
    while True:
        byte, n = n % 128, n // 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def publish_packet(topic, payload, retain = False):
    t = topic.encode("utf-8")
    body = struct.pack("!H", len(t)) + t + payload
    return bytes([0x30 | (1 if retain else 0)]) + encode_length(len(body)) + body


class Reader:
    """Pulls fields out of a packet body, raising ValueError when it runs short."""

    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n):
        if self.pos + n > len(self.data):
            raise ValueError("packet too short")
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack("!H", self.take(2))[0]

    def blob(self):
        return self.take(self.u16())

    def text(self):
        return self.blob().decode("utf-8")

    def rest(self):
        return self.data[self.pos:]


class Server:
    def __init__(self, args):
        self.args = args
        self.clients = set()
        self.retained = {}           # topic -> payload

    def allowed(self, topic):
        if len(topic) > 200 or "\0" in topic:
            return False
        return self.args.any_topic or topic.startswith(TOPIC_PREFIX)

    async def deliver(self, topic, payload, retain, sender = None):
        if retain:
            if payload:
                if topic in self.retained or len(self.retained) < MOST_RETAINED:
                    self.retained[topic] = payload
            else:
                self.retained.pop(topic, None)
        packet = publish_packet(topic, payload)
        for client in list(self.clients):
            if client.wants(topic):
                client.send(packet)

    async def handle(self, reader, writer):
        if len(self.clients) >= self.args.max_clients:
            writer.close()
            return
        client = Client(self, reader, writer)
        self.clients.add(client)
        try:
            await client.run()
        finally:
            self.clients.discard(client)
            await client.finish()

    async def report(self):
        while True:
            await asyncio.sleep(600)
            log.info("%d connected, %d notes kept", len(self.clients), len(self.retained))


class Client:
    def __init__(self, server, reader, writer):
        self.server, self.reader, self.writer = server, reader, writer
        self.peer = writer.get_extra_info("peername")
        self.subscriptions = []
        self.will = None
        self.said_goodbye = False
        self.keepalive = 60
        self.tokens, self.last = float(BURST), time.monotonic()

    def wants(self, topic):
        return any(matches(p, topic) for p in self.subscriptions)

    def send(self, data):
        if self.writer.is_closing():
            return
        if self.writer.transport.get_write_buffer_size() > 256 * 1024:
            self.writer.close()                     # not reading what it's sent: let it go
            return
        self.writer.write(data)

    async def packet(self, timeout):
        header = (await asyncio.wait_for(self.reader.readexactly(1), timeout))[0]
        n, shift = 0, 0
        while True:
            byte = (await asyncio.wait_for(self.reader.readexactly(1), timeout))[0]
            n |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
            if shift > 21:
                raise ValueError("garbled length")
        if n > MOST_PACKET:
            raise ValueError("packet too big")
        body = await asyncio.wait_for(self.reader.readexactly(n), timeout) if n else b""
        return header, body

    def within_rate(self):
        now = time.monotonic()
        self.tokens = min(BURST, self.tokens + (now - self.last) * RATE)
        self.last = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True

    async def run(self):
        try:
            header, body = await self.packet(10)
            if header & 0xF0 != 0x10 or not self.connect(Reader(body)):
                return
            while True:
                header, body = await self.packet(self.keepalive * 1.5 if self.keepalive else None)
                if header & 0xF0 == 0x30 and not self.within_rate():
                    continue                        # posting more than its share: dropped
                if not await self.handle(header, body):
                    return
                await self.writer.drain()
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError, ValueError, UnicodeDecodeError):
            return

    def connect(self, r):
        name, level, flags = r.text(), r.u8(), r.u8()
        self.keepalive = r.u16()
        if name not in ("MQTT", "MQIsdp") or level not in (3, 4):
            self.send(bytes([0x20, 2, 0, 1]))       # unacceptable protocol version
            return False
        r.text()                                    # the client's name: not needed
        if flags & 0x04:
            topic, message = r.text(), r.blob()
            if self.server.allowed(topic):
                self.will = (topic, message, bool(flags & 0x20))
        user = r.text() if flags & 0x80 else ""
        password = r.blob() if flags & 0x40 else b""
        args = self.server.args
        if args.user is not None:
            good = (hmac.compare_digest(user.encode("utf-8"), args.user.encode("utf-8")) and
                    hmac.compare_digest(password, (args.password or "").encode("utf-8")))
            if not good:
                self.send(bytes([0x20, 2, 0, 4]))   # bad username or password
                log.info("login turned away from %s", self.peer[0] if self.peer else "?")
                return False
        self.send(bytes([0x20, 2, 0, 0]))
        return True

    async def handle(self, header, body):
        kind = header & 0xF0
        if kind == 0x30:                            # PUBLISH
            qos = (header >> 1) & 3
            r = Reader(body)
            topic = r.text()
            if qos:
                packet_id = r.u16()
                if qos == 1:
                    self.send(bytes([0x40, 2]) + struct.pack("!H", packet_id))
            payload = r.rest()
            if self.server.allowed(topic) and "+" not in topic and "#" not in topic:
                await self.server.deliver(topic, payload, bool(header & 1))
        elif kind == 0x80:                          # SUBSCRIBE
            r = Reader(body)
            packet_id = r.u16()
            codes, new = bytearray(), []
            while r.pos < len(body):
                pattern, _ = r.text(), r.u8()
                if self.server.allowed(pattern.replace("#", "x").replace("+", "x")) and \
                        len(self.subscriptions) + len(new) < MOST_SUBSCRIPTIONS:
                    new.append(pattern)
                    codes.append(0)
                else:
                    codes.append(0x80)              # refused
            self.subscriptions += new
            self.send(bytes([0x90]) + encode_length(2 + len(codes)) + struct.pack("!H", packet_id) + bytes(codes))
            for topic, payload in list(self.server.retained.items()):
                if any(matches(p, topic) for p in new):
                    self.send(publish_packet(topic, payload, retain = True))
        elif kind == 0xA0:                          # UNSUBSCRIBE
            r = Reader(body)
            packet_id = r.u16()
            while r.pos < len(body):
                pattern = r.text()
                if pattern in self.subscriptions:
                    self.subscriptions.remove(pattern)
            self.send(bytes([0xB0, 2]) + struct.pack("!H", packet_id))
        elif kind == 0xC0:                          # PINGREQ
            self.send(bytes([0xD0, 0]))
        elif kind == 0xE0:                          # DISCONNECT
            self.said_goodbye = True
            return False
        return True

    async def finish(self):
        if self.will and not self.said_goodbye:     # gone without a goodbye: post its will
            await self.server.deliver(*self.will)
        try:
            self.writer.close()
        except Exception:
            pass


async def main(args):
    server = Server(args)
    listener = await asyncio.start_server(server.handle, args.host, args.port)
    login = "with a login" if args.user is not None else "open to anyone (no login)"
    log.info("Hu Taong server on port %d, %s. Stop it with Ctrl+C.", args.port, login)
    asyncio.ensure_future(server.report())
    async with listener:
        await listener.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Where Hu Taong games find each other (a small MQTT server).")
    parser.add_argument("--port", type = int, default = 1883, help = "TCP port to listen on (default 1883)")
    parser.add_argument("--host", default = "0.0.0.0", help = "address to listen on (default: all)")
    parser.add_argument("--user", help = "username players must log in with (default: no login)")
    parser.add_argument("--password", help = "password players must log in with")
    parser.add_argument("--max-clients", type = int, default = 500, help = "most connections at once (default 500)")
    parser.add_argument("--any-topic", action = "store_true", help = "carry any topic, not just Hu Taong's")
    args = parser.parse_args()
    if args.password is not None and args.user is None:
        parser.error("--password needs --user too")
    logging.basicConfig(level = logging.INFO, format = "%(asctime)s %(message)s")
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        pass
