package com.chaosball.game

import kotlin.math.*

enum class GameState { PLAY, LEVEL_CLEAR, GAME_OVER, WIN }

class GameLogic {

    // ── State ──────────────────────────────────────────────────────────────
    var state = GameState.PLAY
    var levelIdx = 0
    var hearts = 10
    var totalDeaths = 0
    var score = 0

    // Ball
    var bx = 0f; var by = 0f
    var bvx = 0f; var bvy = 0f
    val ballR = 22f * (1920f / 1920f)   // scale-adjusted later in renderer
    var onGround = false
    var jumpsLeft = 2
    var squash = 1.0f

    // Gravity
    var gravity = GravityDir.DOWN
    var wallsDeadly = false

    // Timers
    var invincibleTimer = 0f
    var dashTimer = 0f
    var dashCooldownTimer = 0f
    var coyoteTimer = 0f
    var jumpBufferTimer = 0f
    var freezeTimer = 0f
    var pendingDeath = false
    var shootTimer = 0f
    var slowmoTimer = 0f
    var killStreakTimer = 0f
    var killStreak = 0
    var levelTime = 0f
    var gravityAnnounceTimer = 0f
    var gravityAnnounceText = ""
    var coinComboTimer = 0f
    var coinCombo = 0
    var comboText = ""

    // Level entities
    lateinit var levelData: LevelData
    val rotators = mutableListOf<RotatingObstacle>()
    val enemies   = mutableListOf<FlyingEnemy>()
    val shooters  = mutableListOf<ShootingEnemy>()
    val voidWalls = mutableListOf<VoidWall>()
    val enemyProjectiles  = mutableListOf<EnemyProjectile>()
    val playerProjectiles = mutableListOf<PlayerProjectile>()
    val coins = mutableListOf<Vec2>()   // alive coins (mutable copy)
    val coinsDead = mutableSetOf<Int>() // indices collected
    var boostPads = emptyList<Triple<Float,Float,String>>()
    var hasGun = false
    var coinsRewarded = false

    // ── Init ──────────────────────────────────────────────────────────────
    init { loadLevel() }

    fun startAt(idx: Int) { levelIdx = idx; hearts = 10; totalDeaths = 0; score = 0; loadLevel() }

    fun loadLevel() {
        levelData = LevelGenerator.ALL_LEVELS[levelIdx % NUM_LEVELS]
        bx = levelData.spawn.x; by = levelData.spawn.y
        bvx = 0f; bvy = 0f
        onGround = false; jumpsLeft = 2

        rotators.clear(); rotators.addAll(levelData.rotators.map { RotatingObstacle(it) })
        enemies.clear();   enemies.addAll(levelData.enemies.map { FlyingEnemy(it) })
        shooters.clear();  shooters.addAll(levelData.shooters.map { ShootingEnemy(it) })
        voidWalls.clear(); voidWalls.addAll(levelData.voidWalls.map { VoidWall(it) })
        enemyProjectiles.clear(); playerProjectiles.clear()

        coins.clear(); coins.addAll(levelData.coins); coinsDead.clear()
        boostPads = levelData.boostPads
        hasGun = levelData.hasGun
        coinsRewarded = false

        coyoteTimer = 0f; jumpBufferTimer = 0f; freezeTimer = 0f
        pendingDeath = false; dashTimer = 0f; dashCooldownTimer = 0f
        invincibleTimer = 0f; shootTimer = 0f
        levelTime = 0f; coinCombo = 0; coinComboTimer = 0f; comboText = ""
        squash = 1.0f; state = GameState.PLAY
    }

    // ── Input API (called from GameScreen) ────────────────────────────────

    fun tryJump() {
        var canJump = jumpsLeft > 0
        if (!canJump && coyoteTimer > 0) { canJump = true; jumpsLeft = 1; coyoteTimer = 0f }
        if (!canJump) { jumpBufferTimer = JUMP_BUFFER_TIME; return }
        bvx -= gravity.gx * 700f; bvy -= gravity.gy * 700f
        jumpsLeft--; onGround = false; coyoteTimer = 0f; squash = 1.4f
    }

