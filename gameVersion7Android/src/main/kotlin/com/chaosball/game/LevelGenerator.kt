package com.chaosball.game

import kotlin.math.*
import kotlin.random.Random

/** Level Generator - Handles procedural level creation */
object LevelGenerator {

    private fun overlap(ax: Float, ay: Float, aw: Float, ah: Float,
                        bx: Float, by: Float, bw: Float, bh: Float, margin: Float = 20f) =
        ax - margin < bx + bw && ax + aw + margin > bx &&
        ay - margin < by + bh && ay + ah + margin > by

    private fun nearCentre(x: Float, y: Float, w: Float, h: Float, safeR: Float = GOAL_SAFE_R): Boolean {
        val dx = x + w / 2f - GOAL_CX; val dy = y + h / 2f - GOAL_CY
        return sqrt(dx * dx + dy * dy) < safeR
    }

    private fun nearSpawn(x: Float, y: Float, w: Float, h: Float, sx: Float, sy: Float): Boolean {
        val dx = x + w / 2f - sx; val dy = y + h / 2f - sy
        return sqrt(dx * dx + dy * dy) < SPAWN_SAFE_R
    }

    private fun placePlatform(existing: MutableList<Rect>, x: Float, y: Float, w: Float, h: Float, sx: Float, sy: Float): Boolean {
        if (nearCentre(x, y, w, h)) return false
        if (nearSpawn(x, y, w, h, sx, sy)) return false
        val mg = 40f
        if (x < mg || y < mg || x + w > CANVAS_W - mg || y + h > CANVAS_H - mg) return false
        for (e in existing) if (overlap(x, y, w, h, e.x, e.y, e.w, e.h)) return false
        existing.add(Rect(x, y, w, h)); return true
    }

    private fun addShape(platforms: MutableList<Rect>, shape: List<Rect>, sx: Float, sy: Float): Boolean {
        val tmp = platforms.toMutableList()
        for (p in shape) if (!placePlatform(tmp, p.x, p.y, p.w, p.h, sx, sy)) return false
        platforms.clear(); platforms.addAll(tmp); return true
    }

    // ── Shape generators ──────────────────────────────────────────────────

    private fun randSlab(r: Random): List<Rect> {
        val w = r.nextInt(120, 341).toFloat(); val h = r.nextInt(18, 29).toFloat()
        return listOf(Rect(r.nextInt(60, (CANVAS_W - 60 - w).toInt()).toFloat(),
                           r.nextInt(80, (CANVAS_H - 80 - h).toInt()).toFloat(), w, h))
    }

    private fun randPillar(r: Random): List<Rect> {
        val w = r.nextInt(18, 31).toFloat(); val h = r.nextInt(100, 261).toFloat()
        return listOf(Rect(r.nextInt(60, (CANVAS_W - 60 - w).toInt()).toFloat(),
                           r.nextInt(80, (CANVAS_H - 80 - h).toInt()).toFloat(), w, h))
    }

    private fun randL(r: Random): List<Rect> {
        val w1 = r.nextInt(160, 281).toFloat(); val h1 = 22f; val w2 = 22f; val h2 = r.nextInt(80, 181).toFloat()
        val x = r.nextInt(60, (CANVAS_W - 60 - w1).toInt()).toFloat()
        val y = r.nextInt(80, (CANVAS_H - 80 - h1 - h2).toInt()).toFloat()
        return if (r.nextBoolean()) listOf(Rect(x,y,w1,h1), Rect(x+w1-w2, y+h1, w2, h2))
        else listOf(Rect(x,y,w1,h1), Rect(x, y+h1, w2, h2))
    }

    private fun randT(r: Random): List<Rect> {
        val w1 = r.nextInt(180, 301).toFloat(); val h1 = 22f; val w2 = 22f; val h2 = r.nextInt(60, 141).toFloat()
        val x = r.nextInt(60, (CANVAS_W - 60 - w1).toInt()).toFloat()
        val y = r.nextInt(80, (CANVAS_H - 80 - h1 - h2).toInt()).toFloat()
        return listOf(Rect(x,y,w1,h1), Rect(x+w1/2f-w2/2f, y+h1, w2, h2))
    }

