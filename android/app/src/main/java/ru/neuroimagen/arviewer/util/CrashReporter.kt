package ru.neuroimagen.arviewer.util

import android.util.Log
import com.google.firebase.crashlytics.ktx.crashlytics
import com.google.firebase.ktx.Firebase

/**
 * Centralized crash and error reporting wrapper over Firebase Crashlytics.
 *
 * All non-fatal exceptions and contextual breadcrumbs should go through this
 * object so the reporting backend can be swapped without touching call sites.
 *
 * **Setup**: Replace the placeholder `google-services.json` in `app/` with a
 * real config from the Firebase Console to enable crash delivery.
 */
object CrashReporter {

    private const val TAG = "CrashReporter"

    /**
     * Initialize Crashlytics settings.
     * Call from [ru.neuroimagen.arviewer.ArViewerApp.onCreate].
     *
     * @param enabled `true` for release builds, `false` to disable during development.
     */
    fun init(enabled: Boolean) {
        try {
            Firebase.crashlytics.setCrashlyticsCollectionEnabled(enabled)
            Log.i(TAG, "Crashlytics collection enabled=$enabled")
        } catch (e: Exception) {
            Log.w(TAG, "Crashlytics init failed (placeholder google-services.json?)", e)
        }
    }

    /**
     * Record a non-fatal exception. Shows up in the Crashlytics dashboard
     * under "Non-fatals" with full stack trace.
     */
    fun recordException(throwable: Throwable) {
        try {
            Firebase.crashlytics.recordException(throwable)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to record exception", e)
        }
    }

    /**
     * Log a breadcrumb message visible in the Crashlytics "Logs" tab when
     * a crash or non-fatal event is reported.
     */
    fun log(message: String) {
        try {
            Firebase.crashlytics.log(message)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to log to Crashlytics", e)
        }
    }

    /**
     * Set a custom key-value pair that will appear in the Crashlytics dashboard.
     * Useful for filtering crashes by screen, user action, etc.
     */
    fun setCustomKey(key: String, value: String) {
        try {
            Firebase.crashlytics.setCustomKey(key, value)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to set Crashlytics key", e)
        }
    }

    /**
     * Set a user identifier for correlating crashes to a specific session.
     */
    fun setUserId(id: String) {
        try {
            Firebase.crashlytics.setUserId(id)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to set Crashlytics userId", e)
        }
    }
}
