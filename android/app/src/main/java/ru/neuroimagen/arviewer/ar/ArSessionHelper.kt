package ru.neuroimagen.arviewer.ar

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import com.google.ar.core.ArCoreApk
import com.google.ar.core.AugmentedImageDatabase
import com.google.ar.core.Config
import com.google.ar.core.Session
import com.google.ar.core.exceptions.UnavailableException
import ru.neuroimagen.arviewer.data.model.ViewerManifest

private const val TAG = "ArSessionHelper"
private const val MARKER_NAME = "marker"
private const val MARKER_WIDTH_METERS = 0.2f

/**
 * Creates and configures ARCore Session with Augmented Image database from manifest marker.
 */
object ArSessionHelper {

    /**
     * Checks if ARCore is available and installs if needed.
     * @return true if ready to create session, false if user must install or device unsupported.
     */
    fun checkAndInstallArCore(activity: Activity): Boolean {
        return when (ArCoreApk.getInstance().requestInstall(activity, true)) {
            ArCoreApk.InstallStatus.INSTALLED -> true
            ArCoreApk.InstallStatus.INSTALL_REQUESTED -> false
            else -> false
        }
    }

    /**
     * Creates a Session with Augmented Image mode and the marker from the manifest.
     * Must be called on main thread. Bitmap is not recycled by this method.
     */
    fun createSession(activity: Activity, bitmap: Bitmap, manifest: ViewerManifest): Session? {
        return try {
            val session = Session(activity)
            val config = Config(session)
            // Augmented Images enabled automatically when database is set
            val db = AugmentedImageDatabase(session)
            db.addImage(MARKER_NAME, bitmap, MARKER_WIDTH_METERS)
            config.augmentedImageDatabase = db
            config.focusMode = Config.FocusMode.AUTO
            session.configure(config)
            session
        } catch (e: UnavailableException) {
            Log.e(TAG, "ARCore session creation failed", e)
            null
        }
    }
}
