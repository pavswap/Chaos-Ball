"""
particles.py
------------
Visual effect classes:
  - Particle  : a single burst particle (position, velocity, fade)
  - Flash     : a full-screen colour overlay that fades out
"""

import math
import random

import pygame
from settings import SW, SH


class Particle:
    """
    A small coloured circle that flies outward from a spawn point,
    fades, and then dies.
    """

    def __init__(self, x: float, y: float, color: tuple) -> None:
        self.x     = x
        self.y     = y
        angle      = random.uniform(0, 2 * math.pi)
        speed      = random.uniform(100, 400)
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.life  = random.uniform(0.4, 1.0)
        self._max  = self.life
        self.color = color
        self.r     = random.randint(3, 8)

    def update(self, dt: float) -> None:
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += 200 * dt   # mild downward drag regardless of game gravity
        self.life -= dt

    def draw(self, surf: pygame.Surface) -> None:
        alpha = max(0.0, self.life / self._max)
        r = int(self.r * alpha)
        if r > 0:
            c = tuple(int(v * alpha) for v in self.color)
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)

    @property
    def alive(self) -> bool:
        return self.life > 0


class Flash:
    """
    A full-screen translucent colour overlay that fades out over *duration*
    seconds.  Useful for death flashes, level-clear flashes, etc.
    """

    def __init__(self, color: tuple, duration: float = 0.3) -> None:
        self.color    = color
        self.duration = duration
        self.timer    = duration

    def update(self, dt: float) -> None:
        self.timer -= dt

    def draw(self, surf: pygame.Surface) -> None:
        alpha   = max(0.0, self.timer / self.duration)
        overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
        overlay.fill((*self.color, int(120 * alpha)))
        surf.blit(overlay, (0, 0))

    @property
    def done(self) -> bool:
        return self.timer <= 0
