# Changelog

Every version of Hu Taong, newest first. Toki Hub shows each version's section on that version's page.

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
