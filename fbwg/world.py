"""Game logic: a Python port of the dylanroman03/FireAndWater-Game Java code.

This module has no pygame dependency, so it can run headless (for example
inside a reinforcement learning environment). One call to ``World.update``
is one physics tick; the original game runs 200 ticks per second.

Differences from the Java version:
- Both heroes play at the same time (the Java game lets you pick one).
  The level is won when both heroes have reached their own door, and it is
  lost as soon as either hero dies.
- The button (switch) timers are counted in ticks instead of wall-clock time
  (4 s = 800 ticks, 8 s = 1600 ticks), so runs are fully deterministic.
- The swing tilt animation, which Java updated inside render(), is advanced
  at the same 120-per-second rate inside update().
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .config import (
    A_DIE,
    A_DOWN,
    A_IDLE,
    A_IDLE_LEFT,
    A_JUMP,
    A_RUN_LEFT,
    A_RUN_RIGHT,
    DUDE,
    FPS,
    GAME_HEIGHT,
    GAME_WIDTH,
    HEROES,
    PINK,
    SCALE,
    T_BOX,
    T_CRYSTAL_BLUE,
    T_CRYSTAL_PURPLE,
    T_DOOR_DUDE,
    T_DOOR_PINK,
    T_FIRE_BLUE,
    T_FIRE_GREEN,
    T_FIRE_PURPLE,
    T_FLOOR,
    T_START_DUDE,
    T_START_PINK,
    T_SWING,
    TILES_SIZE,
    UPS,
)
from .geometry import Rect, convex_overlap, f32, rotate_points
from .level import level_count, level_path, load_level

T = TILES_SIZE

# Frame counts of each animation, taken from the sprite file names (Constants.java)
HERO_FRAMES = [8, 6, 6, 4, 4, 4, 8]
FIRE_FRAMES = 8
SWITCH_FRAMES = 4

SWITCH_MOVE_TICKS = 4 * UPS  # 4 seconds
SWITCH_RESET_TICKS = 8 * UPS  # 8 seconds


# --------------------------------------------------------------------------- entities


class Entity:
    """entities/Entity.java"""

    ani_speed = 15

    def __init__(self, x: float, y: float, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.hitbox = Rect(x, y, width, height)
        self.ani_index = 0
        self.ani_tick = 0
        self.frames = 1

    def intersect(self, player: Player) -> bool:
        """Overlap with the player's hitbox at its next position."""
        return self.hitbox.intersects(
            f32(player.hitbox.x + player.x_speed),
            f32(player.hitbox.y + player.air_speed),
            player.width,
            player.height,
        )

    def update(self) -> None:
        self.ani_tick += 1
        if self.ani_tick >= self.ani_speed:
            self.ani_tick = 0
            self.ani_index += 1
            if self.ani_index >= self.frames:
                self.ani_index = 0


