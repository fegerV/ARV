package ru.neuroimagen.arviewer.data.model

/**
 * Domain error for viewer flow.
 *
 * Maps from [ContentCheckResponse.reason], HTTP errors, and device-side
 * ARCore / hardware issues.
 *
 * Extends [Exception] so it can be used with [Result.failure].
 */
sealed class ViewerError(message: String? = null) : Exception(message) {

    // ── Server / API errors ─────────────────────────────────────────
    data class Unavailable(val reason: ContentUnavailableReason) : ViewerError(reason.apiValue)
    data class Network(val msg: String? = null) : ViewerError(msg)
    data class Server(val code: Int, val msg: String? = null) : ViewerError("HTTP $code: $msg")

    // ── Device-side errors ──────────────────────────────────────────

    /** Device is not in the ARCore supported devices list. */
    data object DeviceNotSupported : ViewerError("Device not supported by ARCore")

    /** ARCore is not installed; an installation prompt has been shown. */
    data object ArCoreInstallRequested : ViewerError("ARCore installation requested")

    /** User declined the ARCore installation prompt. */
    data object ArCoreUserDeclined : ViewerError("User declined ARCore installation")

    /** Device SDK version is too old for the required ARCore version. */
    data object ArCoreSdkTooOld : ViewerError("Android version too old for ARCore")

    /** ARCore session could not be created (generic / unexpected). */
    data class ArCoreSessionFailed(val detail: String? = null) : ViewerError(detail)

    /** Camera permission was not granted. */
    data object CameraPermissionDenied : ViewerError("Camera permission denied")
}

/**
 * Reasons returned by `GET /api/viewer/ar/{unique_id}/check` when
 * `content_available` is `false`.
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
