package ru.neuroimagen.arviewer

import android.os.Bundle
import android.view.View
import android.view.animation.AlphaAnimation
import android.view.animation.LinearInterpolator
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity

/**
 * Simple screen explaining how to use the app: 4 steps from purchase to AR experience.
 * Shown for RuStore moderation and user onboarding.
 */
class HowItWorksActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_how_it_works)
        findViewById<ImageView>(R.id.button_back).setOnClickListener { finish() }
        startHeroStarAnimation()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun startHeroStarAnimation() {
        val stars = listOf<View>(
            findViewById(R.id.star_one),
            findViewById(R.id.star_two),
            findViewById(R.id.star_three),
        )
        stars.forEachIndexed { index, star ->
            val animation = AlphaAnimation(0.3f, 1f).apply {
                duration = 3200L + (index * 800L)
                repeatCount = AlphaAnimation.INFINITE
                repeatMode = AlphaAnimation.REVERSE
                interpolator = LinearInterpolator()
                startOffset = index * 450L
            }
            star.startAnimation(animation)
        }
    }
}
