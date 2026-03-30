package ru.neuroimagen.arviewer.data.model

import org.junit.Assert.assertEquals
import org.junit.Test

class ContentUnavailableReasonTest {

    @Test
    fun `fromApiValue maps known reasons`() {
        assertEquals(
            ContentUnavailableReason.INVALID_UNIQUE_ID,
            ContentUnavailableReason.fromApiValue("invalid_unique_id")
        )
        assertEquals(
            ContentUnavailableReason.MARKER_STILL_GENERATING,
            ContentUnavailableReason.fromApiValue("marker_still_generating")
        )
        assertEquals(
            ContentUnavailableReason.NO_PLAYABLE_VIDEO,
            ContentUnavailableReason.fromApiValue("no_playable_video")
        )
    }

    @Test
    fun `fromApiValue falls back to unknown for null or unsupported values`() {
        assertEquals(ContentUnavailableReason.UNKNOWN, ContentUnavailableReason.fromApiValue(null))
        assertEquals(ContentUnavailableReason.UNKNOWN, ContentUnavailableReason.fromApiValue(""))
        assertEquals(ContentUnavailableReason.UNKNOWN, ContentUnavailableReason.fromApiValue("something_else"))
    }
}
