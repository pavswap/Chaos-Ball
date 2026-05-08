package com.chaosball.game

import com.badlogic.gdx.Gdx
import com.badlogic.gdx.InputAdapter
import com.badlogic.gdx.Screen
import com.badlogic.gdx.graphics.GL20
import com.badlogic.gdx.graphics.OrthographicCamera
import com.badlogic.gdx.graphics.glutils.ShapeRenderer
import com.badlogic.gdx.utils.Align
import com.badlogic.gdx.utils.viewport.FitViewport
import kotlin.math.*

class MenuScreen(private val game: ChaosBallGame) : Screen {

    private val camera   = OrthographicCamera()
    private val viewport = FitViewport(CANVAS_W, CANVAS_H, camera)
    private var time     = 0f
    private var state    = "main"

    private val btnPlay   = Rect(CANVAS_W/2f-250f, 480f, 500f, 110f)
    private val btnSelect = Rect(CANVAS_W/2f-250f, 340f, 500f, 110f)
    private val btnQuit   = Rect(CANVAS_W/2f-250f, 200f, 500f, 110f)
    private val btnBack   = Rect(80f, 80f, 240f, 80f)

    override fun show() {
        Gdx.input.inputProcessor = object : InputAdapter() {
            override fun touchDown(screenX: Int, screenY: Int, pointer: Int, button: Int): Boolean {
                val wx = viewport.unproject(com.badlogic.gdx.math.Vector2(screenX.toFloat(), screenY.toFloat())).x
                val wy = viewport.unproject(com.badlogic.gdx.math.Vector2(screenX.toFloat(), screenY.toFloat())).y
                handleTap(wx, wy); return true
            }
        }
    }

    private fun handleTap(wx: Float, wy: Float) {
        if (state == "main") {
            when {
                btnPlay.contains(wx, wy)   -> game.setScreen(GameScreen(game, 0))
                btnSelect.contains(wx, wy) -> state = "select"
                btnQuit.contains(wx, wy)   -> Gdx.app.exit()
            }
        } else {
            if (btnBack.contains(wx, wy)) { state = "main"; return }
            val tileIdx = tileAt(wx, wy)
            if (tileIdx >= 0) game.setScreen(GameScreen(game, tileIdx))
        }
    }

    private fun tileAt(wx: Float, wy: Float): Int {
        val cols = 5; val tileW = 280f; val tileH = 120f; val spacing = 30f
        val startX = (CANVAS_W - (cols * tileW + (cols-1) * spacing)) / 2f
        val startY = CANVAS_H - 350f
        for (i in 0 until NUM_LEVELS) {
            val col = i % cols; val row = i / cols
            val tx = startX + col * (tileW + spacing); val ty = startY - row * (tileH + spacing)
            if (wx in tx..(tx+tileW) && wy in ty..(ty+tileH)) return i
        }
        return -1
    }

    private fun Rect.contains(wx: Float, wy: Float) = wx in x..(x+w) && wy in y..(y+h)

    override fun render(delta: Float) {
        time += delta
        Gdx.gl.glClearColor(0.01f, 0.01f, 0.03f, 1f)
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT)
        camera.update()
        
