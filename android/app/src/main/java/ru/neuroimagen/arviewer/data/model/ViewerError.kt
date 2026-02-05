package ru.neuroimagen.arviewer.data.model

/**
 * Domain error for viewer flow.
 * Maps from ContentCheckResponse.reason and HTTP errors.
 * Extends Exception so it can be used with Result.failure().
 */
sealed class ViewerError(message: String? = null) : Exception(message) {
    data class Unavailable(val reason: ContentUnavailableReason) : ViewerError(reason.apiValue)
    data class Network(val msg: String? = null) : ViewerError(msg)
    data class Server(val code: Int, val msg: String? = null) : ViewerError("HTTP $code: $msg")
}

/**
 * Reasons returned by GET /api/viewer/ar/{unique_id}/check when content_available is false.
 */
enum class ContentUnavailableReason(val apiValue: String) {
    INVALID_UNIQUE_ID("invalid_unique_id"),
    NOT_FOUND("not_found"),
    SUBSCRIPTION_EXPIRED("subscription_expired"),
    CONTENT_NOT_ACTIVE("content_not_active"),
    MARKER_IMAGE_NOT_AVAILABLE("marker_image_not_available"),
    MARKER_STILL_GENERATING("marker_still_generating"),
    NO_PLAYABLE_VIDEO("no_playable_video"),
    UNKNOWN("");

    companion object {
        fun fromApiValue(value: String?): ContentUnavailableReason =
            entries.find { it.apiValue == value } ?: UNKNOWN
    }
}
