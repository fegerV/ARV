package ru.neuroimagen.arviewer.data.cache

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.locks.ReentrantReadWriteLock
import kotlin.concurrent.read
import kotlin.concurrent.write

/**
 * Disk cache for AR marker images.
 * Caches by URL (SHA-256 hash as filename). Reduces repeated network loads when
 * opening the same AR content.
 */
object MarkerCache {

    private const val CACHE_DIR_NAME = "marker_cache"
    private const val MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000L // 7 days

    private val lock = ReentrantReadWriteLock()

    /**
     * Returns cache directory for marker images. Uses app cache dir so OS can evict when needed.
     */
    private fun cacheDir(context: Context): File {
        return File(context.cacheDir, CACHE_DIR_NAME).also {
            if (!it.exists()) it.mkdirs()
        }
    }

    private fun cacheKey(url: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(url.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }

    private fun cacheFile(context: Context, url: String): File {
        return File(cacheDir(context), "${cacheKey(url)}.bin")
    }

    /**
     * Gets marker image from cache if present and not expired.
     * @return decoded Bitmap or null if miss/expired/error
     */
    fun get(context: Context, url: String): Bitmap? = lock.read {
        val file = cacheFile(context, url)
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
     * @param imageBytes raw image bytes (e.g. from HTTP response body)
     */
    fun put(context: Context, url: String, imageBytes: ByteArray): Unit = lock.write {
        val file = cacheFile(context, url)
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
