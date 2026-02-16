package ru.neuroimagen.arviewer.data.repository

import android.content.Context
import android.util.Log
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import retrofit2.HttpException
import ru.neuroimagen.arviewer.data.api.ViewerApi
import ru.neuroimagen.arviewer.data.cache.ManifestCache
import ru.neuroimagen.arviewer.data.model.ContentUnavailableReason
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.model.ViewerManifestVideo
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for viewer API: check content, load manifest, fetch next active video.
 *
 * Uses a **cache-first** strategy: if a cached manifest exists, it is returned
 * immediately while a background refresh updates the cache for next time.
 * This avoids a 2+ second network roundtrip (check + manifest + YD URL resolve)
 * on repeated opens of the same AR content, since the video and marker are
 * already in their own stable caches keyed by [ViewerManifest.uniqueId].
 */
@Singleton
class ViewerRepository @Inject constructor(
    private val api: ViewerApi,
    @ApplicationContext private val context: Context,
) {

    private val backgroundScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /**
     * Loads manifest with cache-first strategy:
     *
     * 1. If a cached manifest exists → return it **instantly** and refresh
     *    the cache in the background (stale-while-revalidate).
     * 2. If no cache → full network fetch (check + manifest).
     * 3. On network failure without cache → propagate error.
     *
     * @return Result with [ViewerManifest] on success, or [ViewerError] on failure.
     */
    suspend fun loadManifest(uniqueId: String): Result<ViewerManifest> {
        val trimmed = uniqueId.trim()
        if (trimmed.isBlank()) {
            return Result.failure(ViewerError.Unavailable(ContentUnavailableReason.INVALID_UNIQUE_ID))
        }

        val cached = ManifestCache.get(context, trimmed)
        if (cached != null) {
            Log.d(TAG, "Manifest cache HIT for $trimmed — returning instantly")
            backgroundScope.launch { refreshManifest(trimmed) }
            return Result.success(cached)
        }

        Log.d(TAG, "Manifest cache MISS for $trimmed — full network fetch")
        val networkResult = fetchManifestFromNetwork(trimmed)
        networkResult.getOrNull()?.let { manifest ->
            ManifestCache.put(context, trimmed, manifest)
            return Result.success(manifest)
        }
        return Result.failure(
            networkResult.exceptionOrNull() as? ViewerError
                ?: ViewerError.Network(msg = "Unknown error"),
        )
    }

    /**
     * Background refresh: fetches fresh manifest from network and updates cache.
     * Errors are silently logged — the user already has a working cached manifest.
     */
    private suspend fun refreshManifest(uniqueId: String) {
        val result = fetchManifestFromNetwork(uniqueId)
        result.getOrNull()?.let { manifest ->
            ManifestCache.put(context, uniqueId, manifest)
            Log.d(TAG, "Background manifest refresh OK for $uniqueId")
        } ?: run {
            Log.w(TAG, "Background manifest refresh failed for $uniqueId: ${result.exceptionOrNull()}")
        }
    }

    /**
     * Fetches manifest from API. Returns Result with proper error (Server/Unavailable/Network).
     */
    private suspend fun fetchManifestFromNetwork(uniqueId: String): Result<ViewerManifest> {
        return try {
            val checkResponse = api.checkContent(uniqueId)
            if (!checkResponse.isSuccessful) {
                return Result.failure(mapHttpToError(checkResponse.code(), checkResponse.message()))
            }
            val checkBody = checkResponse.body()
            if (checkBody == null || !checkBody.contentAvailable) {
                val reason = ContentUnavailableReason.fromApiValue(checkBody?.reason)
                return Result.failure(ViewerError.Unavailable(reason))
            }

            val manifestResponse = api.getManifest(uniqueId)
            if (!manifestResponse.isSuccessful) {
                return Result.failure(mapHttpToError(manifestResponse.code(), manifestResponse.message()))
            }
            val manifest = manifestResponse.body()
                ?: return Result.failure(ViewerError.Server(manifestResponse.code(), msg = "Empty manifest"))
            Result.success(manifest)
        } catch (e: HttpException) {
            Result.failure(mapHttpToError(e.code(), e.message()))
        } catch (e: IOException) {
            Result.failure(ViewerError.Network(msg = e.message ?: e.javaClass.simpleName))
        }
    }

    /**
     * Fetches the current/next active video for rotation (e.g. after current video ends).
     * Does not increment view count.
     */
    suspend fun getActiveVideo(uniqueId: String): Result<ViewerManifestVideo> {
        val trimmed = uniqueId.trim()
        if (trimmed.isBlank()) {
            return Result.failure(ViewerError.Unavailable(ContentUnavailableReason.INVALID_UNIQUE_ID))
        }

        return try {
            val response = api.getActiveVideo(trimmed)
            if (!response.isSuccessful) {
                return Result.failure(mapHttpToError(response.code(), response.message()))
            }
            val video = response.body()
                ?: return Result.failure(ViewerError.Server(response.code(), msg = "Empty active video"))
            Result.success(video)
        } catch (e: IOException) {
            Result.failure(ViewerError.Network(msg = e.message))
        } catch (e: HttpException) {
            Result.failure(mapHttpToError(e.code(), e.message()))
        }
    }

    private fun mapHttpToError(code: Int, message: String?): ViewerError {
        return when (code) {
            403 -> ViewerError.Unavailable(ContentUnavailableReason.SUBSCRIPTION_EXPIRED)
            404 -> ViewerError.Unavailable(ContentUnavailableReason.NOT_FOUND)
            400 -> ViewerError.Server(code, msg = message)
            else -> ViewerError.Server(code, msg = message)
        }
    }

    companion object {
        private const val TAG = "ViewerRepository"
    }
}
