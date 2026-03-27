package ru.neuroimagen.arviewer

import android.os.Bundle
import android.view.View
import android.view.animation.AlphaAnimation
import android.view.animation.Animation
import android.view.animation.AnimationSet
import android.view.animation.LinearInterpolator
import android.view.animation.ScaleAnimation
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

        findViewById<View>(R.id.logo_glow).startAnimation(
            AnimationSet(true).apply {
                interpolator = LinearInterpolator()
                repeatCount = Animation.INFINITE
                repeatMode = Animation.REVERSE
                addAnimation(AlphaAnimation(0.42f, 0.9f).apply {
                    duration = 4200L
                    repeatCount = Animation.INFINITE
                    repeatMode = Animation.REVERSE
                })
                addAnimation(ScaleAnimation(
                    0.94f,
                    1.08f,
                    0.94f,
                    1.08f,
                    Animation.RELATIVE_TO_SELF,
                    0.5f,
                    Animation.RELATIVE_TO_SELF,
                    0.5f,
                ).apply {
                    duration = 4200L
                    repeatCount = Animation.INFINITE
                    repeatMode = Animation.REVERSE
                })
            },
        )
    }
}
