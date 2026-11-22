"""Level loading, ported from managers/LevelManager.java."""

from __future__ import annotations

from pathlib import Path

from .config import LEVEL_FILES, LEVELS_DIR


def load_level(path: str | Path) -> list[list[int]]:
    """Read a level file.

    Format: first line is "<rows> <cols>", then one line per row. Like the Java
    Scanner code, only the first <cols> numbers of each line are used.
    """
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows, cols = (int(v) for v in lines[0].split()[:2])
    grid = []
    for i in range(rows):
        values = [int(v) for v in lines[1 + i].split()[:cols]]
        if len(values) < cols:
            raise ValueError(f"{path}: row {i} has {len(values)} values, expected {cols}")
        grid.append(values)
    return grid


def level_path(index: int) -> Path:
    return LEVELS_DIR / LEVEL_FILES[index]


def level_count() -> int:
    return len(LEVEL_FILES)