class Fire(Entity):
    def __init__(self, x, y, kind: int):
        super().__init__(x, y + 5, T, T)
        self.kind = kind
        self.frames = FIRE_FRAMES
        self.hitbox = Rect(x, y + T // 2, T, T // 2)


class Crystal(Entity):
    def __init__(self, x, y, kind: int):
        super().__init__(x, y, T, T)
        self.kind = kind
        self.visible = True

    def intersect(self, player) -> bool:
        if super().intersect(player) and self.visible:
            self.visible = False
            return True
        return False


class Door(Entity):
    def __init__(self, x, y, hero: str):
        super().__init__(x, y, T, T)
        self.hero = hero


class Floor(Entity):
    def __init__(self, x, y, image_name: str):
        super().__init__(x, y, T, T)
        self.image_name = image_name


class Lever(Entity):
    def __init__(self, x, y, platform_id: int, is_on: int):
        super().__init__(x, y, T, T)
        self.platform_id = platform_id
        self.is_on = is_on != 0
        self.ani_index = 0 if self.is_on else 1

    def intersect_lever(self, player: Player, world: World) -> bool:
        if player.action == A_RUN_LEFT:
            if self.hitbox.intersects(f32(player.hitbox.x + player.x_speed), player.hitbox.y, 1, 1):
                if self.is_on:
                    self.is_on = False
                    self.ani_index = 1
                    world.move_platform(self.platform_id)
                    world.emit("lever", None)
                return True
        elif player.action == A_RUN_RIGHT:
            if self.hitbox.intersects(
                f32(f32(player.hitbox.x + player.hitbox.w) + player.x_speed), player.hitbox.y, 1, self.hitbox.h
            ):
                if not self.is_on:
                    self.is_on = True
                    self.ani_index = 0
                    world.move_platform(self.platform_id)
                    world.emit("lever", None)
                return True
        return super().intersect(player)


class Switch(Entity):
    """A floor button. Pressing it moves its platform after 4 s and back after 8 s."""

    def __init__(self, x, y, platform_id: int):
        super().__init__(x, y + T // 2, T, T)
        self.platform_id = platform_id
        self.is_on = False
        self.frames = SWITCH_FRAMES
        self.ani_index = 1
        self.hitbox = Rect(x, y + T // 2, T, T // 2)

    def update(self) -> None:
        self.ani_tick += 1
        if self.ani_tick >= self.ani_speed:
            self.ani_tick = 0
            if self.is_on and self.ani_index < self.frames - 1:
                self.ani_index += 1
            elif not self.is_on and self.ani_index > 0:
                self.ani_index -= 1

    def intersect(self, player) -> bool:
        if super().intersect(player) and not self.is_on:
            self.is_on = True
            return True
        return False


class Platform(Entity):
    def __init__(self, x, y, pid: int, status: int, direction: int, size: int):
        if size > 0 and direction == 1:
            w, h = T // 2, T * size
        elif size > 0:
            w, h = T * size, T // 3
        else:
            w, h = T * 2, T // 3
        super().__init__(x, y, w, h)
        self.id = pid
        x_sum = 100 if w == T * 2 else (w // (T * 2)) * 100
        self.y_init = y if status == 0 else y + 100
        self.x_init = x if status == 0 else x + x_sum
        self.vertical = direction == 1
        self.climbing = status != 0
        self.dropping = False

    def _player_over(self, p: Player) -> bool:
        hb = self.hitbox
        return (
            f32(p.hitbox.x + p.width) > hb.x
            and p.hitbox.x < f32(hb.x + self.width)
            and f32(f32(p.hitbox.y + p.height) + 5) > hb.y
            and p.hitbox.y < f32(hb.y + self.height)
        )

    def update_with(self, players) -> None:
        hb = self.hitbox
        if self.vertical:
            if self.climbing and self.y_init - 100 < hb.y:
                for p in players:
                    if self._player_over(p):
                        p.hitbox.y -= 0.5
                hb.y -= 0.5
            elif self.dropping and hb.y < self.y_init:
                for p in players:
                    if self._player_over(p):
                        p.hitbox.y += 0.5
                hb.y += 0.5
        else:
            size = 100 if self.width == T * 2 else (self.width // (T * 2)) * 100
            if self.climbing and self.x_init - size < hb.x:
                for p in players:
                    if self._player_over(p):
                        p.hitbox.x -= 0.5
                hb.x -= 0.5
            elif self.dropping and hb.x < self.x_init:
                for p in players:
                    if self._player_over(p):
                        p.hitbox.x += 0.5
                hb.x += 0.5

    def move(self) -> None:
        if self.climbing:
            self.climbing, self.dropping = False, True
        else:
            self.climbing, self.dropping = True, False


class Box(Entity):
    def __init__(self, x, y, world: World):
        super().__init__(x, y, T, T)
        self.world = world

    def intersect(self, player) -> bool:
        hb = player.hitbox
        if player.action == A_RUN_LEFT:
            if self.hitbox.intersects(hb.x + player.x_speed, hb.y, 1, 1):
                if not self._intersect_floor(1):
                    self.hitbox.x -= 1
        elif player.action == A_RUN_RIGHT:
            if self.hitbox.intersects(hb.x + hb.w + player.x_speed, hb.y, 1, self.hitbox.h):
                if not self._intersect_floor(-1):
                    self.hitbox.x += 1
        return super().intersect(player)

    def _intersect_floor(self, dx: int) -> bool:
        b = self.hitbox
        return any(b.intersects(f.hitbox.x + dx, f.hitbox.y, T, T) for f in self.world.floors_near(b, 1))

    def fall_if_unsupported(self) -> None:
        b = self.hitbox
        for f in self.world.floors_near(b, 1):
            if b.intersects(f.hitbox.x, f.hitbox.y - 1, T, 1):
                return
        b.y += 1


class Swing(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, T * 4, T // 2)
        self.angle = 0.0

    def intersect(self, player) -> bool:
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        px, py = player.hitbox.x, player.hitbox.y
        dx, dy = px - cx, py - cy
        if cx > px and cy > py:
            new_angle, direction = math.atan2(dy, -dx), "L"
        elif cx < px and cy > py:
            new_angle, direction = math.atan2(-dy, dx), "R"
        elif cx > px and cy < py:
            new_angle, direction = math.atan2(-dy, -dx), "LD"
        elif cx < px and cy < py:
            new_angle, direction = math.atan2(dy, dx), "RD"
        else:
            new_angle, direction = math.atan2(-dy, dx), "R"

        if self.hitbox.intersects_rect(player.hitbox):
            nudge = {"L": (-0.5, -0.5), "LD": (-0.5, 0.5), "R": (0.5, -0.5), "RD": (0.5, 0.5)}[direction]
            player.hitbox.x += nudge[0]
            player.hitbox.y += nudge[1]

        if self._collides_with(player):
            self.angle = self.angle + 0.1 * (new_angle - self.angle)
            return True
        return False

    def _collides_with(self, player) -> bool:
        r = self.hitbox
        p1 = rotate_points(
            [(r.x, r.y), (r.x + r.w, r.y), (r.x + r.w, r.y + r.h), (r.x, r.y + r.h)], self.angle, r.cx, r.cy
        )
        x = f32(player.hitbox.x + player.x_speed)
        y = f32(player.hitbox.y + player.air_speed)
        w, h = player.width, player.height
        xw, yh = f32(x + w), f32(y + h)
        p2 = [(int(x), int(y)), (int(xw), int(y)), (int(xw), int(yh)), (int(x), int(yh))]
        return convex_overlap(p1, p2)

    def visual_tick(self) -> None:
        if self.angle >= 180 or self.angle <= -180:
            self.angle = 0.0
        elif self.angle != 0:
            self.angle += self.angle * 0.08


class Player(Entity):
    """entities/Player.java"""

    ani_speed = 10
    running_speed = f32(1.2)
    gravity = f32(f32(0.02) * SCALE)
    jumping_speed = f32(f32(-1.2) * SCALE)
    fall_speed = f32(f32(0.3) * SCALE)

    def __init__(self, hero: str, x: float, y: float, world: World):
        super().__init__(x, y, int(T * 0.6), int(T * 0.8))
        self.hero = hero
        self.world = world
        self.action = A_IDLE
        self.ani_index = 0.0
        self.moving = False
        self.left = self.right = self.jump = False
        self.view_left = False
        self.death = False
        self.stop_animation = False
        self.game_won = False  # reached its door
        self.air_speed = 0.0
        self.in_air = False
        self.x_speed = 0.0
        self.death_finished = False

    # input -------------------------------------------------------------
    def set_input(self, left: bool, right: bool, jump: bool) -> None:
        # In Java, every press or release of left/right sets the facing direction.
        if left != self.left:
            self.view_left = True
        if right != self.right:
            self.view_left = False
        self.left, self.right, self.jump = bool(left), bool(right), bool(jump)

    # update ------------------------------------------------------------
    def update(self) -> None:
        self._update_position()
        if not self.stop_animation:
            self._update_animation_tick()
        self._set_animation()

    def _update_animation_tick(self) -> None:
        self.ani_tick += 1
        if self.ani_tick >= self.ani_speed:
            self.ani_tick = 0
            self.ani_index += 1 if self.moving else 0.25
            if self.ani_index >= HERO_FRAMES[self.action]:
                if self.death:
                    self.stop_animation = True
                    self.death_finished = True
                    self.ani_index -= 1
                else:
                    self.ani_index = 0

    def _set_animation(self) -> None:
        start = self.action
        if self.moving:
            if self.left:
                self.action = A_RUN_LEFT
            elif self.right:
                self.action = A_RUN_RIGHT
            elif self.jump:
                self.action = A_JUMP
            else:
                self.action = A_DOWN
        elif self.death:
            self.action = A_DIE
        elif self.view_left:
            self.action = A_IDLE_LEFT
        else:
            self.action = A_IDLE
        if start != self.action:
            self.ani_tick = 0
            self.ani_index = 0

    def _update_position(self) -> None:
        w = self.world
        self.moving = False
        if self.death:
            return
        if self.jump and not self.in_air:
            self.in_air = True
            self.air_speed = self.jumping_speed
            w.emit("jump", self.hero)

        if self.in_air:
            self._in_air()
        elif not self._is_in_floor():
            self.in_air = True

        if (not self.left and not self.right and not self.in_air) or self.game_won:
            return

        self.x_speed = 0.0
        if self.left and not self.right:
            self.x_speed = -self.running_speed
        elif self.right and not self.left:
            self.x_speed = self.running_speed

        if w.can_move(self, f32(self.hitbox.x + self.x_speed), self.hitbox.y):
            self.hitbox.x += self.x_speed

        self.moving = True

        if w.fire_intersect(self):
            self.death = True
            self.moving = False
            w.emit("die", self.hero)

        if w.doors[self.hero].intersect(self):
            self.game_won = True
            self.stop_animation = True
            w.emit("door", self.hero)

        if w.crystal_intersect(self):
            w.emit("gem", self.hero)

        w.switch_intersect(self)
        w.lever_intersect(self)

    def _is_in_floor(self) -> bool:
        w, hb = self.world, self.hitbox
        below = f32(f32(hb.y + hb.h) + 1)
        if not w.is_solid(self, hb.x, below) and not w.is_solid(self, f32(hb.x + hb.w), below):
            if not w.over_some_platform(self):
                return False
        return True

    def _in_air(self) -> None:
        if self.world.can_move(self, self.hitbox.x, f32(self.hitbox.y + self.air_speed)):
            self.hitbox.y += self.air_speed
            self.air_speed = f32(self.air_speed + self.gravity)
        elif self.air_speed > 0:
            self.in_air = False
            self.air_speed = 0.0
        else:
            self.air_speed = self.fall_speed


# --------------------------------------------------------------------------- world


@dataclass
class StepInfo:
    events: list = field(default_factory=list)


class World:
    """One level being played (screens/Playing.java plus all managers)."""

    def __init__(self, level_index: int = 0, grid: list[list[int]] | None = None):
        self.level_index = level_index
        self.grid = grid if grid is not None else load_level(level_path(level_index))
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.tick = 0
        self.events: list[tuple[str, str | None]] = []
        self._scheduled: list[tuple[int, object]] = []
        self._visual_acc = 0.0
        self.game_over = False
        self.level_won = False
        self._build()

    # construction --------------------------------------------------------
    def _cells(self, predicate):
        for i, row in enumerate(self.grid):
            for j, v in enumerate(row):
                if predicate(v):
                    yield i, j, v

    def _build(self) -> None:
        g = self.grid
        self.fires = {
            T_FIRE_BLUE: [Fire(T * j, T * i, v) for i, j, v in self._cells(lambda v: v == T_FIRE_BLUE)],
            T_FIRE_PURPLE: [Fire(T * j, T * i, v) for i, j, v in self._cells(lambda v: v == T_FIRE_PURPLE)],
            T_FIRE_GREEN: [Fire(T * j, T * i, v) for i, j, v in self._cells(lambda v: v == T_FIRE_GREEN)],
        }
        self.crystals = {
            PINK: [Crystal(T * j, T * i, v) for i, j, v in self._cells(lambda v: v == T_CRYSTAL_PURPLE)],
            DUDE: [Crystal(T * j, T * i, v) for i, j, v in self._cells(lambda v: v == T_CRYSTAL_BLUE)],
        }
        self.doors = {}
        for i, j, v in self._cells(lambda v: v in (T_DOOR_PINK, T_DOOR_DUDE)):
            hero = PINK if v == T_DOOR_PINK else DUDE
            self.doors[hero] = Door(T * j, T * i, hero)

        self.floors: list[Floor] = []
        self.floor_at: dict[tuple[int, int], Floor] = {}
        cols = self.cols
        for i, j, _ in self._cells(lambda v: v == T_FLOOR):
            if i != 0 and g[i - 1][j] == T_FLOOR:
                img = "back"
            elif j == 0 or g[i][j - 1] != T_FLOOR:
                img = "corner_l1"
            elif j == 1 or g[i][j - 2] != T_FLOOR:
                img = "corner_l2"
            elif j == cols - 1:
                img = "corner_r2"
            elif j == cols - 2:
                img = "corner_r1"
            elif g[i][j + 1] != T_FLOOR:
                img = "border_r"
            else:
                img = "floor"
            f = Floor(T * j, T * i, img)
            self.floors.append(f)
            self.floor_at[(i, j)] = f

        self.platforms = []
        for i, j, v in self._cells(lambda v: 1000 < v < 3000):
            s = str(v)
            self.platforms.append(Platform(T * j, T * i, int(s[1]), int(s[2]), int(s[0]), int(s[3])))
        self.boxes = [Box(T * j, T * i, self) for i, j, _ in self._cells(lambda v: v == T_BOX)]
        self.swings = [Swing(T * j, T * i) for i, j, _ in self._cells(lambda v: v == T_SWING)]
        self.levers = []
        for i, j, v in self._cells(lambda v: 700 < v < 800):
            s = str(v)
            self.levers.append(Lever(T * j, T * i, int(s[1]), int(s[2])))
        self.switches = []
        for i, j, v in self._cells(lambda v: 80 < v < 90):
            self.switches.append(Switch(T * j, T * i, int(str(v)[1])))

        self.players = {}
        for hero, tile in ((PINK, T_START_PINK), (DUDE, T_START_DUDE)):
            pos = (0, GAME_HEIGHT - int(T * 2.05))
            for i, j, _ in self._cells(lambda v, t=tile: v == t):
                pos = (T * j, T * i)
            self.players[hero] = Player(hero, pos[0], pos[1], self)

    # queries used by the player -----------------------------------------
    def floors_near(self, rect: Rect, margin: int = 1):
        """Floor tiles near a rectangle (all others cannot touch it)."""
        r0 = max(0, int(rect.y // T) - margin)
        r1 = min(self.rows - 1, int((rect.y + rect.h) // T) + margin)
        c0 = max(0, int(rect.x // T) - margin)
        c1 = min(self.cols - 1, int((rect.x + rect.w) // T) + margin)
        for i in range(r0, r1 + 1):
            for j in range(c0, c1 + 1):
                f = self.floor_at.get((i, j))
                if f is not None:
                    yield f

    def is_solid(self, player: Player, x: float, y: float) -> bool:
        """Helpers.isSolid. Note: the platform/box/swing checks test the
        player's whole next hitbox, not the point, exactly like the original."""
        xi, yi = f32(x / T), f32(y / T)
        if xi >= self.cols or yi >= self.rows:
            return True
        value = self.grid[int(yi)][int(xi)]
        if x < 0 or x >= GAME_WIDTH or y < 0 or y >= GAME_HEIGHT or value == T_FLOOR or 700 < value < 800:
            return True
        if any(p.intersect(player) for p in self.platforms):
            return True
        if any(b.intersect(player) for b in self.boxes):
            return True
        if any(s.intersect(player) for s in self.swings):
            return True
        return False

    def can_move(self, player: Player, x: float, y: float) -> bool:
        w, h = player.hitbox.w, player.hitbox.h
        if x < 0 or x >= GAME_WIDTH or y < 0 or y >= GAME_HEIGHT:
            return False
        xw, yh = f32(x + w), f32(y + h)
        return (
            not self.is_solid(player, x, y)
            and not self.is_solid(player, xw, yh)
            and not self.is_solid(player, xw, y)
            and not self.is_solid(player, x, yh)
        )

    def over_some_platform(self, p: Player) -> bool:
        for pl in self.platforms:
            hb = pl.hitbox
            if (
                f32(p.hitbox.x + p.width) > hb.x
                and p.hitbox.x < f32(hb.x + pl.width)
                and f32(f32(p.hitbox.y + p.height) + 5) > hb.y
                and p.hitbox.y < f32(hb.y + pl.height)
            ):
                return True
        return False

    def fire_intersect(self, p: Player) -> bool:
        own_danger = T_FIRE_BLUE if p.hero == PINK else T_FIRE_PURPLE
        return any(f.intersect(p) for f in self.fires[own_danger]) or any(
            f.intersect(p) for f in self.fires[T_FIRE_GREEN]
        )

    def crystal_intersect(self, p: Player) -> bool:
        return any(c.intersect(p) for c in self.crystals[p.hero])

    def switch_intersect(self, p: Player) -> bool:
        for s in self.switches:
            if s.intersect(p):
                pid = s.platform_id
                self.schedule(SWITCH_MOVE_TICKS, lambda pid=pid: self.move_platform(pid))

                def reset(s=s, pid=pid):
                    s.is_on = False
                    self.move_platform(pid)

                self.schedule(SWITCH_RESET_TICKS, reset)
                return True
        return False

    def lever_intersect(self, p: Player) -> bool:
        return any(lv.intersect_lever(p, self) for lv in self.levers)

    def move_platform(self, pid: int) -> None:
        for pl in self.platforms:
            if pl.id == pid:
                pl.move()

    # bookkeeping ---------------------------------------------------------
    def emit(self, name: str, hero: str | None) -> None:
        self.events.append((name, hero))

    def schedule(self, delay_ticks: int, fn) -> None:
        self._scheduled.append((self.tick + delay_ticks, fn))

    def time_seconds(self) -> int:
        return self.tick // UPS

    def crystal_score(self, hero: str) -> tuple[int, int]:
        cs = self.crystals[hero]
        return sum(not c.visible for c in cs), len(cs)

    @property
    def finished(self) -> bool:
        return self.game_over or self.level_won

    # main update ---------------------------------------------------------
    def set_inputs(self, inputs: dict[str, tuple[bool, bool, bool]]) -> None:
        """inputs: {hero: (left, right, jump)}"""
        for hero, (left, right, jump) in inputs.items():
            self.players[hero].set_input(left, right, jump)

    def update(self) -> list[tuple[str, str | None]]:
        """Advance one physics tick (1/200 s). Returns the events of this tick."""
        self.events = []
        if self.finished:
            return self.events
        self.tick += 1

        due = [fn for t, fn in self._scheduled if t <= self.tick]
        self._scheduled = [(t, fn) for t, fn in self._scheduled if t > self.tick]
        for fn in due:
            fn()

        for fires in self.fires.values():
            for f in fires:
                f.update()
        for s in self.switches:
            s.update()
        players = [self.players[h] for h in HEROES]
        for pl in self.platforms:
            pl.update_with(players)
        for b in self.boxes:
            b.update()
            b.fall_if_unsupported()
        for sw in self.swings:
            sw.update()
        for p in players:
            p.update()

        self._visual_acc += FPS / UPS
        while self._visual_acc >= 1:
            self._visual_acc -= 1
            for sw in self.swings:
                sw.visual_tick()

        if any(p.death_finished for p in players):
            self.game_over = True
            self.emit("game_over", None)
        elif all(p.game_won for p in players):
            self.level_won = True
            self.emit("level_won", None)
        return self.events

    def step(self, inputs: dict[str, tuple[bool, bool, bool]], ticks: int = 1) -> list:
        """Set inputs and run several ticks (frame skip). Returns all events."""
        self.set_inputs(inputs)
        events = []
        for _ in range(ticks):
            events += self.update()
            if self.finished:
                break
        return events


def new_world(level_index: int = 0) -> World:
    return World(level_index)


__all__ = ["World", "Player", "new_world", "level_count", "HEROES", "PINK", "DUDE"]
