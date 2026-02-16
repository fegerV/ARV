package ru.neuroimagen.arviewer.util

import android.util.Log

/**
 * Centralized crash and error reporting facade.
 *
 * Currently logs to Logcat. To enable Firebase Crashlytics:
 * 1. Create a Firebase project at https://console.firebase.google.com
 * 2. Add `google-services.json` to `app/`
 * 3. Uncomment Firebase plugins in both `build.gradle.kts` files
 * 4. Uncomment Firebase dependencies in `app/build.gradle.kts`
 * 5. Replace the bodies below with Crashlytics API calls
 */
object CrashReporting {

    private const val TAG = "CrashReporting"

    /** Initialize crash reporting. Call from [android.app.Application.onCreate]. */
    fun initialize() {
        // TODO: FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(true)
        Log.d(TAG, "Crash reporting initialized (no-op, configure Firebase for production)")
    }

    /** Log a non-fatal exception for crash analytics. */
    fun logException(throwable: Throwable) {
        // TODO: FirebaseCrashlytics.getInstance().recordException(throwable)
        Log.w(TAG, "Non-fatal exception", throwable)
    }

    /** Attach a custom key-value pair to future crash reports. */
    fun setCustomKey(key: String, value: String) {
        // TODO: FirebaseCrashlytics.getInstance().setCustomKey(key, value)
        Log.d(TAG, "Custom key: $key=$value")
    }
}