    private fun randStaircase(r: Random): List<Rect> {
        val sw = r.nextInt(90, 151).toFloat(); val sh = 20f
        val dx = (if (r.nextBoolean()) 1 else -1) * r.nextInt(60, 101).toFloat()
        val dy = r.nextInt(60, 121).toFloat()
        val x0 = r.nextInt(200, (CANVAS_W - 200 - sw).toInt()).toFloat()
        val y0 = r.nextInt(200, (CANVAS_H - 200 - sh).toInt()).toFloat()
        return (0..2).map { Rect(x0 + dx * it, y0 + dy * it, sw, sh) }
    }

    private fun randU(r: Random): List<Rect> {
        val bw = r.nextInt(160, 261).toFloat(); val bh = 20f
        val wh = r.nextInt(80, 161).toFloat(); val ww = 20f
        val x = r.nextInt(80, (CANVAS_W - 80 - bw).toInt()).toFloat()
        val y = r.nextInt(80, (CANVAS_H - 80 - bh - wh).toInt()).toFloat()
        return listOf(Rect(x, y+wh, bw, bh), Rect(x, y, ww, wh), Rect(x+bw-ww, y, ww, wh))
    }

    private fun randRing(r: Random): List<Rect> {
        val sz = r.nextInt(160, 261).toFloat(); val t = 18f
        val x = r.nextInt(80, (CANVAS_W - 80 - sz).toInt()).toFloat()
        val y = r.nextInt(80, (CANVAS_H - 80 - sz).toInt()).toFloat()
        return listOf(Rect(x,y,sz,t), Rect(x,y+sz-t,sz,t), Rect(x,y+t,t,sz-2*t), Rect(x+sz-t,y+t,t,sz-2*t))
    }

    private fun randCross(r: Random): List<Rect> {
        val arm = r.nextInt(100, 181).toFloat(); val t = 22f
        val x = r.nextInt(100, (CANVAS_W - 100 - arm).toInt()).toFloat()
        val y = r.nextInt(100, (CANVAS_H - 100 - arm).toInt()).toFloat()
        return listOf(Rect(x, y+arm/2f-t/2f, arm, t), Rect(x+arm/2f-t/2f, y, t, arm))
    }

    private fun shapes(r: Random): List<Rect> = when (r.nextInt(10)) {
        0,1,2 -> randSlab(r); 3 -> randPillar(r); 4 -> randL(r)
        5 -> randT(r); 6 -> randStaircase(r); 7 -> randU(r)
        8 -> randRing(r); else -> randCross(r)
    }

    private fun spikesForPlatform(px: Float, py: Float, pw: Float, ph: Float, difficulty: Int, r: Random): List<Spike> {
        val st = 24f
        val faces = listOf(
            Pair(SpikeDir.UP,    Rect(px, py-st, pw, st)),
            Pair(SpikeDir.DOWN,  Rect(px, py+ph, pw, st)),
            Pair(SpikeDir.RIGHT, Rect(px+pw, py, st, ph)),
            Pair(SpikeDir.LEFT,  Rect(px-st, py, st, ph))
        ).shuffled(r)
        val maxF = 1 + difficulty / 2
        val prob = 0.35f + difficulty * 0.10f
        val out = mutableListOf<Spike>()
        for ((dir, rect) in faces.take(maxF)) {
            if (r.nextFloat() > prob) continue
            val sx = rect.x.coerceIn(10f, CANVAS_W - 10f - rect.w)
            val sy = rect.y.coerceIn(10f, CANVAS_H - 10f - rect.h)
            out.add(Spike(Rect(sx, sy, rect.w, rect.h), dir))
        }
        return out
    }

