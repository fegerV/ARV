from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


def test_sanitise_payload_coerces_frontend_values():
    from app.api.routes.rotation import _sanitise_payload

    result = _sanitise_payload(
        {
            "id": 77,
            "default_video_id": "12",
            "no_repeat_days": "4",
            "notify_before_expiry_days": "9",
            "current_index": "2",
            "day_of_week": "5",
            "day_of_month": "10",
            "is_active": "false",
            "video_sequence": ["1", 2, None, "3"],
        }
    )

    assert "id" not in result
    assert result["default_video_id"] == 12
    assert result["no_repeat_days"] == 4
    assert result["notify_before_expiry_days"] == 9
    assert result["current_index"] == 2
    assert result["day_of_week"] == 5
    assert result["day_of_month"] == 10
    assert result["is_active"] is False
    assert result["video_sequence"] == [1, 2, 3]


def test_require_auth_rejects_missing_or_inactive_user():
    from app.api.routes.rotation import _require_auth

    with pytest.raises(HTTPException) as missing_user:
        _require_auth(None)
    assert missing_user.value.status_code == 401

    with pytest.raises(HTTPException) as inactive_user:
        _require_auth(SimpleNamespace(is_active=False))
    assert inactive_user.value.status_code == 401


@pytest.mark.asyncio
async def test_set_rotation_creates_schedule_with_sanitized_values():
    from app.api.routes import rotation

    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(None)])

    result = await rotation.set_rotation(
        41,
        {
            "rotation_type": "fixed",
            "default_video_id": "12",
            "video_sequence": ["5", "7"],
            "is_active": "false",
        },
        current_user=SimpleNamespace(is_active=True),
        db=db,
    )

    assert result == {"id": 301, "status": "created"}
    assert db.added is not None
    assert db.added.ar_content_id == 41
    assert db.added.default_video_id == 12
    assert db.added.video_sequence == [5, 7]
    assert db.added.is_active is False
    assert db.commit_calls == 1
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_set_rotation_updates_existing_schedule():
    from app.api.routes import rotation

    existing = SimpleNamespace(id=8, rotation_type="fixed", current_index=0, is_active=True)
    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(existing)])

    result = await rotation.set_rotation(
        41,
        {"current_index": "4", "is_active": "false", "ignored_field": "x"},
        current_user=SimpleNamespace(is_active=True),
        db=db,
    )

    assert result == {"id": 8, "status": "updated"}
    assert existing.current_index == 4
    assert existing.is_active is False
    assert not hasattr(existing, "ignored_field")


@pytest.mark.asyncio
async def test_update_rotation_requires_existing_schedule():
    from app.api.routes import rotation

    with pytest.raises(HTTPException) as exc_info:
        await rotation.update_rotation(
            99,
            {"rotation_type": "random"},
            current_user=SimpleNamespace(is_active=True),
            db=_FakeDb(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Rotation schedule not found"


@pytest.mark.asyncio
async def test_delete_rotation_deletes_existing_schedule():
    from app.api.routes import rotation

    sched = SimpleNamespace(id=12)
    db = _FakeDb(get_map={(rotation.VideoRotationSchedule, 12): sched})

    result = await rotation.delete_rotation(12, current_user=SimpleNamespace(is_active=True), db=db)

    assert result == {"status": "deleted"}
    assert db.deleted is sched
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_set_rotation_sequence_validates_non_empty_list():
    from app.api.routes import rotation

    with pytest.raises(HTTPException) as exc_info:
        await rotation.set_rotation_sequence(
            5,
            {"video_sequence": []},
            current_user=SimpleNamespace(is_active=True),
            db=_FakeDb(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "video_sequence must be a non-empty array of video IDs"


@pytest.mark.asyncio
async def test_set_rotation_sequence_creates_schedule_when_missing():
    from app.api.routes import rotation

    db = _FakeDb(execute_results=[_FakeScalarsResult([])])

    result = await rotation.set_rotation_sequence(
        77,
        {"video_sequence": ["3", "4"]},
        current_user=SimpleNamespace(is_active=True),
        db=db,
    )

    assert result == {"status": "sequence_set", "count": 2}
    assert db.added is not None
    assert db.added.ar_content_id == 77
    assert db.added.rotation_type == "daily_cycle"
    assert db.added.video_sequence == [3, 4]
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_rotation_calendar_rejects_invalid_month():
    from app.api.routes import rotation

    with pytest.raises(HTTPException) as exc_info:
        await rotation.rotation_calendar(
            5,
            month="2025-13",
            current_user=SimpleNamespace(is_active=True),
            db=_FakeDb(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "month must be YYYY-MM"


@pytest.mark.asyncio
async def test_rotation_calendar_prefers_scheduled_video_then_sequence():
    from app.api.routes import rotation

    january_first = datetime(2025, 1, 1)
    january_second = datetime(2025, 1, 2)
    january_third = datetime(2025, 1, 3)
    vids = [
        SimpleNamespace(
            id=10,
            title="Promo",
            rotation_order=1,
            schedule_start=january_second,
            schedule_end=january_second,
        ),
        SimpleNamespace(
            id=20,
            title="Loop A",
            rotation_order=2,
            schedule_start=None,
            schedule_end=None,
        ),
        SimpleNamespace(
            id=30,
            title="Loop B",
            rotation_order=3,
            schedule_start=None,
            schedule_end=None,
        ),
    ]
    sched = SimpleNamespace(video_sequence=[20, 30])
    db = _FakeDb(
        execute_results=[
            _FakeScalarsResult(vids),
            _FakeScalarsResult([sched]),
        ]
    )

    result = await rotation.rotation_calendar(
        5,
        month="2025-01",
        current_user=SimpleNamespace(is_active=True),
        db=db,
    )

    assert result["month"] == "2025-01"
    assert len(result["days"]) == 31
    assert result["days"][0] == {"date": "2025-01-01", "video_id": 20, "title": "Loop A"}
    assert result["days"][1] == {"date": "2025-01-02", "video_id": 10, "title": "Promo"}
    assert result["days"][2] == {"date": "2025-01-03", "video_id": 20, "title": "Loop A"}


class _FakeScalarOneOrNoneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)

    def first(self):
        return self._values[0] if self._values else None


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeDb:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.added = None
        self.deleted = None
        self.commit_calls = 0
        self.refresh_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 301
        self.added = obj

    async def flush(self):
        return None

    async def delete(self, obj):
        self.deleted = obj

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1
