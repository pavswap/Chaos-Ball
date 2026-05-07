"""
settings.py  –  Android version. Screen is always full-screen device resolution.
"""
import pygame
pygame.init()

# On Android pygame gives the real device resolution automatically
_info = pygame.display.Info()
SW: int = _info.current_w  if _info.current_w  > 0 else 1080
SH: int = _info.current_h  if _info.current_h  > 0 else 1920
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
    (15, 10, 30),(10, 30, 15),(30, 10, 10),(10, 20, 35),
    (30, 25, 5),(5, 20, 25),(25, 5, 20),(20, 20, 5),
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
# Level layout
# ---------------------------------------------------------------------------
NUM_LEVELS: int = 20
TIER_BASIC_END:     int =  8
TIER_SPINNER_END:   int = 12
TIER_VOID_END:      int = 20
TIER_SHOOTER_START: int = 16

# ---------------------------------------------------------------------------
# Canvas (normalised design space)
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
# Gun
# ---------------------------------------------------------------------------
GUN_AMMO_PER_LEVEL: int = 3
GUN_PROJ_SPEED:     int = 900
GUN_PROJ_RADIUS:    int = 7

# ---------------------------------------------------------------------------
# Dash
# ---------------------------------------------------------------------------
DASH_SPEED:    float = 1400.0
DASH_DURATION: float = 0.18
DASH_COOLDOWN: float = 0.60

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
INVINCIBLE_DURATION: float = 1.5
COYOTE_TIME:         float = 0.10
JUMP_BUFFER_TIME:    float = 0.12
DEATH_FREEZE_TIME:   float = 0.35
KILL_COMBO_WINDOW:   float = 2.0

# ---------------------------------------------------------------------------
# Touch / virtual controls sizes (scale with screen)
# ---------------------------------------------------------------------------
# Joystick on the left, action buttons on the right
TOUCH_BTN_RADIUS   = int(min(SW, SH) * 0.075)   # action buttons radius
JOYSTICK_RADIUS    = int(min(SW, SH) * 0.10)     # outer joystick ring
JOYSTICK_KNOB_R    = int(min(SW, SH) * 0.045)    # inner knob
CONTROLS_ALPHA     = 180                          # transparency of controls
