package ru.neuroimagen.arviewer

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

/**
 * Simple screen explaining how to use the app: 4 steps from purchase to AR experience.
 * Shown for RuStore moderation and user onboarding.
 */
class HowItWorksActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_how_it_works)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }
}
