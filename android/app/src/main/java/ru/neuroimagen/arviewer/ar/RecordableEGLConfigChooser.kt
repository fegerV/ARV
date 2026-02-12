package ru.neuroimagen.arviewer.ar

import android.opengl.GLSurfaceView
import android.util.Log
import javax.microedition.khronos.egl.EGL10
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.egl.EGLDisplay

/**
 * EGL config chooser that requests [EGL_RECORDABLE_ANDROID] so the GL context
 * can be shared with a MediaCodec encoder surface for video recording.
 *
 * Falls back to a standard RGBA8888 + Depth16 config if the device does not
 * support the recordable attribute.
 */
class RecordableEGLConfigChooser : GLSurfaceView.EGLConfigChooser {

    override fun chooseConfig(egl: EGL10, display: EGLDisplay): EGLConfig {
        // Try recordable config first
        val recordableConfig = tryChooseConfig(egl, display, withRecordable = true)
        if (recordableConfig != null) {
            Log.d(TAG, "Using EGL config with EGL_RECORDABLE_ANDROID")
            return recordableConfig
        }

        // Fallback: standard config without recordable
        val fallbackConfig = tryChooseConfig(egl, display, withRecordable = false)
        if (fallbackConfig != null) {
            Log.w(TAG, "EGL_RECORDABLE_ANDROID not available, using fallback config")
            return fallbackConfig
        }

        throw IllegalStateException("No suitable EGL config found")
    }

    private fun tryChooseConfig(
        egl: EGL10,
        display: EGLDisplay,
        withRecordable: Boolean
    ): EGLConfig? {
        val spec = buildList {
            add(EGL10.EGL_RED_SIZE); add(8)
            add(EGL10.EGL_GREEN_SIZE); add(8)
            add(EGL10.EGL_BLUE_SIZE); add(8)
            add(EGL10.EGL_ALPHA_SIZE); add(8)
            add(EGL10.EGL_DEPTH_SIZE); add(16)
            add(EGL10.EGL_RENDERABLE_TYPE); add(EGL_OPENGL_ES2_BIT)
            if (withRecordable) {
                add(EGL_RECORDABLE_ANDROID); add(1)
            }
            add(EGL10.EGL_NONE)
        }.toIntArray()

        val numConfigs = IntArray(1)
        if (!egl.eglChooseConfig(display, spec, null, 0, numConfigs) || numConfigs[0] <= 0) {
            return null
        }
        val configs = arrayOfNulls<EGLConfig>(numConfigs[0])
        if (!egl.eglChooseConfig(display, spec, configs, numConfigs[0], numConfigs)) {
            return null
        }
        return configs[0]
    }

    companion object {
        private const val TAG = "RecordableEGLConfig"
        private const val EGL_OPENGL_ES2_BIT = 4
        /** EGL_RECORDABLE_ANDROID (not in javax.microedition.khronos.egl.EGL10) */
        private const val EGL_RECORDABLE_ANDROID = 0x3142
    }
}