        if (state == "main") drawMain() else drawSelect()
    }

    private fun drawMain() {
        val shape = game.shape
        val batch = game.batch
        val font = game.font
        
        shape.projectionMatrix = camera.combined
        shape.begin(ShapeRenderer.ShapeType.Filled)
        for (i in 0 until 60) {
            val angle = i * 2.1f + time * 0.1f
            val sx = CANVAS_W/2f + cos(angle) * (500f + i * 10f)
            val sy = CANVAS_H/2f + sin(angle * 0.7f) * (300f + i * 5f)
            shape.setColor(0.3f, 0.5f, 1f, 0.2f)
            shape.circle(sx, sy, 2f)
        }
        shape.end()

        batch.projectionMatrix = camera.combined
        batch.begin()
        val pulse = 1f + 0.05f * sin(time * 3f)
        font.data.setScale(7f * pulse)
        font.setColor(1f, 0.3f, 0.2f, 1f)
        font.draw(batch, "CHAOS BALL", 0f, CANVAS_H - 200f, CANVAS_W, Align.center, false)
        
        font.data.setScale(2.5f)
        drawBtnWithText(batch, shape, btnPlay,   0.2f, 0.8f, 0.4f, "NEW GAME")
        drawBtnWithText(batch, shape, btnSelect, 0.3f, 0.6f, 1.0f, "CHAPTERS")
        drawBtnWithText(batch, shape, btnQuit,   0.9f, 0.3f, 0.3f, "EXIT")
        batch.end()
    }

    private fun drawBtnWithText(batch: com.badlogic.gdx.graphics.g2d.SpriteBatch, shape: ShapeRenderer, rect: Rect, r: Float, g: Float, b: Float, label: String) {
        batch.end()
        Gdx.gl.glEnable(GL20.GL_BLEND)
        shape.begin(ShapeRenderer.ShapeType.Filled)
        shape.setColor(r, g, b, 0.15f)
        shape.rect(rect.x, rect.y, rect.w, rect.h)
        shape.end()
        shape.begin(ShapeRenderer.ShapeType.Line)
        shape.setColor(r, g, b, 0.8f)
        shape.rect(rect.x, rect.y, rect.w, rect.h)
        shape.end()
        batch.begin()
        game.font.setColor(r, g, b, 1f)
        game.font.draw(batch, label, rect.x, rect.y + rect.h/2f + 15f, rect.w, Align.center, false)
    }

    private fun drawSelect() {
        val batch = game.batch
        batch.projectionMatrix = camera.combined
        batch.begin()
        game.font.data.setScale(4f)
        game.font.setColor(1f, 1f, 1f, 1f)
        game.font.draw(batch, "SELECT STAGE", 0f, CANVAS_H - 120f, CANVAS_W, Align.center, false)
        batch.end()

        val shape = game.shape
        shape.projectionMatrix = camera.combined
        shape.begin(ShapeRenderer.ShapeType.Filled)
        val cols = 5; val tileW = 280f; val tileH = 120f; val spacing = 30f
        val startX = (CANVAS_W - (cols * tileW + (cols-1) * spacing)) / 2f
        val startY = CANVAS_H - 350f
        for (i in 0 until NUM_LEVELS) {
            val col = i % cols; val row = i / cols
            val tx = startX + col * (tileW + spacing); val ty = startY - row * (tileH + spacing)
            val (tr, tg, tb) = tierColor(i)
            shape.setColor(tr, tg, tb, 0.2f)
            shape.rect(tx, ty, tileW, tileH)
        }
        shape.end()

        batch.begin()
        game.font.data.setScale(2f)
        for (i in 0 until NUM_LEVELS) {
            val col = i % cols; val row = i / cols
            val tx = startX + col * (tileW + spacing); val ty = startY - row * (tileH + spacing)
            val (tr, tg, tb) = tierColor(i)
            game.font.setColor(tr, tg, tb, 1f)
            game.font.draw(batch, "${i+1}", tx, ty + tileH/2f + 15f, tileW, Align.center, false)
        }
        drawBtnWithText(batch, shape, btnBack, 0.6f, 0.6f, 0.6f, "BACK")
        batch.end()
    }

    private fun tierColor(idx: Int): Triple<Float, Float, Float> = when {
        idx < TIER_BASIC_END    -> Triple(0.2f, 0.7f, 1f)
        idx < TIER_SPINNER_END  -> Triple(1f, 0.6f, 0.1f)
        idx < TIER_SHOOTER_START-> Triple(0.6f, 0.2f, 1f)
        else                    -> Triple(1f, 0.3f, 0.3f)
    }

    override fun resize(w: Int, h: Int) { viewport.update(w, h, true) }
    override fun pause() {} ; override fun resume() {} ; override fun hide() {} ; override fun dispose() {}
}

