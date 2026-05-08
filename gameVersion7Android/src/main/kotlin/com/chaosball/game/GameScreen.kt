package com.chaosball.game

import com.badlogic.gdx.Gdx
import com.badlogic.gdx.Screen
import com.badlogic.gdx.graphics.Color
import com.badlogic.gdx.graphics.GL20
import com.badlogic.gdx.graphics.OrthographicCamera
import com.badlogic.gdx.graphics.glutils.ShapeRenderer
import com.badlogic.gdx.utils.Align
import com.badlogic.gdx.utils.viewport.FitViewport
import kotlin.math.*

/**
 * GameScreen — the main playing screen.
 */
class GameScreen(private val game: ChaosBallGame, startLevel: Int = 0) : Screen {

    private val logic = GameLogic().also { it.startAt(startLevel) }
    private val camera = OrthographicCamera()
    private val viewport = FitViewport(CANVAS_W, CANVAS_H, camera)
    private val touch = TouchInputHandler(viewport)

    private var clearHoldTimer = 0f

    override fun show() {}

    override fun render(delta: Float) {
        val dt = delta.coerceAtMost(0.05f)
        handleInput()
        logic.update(dt, touch.joyX, touch.joyY)
        checkStateTransitions()
        draw()
        touch.postFrame()
    }

    private fun handleInput() {
        touch.update()
        if (touch.jumpJustPressed) logic.tryJump()
        if (touch.dashJustPressed) logic.tryDash(touch.joyX, touch.joyY)
        
        val shootTarget = touch.tapShootPos ?: touch.shootWorldPos
        if (shootTarget != null) {
            logic.tryShoot(shootTarget.x, shootTarget.y)
        }
    }

    private fun checkStateTransitions() {
        when (logic.state) {
            GameState.LEVEL_CLEAR -> {
                clearHoldTimer += Gdx.graphics.deltaTime
                if (clearHoldTimer > 2.0f || touch.jumpJustPressed || touch.dashJustPressed) {
                    clearHoldTimer = 0f
                    logic.advanceLevel()
                    if (logic.state == GameState.WIN) {
                        game.setScreen(WinScreen(game, logic.score, logic.totalDeaths))
                    }
                }
            }
            GameState.GAME_OVER -> {
                game.setScreen(GameOverScreen(game, logic.score, logic.totalDeaths))
            }
            GameState.WIN -> {
                game.setScreen(WinScreen(game, logic.score, logic.totalDeaths))
            }
            else -> { clearHoldTimer = 0f }
        }
    }

    private fun draw() {
        Gdx.gl.glClearColor(0f, 0f, 0f, 1f)
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT)

        camera.position.set(CANVAS_W / 2f, CANVAS_H / 2f, 0f)
        camera.update()

        val shape = game.shape
        val batch = game.batch
        val font = game.font

        shape.projectionMatrix = camera.combined
        
        // 1. BG
        drawBackground()

        // 2. Void Walls (Called outside main batch because it manages its own ShapeRenderer batch)
        drawVoidWalls(shape)

        // 3. Main Game Entities (ShapeRenderer)
        shape.begin(ShapeRenderer.ShapeType.Filled)

        // Platforms
        shape.setColor(0.2f, 0.6f, 1f, 1f)
        for (p in logic.levelData.platforms) {
            shape.rect(p.x, p.y, p.w, p.h)
        }

        // Spikes
        for (s in logic.levelData.spikes) drawSpike(shape, s)

        // Goal
        val pulse = 0.7f + 0.3f * sin(logic.levelTime * 5f)
        shape.setColor(0.1f, pulse, 0.4f, 1f)
        val g = logic.levelData.goal
        shape.rect(g.x, g.y, g.w, g.h)

        // Coins
        for ((i, c) in logic.coins.withIndex()) {
            if (i in logic.coinsDead) continue
            val cp = 0.8f + 0.2f * sin(logic.levelTime * 6f + i)
            shape.setColor(1f, cp, 0f, 1f)
            shape.circle(c.x, c.y, 14f, 12)
        }

