package ru.neuroimagen.arviewer.data.cache

import android.content.Context
import androidx.annotation.OptIn
import androidx.media3.common.util.UnstableApi
import androidx.media3.database.StandaloneDatabaseProvider
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.datasource.FileDataSource
import androidx.media3.datasource.cache.CacheDataSink
import androidx.media3.datasource.cache.CacheDataSource
import androidx.media3.datasource.cache.LeastRecentlyUsedCacheEvictor
import androidx.media3.datasource.cache.SimpleCache
import java.io.File

/**
 * Media3 disk cache for video content.
 *
 * Caches video streams so playback works offline after first view.
 * Single instance per app; use [getDataSourceFactory] when building a MediaSource.
 */
object VideoCache {

    private const val CACHE_DIR_NAME = "video_cache"
    private const val MAX_BYTES = 256L * 1024 * 1024 // 256 MB
    private const val FRAGMENT_SIZE = 2L * 1024 * 1024 // 2 MB

    @Volatile
    private var cache: SimpleCache? = null
    private var dataSourceFactory: CacheDataSource.Factory? = null

    /** Returns (or lazily creates) a [CacheDataSource.Factory] backed by an on-disk LRU cache. */
    @OptIn(UnstableApi::class)
    @Synchronized
    fun getDataSourceFactory(context: Context): CacheDataSource.Factory {
        if (dataSourceFactory == null) {
            val cacheDir = File(context.cacheDir, CACHE_DIR_NAME)
            val evictor = LeastRecentlyUsedCacheEvictor(MAX_BYTES)
            val databaseProvider = StandaloneDatabaseProvider(context)
            cache = SimpleCache(cacheDir, evictor, databaseProvider)

            val upstream = DefaultHttpDataSource.Factory()
            val sinkFactory = CacheDataSink.Factory()
                .setCache(cache!!)
                .setFragmentSize(FRAGMENT_SIZE)

            dataSourceFactory = CacheDataSource.Factory()
                .setCache(cache!!)
                .setUpstreamDataSourceFactory(upstream)
                .setCacheReadDataSourceFactory(FileDataSource.Factory())
                .setCacheWriteDataSinkFactory(sinkFactory)
        }
        return dataSourceFactory!!
    }

    /** Releases the cache. Normally not needed — keep for the app lifetime. */
    @Synchronized
    fun release() {
        try {
            cache?.release()
        } catch (_: Exception) { }
        cache = null
        dataSourceFactory = null
    }
}
