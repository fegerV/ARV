package ru.neuroimagen.arviewer.ar

import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import com.google.ar.core.ArCoreApk
import com.google.ar.core.AugmentedImageDatabase
import com.google.ar.core.Config
import com.google.ar.core.Session
import com.google.ar.core.exceptions.UnavailableArcoreNotInstalledException
import com.google.ar.core.exceptions.UnavailableDeviceNotCompatibleException
import com.google.ar.core.exceptions.UnavailableException
import com.google.ar.core.exceptions.UnavailableSdkTooOldException
import com.google.ar.core.exceptions.UnavailableUserDeclinedInstallationException
import ru.neuroimagen.arviewer.data.model.ViewerManifest

private const val TAG = "ArSessionHelper"
private const val MARKER_NAME = "marker"
private const val MARKER_WIDTH_METERS = 0.2f

/**
 * Result of an ARCore availability / installation check.
 *
 * Replaces the old [Boolean]-based API so callers can provide
 * a clear, device-specific error message to the user.
 */
sealed class ArCoreCheckResult {
    /** ARCore is installed and ready to use. */
    data object Ready : ArCoreCheckResult()

    /** Device does not support ARCore (not in the supported devices list). */
    data object DeviceNotSupported : ArCoreCheckResult()

    /** ARCore is not installed; an installation prompt has been shown. */
    data object InstallRequested : ArCoreCheckResult()

    /** User explicitly declined the ARCore installation prompt. */
    data object UserDeclinedInstall : ArCoreCheckResult()

    /** The device's Android SDK is too old for this version of ARCore. */
    data object SdkTooOld : ArCoreCheckResult()

    /** ARCore availability could not be determined (timeout / network issue). */
    data object Unknown : ArCoreCheckResult()
}

/**
 * Result of an ARCore session creation attempt.
 */
sealed class ArSessionResult {
    /** Session created successfully. */
    data class Success(val session: Session) : ArSessionResult()

    /** Device does not support ARCore. */
    data object DeviceNotCompatible : ArSessionResult()

    /** ARCore is not installed. */
    data object ArCoreNotInstalled : ArSessionResult()

    /** User declined the installation. */
    data object UserDeclined : ArSessionResult()

    /** SDK is too old for this version of ARCore. */
    data object SdkTooOld : ArSessionResult()

    /** Unexpected error during session creation. */
    data class Failed(val message: String) : ArSessionResult()
}

/**
 * Creates and configures ARCore Session with Augmented Image database from manifest marker.
 */
object ArSessionHelper {

    /**
     * Lightweight, non-blocking check of ARCore availability.
     *
     * Call from [Activity.onCreate] / [Activity.onResume] to decide early
     * whether the device can run AR at all.  Does **not** trigger an
     * installation dialog.
     *
     * @return `true` when the device is capable of running ARCore
     *         (regardless of whether it is already installed).
     */
    fun isArCoreSupported(context: Context): Boolean {
        return try {
            val availability = ArCoreApk.getInstance().checkAvailability(context)
            when (availability) {
                ArCoreApk.Availability.SUPPORTED_INSTALLED,
                ArCoreApk.Availability.SUPPORTED_APK_TOO_OLD,
                ArCoreApk.Availability.SUPPORTED_NOT_INSTALLED -> true

                ArCoreApk.Availability.UNSUPPORTED_DEVICE_NOT_CAPABLE -> false

                ArCoreApk.Availability.UNKNOWN_CHECKING,
                ArCoreApk.Availability.UNKNOWN_TIMED_OUT,
                ArCoreApk.Availability.UNKNOWN_ERROR -> {
                    Log.w(TAG, "ARCore availability unknown: $availability")
                    // Optimistically assume supported — requestInstall will decide.
                    true
                }
            }
        } catch (e: Throwable) {
            Log.e(TAG, "isArCoreSupported failed", e)
            false
        }
    }

    /**
     * Checks ARCore availability and requests installation when needed.
     *
     * Returns a granular [ArCoreCheckResult] so callers can show the right
     * error message (device unsupported vs. needs install vs. user declined, etc.).
     */
    fun checkAndInstallArCore(activity: Activity): ArCoreCheckResult {
        return try {
            // Quick pre-check: is the device even capable?
            val availability = ArCoreApk.getInstance().checkAvailability(activity)
            if (availability == ArCoreApk.Availability.UNSUPPORTED_DEVICE_NOT_CAPABLE) {
                return ArCoreCheckResult.DeviceNotSupported
            }

            when (ArCoreApk.getInstance().requestInstall(activity, true)) {
                ArCoreApk.InstallStatus.INSTALLED -> ArCoreCheckResult.Ready
                ArCoreApk.InstallStatus.INSTALL_REQUESTED -> ArCoreCheckResult.InstallRequested
                else -> ArCoreCheckResult.Unknown
            }
        } catch (e: UnavailableDeviceNotCompatibleException) {
            Log.w(TAG, "Device not compatible with ARCore", e)
            ArCoreCheckResult.DeviceNotSupported
        } catch (e: UnavailableUserDeclinedInstallationException) {
            Log.w(TAG, "User declined ARCore installation", e)
            ArCoreCheckResult.UserDeclinedInstall
        } catch (e: UnavailableSdkTooOldException) {
            Log.w(TAG, "Android SDK too old for ARCore", e)
            ArCoreCheckResult.SdkTooOld
        } catch (e: UnavailableArcoreNotInstalledException) {
            Log.w(TAG, "ARCore not installed", e)
            ArCoreCheckResult.InstallRequested
        } catch (e: Throwable) {
            Log.e(TAG, "ARCore check/install failed", e)
            ArCoreCheckResult.Unknown
        }
    }

    /**
     * Creates a Session with Augmented Image mode and the marker from the manifest.
     *
     * Must be called on main thread.  Bitmap is not recycled by this method.
     * Returns a granular [ArSessionResult] for proper error handling.
     */
    fun createSession(activity: Activity, bitmap: Bitmap, manifest: ViewerManifest): ArSessionResult {
        return try {
            val session = Session(activity)
            val config = Config(session)
            val db = AugmentedImageDatabase(session)
            db.addImage(MARKER_NAME, bitmap, MARKER_WIDTH_METERS)
            config.augmentedImageDatabase = db
            config.focusMode = Config.FocusMode.AUTO
            session.configure(config)
            ArSessionResult.Success(session)
        } catch (e: UnavailableDeviceNotCompatibleException) {
            Log.e(TAG, "Device not compatible", e)
            ArSessionResult.DeviceNotCompatible
        } catch (e: UnavailableArcoreNotInstalledException) {
            Log.e(TAG, "ARCore not installed", e)
            ArSessionResult.ArCoreNotInstalled
        } catch (e: UnavailableUserDeclinedInstallationException) {
            Log.e(TAG, "User declined installation", e)
            ArSessionResult.UserDeclined
        } catch (e: UnavailableSdkTooOldException) {
            Log.e(TAG, "SDK too old", e)
            ArSessionResult.SdkTooOld
        } catch (e: UnavailableException) {
            Log.e(TAG, "ARCore session creation failed", e)
            ArSessionResult.Failed(e.message ?: "Unknown ARCore error")
        } catch (e: Throwable) {
            Log.e(TAG, "Unexpected error creating AR session", e)
            ArSessionResult.Failed(e.message ?: "Unexpected error")
        }
    }
}
