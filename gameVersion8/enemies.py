"""
enemies.py  –  Enemy classes, obstacles, void walls, and projectiles.
"""

import math
import random
import pygame
from settings import SW, SH, CANVAS_W, CANVAS_H, PALETTE, GUN_PROJ_RADIUS
from utils import scale_pt, scale_rect


class RotatingObstacle:
    """A rotating cross-shaped obstacle that kills on contact."""
    
    def __init__(self, pos, arm_len, thick, speed):
        self.x, self.y = scale_pt(pos)
        self.arm   = int(arm_len * SW / CANVAS_W)
        self.thick = int(thick * SW / CANVAS_W)
        self.speed = speed  # degrees per second
        self.angle = 0.0
    
    def update(self, dt):
        self.angle += self.speed * dt
    
    def draw(self, surf):
        # Draw rotating cross
        pygame.draw.circle(surf, (60, 60, 80), (int(self.x), int(self.y)), 
                          self.thick + 4)
        pygame.draw.circle(surf, (255, 80, 50), (int(self.x), int(self.y)), 
                          self.thick)
        
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        
        # Two perpendicular arms
        for angle_offset in [0, 90]:
            a = rad + math.radians(angle_offset)
            cx, cy = math.cos(a), math.sin(a)
            x1 = int(self.x + cx * self.arm)
            y1 = int(self.y + cy * self.arm)
            x2 = int(self.x - cx * self.arm)
            y2 = int(self.y - cy * self.arm)
            pygame.draw.line(surf, (255, 120, 80), (x1, y1), (x2, y2), 
                           self.thick * 2)
    
    def collides_with_ball(self, bx, by, br):
        # Check distance to center
        if math.hypot(bx - self.x, by - self.y) < br + self.thick:
            return True
        
        # Check collision with arms
        rad = math.radians(self.angle)
        for angle_offset in [0, 90]:
            a = rad + math.radians(angle_offset)
            cx, cy = math.cos(a), math.sin(a)
            
            # Check line segment collision
            for dist in [-self.arm, self.arm]:
                px = self.x + cx * dist
                py = self.y + cy * dist
                if math.hypot(bx - px, by - py) < br + self.thick:
                    return True
        
        return False


class FlyingEnemy:
    """A floating ghost enemy that pursues the player."""
    
    RADIUS = 28
    
    def __init__(self, pos, speed):
        self.x, self.y = scale_pt(pos)
        self.speed = speed * SW / CANVAS_W
        self.alive = True
        self.phase = 0.0
        self.hit_cooldown = 0.0
        # Random movement behavior
        self.behavior = random.choice(['chase', 'orbit', 'zigzag'])
        self.orbit_radius = random.uniform(150, 250)
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.zigzag_timer = 0.0
        self.zigzag_dir = 1
    
    def update(self, dt, player_x, player_y):
        if not self.alive:
            return
        
        self.phase += dt * 3
        self.hit_cooldown = max(0, self.hit_cooldown - dt)
        
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        
        if self.behavior == 'chase':
            # Direct chase
            if dist > 5:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt
        
        elif self.behavior == 'orbit':
            # Orbit around player
            self.orbit_angle += dt * 1.2
            target_x = player_x + math.cos(self.orbit_angle) * self.orbit_radius
            target_y = player_y + math.sin(self.orbit_angle) * self.orbit_radius
            dx2 = target_x - self.x
            dy2 = target_y - self.y
            dist2 = math.hypot(dx2, dy2)
            if dist2 > 5:
                self.x += (dx2 / dist2) * self.speed * dt
                self.y += (dy2 / dist2) * self.speed * dt
        
        else:  # zigzag
            self.zigzag_timer += dt
            if self.zigzag_timer > 0.8:
                self.zigzag_timer = 0
                self.zigzag_dir *= -1
            
            if dist > 5:
                # Move toward player with perpendicular zigzag
                perp_x = -dy / dist
                perp_y = dx / dist
                self.x += (dx / dist + perp_x * self.zigzag_dir * 0.3) * self.speed * dt
                self.y += (dy / dist + perp_y * self.zigzag_dir * 0.3) * self.speed * dt
    
    def try_hit(self, bx, by, br):
        """Check if enemy hits the ball. Returns True if hit and cooldown allows."""
        if not self.alive or self.hit_cooldown > 0:
            return False
        if math.hypot(bx - self.x, by - self.y) < br + self.RADIUS:
            self.hit_cooldown = 1.0  # 1 second cooldown
            return True
        return False
    
    def draw(self, surf):
        if not self.alive:
            return
        
        # Floating animation
        bob = math.sin(self.phase) * 4
        draw_y = int(self.y + bob)
        
        # Glow effect
        for r in range(self.RADIUS + 15, self.RADIUS - 5, -3):
            alpha = max(0, 80 - (r - self.RADIUS) * 8)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 80, 255, alpha), (r, r), r)
            surf.blit(s, (int(self.x) - r, draw_y - r))
        
        # Main body
        pygame.draw.circle(surf, (140, 60, 200), (int(self.x), draw_y), 
                          self.RADIUS)
        pygame.draw.circle(surf, (200, 120, 255), (int(self.x), draw_y), 
                          self.RADIUS, 3)
        
        # Eyes
        eye_offset = 8
        for ex in [-eye_offset, eye_offset]:
            pygame.draw.circle(surf, (255, 255, 255), 
                             (int(self.x + ex), draw_y - 5), 6)
            pygame.draw.circle(surf, (80, 0, 150), 
                             (int(self.x + ex), draw_y - 5), 4)


