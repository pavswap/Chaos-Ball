"""
renderer.py
-----------
Pure drawing logic.  The Renderer class owns no game state; it receives
everything it needs as arguments or reads from the Game object passed in.

Keeping all pygame.draw calls here makes Game.update() easy to read and
makes visual changes straightforward to find.
"""

import math

import pygame
from settings import SW, SH, BG_COLORS, PALETTE, NUM_LEVELS
from utils import draw_spike, draw_heart


class Renderer:
    """Handles every pygame.draw / blit call for the game."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font_big   = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)

    # ------------------------------------------------------------------
    # Master draw entry point
    # ------------------------------------------------------------------

    def draw(self, game) -> None:
        """Draw a complete frame.  *game* is the Game instance."""
        self._draw_background(game)
        self._draw_border(game)
        self._draw_platforms(game)
        self._draw_spikes(game)
        self._draw_goal(game)
        self._draw_ball(game)
        self._draw_particles(game)
        self._draw_flashes(game)
        self._draw_hud(game)
        self._draw_overlay(game)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _draw_background(self, game) -> None:
        bg = BG_COLORS[game.bg_color_idx]
        self.screen.fill(bg)
        grid_col = tuple(min(255, c + 15) for c in bg)
        for x in range(0, SW, 80):
            pygame.draw.line(self.screen, grid_col, (x, 0), (x, SH), 1)
        for y in range(0, SH, 80):
            pygame.draw.line(self.screen, grid_col, (0, y), (SW, y), 1)

    # ------------------------------------------------------------------
    # Border (shows deadly-wall state)
    # ------------------------------------------------------------------

    def _draw_border(self, game) -> None:
        color = PALETTE["deadly_wall"] if game.walls_deadly else PALETTE["safe_wall"]
        pygame.draw.rect(self.screen, color, (0, 0, SW, SH), 6)

    # ------------------------------------------------------------------
    # Platforms
    # ------------------------------------------------------------------

    def _draw_platforms(self, game) -> None:
        for plat in game.platforms:
            pygame.draw.rect(self.screen, PALETTE["platform"], plat)
            pygame.draw.rect(self.screen, (100, 220, 255), plat, 2)

    # ------------------------------------------------------------------
    # Spikes
    # ------------------------------------------------------------------

    def _draw_spikes(self, game) -> None:
        for spike_rect, direction in game.spikes:
            draw_spike(self.screen, spike_rect, direction, PALETTE["spike"])

    # ------------------------------------------------------------------
    # Goal portal
    # ------------------------------------------------------------------

    def _draw_goal(self, game) -> None:
        gr = game.goal_rect

        # Soft glow rings
        for ring in range(4, 0, -1):
            gs    = pygame.Surface((gr.w + ring * 16, gr.h + ring * 16), pygame.SRCALPHA)
            alpha = max(0, 40 - ring * 8)
            pygame.draw.rect(
                gs, (50, 255, 150, alpha),
                (0, 0, gr.w + ring * 16, gr.h + ring * 16),
                border_radius=12,
            )
            self.screen.blit(gs, (gr.x - ring * 8, gr.y - ring * 8))

        pygame.draw.rect(self.screen, PALETTE["goal"], gr, border_radius=6)
        pygame.draw.rect(self.screen, (200, 255, 220), gr, 3, border_radius=6)

        # Orbiting dots
        t = pygame.time.get_ticks() / 500
        for i in range(8):
            angle = i * math.pi / 4 + t
            ex    = gr.centerx + math.cos(angle) * 22
            ey    = gr.centery + math.sin(angle) * 22
            pygame.draw.circle(self.screen, (200, 255, 200), (int(ex), int(ey)), 4)

        # Label
        label = self.font_small.render("EXIT", True, (20, 80, 40))
        self.screen.blit(
            label,
            (gr.centerx - label.get_width() // 2,
             gr.centery - label.get_height() // 2),
        )

    # ------------------------------------------------------------------
    # Player ball
    # ------------------------------------------------------------------

    def _draw_ball(self, game) -> None:
        bxi, byi = int(game.bx), int(game.by)
        r        = game.ball_r

        # Glow rings
        for glow_r in range(r + 12, r - 1, -4):
            alpha_val = max(0, 120 - (glow_r - r) * 20)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surf, (*PALETTE["ball"], alpha_val), (glow_r, glow_r), glow_r
            )
            self.screen.blit(glow_surf, (bxi - glow_r, byi - glow_r))

        pygame.draw.circle(self.screen, PALETTE["ball"], (bxi, byi), r)
        pygame.draw.circle(self.screen, (255, 200, 190), (bxi - 5, byi - 5), 6)

        # Double-jump indicator dots (positioned "below" the ball, i.e. in the
        # direction gravity is pulling so they sit under the ball visually)
        gx, gy     = game.gravity_dir
        dot_offset = r + 10
        for i in range(2):
            active  = i < game.jumps_left
            dot_col = (150, 200, 255) if active else (50, 60, 80)
            dot_x   = (bxi + int(gx * dot_offset)
                       + (i * 14 - 7) * int(abs(gy)))
            dot_y   = (byi + int(gy * dot_offset)
                       + (i * 14 - 7) * int(abs(gx)))
            pygame.draw.circle(self.screen, dot_col, (dot_x, dot_y), 5)
            if active:
                pygame.draw.circle(self.screen, (200, 230, 255), (dot_x, dot_y), 3)

    # ------------------------------------------------------------------
    # Particles & flashes
    # ------------------------------------------------------------------

    def _draw_particles(self, game) -> None:
        for p in game.particles:
            p.draw(self.screen)

    def _draw_flashes(self, game) -> None:
        for f in game.flashes:
            f.draw(self.screen)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _draw_hud(self, game) -> None:
        # Level counter
        lv = self.font_med.render(
            f"LEVEL {game.level_idx + 1}/{NUM_LEVELS}", True, PALETTE["text"]
        )
        self.screen.blit(lv, (20, 20))

        # Gravity direction label
        gx, gy = game.gravity_dir
        dir_map = {
            (0,  1): "↓ Gravity",
            (0, -1): "↑ Gravity",
            (1,  0): "→ Gravity",
            (-1, 0): "← Gravity",
        }
        grav = self.font_small.render(dir_map.get((gx, gy), ""), True, (180, 180, 255))
        self.screen.blit(grav, (20, 65))

        # Deadly-wall state
        wall_txt = "⚠ DEADLY WALLS" if game.walls_deadly else "Safe Walls"
        wall_col = PALETTE["deadly_wall"] if game.walls_deadly else (120, 120, 160)
        self.screen.blit(self.font_small.render(wall_txt, True, wall_col), (20, 92))

        # Compass arrow pointing to exit
        self._draw_compass(game)

        # Hearts (top-right)
        heart_size    = 28
        heart_spacing = 44
        start_x       = SW - heart_spacing * 5 - 20
        for i in range(5):
            cx    = start_x + i * heart_spacing + heart_size
            color = PALETTE["heart_full"] if i < game.hearts else PALETTE["heart_empty"]
            draw_heart(self.screen, cx, 36, heart_size, color)

        # First-level controls hint
        if game.level_idx == 0 and game.total_deaths == 0:
            hint = self.font_small.render(
                "WASD / Arrows: Move   |   SPACE: Jump (×2 Double Jump)   |   ESC: Quit",
                True, (140, 140, 160),
            )
            self.screen.blit(hint, (SW // 2 - hint.get_width() // 2, SH - 40))

    def _draw_compass(self, game) -> None:
        """Small circular compass that points toward the exit portal."""
        cx, cy = 60, SH - 80
        pygame.draw.circle(self.screen, (30, 30, 50), (cx, cy), 28)
        pygame.draw.circle(self.screen, (60, 60, 90), (cx, cy), 28, 2)

        dx   = SW // 2 - int(game.bx)
        dy   = SH // 2 - int(game.by)
        dist = math.hypot(dx, dy)

        if dist > 1:
            ndx, ndy   = dx / dist, dy / dist
            tip        = (cx + int(ndx * 18), cy + int(ndy * 18))
            px_, py_   = -ndy, ndx
            base1 = (cx + int((-ndx + px_ * 0.5) * 10),
                     cy + int((-ndy + py_ * 0.5) * 10))
            base2 = (cx + int((-ndx - px_ * 0.5) * 10),
                     cy + int((-ndy - py_ * 0.5) * 10))
            pygame.draw.polygon(self.screen, PALETTE["goal"], [tip, base1, base2])

        label = self.font_small.render("EXIT", True, PALETTE["goal"])
        self.screen.blit(label, (cx - label.get_width() // 2, cy + 32))

        deaths = self.font_small.render(
            f"Deaths: {game.total_deaths}", True, (160, 160, 180)
        )
        self.screen.blit(deaths, (cx + 36, cy + 32))

    # ------------------------------------------------------------------
    # State overlays (level clear / game over / win)
    # ------------------------------------------------------------------

    def _draw_overlay(self, game) -> None:
        if game.state == "level_clear":
            self._overlay("LEVEL CLEAR!", (50, 255, 150), "Press ENTER to continue")
        elif game.state == "game_over":
            self._overlay(
                "GAME OVER", (255, 60, 60),
                f"Deaths: {game.total_deaths}  |  Press R to restart",
            )
        elif game.state == "win":
            self._overlay(
                "YOU WIN!", (255, 220, 50),
                f"Deaths: {game.total_deaths}  |  Press R to play again",
            )

    def _overlay(self, title: str, color: tuple, sub: str = "") -> None:
        panel = pygame.Surface((SW, SH), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        self.screen.blit(panel, (0, 0))

        t_surf = self.font_big.render(title, True, color)
        self.screen.blit(t_surf, (SW // 2 - t_surf.get_width() // 2, SH // 2 - 80))

        if sub:
            s_surf = self.font_med.render(sub, True, PALETTE["text"])
            self.screen.blit(s_surf, (SW // 2 - s_surf.get_width() // 2, SH // 2 + 20))