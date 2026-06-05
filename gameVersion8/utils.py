"""
utils.py
--------
Stateless helper functions:
  - coordinate scaling from the 1920×1080 canvas to the real screen
  - shared drawing primitives (spikes, hearts)
"""

import pygame
from settings import SW, SH, CANVAS_W, CANVAS_H


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def scale_rect(r: tuple) -> tuple:
    """Scale a (x, y, w, h) rect from canvas space to screen space."""
    x, y, w, h = r
    return (
        int(x * SW / CANVAS_W),
        int(y * SH / CANVAS_H),
        int(w * SW / CANVAS_W),
        int(h * SH / CANVAS_H),
    )


def scale_pt(pt: tuple) -> tuple:
    """Scale a (x, y) point from canvas space to screen space."""
    x, y = pt
    return (int(x * SW / CANVAS_W), int(y * SH / CANVAS_H))


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def draw_spike(surf: pygame.Surface, rect: tuple, direction: str, color: tuple) -> None:
    """
    Draw a row of triangular spikes inside *rect*.

    direction : "up" | "down" | "left" | "right"
                Points in the direction the spike tips face.
    """
    x, y, w, h = rect
    num = max(1, w // 20)
    tw  = w // num

    for i in range(num):
        if direction == "up":
            pts = [
                (x + i*tw,          y + h),
                (x + i*tw + tw//2,  y),
                (x + i*tw + tw,     y + h),
            ]
        elif direction == "down":
            pts = [
                (x + i*tw,          y),
                (x + i*tw + tw//2,  y + h),
                (x + i*tw + tw,     y),
            ]
        elif direction == "right":
            pts = [
                (x,      y + i*tw),
                (x + h,  y + i*tw + tw//2),
                (x,      y + i*tw + tw),
            ]
        elif direction == "left":
            pts = [
                (x + w,  y + i*tw),
                (x,      y + i*tw + tw//2),
                (x + w,  y + i*tw + tw),
            ]
        else:
            continue
        pygame.draw.polygon(surf, color, pts)


def draw_heart(surf: pygame.Surface, cx: int, cy: int, size: int, color: tuple) -> None:
    """Draw a simple filled heart centred at (cx, cy)."""
    r = size // 2
    pygame.draw.circle(surf, color, (cx - r//2, cy - r//4), r//2)
    pygame.draw.circle(surf, color, (cx + r//2, cy - r//4), r//2)
    pts = [
        (cx - r, cy - r//4),
        (cx + r, cy - r//4),
        (cx,     cy + r),
    ]
    pygame.draw.polygon(surf, color, pts)
