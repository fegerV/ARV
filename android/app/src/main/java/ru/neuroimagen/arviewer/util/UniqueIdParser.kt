package ru.neuroimagen.arviewer.util

import android.net.Uri
import java.net.URI

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
            parseFromUriString(trimmed)
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
        return parseUriComponents(
            scheme = uri.scheme,
            host = uri.host,
            pathSegments = uri.pathSegments,
            path = uri.path,
        )
    }

    private fun parseFromUriString(value: String): String? {
        val uri = URI(value)
        return parseUriComponents(
            scheme = uri.scheme,
            host = uri.host,
            pathSegments = uri.path
                ?.trim('/')
                ?.split('/')
                ?.filter { it.isNotBlank() }
                .orEmpty(),
            path = uri.path,
        )
    }

    private fun parseUriComponents(
        scheme: String?,
        host: String?,
        pathSegments: List<String>,
        path: String?,
    ): String? {
        return when (scheme) {
            "arv" -> parseArvScheme(host, pathSegments, path)
            "https", "http" -> parseHttpScheme(host, pathSegments)
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

    private fun parseArvScheme(host: String?, pathSegments: List<String>, path: String?): String? {
        return if (host == "view") {
            pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
                ?: path?.trimStart('/')?.takeIf { UUID_REGEX.matches(it) }
        } else {
            host?.takeIf { UUID_REGEX.matches(it) }
                ?: pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
        }
    }

    private fun parseHttpScheme(host: String?, pathSegments: List<String>): String? {
        if (host != EXPECTED_HOST) return null
        val segments = pathSegments
        return if (segments.size >= 2 && segments[0] == "view") {
            segments[1].takeIf { UUID_REGEX.matches(it) }
        } else {
            null
        }
    }
}
