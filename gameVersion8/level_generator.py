"""
level_generator.py  –  Procedural generator for all 20 levels.

Tier layout
-----------
L01-08  BASIC     : platforms + spikes
L09-12  SPINNERS  : + up to 3 rotating obstacles
L13-20  VOID      : + secret void walls + player gun (3 shots/level)
L17-20  HAUNTED+  : void tier also gets flying ghosts + shooting turrets
"""

import math, random
from settings import (
    CANVAS_W, CANVAS_H,
    GOAL_W, GOAL_H, GOAL_CX, GOAL_CY,
    GOAL_SAFE_R, SPAWN_SAFE_R,
    NUM_LEVELS,
    TIER_BASIC_END, TIER_SPINNER_END, TIER_VOID_END, TIER_SHOOTER_START,
)

# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _overlap(ax,ay,aw,ah,bx,by,bw,bh,margin=20):
    return ax-margin<bx+bw and ax+aw+margin>bx and ay-margin<by+bh and ay+ah+margin>by

def _near_centre(x,y,w,h,safe_r=GOAL_SAFE_R):
    return math.hypot(x+w/2-GOAL_CX, y+h/2-GOAL_CY) < safe_r

def _near_spawn(x,y,w,h,sx,sy,safe_r=SPAWN_SAFE_R):
    return math.hypot(x+w/2-sx, y+h/2-sy) < safe_r

def _place_platform(existing, x,y,w,h, sx,sy):
    if _near_centre(x,y,w,h): return False
    if _near_spawn(x,y,w,h,sx,sy): return False
    mg = 40
    if x<mg or y<mg or x+w>CANVAS_W-mg or y+h>CANVAS_H-mg: return False
    for ex,ey,ew,eh in existing:
        if _overlap(x,y,w,h,ex,ey,ew,eh): return False
    existing.append((x,y,w,h))
    return True

def _add_shape(platforms, shape, sx, sy):
    tmp = list(platforms)
    for piece in shape:
        if not _place_platform(tmp, *piece, sx, sy): return False
    platforms.clear(); platforms.extend(tmp); return True

# ─────────────────────────────────────────────────────────────────────────────
# Shape generators
# ─────────────────────────────────────────────────────────────────────────────

def _rand_slab(r):
    w=r.randint(120,340); h=r.randint(18,28)
    return [(r.randint(60,CANVAS_W-60-w), r.randint(80,CANVAS_H-80-h), w, h)]

def _rand_pillar(r):
    w=r.randint(18,30); h=r.randint(100,260)
    return [(r.randint(60,CANVAS_W-60-w), r.randint(80,CANVAS_H-80-h), w, h)]

def _rand_L(r):
    w1=r.randint(160,280); h1=22; w2=22; h2=r.randint(80,180)
    x=r.randint(60,CANVAS_W-60-w1); y=r.randint(80,CANVAS_H-80-h1-h2)
    if r.choice([True,False]): return [(x,y,w1,h1),(x+w1-w2,y+h1,w2,h2)]
    return [(x,y,w1,h1),(x,y+h1,w2,h2)]

