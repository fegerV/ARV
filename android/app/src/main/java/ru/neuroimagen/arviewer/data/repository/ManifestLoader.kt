package ru.neuroimagen.arviewer.data.repository

import ru.neuroimagen.arviewer.data.model.ViewerManifest

interface ManifestLoader {
    suspend fun loadManifest(uniqueId: String, forceRefresh: Boolean = false): Result<ViewerManifest>
}
