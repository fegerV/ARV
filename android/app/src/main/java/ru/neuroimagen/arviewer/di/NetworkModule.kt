package ru.neuroimagen.arviewer.di

import com.google.gson.Gson
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import ru.neuroimagen.arviewer.BuildConfig
import ru.neuroimagen.arviewer.data.api.AnalyticsApi
import ru.neuroimagen.arviewer.data.api.ViewerApi
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

/**
 * Hilt module that provides network-layer singletons: OkHttp, Retrofit, and API interfaces.
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideGson(): Gson = Gson()

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .build()

    @Provides
    @Singleton
    fun provideRetrofit(client: OkHttpClient, gson: Gson): Retrofit {
        val url = BuildConfig.API_BASE_URL
        val baseUrl = if (url.endsWith("/")) url else "$url/"
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    @Provides
    @Singleton
    fun provideViewerApi(retrofit: Retrofit): ViewerApi =
        retrofit.create(ViewerApi::class.java)

    @Provides
    @Singleton
    fun provideAnalyticsApi(retrofit: Retrofit): AnalyticsApi =
        retrofit.create(AnalyticsApi::class.java)
}
