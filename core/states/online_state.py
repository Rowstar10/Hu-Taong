"""The online lobby: host a game (by code, or listed publicly for anyone to find), join a friend's
game with its code, or browse the public rooms and join one, with its password if it has one.
Server picks what games find each other through: the free public servers, or your own."""
import threading

import pygame

from core import files, rooms, save_data
from core import net as netcode
from core.states.base_state import State

CODE_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.:- ")
FIELDS = {"code": 24, "join_password": 24, "room_name": 28, "password": 24, "room_password": 24,
          "server_address": 80, "server_user": 40, "server_password": 40}     # field -> most characters
SERVER_FIELDS = ("server_address", "server_user", "server_password")


class OnlineState(State):
    NAME = "online"
    is_menu = True
    ROOMS_SHOWN = 6

    def __init__(self, app, resume = None):
        super().__init__(app)
        self.mode = "choose"         # choose, host, join, browse, server
        self.text = {name: "" for name in FIELDS}
        self.text["room_name"] = "Hu Taong room"
        online = app.settings.online
        for name in SERVER_FIELDS:
            self.text[name] = getattr(online, name)
        self.server_check = ""       # what the last Test found
        net = app.net
        if resume and net:
            # back from a match with the friend still connected (Lobby, on the pause or result screen)
            self.mode = "host" if net.role == "host" else "join"
            if net.role == "host":
                self.text["room_name"] = net.room_name or self.text["room_name"]
                self.text["password"] = net.password
        self.focus = None            # the text box being typed into
        self.message = ""
        self.starting = False        # on the way into the match, so the session stays open
        self.room_list = None        # while browsing: core.rooms.RoomList
        self.shown_rooms = []        # the rooms on screen, in order
        self.picked = None           # the room chosen to join, while its password is asked for
        self.trying = None           # the room being joined from the list

    @property
    def code(self):
        return self.text["code"]

    @code.setter
    def code(self, value):
        self.text["code"] = value

    def set_mode(self, mode):
        self.mode = mode
        self._laid = None            # lay the screen out afresh for this step
        self.message = ""
        self.picked = None
        self.focus = {"join": "code"}.get(mode)
        if mode == "server":
            self.server_check = ""
            self.focus = "server_address" if self.app.settings.online.own_server else None
        if mode == "browse" and self.room_list is None:
            self.room_list = rooms.RoomList()
        if mode != "browse" and self.room_list is not None:
            self.room_list.close()
            self.room_list = None

    def exit(self, **kwargs):
        super().exit(**kwargs)
        if self.room_list is not None:
            self.room_list.close()
            self.room_list = None
        # Leaving the lobby for anywhere but the match ends whatever was set up
        if not self.starting:
            self.app.leave_online()

    # ---------------- Hosting ----------------

    def host(self):
        self.app.leave_online()
        try:
            self.app.net = netcode.HostSession(self.app, netcode.PORT)
        except OSError:
            try:
                self.app.net = netcode.HostSession(self.app, 0)       # the usual port is taken: any will do
            except OSError as e:
                self.message = f"Couldn't open a port to host on: {e.strerror or e}"
                return
        self.set_mode("host")
        self.sync_room()

    def sync_room(self):
        """The room's name and password, as typed, onto the session."""
        net = self.app.net
        if net and net.role == "host":
            net.room_name = self.text["room_name"].strip()
            net.password = self.text["password"]

    def toggle_public(self):
        net = self.app.net
        if net and net.role == "host":
            net.set_public(net.ad is None)

    def start_match(self):
        net = self.app.net
        if not (net and net.role == "host" and net.connected()):
            return
        self.app.fx.swarm()
        self.starting = True
        self.set_state("game", mute = True)

    def copy_code(self):
        net = self.app.net
        text = (net.code() or f"{net.lan}:{net.port}") if net else ""
        if text and files.copy_text(text):
            self.app.renderer.show_toast(f"Copied {text}: send it to your friend")
        elif text:
            self.app.renderer.show_toast("Couldn't reach the clipboard: read the code out instead")

    # ---------------- Joining ----------------

    def join(self, code = None, password = None):
        if password is None:
            password = self.text["join_password"] if self.mode == "join" else ""
        text = code if code is not None else self.code
        room = netcode.read_room_code(text)
        address = None if room else netcode.read_code(text)
        if room is None and address is None:
            self.message = "That doesn't look like a code. It's 8 letters and numbers, like K7Q2-9FHD."
            return
        self.app.leave_online()
        try:
            self.app.net = netcode.GuestSession(self.app, address, password, room = room)
        except OSError as e:
            self.message = f"Couldn't connect: {e.strerror or e}"
            return
        self.message = ""

    def join_room(self, room):
        """Join a public room; one with a password asks for it first."""
        if room.get("v") != netcode.PROTOCOL:
            self.message = "That room is on a different version of Hu Taong."
            return
        if room.get("players", 1) >= 2:
            self.message = "That room is full."
            return
        if room.get("playing"):
            self.message = "That room is in the middle of a match."
            return
        chosen = self.picked is not None and self.picked.get("id") == room.get("id")
        if room.get("locked") and not chosen:
            self.picked = room
            self.focus = "room_password"
            self.text["room_password"] = ""
            self._laid = None
            return
        self.trying = room
        self.join(room["code"], self.text["room_password"] if chosen else "")

    # ---------------- Server ----------------

    def sync_server(self):
        """The server boxes, as typed, into the settings, and used from now on."""
        online = self.app.settings.online
        for name in SERVER_FIELDS:
            setattr(online, name, self.text[name].strip())
        online.apply()
        self.server_check = ""

    def pick_server(self, own):
        online = self.app.settings.online
        online.own_server = own
        self.focus = "server_address" if own else None
        self.sync_server()
        self._laid = None
        if own and not online.server_address:
            self.server_check = "Type your server's address, then Test."

    def test_server(self):
        online = self.app.settings.online
        if not online.server_address:
            self.server_check = "Type your server's address first."
            return
        self.server_check = "Connecting..."
        address, user, password = online.server_address, online.server_user, online.server_password

        def run():
            result, detail = rooms.check_server(address, user, password)
            if (address, user, password) == (online.server_address, online.server_user, online.server_password):
                self.server_check = ("Works! " if result == "ok" else "") + detail
        threading.Thread(target = run, daemon = True, name = "server-test").start()

    def leave_server(self):
        self.sync_server()
        save_data.save(self.app)
        self.set_mode("choose")

    def server_line(self):
        online = self.app.settings.online
        if online.own_server and rooms.OWN:
            return f"Server: your own ({rooms.OWN[0]})"
        if online.own_server:
            return "Server: your own (no address yet)"
        return "Server: the free public servers"

    def paste(self):
        text = files.paste_text()
        if text:
            self.code = "".join(c for c in text.strip() if c in CODE_CHARS)[:FIELDS["code"]]

    def update(self, dt):
        net = self.app.net
        if self.mode in ("join", "browse") and net and net.role == "guest":
            if net.status == "playing":
                self.starting = True
                self.set_state("guest_match", mute = True)
            elif net.status in ("lost", "refused"):
                self.message = net.reason
                if net.status == "refused" and net.needs_password:
                    # ask for it (again): the box empties and waits for typing
                    if self.mode == "join":
                        self.text["join_password"] = ""
                        self.focus = "join_password"
                    elif self.trying is not None:
                        self.picked = self.trying
                        self.text["room_password"] = ""
                        self.focus = "room_password"
                    self._laid = None
                self.app.leave_online()
        if self.mode == "host" and net and net.notice:
            self.app.renderer.show_toast(net.notice, important = True)
            net.notice = None
        if self.mode == "browse" and self.room_list is not None:
            found = self.room_list.rooms()[:self.ROOMS_SHOWN]
            signature = lambda rs: [(r["id"], r.get("players"), r.get("playing"), r.get("name"), r.get("rules"),
                                    r.get("locked")) for r in rs]
            if signature(found) != signature(self.shown_rooms):
                self.shown_rooms = found
                self._laid = None

    # ---------------- Events ----------------

    def type_into(self, text):
        name = self.focus
        if name is None or not text:
            return
        if name == "code":
            text = "".join(c for c in text if c in CODE_CHARS)
        else:
            text = "".join(c for c in text if c.isprintable())
        self.text[name] = (self.text[name] + text)[:FIELDS[name]]
        self.sync_room()
        if name in SERVER_FIELDS:
            self.sync_server()

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.TEXTINPUT:
            self.type_into(event.text)
        elif event.type == pygame.KEYDOWN and self.focus:
            if event.key == pygame.K_BACKSPACE:
                self.text[self.focus] = self.text[self.focus][:-1]
                self.sync_room()
                if self.focus in SERVER_FIELDS:
                    self.sync_server()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.focus in ("code", "join_password"):
                    self.join()
                elif self.focus in SERVER_FIELDS:
                    self.test_server()
                elif self.focus == "room_password" and self.picked is not None:
                    self.join_room(self.picked)
            elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                if self.focus == "code":
                    self.paste()
                else:
                    self.type_into(files.paste_text())
            elif event.key == pygame.K_TAB and self.mode == "host":
                self.focus = "password" if self.focus == "room_name" else "room_name"
            elif event.key == pygame.K_TAB and self.mode == "join":
                self.focus = "join_password" if self.focus == "code" else "code"
            elif event.key == pygame.K_TAB and self.mode == "server" and self.focus in SERVER_FIELDS:
                self.focus = SERVER_FIELDS[(SERVER_FIELDS.index(self.focus) + 1) % len(SERVER_FIELDS)]

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            if key and key.endswith("_field") and key[:-len("_field")] in FIELDS:
                self.focus = key[:-len("_field")]
                return
            if key and key.startswith("join_room_"):
                index = int(key[len("join_room_"):])
                if index < len(self.shown_rooms):
                    self.join_room(self.shown_rooms[index])
                return
            if key == "host_game":
                self.host()
            elif key == "join_game":
                self.set_mode("join")
            elif key == "find_rooms":
                self.set_mode("browse")
            elif key == "change_server":
                self.set_mode("server")
            elif key == "server_public":
                self.pick_server(False)
            elif key == "server_own":
                self.pick_server(True)
            elif key == "server_test":
                self.test_server()
            elif key == "server_done":
                self.leave_server()
            elif key == "start_online":
                self.start_match()
            elif key == "copy_code":
                self.copy_code()
            elif key == "toggle_public":
                self.toggle_public()
            elif key == "online_settings":
                self.push_state("gameplay")
            elif key in ("cycle_court_left", "cycle_court_right"):
                g = self.app.settings.gameplay
                g.court = (g.court + (1 if key.endswith("right") else -1)) % len(g.court_options)
            elif key == "host_red":
                self.app.settings.gameplay.online_host_blue = False
            elif key == "host_blue":
                self.app.settings.gameplay.online_host_blue = True
            elif key == "paste_code":
                self.paste()
            elif key == "join_now":
                self.join()
            elif key == "join_picked" and self.picked is not None:
                self.join_room(self.picked)
            elif key in ("back", "cancel_online"):
                self.back()

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_online_lobby(self, screen)

    def back(self):
        if self.mode == "server":
            self.leave_server()
        elif self.mode == "choose":
            self.pop_state()
        else:
            self.app.leave_online()
            self.set_mode("choose")
