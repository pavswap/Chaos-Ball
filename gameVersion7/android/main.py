"""
main.py  –  Android entry point for CHAOS BALL.

Touch controls:
  LEFT side  → virtual joystick  (move)
  JUMP btn   → jump / double-jump
  DASH btn   → dash
  FIRE btn   → shoot (gun levels)
  Tap right  → shoot toward tap point
"""

import sys
import os

# Buildozer sets ANDROID_ARGUMENT; detect and set up paths
try:
    import android  # type: ignore  (only present on-device)
    _ON_ANDROID = True
except ImportError:
    _ON_ANDROID = False

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

import pygame
from settings import SW, SH, FPS
from game import Game
from renderer import Renderer
from menu import Menu
from touch_controls import TouchControls


def main():
    pygame.init()
    pygame.mixer.init()

    if _ON_ANDROID:
        # Full-screen on the actual device
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        # Desktop test window  (portrait-ish for phone feel)
        screen = pygame.display.set_mode((SW, SH))

    pygame.display.set_caption("CHAOS BALL")
    clock    = pygame.time.Clock()
    game     = Game()
    renderer = Renderer(screen)
    touch    = TouchControls()

    while True:
        # ── Main menu ────────────────────────────────────────────────────
        menu   = Menu(screen, clock)
        result = menu.run()

        if result == "quit":
            pygame.quit()
            return

        _, start_level = result
        game.start_at(start_level)

        # ── Game loop ────────────────────────────────────────────────────
        back_to_menu = False
        while not back_to_menu:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                touch.handle_event(event)
                game.handle_event_android(event)

            touch_state = touch.get_state()
            game.update_android(dt, touch_state)
            renderer.draw(game)
            touch.draw(screen)
            pygame.display.flip()

            # Back-to-menu: swipe from very left edge OR game ended
            if game.state in ("game_over", "win"):
                # Show overlay for 2 s then return to menu
                pygame.time.wait(2000)
                back_to_menu = True


if __name__ == "__main__":
    main()
