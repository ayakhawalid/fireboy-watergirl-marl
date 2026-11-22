"""Headless checks of the game logic: python -m pytest tests  (or python tests/test_world.py)"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fbwg.config import DUDE, PINK, TILES_SIZE, UPS  # noqa: E402
from fbwg.world import World  # noqa: E402

IDLE = (False, False, False)


def test_levels_load():
    for i in range(2):
        w = World(i)
        assert w.rows == 25 and w.cols == 29
        assert set(w.doors) == {PINK, DUDE}
        assert set(w.players) == {PINK, DUDE}


def test_players_rest_on_floor():
    w = World(0)
    start = {h: (p.hitbox.x, p.hitbox.y) for h, p in w.players.items()}
    w.step({PINK: IDLE, DUDE: IDLE}, ticks=2 * UPS)
    for h, p in w.players.items():
        assert not p.in_air
        assert abs(p.hitbox.y - start[h][1]) < TILES_SIZE  # did not fall through the floor
        assert not p.death


def test_walking_and_jumping():
    w = World(0)
    p = w.players[PINK]
    x0 = p.hitbox.x
    w.step({PINK: (False, True, False), DUDE: IDLE}, ticks=UPS)
    assert p.hitbox.x > x0 + 50  # about 1.2 px per tick
    y0 = p.hitbox.y
    w.step({PINK: (False, False, True), DUDE: IDLE}, ticks=20)
    assert p.hitbox.y < y0  # going up
    w.step({PINK: IDLE, DUDE: IDLE}, ticks=2 * UPS)
    assert not p.in_air  # landed again


def test_wrong_fire_kills():
    # Level 1 bottom row: purple fire (kills DUDE) at columns 13-15, blue fire (kills PINK) at 20-22.
    # DUDE starts above PINK; walking right he drops to the bottom row and into the purple fire.
    w = World(0)
    p = w.players[DUDE]
    for _ in range(30 * UPS):
        w.step({DUDE: (False, True, False), PINK: IDLE})
        if w.finished:
            break
    assert p.death and w.game_over


def test_deterministic():
    def run():
        w = World(0)
        seq = [(False, True, False), (False, True, True), (True, False, False), IDLE]
        for k in range(3000):
            a = seq[(k // 150) % len(seq)]
            w.step({PINK: a, DUDE: a})
        return [(round(p.hitbox.x, 4), round(p.hitbox.y, 4)) for p in w.players.values()]

    assert run() == run()


def test_speed():
    w = World(0)
    t = time.perf_counter()
    n = 5000
    for k in range(n):
        w.step({PINK: (False, k % 400 < 200, k % 97 == 0), DUDE: (k % 300 < 150, False, False)})
        if w.finished:
            w = World(0)
    rate = n / (time.perf_counter() - t)
    print(f"{rate:.0f} ticks per second headless")
    assert rate > UPS  # faster than real time


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
