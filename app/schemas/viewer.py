"""Pydantic schemas for AR viewer API (manifest for Android ARCore app)."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ViewerManifestVideo(BaseModel):
    """Video object in viewer manifest."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: Optional[str] = None
    selection_source: Optional[str] = None
    schedule_id: Optional[int] = None
    expires_in_days: Optional[int] = None
    selected_at: Optional[str] = None


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
