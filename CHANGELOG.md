# Changelog

Every version of Hu Taong, newest first. Toki Hub shows each version's section on that version's page.

## 1.8 — 2026-11-18

Three physics to choose from, a Speed Cap so a charge shot can always be reached, the Black Hole talisman and game mode, and a review of the talismans.

### Added
- Physics, in Match settings under Ball & Paddles (online, the host's choice counts). Changes come in at the next serve:
  - Current: as in 1.7. A hit's speed comes from how hard the paddle drives into the ball, easing off towards a top speed.
  - Classic: the angle comes from where the ball meets the paddle, and every hit of a rally is a little faster, up to the usual top speed. Moving the paddle adds no speed.
  - v0.9: Hu Taong 0.9's. Drive into the ball to speed it up, a still paddle slows it, off an end the ball goes mostly up or down, and there's no top speed. Only two things are added, so a point can't freeze: it never slows below a quarter of the serve's speed, and never goes quite straight up and down.
- Speed Cap, in the same place: a paddle hands on its speed to the ball only up to a limit (a little under the usual paddle speed), and gives way rather than catching its own ball again. Tapping the ball softly, running after it and hitting it again by the Middle Wall no longer makes a shot nobody could reach. Classic physics never hands on a paddle's speed, so it makes no difference there.
- Match settings shows the physics and the Speed Cap under Ball & Paddles.
- Black Hole, a new Wild talisman. A black hole opens mid-court until the point ends, and drifts about the middle third of the court, away from the goals. Its gravity pulls the ball in, harder the closer it comes: the ball speeds up as it falls towards it and spirals in, and a near miss is whipped round it. The paddles feel nothing. A ball that falls in is held for a moment while the heart pulses, then flung out as fast as it went in, still heading for the same side but at a new angle. At the point's end it implodes.
- The Black Hole grows: each ball it swallows makes it bigger and its pull stronger, up to twice its size. The sixth ball it swallows makes it collapse in on itself, and the ball bursts out as Twin Balls, each heading for the goal it can score in. (With two balls in play already, the ball comes out alone, heading for the goal it can score in.) Then mini black holes drift about the middle of the court until the point ends, each pulling the ball in and flinging it on towards the side it was heading for.
- Black holes have sounds: a low hum while one is on the court, louder as the Black Hole grows; a deep whoomp as one swallows a ball; and a roar as the Black Hole collapses, ending in a boom as it bursts. You hear them on your friend's screen online and in replays too.
- Black Hole game mode, in place of Portal Pair: a black hole all match, growing point after point. Once it collapses, mini black holes come and go until the point ends, and a new one opens at the next serve. The Black Hole talisman doesn't turn up. If you had Portal Pair on, Black Hole is on instead, and 1.7 still sees Portal Pair on.
- Talismans at Once, in Match settings beside Spawn: how many talismans can be in play at once, counting those waiting on the court. It can be 1, 2 or 3, and starts at 1. Safety Teleport, Double or Nothing, Lantern Night and Open Court don't count, and Talisman Rush lifts the limit. Before, up to two could wait on the court, or three on Chaotic.

### Changed
- The Trickster AI doesn't try its pounce (that same charge shot) under Classic physics or with the Speed Cap, where it can't work.
- Talismans waiting on the court stay for 20 seconds of play, through points. They went after 14 seconds, and at every point.
- Lantern Night lasts 20 seconds of play and stays dark between points until dawn comes. It used to end with the point.
- Soul Swap ends with the point: everyone is back on their own paddle for the next serve. In a Switch match, the switching carries on from where it left you.
- Tombstone: every hit wears it down. Three hits break it, two blazing ones or one from the Snowball. Once the Snowball has grown big, it ploughs straight through one in a burst of frost and stone, keeping most of its speed. The court's own stones are unchanged.
- Portal Pair: each portal is an oval instead of a ring with arrows, with a dotted line along the way the ball will come out, which lights up just before it does. One portal faces each way, and each sweeps slowly up and down instead of turning right round, so its way out never jumps from steeply up to steeply down. They no longer grow: they keep the size they open at, and they keep to the middle third of the court, away from the goals. A ball spends half a second inside while the way out lights up, and comes out a little slower each time, though never slower than a serve.
- Choose Talismans is under the Power-Ups switch in Match settings. The Choose Talismans screen no longer repeats the Power-Ups switch and the spawn rate.
- Spirit Fire: blazing shots are 20% faster, not 40%, and never go past the usual top speed.
- Shrink Curse: the paddle shrinks by a fifth, not a third.
- Sticky Goo: the ball comes off a little slower. Its aim locks half a second before it's slung, so a last-moment fake no longer changes where it goes, and the arrow holds steady once it's locked.
- Talismans with a big effect on the court fade out when they end, instead of cutting straight back to normal: night lifts into dawn, the wind dies down, a Ghost Ball fades back into sight, portals shrink away, Shape Shift's sizes ease back, Sticky Goo's coat fades off and Open Court's wall fades back in.
- Talisman Rush brings as many talismans at once as come (it was up to three).
- Online play needs both players on 1.8: it won't connect to 1.7 or earlier.

### Removed
- The Portal Pair game mode: it's the Black Hole mode now. The Portal Pair talisman stays, and can turn up in a Black Hole match.

## 1.7 — 2026-11-17

Game modes you can mix on Match Setup, a reworked Switch, match settings from the pause menu, tidier settings menus, and drifting portals.

### Added
- Game modes, picked on Match Setup and in Match settings, any of them together. Chaos and Switch each have one button that steps through Off and their versions:
  - Chaos, Every point: new random sizes and speeds for the ball and paddles each point, fixed through the rally.
  - Chaos, Constant drift: the ball's and paddles' sizes keep drifting all match, both paddles together, as with Shape Shift. Speeds stay put.
  - Switch, Every point (after each point you take over the other paddle as it is, colour and all) or Mid-rally (at random moments both paddles glow, and the next hit switches; each player keeps their colour).
  - Curveball and Lantern Night, for the whole match.
  - Twin Ball: every point is played with two balls, Red's and Blue's, under the Twin Balls rules.
  - Talisman Rush: talismans turn up three times as often, up to three at once, even with Power-Ups off.
  - Portal Pair: the Portal Pair talisman's portals, all match. They open small and grow a little each time a ball goes through, and keep their size from point to point, up to the full size.
- Change the rules mid-match from Pause > Settings > Match. Changes come in at the next serve. Online only the host has Match settings: the host's rules are the match's.
- A Match Settings button on Match Setup.
- Hosting online has the game modes too, as on Match Setup, and its Match Settings button (it said Gameplay Settings) opens the rules. The line of rules your friend sees, and the public room list, name Chaos's and Switch's versions.

### Changed
- Settings is now five menus. Match holds the rules, the same for both players: modes, points to win, the court, talismans, the ball and paddles, the AI and the serve countdown. The rest are your own: Gameplay (your keys and Auto-Pause), Display (now with Effects, Screen Shake and Ball Trail), Audio and UI (tooltips, the HUD, AI banter and replays; it was called Interface). The ball's and paddles' sizes and speeds have a screen of their own, under Match.
- A Switch always works one way now: you take over the other paddle, and the goal it defends. Your keys and your score stay yours, and the paddles stay where they are. Mid-rally switches no longer swap the paddles' places or slow the ball to half speed, and none of it needs the Middle Wall down any more.
- Mid-rally switches go off at a hit: both paddles glow, each saying who takes it over, and the next hit switches. A ball you let through is always your point lost (with a switch on a timer, you could leave a ball for it to go in just after the switch, into what was then the other player's goal). Each player keeps their colour, too: the paddles, the scores and the goals change colour with them.
- Soul Swap: until the point ends, you and your opponent keep taking over each other's paddle, at a hit once they glow, each keeping your colour. It no longer takes the Middle Wall down.
- Chaos Mode + is now Chaos with Constant drift, and changes sizes only: speeds no longer drift mid-rally.
- Chaos's every-point sizes and speeds no longer touch your own ball and paddle settings.
- Settings changed mid-match come in at the next serve, never mid-rally.
- Portal Pair: the portals drift slowly about the court and their arrows slowly turn, and they grow a little each time a ball goes through. A ball never leaves one steeper than before.
- Pause has fewer buttons: Reset opens to show Reset Point (serve again, scores kept; it was Reset) and Reset Match (start again from 0-0; it was Reset Scores).
- Replay is called View Replay, and after a match the highlights are in there, under a Highlights button, instead of on a button of their own.
- The volume sliders' Mute buttons are speaker icons now, to the left of the sliders.
- In Match settings, the lines saying how many talismans are on and how big and fast the ball and paddles are sit under their buttons.
- Your Chaos Mode, Chaos Switch, Curveball and Lantern Night settings carry over as the matching modes (Chaos Switch & + becomes Switch, Mid-rally), and 1.6 still reads the settings 1.7 saves.
- Online play needs both players on 1.7: it won't connect to 1.6 or earlier, and their rooms show "Other version".

### Fixed
- Portal Pair: the talisman always opens its portals now. On a court with stones it sometimes opened none, and was used up for nothing.

## 1.6 — 2026-11-12

Power-up fixes and changes, from a review of every power-up, then two rounds of changes from playtesting it.

### Fixed
- With the Middle Wall down, a ball caught between the two paddles, or between a paddle and a stone, no longer rattles on the spot hundreds of times a second. It squirts out past the paddles' ends.
- Snowball: holding the key towards your own goal no longer stops a shove from counting. While a paddle reels from the hit, a shove that carries it into its own goal gives away the point whatever key is held. Steering into your own goal yourself, unshoved, still gives nothing away.
- Portal Pair: a ball can no longer loop between the portals for ever. After three trips through them with no paddle touching a ball, the portals close.
- Safety Teleport under Twin Balls: the save now guards against the ball that can score on you. Red's save watched the red ball, which can't score on Red.
- Sticky Goo with the Middle Wall down: a paddle can only hold the ball in its own half. Carried over the halfway line, or caught in the other half, the ball is slung there and then. Before, it could be carried right up to the other goal.
- Double or Nothing now says "This point is worth 2". It said "the next point", but it has always doubled the point being played.
- Online, the joining player's Safety Teleport is judged on their own screen, as their saves are. The host judged it from its slightly late copy of their paddle, so it fired on saves they were already making.
- Online and in replays, the scored message says "x2" when Double or Nothing made the point worth 2. The joining player saw their score jump by 2 without being told why.
- Sticky Goo on a big Snowball: a ball caught on the end of a paddle is held where it touched. It was dragged onto the paddle, jumping as much as 70 px in an instant.

### Changed
- The wait for the next talisman carries on from point to point. It restarted at every point, so quick points, attacking play and games without the Middle Wall hardly saw any.
- Ghost Ball, Wind Gust and Sticky Goo end when the point ends, so the next serve is a plain one. Your own Boons and Curses still carry on until their time runs out.
- Safety Teleport: an unused save is lost when the point ends. It could be saved up for the rest of the match, which made it the strongest Boon.
- Swift Step: your paddle still moves half as fast again, but its hits are no harder than usual. A faster paddle hit much harder, and that was most of its edge.
- Spirit Fire: blazing shots are still 40% faster, but go at most 10% past the usual top speed. They reached about 4,450 px/s, too fast to follow.
- Ghost Ball is always in sight for the last 300 px before the paddle it's heading for.
- Blink Ball doesn't hop within 350 px of the paddle it's heading for.
- Twin Balls never split slower than half a serve. They could crawl at a quarter.
- Wind Gust blows harder: 500 px/s² at the height of a gust, up from 360.
- Firecracker: its fuse is lit as it's taken and burns for 5 seconds, burning down on the ball where everyone can see it, then it bangs. A number over the ball counts it down from 5 to 1, turning red for the last two. It banged after 3 hits. It still goes out without a bang if the point ends first.
- Firecracker: the bang always shoots the ball away from whoever hit it last. It could shoot straight back at them from point-blank.
- Safety Teleport: a waiting save shows on your paddle, with a soft gold glow and its 遁 glyph, so both players can see it.
- Swift Step: a Swift paddle leaves gold after-images as it moves.
- Sticky Goo: the goo sits round the paddle's edges, so your paddle still shows red or blue.
- Snowball: the goal line lights up while a paddle is being shoved back at it.
- Twin Balls: the red ball is properly red, and each goal line flashes the colour of the ball that can score there.
- Double or Nothing: a big x2 beside both scores while the point is worth 2.
- Wind Gust: bolder, busier leaves, and an arrow by its icon showing which way it blows.
- Portal Pair: bigger, brighter exit arrows, and the portals glow at night.
- Clearer descriptions for Soul Swap.
- The Chaos Mode + talisman is now Shape Shift: for the rest of the point the paddles grow and shrink together, always the same size as each other, and the ball grows and shrinks on its own. Their speeds no longer change. If you'd switched it off, it stays off. The Chaos Mode + setting is unchanged.
- The computer player reads where a Sticky Goo ball will be slung, as the aim arrow shows. It expected the ball to leave on its old return, so any flick of the paddle fooled it.
- Lantern Night: the computer player misjudges a ball out in the dark, as it does a Ghost Ball. It used to see perfectly, so only you were handicapped. This applies with Lantern Night on for the whole match, in Settings, too.
- Resuming a match from a pause counts 3-2-1 first, at the same pace as the serve countdown, so nobody is caught out. Online, both screens show it.
- Online, clicking away from the game pauses it for both players, and it only carries on while both of you are in the game. Turn Auto-Pause off if you'd rather your clicking away didn't pause it.
- Court Dim is a slider, like the Dim Overlay's, instead of four steps. Your old setting keeps its darkness.
- Max FPS starts at your screen's refresh rate (or the next step up), instead of 120 whatever the screen. A Max FPS you've already chosen is kept.
- Smoother play: far fewer stutters mid-match. Pictures a match needs are got ready while the game loads and between points instead of the first time they're shown, the next background is got ready before it fades in, the end of a background fade and the start of a change of screen no longer catch, and the first pause no longer freezes for a moment. Nothing looks any different.
- Online play needs both players on 1.6: it won't connect to 1.5 or earlier, and their rooms show "Other version".
- 1.6 was updated after playtesting it. To get the latest, uninstall 1.6 and install it again, both of you: the first 1.6 won't play online with an updated one.

### Added
- Clicking back into the game after Auto-Pause has paused it carries on by itself, after the 3-2-1. A pause you made yourself, or used (opened Settings from, say), stays until you resume.
- A Mute button by each volume slider. The slider keeps its place, so unmuting brings back the same level, and the mute is saved.
- A "Reset Ball & Paddles" button under "Randomise Ball & Paddles", putting the ball's and paddles' sizes and speeds back to their defaults.
- Tests for these fixes, in the tests folder.

### Removed
- The Gravity and Frostbite power-ups. Saves and replays from before still load; in an old replay they simply don't show.

## 1.5 — 2026-11-11

Smoother online play, and hits off the joining player's paddle that look the same on both screens.

### Fixed
- Online, on the screen of the player who joined, the ball no longer stops in mid-air when an update from the host comes late. It flies on for up to a tenth of a second while the next one arrives.
- Online, both games now send 60 updates a second, as they were meant to, and each one carries the frame just worked out. Before, it was about 40 to 50 a second, each a frame old.
- Online, the player who joined sees the court held back only as much as their connection needs: less on a steady link, more on an uneven one (0.03 to 0.1 seconds; it was always 0.05).
- Online, the joining player's own paddle is no longer nudged back while it moves and on again when it stops.
- The host's lobby shows the real ping to your friend. Between two computers it showed 0 ms or a huge number.
- Online, on the host's screen, a save whose word comes late no longer shows the ball going into the friend's paddle and back out through it. The ball waits at the paddle's face until word comes.
- Online, the joining player's returns leave at the speed the host's game plays them, so the ball no longer slips back a moment after they hit it (it did on about 4 in 10 returns, and on nearly every smash). Their returns also can't come out faster than the physics allows any more.
- Online, a quick ball, or any ball after the game stutters, no longer passes straight through the joining player's paddle. Their game now follows the ball's whole path between frames, not just where it ends up.
- Online, a save made as the connection stalls no longer turns into a goal: the host waits up to 0.8 seconds for word of it. A real miss counts as soon as the joining player's game has shown the ball go in, usually sooner than before.
- Online, a save off the paddle's end with the ball pinned against the wall now counts, and a save the host turns down no longer moves the ball back in time.
- Online, right after a lag spike, the joining player's saves are no longer turned down as too early and then taken back.

### Changed
- Online play needs both players on 1.5: it won't connect to 1.4 or earlier, and their rooms show "Other version".
- 1.5 was updated the same day with the hit fixes above. To get them, uninstall 1.5 and install it again, both of you: a copy installed before still plays online with an updated one, but without the fixes.

### Added
- Tests for these online fixes, in the tests folder.
- Android: 1.5 also plays on phones and tablets (Toki Hub for Android installs it). Slide a finger to steer your paddle, two players each get half the screen, menus work by touch, and Back pauses. It plays online with 1.5 on a PC.

## 1.4 — 2026-11-10

Fixes for hits off a paddle's ends, and for a friend leaving an online match.

### Fixed
- A ball hit with the top or bottom end of a moving paddle no longer flies off at up to 3 times serve speed. It keeps the speed it came in at, and the paddle can't run on through it.
- A ball pinned between a paddle's end and the top or bottom wall no longer shoots out along the wall at nearly 4 times serve speed.
- Online, when your friend leaves, you're told they left and get the end-of-match screen, with Replay, Highlights (when there are some), Settings and Main Menu but no Play Again. Before, the pause screen said "Your friend is in the settings..." and wouldn't resume.
- The same happens when the host leaves a guest, or the connection is lost. A match cut short like this doesn't count in your stats.
- A friend leaving after a match has ended no longer leaves Play Again, Endless Mode or Lobby on the result screen.
- The Ball Speed tooltip now says hard hits speed the ball up to about 4.5 times its serve speed. It still said 2.4, the limit before 1.3.

### Added
- Tests for these fixes, in the tests folder. Run them with: python -m unittest discover -s tests -t .

## 1.3 — 2026-11-10

Online play, replays, courts and twelve new power-ups, with an overhaul of settings, assets and the AI.

### Added
- Online play with a friend: one of you hosts and the other joins with an eight-character code, or lists the game as a public room (with an optional password) for others to find. Uses free public servers, or a server of your own (see ONLINE.md and SERVER.md).
- Online matches have a lobby, rematch and restart requests, and pausing for both players.
- Replays: an instant replay after great points, after the match, or both, with slow motion. Save whole matches, clips (Mark In and Mark Out) or highlights, and watch or delete them from Stats.
- Courts: Classic, Twin Stones, Graveyard, Ferry Gates and Narrow Pass, or a different court every match.
- New power-ups: Sticky Goo, Blink Ball, Tombstone, Snowball, Twin Balls, Chaos Mode +, Curveball, Double or Nothing, Wind Gust, Firecracker, Lantern Night and Portal Pair.
- Hold Tab in a match to see every power-up in play.
- Lantern Night and Curveball can also be switched on for a whole match.
- A Chaotic power-up rate, and a Court Dim setting (Off, Light, Medium, Strong).
- Jukebox progress bar: click or drag to jump through a track, plus play and pause.
- Export and import your stats, to keep them or move them to another computer. Stats now count online matches, online win rate and online win streak.

### Changed
- Tooltips now show a title, a short description and tips, including keyboard shortcuts.
- Hard hits can speed the ball up to 4.5 times its serve speed (was 2.4), so you can out-hit the AI again.
- Spirit Fire now lasts 10 seconds, with every hit a blazing shot.
- Frostbite's frost now passes back and forth with every hit.
- Ghost Ball is now a Wild power-up: the ball keeps vanishing and reappearing at random.
- Gravity now makes both paddles fall, and Open Court and Soul Swap last until the point ends.

### Removed
- The Jiangshi Hex power-up.

## 1.2 — 2026-11-04

Power-ups arrive, with more backgrounds and music and a full jukebox.

### Added
- Power-ups: talismans appear on the court during a match. Touch one with your paddle, or with a ball you hit last, to take it.
- Boons: Safety Teleport, Giant Paddle, Swift Step and Spirit Fire. Curses: Frostbite, Shrink Curse, Jiangshi Hex and Ghost Ball. Wild: Gravity, Open Court and Soul Swap.
- A Power-Ups screen showing what each one does, where you choose which can turn up and how often (Rare, Normal, Frequent).
- Rally rewards: every 20 or 10 hits in one rally, both players earn a Safety Teleport (you can hold two).
- Game Pace: slows down or speeds up the whole match, including the ball, paddles, AI and Chaos timers.
- Chaos Switch & +, for both kinds of switch at once.
- The jukebox: click the track's name for the full list.
- Ambience: crackling spirit fire and crickets under the music, in the menus only or everywhere.
- Even Out Volume turns down tracks recorded much louder than the rest.
- Track Fade (Quick, Smooth, Slow) between songs, and Menu Sounds (clicks and whooshes).
- Rotate can change the background every 30 to 60 seconds, 2 minutes or 5 minutes.
- Parallax: the menu background drifts against the mouse, for depth.
- 5 more backgrounds (34 in all) and 15 more music tracks (58 in all).

### Changed
- Chaos Switch + now swaps the paddles' places on the court at random moments, with a warning first. Your keys, score and goal stay yours, and it takes the Middle Wall down.
- Hard hits speed the ball up to at most about 2.4 times its serve speed.
- Background pictures load while you play instead of all at the start.

### Fixed
- After a hitch, the game slows for a moment instead of letting the ball jump ahead.

## 1.1 — 2026-11-03

AI styles, key rebinding, new Chaos modes and an Interface settings page.

### Added
- AI styles: Balanced, Guardian, Striker and Trickster.
- AI Banter: the AI teases you when it scores and grumbles when it doesn't.
- From the pause menu, hand either paddle to the AI or take it back, and change settings without leaving the match.
- Restart a match from 0-0.
- Middle Wall setting: switch it off and the paddles can roam the whole court.
- Chaos Mode +: sizes and speeds keep drifting during play, separately for each paddle and the ball.
- Chaos Switch: after every point you take over your opponent's paddle, scores and all. Chaos Switch + makes the swap at random moments mid-rally, with a warning first.
- Interface settings: tooltips, HUD (Full or Minimal), effects (Full, Reduced or Off), countdown length (3, 2 or 1 seconds), screen shake, a fire trail behind the ball, auto-pause when you click away, and hiding the mouse during a match.
- Key rebinding: click a key, then press the new one.

## 1.0 — 2026-11-03

First release, with a new Wangsheng Funeral Parlor look.

### Added
- A new look themed on the Wangsheng Funeral Parlor: lacquer and paper panels, plum blossom headings, title boards, and paddles drawn as lacquered staffs.
- Effects: butterflies, embers, sparks, falling petals and bursts.
- New fonts: Ma Shan Zheng and Philosopher.
- A loading screen, and "Red scored!" and "Blue scored!" banners.
- A Match the Display resolution option.
- Reset to Default on each settings screen, and Reset All Settings.
- 17 more backgrounds (29 in all) and 27 more music tracks (43 in all).
- CREDITS.md, crediting the artists, musicians and font designers.

## 0.9 — 2026-11-02

Match setup, stats, and settings that are remembered.

### Added
- A Match Setup screen: choose your opponent (another player or the AI) and which paddle you play.
- Adaptive AI: it eases off while it's ahead and sharpens up when it's behind, to keep matches close.
- Chaos Mode: new random sizes and speeds every round.
- A Stats screen: matches played, wins and losses against the AI, win rate, win streak, longest rally, fastest ball, points scored and time played, with Reset Stats.
- Settings and stats are saved between sessions.
- Music by mood: relaxed in the menus, upbeat in matches, and triumphant or downbeat after a match, with the track name shown as it starts.
- The controls are shown on screen (Red: W A S D, Blue: arrow keys).

### Changed
- Text too long for its space now shrinks to fit instead of running off the edge.

## 0.8 — 2026-10-28

A behind-the-scenes rebuild of the menus and sound.

### Changed
- Menus, text and the HUD now scale properly when the window size changes.
- One Background setting with its own picker screen, instead of separate menu and game backgrounds.
- The menu drawing, font and sound code was rebuilt and shared between screens, ready for the bigger changes that followed.

## 0.7 — 2026-03-20

Endless Mode and a bigger soundtrack.

### Added
- Endless Mode: play with no score limit, either as the winning score or by carrying on after a match ends.
- Separate win and lose music, and Loop or Shuffle for the music.
- Randomise buttons for the music, and Randomise All for random ball and paddle speeds and sizes.
- Reset All, to put the settings back to their defaults.
- Rotate: the background fades to a different picture every so often.
- Red-wins and Blue-wins announcements, a losing sound, a shutdown sound and a second win sound.
- 9 new music tracks (16 in all). Relaxed Tao is now three tracks.

### Changed
- Winning score choices are now 3, 5, 11, 15, 21 or Endless (were 1, 3, 5, 10, 15 or 20).

## 0.6 — 2026-03-14

Settings, music and backgrounds.

### Added
- Gameplay settings: paddle size and speed, ball size and speed, winning score (1, 3, 5, 10, 15 or 20), win by two, and the AI on or off at five difficulties (Baby, Easy, Normal, Hard, Insane).
- Display settings: resolutions from 854 x 480 up to 7680 x 4320, maximum FPS (30 to 240, or unlimited), Show FPS, and dimming the background.
- 12 backgrounds, with a picker for the menu and for matches.
- Music: 8 tracks, chosen separately for the menu, matches and the win screen, with music and sound-effect volumes.
- Sound effects for the menus, the countdown and winning.
- A win screen with Play Again, and a confirmation before resetting, leaving or quitting.

### Changed
- The game is laid out for 1920 x 1080 (was 1280 x 720) and scales to the window.

## 0.5 — 2026-02-25

Rebuilt in Pygame.

### Changed
- Rebuilt in Pygame instead of Tkinter, with a new game loop, menus and HUD.
- Settings are split into Gameplay, Display and Audio pages.
- Paddles bounce the ball at up to 60° again.

### Added
- Display settings: resolution (960 x 540 up to 2560 x 1440) and window mode.
- Audio settings: master volume, and paddle and score sounds on or off.

## 0.4 — 2026-02-16

Faster rallies and a fairer AI.

### Changed
- The ball keeps its speed off a paddle and speeds up as a rally goes on, up to 5 times as fast by 100 hits.
- Paddles bounce the ball at up to 50° (was 60°), and the walls are fully bouncy.
- The goals are coloured red and blue, with a dashed centre line.
- The AI starts at difficulty 5 out of 10 (was 10), reacts faster at low levels, reads the ball further ahead at high levels, and no longer panics.
- The ball no longer pushes the paddles back, and paddles move a little slower.

### Fixed
- Blue's score was shown in Red's place.

## 0.3 — 2026-02-15

The game split into modules.

### Changed
- The single script was split into modules (app, game, objects and physics) with a config file and shared helpers, ready for bigger changes. It plays almost the same as 0.2, with small bounce tweaks.

## 0.2 — 2026-02-15

A rewrite with proper physics and sound.

### Added
- Sounds: each paddle has its own hit sound.
- A HUD showing the scores, rally count and ball speed, with a button to switch the AI on or off.

### Changed
- Rewritten around screens (main menu, settings and game) and a shared game loop.
- New physics: swept collisions, so the ball can't pass through a paddle, with mass, bounciness and spin.

## 0.1 — 2026-02-15

The first version.

### Added
- Pong for two on one keyboard in a Tkinter window. Red uses W A S D and Blue the arrow keys, and paddles move up, down, left and right.
- An AI that can take over a paddle.
- A main menu, a pause menu (Resume, Reset, Main Menu) and a Settings screen.
- A countdown before each serve, a rally counter and a ball speed display.
- Spin and angled bounces, depending on where the ball hits the paddle.
