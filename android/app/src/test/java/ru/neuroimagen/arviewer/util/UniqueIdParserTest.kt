package ru.neuroimagen.arviewer.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UniqueIdParserTest {

    private val uniqueId = "123e4567-e89b-12d3-a456-426614174000"

    @Test
    fun `extractFromInput returns raw uuid as is`() {
        assertEquals(uniqueId, UniqueIdParser.extractFromInput(uniqueId))
    }

    @Test
    fun `extractFromInput parses supported https link`() {
        val input = "https://ar.neuroimagen.ru/view/$uniqueId"

        assertEquals(uniqueId, UniqueIdParser.extractFromInput(input))
    }

    @Test
    fun `extractFromInput parses arv deep link`() {
        assertEquals(uniqueId, UniqueIdParser.extractFromInput("arv://view/$uniqueId"))
    }

    @Test
    fun `extractFromInput rejects unknown http host`() {
        assertNull(UniqueIdParser.extractFromInput("https://example.com/view/$uniqueId"))
    }

    @Test
    fun `looksLikeUrl recognizes supported schemes`() {
        assertTrue(UniqueIdParser.looksLikeUrl("https://ar.neuroimagen.ru/view/$uniqueId"))
        assertTrue(UniqueIdParser.looksLikeUrl("http://ar.neuroimagen.ru/view/$uniqueId"))
        assertTrue(UniqueIdParser.looksLikeUrl("arv://view/$uniqueId"))
        assertFalse(UniqueIdParser.looksLikeUrl(uniqueId))
    }
}
