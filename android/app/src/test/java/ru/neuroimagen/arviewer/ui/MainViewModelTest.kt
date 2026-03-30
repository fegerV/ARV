package ru.neuroimagen.arviewer.ui

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.model.ViewerManifestVideo
import ru.neuroimagen.arviewer.data.repository.ManifestLoader
import ru.neuroimagen.arviewer.util.CrashLogger

@OptIn(ExperimentalCoroutinesApi::class)
class MainViewModelTest {

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `loadManifest navigates on success and stores last attempted id`() = runTest {
        val manifest = sampleManifest(uniqueId = "abc-123")
        val loader = FakeManifestLoader { uniqueId, forceRefresh ->
            assertEquals("abc-123", uniqueId)
            assertFalse(forceRefresh)
            Result.success(manifest)
        }
        val crashLogger = FakeCrashLogger()
        val viewModel = MainViewModel(loader, Gson(), crashLogger, dispatcher)

        viewModel.loadManifest("abc-123")

        assertTrue(viewModel.uiState.value is MainViewModel.UiState.Loading)
        advanceUntilIdle()

        val state = viewModel.uiState.value as MainViewModel.UiState.NavigateToAr
        assertEquals("abc-123", state.uniqueId)
        assertTrue(state.manifestJson.contains("\"unique_id\":\"abc-123\""))
        assertEquals("abc-123", viewModel.lastAttemptedUniqueId)
        assertTrue(crashLogger.loggedMessages.isEmpty())
    }

    @Test
    fun `loadManifest exposes non-retryable error and reports crash`() = runTest {
        val loader = FakeManifestLoader { _, _ ->
            Result.failure(ViewerError.DeviceNotSupported)
        }
        val crashLogger = FakeCrashLogger()
        val viewModel = MainViewModel(loader, Gson(), crashLogger, dispatcher)

        viewModel.loadManifest("device-check", forceRefresh = true)
        advanceUntilIdle()

        val state = viewModel.uiState.value as MainViewModel.UiState.Error
        assertEquals(ViewerError.DeviceNotSupported, state.viewerError)
        assertFalse(state.retryable)
        assertEquals(1, crashLogger.loggedMessages.size)
        assertEquals(1, crashLogger.recordedExceptions.size)
        assertEquals("device-check", viewModel.lastAttemptedUniqueId)
        assertEquals(listOf("device-check:true"), loader.calls)
    }

    @Test
    fun `retry reloads last attempted id and reset helpers return to input`() = runTest {
        var attempts = 0
        val loader = FakeManifestLoader { _, _ ->
            attempts += 1
            if (attempts == 1) {
                Result.failure(ViewerError.Network("offline"))
            } else {
                Result.success(sampleManifest(uniqueId = "retry-id"))
            }
        }
        val viewModel = MainViewModel(loader, Gson(), FakeCrashLogger(), dispatcher)

        viewModel.loadManifest("retry-id")
        advanceUntilIdle()
        assertTrue(viewModel.uiState.value is MainViewModel.UiState.Error)

        viewModel.retry()
        advanceUntilIdle()

        assertTrue(viewModel.uiState.value is MainViewModel.UiState.NavigateToAr)
        assertEquals(listOf("retry-id:false", "retry-id:false"), loader.calls)

        viewModel.onNavigated()
        assertTrue(viewModel.uiState.value is MainViewModel.UiState.Input)

        viewModel.setLoading()
        assertTrue(viewModel.uiState.value is MainViewModel.UiState.Loading)

        viewModel.resetToInput()
        assertTrue(viewModel.uiState.value is MainViewModel.UiState.Input)
    }

    @Test
    fun `retry without previous id resets to input`() = runTest {
        val viewModel = MainViewModel(
            FakeManifestLoader { _, _ -> Result.success(sampleManifest()) },
            Gson(),
            FakeCrashLogger(),
            dispatcher,
        )

        viewModel.setLoading()
        viewModel.retry()

        assertTrue(viewModel.uiState.value is MainViewModel.UiState.Input)
    }

    private fun sampleManifest(uniqueId: String = "demo-id") = ViewerManifest(
        manifestVersion = "1.0",
        uniqueId = uniqueId,
        orderNumber = "42",
        markerImageUrl = "https://example.com/marker.jpg",
        photoUrl = "https://example.com/photo.jpg",
        video = ViewerManifestVideo(
            id = 7,
            title = "Demo",
            videoUrl = "https://example.com/video.mp4",
        ),
        expiresAt = "2099-01-01T00:00:00Z",
        status = "active",
    )

    private class FakeManifestLoader(
        private val block: suspend (String, Boolean) -> Result<ViewerManifest>,
    ) : ManifestLoader {
        val calls = mutableListOf<String>()

        override suspend fun loadManifest(uniqueId: String, forceRefresh: Boolean): Result<ViewerManifest> {
            calls += "$uniqueId:$forceRefresh"
            return block(uniqueId, forceRefresh)
        }
    }

    private class FakeCrashLogger : CrashLogger {
        val loggedMessages = mutableListOf<String>()
        val recordedExceptions = mutableListOf<Throwable>()

        override fun log(message: String) {
            loggedMessages += message
        }

        override fun recordException(throwable: Throwable) {
            recordedExceptions += throwable
        }
    }
}
