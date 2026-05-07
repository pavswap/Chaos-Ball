"""
touch_controls.py  –  Virtual joystick + buttons for Android.

Layout (landscape):
  LEFT  side  → joystick  (move left/right / up/down depending on gravity)
  RIGHT side  → JUMP (big), DASH (smaller above), SHOOT (tap anywhere on right half)

All coordinates returned are in screen-space pixels.
"""

import math
import pygame
from settings import (
    SW, SH,
    TOUCH_BTN_RADIUS, JOYSTICK_RADIUS, JOYSTICK_KNOB_R, CONTROLS_ALPHA,
)


# ── colours ─────────────────────────────────────────────────────────────────
_COL_RING   = (100, 140, 255, 120)
_COL_KNOB   = (160, 200, 255, 200)
_COL_JUMP   = ( 50, 220, 120, 200)
_COL_DASH   = ( 80, 180, 255, 200)
_COL_SHOOT  = (255, 220,  50, 200)
_COL_PRESSED= (255, 255, 255,  80)


def _circle_surf(radius, color):
    s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    pygame.draw.circle(s, color, (radius, radius), radius)
    return s


class TouchControls:
    """
    Manages all on-screen touch input.

    Call  .handle_event(event)  every frame for every pygame event.
    Call  .get_state()          to read the current virtual input state.
    Call  .draw(screen)         to render the controls overlay.
    """

    def __init__(self):
        # Joystick centre position (bottom-left area)
        margin = int(SH * 0.08)
        self._joy_cx = JOYSTICK_RADIUS + margin
        self._joy_cy = SH - JOYSTICK_RADIUS - margin

        # Action button positions (bottom-right area)
        br_x = SW - TOUCH_BTN_RADIUS * 2 - int(SW * 0.04)
        br_y = SH - TOUCH_BTN_RADIUS    - int(SH * 0.05)
        self._jump_pos  = (br_x,                        br_y)
        self._dash_pos  = (br_x - TOUCH_BTN_RADIUS*3,   br_y - TOUCH_BTN_RADIUS)
        self._shoot_pos = (br_x + TOUCH_BTN_RADIUS*2,   br_y - TOUCH_BTN_RADIUS*2)

        # State
        self._joy_touch_id  = None
        self._joy_knob      = (0.0, 0.0)   # normalised -1..1
        self._jump_pressed  = False
        self._dash_pressed  = False
        self._shoot_pressed = False
        self._shoot_pos_world = None        # tap position for aiming

        # Pre-render surfaces
        self._surf_joy_ring  = _circle_surf(JOYSTICK_RADIUS, _COL_RING)
        self._surf_knob      = _circle_surf(JOYSTICK_KNOB_R, _COL_KNOB)
        self._surf_jump      = _circle_surf(TOUCH_BTN_RADIUS, _COL_JUMP)
        self._surf_dash      = _circle_surf(TOUCH_BTN_RADIUS, _COL_DASH)
        self._surf_shoot     = _circle_surf(TOUCH_BTN_RADIUS, _COL_SHOOT)
        self._surf_pressed   = _circle_surf(TOUCH_BTN_RADIUS, _COL_PRESSED)

        # Font for button labels
        try:
            self._font = pygame.font.SysFont("consolas", int(TOUCH_BTN_RADIUS * 0.7), bold=True)
        except Exception:
            self._font = pygame.font.Font(None, int(TOUCH_BTN_RADIUS * 0.7))

        # One-frame pulse tracking
        self._jump_consumed  = False
        self._dash_consumed  = False
        self._shoot_consumed = False

    # ─────────────────────────────────────── event handling ──────────────────

    def handle_event(self, event):
        """Feed every pygame event here. Returns nothing – read state via get_state()."""

        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            # pygame finger coords are 0.0-1.0 normalised
            fx = int(event.x * SW)
            fy = int(event.y * SH)
            fid = event.finger_id

            if event.type == pygame.FINGERDOWN:
                self._on_finger_down(fid, fx, fy)
            elif event.type == pygame.FINGERMOTION:
                self._on_finger_move(fid, fx, fy)
            elif event.type == pygame.FINGERUP:
                self._on_finger_up(fid, fx, fy)

        # Mouse events (for desktop testing)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_finger_down(-1, *event.pos)
        elif event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            self._on_finger_move(-1, *event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._on_finger_up(-1, *event.pos)

    def _on_finger_down(self, fid, fx, fy):
        # Joystick zone: left third of screen
        if fx < SW // 3:
            self._joy_touch_id = fid
            self._update_joystick(fx, fy)
        else:
            # Right side – check buttons
            if self._dist((fx, fy), self._jump_pos) < TOUCH_BTN_RADIUS * 1.4:
                self._jump_pressed  = True
                self._jump_consumed = False
            elif self._dist((fx, fy), self._dash_pos) < TOUCH_BTN_RADIUS * 1.4:
                self._dash_pressed  = True
                self._dash_consumed = False
            elif self._dist((fx, fy), self._shoot_pos) < TOUCH_BTN_RADIUS * 1.4:
                self._shoot_pressed   = True
                self._shoot_consumed  = False
                self._shoot_pos_world = (fx, fy)
            else:
                # Tap anywhere on right side → shoot toward that point
                self._shoot_pressed   = True
                self._shoot_consumed  = False
                self._shoot_pos_world = (fx, fy)

    def _on_finger_move(self, fid, fx, fy):
        if fid == self._joy_touch_id:
            self._update_joystick(fx, fy)

    def _on_finger_up(self, fid, fx, fy):
        if fid == self._joy_touch_id:
            self._joy_touch_id = None
            self._joy_knob = (0.0, 0.0)
        # Release buttons
        if self._dist((fx, fy), self._jump_pos) < TOUCH_BTN_RADIUS * 2:
            self._jump_pressed = False
        if self._dist((fx, fy), self._dash_pos) < TOUCH_BTN_RADIUS * 2:
            self._dash_pressed = False
        if self._dist((fx, fy), self._shoot_pos) < TOUCH_BTN_RADIUS * 2:
            self._shoot_pressed = False
        # For right-side tap shoots, just clear flag
        if fx > SW // 3:
            self._shoot_pressed = False

    def _update_joystick(self, fx, fy):
        dx = fx - self._joy_cx
        dy = fy - self._joy_cy
        dist = math.hypot(dx, dy)
        if dist > JOYSTICK_RADIUS:
            dx = dx / dist * JOYSTICK_RADIUS
            dy = dy / dist * JOYSTICK_RADIUS
            dist = float(JOYSTICK_RADIUS)
        if JOYSTICK_RADIUS > 0:
            self._joy_knob = (dx / JOYSTICK_RADIUS, dy / JOYSTICK_RADIUS)
        else:
            self._joy_knob = (0.0, 0.0)

    @staticmethod
    def _dist(a, b):
        return math.hypot(a[0]-b[0], a[1]-b[1])

    # ──────────────────────────────────────── state query ────────────────────

    def get_state(self):
        """
        Returns a dict:
          joy_x, joy_y   : float -1..1
          jump            : bool (True only once per press via consume)
          dash            : bool (True only once per press via consume)
          shoot           : bool (True only once per tap)
          shoot_target    : (x,y) screen pos or None
        """
        # One-shot jump / dash / shoot
        jump = self._jump_pressed and not self._jump_consumed
        if jump:
            self._jump_consumed = True

        dash = self._dash_pressed and not self._dash_consumed
        if dash:
            self._dash_consumed = True

        shoot = self._shoot_pressed and not self._shoot_consumed
        if shoot:
            self._shoot_consumed = True

        jx, jy = self._joy_knob
        return {
            "joy_x":        jx,
            "joy_y":        jy,
            "jump":         jump,
            "dash":         dash,
            "shoot":        shoot,
            "shoot_target": self._shoot_pos_world,
        }

    def is_holding_jump(self):
        return self._jump_pressed

    # ──────────────────────────────────────── drawing ────────────────────────

    def draw(self, screen):
        # Joystick ring
        r = JOYSTICK_RADIUS
        screen.blit(self._surf_joy_ring,
                    (self._joy_cx - r, self._joy_cy - r))
        # Knob
        kx = self._joy_cx + int(self._joy_knob[0] * r)
        ky = self._joy_cy + int(self._joy_knob[1] * r)
        kr = JOYSTICK_KNOB_R
        screen.blit(self._surf_knob, (kx - kr, ky - kr))

        # Action buttons
        self._draw_btn(screen, self._surf_jump,  self._jump_pos,
                       "JUMP",  self._jump_pressed)
        self._draw_btn(screen, self._surf_dash,  self._dash_pos,
                       "DASH",  self._dash_pressed)
        self._draw_btn(screen, self._surf_shoot, self._shoot_pos,
                       "FIRE",  self._shoot_pressed)

    def _draw_btn(self, screen, surf, pos, label, pressed):
        r = TOUCH_BTN_RADIUS
        screen.blit(surf, (pos[0]-r, pos[1]-r))
        if pressed:
            screen.blit(self._surf_pressed, (pos[0]-r, pos[1]-r))
        try:
            txt = self._font.render(label, True, (255, 255, 255))
            screen.blit(txt, (pos[0]-txt.get_width()//2,
                               pos[1]-txt.get_height()//2))
        except Exception:
            pass
