# Changelog

Every version of Hu Taong, newest first. Toki Hub shows each version's section on that version's page.

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
