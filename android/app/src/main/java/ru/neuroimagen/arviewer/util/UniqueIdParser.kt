package ru.neuroimagen.arviewer.util

import android.net.Uri

/**
 * Single source of truth for parsing AR content unique_id from various inputs.
 *
 * Supported formats:
 * - Raw UUID: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
 * - HTTPS link: `https://ar.neuroimagen.ru/view/{unique_id}`
 * - Custom scheme: `arv://view/{unique_id}`
 */
object UniqueIdParser {

    private const val EXPECTED_HOST = "ar.neuroimagen.ru"

    val UUID_REGEX = Regex(
        "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    /**
     * Extract unique_id from free-form user input (raw UUID or URL string).
     *
     * @return unique_id or null if format is not recognised
     */
    fun extractFromInput(input: String): String? {
        val trimmed = input.trim()
        if (UUID_REGEX.matches(trimmed)) return trimmed
        return try {
            parseFromUri(Uri.parse(trimmed))
        } catch (_: Exception) {
            null
        }
    }

    /**
     * Extract unique_id from a parsed [Uri] (deep link, QR code URL, etc.).
     *
     * @return unique_id or null if the URI does not match any known pattern
     */
    fun parseFromUri(uri: Uri): String? {
        return when (uri.scheme) {
            "arv" -> parseArvScheme(uri)
            "https", "http" -> parseHttpScheme(uri)
            else -> null
        }
    }

    /**
     * Returns true if [input] looks like a URL (starts with http/https/arv scheme).
     */
    fun looksLikeUrl(input: String): Boolean {
        return input.startsWith("http://") ||
                input.startsWith("https://") ||
                input.startsWith("arv://")
    }

    // ── Private helpers ──────────────────────────────────────────────

    private fun parseArvScheme(uri: Uri): String? {
        return if (uri.host == "view") {
            uri.pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
                ?: uri.path?.trimStart('/')?.takeIf { UUID_REGEX.matches(it) }
        } else {
            uri.host?.takeIf { UUID_REGEX.matches(it) }
                ?: uri.pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
        }
    }

    private fun parseHttpScheme(uri: Uri): String? {
        if (uri.host != EXPECTED_HOST) return null
        val segments = uri.pathSegments
        return if (segments.size >= 2 && segments[0] == "view") {
            segments[1].takeIf { UUID_REGEX.matches(it) }
        } else {
            null
        }
    }
}
