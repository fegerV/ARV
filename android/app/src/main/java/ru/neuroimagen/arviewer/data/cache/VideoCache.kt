package ru.neuroimagen.arviewer.data.cache

import android.content.Context
import com.google.android.exoplayer2.database.StandaloneDatabaseProvider
import com.google.android.exoplayer2.upstream.DefaultHttpDataSource
import com.google.android.exoplayer2.upstream.cache.CacheDataSource
import com.google.android.exoplayer2.upstream.cache.LeastRecentlyUsedCacheEvictor
import com.google.android.exoplayer2.upstream.cache.SimpleCache
import java.io.File

/**
 * ExoPlayer disk cache for video. Caches streams so playback works offline after first view.
 * Single instance per app; use [dataSourceFactory] when building MediaSource.
 */
object VideoCache {

    private const val CACHE_DIR_NAME = "video_cache"
    private const val MAX_BYTES = 256 * 1024 * 1024L // 256 MB
    private const val FRAGMENT_SIZE = 2 * 1024 * 1024L // 2 MB

    @Volatile
    private var cache: SimpleCache? = null
    private var dataSourceFactory: CacheDataSource.Factory? = null

    @Synchronized
    fun getDataSourceFactory(context: Context): CacheDataSource.Factory {
        if (dataSourceFactory == null) {
            val cacheDir = File(context.cacheDir, CACHE_DIR_NAME)
            val evictor = LeastRecentlyUsedCacheEvictor(MAX_BYTES)
            val databaseProvider = StandaloneDatabaseProvider(context)
            cache = SimpleCache(cacheDir, evictor, databaseProvider)
            val upstream = DefaultHttpDataSource.Factory()
            val cacheDataSinkFactory = com.google.android.exoplayer2.upstream.cache.CacheDataSink.Factory()
                .setCache(cache!!)
                .setFragmentSize(FRAGMENT_SIZE)
            dataSourceFactory = CacheDataSource.Factory()
                .setCache(cache!!)
                .setUpstreamDataSourceFactory(upstream)
                .setCacheReadDataSourceFactory(com.google.android.exoplayer2.upstream.FileDataSource.Factory())
                .setCacheWriteDataSinkFactory(cacheDataSinkFactory)
        }
        return dataSourceFactory!!
    }

    /**
     * Releases cache. Call only when app is being destroyed if needed; normally keep for app lifetime.
     */
    @Synchronized
    fun release() {
        try {
            cache?.release()
        } catch (_: Exception) { }
        cache = null
        dataSourceFactory = null
    }
}
