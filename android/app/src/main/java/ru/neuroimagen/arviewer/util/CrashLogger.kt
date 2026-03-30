package ru.neuroimagen.arviewer.util

import javax.inject.Inject
import javax.inject.Singleton

interface CrashLogger {
    fun log(message: String)
    fun recordException(throwable: Throwable)
}

@Singleton
class FirebaseCrashLogger @Inject constructor() : CrashLogger {
    override fun log(message: String) {
        CrashReporter.log(message)
    }

    override fun recordException(throwable: Throwable) {
        CrashReporter.recordException(throwable)
    }
}