class ShootingEnemy:
    """A stationary turret that shoots at the player."""
    
    RADIUS = 24
    
    def __init__(self, pos, fire_interval):
        self.x, self.y = scale_pt(pos)
        self.fire_interval = fire_interval
        self.fire_timer = fire_interval
        self.alive = True
        self.angle = 0.0
    
    def update(self, dt, player_x, player_y):
        if not self.alive:
            return
        
        # Aim at player
        dx = player_x - self.x
        dy = player_y - self.y
        self.angle = math.atan2(dy, dx)
        
        self.fire_timer -= dt
    
    def try_fire(self):
        """Returns an EnemyProjectile if ready to fire, else None."""
        if not self.alive or self.fire_timer > 0:
            return None
        
        self.fire_timer = self.fire_interval
        
        # Fire toward current angle
        speed = 400
        vx = math.cos(self.angle) * speed
        vy = math.sin(self.angle) * speed
        return EnemyProjectile(self.x, self.y, vx, vy)
    
    def draw(self, surf):
        if not self.alive:
            return
        
        # Base
        pygame.draw.circle(surf, (60, 60, 80), (int(self.x), int(self.y)), 
                          self.RADIUS + 4)
        pygame.draw.circle(surf, (180, 40, 40), (int(self.x), int(self.y)), 
                          self.RADIUS)
        pygame.draw.circle(surf, (255, 80, 80), (int(self.x), int(self.y)), 
                          self.RADIUS, 3)
        
        # Gun barrel
        barrel_len = 30
        ex = int(self.x + math.cos(self.angle) * barrel_len)
        ey = int(self.y + math.sin(self.angle) * barrel_len)
        pygame.draw.line(surf, (255, 120, 120), (int(self.x), int(self.y)), 
                        (ex, ey), 6)
        
        # Barrel tip
        pygame.draw.circle(surf, (255, 60, 60), (ex, ey), 5)


