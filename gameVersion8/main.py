"""
main.py  –  Entry point for CHAOS BALL.

    python main.py

Requirements:  pip install pygame
"""

import sys
import os

# When running as a PyInstaller .exe, switch working directory to the
# temporary folder where bundled files (assets, sounds, etc.) are extracted.
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

import pygame
from settings import SW, SH, FPS
from game import Game
from renderer import Renderer
from menu import Menu


def main():
    screen = pygame.display.set_mode((SW, SH))
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.2)
    try:
        pygame.mixer.music.load("assets/sounds/background/chaosball1.mp3")
        pygame.mixer.music.play(loops=-1)
    except Exception:
        pass
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

            # Check for return to menu (ESC or button click)
            if game.return_to_menu:
                back_to_menu = True

            # Allow returning to menu with M when the game is in an end state
            keys = pygame.key.get_pressed()
            if keys[pygame.K_m] and game.state in ("game_over","win","level_clear"):
                back_to_menu = True


if __name__ == "__main__":
    main()
