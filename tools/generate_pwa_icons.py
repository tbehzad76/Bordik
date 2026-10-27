"""Generate the PWA icons for Bordik without any third-party dependency.

The icons are produced from scratch (a rounded square with a white check mark)
and written as PNG files into ``task_manager/static/icons``.  Run it again after
changing the design:

    .\\.venv\\Scripts\\python.exe tools\\generate_pwa_icons.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "task_manager" / "static" / "icons"

BACKGROUND = (37, 99, 235)  # --primary #2563eb
FOREGROUND = (255, 255, 255)
SUPERSAMPLE = 3

CHECK_POINTS = ((0.30, 0.52), (0.44, 0.68), (0.72, 0.34))
CHECK_WIDTH = 0.085


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _write_png(path: Path, size: int, pixels: list[bytes]) -> None:
    raw = b"".join(b"\x00" + row for row in pixels)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def _inside_rounded_rect(x: float, y: float, radius: float) -> bool:
    if x < 0 or y < 0 or x > 1 or y > 1:
        return False
    cx = min(max(x, radius), 1 - radius)
    cy = min(max(y, radius), 1 - radius)
    if x == cx or y == cy:
        return True
    return math.hypot(x - cx, y - cy) <= radius


def _distance_to_segment(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _scaled_check_points(scale: float) -> tuple[tuple[float, float], ...]:
    return tuple(
        (0.5 + (x - 0.5) * scale, 0.5 + (y - 0.5) * scale) for x, y in CHECK_POINTS
    )


def render(size: int, *, rounded: bool, check_scale: float) -> bytes:
    points = _scaled_check_points(check_scale)
    half_width = CHECK_WIDTH * check_scale
    radius = 0.22 if rounded else 0.0
    samples = SUPERSAMPLE * SUPERSAMPLE
    step = 1.0 / SUPERSAMPLE
    rows: list[bytes] = []

    for py in range(size):
        row = bytearray()
        for px in range(size):
            background_hits = 0
            check_hits = 0
            for sy in range(SUPERSAMPLE):
                y = (py + (sy + 0.5) * step) / size
                for sx in range(SUPERSAMPLE):
                    x = (px + (sx + 0.5) * step) / size
                    if rounded:
                        inside = _inside_rounded_rect(x, y, radius)
                    else:
                        inside = 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0
                    if not inside:
                        continue
                    background_hits += 1
                    for (ax, ay), (bx, by) in zip(points, points[1:]):
                        if (
                            _distance_to_segment(x, y, ax, ay, bx, by)
                            <= half_width
                        ):
                            check_hits += 1
                            break
            if background_hits == 0:
                row += bytes((0, 0, 0, 0))
                continue
            background_alpha = background_hits / samples
            check_ratio = check_hits / background_hits
            color = tuple(
                round(bg + (fg - bg) * check_ratio)
                for bg, fg in zip(BACKGROUND, FOREGROUND)
            )
            row += bytes((*color, round(background_alpha * 255)))
        rows.append(bytes(row))
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        ("icon-192.png", 192, True, 1.0),
        ("icon-512.png", 512, True, 1.0),
        ("icon-maskable-192.png", 192, False, 0.66),
        ("icon-maskable-512.png", 512, False, 0.66),
        ("apple-touch-icon.png", 180, False, 0.9),
    ]
    for name, size, rounded, scale in targets:
        _write_png(OUTPUT_DIR / name, size, render(size, rounded=rounded, check_scale=scale))
        print(f"wrote {name} ({size}x{size})")


if __name__ == "__main__":
    main()
