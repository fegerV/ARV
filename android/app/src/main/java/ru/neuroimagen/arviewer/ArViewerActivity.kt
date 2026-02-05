package ru.neuroimagen.arviewer

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.opengl.GLSurfaceView
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.PixelCopy
import android.view.Surface
import android.widget.Button
import android.widget.Toast
import java.io.OutputStream
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.ar.core.Session
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.ar.ArRenderer
import ru.neuroimagen.arviewer.ar.ArSessionHelper
import ru.neuroimagen.arviewer.data.api.ApiProvider
import ru.neuroimagen.arviewer.data.model.ViewerManifest

/**
 * AR viewer scene: camera, ARCore Augmented Image, video overlay.
 * Receives either [EXTRA_MANIFEST_JSON] (pre-loaded) or [EXTRA_UNIQUE_ID] (will load manifest).
 */
class ArViewerActivity : AppCompatActivity() {

    private val gson = Gson()
    private var arSession: Session? = null
    private var exoPlayer: ExoPlayer? = null

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
        arSession?.pause()
    }

    override fun onDestroy() {
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

    private fun onManifestReady(manifest: ViewerManifest) {
        lifecycleScope.launch {
            val bitmap = withContext(Dispatchers.IO) {
                loadMarkerBitmap(manifest.markerImageUrl)
            }
            if (bitmap == null) {
                Toast.makeText(this@ArViewerActivity, R.string.error_marker_not_available, Toast.LENGTH_LONG).show()
                finish()
                return@launch
            }
            withContext(Dispatchers.Main) {
                if (!ArSessionHelper.checkAndInstallArCore(this@ArViewerActivity)) {
                    Toast.makeText(this@ArViewerActivity, R.string.error_arcore_required, Toast.LENGTH_LONG).show()
                    finish()
                    return@withContext
                }
                val session = ArSessionHelper.createSession(this@ArViewerActivity, bitmap, manifest)
                if (session == null) {
                    Toast.makeText(this@ArViewerActivity, R.string.error_arcore_session, Toast.LENGTH_LONG).show()
                    finish()
                    return@withContext
                }
                arSession = session
                val root = layoutInflater.inflate(R.layout.activity_ar_viewer_gl, null)
                val glView = root.findViewById<GLSurfaceView>(R.id.ar_gl_surface).apply {
                    setEGLContextClientVersion(2)
                    setEGLConfigChooser(8, 8, 8, 8, 16, 0)
                    setRenderer(ArRenderer(
                        this@ArViewerActivity,
                        session,
                        manifest,
                        onVideoSurfaceReady = { surface -> startVideoPlayer(surface, manifest) }
                    ))
                }
                root.findViewById<Button>(R.id.button_capture_photo).setOnClickListener {
                    capturePhoto(glView)
                }
                root.findViewById<Button>(R.id.button_record_video).setOnClickListener {
                    Toast.makeText(this@ArViewerActivity, R.string.record_video_coming_soon, Toast.LENGTH_SHORT).show()
                }
                setContentView(root)
            }
        }
    }

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
            val contentValues = android.content.ContentValues().apply {
                put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, filename)
                put(android.provider.MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
            }
            val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                contentResolver.insert(
                    android.provider.MediaStore.Images.Media.getContentUri(android.provider.MediaStore.VOLUME_EXTERNAL_PRIMARY),
                    contentValues
                )
            } else {
                @Suppress("DEPRECATION")
                contentResolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
            } ?: return false
            contentResolver.openOutputStream(uri)?.use { out: OutputStream ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun startVideoPlayer(surface: Surface, manifest: ViewerManifest) {
        exoPlayer?.release()
        val player = ExoPlayer.Builder(this).build()
        exoPlayer = player
        player.setMediaItem(MediaItem.fromUri(manifest.video.videoUrl))
        player.setVideoSurface(surface)
        player.prepare()
        player.playWhenReady = true
    }

    private suspend fun loadMarkerBitmap(url: String): Bitmap? = withContext(Dispatchers.IO) {
        val response = ApiProvider.viewerApi.downloadImage(url)
        if (!response.isSuccessful) return@withContext null
        val body = response.body() ?: return@withContext null
        body.byteStream().use { BitmapFactory.decodeStream(it) }
    }

    private fun loadManifestAndStart(uniqueId: String) {
        val repository = ApiProvider.viewerRepository
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) { repository.loadManifest(uniqueId) }
            result.fold(
                onSuccess = { onManifestReady(it) },
                onFailure = { finish() }
            )
        }
    }

    companion object {
        const val EXTRA_MANIFEST_JSON = "manifest_json"
        const val EXTRA_UNIQUE_ID = "unique_id"
    }
}
