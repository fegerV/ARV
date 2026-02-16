package ru.neuroimagen.arviewer.data.cache

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.File
import java.util.concurrent.locks.ReentrantReadWriteLock
import kotlin.concurrent.read
import kotlin.concurrent.write

/**
 * Disk cache for AR marker images.
 *
 * Keyed by a **stable identifier** (e.g. `unique_id`) rather than the download
 * URL.  Yandex Disk generates a different temporary URL on every manifest
 * request; URL-based keys caused 100 % cache misses and forced a 3+ MB
 * re-download on every AR session open.
 */
object MarkerCache {

    private const val CACHE_DIR_NAME = "marker_cache"
    private const val MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000L // 7 days

    private val lock = ReentrantReadWriteLock()

    private fun cacheDir(context: Context): File {
        return File(context.cacheDir, CACHE_DIR_NAME).also {
            if (!it.exists()) it.mkdirs()
        }
    }

    /** Sanitise key to a safe filename (UUID is safe, but guard anyway). */
    private fun safeFileName(stableKey: String): String {
        return stableKey.replace(Regex("[^a-zA-Z0-9_-]"), "_").take(64)
    }

    private fun cacheFile(context: Context, stableKey: String): File {
        return File(cacheDir(context), "${safeFileName(stableKey)}.bin")
    }

    /**
     * Gets marker image from cache if present and not expired.
     *
     * @param stableKey content-stable key (e.g. `unique_id`), NOT the download URL
     * @return decoded Bitmap or null if miss / expired / error
     */
    fun get(context: Context, stableKey: String): Bitmap? = lock.read {
        val file = cacheFile(context, stableKey)
        if (!file.exists()) return null
        if (file.lastModified() + MAX_AGE_MS < System.currentTimeMillis()) {
            file.delete()
            return null
        }
        runCatching {
            val bytes = file.readBytes()
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        }.getOrNull()
    }

    /**
     * Saves marker image bytes to cache.
     *
     * @param stableKey  content-stable key (e.g. `unique_id`)
     * @param imageBytes raw image bytes (e.g. from HTTP response body)
     */
    fun put(context: Context, stableKey: String, imageBytes: ByteArray): Unit = lock.write {
        val file = cacheFile(context, stableKey)
        runCatching {
            file.writeBytes(imageBytes)
        }
    }

    /**
     * Clears all cached marker files. Call when user wants to free space or force refresh.
     */
    fun clear(context: Context): Unit = lock.write {
        cacheDir(context).listFiles()?.forEach { it.delete() }
    }
}
