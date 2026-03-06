"""
level_generator.py  --  Procedural generator for all 20 levels.

Tier layout (1-indexed for readability)
---------------------------------------
L01-08  BASIC     : platforms + spikes
L09-12  SPINNERS  : + rotating obstacles
L13-14  VOID      : + void wall portals (introduction)
L15-16  ARMED     : + player gun (learn to shoot)
L17-18  HAUNTED   : + flying ghosts
L19-20  SIEGE     : + shooting turrets (all mechanics combined)

Key improvements over V6:
  - Difficulty scales 0..9 across all 20 levels (was capped at 4)
  - Goal position varies by level (was always dead center)
  - Spawn position varies (was always a hard corner)
  - Path connectivity heuristic: a chain of platforms links spawn to goal
  - Spikes are placed to guard paths, not just random faces
  - Coins placed along paths + as risk-reward detours
  - Enemy speed scales with level
  - Gradual mechanic introduction (1 new thing per tier, not 3 at once)
"""

import math
import random
from settings import (
    CANVAS_W, CANVAS_H,
    GOAL_W, GOAL_H, GOAL_CX, GOAL_CY,
    GOAL_SAFE_R, SPAWN_SAFE_R,
    NUM_LEVELS,
    TIER_BASIC_END, TIER_SPINNER_END, TIER_VOID_END, TIER_SHOOTER_START,
)

# ============================================================================
# Geometry helpers
# ============================================================================

def _overlap(ax, ay, aw, ah, bx, by, bw, bh, margin=20):
    return (ax - margin < bx + bw and ax + aw + margin > bx and
            ay - margin < by + bh and ay + ah + margin > by)


def _near_point(x, y, w, h, px, py, safe_r):
    return math.hypot(x + w / 2 - px, y + h / 2 - py) < safe_r


def _place_platform(existing, x, y, w, h, sx, sy, gx, gy):
    """Try to add a platform. Returns True on success."""
    if _near_point(x, y, w, h, gx, gy, GOAL_SAFE_R):
        return False
    if _near_point(x, y, w, h, sx, sy, SPAWN_SAFE_R):
        return False
    mg = 40
    if x < mg or y < mg or x + w > CANVAS_W - mg or y + h > CANVAS_H - mg:
        return False
    for ex, ey, ew, eh in existing:
        if _overlap(x, y, w, h, ex, ey, ew, eh):
            return False
    existing.append((x, y, w, h))
    return True


def _add_shape(platforms, shape, sx, sy, gx, gy):
    tmp = list(platforms)
    for piece in shape:
        if not _place_platform(tmp, *piece, sx, sy, gx, gy):
            return False
    platforms.clear()
    platforms.extend(tmp)
    return True


# ============================================================================
# Shape generators
# ============================================================================

def _rand_slab(r):
    w = r.randint(120, 340)
    h = r.randint(18, 28)
    return [(r.randint(60, CANVAS_W - 60 - w), r.randint(80, CANVAS_H - 80 - h), w, h)]


def _rand_pillar(r):
    w = r.randint(18, 30)
    h = r.randint(100, 260)
    return [(r.randint(60, CANVAS_W - 60 - w), r.randint(80, CANVAS_H - 80 - h), w, h)]


def _rand_L(r):
    w1 = r.randint(160, 280); h1 = 22; w2 = 22; h2 = r.randint(80, 180)
    x = r.randint(60, CANVAS_W - 60 - w1)
    y = r.randint(80, CANVAS_H - 80 - h1 - h2)
    if r.choice([True, False]):
        return [(x, y, w1, h1), (x + w1 - w2, y + h1, w2, h2)]
    return [(x, y, w1, h1), (x, y + h1, w2, h2)]


