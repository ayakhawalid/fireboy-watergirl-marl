"""Image, font and sound loading (utilities/Helpers.java)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pygame

from . import config as C


@lru_cache(maxsize=None)
def image(path: Path) -> pygame.Surface:
    surf = pygame.image.load(str(path))
    return surf.convert_alpha() if pygame.display.get_surface() else surf


def _frame_count(path: Path) -> int:
    # Like getAnimationsX: the digit before ".png" is the number of frames.
    m = re.search(r"(\d)\.png$", path.name)
    return int(m.group(1)) if m else 1


@lru_cache(maxsize=None)
def frames_x(path: Path) -> tuple[pygame.Surface, ...]:
    img = image(path)
    n = _frame_count(path)
    w, h = img.get_width() // n, img.get_height()
    return tuple(img.subsurface((i * w, 0, w, h)) for i in range(n))


@lru_cache(maxsize=None)
def frames_y(path: Path) -> tuple[pygame.Surface, ...]:
    img = image(path)
    n = _frame_count(path)
    w, h = img.get_width(), img.get_height() // n
    return tuple(img.subsurface((0, i * h, w, h)) for i in range(n))


@lru_cache(maxsize=None)
def sub(path: Path, x: int, y: int, w: int, h: int) -> pygame.Surface:
    return image(path).subsurface((x, y, w, h))


_scaled: dict = {}


def scaled(surf: pygame.Surface, w: int, h: int) -> pygame.Surface:
    """Nearest-neighbour scaling (what Java drawImage does by default), cached."""
    key = (id(surf), w, h)
    hit = _scaled.get(key)
    if hit is None:
        # Keep a reference to the source surface so its id() is never reused.
        hit = (surf, pygame.transform.scale(surf, (max(1, w), max(1, h))))
        _scaled[key] = hit
    return hit[1]


def hero_frames(hero: str) -> list[tuple[pygame.Surface, ...]]:
    folder, prefix = C.P_HERO_DIR[hero], C.P_HERO_PREFIX[hero]
    return [frames_x(folder / f"{prefix}_{name}.png") for name in C.HERO_ANIMS]


def hero_portrait(hero: str) -> pygame.Surface:
    return image(C.P_HERO_DIR[hero] / f"{C.P_HERO_PREFIX[hero]}.png")


# Floor tile images (FloorManager.java)
def floor_images() -> dict[str, pygame.Surface]:
    p = C.P_LEVEL_BUILD
    return {
        "corner_l1": sub(p, 16, 240, 30, 37),
        "corner_l2": sub(p, 46, 240, 15, 37),
        "corner_r1": sub(p, 624, 240, 30, 37),
        "corner_r2": sub(p, 654, 240, 15, 37),
        "border_r": sub(p, 257, 175, 31, 40),
        "floor": sub(p, 130, 240, 30, 30),
        "back": sub(p, 38, 38, 25, 20),
    }


def platform_image() -> pygame.Surface:
    return sub(C.P_LEVEL_BUILD, 753, 20, 175, 12)


@lru_cache(maxsize=None)
def font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(str(C.P_FONT), size)
    except (OSError, FileNotFoundError):
        return pygame.font.Font(None, size)


def number_image(ch: str) -> pygame.Surface | None:
    name = "colon" if ch == ":" else ch
    path = C.P_NUMBERS / f"{name}.png"
    return image(path) if path.exists() else None


class Sound:
    """Music and sound effects. Silently does nothing if audio is unavailable."""

    def __init__(self, enabled: bool = True):
        self.enabled = False
        self._cache: dict[Path, pygame.mixer.Sound] = {}
        self._music: Path | None = None
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play(self, path: Path) -> None:
        if not self.enabled:
            return
        try:
            snd = self._cache.get(path)
            if snd is None:
                snd = self._cache[path] = pygame.mixer.Sound(str(path))
            snd.play()
        except pygame.error:
            pass

    def music(self, path: Path | None) -> None:
        if not self.enabled or path == self._music:
            return
        self._music = path
        try:
            if path is None:
                pygame.mixer.music.stop()
            else:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.play(-1)
        except pygame.error:
            pass
