package ru.neuroimagen.arviewer

import android.Manifest
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
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
import ru.neuroimagen.arviewer.ar.ArRenderer
import ru.neuroimagen.arviewer.ar.ArSessionHelper
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
 * photo capture, video recording (with optional audio), and sharing.
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

    // ── Sharing state ────────────────────────────────────────────────
    private var lastSavedMediaUri: Uri? = null
    private var lastSavedMimeType: String? = null

    // ── Loading tips ─────────────────────────────────────────────────
    private var tipsHandler: Handler? = null
    private var tipsRunnable: Runnable? = null
    private var currentTipIndex = 0

    // ── Permission launchers ─────────────────────────────────────────

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

    /**
     * Microphone permission result: start recording with or without audio.
     */
    private val micPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        val renderer = arRenderer ?: return@registerForActivityResult
        if (!granted) {
            Toast.makeText(this, R.string.error_microphone_required, Toast.LENGTH_SHORT).show()
        }
        doStartRecording(renderer, enableAudio = granted)
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

    /**
     * Stop the tips cycle (called when AR scene is ready or activity is destroyed).
     */
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
                if (ContextCompat.checkSelfPermission(this@ArViewerActivity, Manifest.permission.CAMERA)
                    != PackageManager.PERMISSION_GRANTED
                ) {
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
     */
    private fun startArWithPermission(manifest: ViewerManifest, bitmap: Bitmap) {
        if (isDestroyed) return
        if (!ArSessionHelper.checkAndInstallArCore(this)) {
            Toast.makeText(this, R.string.error_arcore_required, Toast.LENGTH_LONG).show()
            finish()
            return
        }
        if (isDestroyed) return
        val session = ArSessionHelper.createSession(this, bitmap, manifest)
        if (session == null) {
            Toast.makeText(this, R.string.error_arcore_session, Toast.LENGTH_LONG).show()
            finish()
            return
        }
        if (isDestroyed) return
        arSession = session

        // Stop loading tips — AR scene is ready
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
        root.findViewById<Button>(R.id.button_share).setOnClickListener {
            onShareButtonClicked()
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
                    val uri = saveBitmapToMediaStore(bitmap)
                    if (uri != null) {
                        lastSavedMediaUri = uri
                        lastSavedMimeType = MIME_TYPE_JPEG
                        Toast.makeText(this, R.string.photo_saved, Toast.LENGTH_SHORT).show()
                        shareMedia(uri, MIME_TYPE_JPEG)
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
     * Save bitmap to MediaStore and return its content URI, or null on failure.
     */
    private fun saveBitmapToMediaStore(bitmap: Bitmap): Uri? {
        return try {
            val filename = "AR_${System.currentTimeMillis()}.jpg"
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                put(MediaStore.MediaColumns.MIME_TYPE, MIME_TYPE_JPEG)
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
            } ?: return null
            contentResolver.openOutputStream(uri)?.use { out: OutputStream ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
            }
            uri
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save photo to MediaStore", e)
            null
        }
    }

    // ── Video recording ──────────────────────────────────────────────

    /**
     * Toggle recording on/off. Requests microphone permission if not yet granted.
     */
    private fun toggleRecording() {
        val renderer = arRenderer ?: return
        if (renderer.isRecording) {
            stopRecordingIfActive()
        } else {
            if (hasMicPermission()) {
                doStartRecording(renderer, enableAudio = true)
            } else {
                micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }
    }

    /**
     * Start recording with the given audio setting.
     */
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

    /**
     * Stop recording if currently active (called on pause/destroy too).
     */
    private fun stopRecordingIfActive() {
        val renderer = arRenderer ?: return
        if (renderer.isRecording) {
            renderer.stopRecording()
        }
    }

    /**
     * Copy the recorded MP4 from cache to the device gallery via MediaStore.
     * After saving, auto-opens the share sheet.
     */
    private fun saveVideoToGallery(sourceFile: File) {
        lifecycleScope.launch {
            val uri = withContext(Dispatchers.IO) {
                try {
                    val filename = "AR_${System.currentTimeMillis()}.mp4"
                    val contentValues = ContentValues().apply {
                        put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                        put(MediaStore.MediaColumns.MIME_TYPE, MIME_TYPE_MP4)
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/AR Viewer")
                            put(MediaStore.Video.Media.IS_PENDING, 1)
                        }
                    }
                    val mediaUri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        contentResolver.insert(
                            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                            contentValues
                        )
                    } else {
                        @Suppress("DEPRECATION")
                        contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, contentValues)
                    } ?: return@withContext null

                    contentResolver.openOutputStream(mediaUri)?.use { out ->
                        FileInputStream(sourceFile).use { input ->
                            input.copyTo(out, bufferSize = 8192)
                        }
                    }

                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        val update = ContentValues().apply {
                            put(MediaStore.Video.Media.IS_PENDING, 0)
                        }
                        contentResolver.update(mediaUri, update, null, null)
                    }
                    sourceFile.delete()
                    mediaUri
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to save video to gallery", e)
                    null
                }
            }
            if (uri != null) {
                lastSavedMediaUri = uri
                lastSavedMimeType = MIME_TYPE_MP4
                Toast.makeText(this@ArViewerActivity, R.string.video_saved, Toast.LENGTH_SHORT).show()
                shareMedia(uri, MIME_TYPE_MP4)
            } else {
                Toast.makeText(this@ArViewerActivity, R.string.video_save_failed, Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ── Sharing ──────────────────────────────────────────────────────

    /**
     * Open the system share sheet for the given media [uri].
     */
    private fun shareMedia(uri: Uri, mimeType: String) {
        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(shareIntent, getString(R.string.share_ar_content)))
    }

    /**
     * Share the last saved photo or video, or show a hint if nothing was saved yet.
     */
    private fun onShareButtonClicked() {
        val uri = lastSavedMediaUri
        val mime = lastSavedMimeType
        if (uri != null && mime != null) {
            shareMedia(uri, mime)
        } else {
            Toast.makeText(this, R.string.share_no_content, Toast.LENGTH_SHORT).show()
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
        player.prepare()
        player.playWhenReady = false // wait for marker recognition
        Log.d(TAG, "Video player prepared (paused, waiting for marker)")
    }

    /**
     * Called from ArRenderer when marker tracking starts or stops.
     * Plays video when marker is visible, pauses when lost.
     */
    private fun onMarkerTrackingChanged(isTracking: Boolean) {
        val player = exoPlayer ?: return
        if (isTracking) {
            if (!player.playWhenReady) {
                player.playWhenReady = true
                Log.d(TAG, "Marker tracked — video playing")
            }
        } else {
            if (player.playWhenReady) {
                player.playWhenReady = false
                Log.d(TAG, "Marker lost — video paused")
            }
        }
    }

    // ── Utilities ────────────────────────────────────────────────────

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED

    /**
     * Builds absolute URL for marker image (server may send relative path).
     */
    private fun absoluteMarkerUrl(url: String): String {
        val trimmed = url.trim()
        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed
        val base = BuildConfig.API_BASE_URL.trimEnd('/')
        return if (trimmed.startsWith("/")) "$base$trimmed" else "$base/$trimmed"
    }

    /**
     * Loads marker image: from cache first, then from network. Saves to cache on download.
     */
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

    /**
     * Forward touch events to [ScaleGestureDetector] for pinch-to-zoom.
     */
    @Suppress("ClickableViewAccessibility")
    private fun onGlSurfaceTouch(event: MotionEvent): Boolean {
        scaleDetector?.onTouchEvent(event)
        return true
    }

    companion object {
        private const val TAG = "ArViewerActivity"
        const val EXTRA_MANIFEST_JSON = "manifest_json"
        const val EXTRA_UNIQUE_ID = "unique_id"
        private const val MIN_ZOOM = 1.0f
        private const val MAX_ZOOM = 5.0f
        private const val TIP_ROTATION_INTERVAL_MS = 3_000L
        private const val TIP_FADE_DURATION_MS = 300L
        private const val MIME_TYPE_JPEG = "image/jpeg"
        private const val MIME_TYPE_MP4 = "video/mp4"
    }
}