    fun tryDash(joyX: Float, joyY: Float) {
        if (dashCooldownTimer > 0) return
        var dx = joyX; var dy = joyY
        if (abs(dx) < 0.15f && abs(dy) < 0.15f) { dx = -gravity.gx; dy = -gravity.gy }
        val dist = hypot(dx.toDouble(), dy.toDouble()).toFloat()
        if (dist > 0) { dx /= dist; dy /= dist }
        bvx = dx * DASH_SPEED; bvy = dy * DASH_SPEED
        dashTimer = DASH_DURATION; dashCooldownTimer = DASH_COOLDOWN
    }

    fun tryShoot(targetX: Float, targetY: Float) {
        if (shootTimer > 0 || !hasGun) return
        val dx = targetX - bx; val dy = targetY - by
        val dist = hypot(dx.toDouble(), dy.toDouble()).toFloat()
        if (dist < 1f) return
        playerProjectiles.add(PlayerProjectile(bx, by, dx/dist * GUN_PROJ_SPEED, dy/dist * GUN_PROJ_SPEED))
        shootTimer = 0.15f
    }

    // ── Update ─────────────────────────────────────────────────────────────

    fun update(dt: Float, joyX: Float, joyY: Float) {
        if (state != GameState.PLAY) return

        // Freeze frame (death animation pause)
        if (freezeTimer > 0) {
            freezeTimer -= dt
            if (freezeTimer <= 0 && pendingDeath) executeRespawn()
            return
        }

        val effDt = if (slowmoTimer > 0) dt * 0.25f else dt
        levelTime += dt

        // Tick timers
        if (shootTimer > 0)          shootTimer          = maxOf(0f, shootTimer - dt)
        if (invincibleTimer > 0)     invincibleTimer     = maxOf(0f, invincibleTimer - dt)
        if (dashCooldownTimer > 0)   dashCooldownTimer   = maxOf(0f, dashCooldownTimer - dt)
        if (dashTimer > 0)           dashTimer           = maxOf(0f, dashTimer - dt)
        if (coyoteTimer > 0) {
            coyoteTimer = maxOf(0f, coyoteTimer - dt)
            if (coyoteTimer <= 0f && !onGround && jumpsLeft == 2) jumpsLeft = 1
        }
        if (jumpBufferTimer > 0)     jumpBufferTimer     = maxOf(0f, jumpBufferTimer - dt)
        if (slowmoTimer > 0)         slowmoTimer         = maxOf(0f, slowmoTimer - dt)
        if (killStreakTimer > 0) {
            killStreakTimer -= dt
            if (killStreakTimer <= 0) killStreak = 0
        }
        if (coinComboTimer > 0) {
            coinComboTimer -= dt
            if (coinComboTimer <= 0) { coinCombo = 0; comboText = "" }
        }
        if (gravityAnnounceTimer > 0) gravityAnnounceTimer = maxOf(0f, gravityAnnounceTimer - dt)

        val prevGround = onGround
        onGround = false

        if (dashTimer <= 0f) {
            applyMovement(effDt, joyX, joyY)
            applyGravity(effDt)
            capVelocity()
        }

        moveX(effDt); moveY(effDt)
        checkScreenWalls()
        if (state != GameState.PLAY) return

        if (onGround && !prevGround) {
            squash = 0.6f
            if (jumpBufferTimer > 0) { jumpBufferTimer = 0f; tryJump() }
        }
        if (prevGround && !onGround && jumpsLeft == 2) coyoteTimer = COYOTE_TIME

        // Squash recovery
        squash += (1f - squash) * minOf(1f, dt * 12f)

        checkVoidWalls()
        checkSpikes()
        if (state != GameState.PLAY) return
        checkRotators(effDt)
        if (state != GameState.PLAY) return
        checkCoins()
        checkBoostPads()
        checkEnemies(effDt)
        if (state != GameState.PLAY) return
        checkShooters(effDt)
        if (state != GameState.PLAY) return
        tickPlayerProjectiles(effDt)
        checkGoal()

        // Update void walls
        voidWalls.forEach { it.update(dt) }
    }

    // ── Movement ──────────────────────────────────────────────────────────

