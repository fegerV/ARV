package ru.neuroimagen.arviewer.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * Analytics API for session tracking.
 * POST /api/analytics/mobile/sessions — регистрация сессии просмотра (для статистики по устройствам и моделям).
 */
interface AnalyticsApi {

    @POST("api/analytics/mobile/sessions")
    suspend fun createSession(@Body body: Map<String, Any?>): Response<Unit>
}
