package com.chaosball.game

import kotlin.math.*
import kotlin.random.Random

// ─── Canvas design space (matches pygame 1920×1080) ───────────────────────
const val CANVAS_W = 1920f
const val CANVAS_H = 1080f

const val GOAL_W = 70f
const val GOAL_H = 90f
const val GOAL_CX = CANVAS_W / 2f
const val GOAL_CY = CANVAS_H / 2f
const val GOAL_SAFE_R = 140f
const val SPAWN_SAFE_R = 180f

const val NUM_LEVELS = 20
const val TIER_BASIC_END = 8
const val TIER_SPINNER_END = 12
const val TIER_VOID_END = 20
const val TIER_SHOOTER_START = 16

// Physics
const val GRAVITY_STRENGTH = 1400f
const val DASH_SPEED = 1400f
const val DASH_DURATION = 0.18f
const val DASH_COOLDOWN = 0.60f
const val INVINCIBLE_DURATION = 1.5f
const val COYOTE_TIME = 0.10f
const val JUMP_BUFFER_TIME = 0.12f
const val DEATH_FREEZE_TIME = 0.35f
const val KILL_COMBO_WINDOW = 2.0f
const val GUN_PROJ_SPEED = 900f

// ─── Data classes ─────────────────────────────────────────────────────────

data class Rect(val x: Float, val y: Float, val w: Float, val h: Float) {
    fun overlaps(o: Rect, margin: Float = 0f) =
        x - margin < o.x + o.w && x + w + margin > o.x &&
        y - margin < o.y + o.h && y + h + margin > o.y
    val cx get() = x + w / 2f
    val cy get() = y + h / 2f
}

data class Vec2(val x: Float, val y: Float) {
    operator fun plus(o: Vec2) = Vec2(x + o.x, y + o.y)
    operator fun minus(o: Vec2) = Vec2(x - o.x, y - o.y)
    operator fun times(s: Float) = Vec2(x * s, y * s)
    fun len() = sqrt(x * x + y * y)
    fun norm(): Vec2 { val l = len(); return if (l < 0.001f) Vec2(0f, 0f) else Vec2(x / l, y / l) }
    fun dist(o: Vec2) = (this - o).len()
}

enum class GravityDir(val gx: Float, val gy: Float, val label: String) {
    DOWN(0f, -1f, "DOWN"), UP(0f, 1f, "UP"),
    RIGHT(-1f, 0f, "RIGHT"), LEFT(1f, 0f, "LEFT");
    companion object { fun random(rng: Random) = values()[rng.nextInt(4)] }
}

// Spike direction
enum class SpikeDir { UP, DOWN, LEFT, RIGHT }

data class Spike(val rect: Rect, val dir: SpikeDir)

data class RotatorData(
    val pos: Vec2, val armLen: Float, val thick: Float, val speed: Float
)

data class EnemyData(val pos: Vec2, val speed: Float)
data class ShooterData(val pos: Vec2, val fireInterval: Float)

enum class VoidSide { NEAR, FAR }
enum class VoidOrientation { VERTICAL, HORIZONTAL }
data class VoidWallData(val orientation: VoidOrientation, val side: VoidSide)

data class LevelData(
    val platforms: List<Rect>,
    val spikes: List<Spike>,
    val goal: Rect,
    val spawn: Vec2,
    val rotators: List<RotatorData>,
    val enemies: List<EnemyData>,
    val shooters: List<ShooterData>,
    val voidWalls: List<VoidWallData>,
    val hasGun: Boolean,
    val coins: List<Vec2>,
    val boostPads: List<Triple<Float, Float, String>>
)
