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
import android.view.PixelCopy
import android.view.Surface
import android.widget.Button
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
 * AR viewer scene: camera, ARCore Augmented Image, video overlay, photo capture, and video recording.
 * Receives either [EXTRA_MANIFEST_JSON] (pre-loaded) or [EXTRA_UNIQUE_ID] (will load manifest).
 */
class ArViewerActivity : AppCompatActivity() {

    private val gson = Gson()
    private var arSession: Session? = null
    private var exoPlayer: ExoPlayer? = null
    private var arRenderer: ArRenderer? = null
    private var recordButton: Button? = null

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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_ar_viewer)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

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

        val renderer = ArRenderer(
            this,
            session,
            manifest,
            onVideoSurfaceReady = { surface -> startVideoPlayer(surface, manifest) }
        )
        arRenderer = renderer

        val root = layoutInflater.inflate(R.layout.activity_ar_viewer_gl, null)
        val glView = root.findViewById<GLSurfaceView>(R.id.ar_gl_surface).apply {
            setEGLContextClientVersion(2)
            setEGLConfigChooser(RecordableEGLConfigChooser())
            preserveEGLContextOnPause = true
            setRenderer(renderer)
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

    private fun saveBitmapToMediaStore(bitmap: Bitmap): Boolean {
        return try {
            val filename = "AR_${System.currentTimeMillis()}.jpg"
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
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
            false
        }
    }

    // ── Video recording ──────────────────────────────────────────────

    private fun toggleRecording() {
        val renderer = arRenderer ?: return
        if (renderer.isRecording) {
            stopRecordingIfActive()
        } else {
            startRecording(renderer)
        }
    }

    private fun startRecording(renderer: ArRenderer) {
        val tempFile = File(cacheDir, "ar_record_${System.currentTimeMillis()}.mp4")
        recordButton?.text = getString(R.string.stop_recording)
        renderer.startRecording(tempFile) { outputPath ->
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

    private fun startVideoPlayer(surface: Surface, manifest: ViewerManifest) {
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
        player.playWhenReady = true
    }

    // ── Utilities ────────────────────────────────────────────────────

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

    companion object {
        private const val TAG = "ArViewerActivity"
        const val EXTRA_MANIFEST_JSON = "manifest_json"
        const val EXTRA_UNIQUE_ID = "unique_id"
    }
}
