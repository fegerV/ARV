package ru.neuroimagen.arviewer.data.api

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import ru.neuroimagen.arviewer.BuildConfig
import ru.neuroimagen.arviewer.data.repository.ViewerRepository
import java.util.concurrent.TimeUnit

/**
 * Provides ViewerApi and ViewerRepository.
 * Base URL must end with / so that paths "api/viewer/ar/..." resolve correctly.
 */
object ApiProvider {

    private val okHttp = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(20, TimeUnit.SECONDS)
        .build()

    private val baseUrl: String
        get() {
            val url = BuildConfig.API_BASE_URL
            return if (url.endsWith("/")) url else "$url/"
        }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val viewerApi: ViewerApi by lazy { retrofit.create(ViewerApi::class.java) }

    val viewerRepository: ViewerRepository by lazy { ViewerRepository(viewerApi) }
}
