package ru.neuroimagen.arviewer

import android.app.Application

class ArViewerApp : Application() {

    override fun onCreate() {
        super.onCreate()
        appContext = applicationContext
    }

    companion object {
        @Volatile
        private var appContext: android.content.Context? = null

        fun applicationContext(): android.content.Context {
            return appContext
                ?: throw IllegalStateException("ArViewerApp not initialized")
        }
    }
}
