"""
game.py  –  Core game state and update logic. Zero pygame.draw calls.

Fixes applied:
  - Unlimited ammo (ammo = -1 means infinite; never decrements)
  - Wall contact ONLY restores jumps when gravity pushes INTO that wall
    (touching the left wall while gravity pulls RIGHT restores jumps,
     but touching the left wall when gravity pulls DOWN does NOT)
  - _move_x resets on_ground=False only when actually moving so _move_y
    ground state isn't wiped on the same frame
  - Spike collision uses a tighter shrink=6 so near-misses feel fair
  - respawn_with_chaos preserves jumps_left=2 after reload
  - Dead enemies / turrets no longer block player projectiles
  - Enemy hit-cooldown resets properly on level reload
"""

import math
import math
import random
import pygame
from settings import (
    SW, SH, BG_COLORS,
    GRAVITY_DIRS, GRAVITY_STRENGTH, NUM_LEVELS,
    GUN_PROJ_SPEED,
)
from utils import scale_rect, scale_pt
from particles import Particle, Flash
from level_generator import LEVELS_DATA
from enemies import (RotatingObstacle, FlyingEnemy,
                     ShootingEnemy, VoidWall, PlayerProjectile)

# Sentinel for unlimited ammo
_UNLIMITED = -1

# Minimum time between shots (prevents accidental double-fire)
_SHOOT_COOLDOWN = 0.15


