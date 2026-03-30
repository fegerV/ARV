import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


def test_viewer_routes_are_registered():
    from app.api.routes.viewer import router

    routes = {route.path for route in router.routes}

    assert "/viewer/{ar_content_id}/active-video" in routes
    assert "/ar/{unique_id}/active-video" in routes
    assert "/ar/{unique_id}/check" in routes
    assert "/ar/{unique_id}/manifest" in routes
    assert "/demo/list" in routes


def test_viewer_helper_functions_cover_expected_cases():
    from app.api.routes import viewer

    assert viewer._parse_demo_index("demo_1") == 1
    assert viewer._parse_demo_index(" demo_5 ") == 5
    assert viewer._parse_demo_index("demo_6") is None
    assert viewer._parse_demo_index("abc") is None

    assert viewer._absolute_url("/storage/demo/file.jpg").endswith("/storage/demo/file.jpg")
    assert viewer._absolute_url("storage/demo/file.jpg").endswith("/storage/demo/file.jpg")
    assert viewer._absolute_url("https://cdn.example.com/file.jpg") == "https://cdn.example.com/file.jpg"
    assert viewer._yadisk_proxy_url("yadisk://company/demo/file.mp4", 42) == (
        "/api/storage/yd-file?path=company/demo/file.mp4&company_id=42"
    )


def test_parse_user_agent_recognizes_mobile_and_app_client():
    from app.api.routes import viewer

    device_type, browser_name, os_name = viewer._parse_user_agent(
        "VertexAR/1.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36"
    )

    assert device_type == "mobile"
    assert browser_name == "Vertex AR App"
    assert os_name == "Android"


@pytest.mark.asyncio
async def test_demo_manifest_is_built_from_storage_files(monkeypatch):
    from app.api.routes import viewer

    temp_root = _make_workspace_temp_dir()
    demo_dir = temp_root / "Demo" / "demo_1"
    demo_dir.mkdir(parents=True)
    (demo_dir / "marker.jpg").write_bytes(b"marker")
    (demo_dir / "video.mp4").write_bytes(b"video")

    monkeypatch.setattr(viewer.settings, "STORAGE_BASE_PATH", str(temp_root))
    monkeypatch.setattr(viewer.settings, "PUBLIC_URL", "https://example.test")

    try:
        response = await viewer._build_demo_manifest(1)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    payload = response.body.decode("utf-8")

    assert response.status_code == 200
    assert response.headers["X-Manifest-Version"] == viewer.VIEWER_MANIFEST_VERSION
    assert response.headers["X-Cache"] == "DEMO"
    assert '"unique_id":"demo_1"' in payload
    assert '"marker_image_url":"https://example.test/storage/Demo/demo_1/marker.jpg"' in payload
    assert '"video_url":"https://example.test/storage/Demo/demo_1/video.mp4"' in payload


@pytest.mark.asyncio
async def test_demo_manifest_returns_404_when_demo_files_are_missing(monkeypatch):
    from app.api.routes import viewer

    temp_root = _make_workspace_temp_dir()
    monkeypatch.setattr(viewer.settings, "STORAGE_BASE_PATH", str(temp_root))

    try:
        with pytest.raises(HTTPException) as exc_info:
            await viewer._build_demo_manifest(2)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail.startswith("Demo content not found")


@pytest.mark.asyncio
async def test_viewer_content_check_supports_demo_mode(monkeypatch):
    from app.api.routes import viewer

    monkeypatch.setattr(viewer, "_demo_file_exists", lambda index: (True, True))

    result = await viewer.get_viewer_content_check("demo_3", db=SimpleNamespace())

    assert result == {"content_available": True}


@pytest.mark.asyncio
async def test_demo_list_returns_marker_urls_from_storage(monkeypatch):
    from app.api.routes import viewer

    temp_root = _make_workspace_temp_dir()
    demo_dir = temp_root / "Demo" / "demo_2"
    demo_dir.mkdir(parents=True)
    marker_path = demo_dir / "marker.png"
    marker_path.write_bytes(b"marker")

    monkeypatch.setattr(viewer.settings, "STORAGE_BASE_PATH", str(temp_root))
    monkeypatch.setattr(viewer.settings, "PUBLIC_URL", "https://example.test")

    try:
        response = await viewer.get_demo_list()
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    assert response["demos"][0]["marker_image_url"] is None
    assert response["demos"][1]["unique_id"] == "demo_2"
    assert response["demos"][1]["title"].endswith("2")
    assert response["demos"][1]["marker_image_url"] == "https://example.test/storage/Demo/demo_2/marker.png"


