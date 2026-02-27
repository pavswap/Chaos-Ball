"""
settings.py
-----------
All global constants: screen, colours, physics, level parameters.
Nothing here imports from the rest of the project.
"""

import pygame

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
pygame.init()
_info = pygame.display.Info()
SW: int = _info.current_w   # screen width  (actual desktop resolution)
SH: int = _info.current_h   # screen height
FPS: int = 60

# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------
GRAVITY_STRENGTH: float = 1400.0   # px/s²  – feels weighty at any direction

GRAVITY_DIRS = [
    ( 0,  1),   # down  (default)
    ( 0, -1),   # up
    ( 1,  0),   # right
    (-1,  0),   # left
]

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
BG_COLORS = [
    (15, 10, 30),    # deep purple night
    (10, 30, 15),    # deep forest green
    (30, 10, 10),    # deep red ember
    (10, 20, 35),    # deep ocean blue
    (30, 25,  5),    # deep amber dusk
]

PALETTE = {
    "ball":        (255,  80,  50),
    "platform":    ( 70, 180, 255),
    "spike":       (255, 220,  50),
    "deadly_wall": (255,  50, 100),
    "safe_wall":   ( 60,  60,  80),
    "goal":        ( 50, 255, 150),
    "heart_full":  (255,  60,  80),
    "heart_empty": ( 80,  40,  50),
    "text":        (240, 240, 255),
    "shadow":      (  0,   0,   0),
}

# ---------------------------------------------------------------------------
# Level generation
# ---------------------------------------------------------------------------
NUM_LEVELS: int = 8

# Normalised design canvas (levels are authored in this space, then scaled)
CANVAS_W: int = 1920
CANVAS_H: int = 1080

# Goal is always at the exact centre of the canvas
GOAL_W:  int = 70
GOAL_H:  int = 90
GOAL_CX: int = CANVAS_W // 2   # 960
GOAL_CY: int = CANVAS_H // 2   # 540

# Exclusion radii (normalised pixels)
GOAL_SAFE_R:  int = 140   # no platforms/spikes inside this radius around goal
SPAWN_SAFE_R: int = 180   # no spikes inside this radius around spawn