package ru.neuroimagen.arviewer.ui

import ru.neuroimagen.arviewer.R
import ru.neuroimagen.arviewer.data.model.ContentUnavailableReason
import ru.neuroimagen.arviewer.data.model.ViewerError

/**
 * Maps [ViewerError] to string resource IDs for user-facing messages.
 */
object ViewerErrorMessages {

    /**
     * Whether the error is retryable (user can tap "Retry").
     *
     * Device-not-supported and SDK-too-old are permanent; everything
     * else can potentially be resolved by retrying or installing ARCore.
     */
    fun isRetryable(error: ViewerError): Boolean = when (error) {
        is ViewerError.DeviceNotSupported,
        is ViewerError.ArCoreSdkTooOld -> false
        else -> true
    }

    fun getMessageResId(error: ViewerError): Int = when (error) {
        is ViewerError.Unavailable -> getReasonResId(error.reason)
        is ViewerError.Network -> R.string.error_network
        is ViewerError.Server -> R.string.error_server

        // Device-side errors
        is ViewerError.DeviceNotSupported -> R.string.error_device_not_supported
        is ViewerError.ArCoreInstallRequested -> R.string.error_arcore_install_requested
        is ViewerError.ArCoreUserDeclined -> R.string.error_arcore_user_declined
        is ViewerError.ArCoreSdkTooOld -> R.string.error_arcore_sdk_too_old
        is ViewerError.ArCoreSessionFailed -> R.string.error_arcore_session
        is ViewerError.CameraPermissionDenied -> R.string.error_camera_required
    }

    fun getReasonResId(reason: ContentUnavailableReason): Int = when (reason) {
        ContentUnavailableReason.INVALID_UNIQUE_ID -> R.string.error_invalid_unique_id
        ContentUnavailableReason.NOT_FOUND -> R.string.error_not_found
        ContentUnavailableReason.SUBSCRIPTION_EXPIRED -> R.string.error_subscription_expired
        ContentUnavailableReason.CONTENT_NOT_ACTIVE -> R.string.error_content_not_active
        ContentUnavailableReason.MARKER_IMAGE_NOT_AVAILABLE -> R.string.error_marker_not_available
        ContentUnavailableReason.MARKER_STILL_GENERATING -> R.string.error_marker_still_generating
        ContentUnavailableReason.NO_PLAYABLE_VIDEO -> R.string.error_no_playable_video
        ContentUnavailableReason.UNKNOWN -> R.string.error_unknown
    }
}