@pytest.mark.asyncio
async def test_manifest_endpoint_rejects_invalid_unique_id():
    from app.api.routes import viewer

    with pytest.raises(HTTPException) as exc_info:
        await viewer.get_viewer_manifest(
            unique_id="not-a-uuid",
            request=SimpleNamespace(headers={}, client=None),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid unique_id format"


def _make_workspace_temp_dir():
    root = Path("e:/Project/ARV/.pytest-temp") / f"viewer-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.mark.asyncio
async def test_get_viewer_landing_data_returns_absolute_urls(monkeypatch):
    from app.api.routes import viewer

    ar_content = SimpleNamespace(
        id=101,
        unique_id=str(uuid4()),
        company_id=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5),
        duration_years=1,
        status="active",
        photo_url="/storage/photos/marker.jpg",
        photo_path=None,
        order_number="ORD-101",
    )
    video = SimpleNamespace(video_url="/storage/videos/clip.mp4")

    db = _FakeDb(
        execute_result=ar_content,
        get_result=None,
    )

    async def fake_get_active_video(ar_content_id, _db):
        assert ar_content_id == 101
        return {"video": video, "source": "fallback"}

    monkeypatch.setattr(viewer.settings, "PUBLIC_URL", "https://example.test")
    monkeypatch.setattr(viewer, "get_active_video", fake_get_active_video)

    result = await viewer.get_viewer_landing_data(ar_content.unique_id, db)

    assert result == {
        "photo_url": "https://example.test/storage/photos/marker.jpg",
        "video_url": "https://example.test/storage/videos/clip.mp4",
        "order_number": "ORD-101",
    }


@pytest.mark.asyncio
async def test_get_viewer_content_check_returns_marker_generating_reason(monkeypatch):
    from app.api.routes import viewer

    ar_content = SimpleNamespace(
        id=7,
        unique_id=str(uuid4()),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2),
        duration_years=1,
        status="active",
        photo_url="/storage/photos/marker.jpg",
        photo_path=None,
        marker_status="pending",
    )
    db = _FakeDb(execute_result=ar_content)

    result = await viewer.get_viewer_content_check(ar_content.unique_id, db)

    assert result == {"content_available": False, "reason": "marker_still_generating"}


@pytest.mark.asyncio
async def test_build_manifest_returns_payload_and_updates_rotation(monkeypatch):
    from app.api.routes import viewer

    unique_id = str(uuid4())
    ar_content = SimpleNamespace(
        id=11,
        unique_id=unique_id,
        company_id=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10),
        duration_years=1,
        status="ready",
        photo_url="/storage/photos/marker.jpg",
        photo_path=None,
        marker_status="ready",
        order_number="ORD-11",
    )
    video = SimpleNamespace(
        id=22,
        filename="clip.mp4",
        video_url="/storage/videos/clip.mp4",
        preview_url="/storage/videos/clip-preview.jpg",
        duration=15,
        width=1080,
        height=1920,
        mime_type="video/mp4",
        rotation_type="sequential",
        is_active=True,
        subscription_end=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db = _FakeDb(execute_result=ar_content, get_result=None)
    request = SimpleNamespace(headers={"user-agent": "VertexAR/1.0 Android"}, client=SimpleNamespace(host="127.0.0.1"))
    seen = {"rotation_updates": 0, "recorded": 0, "cached": 0}

    async def fake_get_active_video(ar_content_id, _db):
        assert ar_content_id == 11
        return {"video": video, "source": "rotation", "schedule_id": 5, "expires_in": 30}

    async def fake_update_rotation_state(_ar_content, _db):
        seen["rotation_updates"] += 1

    async def fake_record_view(_ar_content, _request, _db):
        seen["recorded"] += 1

    async def fake_set_cached_manifest(cache_unique_id, payload):
        seen["cached"] += 1
        assert cache_unique_id == unique_id
        assert payload["unique_id"] == unique_id

    monkeypatch.setattr(viewer.settings, "PUBLIC_URL", "https://example.test")
    monkeypatch.setattr(viewer, "get_active_video", fake_get_active_video)
    monkeypatch.setattr(viewer, "update_rotation_state", fake_update_rotation_state)
    monkeypatch.setattr(viewer, "_record_view", fake_record_view)
    monkeypatch.setattr(viewer, "_set_cached_manifest", fake_set_cached_manifest)

    response = await viewer._build_manifest(unique_id, request, db)
    payload = response.body.decode("utf-8")

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    assert '"unique_id":"' + unique_id + '"' in payload
    assert '"order_number":"ORD-11"' in payload
    assert '"selection_source":"rotation"' in payload
    assert '"video_url":"https://example.test/storage/videos/clip.mp4"' in payload
    assert seen == {"rotation_updates": 1, "recorded": 1, "cached": 1}


@pytest.mark.asyncio
async def test_build_manifest_rejects_missing_marker(monkeypatch):
    from app.api.routes import viewer

    unique_id = str(uuid4())
    ar_content = SimpleNamespace(
        id=15,
        unique_id=unique_id,
        company_id=None,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10),
        duration_years=1,
        status="active",
        photo_url="/storage/photos/marker.jpg",
        photo_path=None,
        marker_status="processing",
        order_number="ORD-15",
    )
    db = _FakeDb(execute_result=ar_content)

    monkeypatch.setattr(viewer.settings, "PUBLIC_URL", "https://example.test")

    with pytest.raises(HTTPException) as exc_info:
        await viewer._build_manifest(
            unique_id,
            SimpleNamespace(headers={}, client=None),
            db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Marker is still being generated, try again later"


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, execute_result=None, get_result=None):
        self.execute_result = execute_result
        self.get_result = get_result

    async def execute(self, _stmt):
        return _FakeScalarResult(self.execute_result)

    async def get(self, _model, _pk):
        return self.get_result
