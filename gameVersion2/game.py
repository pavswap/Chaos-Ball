"""
game.py
-------
Core game state and logic.

The Game class is responsible for:
  - Player physics (movement, gravity, collision)
  - Death / chaos respawn (gravity shuffle, wall mode toggle)
  - Level loading and progression
  - Maintaining particles & flashes lists (updated here, drawn by Renderer)

No pygame.draw calls live here – all rendering is delegated to Renderer.
"""

import random

import pygame
from settings import (
    SW, SH,
    GRAVITY_DIRS, GRAVITY_STRENGTH,
    NUM_LEVELS,
)
from utils import scale_rect, scale_pt
from particles import Particle, Flash
from level_generator import LEVELS_DATA


class Game:
    """Owns all mutable game state and drives the update loop."""

    def __init__(self) -> None:
        self.reset_all()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def reset_all(self) -> None:
        """Full reset to level 1 with 5 hearts."""
        self.level_idx    = 0
        self.hearts       = 5
        self.total_deaths = 0
        self.state        = "play"   # "play" | "level_clear" | "game_over" | "win"
        self.gravity_dir  = (0, 1)   # starts as normal downward gravity
        self.walls_deadly = False
        self.bg_color_idx = 0
        self.particles: list = []
        self.flashes:   list = []
        self.death_timer     = 0.0
        self.load_level()

    def load_level(self) -> None:
        """Load / reload the current level from LEVELS_DATA."""
        data = LEVELS_DATA[self.level_idx % NUM_LEVELS]

        self.platforms = [pygame.Rect(*scale_rect(p)) for p in data["platforms"]]
        self.spikes    = [(pygame.Rect(*scale_rect(s[:4])), s[4]) for s in data["spikes"]]
        self.goal_rect = pygame.Rect(*scale_rect(data["goal"]))

        sx, sy      = scale_pt(data["spawn"])
        self.ball_r = int(22 * SW / 1920)
        self.bx     = float(sx)
        self.by     = float(sy)
        self.bvx    = 0.0
        self.bvy    = 0.0

        self.on_ground  = False
        self.jumps_left = 2

        self.particles = []
        self.flashes   = []

    # ------------------------------------------------------------------
    # Death / chaos
    # ------------------------------------------------------------------

    def respawn_with_chaos(self) -> None:
        """Kill the player: lose a heart, randomise physics, reload level."""
        self.total_deaths += 1
        self.hearts -= 1

        # Burst particles at ball position
        for _ in range(40):
            self.particles.append(Particle(self.bx, self.by, (255, 80, 50)))
        self.flashes.append(Flash((255, 60, 60), 0.4))

        if self.hearts <= 0:
            self.state = "game_over"
            return

        # Randomise physics
        self.gravity_dir = random.choice(GRAVITY_DIRS)
        if random.random() < 0.4:
            self.walls_deadly = not self.walls_deadly

        self.bg_color_idx = (self.bg_color_idx + 1) % 5
        self.load_level()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

                if event.key == pygame.K_r and self.state in ("game_over", "win"):
                    self.reset_all()
                    return

                if event.key == pygame.K_RETURN and self.state == "level_clear":
                    self.level_idx += 1
                    if self.level_idx >= NUM_LEVELS:
                        self.state = "win"
                    else:
                        self.state = "play"
                        self.load_level()

                # Jump (space / up / w) – supports double jump
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w) \
                        and self.state == "play":
                    if self.jumps_left > 0:
                        gx, gy       = self.gravity_dir
                        jump_speed   = 700
                        self.bvx    -= gx * jump_speed
                        self.bvy    -= gy * jump_speed
                        self.jumps_left -= 1
                        self.on_ground   = False

                        # Puff effect on second (air) jump
                        if self.jumps_left == 0:
                            for _ in range(18):
                                p     = Particle(self.bx, self.by, (150, 200, 255))
                                p.vx *= 0.6
                                p.vy *= 0.6
                                self.particles.append(p)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        # Always tick particles and flashes, even on non-play screens
        self._tick_effects(dt)

        if self.state != "play":
            return

        self._apply_movement(dt)
        self._apply_gravity(dt)
        self._cap_velocity()
        self._move_x(dt)
        self._move_y(dt)
        self._check_walls()
        self._check_spikes()
        self._check_goal()

    # ------------------------------------------------------------------
    # Physics sub-steps
    # ------------------------------------------------------------------

    def _apply_movement(self, dt: float) -> None:
        """Apply left/right (or up/down for sideways gravity) player input."""
        keys       = pygame.key.get_pressed()
        gx, gy     = self.gravity_dir
        move_accel = 500 * 8   # px/s² equivalent per frame

        if gy != 0:
            # Vertical gravity → move left / right
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
                self.bvx -= move_accel * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.bvx += move_accel * dt
            self.bvx *= 0.80   # horizontal friction
        else:
            # Horizontal gravity → move up / down
            if keys[pygame.K_UP]   or keys[pygame.K_w]:
                self.bvy -= move_accel * dt
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.bvy += move_accel * dt
            self.bvy *= 0.80

    def _apply_gravity(self, dt: float) -> None:
        gx, gy    = self.gravity_dir
        self.bvx += gx * GRAVITY_STRENGTH * dt
        self.bvy += gy * GRAVITY_STRENGTH * dt

    def _cap_velocity(self) -> None:
        max_vel  = 1200
        self.bvx = max(-max_vel, min(max_vel, self.bvx))
        self.bvy = max(-max_vel, min(max_vel, self.bvy))

    def _move_x(self, dt: float) -> None:
        self.bx       += self.bvx * dt
        self.on_ground = False
        rect           = self._ball_rect()

        for plat in self.platforms:
            if rect.colliderect(plat):
                if self.bvx > 0:
                    self.bx = plat.left - self.ball_r
                elif self.bvx < 0:
                    self.bx = plat.right + self.ball_r
                self.bvx = 0

    def _move_y(self, dt: float) -> None:
        gx, gy    = self.gravity_dir
        self.by  += self.bvy * dt
        rect       = self._ball_rect()

        for plat in self.platforms:
            if rect.colliderect(plat):
                if self.bvy > 0:
                    self.by = plat.top - self.ball_r
                    if gy > 0:
                        self.on_ground  = True
                        self.jumps_left = 2
                elif self.bvy < 0:
                    self.by = plat.bottom + self.ball_r
                    if gy < 0:
                        self.on_ground  = True
                        self.jumps_left = 2

                # Sideways gravity: treat the platform side as the "ground"
                if gx > 0 and self.bvx > 0:
                    self.bx         = plat.left - self.ball_r
                    self.on_ground  = True
                    self.jumps_left = 2
                elif gx < 0 and self.bvx < 0:
                    self.bx         = plat.right + self.ball_r
                    self.on_ground  = True
                    self.jumps_left = 2

                self.bvy = 0

    def _check_walls(self) -> None:
        gx, gy   = self.gravity_dir
        hit_wall = False

        if self.bx - self.ball_r < 0:
            self.bx  = self.ball_r
            self.bvx = abs(self.bvx) * 0.5
            hit_wall = True
            if gx < 0:
                self.on_ground  = True
                self.jumps_left = 2

        if self.bx + self.ball_r > SW:
            self.bx  = SW - self.ball_r
            self.bvx = -abs(self.bvx) * 0.5
            hit_wall = True
            if gx > 0:
                self.on_ground  = True
                self.jumps_left = 2

        if self.by - self.ball_r < 0:
            self.by  = self.ball_r
            self.bvy = abs(self.bvy) * 0.5
            hit_wall = True
            if gy < 0:
                self.on_ground  = True
                self.jumps_left = 2

        if self.by + self.ball_r > SH:
            self.by  = SH - self.ball_r
            self.bvy = -abs(self.bvy) * 0.5
            hit_wall = True
            if gy > 0:
                self.on_ground  = True
                self.jumps_left = 2

        if hit_wall and self.walls_deadly:
            self.respawn_with_chaos()

    def _check_spikes(self) -> None:
        rect = self._ball_rect(shrink=4)
        for spike_rect, _ in self.spikes:
            if rect.colliderect(spike_rect):
                self.respawn_with_chaos()
                return

    def _check_goal(self) -> None:
        if self._ball_rect(shrink=4).colliderect(self.goal_rect):
            self.state = "level_clear"
            self.flashes.append(Flash((50, 255, 150), 0.5))
            for _ in range(60):
                self.particles.append(
                    Particle(self.goal_rect.centerx, self.goal_rect.centery, (50, 255, 150))
                )

    # ------------------------------------------------------------------
    # Effect tick
    # ------------------------------------------------------------------

    def _tick_effects(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update(dt)
        self.flashes = [f for f in self.flashes if not f.done]
        for f in self.flashes:
            f.update(dt)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _ball_rect(self, shrink: int = 0) -> pygame.Rect:
        r = self.ball_r - shrink
        return pygame.Rect(
            int(self.bx) - r,
            int(self.by) - r,
            r * 2,
            r * 2,
        )