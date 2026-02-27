"""
main.py
-------
Entry point for CHAOS BALL.

Run with:
    python main.py

Requirements:
    pip install pygame
"""

import pygame
from settings import SW, SH, FPS
from game import Game
from renderer import Renderer


def main() -> None:
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("CHAOS BALL")
    clock    = pygame.time.Clock()
    game     = Game()
    renderer = Renderer(screen)

    while True:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)   # cap to avoid tunnelling on lag spikes

        game.handle_events()
        game.update(dt)
        renderer.draw(game)


if __name__ == "__main__":
    main()