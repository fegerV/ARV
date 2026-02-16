package ru.neuroimagen.arviewer

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.opengl.GLSurfaceView
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.util.Log
import android.view.MotionEvent
import android.view.PixelCopy
import android.view.ScaleGestureDetector
import android.view.Surface
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.annotation.OptIn
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.ProgressiveMediaSource
import com.google.ar.core.Session
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.ar.ArCoreCheckResult
import ru.neuroimagen.arviewer.ar.ArRenderer
import ru.neuroimagen.arviewer.ar.ArSessionHelper
import ru.neuroimagen.arviewer.ar.ArSessionResult
import ru.neuroimagen.arviewer.ar.RecordableEGLConfigChooser
import ru.neuroimagen.arviewer.data.cache.VideoCache
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import dagger.hilt.android.AndroidEntryPoint
import ru.neuroimagen.arviewer.ui.ArViewerViewModel
import ru.neuroimagen.arviewer.util.CrashReporter
import java.io.File
import java.io.FileInputStream
import java.io.OutputStream

/**
 * AR viewer scene: camera, ARCore Augmented Image, video overlay,
 * photo capture, and video recording (with optional microphone audio).
 *
 * Manifest parsing and marker bitmap loading are delegated to [ArViewerViewModel].
 * This activity manages the AR session, GL surface, ExoPlayer, and recording.
 *
 * Receives either [EXTRA_MANIFEST_JSON] (pre-loaded) or [EXTRA_UNIQUE_ID] (will load manifest).
 */
@AndroidEntryPoint
class ArViewerActivity : AppCompatActivity() {

    private val viewModel: ArViewerViewModel by viewModels()

    private var arSession: Session? = null
    private var exoPlayer: ExoPlayer? = null
    private var arRenderer: ArRenderer? = null
    private var recordButton: Button? = null
    private var currentZoom = 1.0f
    private var scaleDetector: ScaleGestureDetector? = null

    // ── Loading tips ─────────────────────────────────────────────────
    private var tipsHandler: Handler? = null
    private var tipsRunnable: Runnable? = null
    private var currentTipIndex = 0

    // ── Camera permission fallback ───────────────────────────────────

