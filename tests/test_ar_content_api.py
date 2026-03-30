from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


def test_ar_content_helper_functions_cover_basic_validation():
    from app.api.routes import ar_content
    from app.html.routes.ar_content import _js_safe_text

    order_number = ar_content.generate_order_number()

    assert order_number.startswith("ORD-")
    assert len(order_number) == len("ORD-YYYYMMDD-0000")
    assert ar_content.validate_file_extension("photo.JPG", ["jpg", "png"]) is True
    assert ar_content.validate_file_extension("clip.mov", ["mp4", "webm"]) is False
    assert ar_content.validate_file_size(1024, 2048) is True
    assert ar_content.validate_file_size(4096, 2048) is False
    assert _js_safe_text('A "quote" & test') == "A &quot;quote&quot; &amp; test"


@pytest.mark.asyncio
async def test_validate_company_project_requires_matching_project():
    from app.api.routes import ar_content

    company = SimpleNamespace(id=1, name="Vertex")
    project = SimpleNamespace(id=2, company_id=99, name="Mismatch")
    db = _FakeDb(
        get_map={
            (ar_content.Company, 1): company,
            (ar_content.Project, 2): project,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        await ar_content.validate_company_project(1, 2, db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Project does not belong to company"


@pytest.mark.asyncio
async def test_get_ar_content_or_404_returns_content_when_found():
    from app.api.routes import ar_content

    content = SimpleNamespace(id=12, order_number="ORD-12")
    db = _FakeDb(get_map={(ar_content.ARContent, 12): content})

    result = await ar_content.get_ar_content_or_404(12, db)

    assert result is content


@pytest.mark.asyncio
async def test_parse_ar_content_data_supports_new_format():
    from app.api.routes import ar_content

    photo = SimpleNamespace(filename="photo.jpg")
    video = SimpleNamespace(filename="video.mp4")
    request = _FakeRequest(
        {
            "customer_name": "Alice",
            "customer_phone": "+123",
            "customer_email": "alice@example.com",
            "duration_years": "5",
            "photo_file": photo,
            "video_file": video,
            "auto_enhance": "yes",
        }
    )

    result = await ar_content.parse_ar_content_data(request)

    assert result == {
        "customer_name": "Alice",
        "customer_phone": "+123",
        "customer_email": "alice@example.com",
        "duration_years": 5,
        "photo_file": photo,
        "video_file": video,
        "auto_enhance": True,
    }


@pytest.mark.asyncio
async def test_parse_ar_content_data_supports_legacy_format():
    from app.api.routes import ar_content

    image = SimpleNamespace(filename="legacy.jpg")
    video = SimpleNamespace(filename="legacy.mp4")
    request = _FakeRequest(
        {
            "content_metadata": '{"customer_name":"Bob","customer_phone":"555","customer_email":"bob@example.com","playback_duration":"3_years"}',
            "image": image,
            "video": video,
            "auto_enhance": "0",
        }
    )

    result = await ar_content.parse_ar_content_data(request)

    assert result == {
        "customer_name": "Bob",
        "customer_phone": "555",
        "customer_email": "bob@example.com",
        "duration_years": 3,
        "photo_file": image,
        "video_file": video,
        "auto_enhance": False,
    }


@pytest.mark.asyncio
async def test_parse_ar_content_data_rejects_bad_legacy_json():
    from app.api.routes import ar_content

    request = _FakeRequest({"content_metadata": "{bad json}"})

    with pytest.raises(HTTPException) as exc_info:
        await ar_content.parse_ar_content_data(request)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid content_metadata JSON format"


@pytest.mark.asyncio
async def test_get_ar_marker_rejects_invalid_uuid():
    from app.api.routes import ar_content

    with pytest.raises(HTTPException) as exc_info:
        await ar_content.get_ar_marker("not-a-uuid", _FakeDb())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid unique_id format"


@pytest.mark.asyncio
async def test_get_ar_image_redirects_to_photo_url():
    from app.api.routes import ar_content

    unique_id = str(uuid4())
    content = SimpleNamespace(photo_url="https://example.test/photo.jpg")
    db = _FakeDb(execute_result=content)

    response = await ar_content.get_ar_image(unique_id, db)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.test/photo.jpg"


@pytest.mark.asyncio
async def test_validate_marker_requires_existing_photo_path():
    from app.api.routes import ar_content

    content = SimpleNamespace(
        id=50,
        order_number="ORD-50",
        marker_path=None,
        photo_path=None,
        marker_url=None,
        marker_metadata=None,
    )
    db = _FakeDb(get_map={(ar_content.ARContent, 50): content})

    with pytest.raises(HTTPException) as exc_info:
        await ar_content.validate_marker(50, db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Marker (photo) not set. Please upload photo or regenerate media."


@pytest.mark.asyncio
async def test_validate_marker_reports_missing_file(monkeypatch):
    from app.api.routes import ar_content

    content = SimpleNamespace(
        id=51,
        order_number="ORD-51",
        marker_path="missing/marker.jpg",
        photo_path=None,
        marker_url="/storage/missing/marker.jpg",
        marker_metadata={},
    )
    db = _FakeDb(get_map={(ar_content.ARContent, 51): content})
    monkeypatch.setattr(ar_content.settings, "STORAGE_BASE_PATH", "e:/Project/ARV/.pytest-temp-storage")

    with pytest.raises(HTTPException) as exc_info:
        await ar_content.validate_marker(51, db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Marker image not found at missing/marker.jpg"


class _FakeRequest:
    def __init__(self, form_data):
        self._form_data = form_data

    async def form(self):
        return self._form_data


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, get_map=None, execute_result=None):
        self.get_map = get_map or {}
        self.execute_result = execute_result

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return _FakeScalarResult(self.execute_result)
