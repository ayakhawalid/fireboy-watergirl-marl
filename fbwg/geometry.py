"""Small geometry helpers that mirror java.awt.geom behaviour."""

from __future__ import annotations

import math
from struct import Struct

_F32 = Struct("f")


def f32(v: float) -> float:
    """Round to a 32-bit float, like Java float arithmetic (the original uses floats)."""
    return _F32.unpack(_F32.pack(v))[0]


def intersects(ax, ay, aw, ah, bx, by, bw, bh) -> bool:
    """Rectangle2D.intersects: true only if the interiors overlap."""
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return False
    return bx + bw > ax and by + bh > ay and bx < ax + aw and by < ay + ah


class Rect:
    """Rectangle2D.Float: x and y are stored as 32-bit floats."""

    __slots__ = ("_x", "_y", "w", "h")

    def __init__(self, x: float, y: float, w: float, h: float):
        self._x = f32(x)
        self._y = f32(y)
        self.w = w
        self.h = h

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, v: float) -> None:
        self._x = f32(v)

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, v: float) -> None:
        self._y = f32(v)

    def intersects(self, x, y, w, h) -> bool:
        return intersects(self.x, self.y, self.w, self.h, x, y, w, h)

    def intersects_rect(self, other: Rect) -> bool:
        return intersects(self.x, self.y, self.w, self.h, other.x, other.y, other.w, other.h)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


def rotate_points(points, degrees, cx, cy):
    """AffineTransform.rotate(theta, cx, cy) applied to points, cast to int like the Java code."""
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    out = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        out.append((int(cx + dx * c - dy * s), int(cy + dx * s + dy * c)))
    return out


def _project(poly, ax, ay):
    vals = [px * ax + py * ay for px, py in poly]
    return min(vals), max(vals)


def convex_overlap(p1, p2) -> bool:
    """True if two convex polygons overlap with positive area (like a non-empty java.awt.geom.Area)."""
    for poly in (p1, p2):
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            ax, ay = y1 - y2, x2 - x1  # edge normal
            if ax == 0 and ay == 0:
                continue
            min1, max1 = _project(p1, ax, ay)
            min2, max2 = _project(p2, ax, ay)
            if max1 <= min2 or max2 <= min1:
                return False
    return True
