package com.chaosball.game

import com.badlogic.gdx.Gdx
import com.badlogic.gdx.InputAdapter
import com.badlogic.gdx.graphics.GL20
import com.badlogic.gdx.graphics.glutils.ShapeRenderer
import com.badlogic.gdx.math.Vector2
import com.badlogic.gdx.utils.Align
import com.badlogic.gdx.utils.viewport.FitViewport
import kotlin.math.*

/**
 * Professional Touch Overlay.
 * Features a dynamic joystick that centers on touch and ergonomic buttons.
 */
class TouchInputHandler(private val viewport: FitViewport) : InputAdapter() {

    // Dynamic Joystick State
    private var joyCx = 0f
    private var joyCy = 0f
    private val joyOuterR = 150f
    private val joyKnobR  = 65f
    private var isJoyActive = false
    
    private var joyTouchId = -1
    private var knobX = 0f; private var knobY = 0f
    var joyX = 0f; var joyY = 0f

    // Action Buttons (Ergonomic Thumb Arc)
    private val jumpCx = CANVAS_W - 220f
    private val jumpCy = 220f
    private val dashCx = CANVAS_W - 480f
    private val dashCy = 180f
    private val fireCx = CANVAS_W - 180f
    private val fireCy = 480f
    private val btnR = 100f

    // Input state
    var jumpJustPressed  = false; private var jumpHeld = false; private var jumpConsumed = false
    var dashJustPressed  = false; private var dashHeld = false; private var dashConsumed = false
    var shootJustPressed = false; var shootWorldPos: Vector2? = null
    var tapShootPos: Vector2? = null

    init { Gdx.input.inputProcessor = this }

    private fun screenToWorld(sx: Int, sy: Int): Vector2 {
        return viewport.unproject(Vector2(sx.toFloat(), sy.toFloat()))
    }

    override fun touchDown(screenX: Int, screenY: Int, pointer: Int, button: Int): Boolean {
        val w = screenToWorld(screenX, screenY)
        
        if (w.x < CANVAS_W * 0.45f) {
            // Initialize Dynamic Joystick at touch location
            joyTouchId = pointer
            joyCx = w.x; joyCy = w.y
            isJoyActive = true
            updateJoy(w.x, w.y)
        } else {
            when {
                dist(w.x, w.y, jumpCx, jumpCy) < btnR * 1.5f -> { jumpHeld = true; jumpConsumed = false }
                dist(w.x, w.y, dashCx, dashCy) < btnR * 1.5f -> { dashHeld = true; dashConsumed = false }
                dist(w.x, w.y, fireCx, fireCy) < btnR * 1.5f -> { shootJustPressed = true; shootWorldPos = Vector2(w.x, w.y) }
                else -> { tapShootPos = Vector2(w.x, w.y) }
            }
        }
        return true
    }

    override fun touchDragged(screenX: Int, screenY: Int, pointer: Int): Boolean {
        if (pointer == joyTouchId) {
            val w = screenToWorld(screenX, screenY)
            updateJoy(w.x, w.y)
        }
        return true
    }

    override fun touchUp(screenX: Int, screenY: Int, pointer: Int, button: Int): Boolean {
        if (pointer == joyTouchId) {
            isJoyActive = false
            joyTouchId = -1; knobX = 0f; knobY = 0f; joyX = 0f; joyY = 0f
        }
        val w = screenToWorld(screenX, screenY)
        if (dist(w.x, w.y, jumpCx, jumpCy) < btnR * 2f) jumpHeld = false
        if (dist(w.x, w.y, dashCx, dashCy) < btnR * 2f) dashHeld = false
        return true
    }

    private fun updateJoy(wx: Float, wy: Float) {
        val dx = wx - joyCx; val dy = wy - joyCy
        val d  = hypot(dx.toDouble(), dy.toDouble()).toFloat()
        val limited = minOf(d, joyOuterR)
        knobX = if (d > 0) dx/d * limited else 0f
        knobY = if (d > 0) dy/d * limited else 0f
        joyX  = if (d > 0) dx/d * minOf(d/joyOuterR, 1f) else 0f
        joyY  = if (d > 0) dy/d * minOf(d/joyOuterR, 1f) else 0f
    }

    private fun dist(ax: Float, ay: Float, bx: Float, by: Float) = hypot((ax-bx).toDouble(), (ay-by).toDouble()).toFloat()

    fun update() {
        jumpJustPressed  = jumpHeld  && !jumpConsumed;  if (jumpJustPressed)  jumpConsumed  = true
        dashJustPressed  = dashHeld  && !dashConsumed;  if (dashJustPressed)  dashConsumed  = true
    }

    fun postFrame() {
        tapShootPos = null; shootJustPressed = false; shootWorldPos = null
    }

    fun draw(game: ChaosBallGame) {
        val shape = game.shape
        val batch = game.batch
        val font = game.font
        
        Gdx.gl.glEnable(GL20.GL_BLEND)
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA)
        
        shape.begin(ShapeRenderer.ShapeType.Filled)

        // 1. Dynamic Joystick (Only visible when touching)
        if (isJoyActive) {
            shape.setColor(1f, 1f, 1f, 0.1f) 
            shape.circle(joyCx, joyCy, joyOuterR, 32)
            shape.setColor(1f, 1f, 1f, 0.3f) 
            shape.circle(joyCx + knobX, joyCy + knobY, joyKnobR, 32)
        }

        // 2. Buttons - High-End "Glass" Look
        drawButton(shape, jumpCx, jumpCy, btnR, 0.2f, 1f, 0.5f) // JUMP
        drawButton(shape, dashCx, dashCy, btnR * 0.85f, 0.3f, 0.7f, 1f) // DASH
        drawButton(shape, fireCx, fireCy, btnR * 0.9f, 1f, 0.8f, 0.2f) // FIRE

        shape.end()
        
        // 3. Button Labels
        batch.begin()
        font.data.setScale(1.6f)
        font.setColor(1f, 1f, 1f, 0.5f)
        font.draw(batch, "JUMP", jumpCx - 100f, jumpCy + 10f, 200f, Align.center, false)
        font.draw(batch, "DASH", dashCx - 100f, dashCy + 10f, 200f, Align.center, false)
        font.draw(batch, "FIRE", fireCx - 100f, fireCy + 10f, 200f, Align.center, false)
        batch.end()

        Gdx.gl.glDisable(GL20.GL_BLEND)
    }

    private fun drawButton(shape: ShapeRenderer, cx: Float, cy: Float, r: Float, red: Float, g: Float, b: Float) {
        // Main translucent body
        shape.setColor(red, g, b, 0.15f)
        shape.circle(cx, cy, r, 32)
        // Bright rim
        shape.end()
        shape.begin(ShapeRenderer.ShapeType.Line)
        shape.setColor(red, g, b, 0.5f)
        shape.circle(cx, cy, r, 32)
        shape.end()
        shape.begin(ShapeRenderer.ShapeType.Filled)
    }
}