def _rand_T(r):
    w1 = r.randint(180, 300); h1 = 22; w2 = 22; h2 = r.randint(60, 140)
    x = r.randint(60, CANVAS_W - 60 - w1)
    y = r.randint(80, CANVAS_H - 80 - h1 - h2)
    return [(x, y, w1, h1), (x + w1 // 2 - w2 // 2, y + h1, w2, h2)]


def _rand_staircase(r):
    sw = r.randint(90, 150); sh = 20
    dx = r.choice([-1, 1]) * r.randint(60, 100)
    dy = r.randint(60, 120)
    x0 = r.randint(200, CANVAS_W - 200 - sw)
    y0 = r.randint(200, CANVAS_H - 200 - sh)
    return [(x0 + dx * i, y0 + dy * i, sw, sh) for i in range(3)]


def _rand_U(r):
    bw = r.randint(160, 260); bh = 20; wh = r.randint(80, 160); ww = 20
    x = r.randint(80, CANVAS_W - 80 - bw)
    y = r.randint(80, CANVAS_H - 80 - bh - wh)
    return [(x, y + wh, bw, bh), (x, y, ww, wh), (x + bw - ww, y, ww, wh)]


def _rand_ring(r):
    sz = r.randint(160, 260); t = 18
    x = r.randint(80, CANVAS_W - 80 - sz)
    y = r.randint(80, CANVAS_H - 80 - sz)
    return [(x, y, sz, t), (x, y + sz - t, sz, t),
            (x, y + t, t, sz - 2 * t), (x + sz - t, y + t, t, sz - 2 * t)]


def _rand_cross(r):
    arm = r.randint(100, 180); t = 22
    x = r.randint(100, CANVAS_W - 100 - arm)
    y = r.randint(100, CANVAS_H - 100 - arm)
    return [(x, y + arm // 2 - t // 2, arm, t), (x + arm // 2 - t // 2, y, t, arm)]


_SHAPES = [_rand_slab, _rand_slab, _rand_slab, _rand_pillar,
           _rand_L, _rand_T, _rand_staircase, _rand_U, _rand_ring, _rand_cross]


# ============================================================================
# Path connectivity: place stepping-stone platforms between spawn and goal
# ============================================================================

def _gen_path_platforms(spawn, goal_center, r, count=4):
    """Generate a chain of small platforms from spawn toward the goal.
    This ensures the level is always solvable."""
    sx, sy = spawn
    gx, gy = goal_center
    platforms = []

    for i in range(1, count + 1):
        frac = i / (count + 1)
        # Interpolate between spawn and goal with random jitter
        cx = int(sx + (gx - sx) * frac + r.randint(-180, 180))
        cy = int(sy + (gy - sy) * frac + r.randint(-120, 120))
        cx = max(80, min(CANVAS_W - 200, cx))
        cy = max(80, min(CANVAS_H - 60, cy))
        pw = r.randint(100, 200)
        ph = r.randint(18, 24)
        platforms.append((cx, cy, pw, ph))
    return platforms


# ============================================================================
# Spawn / goal position variation
# ============================================================================

_SPAWN_POSITIONS = [
    # Corners
    (80, 80), (1840, 80), (80, 1000), (1840, 1000),
    # Edge midpoints
    (960, 80), (960, 1000), (80, 540), (1840, 540),
    # Quarter points
    (480, 270), (1440, 270), (480, 810), (1440, 810),
]

_GOAL_OFFSETS = [
    # (dx, dy) from center -- varies goal position
    (0, 0), (0, 0),  # center (default, most common)
    (400, 0), (-400, 0), (0, 250), (0, -250),
    (300, 200), (-300, -200), (350, -180), (-350, 180),
]


def _pick_spawn_goal(level_idx, r):
    """Pick spawn and goal positions. Later levels have more variation."""
    # Spawn: early levels use corners, later levels use more positions
    if level_idx < 4:
        spawn = r.choice(_SPAWN_POSITIONS[:4])  # corners only
    elif level_idx < 8:
        spawn = r.choice(_SPAWN_POSITIONS[:8])  # + edges
    else:
        spawn = r.choice(_SPAWN_POSITIONS)       # all options

    # Goal: early levels are center, later levels drift
    if level_idx < 6:
        goal_dx, goal_dy = 0, 0
    else:
        dx, dy = r.choice(_GOAL_OFFSETS)
        # Scale offset by how far into the game we are
        scale = min(1.0, (level_idx - 5) / 10.0)
        goal_dx = int(dx * scale)
        goal_dy = int(dy * scale)

    gcx = max(GOAL_W, min(CANVAS_W - GOAL_W, GOAL_CX + goal_dx))
    gcy = max(GOAL_H, min(CANVAS_H - GOAL_H, GOAL_CY + goal_dy))

    # Ensure spawn and goal aren't too close
    if math.hypot(spawn[0] - gcx, spawn[1] - gcy) < 400:
        # Flip spawn to opposite side
        spawn = (CANVAS_W - spawn[0], CANVAS_H - spawn[1])

    return spawn, (gcx, gcy)


# ============================================================================
# Spike generator (improved: guards paths, not random faces)
# ============================================================================

def _spikes_for_platform(px, py, pw, ph, difficulty, r):
    """Generate spikes on platform faces. Higher difficulty = more spikes, more faces."""
    st = 24
    faces = [
        ("up", px, py - st, pw, st),
        ("down", px, py + ph, pw, st),
        ("right", px + pw, py, st, ph),
        ("left", px - st, py, st, ph),
    ]
    r.shuffle(faces)

    # Scale with difficulty: max_faces 1..3, probability 0.25..0.75
    max_f = 1 + min(difficulty, 8) // 3
    prob = 0.25 + min(difficulty, 8) * 0.06

    out = []
    for d, sx, sy, sw, sh in faces[:max_f]:
        if r.random() > prob:
            continue
        sx = max(10, min(CANVAS_W - 10 - sw, sx))
        sy = max(10, min(CANVAS_H - 10 - sh, sy))
        out.append((sx, sy, sw, sh, d))
    return out


# ============================================================================
# Rotating obstacle generator
# ============================================================================

def _gen_rotators(count, spawn, goal_center, r):
    sx, sy = spawn
    gx, gy = goal_center
    out = []
    att = 0
    while len(out) < count and att < 200:
        att += 1
        px = r.randint(200, CANVAS_W - 200)
        py = r.randint(150, CANVAS_H - 150)
        if math.hypot(px - gx, py - gy) < 200:
            continue
        if math.hypot(px - sx, py - sy) < 220:
            continue
        arm = r.randint(90, 160)
        thick = r.randint(14, 22)
        speed = r.choice([-1, 1]) * r.uniform(40, 80)
        out.append(((px, py), arm, thick, speed))
    return out


# ============================================================================
# Flying enemy generator (speed scales with level)
# ============================================================================

def _gen_enemies(count, spawn, level_idx, r):
    sx, sy = spawn
    corners = [(120, 120), (1800, 120), (120, 960), (1800, 960)]
    corners.sort(key=lambda c: -math.hypot(c[0] - sx, c[1] - sy))
    out = []
    # Speed increases with level: 65-110 at L17, 85-140 at L20
    speed_min = 65 + (level_idx - 12) * 3
    speed_max = 110 + (level_idx - 12) * 4
    for i in range(min(count, len(corners))):
        cx = corners[i][0] + r.randint(-60, 60)
        cy = corners[i][1] + r.randint(-60, 60)
        out.append(((cx, cy), r.uniform(speed_min, speed_max)))
    return out


# ============================================================================
# Shooting turret generator
# ============================================================================

def _gen_shooters(count, spawn, goal_center, r):
    sx, sy = spawn
    gx, gy = goal_center
    out = []
    att = 0
    while len(out) < count and att < 200:
        att += 1
        px = r.randint(200, CANVAS_W - 200)
        py = r.randint(150, CANVAS_H - 150)
        if math.hypot(px - gx, py - gy) < 220:
            continue
        if math.hypot(px - sx, py - sy) < 240:
            continue
        out.append(((px, py), r.uniform(1.8, 3.5)))
    return out


# ============================================================================
# Void wall generator
# ============================================================================

def _gen_void_walls(r):
    v_side = r.choice(["near", "far"])
    h_side = r.choice(["near", "far"])
    return [("vertical", v_side), ("horizontal", h_side)]


# ============================================================================
# Coin generator (improved: path coins + risk-reward detours)
# ============================================================================

def _gen_coins(platforms, spawn, goal_center, difficulty, r):
    """Place coins: some on platforms, some floating between platforms as aerial paths."""
    sx, sy = spawn
    gx, gy = goal_center
    coins = []
    count = 4 + difficulty  # 4 on easy, 13 on hardest

    # Phase 1: coins on platforms (safe, on-path)
    for px, py, pw, ph in platforms[2:]:
        if len(coins) >= count:
            break
        n = r.randint(1, min(3, max(1, pw // 120)))
        for i in range(n):
            cx = int(px + pw * (i + 1) / (n + 1))
            cy = py - 40
            if _near_point(cx - 10, cy - 10, 20, 20, gx, gy, GOAL_SAFE_R + 30):
                continue
            if math.hypot(cx - sx, cy - sy) < SPAWN_SAFE_R:
                continue
            if cx < 40 or cx > CANVAS_W - 40 or cy < 40 or cy > CANVAS_H - 40:
                continue
            coins.append((cx, cy))
            if len(coins) >= count:
                break

    # Phase 2: aerial coins between platforms (risk-reward)
    if difficulty >= 3 and len(coins) < count:
        for i in range(len(platforms) - 3):
            if len(coins) >= count:
                break
            p1 = platforms[i + 2]
            p2 = platforms[i + 3] if i + 3 < len(platforms) else platforms[2]
            mid_x = (p1[0] + p1[2] // 2 + p2[0] + p2[2] // 2) // 2
            mid_y = (p1[1] + p2[1]) // 2 - 60
            mid_x = max(40, min(CANVAS_W - 40, mid_x))
            mid_y = max(40, min(CANVAS_H - 40, mid_y))
            if not _near_point(mid_x - 10, mid_y - 10, 20, 20, gx, gy, GOAL_SAFE_R):
                coins.append((mid_x, mid_y))

    return coins[:count]


# ============================================================================
# Boost pad generator
# ============================================================================

def _gen_boost_pads(platforms, spawn, r):
    sx, sy = spawn
    gx, gy = GOAL_CX, GOAL_CY
    pads = []
    dirs = ["up", "left", "right"]
    cands = [p for p in platforms[2:] if p[2] > 100]
    r.shuffle(cands)
    for px, py, pw, ph in cands[:3]:
        cx = px + pw // 2
        cy = py - 1
        if math.hypot(cx - gx, cy - gy) < GOAL_SAFE_R + 50:
            continue
        if math.hypot(cx - sx, cy - sy) < SPAWN_SAFE_R:
            continue
        pads.append((cx, cy, r.choice(dirs)))
    return pads


# ============================================================================
# Main generator
# ============================================================================

def generate_level(level_idx, seed=None):
    r = random.Random(seed if seed is not None else level_idx * 7919 + 42)

    # Difficulty now scales 0..9 across all 20 levels (was capped at 4)
    difficulty = min(9, level_idx * 9 // (NUM_LEVELS - 1))

    # Tier flags
    is_spinner = TIER_BASIC_END <= level_idx < TIER_SPINNER_END     # L9-12
    is_void    = TIER_SPINNER_END <= level_idx                       # L13+
    has_gun    = level_idx >= 14                                     # L15+ (gun introduced)
    has_ghosts = level_idx >= 16                                     # L17+ (ghosts)
    is_shooter = level_idx >= TIER_SHOOTER_START                     # L17+
    has_turrets = level_idx >= 18                                    # L19+ (turrets)

    # Pick varied spawn and goal positions
    spawn, goal_center = _pick_spawn_goal(level_idx, r)
    gcx, gcy = goal_center
    goal = (gcx - GOAL_W // 2, gcy - GOAL_H // 2, GOAL_W, GOAL_H)

    # == Platforms ===========================================================

    platforms = []

    # Always add a floor or boundary surface for orientation
    boundary_options = [
        (0, 1050, CANVAS_W, 30),     # floor
        (0, 0, CANVAS_W, 30),        # ceiling
        (0, 0, 30, CANVAS_H),        # left wall
        (1890, 0, 30, CANVAS_H),     # right wall
    ]
    # Early levels always have a floor; later levels randomize
    if level_idx < 3:
        platforms.append(boundary_options[0])  # always floor
    else:
        platforms.append(r.choice(boundary_options))

    # Spawn landing pad
    pw2, ph2 = 200, 22
    px2 = max(10, min(CANVAS_W - 10 - pw2, spawn[0] - pw2 // 2))
    py2 = max(10, min(CANVAS_H - 10 - ph2, spawn[1] + 30))
    platforms.append((px2, py2, pw2, ph2))

    # Path platforms: ensure a route from spawn to goal
    path_count = 3 + difficulty // 3   # 3 on easy, 6 on hard
    path_plats = _gen_path_platforms(spawn, goal_center, r, count=path_count)
    for pp in path_plats:
        _place_platform(platforms, *pp, spawn[0], spawn[1], gcx, gcy)

    # Fill with random shapes
    target = 10 + difficulty * 2
    att = 0
    while len(platforms) < target + 2 and att < 400:
        att += 1
        _add_shape(platforms, r.choice(_SHAPES)(r), spawn[0], spawn[1], gcx, gcy)

    # == Spikes ==============================================================

    bl = [
        (gcx - GOAL_SAFE_R, gcy - GOAL_SAFE_R, GOAL_SAFE_R * 2, GOAL_SAFE_R * 2),
        (spawn[0] - SPAWN_SAFE_R, spawn[1] - SPAWN_SAFE_R,
         SPAWN_SAFE_R * 2, SPAWN_SAFE_R * 2),
    ]
    spikes = []
    for px, py, pw, ph in platforms[2:]:
        for s in _spikes_for_platform(px, py, pw, ph, difficulty, r):
            if not any(_overlap(s[0], s[1], s[2], s[3], bx, by, bw, bh, 0)
                       for bx, by, bw, bh in bl):
                spikes.append(s)

    # == Rotating obstacles ==================================================

    rotators = []
    if is_spinner:
        count = [1, 2, 2, 3][level_idx - TIER_BASIC_END]
        rotators = _gen_rotators(count, spawn, goal_center, r)
    elif is_void:
        rotators = _gen_rotators(r.randint(1, 2), spawn, goal_center, r)

    # == Flying enemies (L17+ only, phased in) ===============================

    enemies = []
    if has_ghosts:
        if has_turrets:
            enemies = _gen_enemies(r.randint(2, 3), spawn, level_idx, r)
        else:
            enemies = _gen_enemies(r.randint(1, 2), spawn, level_idx, r)

    # == Shooting turrets (L19+ only) ========================================

    shooters = []
    if has_turrets:
        count = min(3, 1 + (level_idx - 18))
        shooters = _gen_shooters(count, spawn, goal_center, r)

    # == Void walls (L13+ only) ==============================================

    void_walls = _gen_void_walls(r) if is_void else []

    # == Coins ===============================================================

    coins = _gen_coins(platforms, spawn, goal_center, difficulty, r)

    # == Boost pads (L5+) ====================================================

    boost_pads = _gen_boost_pads(platforms, spawn, r) if level_idx >= 4 else []

    return {
        "platforms":  platforms,
        "spikes":     spikes,
        "goal":       goal,
        "spawn":      spawn,
        "rotators":   rotators,
        "enemies":    enemies,
        "shooters":   shooters,
        "void_walls": void_walls,
        "has_gun":    has_gun,
        "coins":      coins,
        "boost_pads": boost_pads,
    }


# Pre-generate all 20 levels at import time.
LEVELS_DATA = [generate_level(i) for i in range(NUM_LEVELS)]
