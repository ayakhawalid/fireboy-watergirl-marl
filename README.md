# Fireboy and Watergirl – Multi-Agent Reinforcement Learning Project

A Python (pygame) port of the Java game
[dylanroman03/FireAndWater-Game](https://github.com/dylanroman03/FireAndWater-Game),
which we use as the environment for a cooperative multi-agent RL project.

The port keeps the original levels, graphics, sounds, physics and objects
(fires, gems, doors, levers, buttons, moving platforms, boxes, swings).
The game logic (`fbwg/world.py`) does not depend on pygame, so it can run
headless and much faster than real time for training.

## Run the game

Python 3.10 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python play.py
```

On Windows you can also double-click `play_windows.bat`.

Options: `--mute`, `--level 1` (start on level 2), `--debug` (show hitboxes).

## Controls

| | Left | Right | Jump |
|---|---|---|---|
| Pink | A | D | W |
| Dude | ← | → | ↑ |

In a level: `Esc` back to the menu, `R` restart, `F3` show hitboxes.

Each hero must reach its own door (the key above it has the hero's colour).
Pink dies in blue fire, Dude dies in purple fire, both die in green fire.
Pink collects purple gems, Dude collects blue gems.

## Differences from the Java version

- **Both heroes play at the same time** (the Java game lets you pick one).
  The level is won when both reached their doors, and lost if either dies.
- Button timers count physics ticks instead of wall-clock time, so a run
  with the same inputs always gives the same result.
- Menus are in English, and the character/name selection screen was removed.

The physics was checked against the original Java code: for over 100 random
input sequences on both levels, the hero positions match the Java game
exactly, tick by tick.

## Code structure

```
fbwg/
  config.py    constants, tile codes, asset paths
  level.py     level file loader
  geometry.py  rectangle / polygon helpers (Java float semantics)
  world.py     game logic, no pygame (use this for RL)
  assets.py    images, fonts, sounds
  render.py    draws a World with pygame
  app.py       window, menus, main loop
levels/        01.txt, 02.txt (from the original game)
res/           graphics, font and sounds (from the original game)
tests/         headless tests: python tests/test_world.py
```

### Using the game logic directly

```python
from fbwg.world import World

world = World(level_index=0)
# inputs per hero: (left, right, jump); one update = 1/200 s
events = world.step({"pink": (False, True, False), "dude": (False, False, True)}, ticks=8)
print(world.players["pink"].hitbox.x, world.level_won, world.game_over, events)
```

## Credits

- Original game, levels and code structure: Dylan Buitrago and Kevin Gonzalez,
  [FireAndWater-Game](https://github.com/dylanroman03/FireAndWater-Game), MIT license
  (see `THIRD_PARTY_LICENSE_FireAndWater-Game.txt`).
- Graphics and sounds come from that repository; some of them come from
  free asset packs (for example "PGS Fantasy RPG Music Pack"). Check the
  original packs' licenses before publishing this project publicly.
- Python port: Boshra, Aya, Firas and Mohamed (RL course, University of Haifa).
