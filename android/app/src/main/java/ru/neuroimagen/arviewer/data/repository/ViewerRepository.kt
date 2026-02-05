package ru.neuroimagen.arviewer.data.repository

import retrofit2.HttpException
import ru.neuroimagen.arviewer.data.api.ViewerApi
import ru.neuroimagen.arviewer.data.model.ContentUnavailableReason
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.model.ViewerManifestVideo
import java.io.IOException

/**
 * Repository for viewer API: check content, load manifest, fetch next active video.
 * Maps HTTP and check responses to domain errors.
 */
class ViewerRepository(private val api: ViewerApi) {

    /**
     * Checks if content is available, then fetches manifest.
     * @return Result with [ViewerManifest] on success, or [ViewerError] on failure.
     */
    suspend fun loadManifest(uniqueId: String): Result<ViewerManifest> {
        val trimmed = uniqueId.trim()
        if (trimmed.isBlank()) {
            return Result.failure(ViewerError.Unavailable(ContentUnavailableReason.INVALID_UNIQUE_ID))
        }

        return try {
            val checkResponse = api.checkContent(trimmed)
            if (!checkResponse.isSuccessful) {
                return Result.failure(mapHttpToError(checkResponse.code(), checkResponse.message()))
            }
            val checkBody = checkResponse.body()
            if (checkBody == null || !checkBody.contentAvailable) {
                val reason = ContentUnavailableReason.fromApiValue(checkBody?.reason)
                return Result.failure(ViewerError.Unavailable(reason))
            }

            val manifestResponse = api.getManifest(trimmed)
            if (!manifestResponse.isSuccessful) {
                return Result.failure(mapHttpToError(manifestResponse.code(), manifestResponse.message()))
            }
            val manifest = manifestResponse.body()
                ?: return Result.failure(ViewerError.Server(manifestResponse.code(), msg = "Empty manifest"))
            Result.success(manifest)
        } catch (e: IOException) {
            Result.failure(ViewerError.Network(msg = e.message))
        } catch (e: HttpException) {
            Result.failure(mapHttpToError(e.code(), e.message()))
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
}
