package ru.neuroimagen.arviewer.recording

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.media.MediaRecorder
import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.EGLSurface
import android.opengl.GLES20
import android.util.Log
import android.view.Surface
import java.io.File
import java.nio.ByteBuffer

/**
 * Records the AR GL scene (and optionally microphone audio) to an MP4 file.
 *
 * Video: MediaCodec (H.264) fed from an EGL surface.
 * Audio: [AudioRecord] (PCM 16-bit mono 44 100 Hz) → MediaCodec (AAC-LC).
 * Both tracks are muxed into a single MP4 via [MediaMuxer].
 *
 * All **video** methods ([beginFrame], [endFrame]) must be called on the GL thread.
 * Audio runs on its own background thread.
 *
 * Usage:
 * 1. [prepare] — creates encoders, EGL surface, optional audio, and muxer
 * 2. Each frame (GL thread): [beginFrame] → render scene → [endFrame]
 * 3. [stop] — signals end-of-stream, drains, and releases resources
 */
class ArRecorder {

    // ── Video ────────────────────────────────────────────────────────
    private var videoEncoder: MediaCodec? = null
    private var inputSurface: Surface? = null
    private var encoderEglSurface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var savedDrawSurface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var savedReadSurface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var videoTrackIndex = -1
    private var recordWidth = 0
    private var recordHeight = 0
    private var startTimestampNs = -1L

    // ── Audio ────────────────────────────────────────────────────────
    private var audioEncoder: MediaCodec? = null
    private var audioRecord: AudioRecord? = null
    private var audioThread: Thread? = null
    private var audioTrackIndex = -1
    private var audioEnabled = false

    // ── Muxer ────────────────────────────────────────────────────────
    private var muxer: MediaMuxer? = null
    private val muxerLock = Any()
    @Volatile
    private var muxerStarted = false
    private var tracksToAdd = 1
    private var tracksReady = 0

    // ── State ────────────────────────────────────────────────────────
    private var outputPath: String = ""

    @Volatile
    var isRecording = false
        private set

    // ─────────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────────

    /**
     * Prepare encoder(s) and muxer. Must be called on the GL thread.
     *
     * @param outputFile  temporary file to write the MP4 into
     * @param width       recording width (should match GL surface width)
     * @param height      recording height (should match GL surface height)
     * @param enableAudio if true, records microphone audio alongside video
     */
    @SuppressLint("MissingPermission") // permission is checked in Activity before calling
    fun prepare(outputFile: File, width: Int, height: Int, enableAudio: Boolean = false) {
        // H.264 encoders require even dimensions
        recordWidth = (width / 2) * 2
        recordHeight = (height / 2) * 2
        require(recordWidth > 0 && recordHeight > 0) {
            "Invalid recording dimensions: ${width}x$height"
        }
        outputPath = outputFile.absolutePath
        startTimestampNs = -1L
        audioEnabled = enableAudio
        tracksToAdd = if (enableAudio) 2 else 1
        tracksReady = 0
        videoTrackIndex = -1
        audioTrackIndex = -1
        muxerStarted = false

        Log.d(TAG, "Preparing recorder: ${recordWidth}x$recordHeight, audio=$enableAudio -> $outputPath")

        setupVideoEncoder()
        createEncoderEglSurface()

        if (enableAudio) {
            setupAudioEncoder()
            setupAudioRecord()
        }

        muxer = MediaMuxer(outputPath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        isRecording = true

        if (enableAudio) {
            startAudioThread()
        }

        Log.d(TAG, "Recording started: ${recordWidth}x$recordHeight -> $outputPath")
    }

    /**
     * Save current EGL state and make encoder surface current.
     * Call on the GL thread before re-rendering the scene for recording.
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
     * Call on the GL thread after re-rendering the scene.
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

        drainVideoEncoder(endOfStream = false)
    }

    /**
     * Stop recording, drain remaining frames, release resources.
     * Must be called on the GL thread.
     *
     * @return output file path if successful, null otherwise
     */
    fun stop(): String? {
        if (!isRecording) return null
        isRecording = false

        // 1. Stop audio first (unblocks AudioRecord.read on the audio thread)
        if (audioEnabled) {
            try {
                audioRecord?.stop()
            } catch (e: Exception) {
                Log.w(TAG, "Error stopping AudioRecord", e)
            }
            try {
                audioThread?.join(AUDIO_THREAD_JOIN_TIMEOUT_MS)
            } catch (_: InterruptedException) {
                Log.w(TAG, "Interrupted while waiting for audio thread")
            }
            audioThread = null
        }

        // 2. Signal video end-of-stream and drain
        try {
            videoEncoder?.signalEndOfInputStream()
            drainVideoEncoder(endOfStream = true)
        } catch (e: Exception) {
            Log.e(TAG, "Error signaling video end of stream", e)
        }

        release()
        Log.d(TAG, "Recording stopped: $outputPath")
        return outputPath
    }

    // ─────────────────────────────────────────────────────────────────
    // Video encoder setup
    // ─────────────────────────────────────────────────────────────────

    private fun setupVideoEncoder() {
        val format = MediaFormat.createVideoFormat(
            MediaFormat.MIMETYPE_VIDEO_AVC, recordWidth, recordHeight
        ).apply {
            setInteger(
                MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface
            )
            setInteger(MediaFormat.KEY_BIT_RATE, VIDEO_BIT_RATE)
            setInteger(MediaFormat.KEY_FRAME_RATE, FRAME_RATE)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, I_FRAME_INTERVAL)
        }

        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        inputSurface = codec.createInputSurface()
        codec.start()
        videoEncoder = codec
    }

