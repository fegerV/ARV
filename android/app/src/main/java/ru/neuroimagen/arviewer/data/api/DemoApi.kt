package ru.neuroimagen.arviewer.data.api

import retrofit2.Response
import retrofit2.http.GET

/**
 * Demo list API for the intro screen.
 * GET /api/viewer/demo/list returns 5 demos with thumbnail URLs.
 */
interface DemoApi {

    @GET("api/viewer/demo/list")
    suspend fun getDemoList(): Response<DemoListResponse>
}

/**
 * Response: {"demos": [{"unique_id": "demo_1", "title": "Демо 1", "marker_image_url": "https://..."}, ...]}
 */
data class DemoListResponse(
    val demos: List<DemoItem>,
)

data class DemoItem(
    val unique_id: String,
    val title: String,
    val marker_image_url: String?,
)
