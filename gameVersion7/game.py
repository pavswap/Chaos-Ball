"""
game.py  --  Core game state and update logic. Zero pygame.draw calls.

Improvements:
  - Death freeze frame: brief pause on death for dramatic impact
  - Coyote time: 0.10s grace window to jump after walking off a ledge
  - Jump buffer: 0.12s input buffer so pressing jump slightly early still works
  - Ball squash & stretch: visual deformation on jump/land for juicy feel
  - Kill streak system: chain enemy kills for multiplied score + announcements
  - Floating score text: "+50" numbers that pop up and drift upward
  - Per-level death tracking for rank calculation
  - Proper on_ground tracking (reset each frame, set by collisions)
"""

import math
import random
import warnings
import pygame
from settings import (
    SW, SH, BG_COLORS,
    GRAVITY_DIRS, GRAVITY_STRENGTH, NUM_LEVELS,
    GUN_PROJ_SPEED,
    DASH_SPEED, DASH_DURATION, DASH_COOLDOWN,
    INVINCIBLE_DURATION,
    COYOTE_TIME, JUMP_BUFFER_TIME, DEATH_FREEZE_TIME, KILL_COMBO_WINDOW,
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


class _DummySound:
    """Fallback when a .wav file is missing."""
    def play(self): pass
    def set_volume(self, _v): pass


def _load_sound(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return _DummySound()


class Game:
    def __init__(self):
        self._init_sounds()
        self.reset_all()

    # ----------------------------------------------------------------- init --

    def _init_sounds(self):
        self.sounds = {
            "jump":       _load_sound("assets/sounds/Retro/jump.wav"),
            "shoot":      _load_sound("assets/sounds/Retro/throw.wav"),
            "coin":       _load_sound("assets/sounds/Retro/coin.wav"),
            "respawn":    _load_sound("assets/sounds/Retro/power_up.wav"),
            "hit":        _load_sound("assets/sounds/Retro/hurt.wav"),
            "level_clear":_load_sound("assets/sounds/Musical Effects/8_bit_level_complete.wav"),
            "boost":      _load_sound("assets/sounds/Other/whoosh_1.wav"),
            "enemy_hit":  _load_sound("assets/sounds/Retro/explosion_quick.wav"),
            "dash":       _load_sound("assets/sounds/Other/whoosh_2.wav"),
        }
        self.sounds["jump"].set_volume(0.3)
        self.sounds["shoot"].set_volume(0.2)
        self.sounds["coin"].set_volume(0.4)
        self.sounds["respawn"].set_volume(0.5)
        self.sounds["hit"].set_volume(0.3)
        self.sounds["level_clear"].set_volume(0.5)
        self.sounds["boost"].set_volume(0.4)
        self.sounds["enemy_hit"].set_volume(0.3)
        self.sounds["dash"].set_volume(0.3)

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
        self.screen_shake    = 0.0
        self.shake_strength  = 0
        self.trail_points    = []
        self.slowmo_timer    = 0.0
        self.portal_streak   = 0
        # Score / coins
        self.score           = 0
        self.coin_combo      = 0
        self.coin_combo_timer = 0.0
        self.combo_text      = ""
        # Level timer
        self.level_time      = 0.0
        self.best_times      = {}   # level_idx -> best seconds
        # Gravity announcement
        self.gravity_announce_timer = 0.0
        self.gravity_announce_text  = ""
        # Invincibility after respawn
        self.invincible_timer = 0.0
        # Dash
        self.dash_timer          = 0.0
        self.dash_cooldown_timer = 0.0

        # -- NEW: Coyote time + jump buffer --
        self.coyote_timer      = 0.0
        self.jump_buffer_timer = 0.0

        # -- NEW: Death freeze frame --
        self.freeze_timer   = 0.0
        self._pending_death = False

        # -- NEW: Kill streak --
        self.kill_streak       = 0
        self.kill_streak_timer = 0.0

        # -- NEW: Floating score texts [[x, y, text, color, timer]] --
        self.floating_texts = []

        # -- NEW: Ball squash/stretch (1.0 = circle) --
        self.squash = 1.0

        # -- NEW: Per-level stats for ranking --
        self.level_deaths        = 0
        self.total_enemies_killed = 0

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

        # Flying enemies -- fresh random behaviour each load
        self.enemies = [FlyingEnemy(pos, spd)
                        for pos, spd in data.get("enemies", [])]

        # Shooting turrets + their live projectiles
        self.shooters          = [ShootingEnemy(pos, fi)
                                   for pos, fi in data.get("shooters", [])]
        self.enemy_projectiles = []

        # Void walls -- new format: (orientation, side)
        raw_vw = data.get("void_walls", [])
        self.void_walls = [VoidWall(ori, side) for ori, side in raw_vw]
        # Link partners so cooldown syncs on both sides
        vert  = [vw for vw in self.void_walls if vw.is_vertical]
        horiz = [vw for vw in self.void_walls if not vw.is_vertical]
        for vw in vert:
            vw.set_partner(vert[0] if len(vert) > 1 else vw)
        for vw in horiz:
            vw.set_partner(horiz[0] if len(horiz) > 1 else vw)

        # Player gun -- UNLIMITED ammo on gun levels
        self.has_gun            = data.get("has_gun", False)
        self.ammo               = _UNLIMITED if self.has_gun else 0
        self.player_projectiles = []

        # Coins -- store already scaled to screen space
        self.coins = [[int(cx * SW / 1920), int(cy * SH / 1080), True]
                      for cx, cy in data.get("coins", [])]

        # Boost pads -- pre-scale to screen space
        self.boost_pads = [
            (int(cx * SW / 1920), int(cy * SH / 1080), direction)
            for cx, cy, direction in data.get("boost_pads", [])
        ]

        self.particles = []
        self.flashes   = []
        self.level_time = 0.0
        self.coin_combo = 0
        self.coin_combo_timer = 0.0
        self.coins_rewarded = False
        self.level_deaths = 0
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0

    # --------------------------------------------------- death / damage --

    def _trigger_death(self):
        """Phase 1: visual feedback + freeze. Level reloads after freeze ends."""
        self.total_deaths += 1
        self.level_deaths += 1
        self.hearts       -= 1
        self.sounds["respawn"].play()

        # Death burst particles at current position
        for _ in range(40):
            self.particles.append(Particle(self.bx, self.by, (255, 80, 50)))
        self.flashes.append(Flash((255, 60, 60), 0.4))

        if self.hearts <= 0:
            self.state = "game_over"
            return

        # Freeze the game briefly for dramatic impact
        self.freeze_timer   = DEATH_FREEZE_TIME
        self._pending_death = True

    def _execute_respawn(self):
        """Phase 2: randomise chaos + reload level (runs after freeze ends)."""
        self._pending_death = False

        old_gravity      = self.gravity_dir
        self.gravity_dir = random.choice(GRAVITY_DIRS)

        # Disable deadly walls whenever gravity changes (fairness)
        if old_gravity != self.gravity_dir:
            self.walls_deadly = False
            dir_names = {(0,1):"DOWN",(0,-1):"UP",(1,0):"RIGHT",(-1,0):"LEFT"}
            self.gravity_announce_text  = f"GRAVITY: {dir_names.get(self.gravity_dir,'?')}"
            self.gravity_announce_timer = 2.2
        elif random.random() < 0.4:
            self.walls_deadly = not self.walls_deadly

        self.bg_color_idx = (self.bg_color_idx + 1) % len(BG_COLORS)
        self.load_level()
        self.jumps_left = 2
        self.invincible_timer = INVINCIBLE_DURATION

    def lose_heart(self):
        """Partial damage (enemy contact / projectile hit): lose 1 heart."""
        if self.invincible_timer > 0 or self.dash_timer > 0:
            return
        self.hearts -= 1
        self.sounds["hit"].play()
        self.flashes.append(Flash((180, 0, 200), 0.35))
        for _ in range(20):
            self.particles.append(Particle(self.bx, self.by, (200, 80, 255)))
        if self.hearts <= 0:
            self.state = "game_over"

    # ----------------------------------------------------------- events --

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

                # Pause toggle
                if k == pygame.K_p and self.state in ("play", "pause"):
                    self.state = "pause" if self.state == "play" else "play"
                    continue

                if self.state != "play":
                    continue

                # -- Jump -----------------------------------------------
                gx, gy    = self.gravity_dir
                jump_keys = [pygame.K_SPACE]
                if   gy > 0:  jump_keys += [pygame.K_w, pygame.K_UP]
                elif gy < 0:  jump_keys += [pygame.K_s, pygame.K_DOWN]
                elif gx > 0:  jump_keys += [pygame.K_a, pygame.K_LEFT]
                elif gx < 0:  jump_keys += [pygame.K_d, pygame.K_RIGHT]
                if k in jump_keys:
                    self._try_jump()

                # -- Dash -----------------------------------------------
                if k in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._try_dash()

            # -- Shoot: left mouse click -> fire toward crosshair --------
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
        self.sounds["shoot"].play()
        # Muzzle-flash particles
        for _ in range(8):
            p = Particle(self.bx, self.by, (255, 255, 100))
            p.vx *= 0.4; p.vy *= 0.4
            self.particles.append(p)

    def _try_jump(self):
        can_jump = self.jumps_left > 0

        # Coyote time: recently walked off a ledge -> still allow first jump
        if not can_jump and self.coyote_timer > 0:
            can_jump = True
            self.jumps_left = 1      # grant one jump (air jump remains)
            self.coyote_timer = 0.0  # consume coyote grace

        if not can_jump:
            # Can't jump now -- buffer the input for when we land
            self.jump_buffer_timer = JUMP_BUFFER_TIME
            return

        gx, gy          = self.gravity_dir
        self.bvx        -= gx * 700
        self.bvy        -= gy * 700
        self.jumps_left -= 1
        self.on_ground   = False
        self.coyote_timer = 0.0     # cancel coyote on any jump
        self.sounds["jump"].play()

        # Squash: stretch tall on jump
        self.squash = 1.4

        if self.jumps_left == 0:   # second jump -- puff effect
            for _ in range(18):
                p = Particle(self.bx, self.by, (150, 200, 255))
                p.vx *= 0.6; p.vy *= 0.6
                self.particles.append(p)

    def _try_dash(self):
        if self.dash_cooldown_timer > 0:
            return
        keys = pygame.key.get_pressed()
        gx, gy = self.gravity_dir
        dx, dy = 0.0, 0.0
        if gy != 0:   # vertical gravity -> horizontal dash
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
        else:          # horizontal gravity -> vertical dash
            if keys[pygame.K_UP]   or keys[pygame.K_w]: dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1
        if dx == 0 and dy == 0:
            dx, dy = float(-gx), float(-gy)   # default: dash opposite gravity
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist; dy /= dist
        self.bvx = dx * DASH_SPEED
        self.bvy = dy * DASH_SPEED
        self.dash_timer          = DASH_DURATION
        self.dash_cooldown_timer = DASH_COOLDOWN
        self.sounds["dash"].play()
        # Dash burst particles
        for _ in range(15):
            p = Particle(self.bx, self.by, (100, 200, 255))
            p.vx *= 0.3; p.vy *= 0.3
            self.particles.append(p)
        self.flashes.append(Flash((100, 180, 255), 0.08))

    # ----------------------------------------------------------- update --

    def update(self, dt):
        self._tick_effects(dt)
        if self.state != "play":
            return

        # -- Death freeze frame: skip game logic, let particles render --
        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0 and self._pending_death:
                self._execute_respawn()
            return

        # Level timer
        self.level_time += dt
        # Slow-motion: compress game dt during portal aftermath
        if self.slowmo_timer > 0:
            dt *= 0.25
        if self._shoot_timer > 0:
            self._shoot_timer = max(0.0, self._shoot_timer - dt)
        if self.invincible_timer > 0:
            self.invincible_timer = max(0.0, self.invincible_timer - dt)
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer = max(0.0, self.dash_cooldown_timer - dt)
        if self.dash_timer > 0:
            self.dash_timer = max(0.0, self.dash_timer - dt)

        # -- Coyote timer decay --
        if self.coyote_timer > 0:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
            # When coyote time expires while airborne, consume one jump
            if self.coyote_timer <= 0 and not self.on_ground and self.jumps_left == 2:
                self.jumps_left = 1

        # -- Jump buffer decay --
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

        # Capture pre-move state for landing detection
        _prev_ground = self.on_ground
        _pre_speed   = math.hypot(self.bvx, self.bvy)

        # Reset on_ground each frame; collisions will re-set it
        self.on_ground = False

        # During dash: skip normal movement/gravity/cap (dash velocity drives)
        if self.dash_timer > 0:
            pass
        else:
            self._apply_movement(dt)
            self._apply_gravity(dt)
            self._cap_velocity()

        self._move_x(dt)
        self._move_y(dt)

        self._check_screen_walls()
        # Early out if death was triggered by wall check
        if self._pending_death or self.state != "play":
            return

        # -- Landing detection --
        just_landed = self.on_ground and not _prev_ground

        if just_landed:
            # Squash flat on landing
            self.squash = 0.6

            # Jump buffer: if jump was pressed recently, auto-trigger it
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0.0
                self._try_jump()

        # Landing impact particles
        if just_landed and _pre_speed > 500:
            strength = min(_pre_speed / 1200.0, 1.0)
            for _ in range(int(10 * strength)):
                p = Particle(self.bx, self.by, (150, 180, 220))
                p.vx *= 0.5; p.vy *= -0.3
                self.particles.append(p)
            if strength > 0.5:
                self.screen_shake   = 0.08 * strength
                self.shake_strength = int(4 * strength)

        # -- Coyote time: if just walked off a ledge (not jumped), grant grace --
        if _prev_ground and not self.on_ground and self.jumps_left == 2:
            self.coyote_timer = COYOTE_TIME

        self._check_void_walls()
        self._check_spikes()
        if self._pending_death or self.state != "play":
            return
        self._check_rotators(dt)
        if self._pending_death or self.state != "play":
            return
        self._check_coins()
        self._check_boost_pads()
        self._check_enemies(dt)
        if self.state != "play":
            return
        self._check_shooters(dt)
        if self.state != "play":
            return
        self._tick_player_projectiles(dt)
        self._check_goal()

    # --------------------------------------------------------- physics --

    def _apply_movement(self, dt):
        keys = pygame.key.get_pressed()
        gx, gy = self.gravity_dir
        a = 4000 * dt

        if gy != 0:  # vertical gravity -> horizontal movement
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.bvx -= a
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.bvx += a
            self.bvx *= 0.80
        else:        # horizontal gravity -> vertical movement
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
                    if gx > 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                elif self.bvx < 0:
                    self.bx = p.right + self.ball_r
                    if gx < 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                self.bvx = 0
                rect = self._ball_rect()

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
            if gx < 0:
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        # Right wall
        if self.bx + self.ball_r > SW:
            self.bx  = float(SW - self.ball_r)
            self.bvx = -abs(self.bvx) * 0.4
            if gx > 0:
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        # Top wall
        if self.by - self.ball_r < 0:
            self.by  = float(self.ball_r)
            self.bvy = abs(self.bvy) * 0.4
            if gy < 0:
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        # Bottom wall
        if self.by + self.ball_r > SH:
            self.by  = float(SH - self.ball_r)
            self.bvy = -abs(self.bvy) * 0.4
            if gy > 0:
                self.on_ground  = True
                self.jumps_left = 2
            if self.walls_deadly: died = True

        if died and self.invincible_timer <= 0 and self.dash_timer <= 0:
            self._trigger_death()

    def _check_void_walls(self):
        for vw in self.void_walls:
            result = vw.check_teleport(self.bx, self.by, self.ball_r)
            if result:
                old_x, old_y = self.bx, self.by
                self.bx, self.by = float(result[0]), float(result[1])

                # -- WOW MOMENT --
                self.portal_streak  += 1
                intensity            = min(self.portal_streak, 4)

                self.screen_shake   = 0.18 + 0.06 * intensity
                self.shake_strength = 6   + 4    * intensity
                self.slowmo_timer   = 0.12 + 0.04 * intensity

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

                flash_col = rainbow_cols[(self.portal_streak - 1) % len(rainbow_cols)]
                self.flashes.append(Flash(flash_col, 0.20 + 0.05 * intensity))

                for i in range(12):
                    angle = random.uniform(0, 2 * math.pi)
                    dist  = random.uniform(0, self.ball_r * 2)
                    tx    = self.bx + math.cos(angle) * dist
                    ty    = self.by + math.sin(angle) * dist
                    col   = random.choice(rainbow_cols)
                    self.trail_points.append([tx, ty, 0.6, col])

                break

    def _check_spikes(self):
        if self.invincible_timer > 0 or self.dash_timer > 0:
            return
        rect = self._ball_rect(shrink=6)
        for sr, _ in self.spikes:
            if rect.colliderect(sr):
                self._trigger_death(); return

    def _check_rotators(self, dt):
        for rot in self.rotators:
            rot.update(dt)
            if rot.collides_with_ball(self.bx, self.by, self.ball_r):
                if self.invincible_timer <= 0 and self.dash_timer <= 0:
                    self._trigger_death(); return

    def _check_enemies(self, dt):
        for enemy in self.enemies:
            enemy.update(dt, self.bx, self.by)
            if enemy.try_hit(self.bx, self.by, self.ball_r):
                self.lose_heart()
                if self.state == "game_over": return

        # Player bullets vs flying enemies
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for enemy in self.enemies:
                if not enemy.alive: continue
                if proj.hits_enemy(enemy.x, enemy.y, enemy.RADIUS):
                    enemy.alive = False
                    proj.alive  = False
                    self.sounds["enemy_hit"].play()
                    self.total_enemies_killed += 1

                    # Kill streak
                    self.kill_streak += 1
                    self.kill_streak_timer = KILL_COMBO_WINDOW
                    multiplier = min(self.kill_streak, 5)
                    points = 50 * multiplier
                    self.score += points

                    # Floating text
                    self.floating_texts.append(
                        [enemy.x, enemy.y, f"+{points}", (255, 220, 50), 1.0])
                    if self.kill_streak >= 2:
                        streak_names = {2:"DOUBLE KILL", 3:"TRIPLE KILL",
                                        4:"QUAD KILL", 5:"RAMPAGE"}
                        sname = streak_names.get(
                            self.kill_streak, f"x{self.kill_streak} STREAK")
                        self.floating_texts.append(
                            [enemy.x, enemy.y - 30, sname, (255, 100, 50), 1.8])

                    for _ in range(25):
                        self.particles.append(
                            Particle(enemy.x, enemy.y, (200, 80, 255)))
                    break

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

        # Player bullets vs turrets
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for shooter in self.shooters:
                if not shooter.alive: continue
                if proj.hits_enemy(shooter.x, shooter.y, shooter.RADIUS):
                    shooter.alive = False
                    proj.alive    = False
                    self.sounds["enemy_hit"].play()
                    self.total_enemies_killed += 1

                    # Kill streak
                    self.kill_streak += 1
                    self.kill_streak_timer = KILL_COMBO_WINDOW
                    multiplier = min(self.kill_streak, 5)
                    points = 75 * multiplier
                    self.score += points

                    self.floating_texts.append(
                        [shooter.x, shooter.y, f"+{points}", (255, 220, 50), 1.0])
                    if self.kill_streak >= 2:
                        streak_names = {2:"DOUBLE KILL", 3:"TRIPLE KILL",
                                        4:"QUAD KILL", 5:"RAMPAGE"}
                        sname = streak_names.get(
                            self.kill_streak, f"x{self.kill_streak} STREAK")
                        self.floating_texts.append(
                            [shooter.x, shooter.y - 30, sname, (255, 100, 50), 1.8])

                    for _ in range(30):
                        self.particles.append(
                            Particle(shooter.x, shooter.y, (255, 60, 60)))
                    break

        self.enemy_projectiles = [ep for ep in self.enemy_projectiles if ep.alive]

    def _tick_player_projectiles(self, dt):
        for proj in self.player_projectiles:
            proj.update(dt)
        self.player_projectiles = [p for p in self.player_projectiles if p.alive]

    def _check_coins(self):
        """Collect coins; build combo counter for bonus score."""
        COIN_R = int(14 * SW / 1920)
        for coin in self.coins:
            cx, cy, alive = coin
            if not alive:
                continue
            if math.hypot(self.bx - cx, self.by - cy) < self.ball_r + COIN_R:
                coin[2] = False
                self.coin_combo      += 1
                self.coin_combo_timer = 1.5
                points = 10 * self.coin_combo
                self.score += points
                self.sounds["coin"].play()

                # Visual burst
                gold = (255, 220, 40)
                for _ in range(16):
                    p = Particle(cx, cy, gold)
                    p.vx *= 0.7; p.vy *= 0.7
                    self.particles.append(p)

                # Floating text
                self.floating_texts.append(
                    [cx, cy, f"+{points}", (255, 220, 40), 1.0])

                # Combo text label
                if self.coin_combo >= 3:
                    self.combo_text = f"COMBO x{self.coin_combo}!  +{points}"
                else:
                    self.combo_text = f"+{points}"

        # All coins collected -> reward a heart
        if not self.coins_rewarded and self.coins and all(not c[2] for c in self.coins):
            self.coins_rewarded = True
            if self.hearts < 10:
                self.hearts += 1
                self.flashes.append(Flash((50, 255, 100), 0.35))
                for _ in range(30):
                    self.particles.append(
                        Particle(self.bx, self.by, (50, 255, 100)))

    def _check_boost_pads(self):
        """Launch ball when it touches a boost pad arrow."""
        BOOST_SPEED = 1100
        PAD_W = int(70 * SW / 1920)
        PAD_H = int(20 * SH / 1080)
        for cx, cy, direction in self.boost_pads:
            pad_rect = pygame.Rect(cx - PAD_W // 2, cy - PAD_H // 2, PAD_W, PAD_H)
            if self._ball_rect().colliderect(pad_rect):
                boost_map = {
                    "up":    (0, -BOOST_SPEED),
                    "down":  (0,  BOOST_SPEED),
                    "left":  (-BOOST_SPEED, 0),
                    "right": ( BOOST_SPEED, 0),
                }
                dvx, dvy = boost_map[direction]
                self.bvx = dvx
                self.bvy = dvy
                self.sounds["boost"].play()
                col = (80, 255, 200)
                for _ in range(20):
                    p = Particle(self.bx, self.by, col)
                    p.vx = dvx * 0.3 + p.vx * 0.3
                    p.vy = dvy * 0.3 + p.vy * 0.3
                    self.particles.append(p)
                self.flashes.append(Flash((60, 220, 180), 0.12))
                break

    def _check_goal(self):
        if self._ball_rect(shrink=4).colliderect(self.goal_rect):
            self.state = "level_clear"
            self.sounds["level_clear"].play()
            # Save best time for this level
            prev = self.best_times.get(self.level_idx, None)
            if prev is None or self.level_time < prev:
                self.best_times[self.level_idx] = self.level_time
            self.flashes.append(Flash((50, 255, 150), 0.5))
            for _ in range(60):
                self.particles.append(
                    Particle(self.goal_rect.centerx,
                             self.goal_rect.centery, (50, 255, 150)))

    # ----------------------------------------------- effects / utility --

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

        # Rainbow trail -- age each point
        for pt in self.trail_points:
            pt[2] -= dt * 1.8
        self.trail_points = [pt for pt in self.trail_points if pt[2] > 0]

        # Seed trail during active slowmo
        if self.slowmo_timer > 0 and self.state == "play":
            rainbow_cols = [
                (255, 60, 60), (255, 160, 30), (255, 255, 40),
                (60, 255, 80), (40, 180, 255), (180, 60, 255),
            ]
            self.trail_points.append(
                [self.bx, self.by, 0.45, random.choice(rainbow_cols)])

        # Speed trail when moving fast
        if self.state == "play":
            speed = math.hypot(self.bvx, self.bvy)
            if speed > 600:
                alpha = min(1.0, (speed - 600) / 600.0)
                self.trail_points.append(
                    [self.bx, self.by, 0.2 * alpha, (255, 80, 50)])

        # Dash afterimage trail
        if self.dash_timer > 0 and self.state == "play":
            self.trail_points.append(
                [self.bx, self.by, 0.35, (100, 200, 255)])

        # Portal streak resets when all void wall cooldowns expire
        if all(vw.cooldown == 0 for vw in self.void_walls):
            self.portal_streak = 0

        # Coin combo window
        if self.coin_combo_timer > 0:
            self.coin_combo_timer -= dt
            if self.coin_combo_timer <= 0:
                self.coin_combo = 0
                self.combo_text = ""

        # Gravity announcement fade
        if self.gravity_announce_timer > 0:
            self.gravity_announce_timer = max(0.0, self.gravity_announce_timer - dt)

        # -- Kill streak timer --
        if self.kill_streak_timer > 0:
            self.kill_streak_timer -= dt
            if self.kill_streak_timer <= 0:
                self.kill_streak = 0

        # -- Floating texts --
        for ft in self.floating_texts:
            ft[1] -= 50 * dt   # drift upward
            ft[4] -= dt         # decay timer
        self.floating_texts = [ft for ft in self.floating_texts if ft[4] > 0]

        # -- Squash/stretch lerp back to 1.0 --
        self.squash += (1.0 - self.squash) * min(1.0, dt * 12)

    def _ball_rect(self, shrink=0):
        r = self.ball_r - shrink
        return pygame.Rect(int(self.bx) - r, int(self.by) - r, r * 2, r * 2)
