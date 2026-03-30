package ru.neuroimagen.arviewer.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import ru.neuroimagen.arviewer.R
import ru.neuroimagen.arviewer.data.model.ContentUnavailableReason
import ru.neuroimagen.arviewer.data.model.ViewerError

class ViewerErrorMessagesTest {

    @Test
    fun `isRetryable marks permanent device errors as non-retryable`() {
        assertFalse(ViewerErrorMessages.isRetryable(ViewerError.DeviceNotSupported))
        assertFalse(ViewerErrorMessages.isRetryable(ViewerError.ArCoreSdkTooOld))
    }

    @Test
    fun `isRetryable keeps network and recoverable errors retryable`() {
        assertTrue(ViewerErrorMessages.isRetryable(ViewerError.Network("offline")))
        assertTrue(ViewerErrorMessages.isRetryable(ViewerError.Unavailable(ContentUnavailableReason.NOT_FOUND)))
        assertTrue(ViewerErrorMessages.isRetryable(ViewerError.ArCoreInstallRequested))
    }

    @Test
    fun `getMessageResId maps server and device errors`() {
        assertEquals(R.string.error_network, ViewerErrorMessages.getMessageResId(ViewerError.Network("offline")))
        assertEquals(R.string.error_server, ViewerErrorMessages.getMessageResId(ViewerError.Server(500, "boom")))
        assertEquals(
            R.string.error_camera_required,
            ViewerErrorMessages.getMessageResId(ViewerError.CameraPermissionDenied)
        )
        assertEquals(
            R.string.error_arcore_user_declined,
            ViewerErrorMessages.getMessageResId(ViewerError.ArCoreUserDeclined)
        )
    }

    @Test
    fun `getReasonResId maps known unavailable reasons`() {
        assertEquals(
            R.string.error_invalid_unique_id,
            ViewerErrorMessages.getReasonResId(ContentUnavailableReason.INVALID_UNIQUE_ID)
        )
        assertEquals(
            R.string.error_marker_not_available,
            ViewerErrorMessages.getReasonResId(ContentUnavailableReason.MARKER_IMAGE_NOT_AVAILABLE)
        )
        assertEquals(
            R.string.error_unknown,
            ViewerErrorMessages.getReasonResId(ContentUnavailableReason.UNKNOWN)
        )
    }
}