    /**
     * Fallback launcher in case the user revoked camera permission
     * between MainActivity and this activity.
     */
    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            tryStartArFromViewModelState()
        } else {
            Toast.makeText(this, R.string.error_camera_required, Toast.LENGTH_LONG).show()
            finish()
        }
    }

    // ── Lifecycle ────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_ar_viewer)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        startLoadingTipsCycle()
        observeUiState()

        viewModel.loadFromIntent(
            manifestJson = intent.getStringExtra(EXTRA_MANIFEST_JSON),
            uniqueId = intent.getStringExtra(EXTRA_UNIQUE_ID),
        )
    }

    override fun onResume() {
        super.onResume()
        arSession?.resume()
    }

    override fun onPause() {
        super.onPause()
        stopRecordingIfActive()
        arSession?.pause()
    }

    override fun onDestroy() {
        stopLoadingTipsCycle()
        stopRecordingIfActive()
        exoPlayer?.release()
        exoPlayer = null
        arSession?.close()
        arSession = null
        super.onDestroy()
    }

    override fun onSupportNavigateUp(): Boolean {
        onBackPressedDispatcher.onBackPressed()
        return true
    }

    // ── State observation ────────────────────────────────────────────

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    when (state) {
                        is ArViewerViewModel.UiState.Loading -> { /* tips are cycling */ }
                        is ArViewerViewModel.UiState.Ready -> onManifestAndBitmapReady(
                            state.manifest,
                            state.markerBitmap,
                        )
                        is ArViewerViewModel.UiState.MarkerLoadFailed -> {
                            Toast.makeText(this@ArViewerActivity, R.string.error_marker_not_available, Toast.LENGTH_LONG).show()
                            finish()
                        }
                        is ArViewerViewModel.UiState.ManifestLoadFailed -> {
                            Toast.makeText(this@ArViewerActivity, R.string.error_unknown, Toast.LENGTH_LONG).show()
                            finish()
                        }
                    }
                }
            }
        }
    }

    // ── Manifest + bitmap ready ──────────────────────────────────────

    /**
     * Called when ViewModel has both manifest and marker bitmap.
     * Checks camera permission before starting AR.
     */
    private fun onManifestAndBitmapReady(manifest: ViewerManifest, bitmap: Bitmap) {
        if (isDestroyed) return
        if (arSession != null) return // AR already started

        if (!hasPermission(Manifest.permission.CAMERA)) {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            return
        }
        startArWithPermission(manifest, bitmap)
    }

    /**
     * Re-read manifest/bitmap from ViewModel state after permission grant.
     */
    private fun tryStartArFromViewModelState() {
        val state = viewModel.uiState.value
        if (state is ArViewerViewModel.UiState.Ready) {
            startArWithPermission(state.manifest, state.markerBitmap)
        }
    }

    // ── Loading tips ─────────────────────────────────────────────────

    /**
     * Start cycling through AR tips on the loading screen.
     */
    private fun startLoadingTipsCycle() {
        val tipsArray = resources.getStringArray(R.array.ar_loading_tips)
        val tipTextView = findViewById<TextView>(R.id.text_loading_tip) ?: return
        if (tipsArray.isEmpty()) return

        currentTipIndex = 0
        tipTextView.text = tipsArray[0]

        val handler = Handler(Looper.getMainLooper())
        tipsHandler = handler
        val runnable = object : Runnable {
            override fun run() {
                currentTipIndex = (currentTipIndex + 1) % tipsArray.size
                tipTextView.animate()
                    .alpha(0f)
                    .setDuration(TIP_FADE_DURATION_MS)
                    .withEndAction {
                        tipTextView.text = tipsArray[currentTipIndex]
                        tipTextView.animate()
                            .alpha(1f)
                            .setDuration(TIP_FADE_DURATION_MS)
                            .start()
                    }
                    .start()
                handler.postDelayed(this, TIP_ROTATION_INTERVAL_MS)
            }
        }
        tipsRunnable = runnable
        handler.postDelayed(runnable, TIP_ROTATION_INTERVAL_MS)
    }

    private fun stopLoadingTipsCycle() {
        tipsRunnable?.let { tipsHandler?.removeCallbacks(it) }
        tipsHandler = null
        tipsRunnable = null
    }

    // ── AR scene setup ───────────────────────────────────────────────

    /**
     * Starts AR scene. Call only when camera permission is granted.
     *
     * Uses granular [ArCoreCheckResult] and [ArSessionResult] to provide
     * clear, device-specific error messages instead of generic Toasts.
     *
     * ARCore session creation (augmented image DB) is offloaded to
     * [Dispatchers.Default] so the main-thread Handler can keep cycling
     * loading tips while the heavy work runs in the background.
     */
    private fun startArWithPermission(manifest: ViewerManifest, bitmap: Bitmap) {
        if (isDestroyed) return

        // ── Step 1: Check & install ARCore (fast, needs Activity) ───
        when (val checkResult = ArSessionHelper.checkAndInstallArCore(this)) {
            is ArCoreCheckResult.Ready -> { /* proceed */ }

            is ArCoreCheckResult.DeviceNotSupported -> {
                showArError(getString(R.string.error_device_not_supported))
                return
            }
            is ArCoreCheckResult.InstallRequested -> {
                showArError(getString(R.string.error_arcore_install_requested))
                return
            }
            is ArCoreCheckResult.UserDeclinedInstall -> {
                showArError(getString(R.string.error_arcore_user_declined))
                return
            }
            is ArCoreCheckResult.SdkTooOld -> {
                showArError(getString(R.string.error_arcore_sdk_too_old))
                return
            }
            is ArCoreCheckResult.Unknown -> {
                showArError(getString(R.string.error_arcore_session))
                return
            }
        }

        if (isDestroyed) return

        // ── Step 2: Create session on background thread ─────────────
        // This keeps the main-thread message queue free so loading tips
        // continue to rotate while the augmented image DB is built.
        lifecycleScope.launch {
            val sessionResult = withContext(Dispatchers.Default) {
                ArSessionHelper.createSession(this@ArViewerActivity, bitmap, manifest)
            }

            if (isDestroyed) return@launch

            val session = when (sessionResult) {
                is ArSessionResult.Success -> sessionResult.session
                is ArSessionResult.DeviceNotCompatible -> {
                    showArError(getString(R.string.error_device_not_supported))
                    return@launch
                }
                is ArSessionResult.ArCoreNotInstalled -> {
                    showArError(getString(R.string.error_arcore_install_requested))
                    return@launch
                }
                is ArSessionResult.UserDeclined -> {
                    showArError(getString(R.string.error_arcore_user_declined))
                    return@launch
                }
                is ArSessionResult.SdkTooOld -> {
                    showArError(getString(R.string.error_arcore_sdk_too_old))
                    return@launch
                }
                is ArSessionResult.Failed -> {
                    showArError(getString(R.string.error_arcore_session))
                    return@launch
                }
            }

            arSession = session

            stopLoadingTipsCycle()

            setupArScene(session, manifest)
        }
    }

    /**
     * Initialise GL surface, renderer, and UI controls after a successful
     * ARCore session creation.  Must be called on the main thread.
     */
    private fun setupArScene(session: Session, manifest: ViewerManifest) {
        val renderer = ArRenderer(
            appContext = applicationContext,
            session = session,
            manifest = manifest,
            onVideoSurfaceReady = { surface -> prepareVideoPlayer(surface, manifest) },
            onMarkerTrackingChanged = { isTracking -> onMarkerTrackingChanged(isTracking) },
            getDisplayRotation = {
                @Suppress("DEPRECATION")
                windowManager.defaultDisplay.rotation
            },
        )
        arRenderer = renderer

        scaleDetector = ScaleGestureDetector(
            this,
            object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
                override fun onScale(detector: ScaleGestureDetector): Boolean {
                    currentZoom *= detector.scaleFactor
                    currentZoom = currentZoom.coerceIn(MIN_ZOOM, MAX_ZOOM)
                    arRenderer?.setZoomLevel(currentZoom)
                    return true
                }
            }
        )

        val root = layoutInflater.inflate(R.layout.activity_ar_viewer_gl, null)
        val glView = root.findViewById<GLSurfaceView>(R.id.ar_gl_surface).apply {
            setEGLContextClientVersion(2)
            setEGLConfigChooser(RecordableEGLConfigChooser())
            preserveEGLContextOnPause = true
            setRenderer(renderer)
            setOnTouchListener { _, event -> onGlSurfaceTouch(event) }
        }
        root.findViewById<Button>(R.id.button_capture_photo).setOnClickListener {
            capturePhoto(glView)
        }
        recordButton = root.findViewById<Button>(R.id.button_record_video).apply {
            setOnClickListener { toggleRecording() }
        }
        setContentView(root)
    }

    // ── Photo capture ────────────────────────────────────────────────

    private fun capturePhoto(glView: GLSurfaceView) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
            return
        }
        val bitmap = Bitmap.createBitmap(glView.width, glView.height, Bitmap.Config.ARGB_8888)
        PixelCopy.request(glView, bitmap, { result ->
            runOnUiThread {
                if (result == PixelCopy.SUCCESS) {
                    if (saveBitmapToMediaStore(bitmap)) {
                        Toast.makeText(this, R.string.photo_saved, Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
                    }
                } else {
                    Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
                }
                bitmap.recycle()
            }
        }, Handler(Looper.getMainLooper()))
    }

    /**
     * Save bitmap to device gallery via MediaStore.
     */
    private fun saveBitmapToMediaStore(bitmap: Bitmap): Boolean {
        return try {
            val filename = "AR_${System.currentTimeMillis()}.jpg"
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/AR Viewer")
                }
            }
            val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                contentResolver.insert(
                    MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                    contentValues
                )
            } else {
                @Suppress("DEPRECATION")
                contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
            } ?: return false
            contentResolver.openOutputStream(uri)?.use { out: OutputStream ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
            }
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save photo to MediaStore", e)
            false
        }
    }

    // ── Video recording ──────────────────────────────────────────────

    /**
     * Toggle recording on/off. Uses microphone audio if permission was granted.
     */
    private fun toggleRecording() {
        val renderer = arRenderer ?: return
        if (renderer.isRecording) {
            stopRecordingIfActive()
        } else {
            val enableAudio = hasPermission(Manifest.permission.RECORD_AUDIO)
            doStartRecording(renderer, enableAudio)
        }
    }

    private fun doStartRecording(renderer: ArRenderer, enableAudio: Boolean) {
        val tempFile = File(cacheDir, "ar_record_${System.currentTimeMillis()}.mp4")
        recordButton?.text = getString(R.string.stop_recording)
        renderer.startRecording(tempFile, enableAudio) { outputPath ->
            recordButton?.text = getString(R.string.record_video)
            if (outputPath != null) {
                saveVideoToGallery(File(outputPath))
            } else {
                Toast.makeText(this, R.string.video_save_failed, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun stopRecordingIfActive() {
        val renderer = arRenderer ?: return
        if (renderer.isRecording) {
            renderer.stopRecording()
        }
    }

    /**
     * Copy the recorded MP4 from cache to the device gallery via MediaStore.
     */
    private fun saveVideoToGallery(sourceFile: File) {
        lifecycleScope.launch {
            val saved = withContext(Dispatchers.IO) {
                try {
                    val filename = "AR_${System.currentTimeMillis()}.mp4"
                    val contentValues = ContentValues().apply {
                        put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                        put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/AR Viewer")
                            put(MediaStore.Video.Media.IS_PENDING, 1)
                        }
                    }
                    val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        contentResolver.insert(
                            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                            contentValues
                        )
                    } else {
                        @Suppress("DEPRECATION")
                        contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, contentValues)
                    } ?: return@withContext false

                    contentResolver.openOutputStream(uri)?.use { out ->
                        FileInputStream(sourceFile).use { input ->
                            input.copyTo(out, bufferSize = 8192)
                        }
                    }

                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        val update = ContentValues().apply {
                            put(MediaStore.Video.Media.IS_PENDING, 0)
                        }
                        contentResolver.update(uri, update, null, null)
                    }
                    sourceFile.delete()
                    true
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to save video to gallery", e)
                    false
                }
            }
            if (saved) {
                Toast.makeText(this@ArViewerActivity, R.string.video_saved, Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this@ArViewerActivity, R.string.video_save_failed, Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ── Video player ─────────────────────────────────────────────────

    /**
     * Prepare Media3 player but do NOT start playback.
     * Video will begin playing when the marker is first recognized.
     */
    @OptIn(UnstableApi::class)
    private fun prepareVideoPlayer(surface: Surface, manifest: ViewerManifest) {
        exoPlayer?.release()
        val player = ExoPlayer.Builder(this).build()
        exoPlayer = player

        player.repeatMode = Player.REPEAT_MODE_ALL
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                val stateName = when (playbackState) {
                    Player.STATE_IDLE -> "IDLE"
                    Player.STATE_BUFFERING -> "BUFFERING"
                    Player.STATE_READY -> "READY"
                    Player.STATE_ENDED -> "ENDED"
                    else -> "UNKNOWN($playbackState)"
                }
                Log.d(TAG, "Media3 player state: $stateName")
            }

            override fun onPlayerError(error: PlaybackException) {
                Log.e(TAG, "Media3 player error: ${error.errorCodeName}", error)
                CrashReporter.log("Media3 player error: ${error.errorCodeName}")
                CrashReporter.recordException(error)
                runOnUiThread {
                    Toast.makeText(
                        this@ArViewerActivity,
                        getString(R.string.error_video_playback, error.errorCodeName),
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        })

        val cacheFactory = VideoCache.getDataSourceFactory(this)
        val mediaSource = ProgressiveMediaSource.Factory(cacheFactory)
            .createMediaSource(MediaItem.fromUri(manifest.video.videoUrl))
        player.setMediaSource(mediaSource)
        player.setVideoSurface(surface)
        player.volume = 0f
        player.prepare()
        player.playWhenReady = false
        Log.d(TAG, "Video player prepared (muted, paused, waiting for marker)")
    }

    /**
     * Called from ArRenderer when marker tracking starts or stops.
     * Plays and unmutes video when marker is visible; immediately mutes and pauses when lost.
     */
    private fun onMarkerTrackingChanged(isTracking: Boolean) {
        val player = exoPlayer ?: return
        if (isTracking) {
            player.volume = 1f
            player.playWhenReady = true
            Log.d(TAG, "Marker tracked — video playing, unmuted")
        } else {
            player.volume = 0f
            player.playWhenReady = false
            Log.d(TAG, "Marker lost — video muted + paused")
        }
    }

    // ── Utilities ────────────────────────────────────────────────────

    private fun hasPermission(permission: String): Boolean =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    @Suppress("ClickableViewAccessibility")
    private fun onGlSurfaceTouch(event: MotionEvent): Boolean {
        scaleDetector?.onTouchEvent(event)
        return true
    }

    // ── Error UI ───────────────────────────────────────────────────

    /**
     * Show a full-screen error message with a "Back" button instead of
     * a transient Toast.  The user can read the message at their own pace.
     */
    private fun showArError(message: String) {
        CrashReporter.log("AR error displayed: $message")
        stopLoadingTipsCycle()
        val errorView = layoutInflater.inflate(R.layout.layout_ar_error, null)
        errorView.findViewById<TextView>(R.id.text_ar_error).text = message
        errorView.findViewById<Button>(R.id.button_ar_error_back).setOnClickListener { finish() }
        setContentView(errorView)
    }

    companion object {
        private const val TAG = "ArViewerActivity"
        const val EXTRA_MANIFEST_JSON = "manifest_json"
        const val EXTRA_UNIQUE_ID = "unique_id"
        private const val MIN_ZOOM = 1.0f
        private const val MAX_ZOOM = 5.0f
        private const val TIP_ROTATION_INTERVAL_MS = 3_000L
        private const val TIP_FADE_DURATION_MS = 300L
    }
}
