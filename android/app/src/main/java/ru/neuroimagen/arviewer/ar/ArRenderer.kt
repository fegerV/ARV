package ru.neuroimagen.arviewer.ar

import android.content.Context
import android.graphics.SurfaceTexture
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.util.Log
import com.google.ar.core.AugmentedImage
import com.google.ar.core.Frame
import com.google.ar.core.Session
import com.google.ar.core.TrackingState
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.recording.ArRecorder
import java.io.File
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/**
 * OpenGL renderer for AR: camera background, video quad on Augmented Image,
 * and optional recording to MP4 via [ArRecorder].
 */
class ArRenderer(
    private val context: Context,
    private val session: Session,
    private val manifest: ViewerManifest,
    private val onVideoSurfaceReady: (android.view.Surface) -> Unit
) : GLSurfaceView.Renderer {

    private lateinit var backgroundRenderer: BackgroundRenderer
    private lateinit var videoQuadRenderer: VideoQuadRenderer
    private var videoTextureId = 0
    private var videoSurfaceTexture: SurfaceTexture? = null
    private var sessionFailed = false

    private val viewMatrix = FloatArray(16)
    private val projectionMatrix = FloatArray(16)

    private var surfaceWidth = 0
    private var surfaceHeight = 0

    // ── Recording ────────────────────────────────────────────────────
    private val recorder = ArRecorder()

    @Volatile
    private var pendingRecordStart: File? = null

    @Volatile
    private var pendingRecordStop = false
    private var onRecordingStopped: ((String?) -> Unit)? = null

    /** Whether the recorder is currently capturing frames. */
    val isRecording: Boolean get() = recorder.isRecording

    /**
     * Request to start recording on the next GL frame.
     *
     * @param outputFile temporary MP4 file path
     * @param onStopped callback invoked on the UI thread when recording finishes;
     *                  receives the output file path or null on failure
     */
    fun startRecording(outputFile: File, onStopped: (String?) -> Unit) {
        onRecordingStopped = onStopped
        pendingRecordStart = outputFile
    }

    /** Request to stop recording on the next GL frame. */
    fun stopRecording() {
        pendingRecordStop = true
    }

    // ── GLSurfaceView.Renderer ───────────────────────────────────────

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        backgroundRenderer = BackgroundRenderer()
        val textureId = backgroundRenderer.createOnGlThread(context)
        session.setCameraTextureName(textureId)
        session.resume()

        videoQuadRenderer = VideoQuadRenderer()
        val videoWidth = manifest.video.width ?: 0
        val videoHeight = manifest.video.height ?: 0
        val (vidTexId, surfaceTexture) = videoQuadRenderer.createOnGlThread(context, videoWidth, videoHeight)
        videoTextureId = vidTexId
        videoSurfaceTexture = surfaceTexture
        (context as? android.app.Activity)?.runOnUiThread {
            onVideoSurfaceReady(android.view.Surface(surfaceTexture))
        }
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)
        surfaceWidth = width
        surfaceHeight = height
        @Suppress("DEPRECATION")
        val rotation = (context as? android.app.Activity)?.windowManager?.defaultDisplay?.rotation ?: 0
        session.setDisplayGeometry(rotation, width, height)
    }

    override fun onDrawFrame(gl: GL10?) {
        handleRecordingCommands()

        if (sessionFailed) return
        val frame: Frame?
        try {
            frame = session.update()
        } catch (e: Throwable) {
            sessionFailed = true
            return
        }
        if (frame == null) return

        // Update video texture once (shared across screen & encoder renders)
        val st = videoSurfaceTexture
        val allImages = session.getAllTrackables(AugmentedImage::class.java)
        val hasTracking = allImages.any { it.trackingState == TrackingState.TRACKING }
        if (hasTracking && st != null) {
            st.updateTexImage()
        }

        // 1. Render to screen
        renderScene(frame, allImages)

        // 2. If recording, also render to encoder surface
        if (recorder.isRecording) {
            if (recorder.beginFrame()) {
                renderScene(frame, allImages)
                recorder.endFrame(frame.timestamp)
            }
            // Restore screen viewport
            GLES20.glViewport(0, 0, surfaceWidth, surfaceHeight)
        }
    }

    // ── Private helpers ──────────────────────────────────────────────

    /**
     * Render the full AR scene: camera background + video quads on tracked images.
     * Does NOT call [SurfaceTexture.updateTexImage] — that must happen once before
     * the first render in [onDrawFrame].
     */
    private fun renderScene(frame: Frame, images: Collection<AugmentedImage>) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        GLES20.glDisable(GLES20.GL_DEPTH_TEST)
        backgroundRenderer.draw(frame)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)

        frame.camera.getViewMatrix(viewMatrix, 0)
        frame.camera.getProjectionMatrix(projectionMatrix, 0, 0.1f, 100f)

        for (image in images) {
            if (image.trackingState == TrackingState.TRACKING) {
                videoQuadRenderer.draw(
                    videoTextureId,
                    image.centerPose,
                    image.extentX,
                    image.extentZ,
                    viewMatrix,
                    projectionMatrix
                )
            }
        }
    }

    /**
     * Process pending start/stop commands from the UI thread.
     * Must be called at the very beginning of [onDrawFrame] (GL thread).
     */
    private fun handleRecordingCommands() {
        pendingRecordStart?.let { file ->
            pendingRecordStart = null
            try {
                recorder.prepare(file, surfaceWidth, surfaceHeight)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start recording", e)
                (context as? android.app.Activity)?.runOnUiThread {
                    onRecordingStopped?.invoke(null)
                }
            }
        }

        if (pendingRecordStop) {
            pendingRecordStop = false
            val path = recorder.stop()
            (context as? android.app.Activity)?.runOnUiThread {
                onRecordingStopped?.invoke(path)
            }
        }
    }

    companion object {
        private const val TAG = "ArRenderer"
    }
}
