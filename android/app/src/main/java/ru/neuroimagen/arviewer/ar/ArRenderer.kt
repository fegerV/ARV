package ru.neuroimagen.arviewer.ar

import android.content.Context
import android.graphics.SurfaceTexture
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import com.google.ar.core.AugmentedImage
import com.google.ar.core.Frame
import com.google.ar.core.Session
import com.google.ar.core.TrackingState
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/**
 * OpenGL renderer for AR: camera background and video quad on Augmented Image.
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

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        backgroundRenderer = BackgroundRenderer()
        val textureId = backgroundRenderer.createOnGlThread(context)
        session.setCameraTextureName(textureId)
        // Start camera: Activity.onResume() already ran before we set this content view, so resume here.
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
        val rotation = (context as? android.app.Activity)?.windowManager?.defaultDisplay?.rotation ?: 0
        session.setDisplayGeometry(rotation, width, height)
    }

    override fun onDrawFrame(gl: GL10?) {
        if (sessionFailed) return
        val frame: Frame?
        try {
            frame = session.update()
        } catch (e: Throwable) {
            sessionFailed = true
            return
        }
        if (frame == null) return

        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        GLES20.glDisable(GLES20.GL_DEPTH_TEST)
        backgroundRenderer.draw(frame)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)

        frame.camera.getViewMatrix(viewMatrix, 0)
        frame.camera.getProjectionMatrix(projectionMatrix, 0, 0.1f, 100f)

        val st = videoSurfaceTexture
        // Use getAllTrackables instead of getUpdatedTrackables so that
        // updateTexImage() and draw() are called every frame while the
        // marker is visible, not only when tracking state changes.
        val allImages = session.getAllTrackables(AugmentedImage::class.java)
        for (image in allImages) {
            if (image.trackingState == TrackingState.TRACKING && st != null) {
                st.updateTexImage()
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
}