class EnemyProjectile:
    """A projectile fired by a ShootingEnemy."""
    
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.radius = 8
        self.lifetime = 5.0  # seconds
    
    def update(self, dt):
        if not self.alive:
            return
        
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        
        # Die if off screen or lifetime expired
        if (self.x < -50 or self.x > SW + 50 or 
            self.y < -50 or self.y > SH + 50 or 
            self.lifetime <= 0):
            self.alive = False
    
    def hits_ball(self, bx, by, br):
        """Check collision with ball."""
        if not self.alive:
            return False
        return math.hypot(self.x - bx, self.y - by) < self.radius + br
    
    def draw(self, surf):
        if not self.alive:
            return
        
        # Glow
        for r in range(self.radius + 8, self.radius - 2, -2):
            alpha = max(0, 100 - (r - self.radius) * 15)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 60, 60, alpha), (r, r), r)
            surf.blit(s, (int(self.x) - r, int(self.y) - r))
        
        pygame.draw.circle(surf, PALETTE["enemy_proj"], 
                          (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, (255, 150, 150), 
                          (int(self.x), int(self.y)), self.radius, 2)


class PlayerProjectile:
    """A projectile fired by the player's gun."""
    
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.radius = GUN_PROJ_RADIUS
        self.lifetime = 3.0
    
    def update(self, dt):
        if not self.alive:
            return
        
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        
        if (self.x < -50 or self.x > SW + 50 or 
            self.y < -50 or self.y > SH + 50 or 
            self.lifetime <= 0):
            self.alive = False
    
    def hits_enemy(self, ex, ey, er):
        """Check collision with an enemy."""
        if not self.alive:
            return False
        return math.hypot(self.x - ex, self.y - ey) < self.radius + er
    
    def draw(self, surf):
        if not self.alive:
            return
        
        # Glow
        for r in range(self.radius + 6, self.radius - 1, -1):
            alpha = max(0, 120 - (r - self.radius) * 20)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 80, alpha), (r, r), r)
            surf.blit(s, (int(self.x) - r, int(self.y) - r))
        
        pygame.draw.circle(surf, PALETTE["projectile"], 
                          (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, (255, 255, 200), 
                          (int(self.x), int(self.y)), self.radius, 2)


class VoidWall:
    """
    An edge-portal wall that sits flush against one screen edge and teleports
    the player to the opposite edge.

    orientation  : "vertical"   → left edge (x=0) or right edge (x=SW)
                   "horizontal" → top edge  (y=0) or bottom edge (y=SH)
    side         : "near"  → left / top
                   "far"   → right / bottom
    """

    THICKNESS = 18   # visible portal strip width in pixels

    def __init__(self, orientation, side):
        self.orientation   = orientation
        self.side          = side          # "near" | "far"
        self.shimmer_phase = random.uniform(0, math.pi * 2)
        self.cooldown      = 0.0
        self.flash_timer   = 0.0           # bright flash after teleport

        self.is_vertical = (orientation == "vertical")
        if self.is_vertical:
            self.x = 0 if side == "near" else SW
        else:
            self.y = 0 if side == "near" else SH

    # ── partner linkage (set by game after both walls created) ──────────
    def set_partner(self, partner):
        self._partner = partner

    # ── update ──────────────────────────────────────────────────────────
    def update(self, dt):
        self.shimmer_phase += dt * 3.5
        self.cooldown   = max(0.0, self.cooldown   - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)

    # ── teleport check ───────────────────────────────────────────────────
    def check_teleport(self, bx, by, br):
        """
        Return (new_x, new_y) if the ball touches this portal edge,
        placing ball just inside the OPPOSITE edge. Returns None otherwise.
        """
        if self.cooldown > 0:
            return None

        threshold = br + self.THICKNESS

        if self.is_vertical:
            hit = (self.side == "near"  and bx - br <= self.THICKNESS) or \
                  (self.side == "far"   and bx + br >= SW - self.THICKNESS)
            if not hit:
                return None
            # Teleport to opposite x, preserve y
            if self.side == "near":
                new_x = float(SW - br - 2)
            else:
                new_x = float(br + 2)
            self.cooldown    = 0.55
            self.flash_timer = 0.35
            if hasattr(self, "_partner"):
                self._partner.cooldown = 0.55
            return (new_x, by)
        else:
            hit = (self.side == "near"  and by - br <= self.THICKNESS) or \
                  (self.side == "far"   and by + br >= SH - self.THICKNESS)
            if not hit:
                return None
            if self.side == "near":
                new_y = float(SH - br - 2)
            else:
                new_y = float(br + 2)
            self.cooldown    = 0.55
            self.flash_timer = 0.35
            if hasattr(self, "_partner"):
                self._partner.cooldown = 0.55
            return (bx, new_y)

    # ── draw ─────────────────────────────────────────────────────────────
    def draw(self, surf):
        t      = self.shimmer_phase
        pulse  = 0.5 + 0.5 * math.sin(t)
        flash  = self.flash_timer / 0.35 if self.flash_timer > 0 else 0.0

        # Base portal colour: purple → white flash on teleport
        r_col = int(80  + 175 * flash)
        g_col = int(0   + 255 * flash)
        b_col = int(220 + 35  * flash)
        base_alpha = int(130 + 80 * pulse + 125 * flash)
        base_alpha = min(255, base_alpha)

        thick = self.THICKNESS
        if self.is_vertical:
            x = 0 if self.side == "near" else SW - thick
            rect_surf = pygame.Surface((thick, SH), pygame.SRCALPHA)
            # gradient fill along the height
            for row in range(0, SH, 4):
                wave = math.sin(t * 2 + row * 0.04)
                a    = int(base_alpha * (0.6 + 0.4 * wave))
                a    = max(0, min(255, a))
                pygame.draw.rect(rect_surf, (r_col, g_col, b_col, a),
                                 (0, row, thick, 4))
            surf.blit(rect_surf, (x, 0))
            # bright inner edge line
            edge_x = thick - 2 if self.side == "near" else 2
            for row in range(0, SH, 6):
                wave  = abs(math.sin(t * 3 + row * 0.05))
                la    = int(200 * wave)
                pygame.draw.line(surf, (200, 160, 255, la),
                                 (x + edge_x, row), (x + edge_x, row + 3), 2)
            # sparkles
            for i in range(6):
                sy = int((t * 180 + i * (SH // 6)) % SH)
                sa = int(220 * abs(math.sin(t + i)))
                pygame.draw.circle(surf, (220, 150, 255),
                                   (x + thick // 2, sy), 3 + int(2 * pulse))
            # label arrow
            arrow = "▶" if self.side == "near" else "◀"
            _draw_portal_label(surf, arrow, x + thick // 2,
                               SH // 2, pulse, flash)
        else:
            y = 0 if self.side == "near" else SH - thick
            rect_surf = pygame.Surface((SW, thick), pygame.SRCALPHA)
            for col in range(0, SW, 4):
                wave = math.sin(t * 2 + col * 0.04)
                a    = int(base_alpha * (0.6 + 0.4 * wave))
                a    = max(0, min(255, a))
                pygame.draw.rect(rect_surf, (r_col, g_col, b_col, a),
                                 (col, 0, 4, thick))
            surf.blit(rect_surf, (0, y))
            edge_y = thick - 2 if self.side == "near" else 2
            for col in range(0, SW, 6):
                wave  = abs(math.sin(t * 3 + col * 0.05))
                la    = int(200 * wave)
                pygame.draw.line(surf, (200, 160, 255, la),
                                 (col, y + edge_y), (col + 3, y + edge_y), 2)
            for i in range(6):
                sx = int((t * 180 + i * (SW // 6)) % SW)
                sa = int(220 * abs(math.sin(t + i)))
                pygame.draw.circle(surf, (220, 150, 255),
                                   (sx, y + thick // 2), 3 + int(2 * pulse))
            arrow = "▼" if self.side == "near" else "▲"
            _draw_portal_label(surf, arrow, SW // 2,
                               y + thick // 2, pulse, flash)


def _draw_portal_label(surf, arrow, cx, cy, pulse, flash):
    """Draw a small pulsing arrow label on a portal edge."""
    try:
        font = pygame.font.SysFont("consolas", 16, bold=True)
        a_val = int(180 + 75 * pulse + 75 * flash)
        a_val = min(255, a_val)
        txt = font.render(arrow, True, (220, 180, 255))
        tmp = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
        tmp.blit(txt, (0, 0))
        tmp.set_alpha(a_val)
        surf.blit(tmp, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))
    except Exception:
        pass