    private fun applyMovement(dt: Float, joyX: Float, joyY: Float) {
        val acc = 4000f * dt
        if (gravity.gy != 0f) {   // vertical gravity → horizontal joystick
            if (abs(joyX) > 0.15f) bvx += joyX * acc * 1.2f
            bvx *= 0.80f
        } else {                   // horizontal gravity → vertical joystick
            if (abs(joyY) > 0.15f) bvy += joyY * acc * 1.2f
            bvy *= 0.80f
        }
    }

    private fun applyGravity(dt: Float) {
        bvx += gravity.gx * GRAVITY_STRENGTH * dt
        bvy += gravity.gy * GRAVITY_STRENGTH * dt
    }

    private fun capVelocity() {
        val mv = 1200f
        bvx = bvx.coerceIn(-mv, mv); bvy = bvy.coerceIn(-mv, mv)
    }

    private fun moveX(dt: Float) {
        bx += bvx * dt
        val rect = ballRect()
        for (p in levelData.platforms) {
            if (!rect.overlaps(p)) continue
            if (bvx > 0) { bx = p.x - ballR; if (gravity.gx > 0) { onGround = true; jumpsLeft = 2 } }
            else if (bvx < 0) { bx = p.x + p.w + ballR; if (gravity.gx < 0) { onGround = true; jumpsLeft = 2 } }
            bvx = 0f
        }
    }

    private fun moveY(dt: Float) {
        by += bvy * dt
        val rect = ballRect()
        for (p in levelData.platforms) {
            if (!rect.overlaps(p)) continue
            if (bvy > 0) { by = p.y - ballR; if (gravity.gy > 0) { onGround = true; jumpsLeft = 2 } }
            else if (bvy < 0) { by = p.y + p.h + ballR; if (gravity.gy < 0) { onGround = true; jumpsLeft = 2 } }
            bvy = 0f
        }
    }

    private fun checkScreenWalls() {
        var died = false
        if (bx - ballR < 0)           { bx = ballR;              bvx = abs(bvx)*0.4f;  if (gravity.gx < 0) { onGround=true; jumpsLeft=2 }; if(wallsDeadly) died=true }
        if (bx + ballR > CANVAS_W)    { bx = CANVAS_W - ballR;   bvx = -abs(bvx)*0.4f; if (gravity.gx > 0) { onGround=true; jumpsLeft=2 }; if(wallsDeadly) died=true }
        if (by - ballR < 0)           { by = ballR;               bvy = abs(bvy)*0.4f;  if (gravity.gy < 0) { onGround=true; jumpsLeft=2 }; if(wallsDeadly) died=true }
        if (by + ballR > CANVAS_H)    { by = CANVAS_H - ballR;   bvy = -abs(bvy)*0.4f; if (gravity.gy > 0) { onGround=true; jumpsLeft=2 }; if(wallsDeadly) died=true }
        if (died && invincibleTimer <= 0 && dashTimer <= 0) triggerDeath()
    }

    private fun checkVoidWalls() {
        for (vw in voidWalls) {
            val result = vw.checkTeleport(bx, by, ballR) ?: continue
            bx = result.x; by = result.y
            slowmoTimer = 0.15f
            break
        }
    }

    private fun checkSpikes() {
        if (invincibleTimer > 0 || dashTimer > 0) return
        val r = ballRect(shrink = 6f)
        for (s in levelData.spikes) if (r.overlaps(s.rect)) { triggerDeath(); return }
    }

    private fun checkRotators(dt: Float) {
        for (rot in rotators) {
            rot.update(dt)
            if (rot.collidesBall(bx, by, ballR)) {
                if (invincibleTimer <= 0 && dashTimer <= 0) { triggerDeath(); return }
            }
        }
    }

    private fun checkCoins() {
        val coinR = 14f
        for ((i, c) in coins.withIndex()) {
            if (i in coinsDead) continue
            if (hypot((bx - c.x).toDouble(), (by - c.y).toDouble()) < ballR + coinR) {
                coinsDead.add(i); coinCombo++; coinComboTimer = 1.5f
                val pts = 10 * coinCombo; score += pts
                comboText = if (coinCombo >= 3) "COMBO x$coinCombo! +$pts" else "+$pts"
            }
        }
        if (!coinsRewarded && coins.isNotEmpty() && coinsDead.size == coins.size) {
            coinsRewarded = true; if (hearts < 10) hearts++
        }
    }

