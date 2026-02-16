package ru.neuroimagen.arviewer.data.cache

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import java.io.File
import java.util.concurrent.locks.ReentrantReadWriteLock
import kotlin.concurrent.read
import kotlin.concurrent.write

/**
 * Disk cache for viewer manifests. Enables offline playback after first successful load.
 * Cached by unique_id; entries expire after [MAX_AGE_MS].
 */
object ManifestCache {

    private const val TAG = "ManifestCache"
    private const val CACHE_DIR_NAME = "manifest_cache"
    private const val MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000L // 7 days

    private val gson = Gson()
    private val lock = ReentrantReadWriteLock()

    private fun cacheDir(context: Context): File {
        return File(context.cacheDir, CACHE_DIR_NAME).also {
            if (!it.exists()) it.mkdirs()
        }
    }

    /** Safe filename: UUID is already safe; otherwise use hash. */
    private fun cacheFile(context: Context, uniqueId: String): File {
        val safeName = uniqueId.replace(Regex("[^a-zA-Z0-9_-]"), "_").take(64)
        return File(cacheDir(context), "$safeName.json")
    }

    /**
     * Returns cached manifest if present and not expired.
     */
    fun get(context: Context, uniqueId: String): ViewerManifest? = lock.read {
        val start = System.currentTimeMillis()
        val file = cacheFile(context, uniqueId)
        if (!file.exists()) {
            Log.d(TAG, "MISS — file not found for $uniqueId (${file.absolutePath})")
            return null
        }
        val ageMs = System.currentTimeMillis() - file.lastModified()
        if (ageMs > MAX_AGE_MS) {
            Log.d(TAG, "MISS — expired (age=${ageMs / 1000}s) for $uniqueId")
            file.delete()
            return null
        }
        val result = runCatching {
            gson.fromJson(file.readText(), ViewerManifest::class.java)
        }
        val elapsed = System.currentTimeMillis() - start
        result.onFailure { e ->
            Log.e(TAG, "MISS — deserialization failed for $uniqueId in ${elapsed}ms", e)
        }
        result.onSuccess {
            Log.d(TAG, "HIT for $uniqueId in ${elapsed}ms (age=${ageMs / 1000}s)")
        }
        result.getOrNull()
    }

    /**
     * Saves manifest to cache.
     */
    fun put(context: Context, uniqueId: String, manifest: ViewerManifest): Unit = lock.write {
        val file = cacheFile(context, uniqueId)
        val result = runCatching {
            file.writeText(gson.toJson(manifest))
        }
        result.onSuccess {
            Log.d(TAG, "PUT OK for $uniqueId (${file.length()} bytes)")
        }
        result.onFailure { e ->
            Log.e(TAG, "PUT FAILED for $uniqueId", e)
        }
    }

    /**
     * Clears all cached manifests.
     */
    fun clear(context: Context): Unit = lock.write {
        cacheDir(context).listFiles()?.forEach { it.delete() }
    }
}
