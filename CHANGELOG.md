# Changelog

Every version of Hu Taong, newest first. Toki Hub shows each version's section on that version's page.

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
