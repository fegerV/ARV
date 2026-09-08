"""Pydantic schemas for AR viewer API (manifest for Android ARCore app)."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ViewerManifestVideo(BaseModel):
    """Video object in viewer manifest."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    video_url: str
    thumbnail_url: str | None = None
    duration: int | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    selection_source: str | None = None
    schedule_id: int | None = None
    expires_in_days: int | None = None
    selected_at: str | None = None


# Stable manifest version for client compatibility; bump when breaking changes are introduced.
VIEWER_MANIFEST_VERSION = "1"


class ViewerManifestResponse(BaseModel):
    """Response for GET /api/viewer/ar/{unique_id}/manifest."""

    manifest_version: str = VIEWER_MANIFEST_VERSION
    unique_id: str
    order_number: str
    marker_image_url: str
    photo_url: str
    video: ViewerManifestVideo
    expires_at: str
    status: str
