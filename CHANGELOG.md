# Changelog

Every version of Hu Taong, newest first. Toki Hub shows each version's section on that version's page.

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
