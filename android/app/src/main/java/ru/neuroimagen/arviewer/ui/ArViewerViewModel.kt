package ru.neuroimagen.arviewer.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.BuildConfig
import ru.neuroimagen.arviewer.data.api.AnalyticsApi
import ru.neuroimagen.arviewer.data.api.ViewerApi
import ru.neuroimagen.arviewer.data.cache.MarkerCache
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.repository.ViewerRepository
import ru.neuroimagen.arviewer.util.CrashReporter
import javax.inject.Inject
import kotlin.math.max

/**
 * ViewModel for [ru.neuroimagen.arviewer.ArViewerActivity].
 *
 * Manages manifest parsing/loading and marker bitmap retrieval.
 * AR session, ExoPlayer, and recording remain in the Activity.
 */
@HiltViewModel
class ArViewerViewModel @Inject constructor(
    @ApplicationContext private val appContext: Context,
    private val viewerRepository: ViewerRepository,
    private val viewerApi: ViewerApi,
    private val analyticsApi: AnalyticsApi,
    private val gson: Gson,
) : ViewModel() {

    /** Screen states for the AR viewer. */
    sealed interface UiState {
        /** Manifest and marker bitmap are loading. */
        data object Loading : UiState

        /** Manifest and marker bitmap are ready for AR setup. */
        data class Ready(
            val manifest: ViewerManifest,
            val markerBitmap: Bitmap,
        ) : UiState

        /** Marker image could not be loaded. */
        data object MarkerLoadFailed : UiState

        /** Manifest could not be parsed or loaded. */
        data object ManifestLoadFailed : UiState
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    /**
     * Initialize from intent extras.
     *
     * @param manifestJson pre-loaded manifest JSON (from MainActivity), or null
     * @param uniqueId     unique content ID (fallback if JSON is null)
     */
    fun loadFromIntent(manifestJson: String?, uniqueId: String?) {
        if (_uiState.value !is UiState.Loading) return

        when {
            !manifestJson.isNullOrBlank() -> {
                try {
                    val manifest = gson.fromJson(manifestJson, ViewerManifest::class.java)
                    loadMarkerBitmap(manifest)
                } catch (e: Exception) {
                    CrashReporter.log("Failed to parse manifest JSON")
                    CrashReporter.recordException(e)
                    _uiState.value = UiState.ManifestLoadFailed
                }
            }
            !uniqueId.isNullOrBlank() -> loadManifestFromNetwork(uniqueId)
            else -> _uiState.value = UiState.ManifestLoadFailed
        }
    }

    private fun loadManifestFromNetwork(uniqueId: String) {
        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                viewerRepository.loadManifest(uniqueId)
            }
            result.fold(
                onSuccess = { manifest -> loadMarkerBitmap(manifest) },
                onFailure = { throwable ->
                    CrashReporter.log("loadManifestFromNetwork failed for id=$uniqueId")
                    CrashReporter.recordException(throwable)
                    _uiState.value = UiState.ManifestLoadFailed
                },
            )
        }
    }

    private fun loadMarkerBitmap(manifest: ViewerManifest) {
        viewModelScope.launch {
            val bitmap = withContext(Dispatchers.IO) {
                fetchBitmap(manifest.uniqueId, manifest.markerImageUrl)
            }
            _uiState.value = if (bitmap != null) {
                UiState.Ready(manifest, bitmap)
            } else {
                UiState.MarkerLoadFailed
            }
        }
    }

    /**
     * Load marker bitmap from cache or network.
     *
     * Cache is keyed by [uniqueId] (stable) rather than [url] (temporary for
     * Yandex Disk content), so repeated opens hit the cache instead of
     * re-downloading the full image every time.
     *
     * The bitmap is scaled down to [ARCORE_MAX_IMAGE_DIMENSION] before
     * returning.  ARCore's [AugmentedImageDatabase.addImage] performs feature
     * extraction whose cost grows with pixel count; a 3000×2000 image takes
     * 2–3 s, while 1024×682 takes ≈300 ms — the main reason second opens
     * felt as slow as the first.
     */
    private suspend fun fetchBitmap(uniqueId: String, url: String): Bitmap? {
        val absoluteUrl = absoluteMarkerUrl(url)

        val raw = MarkerCache.get(appContext, uniqueId)
            ?: run {
                val response = viewerApi.downloadImage(absoluteUrl)
                if (!response.isSuccessful) return null
                val bytes = response.body()?.bytes() ?: return null
                MarkerCache.put(appContext, uniqueId, bytes)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            }

        return scaleForArCore(raw)
    }

    /**
     * Scales [bitmap] so that its longest side does not exceed [maxDimension].
     *
     * ARCore recommends marker images of at least 300 px; anything above
     * ≈1024 px yields no tracking quality gain but makes
     * [AugmentedImageDatabase.addImage] significantly slower.
     *
     * Returns the original bitmap unchanged if it is already within limits.
     * Otherwise returns a new scaled bitmap and recycles the original.
     */
    private fun scaleForArCore(
        bitmap: Bitmap,
        maxDimension: Int = ARCORE_MAX_IMAGE_DIMENSION,
    ): Bitmap {
        val width = bitmap.width
        val height = bitmap.height
        val longestSide = max(width, height)
        if (longestSide <= maxDimension) return bitmap

        val scale = maxDimension.toFloat() / longestSide
        val newWidth = (width * scale).toInt().coerceAtLeast(1)
        val newHeight = (height * scale).toInt().coerceAtLeast(1)

        Log.d(TAG, "Scaling marker bitmap ${width}×${height} → ${newWidth}×${newHeight}")

        val scaled = Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
        if (scaled !== bitmap) bitmap.recycle()
        return scaled
    }

    private fun absoluteMarkerUrl(url: String): String {
        val trimmed = url.trim()
        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed
        val base = BuildConfig.API_BASE_URL.trimEnd('/')
        return if (trimmed.startsWith("/")) "$base$trimmed" else "$base/$trimmed"
    }

    companion object {
        private const val TAG = "ArViewerViewModel"

        /**
         * Maximum marker image dimension (in pixels) for ARCore.
         * 1024 px is more than enough for reliable tracking and keeps
         * [AugmentedImageDatabase.addImage] under 500 ms on most devices.
         */
        private const val ARCORE_MAX_IMAGE_DIMENSION = 1024
    }
}
