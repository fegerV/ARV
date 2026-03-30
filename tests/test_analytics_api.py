from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_analytics_overview_uses_distinct_fallback_when_needed():
    from app.api.routes import analytics

    db = _FakeDb(
        execute_results=[
            _FakeScalarResult(120),
            RuntimeError("sqlite distinct unsupported"),
            _FakeScalarResult(45),
            _FakeScalarResult(7),
            _FakeScalarResult(3),
            _FakeScalarResult(11),
        ]
    )

    result = await analytics.analytics_overview(db)

    assert result == {
        "total_views": 120,
        "unique_sessions": 45,
        "active_content": 7,
        "storage_used_gb": 0,
        "active_companies": 3,
        "active_projects": 11,
        "revenue": "$0.00",
        "uptime": "99.9%",
    }


@pytest.mark.asyncio
async def test_analytics_summary_delegates_to_overview():
    from app.api.routes import analytics

    db = _FakeDb(
        execute_results=[
            _FakeScalarResult(1),
            _FakeScalarResult(1),
            _FakeScalarResult(1),
            _FakeScalarResult(1),
            _FakeScalarResult(1),
        ]
    )

    result = await analytics.analytics_summary(db)

    assert result["total_views"] == 1
    assert result["unique_sessions"] == 1


@pytest.mark.asyncio
async def test_company_and_project_analytics_return_30_day_views():
    from app.api.routes import analytics

    company_db = _FakeDb(execute_results=[_FakeScalarResult(8)])
    project_db = _FakeDb(execute_results=[_FakeScalarResult(5)])

    company_result = await analytics.analytics_company(4, company_db)
    project_result = await analytics.analytics_project(9, project_db)

    assert company_result == {"company_id": 4, "views_30_days": 8}
    assert project_result == {"project_id": 9, "views_30_days": 5}


@pytest.mark.asyncio
async def test_analytics_content_returns_30_day_views():
    from app.api.routes import analytics

    db = _FakeDb(execute_results=[_FakeScalarResult(12)])

    result = await analytics.analytics_content(77, db)

    assert result == {"ar_content_id": 77, "views_30_days": 12}


@pytest.mark.asyncio
async def test_analytics_content_alias_delegates_to_same_payload():
    from app.api.routes import analytics

    db = _FakeDb(execute_results=[_FakeScalarResult(9)])

    result = await analytics.analytics_content_alias(21, db)

    assert result == {"ar_content_id": 21, "views_30_days": 9}


@pytest.mark.asyncio
async def test_track_ar_session_requires_valid_uuid_session_id():
    from app.api.routes import analytics

    payload = {"ar_content_unique_id": str(uuid4()), "session_id": "not-a-uuid"}

    with pytest.raises(HTTPException) as exc_info:
        await analytics.track_ar_session(payload, _FakeDb())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "session_id must be UUID"


@pytest.mark.asyncio
async def test_track_ar_session_persists_session_for_found_content():
    from app.api.routes import analytics

    unique_id = str(uuid4())
    session_id = str(uuid4())
    ar_content = SimpleNamespace(id=15, project_id=3, company_id=2)
    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(ar_content)])

    result = await analytics.track_ar_session(
        {
            "ar_content_unique_id": unique_id,
            "session_id": session_id,
            "device_type": "mobile",
            "video_played": True,
        },
        db,
    )

    assert result == {"status": "tracked", "session_id": session_id}
    assert db.added is not None
    assert db.added.ar_content_id == 15
    assert db.added.project_id == 3
    assert db.added.company_id == 2
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_mobile_session_start_is_idempotent_for_existing_session():
    from app.api.routes import analytics

    unique_id = str(uuid4())
    session_id = str(uuid4())
    ar_content = SimpleNamespace(id=15, project_id=3, company_id=2)
    existing_session = SimpleNamespace(session_id=session_id)
    db = _FakeDb(
        execute_results=[
            _FakeScalarOneOrNoneResult(ar_content),
            _FakeScalarOneOrNoneResult(existing_session),
        ]
    )

    result = await analytics.mobile_session_start(
        {"ar_content_unique_id": unique_id, "session_id": session_id},
        db,
    )

    assert result == {"status": "exists", "session_id": session_id}
    assert db.added is None
    assert db.commit_calls == 0


@pytest.mark.asyncio
async def test_mobile_analytics_update_updates_existing_session():
    from app.api.routes import analytics

    session_id = str(uuid4())
    session = SimpleNamespace(duration_seconds=None, tracking_quality=None, video_played=False)
    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(session)])

    result = await analytics.mobile_analytics_update(
        {
            "session_id": session_id,
            "duration_seconds": 42,
            "tracking_quality": "good",
            "video_played": True,
        },
        db,
    )

    assert result == {"status": "updated", "session_id": session_id}
    assert session.duration_seconds == 42
    assert session.tracking_quality == "good"
    assert session.video_played is True
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_ar_diagnostic_event_returns_ok():
    from app.api.routes import analytics

    result = await analytics.ar_diagnostic_event({"event": "mindar_start", "duration_ms": 1200})

    assert result == {"status": "ok"}


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeScalarOneOrNoneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = None
        self.commit_calls = 0

    async def execute(self, _stmt):
        result = self.execute_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def add(self, obj):
        self.added = obj

    async def commit(self):
        self.commit_calls += 1
