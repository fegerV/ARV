package ru.neuroimagen.arviewer.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import ru.neuroimagen.arviewer.data.repository.ManifestLoader
import ru.neuroimagen.arviewer.data.repository.ViewerRepository
import ru.neuroimagen.arviewer.util.CrashLogger
import ru.neuroimagen.arviewer.util.FirebaseCrashLogger
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class BindingsModule {

    @Binds
    @Singleton
    abstract fun bindManifestLoader(repository: ViewerRepository): ManifestLoader

    @Binds
    @Singleton
    abstract fun bindCrashLogger(logger: FirebaseCrashLogger): CrashLogger
}
