from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.schemas.video_schedule import VideoActiveUpdate, VideoPlaybackModeUpdate, VideoSubscriptionUpdate


def test_video_helper_functions_handle_yadisk_and_subscription_presets():
    from app.api.routes import videos

    one_year = videos.parse_subscription_preset("1y")
    two_years = videos.parse_subscription_preset("2y")
    iso_value = videos.parse_subscription_preset("2030-01-02T03:04:05Z")

    assert videos._is_yadisk_path("yadisk://company/video.mp4") is True
    assert videos._is_yadisk_path("/storage/video.mp4") is False
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert 360 <= (one_year - now_utc).days <= 366
    assert 725 <= (two_years - now_utc).days <= 731
    assert iso_value.isoformat() == "2030-01-02T03:04:05"

    with pytest.raises(ValueError):
        videos.parse_subscription_preset("not-a-date")


@pytest.mark.asyncio
async def test_regenerate_video_thumbnail_requires_existing_video():
    from app.api.routes import videos

    db = _FakeDb(get_map={})

    with pytest.raises(HTTPException) as exc_info:
        await videos.regenerate_video_thumbnail(99, BackgroundTasks(), db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Video not found"


@pytest.mark.asyncio
async def test_regenerate_video_thumbnail_queues_background_task():
    from app.api.routes import videos

    video = SimpleNamespace(id=10, video_path="/storage/videos/clip.mp4", status=None)
    db = _FakeDb(get_map={(videos.Video, 10): video})
    background_tasks = BackgroundTasks()

    result = await videos.regenerate_video_thumbnail(10, background_tasks, db)

    assert result == {"status": "processing", "video_id": 10}
    assert video.status == videos.VideoStatus.PROCESSING
    assert db.commit_calls == 1
    assert len(background_tasks.tasks) == 1


@pytest.mark.asyncio
async def test_set_video_active_switches_active_video_and_resets_rotation_state():
    from app.api.routes import videos

    ar_content = SimpleNamespace(id=5, active_video_id=None, rotation_state=3)
    target_video = SimpleNamespace(id=12, ar_content_id=5, is_active=False)
    db = _FakeDb(
        get_map={
            (videos.ARContent, 5): ar_content,
            (videos.Video, 12): target_video,
        }
    )

    result = await videos.set_video_active("5", "12", db)

    assert result.status == "success"
    assert result.active_video_id == 12
    assert target_video.is_active is True
    assert ar_content.active_video_id == 12
    assert ar_content.rotation_state == 0
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_update_video_subscription_deactivates_expired_active_video():
    from app.api.routes import videos

    ar_content = SimpleNamespace(id=8, active_video_id=21)
    video = SimpleNamespace(id=21, ar_content_id=8, is_active=True, subscription_end=None)
    db = _FakeDb(
        get_map={
            (videos.ARContent, 8): ar_content,
            (videos.Video, 21): video,
        }
    )
    payload = VideoSubscriptionUpdate(subscription="2000-01-01T00:00:00Z")

    result = await videos.update_video_subscription("8", "21", payload, db)

    assert result["status"] == "updated"
    assert result["is_active"] is False
    assert ar_content.active_video_id is None
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_update_playback_mode_manual_requires_target_video():
    from app.api.routes import videos

    ar_content = SimpleNamespace(id=3, active_video_id=None, rotation_state=1)
    videos_list = [
        SimpleNamespace(id=31, is_active=False, rotation_type="cyclic"),
        SimpleNamespace(id=32, is_active=True, rotation_type="cyclic"),
    ]
    db = _FakeDb(
        get_map={(videos.ARContent, 3): ar_content},
        execute_results=[_FakeExecuteResult(videos_list)],
    )
    payload = VideoPlaybackModeUpdate(mode="manual", active_video_id=31)

    result = await videos.update_playback_mode("3", payload, db)

    assert result == {
        "status": "updated",
        "mode": "manual",
        "active_video_id": 31,
        "active_video_ids": [31],
    }
    assert videos_list[0].is_active is True
    assert videos_list[1].is_active is False
    assert all(video.rotation_type == "none" for video in videos_list)
    assert ar_content.rotation_state == 0
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_update_playback_mode_rejects_unknown_automatic_video_ids():
    from app.api.routes import videos

    ar_content = SimpleNamespace(id=4, active_video_id=40, rotation_state=1)
    videos_list = [
        SimpleNamespace(id=41, is_active=True, rotation_type="none"),
        SimpleNamespace(id=42, is_active=False, rotation_type="none"),
    ]
    db = _FakeDb(
        get_map={(videos.ARContent, 4): ar_content},
        execute_results=[_FakeExecuteResult(videos_list)],
    )
    payload = VideoPlaybackModeUpdate(mode="cyclic", active_video_ids=[41, 99])

    with pytest.raises(HTTPException) as exc_info:
        await videos.update_playback_mode("4", payload, db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Unknown video IDs: [99]"


@pytest.mark.asyncio
async def test_update_video_active_flag_clears_active_video_reference():
    from app.api.routes import videos

    ar_content = SimpleNamespace(id=6, active_video_id=16)
    video = SimpleNamespace(id=16, ar_content_id=6, is_active=True)
    db = _FakeDb(
        get_map={
            (videos.ARContent, 6): ar_content,
            (videos.Video, 16): video,
        }
    )

    result = await videos.update_video_active_flag("6", "16", VideoActiveUpdate(is_active=False), db)

    assert result == {"status": "updated", "video_id": 16, "is_active": False}
    assert ar_content.active_video_id is None
    assert db.commit_calls == 1
    assert db.refresh_calls == 1


class _FakeExecuteResult:
    def __init__(self, values):
        self._values = values

    def scalar_one_or_none(self):
        if isinstance(self._values, list):
            return self._values[0] if self._values else None
        return self._values

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeDb:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.commit_calls = 0
        self.rollback_calls = 0
        self.refresh_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        if self.execute_results:
            return self.execute_results.pop(0)
        return _FakeExecuteResult([])

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1
