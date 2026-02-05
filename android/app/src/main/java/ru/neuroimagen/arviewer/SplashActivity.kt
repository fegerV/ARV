package ru.neuroimagen.arviewer

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity
import ru.neuroimagen.arviewer.databinding.ActivitySplashBinding

/**
 * Экран загрузки при старте приложения (запуск по иконке).
 * После короткой задержки открывает [MainActivity].
 * Deep links по-прежнему открывают [MainActivity] напрямую.
 */
class SplashActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySplashBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySplashBinding.inflate(layoutInflater)
        setContentView(binding.root)

        Handler(Looper.getMainLooper()).postDelayed({
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }, SPLASH_DELAY_MS)
    }

    companion object {
        private const val SPLASH_DELAY_MS = 1500L
    }
}