    // ─────────────────────────────────────────────────────────────────
    // Audio encoder + AudioRecord setup
    // ─────────────────────────────────────────────────────────────────

    private fun setupAudioEncoder() {
        val format = MediaFormat.createAudioFormat(
            MediaFormat.MIMETYPE_AUDIO_AAC,
            AUDIO_SAMPLE_RATE,
            AUDIO_CHANNEL_COUNT
        ).apply {
            setInteger(
                MediaFormat.KEY_AAC_PROFILE,
                MediaCodecInfo.CodecProfileLevel.AACObjectLC
            )
            setInteger(MediaFormat.KEY_BIT_RATE, AUDIO_BIT_RATE)
        }

        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        codec.start()
        audioEncoder = codec
    }

    @SuppressLint("MissingPermission")
    private fun setupAudioRecord() {
        val minBufSize = AudioRecord.getMinBufferSize(
            AUDIO_SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        val bufferSize = maxOf(minBufSize, AUDIO_BUFFER_SIZE)

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            AUDIO_SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )
    }

    // ─────────────────────────────────────────────────────────────────
    // Audio recording thread
    // ─────────────────────────────────────────────────────────────────

    private fun startAudioThread() {
        audioThread = Thread({ audioRecordingLoop() }, "ArRecorder-Audio").apply {
            start()
        }
    }

    /**
     * Main loop for the audio recording thread.
     * Reads PCM from [AudioRecord], feeds it to AAC [MediaCodec], drains output to muxer.
     */
    private fun audioRecordingLoop() {
        android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_URGENT_AUDIO)

        val record = audioRecord ?: return
        val codec = audioEncoder ?: return

        try {
            record.startRecording()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start AudioRecord", e)
            return
        }

        val startTimeNs = System.nanoTime()

        try {
            while (isRecording) {
                feedAudioInputBuffer(codec, record, startTimeNs, flags = 0)
                drainAudioEncoder(endOfStream = false)
            }

            // Send end-of-stream to the audio encoder
            feedAudioInputBuffer(
                codec, record, startTimeNs,
                flags = MediaCodec.BUFFER_FLAG_END_OF_STREAM
            )
            drainAudioEncoder(endOfStream = true)
        } catch (e: Exception) {
            Log.e(TAG, "Error in audio recording loop", e)
        }

