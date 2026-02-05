package ru.neuroimagen.arviewer.ui

import ru.neuroimagen.arviewer.data.model.ContentUnavailableReason
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.R

/**
 * Maps [ViewerError] to string resource IDs for user-facing messages.
 */
object ViewerErrorMessages {

    fun getMessageResId(error: ViewerError): Int = when (error) {
        is ViewerError.Unavailable -> getReasonResId(error.reason)
        is ViewerError.Network -> R.string.error_network
        is ViewerError.Server -> R.string.error_server
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
