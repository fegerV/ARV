package ru.neuroimagen.arviewer.data.model

import com.google.gson.annotations.SerializedName

/**
 * Video object in viewer manifest (and active-video response).
 * Optional fields match backend schema and active-video extras.
 */
data class ViewerManifestVideo(
    @SerializedName("id") val id: Int,
    @SerializedName("title") val title: String,
    @SerializedName("video_url") val videoUrl: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String? = null,
    @SerializedName("duration") val duration: Int? = null,
    @SerializedName("width") val width: Int? = null,
    @SerializedName("height") val height: Int? = null,
    @SerializedName("mime_type") val mimeType: String? = null,
    @SerializedName("selection_source") val selectionSource: String? = null,
    @SerializedName("schedule_id") val scheduleId: Int? = null,
    @SerializedName("expires_in_days") val expiresInDays: Int? = null,
    @SerializedName("selected_at") val selectedAt: String? = null,
    // Active-video only
    @SerializedName("preview_url") val previewUrl: String? = null,
    @SerializedName("is_active") val isActive: Boolean? = null,
    @SerializedName("rotation_type") val rotationType: String? = null,
    @SerializedName("subscription_end") val subscriptionEnd: String? = null,
    @SerializedName("video_created_at") val videoCreatedAt: String? = null
)