    private fun genRotators(count: Int, spawn: Vec2, r: Random): List<RotatorData> {
        val out = mutableListOf<RotatorData>(); var att = 0
        while (out.size < count && att < 200) {
            att++
            val px = r.nextInt(200, (CANVAS_W - 200).toInt()).toFloat()
            val py = r.nextInt(150, (CANVAS_H - 150).toInt()).toFloat()
            if (hypot((px - GOAL_CX).toDouble(), (py - GOAL_CY).toDouble()) < 200) continue
            if (hypot((px - spawn.x).toDouble(), (py - spawn.y).toDouble()) < 220) continue
            val arm = r.nextInt(90, 161).toFloat()
            val thick = r.nextInt(14, 23).toFloat()
            val speed = (if (r.nextBoolean()) 1 else -1) * r.nextFloat() * 40f + 40f
            out.add(RotatorData(Vec2(px, py), arm, thick, speed))
        }
        return out
    }

    private fun genEnemies(count: Int, spawn: Vec2, r: Random): List<EnemyData> {
        val corners = listOf(Vec2(120f,120f), Vec2(1800f,120f), Vec2(120f,960f), Vec2(1800f,960f))
            .sortedByDescending { it.dist(spawn) }
        return corners.take(minOf(count, corners.size)).map {
            EnemyData(Vec2(it.x + r.nextInt(-60,61).toFloat(), it.y + r.nextInt(-60,61).toFloat()),
                      r.nextFloat() * 45f + 65f)
        }
    }

    private fun genShooters(count: Int, spawn: Vec2, r: Random): List<ShooterData> {
        val out = mutableListOf<ShooterData>(); var att = 0
        while (out.size < count && att < 200) {
            att++
            val px = r.nextInt(200, (CANVAS_W - 200).toInt()).toFloat()
            val py = r.nextInt(150, (CANVAS_H - 150).toInt()).toFloat()
            if (hypot((px - GOAL_CX).toDouble(), (py - GOAL_CY).toDouble()) < 220) continue
            if (hypot((px - spawn.x).toDouble(), (py - spawn.y).toDouble()) < 240) continue
            out.add(ShooterData(Vec2(px, py), r.nextFloat() * 1.7f + 1.8f))
        }
        return out
    }

    private fun genVoidWalls(r: Random) = listOf(
        VoidWallData(VoidOrientation.VERTICAL,   if (r.nextBoolean()) VoidSide.NEAR else VoidSide.FAR),
        VoidWallData(VoidOrientation.HORIZONTAL, if (r.nextBoolean()) VoidSide.NEAR else VoidSide.FAR)
    )

    private fun genCoins(platforms: List<Rect>, spawn: Vec2, difficulty: Int, r: Random): List<Vec2> {
        val coins = mutableListOf<Vec2>()
        val count = 4 + difficulty * 2
        for (p in platforms.drop(2)) {
            if (coins.size >= count) break
            val n = r.nextInt(1, minOf(4, maxOf(2, (p.w / 120f).toInt() + 1)))
            for (i in 0 until n) {
                val cx = p.x + p.w * (i + 1f) / (n + 1f)
                val cy = p.y - 40f
                if (hypot((cx - GOAL_CX).toDouble(), (cy - GOAL_CY).toDouble()) < GOAL_SAFE_R + 30) continue
                if (hypot((cx - spawn.x).toDouble(), (cy - spawn.y).toDouble()) < SPAWN_SAFE_R) continue
                if (cx < 40 || cx > CANVAS_W - 40 || cy < 40 || cy > CANVAS_H - 40) continue
                coins.add(Vec2(cx, cy))
                if (coins.size >= count) break
            }
        }
        return coins
    }

    private fun genBoostPads(platforms: List<Rect>, spawn: Vec2, r: Random): List<Triple<Float,Float,String>> {
        val dirs = listOf("up","left","right")
        val cands = platforms.drop(2).filter { it.w > 100f }.toMutableList().also { it.shuffle(r) }
        val out = mutableListOf<Triple<Float,Float,String>>()
        for (p in cands.take(3)) {
            val cx = p.x + p.w / 2f; val cy = p.y - 1f
            if (hypot((cx-GOAL_CX).toDouble(),(cy-GOAL_CY).toDouble()) < GOAL_SAFE_R+50) continue
            if (hypot((cx-spawn.x).toDouble(),(cy-spawn.y).toDouble()) < SPAWN_SAFE_R) continue
            out.add(Triple(cx, cy, dirs[r.nextInt(dirs.size)]))
        }
        return out
    }