def _rand_T(r):
    w1=r.randint(180,300); h1=22; w2=22; h2=r.randint(60,140)
    x=r.randint(60,CANVAS_W-60-w1); y=r.randint(80,CANVAS_H-80-h1-h2)
    return [(x,y,w1,h1),(x+w1//2-w2//2,y+h1,w2,h2)]

def _rand_staircase(r):
    sw=r.randint(90,150); sh=20
    dx=r.choice([-1,1])*r.randint(60,100); dy=r.randint(60,120)
    x0=r.randint(200,CANVAS_W-200-sw); y0=r.randint(200,CANVAS_H-200-sh)
    return [(x0+dx*i, y0+dy*i, sw, sh) for i in range(3)]

def _rand_U(r):
    bw=r.randint(160,260); bh=20; wh=r.randint(80,160); ww=20
    x=r.randint(80,CANVAS_W-80-bw); y=r.randint(80,CANVAS_H-80-bh-wh)
    return [(x,y+wh,bw,bh),(x,y,ww,wh),(x+bw-ww,y,ww,wh)]

def _rand_ring(r):
    sz=r.randint(160,260); t=18
    x=r.randint(80,CANVAS_W-80-sz); y=r.randint(80,CANVAS_H-80-sz)
    return [(x,y,sz,t),(x,y+sz-t,sz,t),(x,y+t,t,sz-2*t),(x+sz-t,y+t,t,sz-2*t)]

def _rand_cross(r):
    arm=r.randint(100,180); t=22
    x=r.randint(100,CANVAS_W-100-arm); y=r.randint(100,CANVAS_H-100-arm)
    return [(x,y+arm//2-t//2,arm,t),(x+arm//2-t//2,y,t,arm)]

_SHAPES = [_rand_slab,_rand_slab,_rand_slab,_rand_pillar,
           _rand_L,_rand_T,_rand_staircase,_rand_U,_rand_ring,_rand_cross]

# ─────────────────────────────────────────────────────────────────────────────
# Spike generator
# ─────────────────────────────────────────────────────────────────────────────

def _spikes_for_platform(px,py,pw,ph,difficulty,r):
    st = 24
    faces = [("up",px,py-st,pw,st), ("down",px,py+ph,pw,st),
             ("right",px+pw,py,st,ph), ("left",px-st,py,st,ph)]
    r.shuffle(faces)
    max_f = 1 + difficulty//2
    prob  = 0.35 + difficulty*0.10
    out = []
    for d,sx,sy,sw,sh in faces[:max_f]:
        if r.random() > prob: continue
        sx = max(10, min(CANVAS_W-10-sw, sx))
        sy = max(10, min(CANVAS_H-10-sh, sy))
        out.append((sx,sy,sw,sh,d))
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Rotating obstacle generator
# ─────────────────────────────────────────────────────────────────────────────

def _gen_rotators(count, spawn, r):
    sx,sy = spawn; out=[]; att=0
    while len(out)<count and att<200:
        att+=1
        px=r.randint(200,CANVAS_W-200); py=r.randint(150,CANVAS_H-150)
        if math.hypot(px-GOAL_CX,py-GOAL_CY) < 200: continue
        if math.hypot(px-sx,py-sy) < 220: continue
        arm   = r.randint(90,160)
        thick = r.randint(14,22)
        speed = r.choice([-1,1]) * r.uniform(40,80)
        out.append(((px,py), arm, thick, speed))
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Flying enemy generator  (behaviour randomised inside FlyingEnemy.__init__)
# ─────────────────────────────────────────────────────────────────────────────

def _gen_enemies(count, spawn, r):
    sx,sy = spawn
    corners = [(120,120),(1800,120),(120,960),(1800,960)]
    corners.sort(key=lambda c: -math.hypot(c[0]-sx, c[1]-sy))
    out = []
    for i in range(min(count, len(corners))):
        cx = corners[i][0] + r.randint(-60,60)
        cy = corners[i][1] + r.randint(-60,60)
        out.append(((cx,cy), r.uniform(65,110)))
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Shooting turret generator
# ─────────────────────────────────────────────────────────────────────────────

def _gen_shooters(count, spawn, r):
    sx,sy = spawn; out=[]; att=0
    while len(out)<count and att<200:
        att+=1
        px=r.randint(200,CANVAS_W-200); py=r.randint(150,CANVAS_H-150)
        if math.hypot(px-GOAL_CX,py-GOAL_CY) < 220: continue
        if math.hypot(px-sx,py-sy) < 240: continue
        out.append(((px,py), r.uniform(1.8,3.5)))
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Void wall generator
# ─────────────────────────────────────────────────────────────────────────────

def _gen_void_walls(r):
    """
    Always returns exactly 2 edge portals:
      • one vertical   wall: either the left edge ("near") or right edge ("far")
      • one horizontal wall: either the top edge  ("near") or bottom edge ("far")
    """
    v_side = r.choice(["near", "far"])
    h_side = r.choice(["near", "far"])
    return [("vertical", v_side), ("horizontal", h_side)]

# ─────────────────────────────────────────────────────────────────────────────
# Coin generator
# ─────────────────────────────────────────────────────────────────────────────

def _gen_coins(platforms, spawn, difficulty, r):
    """Place coins floating above platforms. Returns list of (cx, cy) canvas coords."""
    sx, sy = spawn
    coins  = []
    count  = 4 + difficulty * 2   # 4 on easy, 12 on hard
    for px, py, pw, ph in platforms[2:]:   # skip boundary slab + spawn platform
        if len(coins) >= count:
            break
        # Place 1-3 coins along the top of this platform
        n = r.randint(1, min(3, max(1, pw // 120)))
        for i in range(n):
            cx = int(px + pw * (i + 1) / (n + 1))
            cy = py - 40   # float 40px above platform surface
            # Safety: not too close to goal or spawn
            if math.hypot(cx - GOAL_CX, cy - GOAL_CY) < GOAL_SAFE_R + 30:
                continue
            if math.hypot(cx - sx, cy - sy) < SPAWN_SAFE_R:
                continue
            if cx < 40 or cx > CANVAS_W - 40 or cy < 40 or cy > CANVAS_H - 40:
                continue
            coins.append((cx, cy))
            if len(coins) >= count:
                break
    return coins

# ─────────────────────────────────────────────────────────────────────────────
# Boost pad generator
# ─────────────────────────────────────────────────────────────────────────────

def _gen_boost_pads(platforms, spawn, r):
    """Place speed-boost arrow pads on platform surfaces.
    Returns list of (cx, cy, direction) where direction is 'up'|'down'|'left'|'right'.
    """
    sx, sy = spawn
    pads   = []
    dirs   = ["up", "left", "right"]   # 'down' is rare / only on ceiling platforms
    cands  = [p for p in platforms[2:] if p[2] > 100]   # wide enough platforms only
    r.shuffle(cands)
    for px, py, pw, ph in cands[:3]:   # at most 3 pads per level
        cx = px + pw // 2
        cy = py - 1   # sit on top surface
        if math.hypot(cx - GOAL_CX, cy - GOAL_CY) < GOAL_SAFE_R + 50:
            continue
        if math.hypot(cx - sx, cy - sy) < SPAWN_SAFE_R:
            continue
        pads.append((cx, cy, r.choice(dirs)))
    return pads

# ─────────────────────────────────────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_level(level_idx, seed=None):
    r          = random.Random(seed if seed is not None else level_idx*7919+42)
    difficulty = min(level_idx, 4)

    is_spinner  = TIER_BASIC_END    <= level_idx < TIER_SPINNER_END   # L09-12
    is_void     = TIER_SPINNER_END  <= level_idx < TIER_VOID_END      # L13-20
    is_shooter  = level_idx >= TIER_SHOOTER_START                     # L17-20

    goal  = (GOAL_CX-GOAL_W//2, GOAL_CY-GOAL_H//2, GOAL_W, GOAL_H)
    spawn = r.choice([(80,80),(1840,80),(80,1000),(1840,1000)])

    # ── Platforms ──────────────────────────────────────────────────────────
    platforms = []
    brects = {
        "floor":   (0,    1050, CANVAS_W, 30),
        "ceiling": (0,    0,    CANVAS_W, 30),
        "left":    (0,    0,    30,       CANVAS_H),
        "right":   (1890, 0,    30,       CANVAS_H),
    }
    platforms.append(brects[r.choice(list(brects.keys()))])
    pw2,ph2 = 200,22
    px2 = max(10, min(CANVAS_W-10-pw2, spawn[0]-pw2//2))
    py2 = max(10, min(CANVAS_H-10-ph2, spawn[1]+30))
    platforms.append((px2,py2,pw2,ph2))
    target=10+difficulty*2; att=0
    while len(platforms)<target+2 and att<400:
        att+=1; _add_shape(platforms, r.choice(_SHAPES)(r), spawn[0], spawn[1])

    # ── Spikes ─────────────────────────────────────────────────────────────
    bl = [
        (GOAL_CX-GOAL_SAFE_R, GOAL_CY-GOAL_SAFE_R, GOAL_SAFE_R*2, GOAL_SAFE_R*2),
        (spawn[0]-SPAWN_SAFE_R, spawn[1]-SPAWN_SAFE_R, SPAWN_SAFE_R*2, SPAWN_SAFE_R*2),
    ]
    spikes = []
    for px,py,pw,ph in platforms[2:]:
        for s in _spikes_for_platform(px,py,pw,ph,difficulty,r):
            if not any(_overlap(s[0],s[1],s[2],s[3],bx,by,bw,bh,0) for bx,by,bw,bh in bl):
                spikes.append(s)

    # ── Rotating obstacles ─────────────────────────────────────────────────
    rotators = []
    if is_spinner:
        # L09→1, L10→2, L11→2, L12→3
        count = [1,2,2,3][level_idx - TIER_BASIC_END]
        rotators = _gen_rotators(count, spawn, r)
    elif is_void:
        # Keep 1-2 rotators throughout void tier for continuity
        rotators = _gen_rotators(r.randint(1,2), spawn, r)

    # ── Flying enemies (void tier L13-20, more from L17) ───────────────────
    enemies = []
    if is_void:
        if is_shooter:
            # L17-20: 2-3 flying ghosts
            enemies = _gen_enemies(r.randint(2,3), spawn, r)
        else:
            # L13-16: 1-2 flying ghosts (lighter)
            enemies = _gen_enemies(r.randint(1,2), spawn, r)

    # ── Shooting turrets (L17-20 only) ────────────────────────────────────
    shooters = []
    if is_shooter:
        # L17→1, L18→2, L19→2, L20→3
        count = [1,2,2,3][level_idx - TIER_SHOOTER_START]
        shooters = _gen_shooters(count, spawn, r)

    # ── Void walls: L13-20 only (void tier), always 1 vertical + 1 horizontal ─
    void_walls = _gen_void_walls(r) if is_void else []

    # ── Player gun (L13-20) ───────────────────────────────────────────────
    has_gun = is_void

    # ── Coins (all levels) ────────────────────────────────────────────────
    coins = _gen_coins(platforms, spawn, difficulty, r)

    # ── Boost pads (L05+ to keep early levels clean) ─────────────────────
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