        // Boost pads
        shape.setColor(0f, 1f, 0.7f, 1f)
        for ((cx, cy, _) in logic.boostPads) shape.rect(cx - 35f, cy - 10f, 70f, 20f)

        for (rot in logic.rotators) drawRotator(shape, rot)

        for (e in logic.enemies) if (e.alive) {
            shape.setColor(0.8f, 0.3f, 1f, 1f)
            shape.circle(e.x, e.y, FlyingEnemy.RADIUS, 16)
        }

        for (s in logic.shooters) if (s.alive) {
            shape.setColor(1f, 0.2f, 0.2f, 1f)
            shape.circle(s.x, s.y, ShootingEnemy.RADIUS, 16)
        }

        shape.setColor(1f, 0.2f, 0.2f, 1f)
        for (ep in logic.enemyProjectiles) if (ep.alive) shape.circle(ep.x, ep.y, ep.radius, 8)
        shape.setColor(1f, 1f, 0.3f, 1f)
        for (pp in logic.playerProjectiles) if (pp.alive) shape.circle(pp.x, pp.y, pp.radius, 8)

        drawBall(shape)
        shape.end()

        // 4. HUD (Batch)
        batch.projectionMatrix = camera.combined
        batch.begin()
        
        font.data.setScale(2.2f)
        font.setColor(1f, 1f, 1f, 1f)
        font.draw(batch, "Score: ${logic.score}", 60f, CANVAS_H - 120f)
        
        font.data.setScale(1.8f)
        font.draw(batch, "Level ${logic.levelIdx + 1}", CANVAS_W - 220f, CANVAS_H - 60f)
        
        if (logic.gravityAnnounceTimer > 0) {
            font.data.setScale(4f)
            font.setColor(0.3f, 0.7f, 1f, minOf(1f, logic.gravityAnnounceTimer))
            font.draw(batch, logic.gravityAnnounceText, 0f, CANVAS_H/2f + 320f, CANVAS_W, Align.center, false)
        }

        if (logic.comboText.isNotEmpty()) {
            font.data.setScale(2.5f)
            font.setColor(1f, 0.8f, 0.1f, 1f)
            font.draw(batch, logic.comboText, logic.bx - 200f, logic.by + 120f, 400f, Align.center, false)
        }
        batch.end()

        // 5. Health
        shape.begin(ShapeRenderer.ShapeType.Filled)
        for (i in 0 until 10) {
            if (i < logic.hearts) shape.setColor(1f, 0.2f, 0.3f, 1f)
            else shape.setColor(0.2f, 0.05f, 0.05f, 1f)
            shape.circle(70f + i * 42f, CANVAS_H - 70f, 18f, 12)
        }
        shape.end()

        // 6. Touch Controls (Special draw with transparency)
        touch.draw(game)

