package ru.neuroimagen.arviewer.recording

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.EGLSurface
import android.opengl.GLES20
import android.util.Log
import android.view.Surface
import java.io.File

/**
 * Records the AR GL scene to an MP4 file using MediaCodec (H.264) + MediaMuxer.
 *
 * All public methods must be called on the GL thread (inside [onDrawFrame]).
 *
 * Usage:
 * 1. [prepare] — creates encoder, EGL surface, and muxer
 * 2. Each frame: [beginFrame] → render scene → [endFrame]
 * 3. [stop] — signals end-of-stream, drains, and releases resources
 */
class ArRecorder {

    private var encoder: MediaCodec? = null
    private var muxer: MediaMuxer? = null
    private var inputSurface: Surface? = null
    private var encoderEglSurface: EGLSurface = EGL14.EGL_NO_SURFACE

    private var savedDrawSurface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var savedReadSurface: EGLSurface = EGL14.EGL_NO_SURFACE

    private var trackIndex = -1
    private var muxerStarted = false
    private var outputPath: String = ""
    private var startTimestampNs: Long = -1L

    private var recordWidth = 0
    private var recordHeight = 0

    @Volatile
    var isRecording = false
        private set

    /**
     * Prepare encoder and muxer. Must be called on GL thread.
     *
     * @param outputFile temporary file to write the MP4 into
     * @param width recording width (should match GL surface width)
     * @param height recording height (should match GL surface height)
     */
    fun prepare(outputFile: File, width: Int, height: Int) {
        // H.264 encoders require even dimensions
        recordWidth = (width / 2) * 2
        recordHeight = (height / 2) * 2
        require(recordWidth > 0 && recordHeight > 0) {
            "Invalid recording dimensions: ${width}x$height"
        }
        outputPath = outputFile.absolutePath
        startTimestampNs = -1L

        Log.d(TAG, "Preparing recorder: ${recordWidth}x$recordHeight -> $outputPath")

        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, recordWidth, recordHeight
        ).apply {
            setInteger(
                MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface
            )
            setInteger(MediaFormat.KEY_BIT_RATE, BIT_RATE)
            setInteger(MediaFormat.KEY_FRAME_RATE, FRAME_RATE)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, I_FRAME_INTERVAL)
        }

        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        inputSurface = codec.createInputSurface()
        codec.start()
        encoder = codec

        createEncoderEglSurface()

        muxer = MediaMuxer(outputPath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)

        isRecording = true
        Log.d(TAG, "Recording started: ${width}x$height -> $outputPath")
    }

    /**
     * Save current EGL state and make encoder surface current.
     * Call on GL thread before re-rendering the scene for recording.
     *
     * @return true if encoder surface is now current
     */
    fun beginFrame(): Boolean {
        if (!isRecording) return false

        val display = EGL14.eglGetCurrentDisplay()
        savedDrawSurface = EGL14.eglGetCurrentSurface(EGL14.EGL_DRAW)
        savedReadSurface = EGL14.eglGetCurrentSurface(EGL14.EGL_READ)

        val context = EGL14.eglGetCurrentContext()
        if (!EGL14.eglMakeCurrent(display, encoderEglSurface, encoderEglSurface, context)) {
            Log.e(TAG, "eglMakeCurrent(encoder) failed: 0x${Integer.toHexString(EGL14.eglGetError())}")
            return false
        }

        GLES20.glViewport(0, 0, recordWidth, recordHeight)
        return true
    }

    /**
     * Set presentation timestamp, swap encoder buffers, restore original EGL surface.
     * Call on GL thread after re-rendering the scene.
     *
     * @param frameTimestampNs ARCore frame timestamp in nanoseconds
     */
    fun endFrame(frameTimestampNs: Long) {
        if (!isRecording) return

        if (startTimestampNs < 0) {
            startTimestampNs = frameTimestampNs
        }
        val presentationNs = frameTimestampNs - startTimestampNs

        val display = EGL14.eglGetCurrentDisplay()
        EGLExt.eglPresentationTimeANDROID(display, encoderEglSurface, presentationNs)
        EGL14.eglSwapBuffers(display, encoderEglSurface)

        // Restore original GL surfaces
        val context = EGL14.eglGetCurrentContext()
        EGL14.eglMakeCurrent(display, savedDrawSurface, savedReadSurface, context)

        drainEncoder(endOfStream = false)
    }

    /**
     * Stop recording, drain remaining frames, release resources.
     *
     * @return output file path if successful, null otherwise
     */
    fun stop(): String? {
        if (!isRecording) return null
        isRecording = false

        try {
            encoder?.signalEndOfInputStream()
            drainEncoder(endOfStream = true)
        } catch (e: Exception) {
            Log.e(TAG, "Error signaling end of stream", e)
        }

        release()
        Log.d(TAG, "Recording stopped: $outputPath")
        return outputPath
    }

    // ── Private helpers ──────────────────────────────────────────────

    private fun createEncoderEglSurface() {
        val display = EGL14.eglGetCurrentDisplay()
        val context = EGL14.eglGetCurrentContext()
        Log.d(TAG, "EGL display=$display, context=$context")

        // Strategy 1: reuse the config from the current GL context
        val config = getContextEglConfig(display, context)
            // Strategy 2: find a recordable RGBA8888 config
            ?: findRecordableConfig(display)
            ?: throw IllegalStateException("No suitable EGL config for encoder surface")

        val surfaceAttribs = intArrayOf(EGL14.EGL_NONE)
        encoderEglSurface = EGL14.eglCreateWindowSurface(
            display, config, inputSurface!!, surfaceAttribs, 0
        )
        if (encoderEglSurface == EGL14.EGL_NO_SURFACE) {
            val err = EGL14.eglGetError()
            throw IllegalStateException(
                "eglCreateWindowSurface failed: 0x${Integer.toHexString(err)}"
            )
        }
        Log.d(TAG, "Encoder EGL surface created successfully")
    }

    /**
     * Try to retrieve the EGL config used by the current GL context.
     */
    private fun getContextEglConfig(
        display: android.opengl.EGLDisplay,
        context: android.opengl.EGLContext
    ): android.opengl.EGLConfig? {
        val configIdArr = IntArray(1)
        if (!EGL14.eglQueryContext(display, context, EGL14.EGL_CONFIG_ID, configIdArr, 0)) {
            Log.w(TAG, "eglQueryContext failed: 0x${Integer.toHexString(EGL14.eglGetError())}")
            return null
        }
        Log.d(TAG, "Context config ID: ${configIdArr[0]}")

        val attribs = intArrayOf(EGL14.EGL_CONFIG_ID, configIdArr[0], EGL14.EGL_NONE)
        val configs = arrayOfNulls<android.opengl.EGLConfig>(1)
        val numConfigs = IntArray(1)
        if (!EGL14.eglChooseConfig(display, attribs, 0, configs, 0, 1, numConfigs, 0)
            || numConfigs[0] == 0
        ) {
            Log.w(TAG, "eglChooseConfig for config ID ${configIdArr[0]} returned 0 matches")
            return null
        }
        return configs[0]
    }

    /**
     * Fallback: find an RGBA8888 + GLES2 config with EGL_RECORDABLE_ANDROID.
     */
    private fun findRecordableConfig(
        display: android.opengl.EGLDisplay
    ): android.opengl.EGLConfig? {
        val attribs = intArrayOf(
            EGL14.EGL_RED_SIZE, 8,
            EGL14.EGL_GREEN_SIZE, 8,
            EGL14.EGL_BLUE_SIZE, 8,
            EGL14.EGL_ALPHA_SIZE, 8,
            EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
            EGL_RECORDABLE_ANDROID, 1,
            EGL14.EGL_NONE
        )
        val configs = arrayOfNulls<android.opengl.EGLConfig>(1)
        val numConfigs = IntArray(1)
        if (!EGL14.eglChooseConfig(display, attribs, 0, configs, 0, 1, numConfigs, 0)
            || numConfigs[0] == 0
        ) {
            Log.w(TAG, "No recordable EGL config found either")
            return null
        }
        Log.d(TAG, "Using fallback recordable EGL config")
        return configs[0]
    }

    /**
     * Pull encoded data from MediaCodec and write to MediaMuxer.
     */
    private fun drainEncoder(endOfStream: Boolean) {
        val codec = encoder ?: return
        val mux = muxer ?: return
        val bufferInfo = MediaCodec.BufferInfo()

        while (true) {
            val outputIndex = codec.dequeueOutputBuffer(bufferInfo, TIMEOUT_US)
            when {
                outputIndex == MediaCodec.INFO_TRY_AGAIN_LATER -> break

                outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    if (muxerStarted) {
                        Log.w(TAG, "Output format changed after muxer started")
                        break
                    }
                    trackIndex = mux.addTrack(codec.outputFormat)
                    mux.start()
                    muxerStarted = true
                }

                outputIndex >= 0 -> {
                    val outputBuffer = codec.getOutputBuffer(outputIndex)
                        ?: throw RuntimeException("Encoder output buffer $outputIndex was null")

                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) {
                        bufferInfo.size = 0
                    }

                    if (bufferInfo.size > 0 && muxerStarted) {
                        outputBuffer.position(bufferInfo.offset)
                        outputBuffer.limit(bufferInfo.offset + bufferInfo.size)
                        mux.writeSampleData(trackIndex, outputBuffer, bufferInfo)
                    }

                    codec.releaseOutputBuffer(outputIndex, false)

                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) {
                        break
                    }
                }
            }
        }
    }

    private fun release() {
        try {
            val display = EGL14.eglGetCurrentDisplay()
            if (encoderEglSurface != EGL14.EGL_NO_SURFACE) {
                EGL14.eglDestroySurface(display, encoderEglSurface)
                encoderEglSurface = EGL14.EGL_NO_SURFACE
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing EGL surface", e)
        }

        try {
            encoder?.stop()
            encoder?.release()
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing encoder", e)
        }
        encoder = null

        try {
            if (muxerStarted) muxer?.stop()
            muxer?.release()
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing muxer", e)
        }
        muxer = null
        muxerStarted = false

        inputSurface?.release()
        inputSurface = null
    }

    companion object {
        private const val TAG = "ArRecorder"
        private const val BIT_RATE = 6_000_000      // 6 Mbps — good quality for 1080p
        private const val FRAME_RATE = 30
        private const val I_FRAME_INTERVAL = 2      // keyframe every 2 seconds
        private const val TIMEOUT_US = 10_000L      // 10 ms drain timeout
        /** EGL_RECORDABLE_ANDROID — not in android.opengl.EGL14 constants */
        private const val EGL_RECORDABLE_ANDROID = 0x3142
    }
}