    private fun checkBoostPads() {
        val padW = 70f; val padH = 20f; val boostSpeed = 1100f
        for ((cx, cy, dir) in boostPads) {
            val pad = Rect(cx - padW/2f, cy - padH/2f, padW, padH)
            if (!ballRect().overlaps(pad)) continue
            when (dir) { "up" -> bvy = -boostSpeed; "down" -> bvy = boostSpeed; "left" -> bvx = -boostSpeed; "right" -> bvx = boostSpeed }
            break
        }
    }

    private fun checkEnemies(dt: Float) {
        for (enemy in enemies) {
            enemy.update(dt, bx, by)
            if (enemy.tryHit(bx, by, ballR)) loseHeart()
        }
        for (proj in playerProjectiles) {
            if (!proj.alive) continue
            for (enemy in enemies) {
                if (!enemy.alive) continue
                if (proj.hitsEnemy(enemy.x, enemy.y, FlyingEnemy.RADIUS)) {
                    enemy.alive = false; proj.alive = false
                    killStreak++; killStreakTimer = KILL_COMBO_WINDOW
                    val mult = minOf(killStreak, 5); score += 50 * mult
                    break
                }
            }
        }
    }

    private fun checkShooters(dt: Float) {
        for (shooter in shooters) {
            val proj = shooter.update(dt, bx, by)
            if (proj != null) enemyProjectiles.add(proj)
        }
        for (ep in enemyProjectiles) {
            ep.update(dt)
            if (ep.hitsBall(bx, by, ballR)) { ep.alive = false; loseHeart() }
        }
        for (proj in playerProjectiles) {
            if (!proj.alive) continue
            for (shooter in shooters) {
                if (!shooter.alive) continue
                if (proj.hitsEnemy(shooter.x, shooter.y, ShootingEnemy.RADIUS)) {
                    shooter.alive = false; proj.alive = false
                    killStreak++; killStreakTimer = KILL_COMBO_WINDOW
                    score += 75 * minOf(killStreak, 5)
                    break
                }
            }
        }
        enemyProjectiles.removeAll { !it.alive }
    }

    private fun tickPlayerProjectiles(dt: Float) {
        playerProjectiles.forEach { it.update(dt) }
        playerProjectiles.removeAll { !it.alive }
    }

    private fun checkGoal() {
        if (ballRect(shrink = 4f).overlaps(levelData.goal)) {
            state = GameState.LEVEL_CLEAR
        }
    }

    // ── Death / respawn ────────────────────────────────────────────────────

    private fun triggerDeath() {
        totalDeaths++; hearts--
        if (hearts <= 0) { state = GameState.GAME_OVER; return }
        freezeTimer = DEATH_FREEZE_TIME; pendingDeath = true
    }

    private fun loseHeart() {
        if (invincibleTimer > 0 || dashTimer > 0) return
        hearts--
        if (hearts <= 0) { state = GameState.GAME_OVER; return }
        invincibleTimer = INVINCIBLE_DURATION
    }

    private fun executeRespawn() {
        pendingDeath = false
        val oldGravity = gravity
        val candidates = GravityDir.values().toList()
        gravity = candidates.random()
        if (gravity != oldGravity) {
            wallsDeadly = false
            gravityAnnounceText = "GRAVITY: ${gravity.label}"
            gravityAnnounceTimer = 2.2f
        } else if (Math.random() < 0.4) {
            wallsDeadly = !wallsDeadly
        }
        loadLevel()
        invincibleTimer = INVINCIBLE_DURATION
    }

    fun advanceLevel() {
        levelIdx++
        if (levelIdx >= NUM_LEVELS) { state = GameState.WIN; return }
        loadLevel()
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    fun ballRect(shrink: Float = 0f): Rect {
        val r = ballR - shrink
        return Rect(bx - r, by - r, r * 2f, r * 2f)
    }
}
