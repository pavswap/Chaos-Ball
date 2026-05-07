"""
game.py  –  Android version.
Same core logic as gameVersion7/game.py but input comes from TouchControls
instead of the keyboard.
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

_UNLIMITED   = -1
_SHOOT_COOLDOWN = 0.15


class _DummySound:
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

    def _init_sounds(self):
        self.sounds = {
            "jump":        _load_sound("assets/sounds/Retro/jump.wav"),
            "shoot":       _load_sound("assets/sounds/Retro/throw.wav"),
            "coin":        _load_sound("assets/sounds/Retro/coin.wav"),
            "respawn":     _load_sound("assets/sounds/Retro/power_up.wav"),
            "hit":         _load_sound("assets/sounds/Retro/hurt.wav"),
            "level_clear": _load_sound("assets/sounds/Musical Effects/8_bit_level_complete.wav"),
            "boost":       _load_sound("assets/sounds/Other/whoosh_1.wav"),
            "enemy_hit":   _load_sound("assets/sounds/Retro/explosion_quick.wav"),
            "dash":        _load_sound("assets/sounds/Other/whoosh_2.wav"),
        }
        for k,v in [("jump",0.3),("shoot",0.2),("coin",0.4),("respawn",0.5),
                    ("hit",0.3),("level_clear",0.5),("boost",0.4),
                    ("enemy_hit",0.3),("dash",0.3)]:
            self.sounds[k].set_volume(v)

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
        self.mouse_pos    = (SW//2, SH//2)
        self._shoot_timer = 0.0
        self.screen_shake    = 0.0
        self.shake_strength  = 0
        self.trail_points    = []
        self.slowmo_timer    = 0.0
        self.portal_streak   = 0
        self.score           = 0
        self.coin_combo      = 0
        self.coin_combo_timer= 0.0
        self.combo_text      = ""
        self.level_time      = 0.0
        self.best_times      = {}
        self.gravity_announce_timer = 0.0
        self.gravity_announce_text  = ""
        self.invincible_timer= 0.0
        self.dash_timer          = 0.0
        self.dash_cooldown_timer = 0.0
        self.coyote_timer      = 0.0
        self.jump_buffer_timer = 0.0
        self.freeze_timer   = 0.0
        self._pending_death = False
        self.kill_streak       = 0
        self.kill_streak_timer = 0.0
        self.floating_texts = []
        self.squash = 1.0
        self.level_deaths        = 0
        self.total_enemies_killed= 0
        # Touch state carried over between frames
        self._touch_joy_x = 0.0
        self._touch_joy_y = 0.0
        self.load_level()

    def start_at(self, level_idx):
        self.reset_all()
        self.level_idx = level_idx
        self.load_level()

    def load_level(self):
        data = LEVELS_DATA[self.level_idx % NUM_LEVELS]
        self.platforms = [pygame.Rect(*scale_rect(p)) for p in data["platforms"]]
        self.spikes    = [(pygame.Rect(*scale_rect(s[:4])), s[4]) for s in data["spikes"]]
        self.goal_rect = pygame.Rect(*scale_rect(data["goal"]))

        sx, sy = scale_pt(data["spawn"])
        self.ball_r     = int(22 * SW / 1920)
        self.bx = float(sx); self.by = float(sy)
        self.bvx = 0.0;      self.bvy = 0.0
        self.on_ground  = False
        self.jumps_left = 2

        self.rotators = [RotatingObstacle(p,al,at,sp)
                         for p,al,at,sp in data.get("rotators",[])]
        self.enemies  = [FlyingEnemy(pos,spd)
                         for pos,spd in data.get("enemies",[])]
        self.shooters = [ShootingEnemy(pos,fi)
                         for pos,fi in data.get("shooters",[])]
        self.enemy_projectiles = []

        raw_vw = data.get("void_walls",[])
        self.void_walls = [VoidWall(ori,side) for ori,side in raw_vw]
        vert  = [vw for vw in self.void_walls if vw.is_vertical]
        horiz = [vw for vw in self.void_walls if not vw.is_vertical]
        for vw in vert:  vw.set_partner(vert[0]  if len(vert)  > 1 else vw)
        for vw in horiz: vw.set_partner(horiz[0] if len(horiz) > 1 else vw)

        self.has_gun            = data.get("has_gun", False)
        self.ammo               = _UNLIMITED if self.has_gun else 0
        self.player_projectiles = []

        self.coins = [[int(cx*SW/1920), int(cy*SH/1080), True]
                      for cx,cy in data.get("coins",[])]
        self.boost_pads = [(int(cx*SW/1920), int(cy*SH/1080), direction)
                           for cx,cy,direction in data.get("boost_pads",[])]

        self.particles = []; self.flashes = []
        self.level_time = 0.0
        self.coin_combo = 0; self.coin_combo_timer = 0.0
        self.coins_rewarded = False
        self.level_deaths = 0
        self.coyote_timer = 0.0; self.jump_buffer_timer = 0.0

    # ────────────────────────────────── Android event handler ──────────────

    def handle_event_android(self, event):
        """Handle system-level events (quit / back button)."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_AC_BACK):
                # Android back button: return to menu or quit
                if self.state in ("game_over","win","level_clear"):
                    self.reset_all()

    # ──────────────────────────────────── Android update ───────────────────

    def update_android(self, dt, touch):
        """
        Main update driven by touch state dict from TouchControls.get_state().
        """
        self._touch_joy_x = touch["joy_x"]
        self._touch_joy_y = touch["joy_y"]
        self.mouse_pos = touch["shoot_target"] or (SW//2, SH//2)

        self._tick_effects(dt)
        if self.state != "play":
            return

        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0 and self._pending_death:
                self._execute_respawn()
            return

        self.level_time += dt
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
        if self.coyote_timer > 0:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
            if self.coyote_timer <= 0 and not self.on_ground and self.jumps_left == 2:
                self.jumps_left = 1
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

        # Handle one-shot touch actions
        if touch["jump"]:
            self._try_jump()
        if touch["dash"]:
            self._try_dash_android()
        if touch["shoot"] and touch["shoot_target"] and self.has_gun:
            self._try_shoot(touch["shoot_target"])

        # Level-clear advance: tap anywhere
        if self.state == "level_clear":
            if touch["jump"] or touch["dash"]:
                self.level_idx += 1
                if self.level_idx >= NUM_LEVELS:
                    self.state = "win"
                else:
                    self.state = "play"
                    self.load_level()
            return

        _prev_ground = self.on_ground
        _pre_speed   = math.hypot(self.bvx, self.bvy)
        self.on_ground = False

        if self.dash_timer <= 0:
            self._apply_movement_android(dt)
            self._apply_gravity(dt)
            self._cap_velocity()

        self._move_x(dt); self._move_y(dt)
        self._check_screen_walls()
        if self._pending_death or self.state != "play":
            return

        just_landed = self.on_ground and not _prev_ground
        if just_landed:
            self.squash = 0.6
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0.0
                self._try_jump()

        if just_landed and _pre_speed > 500:
            strength = min(_pre_speed/1200.0, 1.0)
            for _ in range(int(10*strength)):
                p = Particle(self.bx, self.by, (150,180,220))
                p.vx *= 0.5; p.vy *= -0.3
                self.particles.append(p)
            if strength > 0.5:
                self.screen_shake   = 0.08*strength
                self.shake_strength = int(4*strength)

        if _prev_ground and not self.on_ground and self.jumps_left == 2:
            self.coyote_timer = COYOTE_TIME

        self._check_void_walls()
        self._check_spikes()
        if self._pending_death or self.state != "play": return
        self._check_rotators(dt)
        if self._pending_death or self.state != "play": return
        self._check_coins()
        self._check_boost_pads()
        self._check_enemies(dt)
        if self.state != "play": return
        self._check_shooters(dt)
        if self.state != "play": return
        self._tick_player_projectiles(dt)
        self._check_goal()

    # ─────────────────────────────── touch-adapted movement ────────────────

    def _apply_movement_android(self, dt):
        """Use joystick instead of keyboard."""
        gx, gy = self.gravity_dir
        a = 4000 * dt
        jx = self._touch_joy_x
        jy = self._touch_joy_y

        if gy != 0:   # vertical gravity → horizontal movement from joystick X
            if abs(jx) > 0.15:
                self.bvx += jx * a * 1.2
            self.bvx *= 0.80
        else:          # horizontal gravity → vertical movement from joystick Y
            if abs(jy) > 0.15:
                self.bvy += jy * a * 1.2
            self.bvy *= 0.80

    def _try_dash_android(self):
        if self.dash_cooldown_timer > 0:
            return
        gx, gy = self.gravity_dir
        jx = self._touch_joy_x; jy = self._touch_joy_y
        if abs(jx) > 0.2 or abs(jy) > 0.2:
            dist = math.hypot(jx, jy)
            dx = jx/dist; dy = jy/dist
        else:
            dx = float(-gx); dy = float(-gy)
        dist = math.hypot(dx, dy)
        if dist > 0: dx /= dist; dy /= dist
        self.bvx = dx * DASH_SPEED
        self.bvy = dy * DASH_SPEED
        self.dash_timer          = DASH_DURATION
        self.dash_cooldown_timer = DASH_COOLDOWN
        self.sounds["dash"].play()
        for _ in range(15):
            p = Particle(self.bx, self.by, (100,200,255))
            p.vx *= 0.3; p.vy *= 0.3
            self.particles.append(p)
        self.flashes.append(Flash((100,180,255), 0.08))

    # ─────────────────── shared helpers (same as desktop version) ──────────

    def _trigger_death(self):
        self.total_deaths += 1; self.level_deaths += 1; self.hearts -= 1
        self.sounds["respawn"].play()
        for _ in range(40):
            self.particles.append(Particle(self.bx, self.by, (255,80,50)))
        self.flashes.append(Flash((255,60,60), 0.4))
        if self.hearts <= 0:
            self.state = "game_over"; return
        self.freeze_timer   = DEATH_FREEZE_TIME
        self._pending_death = True

    def _execute_respawn(self):
        self._pending_death = False
        old_gravity = self.gravity_dir
        self.gravity_dir = random.choice(GRAVITY_DIRS)
        if old_gravity != self.gravity_dir:
            self.walls_deadly = False
            dir_names = {(0,1):"DOWN",(0,-1):"UP",(1,0):"RIGHT",(-1,0):"LEFT"}
            self.gravity_announce_text  = f"GRAVITY: {dir_names.get(self.gravity_dir,'?')}"
            self.gravity_announce_timer = 2.2
        elif random.random() < 0.4:
            self.walls_deadly = not self.walls_deadly
        self.bg_color_idx = (self.bg_color_idx+1) % len(BG_COLORS)
        self.load_level()
        self.jumps_left = 2
        self.invincible_timer = INVINCIBLE_DURATION

    def lose_heart(self):
        if self.invincible_timer > 0 or self.dash_timer > 0: return
        self.hearts -= 1
        self.sounds["hit"].play()
        self.flashes.append(Flash((180,0,200), 0.35))
        for _ in range(20):
            self.particles.append(Particle(self.bx, self.by, (200,80,255)))
        if self.hearts <= 0:
            self.state = "game_over"

    def _try_shoot(self, target_pos):
        if self._shoot_timer > 0: return
        mx,my = target_pos
        dx = mx-self.bx; dy = my-self.by
        dist = math.hypot(dx,dy)
        if dist < 1: return
        self.player_projectiles.append(
            PlayerProjectile(self.bx, self.by, dx/dist*GUN_PROJ_SPEED, dy/dist*GUN_PROJ_SPEED))
        self._shoot_timer = _SHOOT_COOLDOWN
        self.sounds["shoot"].play()
        for _ in range(8):
            p = Particle(self.bx, self.by, (255,255,100))
            p.vx *= 0.4; p.vy *= 0.4
            self.particles.append(p)

    def _try_jump(self):
        can_jump = self.jumps_left > 0
        if not can_jump and self.coyote_timer > 0:
            can_jump = True; self.jumps_left = 1; self.coyote_timer = 0.0
        if not can_jump:
            self.jump_buffer_timer = JUMP_BUFFER_TIME; return
        gx,gy = self.gravity_dir
        self.bvx -= gx*700; self.bvy -= gy*700
        self.jumps_left -= 1; self.on_ground = False; self.coyote_timer = 0.0
        self.sounds["jump"].play(); self.squash = 1.4
        if self.jumps_left == 0:
            for _ in range(18):
                p = Particle(self.bx, self.by, (150,200,255))
                p.vx *= 0.6; p.vy *= 0.6; self.particles.append(p)

    def _apply_gravity(self, dt):
        gx,gy = self.gravity_dir
        self.bvx += gx*GRAVITY_STRENGTH*dt; self.bvy += gy*GRAVITY_STRENGTH*dt

    def _cap_velocity(self):
        mv=1200
        self.bvx=max(-mv,min(mv,self.bvx)); self.bvy=max(-mv,min(mv,self.bvy))

    def _move_x(self, dt):
        self.bx += self.bvx*dt
        rect = self._ball_rect(); gx,gy = self.gravity_dir
        for p in self.platforms:
            if rect.colliderect(p):
                if self.bvx>0: self.bx=p.left-self.ball_r; (self.on_ground:=gx>0) and setattr(self,'jumps_left',2)
                elif self.bvx<0: self.bx=p.right+self.ball_r; (self.on_ground:=gx<0) and setattr(self,'jumps_left',2)
                if self.bvx>0 and gx>0: self.on_ground=True; self.jumps_left=2
                elif self.bvx<0 and gx<0: self.on_ground=True; self.jumps_left=2
                self.bvx=0; rect=self._ball_rect()

    def _move_y(self, dt):
        self.by += self.bvy*dt
        rect=self._ball_rect(); gx,gy=self.gravity_dir
        for p in self.platforms:
            if rect.colliderect(p):
                if self.bvy>0: self.by=p.top-self.ball_r; (gy>0) and setattr(self,'on_ground',True) or None; (gy>0) and setattr(self,'jumps_left',2)
                elif self.bvy<0: self.by=p.bottom+self.ball_r; (gy<0) and setattr(self,'on_ground',True) or None; (gy<0) and setattr(self,'jumps_left',2)
                if self.bvy>0 and gy>0: self.on_ground=True; self.jumps_left=2
                elif self.bvy<0 and gy<0: self.on_ground=True; self.jumps_left=2
                self.bvy=0; rect=self._ball_rect()

    def _check_screen_walls(self):
        gx,gy=self.gravity_dir; died=False
        if self.bx-self.ball_r<0:
            self.bx=float(self.ball_r); self.bvx=abs(self.bvx)*0.4
            if gx<0: self.on_ground=True; self.jumps_left=2
            if self.walls_deadly: died=True
        if self.bx+self.ball_r>SW:
            self.bx=float(SW-self.ball_r); self.bvx=-abs(self.bvx)*0.4
            if gx>0: self.on_ground=True; self.jumps_left=2
            if self.walls_deadly: died=True
        if self.by-self.ball_r<0:
            self.by=float(self.ball_r); self.bvy=abs(self.bvy)*0.4
            if gy<0: self.on_ground=True; self.jumps_left=2
            if self.walls_deadly: died=True
        if self.by+self.ball_r>SH:
            self.by=float(SH-self.ball_r); self.bvy=-abs(self.bvy)*0.4
            if gy>0: self.on_ground=True; self.jumps_left=2
            if self.walls_deadly: died=True
        if died and self.invincible_timer<=0 and self.dash_timer<=0:
            self._trigger_death()

    def _check_void_walls(self):
        for vw in self.void_walls:
            result = vw.check_teleport(self.bx, self.by, self.ball_r)
            if result:
                old_x,old_y=self.bx,self.by
                self.bx,self.by=float(result[0]),float(result[1])
                self.portal_streak+=1; intensity=min(self.portal_streak,4)
                self.screen_shake=0.18+0.06*intensity; self.shake_strength=6+4*intensity
                self.slowmo_timer=0.12+0.04*intensity
                rainbow_cols=[(255,60,60),(255,160,30),(255,255,40),(60,255,80),(40,180,255),(180,60,255)]
                for _ in range(30+10*intensity):
                    self.particles.append(Particle(old_x,old_y,random.choice(rainbow_cols)))
                    self.particles.append(Particle(self.bx,self.by,random.choice(rainbow_cols)))
                self.flashes.append(Flash(rainbow_cols[(self.portal_streak-1)%len(rainbow_cols)],0.20+0.05*intensity))
                break

    def _check_spikes(self):
        if self.invincible_timer>0 or self.dash_timer>0: return
        rect=self._ball_rect(shrink=6)
        for sr,_ in self.spikes:
            if rect.colliderect(sr): self._trigger_death(); return

    def _check_rotators(self,dt):
        for rot in self.rotators:
            rot.update(dt)
            if rot.collides_with_ball(self.bx,self.by,self.ball_r):
                if self.invincible_timer<=0 and self.dash_timer<=0:
                    self._trigger_death(); return

    def _check_enemies(self,dt):
        for enemy in self.enemies:
            enemy.update(dt,self.bx,self.by)
            if enemy.try_hit(self.bx,self.by,self.ball_r):
                self.lose_heart()
                if self.state=="game_over": return
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for enemy in self.enemies:
                if not enemy.alive: continue
                if proj.hits_enemy(enemy.x,enemy.y,enemy.RADIUS):
                    enemy.alive=False; proj.alive=False
                    self.sounds["enemy_hit"].play(); self.total_enemies_killed+=1
                    self.kill_streak+=1; self.kill_streak_timer=KILL_COMBO_WINDOW
                    multiplier=min(self.kill_streak,5); points=50*multiplier; self.score+=points
                    self.floating_texts.append([enemy.x,enemy.y,f"+{points}",(255,220,50),1.0])
                    for _ in range(25): self.particles.append(Particle(enemy.x,enemy.y,(200,80,255)))
                    break

    def _check_shooters(self,dt):
        for shooter in self.shooters:
            shooter.update(dt,self.bx,self.by)
            ep=shooter.try_fire()
            if ep: self.enemy_projectiles.append(ep)
        for ep in self.enemy_projectiles:
            ep.update(dt)
            if ep.hits_ball(self.bx,self.by,self.ball_r):
                ep.alive=False; self.lose_heart()
                if self.state=="game_over": return
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for shooter in self.shooters:
                if not shooter.alive: continue
                if proj.hits_enemy(shooter.x,shooter.y,shooter.RADIUS):
                    shooter.alive=False; proj.alive=False
                    self.sounds["enemy_hit"].play(); self.total_enemies_killed+=1
                    self.kill_streak+=1; self.kill_streak_timer=KILL_COMBO_WINDOW
                    multiplier=min(self.kill_streak,5); points=75*multiplier; self.score+=points
                    self.floating_texts.append([shooter.x,shooter.y,f"+{points}",(255,220,50),1.0])
                    for _ in range(30): self.particles.append(Particle(shooter.x,shooter.y,(255,60,60)))
                    break
        self.enemy_projectiles=[ep for ep in self.enemy_projectiles if ep.alive]

    def _tick_player_projectiles(self,dt):
        for proj in self.player_projectiles: proj.update(dt)
        self.player_projectiles=[p for p in self.player_projectiles if p.alive]

    def _check_coins(self):
        COIN_R=int(14*SW/1920)
        for coin in self.coins:
            cx,cy,alive=coin
            if not alive: continue
            if math.hypot(self.bx-cx,self.by-cy)<self.ball_r+COIN_R:
                coin[2]=False; self.coin_combo+=1; self.coin_combo_timer=1.5
                points=10*self.coin_combo; self.score+=points; self.sounds["coin"].play()
                for _ in range(16):
                    p=Particle(cx,cy,(255,220,40)); p.vx*=0.7; p.vy*=0.7; self.particles.append(p)
                self.floating_texts.append([cx,cy,f"+{points}",(255,220,40),1.0])
                self.combo_text=f"COMBO x{self.coin_combo}!  +{points}" if self.coin_combo>=3 else f"+{points}"
        if not self.coins_rewarded and self.coins and all(not c[2] for c in self.coins):
            self.coins_rewarded=True
            if self.hearts<10:
                self.hearts+=1; self.flashes.append(Flash((50,255,100),0.35))
                for _ in range(30): self.particles.append(Particle(self.bx,self.by,(50,255,100)))

    def _check_boost_pads(self):
        BOOST_SPEED=1100; PAD_W=int(70*SW/1920); PAD_H=int(20*SH/1080)
        for cx,cy,direction in self.boost_pads:
            pad_rect=pygame.Rect(cx-PAD_W//2,cy-PAD_H//2,PAD_W,PAD_H)
            if self._ball_rect().colliderect(pad_rect):
                boost_map={"up":(0,-BOOST_SPEED),"down":(0,BOOST_SPEED),"left":(-BOOST_SPEED,0),"right":(BOOST_SPEED,0)}
                dvx,dvy=boost_map[direction]; self.bvx=dvx; self.bvy=dvy
                self.sounds["boost"].play()
                for _ in range(20):
                    p=Particle(self.bx,self.by,(80,255,200)); p.vx=dvx*0.3+p.vx*0.3; p.vy=dvy*0.3+p.vy*0.3; self.particles.append(p)
                self.flashes.append(Flash((60,220,180),0.12)); break

    def _check_goal(self):
        if self._ball_rect(shrink=4).colliderect(self.goal_rect):
            self.state="level_clear"; self.sounds["level_clear"].play()
            prev=self.best_times.get(self.level_idx,None)
            if prev is None or self.level_time<prev: self.best_times[self.level_idx]=self.level_time
            self.flashes.append(Flash((50,255,150),0.5))
            for _ in range(60): self.particles.append(Particle(self.goal_rect.centerx,self.goal_rect.centery,(50,255,150)))

    def _tick_effects(self,dt):
        self.particles=[p for p in self.particles if p.alive]
        for p in self.particles: p.update(dt)
        self.flashes=[f for f in self.flashes if not f.done]
        for f in self.flashes: f.update(dt)
        for vw in self.void_walls: vw.update(dt)
        if self.screen_shake>0: self.screen_shake=max(0.0,self.screen_shake-dt)
        if self.slowmo_timer>0: self.slowmo_timer=max(0.0,self.slowmo_timer-dt)
        for pt in self.trail_points: pt[2]-=dt*1.8
        self.trail_points=[pt for pt in self.trail_points if pt[2]>0]
        if self.slowmo_timer>0 and self.state=="play":
            rainbow_cols=[(255,60,60),(255,160,30),(255,255,40),(60,255,80),(40,180,255),(180,60,255)]
            self.trail_points.append([self.bx,self.by,0.45,random.choice(rainbow_cols)])
        if self.state=="play":
            speed=math.hypot(self.bvx,self.bvy)
            if speed>600: self.trail_points.append([self.bx,self.by,0.2*min(1.0,(speed-600)/600.0),(255,80,50)])
        if self.dash_timer>0 and self.state=="play":
            self.trail_points.append([self.bx,self.by,0.35,(100,200,255)])
        if all(vw.cooldown==0 for vw in self.void_walls): self.portal_streak=0
        if self.coin_combo_timer>0:
            self.coin_combo_timer-=dt
            if self.coin_combo_timer<=0: self.coin_combo=0; self.combo_text=""
        if self.gravity_announce_timer>0: self.gravity_announce_timer=max(0.0,self.gravity_announce_timer-dt)
        if self.kill_streak_timer>0:
            self.kill_streak_timer-=dt
            if self.kill_streak_timer<=0: self.kill_streak=0
        for ft in self.floating_texts: ft[1]-=50*dt; ft[4]-=dt
        self.floating_texts=[ft for ft in self.floating_texts if ft[4]>0]
        self.squash+=(1.0-self.squash)*min(1.0,dt*12)

    def _ball_rect(self,shrink=0):
        r=self.ball_r-shrink
        return pygame.Rect(int(self.bx)-r,int(self.by)-r,r*2,r*2)
