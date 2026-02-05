package ru.neuroimagen.arviewer.data.model

import com.google.gson.annotations.SerializedName

/**
 * Response from GET /api/viewer/ar/{unique_id}/manifest.
 * Contains marker image URL, video, and metadata for AR viewer.
 */
data class ViewerManifest(
    @SerializedName("manifest_version") val manifestVersion: String,
    @SerializedName("unique_id") val uniqueId: String,
    @SerializedName("order_number") val orderNumber: String,
    @SerializedName("marker_image_url") val markerImageUrl: String,
    @SerializedName("photo_url") val photoUrl: String,
    @SerializedName("video") val video: ViewerManifestVideo,
    @SerializedName("expires_at") val expiresAt: String,
    @SerializedName("status") val status: String
)