class Game:
    def __init__(self):
        self.reset_all()

    # ─────────────────────────────────────────────────────────────── init ──

    def reset_all(self):
        self.level_idx    = 0
        self.hearts       = 10
        self.total_deaths = 0
        self.state        = "play"
        self.gravity_dir  = (0, 1)
        self.walls_deadly = False
        self.bg_color_idx = 0
        self.particles    = []
        self.flashes      = []
        self.mouse_pos    = (SW // 2, SH // 2)
        self._shoot_timer = 0.0
        # Wow-moment state
        self.screen_shake   = 0.0   # seconds remaining
        self.shake_strength = 0
        self.trail_points   = []    # [(x, y, age, color)] for rainbow trail
        self.slowmo_timer   = 0.0   # seconds of slow-motion remaining
        self.portal_streak  = 0     # consecutive teleports for escalating fx
        self.load_level()

    def start_at(self, level_idx):
        self.reset_all()
        self.level_idx = level_idx
        self.load_level()

    def load_level(self):
        data = LEVELS_DATA[self.level_idx % NUM_LEVELS]

        self.platforms = [pygame.Rect(*scale_rect(p)) for p in data["platforms"]]
        self.spikes    = [(pygame.Rect(*scale_rect(s[:4])), s[4])
                          for s in data["spikes"]]
        self.goal_rect = pygame.Rect(*scale_rect(data["goal"]))

        sx, sy = scale_pt(data["spawn"])
        self.ball_r     = int(22 * SW / 1920)
        self.bx         = float(sx)
        self.by         = float(sy)
        self.bvx        = 0.0
        self.bvy        = 0.0
        self.on_ground  = False
        self.jumps_left = 2

        # Rotating obstacles
        self.rotators = [RotatingObstacle(p, al, at, sp)
                         for p, al, at, sp in data.get("rotators", [])]

        # Flying enemies – fresh random behaviour each load
        self.enemies = [FlyingEnemy(pos, spd)
                        for pos, spd in data.get("enemies", [])]

        # Shooting turrets + their live projectiles
        self.shooters          = [ShootingEnemy(pos, fi)
                                   for pos, fi in data.get("shooters", [])]
        self.enemy_projectiles = []

        # Void walls – new format: (orientation, side)
        raw_vw = data.get("void_walls", [])
        self.void_walls = [VoidWall(ori, side) for ori, side in raw_vw]
        # Link partners so cooldown syncs on both sides
        vert  = [vw for vw in self.void_walls if vw.is_vertical]
        horiz = [vw for vw in self.void_walls if not vw.is_vertical]
        for vw in vert:
            vw.set_partner(vert[0] if len(vert) > 1 else vw)
        for vw in horiz:
            vw.set_partner(horiz[0] if len(horiz) > 1 else vw)

        # Player gun – UNLIMITED ammo on gun levels
        self.has_gun            = data.get("has_gun", False)
        self.ammo               = _UNLIMITED if self.has_gun else 0
        self.player_projectiles = []

        self.particles = []
        self.flashes   = []

    # ──────────────────────────────────────────────────── death / damage ──

    def respawn_with_chaos(self):
        """Full death: lose heart, randomise gravity + wall mode, reload level."""
        self.total_deaths += 1
        self.hearts       -= 1
        for _ in range(40):
            self.particles.append(Particle(self.bx, self.by, (255, 80, 50)))
        self.flashes.append(Flash((255, 60, 60), 0.4))
        if self.hearts <= 0:
            self.state = "game_over"
            return

        old_gravity      = self.gravity_dir
        self.gravity_dir = random.choice(GRAVITY_DIRS)

        # Disable deadly walls whenever gravity changes (fairness)
        if old_gravity != self.gravity_dir:
            self.walls_deadly = False
        elif random.random() < 0.4:
            self.walls_deadly = not self.walls_deadly

        self.bg_color_idx = (self.bg_color_idx + 1) % len(BG_COLORS)
        self.load_level()
        # Ensure jump counter is fresh after respawn
        self.jumps_left = 2

    def lose_heart(self):
        """Partial damage (enemy contact / projectile hit): lose 1 heart."""
        self.hearts -= 1
        self.flashes.append(Flash((180, 0, 200), 0.35))
        for _ in range(20):
            self.particles.append(Particle(self.bx, self.by, (200, 80, 255)))
        if self.hearts <= 0:
            self.state = "game_over"

    # ───────────────────────────────────────────────────────── events ──

    def handle_events(self):
        # Always track mouse position for the crosshair renderer
        self.mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit

            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_ESCAPE:
                    pygame.quit(); raise SystemExit

                # Restart / menu
                if k == pygame.K_r and self.state in ("game_over", "win"):
                    self.reset_all(); return

                # Advance level
                if k == pygame.K_RETURN and self.state == "level_clear":
                    self.level_idx += 1
                    if self.level_idx >= NUM_LEVELS:
                        self.state = "win"
                    else:
                        self.state = "play"
                        self.load_level()

                if self.state != "play":
                    continue

                # ── Jump ──────────────────────────────────────────────────
                # SPACE always works.  The "against-gravity" direction key
                # also triggers a jump so players feel natural in any gravity.
                gx, gy    = self.gravity_dir
                jump_keys = [pygame.K_SPACE]
                if   gy > 0:  jump_keys += [pygame.K_w, pygame.K_UP]
                elif gy < 0:  jump_keys += [pygame.K_s, pygame.K_DOWN]
                elif gx > 0:  jump_keys += [pygame.K_a, pygame.K_LEFT]
                elif gx < 0:  jump_keys += [pygame.K_d, pygame.K_RIGHT]
                if k in jump_keys:
                    self._try_jump()

            # ── Shoot: left mouse click → fire toward crosshair ───────────
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "play" and self.has_gun:
                    self._try_shoot(event.pos)

    def _try_shoot(self, target_pos):
        """Fire one projectile toward target_pos if shoot cooldown allows."""
        if self._shoot_timer > 0:
            return
        mx, my = target_pos
        dx     = mx - self.bx
        dy     = my - self.by
        dist   = math.hypot(dx, dy)
        if dist < 1:
            return
        ndx = dx / dist
        ndy = dy / dist
        self.player_projectiles.append(
            PlayerProjectile(self.bx, self.by,
                             ndx * GUN_PROJ_SPEED,
                             ndy * GUN_PROJ_SPEED))
        self._shoot_timer = _SHOOT_COOLDOWN
        # Muzzle-flash particles
        for _ in range(8):
            p = Particle(self.bx, self.by, (255, 255, 100))
            p.vx *= 0.4; p.vy *= 0.4
            self.particles.append(p)

    def _try_jump(self):
        if self.jumps_left > 0:
            gx, gy          = self.gravity_dir
            self.bvx        -= gx * 700
            self.bvy        -= gy * 700
            self.jumps_left -= 1
            self.on_ground   = False
            if self.jumps_left == 0:   # second jump – puff effect
                for _ in range(18):
                    p = Particle(self.bx, self.by, (150, 200, 255))
                    p.vx *= 0.6; p.vy *= 0.6
                    self.particles.append(p)

    # ───────────────────────────────────────────────────────── update ──

    def update(self, dt):
        self._tick_effects(dt)
        if self.state != "play":
            return
        # Slow-motion: compress game dt during portal aftermath
        if self.slowmo_timer > 0:
            dt *= 0.25
        if self._shoot_timer > 0:
            self._shoot_timer = max(0.0, self._shoot_timer - dt)
        self._apply_movement(dt)
        self._apply_gravity(dt)
        self._cap_velocity()
        self._move_x(dt)
        self._move_y(dt)
        self._check_screen_walls()
        self._check_void_walls()
        self._check_spikes()
        self._check_rotators(dt)
        self._check_enemies(dt)
        self._check_shooters(dt)
        self._tick_player_projectiles(dt)
        self._check_goal()

    # ─────────────────────────────────────────────────────── physics ──

    def _apply_movement(self, dt):
        keys = pygame.key.get_pressed()
        gx, gy = self.gravity_dir
        a = 4000 * dt

        # WASD + Arrow keys always control movement; mouse handles shooting
        if gy != 0:  # vertical gravity → horizontal movement
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.bvx -= a
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.bvx += a
            self.bvx *= 0.80
        else:        # horizontal gravity → vertical movement
            if keys[pygame.K_UP]   or keys[pygame.K_w]: self.bvy -= a
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.bvy += a
            self.bvy *= 0.80

    def _apply_gravity(self, dt):
        gx, gy = self.gravity_dir
        self.bvx += gx * GRAVITY_STRENGTH * dt
        self.bvy += gy * GRAVITY_STRENGTH * dt

    def _cap_velocity(self):
        mv       = 1200
        self.bvx = max(-mv, min(mv, self.bvx))
        self.bvy = max(-mv, min(mv, self.bvy))

    def _move_x(self, dt):
        """Move horizontally and resolve platform collisions."""
        self.bx += self.bvx * dt
        rect     = self._ball_rect()
        gx, gy   = self.gravity_dir
        for p in self.platforms:
            if rect.colliderect(p):
                if self.bvx > 0:
                    self.bx = p.left - self.ball_r
                    # Only counts as "ground" if gravity pulls us rightward
                    if gx > 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                elif self.bvx < 0:
                    self.bx = p.right + self.ball_r
                    if gx < 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                self.bvx = 0
                rect = self._ball_rect()   # recalc after push-out

    def _move_y(self, dt):
        """Move vertically and resolve platform collisions."""
        self.by += self.bvy * dt
        rect     = self._ball_rect()
        gx, gy   = self.gravity_dir
        for p in self.platforms:
            if rect.colliderect(p):
                if self.bvy > 0:
                    self.by = p.top - self.ball_r
                    if gy > 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                elif self.bvy < 0:
                    self.by = p.bottom + self.ball_r
                    if gy < 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                self.bvy = 0
                rect = self._ball_rect()

    def _check_screen_walls(self):
        """Handle screen-edge collisions. Only restore jumps on the
        wall that gravity is actively pressing the ball against."""
        gx, gy = self.gravity_dir
        died   = False

        # Left wall
        if self.bx - self.ball_r < 0:
            self.bx  = float(self.ball_r)
            self.bvx = abs(self.bvx) * 0.4
            if gx < 0:   # gravity pulls left → left wall is the floor
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        # Right wall
        if self.bx + self.ball_r > SW:
            self.bx  = float(SW - self.ball_r)
            self.bvx = -abs(self.bvx) * 0.4
            if gx > 0:   # gravity pulls right → right wall is the floor
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        # Top wall
        if self.by - self.ball_r < 0:
            self.by  = float(self.ball_r)
            self.bvy = abs(self.bvy) * 0.4
            if gy < 0:   # gravity pulls up → ceiling is the floor
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        # Bottom wall
        if self.by + self.ball_r > SH:
            self.by  = float(SH - self.ball_r)
            self.bvy = -abs(self.bvy) * 0.4
            if gy > 0:   # gravity pulls down → floor is the floor
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        if died:
            self.respawn_with_chaos()

    def _check_void_walls(self):
        for vw in self.void_walls:
            result = vw.check_teleport(self.bx, self.by, self.ball_r)
            if result:
                old_x, old_y = self.bx, self.by
                self.bx, self.by = float(result[0]), float(result[1])

                # ── WOW MOMENT ───────────────────────────────────────────
                self.portal_streak  += 1
                intensity            = min(self.portal_streak, 4)

                # Screen shake proportional to streak
                self.screen_shake   = 0.18 + 0.06 * intensity
                self.shake_strength = 6   + 4    * intensity

                # Brief slow-motion after portal (time dilation feel)
                self.slowmo_timer   = 0.12 + 0.04 * intensity

                # Burst of rainbow particles at BOTH exit and entry point
                rainbow_cols = [
                    (255, 60,  60),  (255, 160, 30),
                    (255, 255, 40),  (60,  255, 80),
                    (40,  180, 255), (180, 60,  255),
                ]
                for _ in range(30 + 10 * intensity):
                    col = random.choice(rainbow_cols)
                    self.particles.append(Particle(old_x, old_y, col))
                for _ in range(30 + 10 * intensity):
                    col = random.choice(rainbow_cols)
                    self.particles.append(Particle(self.bx, self.by, col))

                # Flash colour cycles through rainbow on streak
                flash_col = rainbow_cols[(self.portal_streak - 1) % len(rainbow_cols)]
                self.flashes.append(Flash(flash_col, 0.20 + 0.05 * intensity))

                # Seed rainbow trail on the ball
                for i in range(12):
                    angle = random.uniform(0, 2 * math.pi)
                    dist  = random.uniform(0, self.ball_r * 2)
                    tx    = self.bx + math.cos(angle) * dist
                    ty    = self.by + math.sin(angle) * dist
                    col   = random.choice(rainbow_cols)
                    self.trail_points.append([tx, ty, 0.6, col])

                break   # only one teleport per frame

        # Decay streak if no teleport happened recently (handled via cooldowns)

    def _check_spikes(self):
        rect = self._ball_rect(shrink=6)   # tighter hitbox = fairer near-misses
        for sr, _ in self.spikes:
            if rect.colliderect(sr):
                self.respawn_with_chaos(); return

    def _check_rotators(self, dt):
        for rot in self.rotators:
            rot.update(dt)
            if rot.collides_with_ball(self.bx, self.by, self.ball_r):
                self.respawn_with_chaos(); return

    def _check_enemies(self, dt):
        for enemy in self.enemies:
            enemy.update(dt, self.bx, self.by)
            if enemy.try_hit(self.bx, self.by, self.ball_r):
                self.lose_heart()
                if self.state == "game_over": return
        # Player bullets vs flying enemies (skip dead projectiles/enemies)
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for enemy in self.enemies:
                if not enemy.alive: continue
                if proj.hits_enemy(enemy.x, enemy.y, enemy.RADIUS):
                    enemy.alive = False
                    proj.alive  = False
                    for _ in range(25):
                        self.particles.append(
                            Particle(enemy.x, enemy.y, (200, 80, 255)))
                    break   # one proj hits one enemy

    def _check_shooters(self, dt):
        for shooter in self.shooters:
            shooter.update(dt, self.bx, self.by)
            ep = shooter.try_fire()
            if ep:
                self.enemy_projectiles.append(ep)

        for ep in self.enemy_projectiles:
            ep.update(dt)
            if ep.hits_ball(self.bx, self.by, self.ball_r):
                ep.alive = False
                self.lose_heart()
                if self.state == "game_over": return

        # Player bullets vs turrets (skip dead)
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for shooter in self.shooters:
                if not shooter.alive: continue
                if proj.hits_enemy(shooter.x, shooter.y, shooter.RADIUS):
                    shooter.alive = False
                    proj.alive    = False
                    for _ in range(30):
                        self.particles.append(
                            Particle(shooter.x, shooter.y, (255, 60, 60)))
                    break

        self.enemy_projectiles = [ep for ep in self.enemy_projectiles if ep.alive]

    def _tick_player_projectiles(self, dt):
        for proj in self.player_projectiles:
            proj.update(dt)
        self.player_projectiles = [p for p in self.player_projectiles if p.alive]

    def _check_goal(self):
        if self._ball_rect(shrink=4).colliderect(self.goal_rect):
            self.state = "level_clear"
            self.flashes.append(Flash((50, 255, 150), 0.5))
            for _ in range(60):
                self.particles.append(
                    Particle(self.goal_rect.centerx,
                             self.goal_rect.centery, (50, 255, 150)))

    # ─────────────────────────────────────────────── effects / utility ──

    def _tick_effects(self, dt):
        self.particles = [p for p in self.particles if p.alive]
        for p  in self.particles:  p.update(dt)
        self.flashes   = [f for f in self.flashes if not f.done]
        for f  in self.flashes:    f.update(dt)
        for vw in self.void_walls: vw.update(dt)

        # Screen shake decay
        if self.screen_shake > 0:
            self.screen_shake = max(0.0, self.screen_shake - dt)

        # Slow-motion decay
        if self.slowmo_timer > 0:
            self.slowmo_timer = max(0.0, self.slowmo_timer - dt)

        # Rainbow trail – age each point, remove old ones
        for pt in self.trail_points:
            pt[2] -= dt * 1.8   # age faster
        self.trail_points = [pt for pt in self.trail_points if pt[2] > 0]

        # Seed new trail points at current ball position during active slowmo
        if self.slowmo_timer > 0 and self.state == "play":
            rainbow_cols = [
                (255, 60, 60), (255, 160, 30), (255, 255, 40),
                (60, 255, 80), (40, 180, 255), (180, 60, 255),
            ]
            self.trail_points.append(
                [self.bx, self.by, 0.45,
                 random.choice(rainbow_cols)])

        # Portal streak resets when all void wall cooldowns expire
        if all(vw.cooldown == 0 for vw in self.void_walls):
            self.portal_streak = 0

    def _ball_rect(self, shrink=0):
        r = self.ball_r - shrink
        return pygame.Rect(int(self.bx) - r, int(self.by) - r, r * 2, r * 2)