        Log.d(TAG, "Audio thread finished")
    }

    /**
     * Read one buffer of PCM data from [AudioRecord] and queue it into the AAC encoder.
     */
    private fun feedAudioInputBuffer(
        codec: MediaCodec,
        record: AudioRecord,
        startTimeNs: Long,
        flags: Int
    ) {
        val inputIdx = codec.dequeueInputBuffer(DRAIN_TIMEOUT_US)
        if (inputIdx < 0) return

        val inputBuffer = codec.getInputBuffer(inputIdx) ?: return
        val bytesRead = record.read(inputBuffer, inputBuffer.remaining())
        val presentationTimeUs = (System.nanoTime() - startTimeNs) / 1000

        if (bytesRead > 0) {
            codec.queueInputBuffer(inputIdx, 0, bytesRead, presentationTimeUs, flags)
        } else {
            codec.queueInputBuffer(inputIdx, 0, 0, presentationTimeUs, flags)
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Muxer helpers (thread-safe)
    // ─────────────────────────────────────────────────────────────────

    /**
     * Add a track to the muxer. When all expected tracks are added, starts the muxer.
     * Thread-safe: called from both GL and audio threads.
     */
    private fun addTrackAndMaybeStartMuxer(format: MediaFormat): Int {
        synchronized(muxerLock) {
            val mux = muxer ?: return -1
            val idx = mux.addTrack(format)
            tracksReady++
            if (tracksReady >= tracksToAdd) {
                mux.start()
                muxerStarted = true
                Log.d(TAG, "Muxer started with $tracksReady track(s)")
            }
            return idx
        }
    }

    /**
     * Write encoded sample data to the muxer. Thread-safe.
     */
    private fun writeSample(trackIndex: Int, buffer: ByteBuffer, info: MediaCodec.BufferInfo) {
        synchronized(muxerLock) {
            if (muxerStarted && trackIndex >= 0) {
                muxer?.writeSampleData(trackIndex, buffer, info)
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Drain helpers
    // ─────────────────────────────────────────────────────────────────

    /**
     * Pull encoded video data from the H.264 encoder and write to muxer.
     * Called on the GL thread.
     */
    @Suppress("UNUSED_PARAMETER")
    private fun drainVideoEncoder(endOfStream: Boolean) {
        val codec = videoEncoder ?: return
        val bufferInfo = MediaCodec.BufferInfo()

        while (true) {
            val outputIndex = codec.dequeueOutputBuffer(bufferInfo, DRAIN_TIMEOUT_US)
            when {
                outputIndex == MediaCodec.INFO_TRY_AGAIN_LATER -> break

                outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    videoTrackIndex = addTrackAndMaybeStartMuxer(codec.outputFormat)
                    Log.d(TAG, "Video track added: index=$videoTrackIndex")
                }

                outputIndex >= 0 -> {
                    val outputBuffer = codec.getOutputBuffer(outputIndex)
                        ?: throw RuntimeException("Video encoder output buffer $outputIndex was null")

                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) {
                        bufferInfo.size = 0
                    }

                    if (bufferInfo.size > 0) {
                        outputBuffer.position(bufferInfo.offset)
                        outputBuffer.limit(bufferInfo.offset + bufferInfo.size)
                        writeSample(videoTrackIndex, outputBuffer, bufferInfo)
                    }

                    codec.releaseOutputBuffer(outputIndex, false)

                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) {
                        break
                    }
                }
            }
        }
    }

    /**
     * Pull encoded audio data from the AAC encoder and write to muxer.
     * Called on the audio thread.
     */
    @Suppress("UNUSED_PARAMETER")
    private fun drainAudioEncoder(endOfStream: Boolean) {
        val codec = audioEncoder ?: return
        val bufferInfo = MediaCodec.BufferInfo()

        while (true) {
            val outputIndex = codec.dequeueOutputBuffer(bufferInfo, DRAIN_TIMEOUT_US)
            when {
                outputIndex == MediaCodec.INFO_TRY_AGAIN_LATER -> break

                outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    audioTrackIndex = addTrackAndMaybeStartMuxer(codec.outputFormat)
                    Log.d(TAG, "Audio track added: index=$audioTrackIndex")
                }

                outputIndex >= 0 -> {
                    val outputBuffer = codec.getOutputBuffer(outputIndex)
                        ?: throw RuntimeException("Audio encoder output buffer $outputIndex was null")

                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) {
                        bufferInfo.size = 0
                    }

                    if (bufferInfo.size > 0) {
                        outputBuffer.position(bufferInfo.offset)
                        outputBuffer.limit(bufferInfo.offset + bufferInfo.size)
                        writeSample(audioTrackIndex, outputBuffer, bufferInfo)
                    }

                    codec.releaseOutputBuffer(outputIndex, false)

                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) {
                        break
                    }
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // EGL helpers
    // ─────────────────────────────────────────────────────────────────

    private fun createEncoderEglSurface() {
        val display = EGL14.eglGetCurrentDisplay()
        val context = EGL14.eglGetCurrentContext()
        Log.d(TAG, "EGL display=$display, context=$context")

        val config = getContextEglConfig(display, context)
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

    private fun getContextEglConfig(
        display: android.opengl.EGLDisplay,
        context: android.opengl.EGLContext
    ): android.opengl.EGLConfig? {
        val configIdArr = IntArray(1)
        if (!EGL14.eglQueryContext(display, context, EGL14.EGL_CONFIG_ID, configIdArr, 0)) {
            Log.w(TAG, "eglQueryContext failed: 0x${Integer.toHexString(EGL14.eglGetError())}")
            return null
        }
        val attribs = intArrayOf(EGL14.EGL_CONFIG_ID, configIdArr[0], EGL14.EGL_NONE)
        val configs = arrayOfNulls<android.opengl.EGLConfig>(1)
        val numConfigs = IntArray(1)
        if (!EGL14.eglChooseConfig(display, attribs, 0, configs, 0, 1, numConfigs, 0)
            || numConfigs[0] == 0
        ) {
            return null
        }
        return configs[0]
    }

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
            Log.w(TAG, "No recordable EGL config found")
            return null
        }
        Log.d(TAG, "Using fallback recordable EGL config")
        return configs[0]
    }

    // ─────────────────────────────────────────────────────────────────
    // Release
    // ─────────────────────────────────────────────────────────────────

    private fun release() {
        // EGL surface
        try {
            val display = EGL14.eglGetCurrentDisplay()
            if (encoderEglSurface != EGL14.EGL_NO_SURFACE) {
                EGL14.eglDestroySurface(display, encoderEglSurface)
                encoderEglSurface = EGL14.EGL_NO_SURFACE
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing EGL surface", e)
        }

        // Video encoder
        try {
            videoEncoder?.stop()
            videoEncoder?.release()
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing video encoder", e)
        }
        videoEncoder = null

        // Audio encoder
        try {
            audioEncoder?.stop()
            audioEncoder?.release()
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing audio encoder", e)
        }
        audioEncoder = null

        // AudioRecord
        try {
            audioRecord?.release()
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing AudioRecord", e)
        }
        audioRecord = null

        // Muxer
        try {
            if (muxerStarted) muxer?.stop()
            muxer?.release()
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing muxer", e)
        }
        muxer = null
        muxerStarted = false

        // Input surface
        inputSurface?.release()
        inputSurface = null
    }

    companion object {
        private const val TAG = "ArRecorder"

        // Video encoding
        private const val VIDEO_BIT_RATE = 6_000_000     // 6 Mbps
        private const val FRAME_RATE = 30
        private const val I_FRAME_INTERVAL = 2            // keyframe every 2 s

        // Audio encoding
        private const val AUDIO_SAMPLE_RATE = 44_100
        private const val AUDIO_CHANNEL_COUNT = 1
        private const val AUDIO_BIT_RATE = 128_000        // 128 kbps AAC
        private const val AUDIO_BUFFER_SIZE = 4096         // min PCM buffer

        // Timeouts
        private const val DRAIN_TIMEOUT_US = 10_000L       // 10 ms
        private const val AUDIO_THREAD_JOIN_TIMEOUT_MS = 3_000L

        /** EGL_RECORDABLE_ANDROID — not in android.opengl.EGL14 constants. */
        private const val EGL_RECORDABLE_ANDROID = 0x3142
    }
}