    fun generate(levelIdx: Int): LevelData {
        val seed = levelIdx * 7919L + 42L
        val r = Random(seed); val difficulty = minOf(levelIdx, 4)
        val isSpinner = levelIdx in TIER_BASIC_END until TIER_SPINNER_END
        val isVoid    = levelIdx in TIER_SPINNER_END until TIER_VOID_END
        val isShooter = levelIdx >= TIER_SHOOTER_START

        val goal = Rect(GOAL_CX - GOAL_W/2f, GOAL_CY - GOAL_H/2f, GOAL_W, GOAL_H)
        val spawnChoices = listOf(Vec2(80f,80f), Vec2(1840f,80f), Vec2(80f,1000f), Vec2(1840f,1000f))
        val spawn = spawnChoices[r.nextInt(spawnChoices.size)]

        val platforms = mutableListOf<Rect>()
        val boundaryOptions = listOf(Rect(0f,1050f,CANVAS_W,30f), Rect(0f,0f,CANVAS_W,30f), Rect(0f,0f,30f,CANVAS_H), Rect(1890f,0f,30f,CANVAS_H))
        platforms.add(boundaryOptions[r.nextInt(boundaryOptions.size)])
        val pw2 = 200f; val ph2 = 22f; val px2 = (spawn.x - pw2/2f).coerceIn(10f, CANVAS_W - 10f - pw2); val py2 = (spawn.y + 30f).coerceIn(10f, CANVAS_H - 10f - ph2)
        platforms.add(Rect(px2, py2, pw2, ph2))

        var att = 0; while (platforms.size < 10 + difficulty * 2 + 2 && att < 400) { att++; addShape(platforms, shapes(r), spawn.x, spawn.y) }

        val bl = listOf(Rect(GOAL_CX-GOAL_SAFE_R, GOAL_CY-GOAL_SAFE_R, GOAL_SAFE_R*2f, GOAL_SAFE_R*2f), Rect(spawn.x-SPAWN_SAFE_R, spawn.y-SPAWN_SAFE_R, SPAWN_SAFE_R*2f, SPAWN_SAFE_R*2f))
        val spikes = mutableListOf<Spike>()
        for (p in platforms.drop(2)) {
            for (s in spikesForPlatform(p.x, p.y, p.w, p.h, difficulty, r)) {
                if (bl.none { b -> overlap(s.rect.x,s.rect.y,s.rect.w,s.rect.h, b.x,b.y,b.w,b.h, 0f) }) spikes.add(s)
            }
        }

        val rotators = if (isSpinner) genRotators(listOf(1,2,2,3)[levelIdx - TIER_BASIC_END], spawn, r) else if (isVoid) genRotators(r.nextInt(1,3), spawn, r) else emptyList()
        val enemies = if (isVoid) genEnemies(if (isShooter) r.nextInt(2,4) else r.nextInt(1,3), spawn, r) else emptyList()
        val shooters = if (isShooter) genShooters(listOf(1,2,2,3)[levelIdx - TIER_SHOOTER_START], spawn, r) else emptyList()
        val voidWalls = if (isVoid) genVoidWalls(r) else emptyList()
        val coins = genCoins(platforms, spawn, difficulty, r); val boostPads = if (levelIdx >= 4) genBoostPads(platforms, spawn, r) else emptyList()

        return LevelData(platforms, spikes, goal, spawn, rotators, enemies, shooters, voidWalls, isVoid, coins, boostPads)
    }

    val ALL_LEVELS: List<LevelData> by lazy { (0 until NUM_LEVELS).map { generate(it) } }
}
