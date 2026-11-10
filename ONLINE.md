# Playing Hu Taong online

You and your friend both need this same version of the game. Play → Online gives three choices.

## Host a Game

1. Pick **Host a Game**.
2. Choose the **Court**, and whether **You play** Red (left) or Blue (right). Your friend gets
   the other side. The rest of the rules come from **Gameplay Settings**.
3. Let people in, either way:
   - **Send your friend the code** shown, eight letters and numbers like `K7Q2-9FHD` (the
     **Copy** button puts it on the clipboard), or
   - turn on **Public Room** so anyone with Hu Taong can find the game under **Find a Room**.
     Give it a name if you like.
4. A **Password** is optional. If you set one, anyone joining, by code or from the list, has to
   type it.
5. When the screen says your friend is here, press **Start Match**.

## Join with a Code

Type or paste your friend's code (Ctrl+V works; capitals and the dash don't matter), add the
password if they set one, and press **Join**. If you leave the password out, the game tells you it
needs one. On the same Wi-Fi you can also type the host's local address, like `192.168.1.5:47620`.

## Find a Room

This lists the public rooms people are hosting right now. Press **Join** on one. A room marked
"(password)" asks for its password first. Full rooms, rooms mid-match and rooms on a different
version of the game can't be joined.

## Server: free public, or your own

Codes and the room list go through a message server. Under **Server: Change** on the Online
screen you can pick:

- **Free Public Servers** (the default): nothing to set up, but they promise nothing.
- **Your Own Server**: one you or a friend runs (see SERVER.md for how). Type its address
  (like `example.com` or `203.0.113.7:1883`), plus a username and password if it asks for one,
  and press **Test**.

You and your friend need the same server to find each other. If your own server is ever down, the
host screen says so: switch back to Free Public Servers on the same screen (both of you). Your
server's address stays filled in for when it's back. The login is kept in your save file.

## During the match

- Either of you can pause (Esc); it pauses for both, and the match waits while either of you is
  in a menu. Clicking away from the game (to type to your friend, say) doesn't pause it.
- **Pause screen:** the host has Resume, Reset (serve again), Reset Scores, Replay (the match so
  far), Settings, **Lobby** and Leave Match. The guest has Resume, Restart? (asks the host to start
  again from 0-0), Replay, Settings and Leave Match.
- **After the match:** both get the highlights (if Instant Replays is set to show them), a
  Replay of the whole match, Settings, and the jukebox. The host has Play Again, Endless Mode,
  **Lobby** and Leave; the guest has Rematch? (asks the host) and Leave.
- **Lobby** takes the host back to the lobby with their friend still connected, to change the
  court, sides or rules; the friend's game follows, and Start Match begins the next one.
- Online matches have their own lines on the Stats page.

## How the two games find each other

Hu Taong has no server of its own, so it uses free public services, the same way video calls in
a browser do:

1. Each game asks a public **STUN** server (Google's or Cloudflare's) what internet address it is
   seen from. That server sees your internet address and nothing else.
2. The host posts a short **sealed note** of where it can be reached on free public message
   servers (EMQX and HiveMQ, and Mosquitto where it can be reached). The note is named and locked
   with the game's code, so only someone who has the code can find or read it. A joining friend
   leaves a sealed note of their own address the same way.
3. Both games then send packets to each other at once. Each router sees its own player's packets
   going out to the other and lets the answers in ("hole punching"). The host's game also asks
   its router to open the port (UPnP), and both try the local network; whichever way works, wins.

After that, everything goes straight between your two computers.

**What a public room shares:** its name, rules and code are on the public room list, so anyone
who sees the list can join it (or find its internet address). The **password is never posted**:
the joining game sends a scrambled form of it straight to the host. A room comes off the list when
you stop hosting, close the game, or lose your connection. If you'd rather not be listed, leave
Public Room off and send the code instead.

## If your friend can't connect

- **Firewall:** the first time, Windows may ask whether Hu Taong can use the network. Allow it.
- **Swap who hosts.** Some routers (often on mobile hotspots, or at work and school) change the
  port for every connection, so packets can't find their way in. The host screen warns about this
  when it can tell. It usually only needs one of you to have a friendly router, and the host's
  router matters most.
- **Same Wi-Fi:** the friend can type the host's local address shown on the host screen.
- **Router:** forward **UDP port 47620** on the host's router to the host's PC; then the address
  shown as "Internet" works from anywhere.
- **A free VPN:** both install Tailscale or ZeroTier and join the same network, then the friend
  types the host's VPN address (like `100.101.102.103`).

The game uses UDP port 47620 when it's free; the host screen shows the port in use. Codes and the
room list use TCP port 1883 to reach the message servers; some school or work networks block it,
and then the host screen says the code couldn't be set up. Addresses still work there.
