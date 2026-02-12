package ru.neuroimagen.arviewer.ar

import android.content.Context
import android.graphics.SurfaceTexture
import android.opengl.GLES11Ext
import android.opengl.GLES20
import android.opengl.Matrix
import com.google.ar.core.Pose
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

/**
 * Draws a textured quad (video from SurfaceTexture) at an AR pose with given extent.
 */
class VideoQuadRenderer {

    private var program = 0
    private var positionAttrib = 0
    private var texCoordAttrib = 0
    private var mvpUniform = 0
    private var textureUniform = 0

    private var vertexBuffer: FloatBuffer? = null
    private var texCoordBuffer: FloatBuffer? = null

    private val modelMatrix = FloatArray(16)
    private val viewMatrix = FloatArray(16)
    private val projectionMatrix = FloatArray(16)
    private val mvpMatrix = FloatArray(16)

    /**
     * Call on GL thread. Creates OES texture and SurfaceTexture for ExoPlayer.
     * @param context Android context for loading shader assets
     * @param videoWidth video width from manifest (0 = use default 1024)
     * @param videoHeight video height from manifest (0 = use default 576)
     * @return pair of (textureId, SurfaceTexture)
     */
    fun createOnGlThread(context: Context, videoWidth: Int = 0, videoHeight: Int = 0): Pair<Int, SurfaceTexture> {
        val textures = IntArray(1)
        GLES20.glGenTextures(1, textures, 0)
        val textureId = textures[0]
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, textureId)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)

        val bufferWidth = if (videoWidth > 0) videoWidth else DEFAULT_BUFFER_WIDTH
        val bufferHeight = if (videoHeight > 0) videoHeight else DEFAULT_BUFFER_HEIGHT
        val surfaceTexture = SurfaceTexture(textureId)
        surfaceTexture.setDefaultBufferSize(bufferWidth, bufferHeight)

        val vertexShader = ShaderUtil.loadGLShader(GLES20.GL_VERTEX_SHADER, context, "shaders/video_quad.vert")
        val fragmentShader = ShaderUtil.loadGLShader(GLES20.GL_FRAGMENT_SHADER, context, "shaders/video_quad.frag")
        program = GLES20.glCreateProgram()
        GLES20.glAttachShader(program, vertexShader)
        GLES20.glAttachShader(program, fragmentShader)
        GLES20.glLinkProgram(program)
        positionAttrib = GLES20.glGetAttribLocation(program, "a_Position")
        texCoordAttrib = GLES20.glGetAttribLocation(program, "a_TexCoord")
        mvpUniform = GLES20.glGetUniformLocation(program, "u_MVP")
        textureUniform = GLES20.glGetUniformLocation(program, "sTexture")

        val quadVertices = floatArrayOf(
            -0.5f, 0f, -0.5f,  0.5f, 0f, -0.5f,  -0.5f, 0f, 0.5f,  0.5f, 0f, 0.5f
        )
        val quadTexCoords = floatArrayOf(
            0f, 0f,  1f, 0f,  0f, 1f,  1f, 1f
        )
        vertexBuffer = ByteBuffer.allocateDirect(quadVertices.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().apply { put(quadVertices); position(0) }
        texCoordBuffer = ByteBuffer.allocateDirect(quadTexCoords.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().apply { put(quadTexCoords); position(0) }

        ShaderUtil.checkGLError(TAG, "VideoQuadRenderer create")
        return textureId to surfaceTexture
    }

    /**
     * Draw video quad at image pose. Call after surfaceTexture.updateTexImage() on GL thread.
     */
    fun draw(
        textureId: Int,
        pose: Pose,
        extentX: Float,
        extentZ: Float,
        viewMatrixArray: FloatArray,
        projectionMatrixArray: FloatArray
    ) {
        pose.toMatrix(modelMatrix, 0)
        // Scale quad (1x1 in XZ) by extent
        modelMatrix[0] *= extentX; modelMatrix[1] *= extentX; modelMatrix[2] *= extentX
        modelMatrix[8] *= extentZ; modelMatrix[9] *= extentZ; modelMatrix[10] *= extentZ
        Matrix.multiplyMM(mvpMatrix, 0, viewMatrixArray, 0, modelMatrix, 0)
        Matrix.multiplyMM(mvpMatrix, 0, projectionMatrixArray, 0, mvpMatrix, 0)

        GLES20.glEnable(GLES20.GL_BLEND)
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA)
        GLES20.glUseProgram(program)
        GLES20.glUniformMatrix4fv(mvpUniform, 1, false, mvpMatrix, 0)
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, textureId)
        GLES20.glUniform1i(textureUniform, 0)
        vertexBuffer?.let { buf ->
            buf.position(0)
            GLES20.glVertexAttribPointer(positionAttrib, 3, GLES20.GL_FLOAT, false, 0, buf)
            GLES20.glEnableVertexAttribArray(positionAttrib)
        }
        texCoordBuffer?.let { buf ->
            buf.position(0)
            GLES20.glVertexAttribPointer(texCoordAttrib, 2, GLES20.GL_FLOAT, false, 0, buf)
            GLES20.glEnableVertexAttribArray(texCoordAttrib)
        }
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
        GLES20.glDisableVertexAttribArray(positionAttrib)
        GLES20.glDisableVertexAttribArray(texCoordAttrib)
        GLES20.glDisable(GLES20.GL_BLEND)
        ShaderUtil.checkGLError(TAG, "VideoQuadRenderer draw")
    }

    companion object {
        private const val TAG = "VideoQuadRenderer"
        private const val DEFAULT_BUFFER_WIDTH = 1024
        private const val DEFAULT_BUFFER_HEIGHT = 576
    }
}
