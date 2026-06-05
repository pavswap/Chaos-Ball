"""
menu.py  –  Main menu and level-select screen.

Returns ("play", level_idx) or "quit" from Menu.run().
"""

import math
import pygame
from settings import SW, SH, NUM_LEVELS, PALETTE, TIER_BASIC_END, TIER_SPINNER_END, TIER_SHOOTER_START


# Tier appearance config used by the level grid
_TIERS = [
    (0,               TIER_BASIC_END,    "BASIC",    (70,180,255)),
    (TIER_BASIC_END,  TIER_SPINNER_END,  "SPINNERS", (255,160, 40)),
    (TIER_SPINNER_END,TIER_SHOOTER_START,"VOID",     ( 80,  0,180)),
    (TIER_SHOOTER_START, NUM_LEVELS,     "HAUNTED",  (200, 80,255)),
]

def _tier_for(idx):
    for start,end,label,col in _TIERS:
        if start <= idx < end:
            return label, col
    return "?", (200,200,200)


class Menu:
    """Blocks inside run() until the user picks a level or quits."""

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock  = clock
        self.font_xl  = pygame.font.SysFont("consolas", 96, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 52, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32, bold=True)
        self.font_sm  = pygame.font.SysFont("consolas", 22)
        self.font_xs  = pygame.font.SysFont("consolas", 16)
        self._state   = "main"
        self._hovered = 0
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
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._state == "select": self._state = "main"
                    else: return "quit"
                if self._state == "main":
                    r = self._handle_main_key(event.key)
                else:
                    r = self._handle_select_key(event.key)
                if r is not None: return r
            if event.type == pygame.MOUSEMOTION:
                self._handle_hover(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                r = self._handle_click(event.pos)
                if r is not None: return r
        return None

    # main menu keyboard
    def _handle_main_key(self, key):
        n = 3
        if key in (pygame.K_UP, pygame.K_w):
            self._hovered = (self._hovered-1) % n
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._hovered = (self._hovered+1) % n
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            return self._main_choose(self._hovered)
        return None

    def _main_choose(self, idx):
        if idx == 0: return ("play", 0)
        if idx == 1: self._state="select"; self._hovered=0; return None
        return "quit"

    # level select keyboard
    def _handle_select_key(self, key):
        cols = 4
        if key in (pygame.K_RIGHT,pygame.K_d):   self._hovered=min(NUM_LEVELS-1,self._hovered+1)
        elif key in (pygame.K_LEFT,pygame.K_a):  self._hovered=max(0,self._hovered-1)
        elif key in (pygame.K_DOWN,pygame.K_s):  self._hovered=min(NUM_LEVELS-1,self._hovered+cols)
        elif key in (pygame.K_UP,pygame.K_w):    self._hovered=max(0,self._hovered-cols)
        elif key in (pygame.K_RETURN,pygame.K_SPACE): return ("play",self._hovered)
        return None

    def _handle_hover(self, pos):
        if self._state=="main":
            for i in range(3):
                if self._btn_rect(i).collidepoint(pos): self._hovered=i
        else:
            t=self._tile_at(pos)
            if t is not None: self._hovered=t

    def _handle_click(self, pos):
        if self._state=="main":
            for i in range(3):
                if self._btn_rect(i).collidepoint(pos): return self._main_choose(i)
        else:
            t=self._tile_at(pos)
            if t is not None: return ("play",t)
            bx,by,bw,bh=self._back_rect()
            if bx<=pos[0]<=bx+bw and by<=pos[1]<=by+bh:
                self._state="main"
        return None

    # ───────────────────────────────────────────────── main menu draw ──

    def _draw_main(self):
        self.screen.fill((8,5,18))
        t = self._time
        # Animated star particles
        for i in range(32):
            angle = i*0.41+t*0.28
            x = int(SW/2+math.cos(angle)*(280+i*19))
            y = int(SH/2+math.sin(angle*1.27)*(180+i*11))
            r = max(1, 4-i//9)
            al = max(0,80-i*2)
            s = pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(80,130,255,al),(r,r),r)
            self.screen.blit(s,(x-r,y-r))

        # Title
        txt = "CHAOS BALL"
        shadow = self.font_xl.render(txt,True,(90,20,10))
        title  = self.font_xl.render(txt,True,(255,80,50))
        ty = SH//4
        self.screen.blit(shadow,(SW//2-title.get_width()//2+4,ty+4))
        self.screen.blit(title, (SW//2-title.get_width()//2, ty))

        # Subtitle
        sub = self.font_sm.render(
            "Die to change gravity  ·  Chaos rules  ·  20 levels of madness",
            True,(140,140,180))
        self.screen.blit(sub,(SW//2-sub.get_width()//2, ty+96))

        # Tier preview
        tx2 = SW//2 - 420
        for start,end,label,col in _TIERS:
            blk = self.font_xs.render(f"L{start+1}-{end}: {label}", True, col)
            self.screen.blit(blk,(tx2,ty+130)); tx2+=blk.get_width()+30

        # Buttons
        labels = ["PLAY",  "LEVEL SELECT",  "QUIT"]
        colors = [(50,255,150),(70,180,255),(255,80,100)]
        for i,(lbl,col) in enumerate(zip(labels,colors)):
            rect  = self._btn_rect(i)
            hov   = i==self._hovered
            bg    = tuple(min(255,c//3+(55 if hov else 0)) for c in col)
            brd   = col if hov else tuple(c//2 for c in col)
            pygame.draw.rect(self.screen, bg,  rect, border_radius=10)
            pygame.draw.rect(self.screen, brd, rect, 3, border_radius=10)
            tc    = col if hov else tuple(c*2//3 for c in col)
            ts    = self.font_big.render(lbl, True, tc)
            self.screen.blit(ts,(rect.centerx-ts.get_width()//2,
                                  rect.centery-ts.get_height()//2))

        hint = self.font_sm.render(
            "↑↓ / Mouse to navigate  ·  ENTER to select  ·  ESC to quit",
            True,(70,70,100))
        self.screen.blit(hint,(SW//2-hint.get_width()//2, SH-40))

    def _btn_rect(self, idx):
        bw,bh=400,70
        return pygame.Rect(SW//2-bw//2, SH//2-50+idx*100, bw, bh)

    # ──────────────────────────────────────────────── level select draw ──

    def _draw_select(self):
        self.screen.fill((6,6,20))
        title=self.font_big.render("SELECT LEVEL",True,PALETTE["text"])
        self.screen.blit(title,(SW//2-title.get_width()//2,26))

        # Tier legend
        lx=60
        for _,_,label,col in _TIERS:
            s=self.font_sm.render(f"● {label}",True,col)
            self.screen.blit(s,(lx,88)); lx+=s.get_width()+40

        # Tiles  (4 columns × 5 rows = 20)
        cols=4; tw,th=210,130; pad=28
        total_w=cols*(tw+pad)-pad
        start_x=SW//2-total_w//2; start_y=126

        for idx in range(NUM_LEVELS):
            ci=idx%cols; ri=idx//cols
            tx=start_x+ci*(tw+pad); ty=start_y+ri*(th+pad)
            rect=pygame.Rect(tx,ty,tw,th)
            lbl,col=_tier_for(idx)
            hov=(idx==self._hovered)

            # Background
            bg=tuple(min(255,c//4+(38 if hov else 0)) for c in col)
            pygame.draw.rect(self.screen,bg,rect,border_radius=12)
            pygame.draw.rect(self.screen,col,rect,4 if hov else 2,border_radius=12)

            # Level number
            num=self.font_big.render(str(idx+1),True,
                                      col if hov else tuple(c*2//3 for c in col))
            self.screen.blit(num,(rect.centerx-num.get_width()//2,
                                   rect.centery-num.get_height()//2-10))

            # Tier badge
            bdg=self.font_xs.render(lbl,True,col)
            self.screen.blit(bdg,(rect.centerx-bdg.get_width()//2,rect.bottom-22))

            # Feature icons under number
            icons=[]
            if idx>=TIER_SPINNER_END: icons.append("🌀")
            if idx>=TIER_SPINNER_END: icons.append("🔫")
            if idx>=TIER_SHOOTER_START: icons.append("👻")
            if idx>=TIER_SHOOTER_START: icons.append("🔴")
            if icons:
                ics=self.font_xs.render(" ".join(icons),True,(180,180,200))
                self.screen.blit(ics,(rect.centerx-ics.get_width()//2,
                                      rect.centery+14))

        # Back button
        bx,by,bw2,bh2=self._back_rect()
        brect=pygame.Rect(bx,by,bw2,bh2)
        pygame.draw.rect(self.screen,(35,25,55),brect,border_radius=8)
        pygame.draw.rect(self.screen,(110,70,170),brect,2,border_radius=8)
        btxt=self.font_med.render("← BACK",True,(180,130,255))
        self.screen.blit(btxt,(bx+bw2//2-btxt.get_width()//2,
                                by+bh2//2-btxt.get_height()//2))

        hint=self.font_sm.render(
            "Arrows/Mouse: navigate  ·  ENTER: play  ·  ESC: back",
            True,(70,70,100))
        self.screen.blit(hint,(SW//2-hint.get_width()//2,SH-36))

    def _back_rect(self):
        return (50, SH-76, 160, 46)

    def _tile_rect(self, idx):
        cols=4; tw,th=210,130; pad=28
        total_w=cols*(tw+pad)-pad
        start_x=SW//2-total_w//2; start_y=126
        ci=idx%cols; ri=idx//cols
        return pygame.Rect(start_x+ci*(tw+pad), start_y+ri*(th+pad), tw, th)

    def _tile_at(self, pos):
        if self._state!="select": return None
        for i in range(NUM_LEVELS):
            if self._tile_rect(i).collidepoint(pos): return i
        return None
