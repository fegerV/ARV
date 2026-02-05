package ru.neuroimagen.arviewer.data.api

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Url
import ru.neuroimagen.arviewer.data.model.ContentCheckResponse
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.model.ViewerManifestVideo

/**
 * Viewer API under /api/viewer.
 * Base URL must end with slash, e.g. https://ar.neuroimagen.ru/
 * Paths are relative: api/viewer/ar/{uniqueId}/...
 */
interface ViewerApi {

    @GET("api/viewer/ar/{uniqueId}/check")
    suspend fun checkContent(@Path("uniqueId") uniqueId: String): Response<ContentCheckResponse>

    @GET("api/viewer/ar/{uniqueId}/manifest")
    suspend fun getManifest(@Path("uniqueId") uniqueId: String): Response<ViewerManifest>

    @GET("api/viewer/ar/{uniqueId}/active-video")
    suspend fun getActiveVideo(@Path("uniqueId") uniqueId: String): Response<ViewerManifestVideo>

    /**
     * Download image bytes by URL (e.g. marker_image_url).
     * Pass full URL via @Url; base URL is ignored for this call.
     */
    @GET
    suspend fun downloadImage(@Url url: String): Response<ResponseBody>
}
