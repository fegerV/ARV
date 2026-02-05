package ru.neuroimagen.arviewer.ar

import android.content.Context
import android.opengl.GLES20
import android.util.Log
import java.io.BufferedReader
import java.io.IOException
import java.io.InputStreamReader

internal object ShaderUtil {

    private const val TAG = "ShaderUtil"

    fun loadGLShader(type: Int, context: Context, path: String): Int {
        val code = readShaderFromAssets(context, path) ?: return 0
        val shader = GLES20.glCreateShader(type)
        GLES20.glShaderSource(shader, code)
        GLES20.glCompileShader(shader)
        val status = IntArray(1)
        GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0)
        if (status[0] == 0) {
            Log.e(TAG, "Shader compile failed: ${GLES20.glGetShaderInfoLog(shader)}")
            GLES20.glDeleteShader(shader)
            return 0
        }
        return shader
    }

    private fun readShaderFromAssets(context: Context, path: String): String? {
        return try {
            context.assets.open(path).use { input ->
                BufferedReader(InputStreamReader(input)).use { it.readText() }
            }
        } catch (e: IOException) {
            Log.e(TAG, "Failed to read shader: $path", e)
            null
        }
    }

    fun checkGLError(tag: String, op: String) {
        var err: Int
        while (GLES20.glGetError().also { err = it } != GLES20.GL_NO_ERROR) {
            Log.e(tag, "$op: glError $err")
        }
    }
}
