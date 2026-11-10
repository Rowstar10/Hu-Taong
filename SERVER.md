# Running a Hu Taong server

Hu Taong's codes and public room list travel as small notes through a message server (MQTT).
By default the game uses free public ones, which promise nothing. If you have a server of your
own, you can run one there and everyone who picks it in the game finds each other through it.

Matches still go straight between the two players' computers, so the server only carries a few
small notes per game. Any small Linux or Windows server will do.

## The quick way: hutaong_server.py

`server/hutaong_server.py` is a small server that does just what Hu Taong needs. It only needs
Python 3.8 or newer (most Linux servers have it already: try `python3 --version`).

1. Copy `hutaong_server.py` onto the server.
2. Start it:

   ```
   python3 hutaong_server.py
   ```

   It listens on TCP port **1883**. To pick another port, or to make players log in:

   ```
   python3 hutaong_server.py --port 1884 --user hutao --password "a long password"
   ```

3. Open that TCP port in the server's firewall (and in the hosting company's control panel, if
   it has its own firewall). On Ubuntu, for example: `sudo ufw allow 1883/tcp`.
4. In Hu Taong: **Play → Online → Server: Change → Your Own Server**, type the server's address
   (like `example.com` or `203.0.113.7:1884`), plus the username and password if you set them,
   and press **Test**.

Everyone who wants to find each other has to pick the same server. If it's ever down, switch back
to **Free Public Servers** on the same screen (all of you).

### Keeping it running

To keep it running after you log out, and start it again after a restart, on a Linux server with
systemd, save this as `/etc/systemd/system/hutaong.service` (change the path and user):

```
[Unit]
Description=Hu Taong server
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/youruser/hutaong_server.py --port 1883
Restart=always
User=youruser

[Install]
WantedBy=multi-user.target
```

then run `sudo systemctl enable --now hutaong`. `sudo systemctl status hutaong` shows how it's doing.

### What it lets through

Only Hu Taong's notes (topics starting `hutaong/`), each at most 16 KB, from at most 500
connections at once, each posting at most 40 a second. That keeps strangers from using it for
anything else. A login (`--user` and `--password`) keeps them out altogether, but then every
player needs the login too.

## Or: any MQTT server

Hu Taong speaks plain MQTT 3.1.1, so an existing broker such as Mosquitto works as well. A
minimal Mosquitto setup (`/etc/mosquitto/conf.d/hutaong.conf`):

```
listener 1883
allow_anonymous true
```

or, with a login, `allow_anonymous false` and `password_file /etc/mosquitto/passwd` (made with
`mosquitto_passwd -c /etc/mosquitto/passwd hutao`).

Hu Taong doesn't use encrypted (TLS) connections, so a hosted MQTT service that only allows those
(port 8883) won't work. A game's code notes are sealed with its code anyway, public room listings
are public by design, and room passwords are never sent, only a scrambled form of them.
