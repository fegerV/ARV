package ru.neuroimagen.arviewer.data.model

import com.google.gson.annotations.SerializedName

/**
 * Response from GET /api/viewer/ar/{unique_id}/check.
 * Indicates whether AR content is available without incrementing view count.
 */
data class ContentCheckResponse(
    @SerializedName("content_available") val contentAvailable: Boolean,
    @SerializedName("reason") val reason: String? = null
)
