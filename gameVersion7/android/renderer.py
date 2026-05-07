"""
renderer.py  –  All pygame.draw / blit calls. Zero game state owned here.
"""

import math
import random
import pygame
from settings import (
    SW, SH, BG_COLORS, PALETTE, NUM_LEVELS,
    TIER_BASIC_END, TIER_SPINNER_END, TIER_VOID_END, TIER_SHOOTER_START,
)
from utils import draw_spike, draw_heart


class Renderer:
    def __init__(self, screen):
        self.screen     = screen
        self.font_big   = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)
        self.font_tiny  = pygame.font.SysFont("consolas", 18)

    # ─────────────────────────────────────────────────────────── master ──

    def draw(self, game):
        # Manage cursor visibility: hide when gun is active in play
        if game.has_gun and game.state == "play":
            pygame.mouse.set_visible(False)
        else:
            pygame.mouse.set_visible(True)

        # ── Screen shake: render to a temp surface then blit offset ──
        shake_ox = shake_oy = 0
        if getattr(game, 'screen_shake', 0) > 0:
            strength = getattr(game, 'shake_strength', 6)
            frac     = game.screen_shake / 0.30   # normalise
            amp      = int(strength * min(frac, 1.0))
            shake_ox = random.randint(-amp, amp)
            shake_oy = random.randint(-amp, amp)

        if shake_ox or shake_oy:
            canvas = pygame.Surface((SW, SH))
            target = canvas
        else:
            target = self.screen

        self._draw_background(game, target)
        self._draw_border(game, target)
        self._draw_void_walls(game, target)
        self._draw_platforms(game, target)
        self._draw_spikes(game, target)
        self._draw_rotators(game, target)
        self._draw_enemies(game, target)
        self._draw_shooters(game, target)
        self._draw_enemy_projectiles(game, target)
        self._draw_player_projectiles(game, target)
        self._draw_goal(game, target)
        self._draw_coins(game, target)
        self._draw_boost_pads(game, target)
        self._draw_rainbow_trail(game, target)
        self._draw_ball(game, target)
        self._draw_particles(game, target)
        self._draw_flashes(game, target)

        if shake_ox or shake_oy:
            self.screen.fill((0, 0, 0))
            self.screen.blit(canvas, (shake_ox, shake_oy))

        self._draw_hud(game)
        self._draw_overlay(game)
        self._draw_crosshair(game)
        pygame.display.flip()

    # ────────────────────────────────────────────────────── background ──

    def _draw_background(self, game, surf=None):
        surf = surf or self.screen
        bg = BG_COLORS[game.bg_color_idx % len(BG_COLORS)]
        surf.fill(bg)
        gc = tuple(min(255, c+15) for c in bg)
        for x in range(0, SW, 80):
            pygame.draw.line(surf, gc, (x,0), (x,SH), 1)
        for y in range(0, SH, 80):
            pygame.draw.line(surf, gc, (0,y), (SW,y), 1)

    def _draw_border(self, game, surf=None):
        surf = surf or self.screen
        col = PALETTE["deadly_wall"] if game.walls_deadly else PALETTE["safe_wall"]
        pygame.draw.rect(surf, col, (0,0,SW,SH), 6)

    # ───────────────────────────────────────────────────── void walls ──

    def _draw_void_walls(self, game, surf=None):
        surf = surf or self.screen
        for vw in game.void_walls:
            vw.draw(surf)

    # ──────────────────────────────────────────────────── world items ──

    def _draw_platforms(self, game, surf=None):
        surf = surf or self.screen
        for p in game.platforms:
            pygame.draw.rect(surf, PALETTE["platform"], p)
            pygame.draw.rect(surf, (100,220,255), p, 2)

    def _draw_spikes(self, game, surf=None):
        surf = surf or self.screen
        for sr, d in game.spikes:
            draw_spike(surf, sr, d, PALETTE["spike"])

    def _draw_rotators(self, game, surf=None):
        surf = surf or self.screen
        for rot in game.rotators:
            rot.draw(surf)

    def _draw_enemies(self, game, surf=None):
        surf = surf or self.screen
        for e in game.enemies:
            e.draw(surf)

    def _draw_shooters(self, game, surf=None):
        surf = surf or self.screen
        for s in game.shooters:
            s.draw(surf)

    def _draw_enemy_projectiles(self, game, surf=None):
        surf = surf or self.screen
        for ep in game.enemy_projectiles:
            ep.draw(surf)

    def _draw_player_projectiles(self, game, surf=None):
        surf = surf or self.screen
        for pp in game.player_projectiles:
            pp.draw(surf)

    # ──────────────────────────────────────────────────────────── goal ──

    def _draw_goal(self, game, surf=None):
        surf = surf or self.screen
        gr = game.goal_rect
        for ring in range(4, 0, -1):
            gs = pygame.Surface((gr.w+ring*16, gr.h+ring*16), pygame.SRCALPHA)
            pygame.draw.rect(gs, (50,255,150,max(0,40-ring*8)),
                             (0,0,gr.w+ring*16,gr.h+ring*16), border_radius=12)
            surf.blit(gs, (gr.x-ring*8, gr.y-ring*8))
        pygame.draw.rect(surf, PALETTE["goal"], gr, border_radius=6)
        pygame.draw.rect(surf, (200,255,220), gr, 3, border_radius=6)
        t = pygame.time.get_ticks() / 500
        for i in range(8):
            a = i*math.pi/4 + t
            pygame.draw.circle(surf, (200,255,200),
                               (int(gr.centerx+math.cos(a)*22),
                                int(gr.centery+math.sin(a)*22)), 4)
        lbl = self.font_small.render("EXIT", True, (20,80,40))
        surf.blit(lbl, (gr.centerx-lbl.get_width()//2,
                               gr.centery-lbl.get_height()//2))

    # ──────────────────────────────────────────── rainbow trail + ball ──

    def _draw_coins(self, game, surf=None):
        surf = surf or self.screen
        t = pygame.time.get_ticks() / 600.0
        COIN_R = int(14 * SW / 1920)
        for coin in getattr(game, 'coins', []):
            cx, cy, alive = coin
            if not alive:
                continue
            # cx, cy are already in screen space
            bob = int(math.sin(t + cx * 0.01) * 4)
            draw_y = cy + bob
            # Glow
            for r2 in range(COIN_R + 8, COIN_R - 1, -3):
                a = max(0, 80 - (r2 - COIN_R) * 18)
                s = pygame.Surface((r2 * 2, r2 * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 220, 40, a), (r2, r2), r2)
                surf.blit(s, (cx - r2, draw_y - r2))
            # Coin body
            pygame.draw.circle(surf, (255, 210, 30), (cx, draw_y), COIN_R)
            pygame.draw.circle(surf, (255, 240, 120), (cx - 3, draw_y - 3), COIN_R // 3)
            pygame.draw.circle(surf, (200, 160, 0), (cx, draw_y), COIN_R, 2)

    def _draw_boost_pads(self, game, surf=None):
        surf = surf or self.screen
        t = pygame.time.get_ticks() / 400.0
        PAD_W = int(70 * SW / 1920)
        PAD_H = int(18 * SH / 1080)
        arrow_map = {"up": "▲", "down": "▼", "left": "◄", "right": "►"}
        for cx, cy, direction in getattr(game, 'boost_pads', []):
            # cx, cy already in screen space
            pulse = 0.6 + 0.4 * math.sin(t + cx * 0.02)
            col = (int(40 * pulse), int(255 * pulse), int(180 * pulse))
            pad_rect = pygame.Rect(cx - PAD_W // 2, cy - PAD_H // 2, PAD_W, PAD_H)
            glow = pygame.Surface((PAD_W + 12, PAD_H + 12), pygame.SRCALPHA)
            glow.fill((*col, int(60 * pulse)))
            surf.blit(glow, (pad_rect.x - 6, pad_rect.y - 6))
            pygame.draw.rect(surf, col, pad_rect, border_radius=5)
            pygame.draw.rect(surf, (200, 255, 230), pad_rect, 2, border_radius=5)
            lbl = self.font_tiny.render(arrow_map[direction], True, (20, 60, 40))
            surf.blit(lbl, (cx - lbl.get_width() // 2, cy - lbl.get_height() // 2))

    def _draw_rainbow_trail(self, game, surf=None):
        """Glowing rainbow comet trail after portal teleport."""
        surf = surf or self.screen
        for pt in getattr(game, 'trail_points', []):
            tx, ty, age, col = pt
            if age <= 0:
                continue
            alpha = int(220 * age)
            radius = max(1, int(game.ball_r * age * 0.85))
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, alpha), (radius, radius), radius)
            surf.blit(s, (int(tx) - radius, int(ty) - radius))

    def _draw_ball(self, game, surf=None):
        surf = surf or self.screen
        bxi, byi = int(game.bx), int(game.by)
        r = game.ball_r

        # Extra glow pulse during slowmo (portal aftermath)
        slowmo = getattr(game, 'slowmo_timer', 0)
        glow_extra = int(slowmo * 40)

        # Glow rings
        for gr2 in range(r+12+glow_extra, r-1, -4):
            av = max(0, 120-(gr2-r)*20)
            gs = pygame.Surface((gr2*2, gr2*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*PALETTE["ball"],av), (gr2,gr2), gr2)
            surf.blit(gs, (bxi-gr2, byi-gr2))

        pygame.draw.circle(surf, PALETTE["ball"], (bxi,byi), r)
        pygame.draw.circle(surf, (255,200,190), (bxi-5,byi-5), 6)

        # Gold ring when gun is equipped
        if game.has_gun:
            pygame.draw.circle(surf, (255,240,80), (bxi,byi), r+5, 2)

        # Double-jump indicator dots
        gx, gy = game.gravity_dir
        doff   = r + 10
        for i in range(2):
            active = i < game.jumps_left
            dc = (150,200,255) if active else (50,60,80)
            dx2 = bxi + int(gx*doff) + (i*14-7)*int(abs(gy))
            dy2 = byi + int(gy*doff) + (i*14-7)*int(abs(gx))
            pygame.draw.circle(surf, dc, (dx2,dy2), 5)
            if active:
                pygame.draw.circle(surf, (200,230,255), (dx2,dy2), 3)

    # ───────────────────────────────────────────────────────── effects ──

    def _draw_particles(self, game, surf=None):
        surf = surf or self.screen
        for p in game.particles: p.draw(surf)

    def _draw_flashes(self, game, surf=None):
        surf = surf or self.screen
        for f in game.flashes: f.draw(surf)

    # ──────────────────────────────────────────────────────────── HUD ──

    def _draw_hud(self, game):
        idx = game.level_idx

        # Tier badge
        if   idx < TIER_BASIC_END:     tier_lbl,tier_col = "BASIC",    (70,180,255)
        elif idx < TIER_SPINNER_END:   tier_lbl,tier_col = "SPINNERS", (255,160, 40)
        elif idx < TIER_SHOOTER_START: tier_lbl,tier_col = "VOID",     ( 80,  0,180)
        else:                          tier_lbl,tier_col = "HAUNTED",  (200, 80,255)

        lv = self.font_med.render(f"LEVEL {idx+1}/{NUM_LEVELS}", True, PALETTE["text"])
        self.screen.blit(lv, (20, 20))
        badge = self.font_small.render(f"[ {tier_lbl} ]", True, tier_col)
        self.screen.blit(badge, (20+lv.get_width()+14, 30))

        # Score (top-left under level)
        score_val = getattr(game, 'score', 0)
        score_lbl = self.font_small.render(f"SCORE  {score_val:,}", True, (255, 220, 60))
        self.screen.blit(score_lbl, (20, 58))

        # Level timer + best time
        lt   = getattr(game, 'level_time', 0.0)
        best = getattr(game, 'best_times', {}).get(idx, None)
        mins, secs = divmod(int(lt), 60)
        timer_str  = f"TIME  {mins:02d}:{secs:02d}"
        if best is not None:
            bm, bs = divmod(int(best), 60)
            timer_str += f"  BEST {bm:02d}:{bs:02d}"
        timer_col = (100, 220, 255) if (best is None or lt <= best + 0.5) else (255, 140, 60)
        self.screen.blit(self.font_small.render(timer_str, True, timer_col), (20, 80))

        # Gravity label
        gx, gy = game.gravity_dir
        dmap = {(0,1):"↓ Gravity",(0,-1):"↑ Gravity",
                (1,0):"→ Gravity",(-1,0):"← Gravity"}
        self.screen.blit(
            self.font_small.render(dmap.get((gx,gy),""), True, (180,180,255)),
            (20, 105))

        # Wall state
        wtxt = "⚠ DEADLY WALLS" if game.walls_deadly else "Safe Walls"
        wcol = PALETTE["deadly_wall"] if game.walls_deadly else (120,120,160)
        self.screen.blit(self.font_small.render(wtxt, True, wcol), (20, 128))

        # Enemy / hazard counts
        hud_row = 156
        if game.enemies:
            alive_e = sum(1 for e in game.enemies if e.alive)
            self.screen.blit(
                self.font_small.render(f"👻  x{alive_e}", True, (200,80,255)), (20, hud_row))
            hud_row += 26
        if game.shooters:
            alive_s = sum(1 for s in game.shooters if s.alive)
            self.screen.blit(
                self.font_small.render(f"🔴  x{alive_s}", True, (255,80,80)), (20, hud_row))
            hud_row += 26
        if game.void_walls:
            self.screen.blit(
                self.font_small.render(
                    f"🌀  PORTALS x{len(game.void_walls)}", True, (160, 80, 255)),
                (20, hud_row))
            hud_row += 26

        # Coins remaining
        coins_left = sum(1 for c in getattr(game, 'coins', []) if c[2])
        coins_total = len(getattr(game, 'coins', []))
        if coins_total > 0:
            coin_col = (255, 220, 40) if coins_left > 0 else (80, 200, 80)
            coin_lbl = self.font_small.render(
                f"⬟  {coins_total - coins_left}/{coins_total}", True, coin_col)
            self.screen.blit(coin_lbl, (20, hud_row))
            hud_row += 26

        # Ammo strip
        if game.has_gun:
            self._draw_ammo(game, hud_row)
            hud_row += 30

        # Compass
        self._draw_compass(game)

        # Hearts (top-right) – 2 rows of 5 for 10 total
        hs, hsp = 24, 38
        max_hearts   = 10
        cols_per_row = 5
        for hi in range(max_hearts):
            hrow_i   = hi // cols_per_row
            hcol_i   = hi % cols_per_row
            hx = SW - hsp * cols_per_row - 20 + hcol_i * hsp + hs
            hy = 28 + hrow_i * (hs + 6)
            hcolor = PALETTE["heart_full"] if hi < game.hearts else PALETTE["heart_empty"]
            draw_heart(self.screen, hx, hy, hs, hcolor)

        # Coin combo popup (centre-screen)
        combo_txt = getattr(game, 'combo_text', '')
        if combo_txt:
            ctimer = getattr(game, 'coin_combo_timer', 0)
            alpha  = min(1.0, ctimer * 2)
            c_surf = self.font_med.render(combo_txt, True, (255, 230, 50))
            c_surf.set_alpha(int(alpha * 255))
            self.screen.blit(c_surf,
                             (SW // 2 - c_surf.get_width() // 2, SH // 2 - 120))

        # Gravity announcement (big centre text)
        g_timer = getattr(game, 'gravity_announce_timer', 0)
        g_text  = getattr(game, 'gravity_announce_text', '')
        if g_timer > 0 and g_text:
            # Fade in fast, hold, fade out
            fade = min(1.0, g_timer * 3) if g_timer < 0.4 else min(1.0, (g_timer / 2.2) * 2)
            big = self.font_big.render(g_text, True, (255, 100, 60))
            big.set_alpha(int(fade * 230))
            shadow = self.font_big.render(g_text, True, (0, 0, 0))
            shadow.set_alpha(int(fade * 160))
            bx2 = SW // 2 - big.get_width() // 2
            by2 = SH // 3
            self.screen.blit(shadow, (bx2 + 3, by2 + 3))
            self.screen.blit(big, (bx2, by2))

        # One-time hints
        self._draw_hints(game)

    def _draw_ammo(self, game, y):
        lbl = self.font_small.render("AMMO:", True, (255, 255, 100))
        self.screen.blit(lbl, (20, y))
        # Unlimited ammo – show ∞ symbol
        inf_lbl = self.font_med.render("∞", True, (255, 240, 60))
        self.screen.blit(inf_lbl, (20 + lbl.get_width() + 10, y - 4))

    def _draw_compass(self, game):
        cx,cy = 60, SH-80
        pygame.draw.circle(self.screen,(30,30,50),(cx,cy),28)
        pygame.draw.circle(self.screen,(60,60,90),(cx,cy),28,2)
        dx = SW//2 - int(game.bx); dy = SH//2 - int(game.by)
        dist = math.hypot(dx,dy)
        if dist > 1:
            ndx,ndy = dx/dist, dy/dist
            tip=(cx+int(ndx*18),cy+int(ndy*18))
            px_,py_ = -ndy, ndx
            b1=(cx+int((-ndx+px_*0.5)*10),cy+int((-ndy+py_*0.5)*10))
            b2=(cx+int((-ndx-px_*0.5)*10),cy+int((-ndy-py_*0.5)*10))
            pygame.draw.polygon(self.screen,PALETTE["goal"],[tip,b1,b2])
        lbl=self.font_small.render("EXIT",True,PALETTE["goal"])
        self.screen.blit(lbl,(cx-lbl.get_width()//2,cy+32))
        dt2=self.font_small.render(f"Deaths:{game.total_deaths}",True,(160,160,180))
        self.screen.blit(dt2,(cx+36,cy+32))

    def _draw_crosshair(self, game):
        """Draw a crosshair at the mouse cursor position when gun is active."""
        if not game.has_gun or game.state != "play":
            return
        mx, my = getattr(game, 'mouse_pos', pygame.mouse.get_pos())

        # Always yellow – ammo is unlimited
        col  = (255, 240, 60)
        col2 = (255, 255, 180)
        size = 16
        gap  = 5

        pygame.draw.line(self.screen, col, (mx - size, my), (mx - gap, my), 2)
        pygame.draw.line(self.screen, col, (mx + gap,  my), (mx + size, my), 2)
        pygame.draw.line(self.screen, col, (mx, my - size), (mx, my - gap), 2)
        pygame.draw.line(self.screen, col, (mx, my + gap),  (mx, my + size), 2)
        pygame.draw.circle(self.screen, col2, (mx, my), 2)
        pygame.draw.circle(self.screen, col,  (mx, my), gap + 2, 1)

        # Aim tracer: short dashed line from ball toward cursor
        import math as _math
        dx = mx - game.bx; dy = my - game.by
        dist = _math.hypot(dx, dy)
        if dist > game.ball_r + 10:
            ndx = dx / dist; ndy = dy / dist
            sx  = int(game.bx + ndx * (game.ball_r + 4))
            sy  = int(game.by + ndy * (game.ball_r + 4))
            ex  = int(game.bx + ndx * min(dist - 6, 90))
            ey  = int(game.by + ndy * min(dist - 6, 90))
            dash_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
            pygame.draw.line(dash_surf, (*col, 55), (sx, sy), (ex, ey), 1)
            self.screen.blit(dash_surf, (0, 0))

    def _draw_hints(self, game):
        idx = game.level_idx
        if game.state != "play": return
        lines = []
        if idx == 0 and game.total_deaths == 0:
            lines.append(("WASD / Arrows: Move  |  SPACE/W: Jump (×2)  |  ESC: Quit",
                          (140,140,160)))
            lines.append(("🌀 Purple edges are PORTALS – fly into one to warp to the other side!",
                          (200, 130, 255)))
        if game.has_gun and idx == TIER_SPINNER_END and game.total_deaths == 0:
            lines.append(("🔫 LEFT CLICK to shoot toward crosshair  |  Unlimited ammo",
                          (255,255,100)))
        y = SH - 38
        for txt, col in reversed(lines):
            s = self.font_tiny.render(txt, True, col)
            self.screen.blit(s, (SW//2-s.get_width()//2, y))
            y -= 24

    # ─────────────────────────────────────────────────────── overlays ──

    def _draw_overlay(self, game):
        if game.state == "level_clear":
            lt   = getattr(game, 'level_time', 0.0)
            best = getattr(game, 'best_times', {}).get(game.level_idx, None)
            mins, secs = divmod(int(lt), 60)
            time_str = f"{mins:02d}:{secs:02d}"
            is_best  = best is not None and abs(lt - best) < 0.1
            sub = f"Time: {time_str}{'  ★ BEST!' if is_best else ''}  |  Score: {getattr(game,'score',0):,}  |  ENTER to continue"
            self._overlay("LEVEL CLEAR!", (50,255,150), sub)
        elif game.state == "game_over":
            self._overlay("GAME OVER", (255,60,60),
                          f"Score: {getattr(game,'score',0):,}  |  Deaths: {game.total_deaths}  |  R: restart  |  M: menu")
        elif game.state == "win":
            self._overlay("YOU WIN!", (255,220,50),
                          f"Score: {getattr(game,'score',0):,}  |  Deaths: {game.total_deaths}  |  R: play again  |  M: menu")

    def _overlay(self, title, color, sub=""):
        panel = pygame.Surface((SW,SH), pygame.SRCALPHA)
        panel.fill((0,0,0,160))
        self.screen.blit(panel,(0,0))
        ts = self.font_big.render(title, True, color)
        self.screen.blit(ts,(SW//2-ts.get_width()//2, SH//2-80))
        if sub:
            ss = self.font_med.render(sub, True, PALETTE["text"])
            self.screen.blit(ss,(SW//2-ss.get_width()//2, SH//2+20))