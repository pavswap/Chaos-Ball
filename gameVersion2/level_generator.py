"""
level_generator.py
------------------
Procedural level generator.

Every level is a dict:
    {
        "platforms" : [(x, y, w, h), ...],          # canvas-space rects
        "spikes"    : [(x, y, w, h, direction), ...],
        "goal"      : (x, y, w, h),                  # always canvas centre
        "spawn"     : (x, y),                        # always a safe corner
    }

All coordinates are in the 1920×1080 normalised canvas; they are scaled to the
real screen at load time by Game.load_level().
"""

import math
import random

from settings import (
    CANVAS_W, CANVAS_H,
    GOAL_W, GOAL_H, GOAL_CX, GOAL_CY,
    GOAL_SAFE_R, SPAWN_SAFE_R,
    NUM_LEVELS,
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _overlap(ax, ay, aw, ah, bx, by, bw, bh, margin: int = 20) -> bool:
    """Return True if the two rects (expanded by *margin*) overlap."""
    return (
        ax - margin < bx + bw and ax + aw + margin > bx and
        ay - margin < by + bh and ay + ah + margin > by
    )


def _near_centre(x, y, w, h, safe_r: int = GOAL_SAFE_R) -> bool:
    """Return True if the rect centre is too close to the goal centre."""
    cx = x + w / 2
    cy = y + h / 2
    return math.hypot(cx - GOAL_CX, cy - GOAL_CY) < safe_r


def _near_spawn(x, y, w, h, sx, sy, safe_r: int = SPAWN_SAFE_R) -> bool:
    cx = x + w / 2
    cy = y + h / 2
    return math.hypot(cx - sx, cy - sy) < safe_r


# ---------------------------------------------------------------------------
# Platform placement
# ---------------------------------------------------------------------------

def _place_platform(existing: list, x, y, w, h, sx, sy) -> bool:
    """
    Try to add (x,y,w,h) to *existing*.
    Rejects if it overlaps another platform, is too close to the goal or
    spawn zones, or extends outside the arena margin.
    """
    if _near_centre(x, y, w, h):
        return False
    if _near_spawn(x, y, w, h, sx, sy):
        return False
    margin = 40
    if x < margin or y < margin or x + w > CANVAS_W - margin or y + h > CANVAS_H - margin:
        return False
    for (ex, ey, ew, eh) in existing:
        if _overlap(x, y, w, h, ex, ey, ew, eh):
            return False
    existing.append((x, y, w, h))
    return True


def _add_shape(platforms: list, shape: list, sx, sy) -> bool:
    """
    Attempt to add an entire multi-rect shape atomically.
    If any piece fails placement the whole shape is rejected.
    """
    tmp = list(platforms)
    for piece in shape:
        if not _place_platform(tmp, *piece, sx, sy):
            return False
    platforms.clear()
    platforms.extend(tmp)
    return True


# ---------------------------------------------------------------------------
# Shape generators  (all return a list of (x,y,w,h) tuples)
# ---------------------------------------------------------------------------

def _rand_slab(r: random.Random) -> list:
    """Horizontal slab – the most common building block."""
    w = r.randint(120, 340)
    h = r.randint(18, 28)
    x = r.randint(60, CANVAS_W - 60 - w)
    y = r.randint(80, CANVAS_H - 80 - h)
    return [(x, y, w, h)]


def _rand_pillar(r: random.Random) -> list:
    """Tall vertical pillar."""
    w = r.randint(18, 30)
    h = r.randint(100, 260)
    x = r.randint(60, CANVAS_W - 60 - w)
    y = r.randint(80, CANVAS_H - 80 - h)
    return [(x, y, w, h)]


def _rand_L(r: random.Random) -> list:
    """L-shape: horizontal arm + a vertical leg at one end."""
    w1 = r.randint(160, 280)
    h1 = 22
    w2 = 22
    h2 = r.randint(80, 180)
    x  = r.randint(60, CANVAS_W - 60 - w1)
    y  = r.randint(80, CANVAS_H - 80 - h1 - h2)
    if r.choice([True, False]):
        return [(x, y, w1, h1), (x + w1 - w2, y + h1, w2, h2)]
    return [(x, y, w1, h1), (x, y + h1, w2, h2)]


def _rand_T(r: random.Random) -> list:
    """T-shape: wide horizontal bar + thin vertical stem from the centre."""
    w1 = r.randint(180, 300)
    h1 = 22
    w2 = 22
    h2 = r.randint(60, 140)
    x  = r.randint(60, CANVAS_W - 60 - w1)
    y  = r.randint(80, CANVAS_H - 80 - h1 - h2)
    return [(x, y, w1, h1), (x + w1 // 2 - w2 // 2, y + h1, w2, h2)]


def _rand_staircase(r: random.Random) -> list:
    """3-step diagonal staircase (ascending left-to-right or right-to-left)."""
    step_w = r.randint(90, 150)
    step_h = 20
    dx     = r.choice([-1, 1]) * r.randint(60, 100)
    dy     = r.randint(60, 120)
    x0     = r.randint(200, CANVAS_W - 200 - step_w)
    y0     = r.randint(200, CANVAS_H - 200 - step_h)
    return [(x0 + dx * i, y0 + dy * i, step_w, step_h) for i in range(3)]


def _rand_U(r: random.Random) -> list:
    """U-channel: bottom slab + two vertical side walls."""
    bw     = r.randint(160, 260)
    bh     = 20
    wall_h = r.randint(80, 160)
    wall_w = 20
    x      = r.randint(80, CANVAS_W - 80 - bw)
    y      = r.randint(80, CANVAS_H - 80 - bh - wall_h)
    return [
        (x,              y + wall_h, bw,     bh),      # bottom
        (x,              y,          wall_w, wall_h),   # left wall
        (x + bw - wall_w, y,         wall_w, wall_h),   # right wall
    ]


def _rand_ring(r: random.Random) -> list:
    """Square frame / floating ring (4 thin slabs forming a hollow square)."""
    size = r.randint(160, 260)
    t    = 18
    x    = r.randint(80, CANVAS_W - 80 - size)
    y    = r.randint(80, CANVAS_H - 80 - size)
    return [
        (x,            y,            size,        t),             # top
        (x,            y + size - t, size,        t),             # bottom
        (x,            y + t,        t,           size - 2 * t),  # left
        (x + size - t, y + t,        t,           size - 2 * t),  # right
    ]


def _rand_cross(r: random.Random) -> list:
    """Plus / cross shape: two overlapping bars."""
    arm = r.randint(100, 180)
    t   = 22
    x   = r.randint(100, CANVAS_W - 100 - arm)
    y   = r.randint(100, CANVAS_H - 100 - arm)
    cx2 = x + arm // 2 - t // 2
    cy2 = y + arm // 2 - t // 2
    return [
        (x,   cy2, arm, t),    # horizontal arm
        (cx2, y,   t,   arm),  # vertical arm
    ]


# Shape function registry (slabs are weighted 3× because they are most useful)
_SHAPE_FUNCS = [
    _rand_slab, _rand_slab, _rand_slab,
    _rand_pillar,
    _rand_L,
    _rand_T,
    _rand_staircase,
    _rand_U,
    _rand_ring,
    _rand_cross,
]


# ---------------------------------------------------------------------------
# Spike generator
# ---------------------------------------------------------------------------

def _spikes_for_platform(
    px, py, pw, ph,
    difficulty: int,
    r: random.Random,
) -> list:
    """
    Return 0–3 spike tuples for one platform rect.
    Each tuple: (x, y, w, h, direction)
    *difficulty* (0–4) controls face count and placement probability.
    """
    spike_t = 24   # spike "thickness" (height for up/down, width for left/right)

    # All four possible spike faces
    faces = [
        ("up",    px,            py - spike_t,  pw,      spike_t),
        ("down",  px,            py + ph,       pw,      spike_t),
        ("right", px + pw,       py,            spike_t, ph),
        ("left",  px - spike_t,  py,            spike_t, ph),
    ]
    r.shuffle(faces)

    max_faces = 1 + difficulty // 2
    prob      = 0.35 + difficulty * 0.10

    spikes = []
    for direction, sx, sy, sw, sh in faces[:max_faces]:
        if r.random() > prob:
            continue
        # Clamp inside arena
        sx = max(10, min(CANVAS_W - 10 - sw, sx))
        sy = max(10, min(CANVAS_H - 10 - sh, sy))
        spikes.append((sx, sy, sw, sh, direction))

    return spikes


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------

def generate_level(level_idx: int, seed: int = None) -> dict:
    """
    Build and return a complete level dict.

    The goal is always at the exact canvas centre.
    The spawn is always in one of four safe corner regions.
    Difficulty scales 0 → 4 over the first five levels and stays at 4 beyond.
    """
    r          = random.Random(seed if seed is not None else level_idx * 7919 + 42)
    difficulty = min(level_idx, 4)

    # --- Goal (always centre) ---
    goal = (GOAL_CX - GOAL_W // 2, GOAL_CY - GOAL_H // 2, GOAL_W, GOAL_H)

    # --- Spawn (random safe corner) ---
    corners = [(80, 80), (1840, 80), (80, 1000), (1840, 1000)]
    spawn   = r.choice(corners)

    # --- Platforms ---
    platforms: list = []

    # One guaranteed border edge so there is always a landing surface
    # regardless of gravity direction.
    border = r.choice(["floor", "ceiling", "left", "right"])
    border_rects = {
        "floor":   (0,    1050, CANVAS_W,      30),
        "ceiling": (0,    0,    CANVAS_W,      30),
        "left":    (0,    0,    30,        CANVAS_H),
        "right":   (1890, 0,    30,        CANVAS_H),
    }
    platforms.append(border_rects[border])

    # Guaranteed safe landing pad right at spawn
    pad_w, pad_h = 200, 22
    pad_x = max(10, min(CANVAS_W - 10 - pad_w, spawn[0] - pad_w // 2))
    pad_y = max(10, min(CANVAS_H - 10 - pad_h, spawn[1] + 30))
    platforms.append((pad_x, pad_y, pad_w, pad_h))

    # Fill in random shapes
    target = 10 + difficulty * 2
    attempts = 0
    while len(platforms) < target + 2 and attempts < 400:
        attempts += 1
        shape = r.choice(_SHAPE_FUNCS)(r)
        _add_shape(platforms, shape, spawn[0], spawn[1])

    # --- Spikes ---
    blacklist = [
        (GOAL_CX  - GOAL_SAFE_R,  GOAL_CY  - GOAL_SAFE_R,
         GOAL_SAFE_R  * 2,        GOAL_SAFE_R  * 2),
        (spawn[0] - SPAWN_SAFE_R, spawn[1] - SPAWN_SAFE_R,
         SPAWN_SAFE_R * 2,        SPAWN_SAFE_R * 2),
    ]

    spikes: list = []
    for px, py, pw, ph in platforms[2:]:   # skip border + spawn pad
        for sx, sy, sw, sh, direction in _spikes_for_platform(px, py, pw, ph, difficulty, r):
            blocked = any(
                _overlap(sx, sy, sw, sh, bx, by, bw, bh, margin=0)
                for bx, by, bw, bh in blacklist
            )
            if not blocked:
                spikes.append((sx, sy, sw, sh, direction))

    return {
        "platforms": platforms,
        "spikes":    spikes,
        "goal":      goal,
        "spawn":     spawn,
    }


# Pre-generate all levels at import time so Game can index straight into this list.
LEVELS_DATA: list = [generate_level(i) for i in range(NUM_LEVELS)]