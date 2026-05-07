"""
menu.py  –  Android version. Large touch-friendly buttons, no keyboard nav.
"""

import math
import pygame
from settings import SW, SH, NUM_LEVELS, PALETTE, TIER_BASIC_END, TIER_SPINNER_END, TIER_SHOOTER_START

_TIERS = [
    (0,                TIER_BASIC_END,     "BASIC",    (70,180,255)),
    (TIER_BASIC_END,   TIER_SPINNER_END,   "SPINNERS", (255,160, 40)),
    (TIER_SPINNER_END, TIER_SHOOTER_START, "VOID",     ( 80,  0,180)),
    (TIER_SHOOTER_START, NUM_LEVELS,       "HAUNTED",  (200, 80,255)),
]

def _tier_for(idx):
    for start,end,label,col in _TIERS:
        if start <= idx < end:
            return label, col
    return "?", (200,200,200)


class Menu:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock  = clock

        # Scale fonts to screen size
        base = min(SW, SH)
        self.font_xl  = pygame.font.SysFont("consolas", int(base*0.10), bold=True)
        self.font_big = pygame.font.SysFont("consolas", int(base*0.055), bold=True)
        self.font_med = pygame.font.SysFont("consolas", int(base*0.036), bold=True)
        self.font_sm  = pygame.font.SysFont("consolas", int(base*0.026))
        self.font_xs  = pygame.font.SysFont("consolas", int(base*0.020))

        self._state   = "main"
        self._time    = 0.0

    # ────────────────────────────────────────────────────── public api ──

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self._time += dt
            result = self._handle_events()
            if result is not None:
                return result
            if self._state == "main":
                self._draw_main()
            else:
                self._draw_select()
            pygame.display.flip()

    # ─────────────────────────────────────────────────────────── events ──

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self._state == "select":
                    self._state = "main"
                else:
                    return "quit"

            # Touch / mouse
            pos = None
            if event.type == pygame.FINGERDOWN:
                pos = (int(event.x * SW), int(event.y * SH))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

            if pos:
                r = self._handle_tap(pos)
                if r is not None:
                    return r
        return None

    def _handle_tap(self, pos):
        if self._state == "main":
            for i in range(3):
                if self._btn_rect(i).collidepoint(pos):
                    return self._main_choose(i)
        else:
            # Level tiles
            t = self._tile_at(pos)
            if t is not None:
                return ("play", t)
            # Back button
            if self._back_rect_obj().collidepoint(pos):
                self._state = "main"
        return None

    def _main_choose(self, idx):
        if idx == 0: return ("play", 0)
        if idx == 1: self._state = "select"; return None
        return "quit"

    # ───────────────────────────────────────────── main menu draw ──

    def _draw_main(self):
        self.screen.fill((8, 5, 18))
        t = self._time

        # Stars
        for i in range(40):
            angle = i*0.41 + t*0.22
            x = int(SW/2 + math.cos(angle)*(SW*0.35 + i*SW*0.008))
            y = int(SH/2 + math.sin(angle*1.27)*(SH*0.30 + i*SH*0.006))
            r = max(2, 5-i//10)
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (80,130,255,max(0,90-i*2)), (r,r), r)
            self.screen.blit(s, (x-r, y-r))

        # Title
        txt    = "CHAOS BALL"
        shadow = self.font_xl.render(txt, True, (90, 20, 10))
        title  = self.font_xl.render(txt, True, (255, 80, 50))
        ty     = int(SH * 0.12)
        self.screen.blit(shadow, (SW//2-title.get_width()//2+4, ty+4))
        self.screen.blit(title,  (SW//2-title.get_width()//2,   ty))

        sub = self.font_sm.render("Die to change gravity  ·  20 levels of madness",
                                  True, (140,140,180))
        self.screen.blit(sub, (SW//2-sub.get_width()//2, ty+title.get_height()+8))

        # Buttons (extra tall for finger-friendly tapping)
        labels = ["▶  PLAY", "☰  LEVEL SELECT", "✕  QUIT"]
        colors = [(50,255,150),(70,180,255),(255,80,100)]
        for i,(lbl,col) in enumerate(zip(labels,colors)):
            rect = self._btn_rect(i)
            bg   = tuple(min(255,c//4) for c in col)
            pygame.draw.rect(self.screen, bg,  rect, border_radius=18)
            pygame.draw.rect(self.screen, col, rect, 4, border_radius=18)
            ts = self.font_big.render(lbl, True, col)
            self.screen.blit(ts, (rect.centerx-ts.get_width()//2,
                                   rect.centery-ts.get_height()//2))

        hint = self.font_xs.render("Tap a button to start", True, (70,70,100))
        self.screen.blit(hint, (SW//2-hint.get_width()//2, SH-int(SH*0.04)))

    def _btn_rect(self, idx):
        bw = int(SW * 0.55)
        bh = int(SH * 0.10)
        gap = int(SH * 0.025)
        total = 3*bh + 2*gap
        start_y = SH//2 - total//2 + int(SH*0.06)
        return pygame.Rect(SW//2-bw//2, start_y + idx*(bh+gap), bw, bh)

    # ──────────────────────────────────────────── level select draw ──

    def _draw_select(self):
        self.screen.fill((6,6,20))
        title = self.font_big.render("SELECT LEVEL", True, PALETTE["text"])
        self.screen.blit(title, (SW//2-title.get_width()//2, int(SH*0.02)))

        # Tier legend
        lx = int(SW*0.03)
        for _,_,label,col in _TIERS:
            s = self.font_xs.render(f"● {label}", True, col)
            self.screen.blit(s, (lx, int(SH*0.08)))
            lx += s.get_width() + int(SW*0.03)

        # Tiles – 4 columns, 5 rows
        cols = 4
        pad  = int(min(SW,SH)*0.018)
        tw   = (SW - pad*(cols+1)) // cols
        th   = int(SH * 0.14)
        start_x = pad
        start_y = int(SH * 0.12)

        for idx in range(NUM_LEVELS):
            ci = idx % cols
            ri = idx // cols
            tx = start_x + ci*(tw+pad)
            ty = start_y + ri*(th+pad)
            rect = pygame.Rect(tx, ty, tw, th)
            lbl, col = _tier_for(idx)

            bg = tuple(min(255,c//4) for c in col)
            pygame.draw.rect(self.screen, bg,  rect, border_radius=12)
            pygame.draw.rect(self.screen, col, rect, 3, border_radius=12)

            num = self.font_big.render(str(idx+1), True, col)
            self.screen.blit(num, (rect.centerx-num.get_width()//2,
                                    rect.centery-num.get_height()//2-int(th*0.08)))
            bdg = self.font_xs.render(lbl, True, col)
            self.screen.blit(bdg, (rect.centerx-bdg.get_width()//2,
                                    rect.bottom-bdg.get_height()-4))

        # Back button
        br = self._back_rect_obj()
        pygame.draw.rect(self.screen, (35,25,55), br, border_radius=12)
        pygame.draw.rect(self.screen, (110,70,170), br, 3, border_radius=12)
        btxt = self.font_med.render("← BACK", True, (180,130,255))
        self.screen.blit(btxt, (br.centerx-btxt.get_width()//2,
                                  br.centery-btxt.get_height()//2))

    def _back_rect_obj(self):
        w = int(SW*0.22)
        h = int(SH*0.07)
        return pygame.Rect(int(SW*0.03), SH-h-int(SH*0.02), w, h)

    def _tile_at(self, pos):
        cols = 4
        pad  = int(min(SW,SH)*0.018)
        tw   = (SW - pad*(cols+1)) // cols
        th   = int(SH * 0.14)
        start_x = pad
        start_y = int(SH * 0.12)
        for idx in range(NUM_LEVELS):
            ci = idx % cols; ri = idx // cols
            rect = pygame.Rect(start_x+ci*(tw+pad), start_y+ri*(th+pad), tw, th)
            if rect.collidepoint(pos):
                return idx
        return None
