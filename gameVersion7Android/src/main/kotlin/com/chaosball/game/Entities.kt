package com.chaosball.game

import kotlin.math.*

// ─── Runtime game entities ────────────────────────────────────────────────

class RotatingObstacle(val data: RotatorData) {
    var angle = 0f
    fun update(dt: Float) { angle += data.speed * dt }
    fun collidesBall(bx: Float, by: Float, br: Float): Boolean {
        if (hypot((bx - data.pos.x).toDouble(), (by - data.pos.y).toDouble()) < br + data.thick) return true
        val rad = Math.toRadians(angle.toDouble())
        for (offset in listOf(0.0, Math.PI / 2)) {
            val a = rad + offset
            val cx = cos(a).toFloat(); val cy = sin(a).toFloat()
            for (sign in listOf(-data.armLen, data.armLen)) {
                val px = data.pos.x + cx * sign; val py = data.pos.y + cy * sign
                if (hypot((bx - px).toDouble(), (by - py).toDouble()) < br + data.thick) return true
            }
        }
        return false
    }
}

class FlyingEnemy(val data: EnemyData) {
    var x = data.pos.x; var y = data.pos.y
    var alive = true
    private var phase = 0f
    private var hitCooldown = 0f
    private val behavior = listOf("chase","orbit","zigzag").random()
    private var orbitRadius = (150..250).random().toFloat()
    private var orbitAngle = Math.random().toFloat() * 2f * Math.PI.toFloat()
    private var zigzagTimer = 0f
    private var zigzagDir = 1f

    companion object { const val RADIUS = 28f }

    fun update(dt: Float, playerX: Float, playerY: Float) {
        if (!alive) return
        phase += dt * 3f
        hitCooldown = maxOf(0f, hitCooldown - dt)
        val dx = playerX - x; val dy = playerY - y
        val dist = hypot(dx.toDouble(), dy.toDouble()).toFloat()
        val speed = data.speed
        when (behavior) {
            "chase" -> if (dist > 5) { x += dx/dist*speed*dt; y += dy/dist*speed*dt }
            "orbit" -> {
                orbitAngle += dt * 1.2f
                val tx = playerX + cos(orbitAngle) * orbitRadius
                val ty = playerY + sin(orbitAngle) * orbitRadius
                val dx2 = tx - x; val dy2 = ty - y
                val d2 = hypot(dx2.toDouble(), dy2.toDouble()).toFloat()
                if (d2 > 5) { x += dx2/d2*speed*dt; y += dy2/d2*speed*dt }
            }
            "zigzag" -> {
                zigzagTimer += dt
                if (zigzagTimer > 0.8f) { zigzagTimer = 0f; zigzagDir *= -1f }
                if (dist > 5) {
                    val px = -dy/dist; val py = dx/dist
                    x += (dx/dist + px*zigzagDir*0.3f)*speed*dt
                    y += (dy/dist + py*zigzagDir*0.3f)*speed*dt
                }
            }
        }
    }

    fun tryHit(bx: Float, by: Float, br: Float): Boolean {
        if (!alive || hitCooldown > 0) return false
        if (hypot((bx - x).toDouble(), (by - y).toDouble()) < br + RADIUS) {
            hitCooldown = 1.0f; return true
        }
        return false
    }
}

class ShootingEnemy(val data: ShooterData) {
    var x = data.pos.x; var y = data.pos.y
    var alive = true
    var angle = 0f
    private var fireTimer = data.fireInterval

    companion object { const val RADIUS = 24f }

    fun update(dt: Float, playerX: Float, playerY: Float): EnemyProjectile? {
        if (!alive) return null
        angle = atan2((playerY - y).toDouble(), (playerX - x).toDouble()).toFloat()
        fireTimer -= dt
        if (fireTimer <= 0f) {
            fireTimer = data.fireInterval
            val speed = 400f
            return EnemyProjectile(x, y, cos(angle) * speed, sin(angle) * speed)
        }
        return null
    }
}

class EnemyProjectile(var x: Float, var y: Float, val vx: Float, val vy: Float) {
    var alive = true
    private var lifetime = 5f
    val radius = 8f

    fun update(dt: Float) {
        x += vx * dt; y += vy * dt; lifetime -= dt
        if (x < -50 || x > CANVAS_W + 50 || y < -50 || y > CANVAS_H + 50 || lifetime <= 0) alive = false
    }
    fun hitsBall(bx: Float, by: Float, br: Float) =
        alive && hypot((x - bx).toDouble(), (y - by).toDouble()) < radius + br
}

class PlayerProjectile(var x: Float, var y: Float, val vx: Float, val vy: Float) {
    var alive = true
    private var lifetime = 3f
    val radius = 7f

    fun update(dt: Float) {
        x += vx * dt; y += vy * dt; lifetime -= dt
        if (x < -50 || x > CANVAS_W + 50 || y < -50 || y > CANVAS_H + 50 || lifetime <= 0) alive = false
    }
    fun hitsEnemy(ex: Float, ey: Float, er: Float) =
        alive && hypot((x - ex).toDouble(), (y - ey).toDouble()) < radius + er
}

class VoidWall(val data: VoidWallData) {
    var shimmerPhase = Math.random().toFloat() * 2f * Math.PI.toFloat()
    var cooldown = 0f
    private val THICKNESS = 18f

    fun update(dt: Float) { shimmerPhase += dt * 3.5f; cooldown = maxOf(0f, cooldown - dt) }

    /** Returns new (x,y) if teleport triggered, null otherwise */
    fun checkTeleport(bx: Float, by: Float, br: Float): Vec2? {
        if (cooldown > 0) return null
        val threshold = br + THICKNESS
        return when {
            data.orientation == VoidOrientation.VERTICAL && data.side == VoidSide.NEAR && bx - br <= THICKNESS -> {
                cooldown = 0.55f; Vec2(CANVAS_W - br - 2f, by)
            }
            data.orientation == VoidOrientation.VERTICAL && data.side == VoidSide.FAR && bx + br >= CANVAS_W - THICKNESS -> {
                cooldown = 0.55f; Vec2(br + 2f, by)
            }
            data.orientation == VoidOrientation.HORIZONTAL && data.side == VoidSide.NEAR && by - br <= THICKNESS -> {
                cooldown = 0.55f; Vec2(bx, CANVAS_H - br - 2f)
            }
            data.orientation == VoidOrientation.HORIZONTAL && data.side == VoidSide.FAR && by + br >= CANVAS_H - THICKNESS -> {
                cooldown = 0.55f; Vec2(bx, br + 2f)
            }
            else -> null
        }
    }
}
