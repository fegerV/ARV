package ru.neuroimagen.arviewer

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import ru.neuroimagen.arviewer.util.CrashReporter

/**
 * Application entry point.
 *
 * [HiltAndroidApp] triggers Hilt code generation and serves as the
 * application-level dependency container.
 * Initializes Firebase Crashlytics for crash reporting.
 */
@HiltAndroidApp
class ArViewerApp : Application() {

    override fun onCreate() {
        super.onCreate()
        CrashReporter.init(enabled = !BuildConfig.DEBUG)
    }
}
