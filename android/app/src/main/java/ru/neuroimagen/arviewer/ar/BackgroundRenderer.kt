package ru.neuroimagen.arviewer.ar

import android.content.Context
import android.opengl.GLES11Ext
import android.opengl.GLES20
import com.google.ar.core.Coordinates2d
import com.google.ar.core.Frame
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

/**
 * Renders the AR camera background from the texture filled by ARCore Session.
 * Uses Frame.transformCoordinates2d for correct display geometry.
 */
class BackgroundRenderer {

    private val quadCoords: FloatBuffer
    private var quadTexCoords: FloatBuffer

    private var cameraProgram = 0
    private var cameraPositionAttrib = 0
    private var cameraTexCoordAttrib = 0
    private var cameraTextureUniform = 0

    var cameraTextureId = -1
        private set

    private val coordsPerVertex = 2
    private val texCoordsPerVertex = 2
    private val floatSize = 4

    /** Base tex coords computed by ARCore (before zoom). */
    private val baseTexCoords = FloatArray(8)

    init {
        val bbCoords = ByteBuffer.allocateDirect(QUAD_COORDS.size * floatSize)
        bbCoords.order(ByteOrder.nativeOrder())
        quadCoords = bbCoords.asFloatBuffer()
        quadCoords.put(QUAD_COORDS)
        quadCoords.position(0)

        quadTexCoords = ByteBuffer.allocateDirect(4 * texCoordsPerVertex * floatSize)
            .order(ByteOrder.nativeOrder())
            .asFloatBuffer()
    }

    /**
     * Call on GL thread (e.g. in onSurfaceCreated).
     * Creates OES texture and shader program; returns texture id for Session.setCameraTextureName().
     */
    fun createOnGlThread(context: Context): Int {
        val textures = IntArray(1)
        GLES20.glGenTextures(1, textures, 0)
        cameraTextureId = textures[0]
        val textureTarget = GLES11Ext.GL_TEXTURE_EXTERNAL_OES
        GLES20.glBindTexture(textureTarget, cameraTextureId)
        GLES20.glTexParameteri(textureTarget, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(textureTarget, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(textureTarget, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(textureTarget, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)

        val vertexShader = ShaderUtil.loadGLShader(
            GLES20.GL_VERTEX_SHADER, context, "shaders/screenquad.vert"
        )
        val fragmentShader = ShaderUtil.loadGLShader(
            GLES20.GL_FRAGMENT_SHADER, context, "shaders/screenquad.frag"
        )
        cameraProgram = GLES20.glCreateProgram()
        GLES20.glAttachShader(cameraProgram, vertexShader)
        GLES20.glAttachShader(cameraProgram, fragmentShader)
        GLES20.glLinkProgram(cameraProgram)
        cameraPositionAttrib = GLES20.glGetAttribLocation(cameraProgram, "a_Position")
        cameraTexCoordAttrib = GLES20.glGetAttribLocation(cameraProgram, "a_TexCoord")
        cameraTextureUniform = GLES20.glGetUniformLocation(cameraProgram, "sTexture")
        ShaderUtil.checkGLError(TAG, "BackgroundRenderer create")
        return cameraTextureId
    }

    /**
     * Draw camera background with optional digital zoom.
     *
     * @param frame current ARCore frame
     * @param zoomLevel zoom factor (1.0 = no zoom, 2.0 = 2x zoom toward center)
     */
    fun draw(frame: Frame, zoomLevel: Float = 1.0f) {
        if (frame.hasDisplayGeometryChanged()) {
            frame.transformCoordinates2d(
                Coordinates2d.OPENGL_NORMALIZED_DEVICE_COORDINATES,
                quadCoords,
                Coordinates2d.TEXTURE_NORMALIZED,
                quadTexCoords
            )
            // Save original tex coords before zoom
            quadTexCoords.position(0)
            quadTexCoords.get(baseTexCoords)
        }
        if (frame.timestamp == 0L) return

        // Apply zoom: scale tex coords toward center (0.5, 0.5)
        if (zoomLevel != 1.0f) {
            val zoomed = FloatArray(baseTexCoords.size)
            for (i in baseTexCoords.indices) {
                zoomed[i] = 0.5f + (baseTexCoords[i] - 0.5f) / zoomLevel
            }
            quadTexCoords.position(0)
            quadTexCoords.put(zoomed)
        } else {
            quadTexCoords.position(0)
            quadTexCoords.put(baseTexCoords)
        }
        quadTexCoords.position(0)
        GLES20.glDisable(GLES20.GL_DEPTH_TEST)
        GLES20.glDepthMask(false)
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, cameraTextureId)
        GLES20.glUseProgram(cameraProgram)
        GLES20.glUniform1i(cameraTextureUniform, 0)
        GLES20.glVertexAttribPointer(
            cameraPositionAttrib, coordsPerVertex, GLES20.GL_FLOAT, false, 0, quadCoords
        )
        GLES20.glVertexAttribPointer(
            cameraTexCoordAttrib, texCoordsPerVertex, GLES20.GL_FLOAT, false, 0, quadTexCoords
        )
        GLES20.glEnableVertexAttribArray(cameraPositionAttrib)
        GLES20.glEnableVertexAttribArray(cameraTexCoordAttrib)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
        GLES20.glDisableVertexAttribArray(cameraPositionAttrib)
        GLES20.glDisableVertexAttribArray(cameraTexCoordAttrib)
        GLES20.glDepthMask(true)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)
        ShaderUtil.checkGLError(TAG, "BackgroundRenderer draw")
    }

    companion object {
        private const val TAG = "BackgroundRenderer"
        private val QUAD_COORDS = floatArrayOf(
            -1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f
        )
    }
}
