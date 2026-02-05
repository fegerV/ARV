package ru.neuroimagen.arviewer.data.cache

import android.content.Context
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
        val file = cacheFile(context, uniqueId)
        if (!file.exists()) return null
        if (file.lastModified() + MAX_AGE_MS < System.currentTimeMillis()) {
            file.delete()
            return null
        }
        runCatching {
            gson.fromJson(file.readText(), ViewerManifest::class.java)
        }.getOrNull()
    }

    /**
     * Saves manifest to cache.
     */
    fun put(context: Context, uniqueId: String, manifest: ViewerManifest): Unit = lock.write {
        val file = cacheFile(context, uniqueId)
        runCatching {
            file.writeText(gson.toJson(manifest))
        }
    }

    /**
     * Clears all cached manifests.
     */
    fun clear(context: Context): Unit = lock.write {
        cacheDir(context).listFiles()?.forEach { it.delete() }
    }
}
