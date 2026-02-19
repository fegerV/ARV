package ru.neuroimagen.arviewer.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.repository.ViewerRepository
import ru.neuroimagen.arviewer.util.CrashReporter
import javax.inject.Inject

/**
 * ViewModel for [ru.neuroimagen.arviewer.MainActivity].
 *
 * Manages manifest loading, UI state transitions, and retry logic.
 * QR scanning and permission handling remain in the Activity.
 */
@HiltViewModel
class MainViewModel @Inject constructor(
    private val repository: ViewerRepository,
    private val gson: Gson,
) : ViewModel() {

    /** Screen states for the main activity. */
    sealed interface UiState {
        /** Default input state — user can enter unique_id or scan QR. */
        data object Input : UiState

        /** Loading manifest from the API. */
        data object Loading : UiState

        /** An error occurred; the user may retry if [retryable] is true. */
        data class Error(
            val viewerError: ViewerError?,
            val throwable: Throwable,
            val retryable: Boolean,
        ) : UiState

        /** Manifest loaded successfully — navigate to AR viewer. */
        data class NavigateToAr(
            val manifestJson: String,
            val uniqueId: String,
        ) : UiState
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Input)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    /** Last unique_id that was attempted — used for retry. */
    var lastAttemptedUniqueId: String? = null
        private set

    /**
     * Load manifest for the given [uniqueId].
     *
     * @param forceRefresh if true, skip cache and fetch from network (use when user just scanned a new QR).
     * Transitions state: Input → Loading → NavigateToAr | Error.
     */
    fun loadManifest(uniqueId: String, forceRefresh: Boolean = false) {
        lastAttemptedUniqueId = uniqueId
        _uiState.value = UiState.Loading

        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                repository.loadManifest(uniqueId, forceRefresh)
            }
            result.fold(
                onSuccess = { manifest ->
                    _uiState.value = UiState.NavigateToAr(
                        manifestJson = gson.toJson(manifest),
                        uniqueId = uniqueId,
                    )
                },
                onFailure = { throwable ->
                    CrashReporter.log("loadManifest failed for id=$uniqueId")
                    CrashReporter.recordException(throwable)
                    val viewerError = throwable as? ViewerError
                    val retryable = viewerError
                        ?.let { ViewerErrorMessages.isRetryable(it) }
                        ?: true
                    _uiState.value = UiState.Error(
                        viewerError = viewerError,
                        throwable = throwable,
                        retryable = retryable,
                    )
                },
            )
        }
    }

    /** Show loading indicator (e.g. while decoding QR from gallery image). */
    fun setLoading() {
        _uiState.value = UiState.Loading
    }

    /** Return to the default input screen. */
    fun resetToInput() {
        _uiState.value = UiState.Input
    }

    /** Retry the last manifest load. Returns to Input if nothing to retry. */
    fun retry() {
        val id = lastAttemptedUniqueId
        if (!id.isNullOrBlank()) {
            loadManifest(id)
        } else {
            resetToInput()
        }
    }

    /** Call after successfully navigating to AR viewer to reset state. */
    fun onNavigated() {
        _uiState.value = UiState.Input
    }
}