class GameOverScreen(private val game: ChaosBallGame, private val score: Int, private val deaths: Int) : Screen {
    private val camera   = OrthographicCamera()
    private val viewport = FitViewport(CANVAS_W, CANVAS_H, camera)

    override fun show() {
        Gdx.input.inputProcessor = object : InputAdapter() {
            override fun touchDown(screenX: Int, screenY: Int, pointer: Int, button: Int): Boolean {
                game.setScreen(MenuScreen(game)); return true
            }
        }
    }

    override fun render(delta: Float) {
        Gdx.gl.glClearColor(0.1f, 0f, 0f, 1f)
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT)
        camera.position.set(CANVAS_W/2f, CANVAS_H/2f, 0f); camera.update()
        
        val batch = game.batch
        val font = game.font
        batch.projectionMatrix = camera.combined
        batch.begin()
        font.data.setScale(5f)
        font.setColor(1f, 0.2f, 0.2f, 1f)
        font.draw(batch, "GAME OVER", 0f, CANVAS_H/2f + 200f, CANVAS_W, Align.center, false)
        
        font.data.setScale(2.5f)
        font.setColor(1f, 1f, 1f, 1f)
        font.draw(batch, "Score: $score", 0f, CANVAS_H/2f + 20f, CANVAS_W, Align.center, false)
        font.draw(batch, "Total Deaths: $deaths", 0f, CANVAS_H/2f - 60f, CANVAS_W, Align.center, false)
        
        font.data.setScale(1.5f)
        font.setColor(0.6f, 0.6f, 0.6f, 1f)
        font.draw(batch, "Tap anywhere to return to menu", 0f, 150f, CANVAS_W, Align.center, false)
        batch.end()
    }

    override fun resize(w: Int, h: Int) { viewport.update(w, h, true) }
    override fun pause()  {}; override fun resume() {}; override fun hide() {}; override fun dispose() {}
}

class WinScreen(private val game: ChaosBallGame, private val score: Int, private val deaths: Int) : Screen {
    private val camera   = OrthographicCamera()
    private val viewport = FitViewport(CANVAS_W, CANVAS_H, camera)

    override fun show() {
        Gdx.input.inputProcessor = object : InputAdapter() {
            override fun touchDown(screenX: Int, screenY: Int, pointer: Int, button: Int): Boolean {
                game.setScreen(MenuScreen(game)); return true
            }
        }
    }

    override fun render(delta: Float) {
        Gdx.gl.glClearColor(0f, 0.1f, 0.05f, 1f)
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT)
        camera.position.set(CANVAS_W/2f, CANVAS_H/2f, 0f); camera.update()
        
        val batch = game.batch
        val font = game.font
        batch.projectionMatrix = camera.combined
        batch.begin()
        font.data.setScale(5f)
        font.setColor(0.2f, 1f, 0.5f, 1f)
        font.draw(batch, "YOU WIN!", 0f, CANVAS_H/2f + 200f, CANVAS_W, Align.center, false)
        
        font.data.setScale(2.5f)
        font.setColor(1f, 1f, 1f, 1f)
        font.draw(batch, "Final Score: $score", 0f, CANVAS_H/2f + 20f, CANVAS_W, Align.center, false)
        font.draw(batch, "Total Deaths: $deaths", 0f, CANVAS_H/2f - 60f, CANVAS_W, Align.center, false)
        
        font.data.setScale(1.5f)
        font.draw(batch, "Tap anywhere to return to menu", 0f, 150f, CANVAS_W, Align.center, false)
        batch.end()
    }

    override fun resize(w: Int, h: Int) { viewport.update(w, h, true) }
    override fun pause()  {}; override fun resume() {}; override fun hide() {}; override fun dispose() {}
}