        if (logic.state == GameState.LEVEL_CLEAR) drawLevelClearOverlay(batch, font)
    }

    private fun drawBackground() {
        val bgColors = listOf(
            floatArrayOf(0.02f, 0.01f, 0.05f), floatArrayOf(0.01f, 0.05f, 0.02f),
            floatArrayOf(0.05f, 0.01f, 0.01f), floatArrayOf(0.02f, 0.03f, 0.06f)
        )
        val c = bgColors[logic.levelIdx % bgColors.size]
        Gdx.gl.glClearColor(c[0], c[1], c[2], 1f)
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT)
    }

    private fun drawVoidWalls(shape: ShapeRenderer) {
        val t = 20f
        Gdx.gl.glEnable(GL20.GL_BLEND)
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA)
        shape.begin(ShapeRenderer.ShapeType.Filled)
        for (vw in logic.voidWalls) {
            val shimmer = 0.4f + 0.4f * sin(vw.shimmerPhase)
            shape.setColor(0.5f * shimmer, 0.1f, 0.9f * shimmer, 0.5f)
            when {
                vw.data.orientation == VoidOrientation.VERTICAL && vw.data.side == VoidSide.NEAR -> shape.rect(0f, 0f, t, CANVAS_H)
                vw.data.orientation == VoidOrientation.VERTICAL && vw.data.side == VoidSide.FAR -> shape.rect(CANVAS_W - t, 0f, t, CANVAS_H)
                vw.data.orientation == VoidOrientation.HORIZONTAL && vw.data.side == VoidSide.NEAR -> shape.rect(0f, 0f, CANVAS_W, t)
                else -> shape.rect(0f, CANVAS_H - t, CANVAS_W, t)
            }
        }
        shape.end()
        Gdx.gl.glDisable(GL20.GL_BLEND)
    }

    private fun drawSpike(shape: ShapeRenderer, spike: Spike) {
        shape.setColor(1f, 0.7f, 0.1f, 1f)
        val r = spike.rect
        val side = if (spike.dir == SpikeDir.UP || spike.dir == SpikeDir.DOWN) r.w else r.h
        val count = maxOf(1, (side / 24f).toInt())
        val step = side / count
        for (i in 0 until count) {
            when (spike.dir) {
                SpikeDir.UP -> shape.triangle(r.x + i*step, r.y+r.h, r.x + i*step + step/2f, r.y, r.x + (i+1)*step, r.y+r.h)
                SpikeDir.DOWN -> shape.triangle(r.x + i*step, r.y, r.x + i*step + step/2f, r.y+r.h, r.x + (i+1)*step, r.y)
                SpikeDir.RIGHT -> shape.triangle(r.x, r.y + i*step, r.x+r.w, r.y + i*step + step/2f, r.x, r.y + (i+1)*step)
                SpikeDir.LEFT -> shape.triangle(r.x+r.w, r.y + i*step, r.x, r.y + i*step + step/2f, r.x+r.w, r.y + (i+1)*step)
            }
        }
    }

    private fun drawRotator(shape: ShapeRenderer, rot: RotatingObstacle) {
        val d = rot.data; val rad = Math.toRadians(rot.angle.toDouble())
        shape.setColor(0.3f, 0.7f, 1f, 1f)
        shape.circle(d.pos.x, d.pos.y, d.thick, 12)
        for (offset in listOf(0.0, Math.PI / 2)) {
            val a = rad + offset
            val cx = cos(a).toFloat(); val cy = sin(a).toFloat()
            shape.rectLine(d.pos.x - cx * d.armLen, d.pos.y - cy * d.armLen, d.pos.x + cx * d.armLen, d.pos.y + cy * d.armLen, d.thick * 2f)
        }
    }

    private fun drawBall(shape: ShapeRenderer) {
        if (logic.invincibleTimer > 0 && (logic.levelTime * 15).toInt() % 2 == 0) return
        val r = logic.ballR
        val sx = if (logic.dashTimer > 0) 1.4f else logic.squash.coerceIn(0.7f, 1.3f)
        val sy = 2f - sx
        shape.color = if (logic.dashTimer > 0) Color.CYAN else Color.CORAL
        shape.ellipse(logic.bx - r * sx, logic.by - r * sy, r * 2f * sx, r * 2f * sy, 24)
    }

    private fun drawLevelClearOverlay(batch: com.badlogic.gdx.graphics.g2d.SpriteBatch, font: com.badlogic.gdx.graphics.g2d.BitmapFont) {
        batch.begin()
        font.data.setScale(5f)
        font.setColor(0.3f, 1f, 0.6f, 1f)
        font.draw(batch, "LEVEL COMPLETE!", 0f, CANVAS_H/2f + 120f, CANVAS_W, Align.center, false)
        font.data.setScale(2.2f)
        font.setColor(1f, 1f, 1f, 0.7f)
        font.draw(batch, "TAP TO CONTINUE", 0f, CANVAS_H/2f - 60f, CANVAS_W, Align.center, false)
        batch.end()
    }

    override fun resize(width: Int, height: Int) { viewport.update(width, height, true) }
    override fun pause()  {}
    override fun resume() {}
    override fun hide()   {}
    override fun dispose() {}
}
