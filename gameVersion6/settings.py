"""
settings.py  –  All global constants. Zero imports from the rest of the project.
"""
import pygame

pygame.init()
_info = pygame.display.Info()
SW: int = _info.current_w
SH: int = _info.current_h
FPS: int = 60

# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------
GRAVITY_STRENGTH: float = 1400.0
GRAVITY_DIRS = [(0,1),(0,-1),(1,0),(-1,0)]

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
BG_COLORS = [
    (15, 10, 30),   # deep purple night
    (10, 30, 15),   # deep forest green
    (30, 10, 10),   # deep red ember
    (10, 20, 35),   # deep ocean blue
    (30, 25,  5),   # deep amber dusk
    ( 5, 20, 25),   # deep teal
    (25,  5, 20),   # deep crimson
    (20, 20,  5),   # deep khaki
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
    "void_wall":   ( 80,   0, 180),
    "projectile":  (255, 255,  80),
    "enemy_proj":  (255,  60,  60),
}

# ---------------------------------------------------------------------------
# Level / tier layout
# ---------------------------------------------------------------------------
NUM_LEVELS: int = 20

#  L01-08  BASIC     – platforms + spikes
#  L09-12  SPINNERS  – + rotating obstacles (up to 3)
#  L13-20  VOID      – + secret void walls + player gun (3 shots/level)
#  L17-20  HAUNTED+  – void tier also gains flying ghosts + shooting turrets
TIER_BASIC_END:    int =  8   # exclusive upper bound
TIER_SPINNER_END:  int = 12
TIER_VOID_END:     int = 20   # L13-20: void walls active; gun unlocked
TIER_SHOOTER_START: int = 16  # L17-20: shooting turrets + flying enemies added

# ---------------------------------------------------------------------------
# Canvas (normalised 1920×1080 design space)
# ---------------------------------------------------------------------------
CANVAS_W: int = 1920
CANVAS_H: int = 1080

GOAL_W:  int = 70
GOAL_H:  int = 90
GOAL_CX: int = CANVAS_W // 2
GOAL_CY: int = CANVAS_H // 2

GOAL_SAFE_R:  int = 140
SPAWN_SAFE_R: int = 180

# ---------------------------------------------------------------------------
# Player gun  (unlocked from level 13 onward)
# ---------------------------------------------------------------------------
GUN_AMMO_PER_LEVEL: int = 3
GUN_PROJ_SPEED:     int = 900   # px/s screen-space
GUN_PROJ_RADIUS:    int = 7
