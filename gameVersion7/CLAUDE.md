# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
pip install pygame
python main.py
```

The game requires an `assets/sounds/` directory with these WAV files: `jump.wav`, `shoot.wav`, `coin.wav`, `respawn.wav`, `hit.wav`, `level_clear.wav`, `boost.wav`, `enemy_hit.wav`. The game will crash on startup if these are missing.

## Architecture

**CHAOS BALL** is a pygame platformer with 20 procedurally generated levels. The player (a ball) must reach a goal portal while gravity direction and wall lethality randomize on each death.

### Coordinate System

All level data is authored in a **1920x1080 canvas space**. At runtime, coordinates are scaled to the actual screen resolution via `utils.scale_rect()` and `utils.scale_pt()`. The screen size is detected at import time in `settings.py` using `pygame.display.Info()`. When adding new game objects, always define positions in canvas space and scale them on load.

### Module Responsibilities

- **`settings.py`** — All constants (screen size, physics, colors, tier boundaries). Zero imports from other project modules. Runs `pygame.init()` at import time.
- **`game.py`** — `Game` class owns all mutable game state and update logic. Zero rendering code. Handles input events, physics (gravity, movement, collisions), and state transitions (`play` → `level_clear` → `win` / `game_over`).
- **`renderer.py`** — `Renderer` class handles all `pygame.draw` calls. Reads from `Game` but never mutates it. Screen shake renders to an intermediate surface then blits with offset.
- **`menu.py`** — `Menu` class runs its own blocking event loop (`Menu.run()`) for main menu and level select. Returns `("play", level_idx)` or `"quit"`.
- **`level_generator.py`** — Procedural level generation. `LEVELS_DATA` (list of 20 level dicts) is pre-generated at import time via seeded `random.Random`. Level dicts contain: `platforms`, `spikes`, `goal`, `spawn`, `rotators`, `enemies`, `shooters`, `void_walls`, `has_gun`, `coins`, `boost_pads`.
- **`enemies.py`** — Entity classes: `RotatingObstacle`, `FlyingEnemy` (3 AI behaviors: chase/orbit/zigzag), `ShootingEnemy`, `EnemyProjectile`, `PlayerProjectile`, `VoidWall` (edge portals with teleport + cooldown). Each class owns its own `update()` and `draw()` methods.
- **`particles.py`** — `Particle` (burst circles) and `Flash` (full-screen color overlay).
- **`utils.py`** — Stateless helpers: `scale_rect`, `scale_pt`, `draw_spike`, `draw_heart`.

### Tier System

Levels are grouped into tiers that progressively unlock mechanics:

| Levels | Tier | Features Added |
|--------|------|----------------|
| 1-8 | BASIC | Platforms + spikes |
| 9-12 | SPINNERS | + rotating obstacles |
| 13-16 | VOID | + void wall portals + player gun (unlimited ammo) |
| 17-20 | HAUNTED | + flying ghosts + shooting turrets |

Tier boundaries are defined as constants in `settings.py` (`TIER_BASIC_END`, `TIER_SPINNER_END`, `TIER_SHOOTER_START`).

### Game Loop Flow

`main.py` runs an outer loop: Menu → Game loop → back to Menu. The game loop calls `game.handle_events()` → `game.update(dt)` → `renderer.draw(game)` each frame. Delta time is capped at 50ms to prevent physics tunneling.

### Key Mechanics

- **Chaos respawn**: On death, gravity direction randomizes (4 cardinal directions) and deadly walls may toggle. Background color shifts.
- **Double jump**: 2 jumps available; restored when touching the surface gravity pushes toward (not just any wall).
- **Void walls**: Edge portals teleport to the opposite screen edge with cooldown. Portal streak tracking drives screen shake + slow-motion + rainbow particle effects.
- **Player gun**: Available in void tier (L13+). Fires toward mouse cursor. Unlimited ammo with 0.15s cooldown between shots.
