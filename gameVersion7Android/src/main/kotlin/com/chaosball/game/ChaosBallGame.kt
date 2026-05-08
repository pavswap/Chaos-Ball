package com.chaosball.game

import com.badlogic.gdx.Game
import com.badlogic.gdx.graphics.g2d.BitmapFont
import com.badlogic.gdx.graphics.g2d.SpriteBatch
import com.badlogic.gdx.graphics.glutils.ShapeRenderer

/** Entry point — equivalent to main.py */
class ChaosBallGame : Game() {

    lateinit var batch: SpriteBatch
    lateinit var shape: ShapeRenderer
    lateinit var font: BitmapFont

    override fun create() {
        batch = SpriteBatch()
        shape = ShapeRenderer()
        // Uses default Arial 15pt font from LibGDX jar
        font = BitmapFont()
        font.data.setScale(3f) // Scale up for 1080p canvas
        
        setScreen(MenuScreen(this))
    }

    override fun dispose() {
        batch.dispose()
        shape.dispose()
        font.dispose()
    }
}
