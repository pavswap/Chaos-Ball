"""
main.py  –  Entry point for CHAOS BALL.

    python main.py

Requirements:  pip install pygame
"""

import pygame
from settings import SW, SH, FPS
from game import Game
from renderer import Renderer
from menu import Menu


def main():
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("CHAOS BALL")
    clock    = pygame.time.Clock()
    game     = Game()
    renderer = Renderer(screen)

    while True:
        # ── Main / level-select menu ────────────────────────────────────
        menu   = Menu(screen, clock)
        result = menu.run()

        if result == "quit":
            pygame.quit()
            return

        _, start_level = result       # ("play", level_idx)
        game.start_at(start_level)

        # ── Game loop ───────────────────────────────────────────────────
        back_to_menu = False
        while not back_to_menu:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)   # cap at 50 ms

            game.handle_events()
            game.update(dt)
            renderer.draw(game)

            # Allow returning to menu with M when the game is in an end state
            keys = pygame.key.get_pressed()
            if keys[pygame.K_m] and game.state in ("game_over","win","level_clear"):
                back_to_menu = True


if __name__ == "__main__":
    main()
