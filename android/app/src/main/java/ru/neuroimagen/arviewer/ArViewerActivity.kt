package ru.neuroimagen.arviewer

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
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
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.PlaybackException
import com.google.android.exoplayer2.Player
import com.google.android.exoplayer2.source.ProgressiveMediaSource
import com.google.ar.core.Session
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.ar.ArCoreCheckResult
import ru.neuroimagen.arviewer.ar.ArRenderer
import ru.neuroimagen.arviewer.ar.ArSessionHelper
import ru.neuroimagen.arviewer.ar.ArSessionResult
import ru.neuroimagen.arviewer.ar.RecordableEGLConfigChooser
import ru.neuroimagen.arviewer.data.api.ApiProvider
import ru.neuroimagen.arviewer.data.cache.MarkerCache
import ru.neuroimagen.arviewer.data.cache.VideoCache
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import java.io.File
import java.io.FileInputStream
import java.io.OutputStream

/**
 * AR viewer scene: camera, ARCore Augmented Image, video overlay,
 * photo capture, and video recording (with optional microphone audio).
 *
 * Permissions (camera, microphone) are requested upfront in [MainActivity].
 * This activity only checks them as a fallback.
 *
 * Receives either [EXTRA_MANIFEST_JSON] (pre-loaded) or [EXTRA_UNIQUE_ID] (will load manifest).
 */
class ArViewerActivity : AppCompatActivity() {

    private val gson = Gson()
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
            pendingManifest?.let { manifest ->
                pendingBitmap?.let { bitmap ->
                    startArWithPermission(manifest, bitmap)
                }
            }
        } else {
            Toast.makeText(this, R.string.error_camera_required, Toast.LENGTH_LONG).show()
            finish()
        }
        pendingManifest = null
        pendingBitmap = null
    }

    private var pendingManifest: ViewerManifest? = null
    private var pendingBitmap: Bitmap? = null

    // ── Lifecycle ────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_ar_viewer)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        startLoadingTipsCycle()

        val manifestJson = intent.getStringExtra(EXTRA_MANIFEST_JSON)
        val uniqueId = intent.getStringExtra(EXTRA_UNIQUE_ID)

        when {
            !manifestJson.isNullOrBlank() -> {
                try {
                    val manifest = gson.fromJson(manifestJson, ViewerManifest::class.java)
                    onManifestReady(manifest)
                } catch (e: Exception) {
                    finish()
                }
            }
            !uniqueId.isNullOrBlank() -> loadManifestAndStart(uniqueId)
            else -> finish()
        }
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

    // ── Manifest loading ─────────────────────────────────────────────

    private fun onManifestReady(manifest: ViewerManifest) {
        lifecycleScope.launch {
            if (isDestroyed) return@launch
            val bitmap = withContext(Dispatchers.IO) {
                loadMarkerBitmap(manifest.markerImageUrl)
            }
            if (isDestroyed) return@launch
            if (bitmap == null) {
                Toast.makeText(this@ArViewerActivity, R.string.error_marker_not_available, Toast.LENGTH_LONG).show()
                finish()
                return@launch
            }
            withContext(Dispatchers.Main) {
                if (isDestroyed) return@withContext
                if (!hasPermission(Manifest.permission.CAMERA)) {
                    pendingManifest = manifest
                    pendingBitmap = bitmap
                    cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                    return@withContext
                }
                startArWithPermission(manifest, bitmap)
            }
        }
    }

    // ── AR scene setup ───────────────────────────────────────────────

    /**
     * Starts AR scene. Call only when camera permission is granted.
     *
     * Uses granular [ArCoreCheckResult] and [ArSessionResult] to provide
     * clear, device-specific error messages instead of generic Toasts.
     */
    private fun startArWithPermission(manifest: ViewerManifest, bitmap: Bitmap) {
        if (isDestroyed) return

        // ── Step 1: Check & install ARCore ──────────────────────────
        when (val checkResult = ArSessionHelper.checkAndInstallArCore(this)) {
            is ArCoreCheckResult.Ready -> { /* proceed */ }

            is ArCoreCheckResult.DeviceNotSupported -> {
                showArError(getString(R.string.error_device_not_supported))
                return
            }
            is ArCoreCheckResult.InstallRequested -> {
                // Play Store install dialog was shown; activity will resume later.
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

        // ── Step 2: Create ARCore session ───────────────────────────
        val session = when (val sessionResult = ArSessionHelper.createSession(this, bitmap, manifest)) {
            is ArSessionResult.Success -> sessionResult.session
            is ArSessionResult.DeviceNotCompatible -> {
                showArError(getString(R.string.error_device_not_supported))
                return
            }
            is ArSessionResult.ArCoreNotInstalled -> {
                showArError(getString(R.string.error_arcore_install_requested))
                return
            }
            is ArSessionResult.UserDeclined -> {
                showArError(getString(R.string.error_arcore_user_declined))
                return
            }
            is ArSessionResult.SdkTooOld -> {
                showArError(getString(R.string.error_arcore_sdk_too_old))
                return
            }
            is ArSessionResult.Failed -> {
                showArError(getString(R.string.error_arcore_session))
                return
            }
        }

        if (isDestroyed) return
        arSession = session

        stopLoadingTipsCycle()

        val renderer = ArRenderer(
            this,
            session,
            manifest,
            onVideoSurfaceReady = { surface -> prepareVideoPlayer(surface, manifest) },
            onMarkerTrackingChanged = { isTracking -> onMarkerTrackingChanged(isTracking) }
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
     * Prepare ExoPlayer but do NOT start playback.
     * Video will begin playing when the marker is first recognized.
     */
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
                Log.d(TAG, "ExoPlayer state: $stateName")
            }

            override fun onPlayerError(error: PlaybackException) {
                Log.e(TAG, "ExoPlayer error: ${error.errorCodeName}", error)
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

    private fun absoluteMarkerUrl(url: String): String {
        val trimmed = url.trim()
        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed
        val base = BuildConfig.API_BASE_URL.trimEnd('/')
        return if (trimmed.startsWith("/")) "$base$trimmed" else "$base/$trimmed"
    }

    private suspend fun loadMarkerBitmap(url: String): Bitmap? = withContext(Dispatchers.IO) {
        val absoluteUrl = absoluteMarkerUrl(url)
        MarkerCache.get(this@ArViewerActivity, absoluteUrl)
            ?: run {
                val response = ApiProvider.viewerApi.downloadImage(absoluteUrl)
                if (!response.isSuccessful) return@withContext null
                val bytes = response.body()?.bytes() ?: return@withContext null
                MarkerCache.put(this@ArViewerActivity, absoluteUrl, bytes)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            }
    }

    private fun loadManifestAndStart(uniqueId: String) {
        val repository = ApiProvider.viewerRepository
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) { repository.loadManifest(uniqueId) }
            result.fold(
                onSuccess = { onManifestReady(it) },
                onFailure = {
                    Toast.makeText(this@ArViewerActivity, R.string.error_unknown, Toast.LENGTH_LONG).show()
                    finish()
                }
            )
        }
    }

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
