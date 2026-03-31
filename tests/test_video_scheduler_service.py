import importlib
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


def test_ensure_utc_and_status_helpers():
    video_scheduler = _video_scheduler_module()
    now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
    naive = datetime(2026, 3, 29, 12, 0)
    video = SimpleNamespace(is_active=True, subscription_end=now + timedelta(days=10))

    ensured = video_scheduler._ensure_utc(naive)

    assert ensured.tzinfo == timezone.utc
    assert video_scheduler._ensure_utc(None) is None
    assert video_scheduler.compute_video_status(SimpleNamespace(is_active=False, subscription_end=None), now) == "inactive"
    assert video_scheduler.compute_video_status(SimpleNamespace(is_active=True, subscription_end=now - timedelta(days=1)), now) == "expired"
    assert video_scheduler.compute_video_status(SimpleNamespace(is_active=True, subscription_end=now + timedelta(days=3)), now) == "expiring"
    assert video_scheduler.compute_video_status(video, now) == "active"
    assert video_scheduler.compute_days_remaining(SimpleNamespace(subscription_end=None), now) is None
    assert video_scheduler.compute_days_remaining(SimpleNamespace(subscription_end=now - timedelta(days=1)), now) == 0
    assert video_scheduler.compute_days_remaining(video, now) == 10
    assert video_scheduler.compute_video_status(video, naive) == "active"
    assert video_scheduler.compute_days_remaining(video, naive) == 10


@pytest.mark.asyncio
async def test_schedule_query_helpers_return_scalars():
    video_scheduler = _video_scheduler_module()
    schedule = SimpleNamespace(id=5)
    video_a = SimpleNamespace(id=1)
    video_b = SimpleNamespace(id=2)
    db = _FakeDb(
        execute_results=[
            _FakeExecuteResult(one=schedule),
            _FakeExecuteResult(many=[video_a, video_b]),
        ]
    )
    now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)

    active_schedule = await video_scheduler.get_active_video_schedule(7, db, now)
    active_videos = await video_scheduler.get_videos_with_active_schedules(3, db, now)

    assert active_schedule is schedule
    assert active_videos == [video_a, video_b]


@pytest.mark.asyncio
async def test_check_date_rules_supports_exact_recurring_invalid_and_expired(monkeypatch):
    video_scheduler = _video_scheduler_module()
    now = datetime.now(timezone.utc)
    recurring_video = SimpleNamespace(id=1, is_active=True, subscription_end=now + timedelta(days=20))
    exact_video = SimpleNamespace(id=2, is_active=True, subscription_end=None)
    expired_video = SimpleNamespace(id=3, is_active=True, subscription_end=now - timedelta(days=1))
    db = _FakeDb(
        get_map={
            ("video", 1): recurring_video,
            ("video", 2): exact_video,
            ("video", 3): expired_video,
        }
    )
    monkeypatch.setattr(video_scheduler, "Video", "video")

    recurring_rule = SimpleNamespace(date_rules=[{"date": "2020-12-31", "recurring": True, "video_id": 1}])
    exact_rule = SimpleNamespace(date_rules=[{"date": "2026-03-29T00:00:00", "video_id": 2}])
    invalid_rule = SimpleNamespace(date_rules=[{"date": "not-a-date", "video_id": 2}, {"date": "2026-03-29", "video_id": 3}])

    recurring = await video_scheduler.check_date_rules(recurring_rule, date(2026, 12, 31), db)
    exact = await video_scheduler.check_date_rules(exact_rule, date(2026, 3, 29), db)
    invalid = await video_scheduler.check_date_rules(invalid_rule, date(2026, 3, 29), db)

    assert recurring is recurring_video
    assert exact is exact_video
    assert invalid is None


@pytest.mark.asyncio
async def test_cycle_video_helpers_select_expected_items(monkeypatch):
    video_scheduler = _video_scheduler_module()
    now = datetime.now(timezone.utc)
    monday_video = SimpleNamespace(id=10, is_active=True, subscription_end=now + timedelta(days=10))
    sunday_video = SimpleNamespace(id=11, is_active=True, subscription_end=now + timedelta(days=10))
    expired_video = SimpleNamespace(id=12, is_active=True, subscription_end=now - timedelta(days=1))
    db = _FakeDb(
        get_map={
            ("video", 10): monday_video,
            ("video", 11): sunday_video,
            ("video", 12): expired_video,
        }
    )
    monkeypatch.setattr(video_scheduler, "Video", "video")
    monkeypatch.setattr(video_scheduler.random, "choices", lambda videos, weights, k: [videos[1]])

    daily_rule = SimpleNamespace(video_sequence=[12, 10], random_seed="seed")
    weekly_rule = SimpleNamespace(video_sequence=[10, 11])
    random_rule = SimpleNamespace(video_sequence=[10, 11], random_seed="seed")

    daily = await video_scheduler.get_daily_cycle_video(daily_rule, date(2026, 1, 2), db)
    weekly = await video_scheduler.get_weekly_cycle_video(weekly_rule, date(2026, 3, 29), db)  # Sunday
    random_video = await video_scheduler.get_random_daily_video(random_rule, date(2026, 3, 29), db)
    empty_random = await video_scheduler.get_random_daily_video(SimpleNamespace(video_sequence=[]), date(2026, 3, 29), db)

    assert daily is monday_video
    assert weekly is monday_video
    assert random_video is sunday_video
    assert empty_random is None


@pytest.mark.asyncio
async def test_get_rotation_rule_and_default_video_paths(monkeypatch):
    video_scheduler = _video_scheduler_module()
    now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
    rule = SimpleNamespace(id=8)
    active_default = SimpleNamespace(id=20, is_active=True, subscription_end=now + timedelta(days=5))
    expired_default = SimpleNamespace(id=21, is_active=True, subscription_end=now - timedelta(days=1))
    fallback_video = SimpleNamespace(id=22, is_active=True, subscription_end=now + timedelta(days=5))
    db = _FakeDb(
        get_map={
            (video_scheduler.Video, 20): active_default,
            (video_scheduler.Video, 21): expired_default,
        },
        execute_results=[
            _FakeExecuteResult(one=rule),
            _FakeExecuteResult(many=[expired_default, fallback_video]),
        ],
    )

    found_rule = await video_scheduler.get_rotation_rule(5, db)
    direct = await video_scheduler.get_default_video(SimpleNamespace(id=1, active_video_id=20), db, now)
    fallback = await video_scheduler.get_default_video(SimpleNamespace(id=1, active_video_id=21), db, now)

    assert found_rule is rule
    assert direct is active_default
    assert fallback is fallback_video


@pytest.mark.asyncio
async def test_get_next_rotation_video_supports_rotation_types(monkeypatch):
    video_scheduler = _video_scheduler_module()
    now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
    sequential = [
        SimpleNamespace(id=1, is_active=True, subscription_end=now + timedelta(days=10), rotation_type="sequential"),
        SimpleNamespace(id=2, is_active=True, subscription_end=now + timedelta(days=10), rotation_type="sequential"),
    ]
    cyclic = [
        SimpleNamespace(id=3, is_active=True, subscription_end=now + timedelta(days=10), rotation_type="cyclic"),
        SimpleNamespace(id=4, is_active=True, subscription_end=now + timedelta(days=10), rotation_type="cyclic"),
    ]
    none_type = [SimpleNamespace(id=5, is_active=True, subscription_end=None, rotation_type="none")]
    unknown = [
        SimpleNamespace(id=6, is_active=True, subscription_end=now + timedelta(days=10), rotation_type="mystery"),
        SimpleNamespace(id=7, is_active=True, subscription_end=now + timedelta(days=10), rotation_type="mystery"),
    ]

    db = _FakeDb(
        execute_results=[
            _FakeExecuteResult(many=sequential),
            _FakeExecuteResult(many=cyclic),
            _FakeExecuteResult(many=none_type),
            _FakeExecuteResult(many=unknown),
            _FakeExecuteResult(many=[]),
        ]
    )

    seq_video = await video_scheduler.get_next_rotation_video(SimpleNamespace(id=1, rotation_state=1), db, now)
    cyclic_video = await video_scheduler.get_next_rotation_video(SimpleNamespace(id=1, rotation_state=3), db, now)
    none_video = await video_scheduler.get_next_rotation_video(SimpleNamespace(id=1, rotation_state=0), db, now)
    unknown_video = await video_scheduler.get_next_rotation_video(SimpleNamespace(id=1, rotation_state=0), db, now)
    no_video = await video_scheduler.get_next_rotation_video(SimpleNamespace(id=1, rotation_state=0), db, now)

    assert seq_video is sequential[1]
    assert cyclic_video is cyclic[1]
    assert none_video is none_type[0]
    assert unknown_video is unknown[0]
    assert no_video is None


@pytest.mark.asyncio
async def test_get_active_video_returns_none_when_ar_content_missing():
    video_scheduler = _video_scheduler_module()
    db = _FakeDb(get_map={(video_scheduler.ARContent, 1): None})

    result = await video_scheduler.get_active_video(1, db)

    assert result is None


@pytest.mark.asyncio
async def test_get_active_video_prefers_date_rule(monkeypatch):
    video_scheduler = _video_scheduler_module()
    ar_content = SimpleNamespace(id=1, active_video_id=None)
    video = SimpleNamespace(id=5, subscription_end=None)
    db = _FakeDb(get_map={(video_scheduler.ARContent, 1): ar_content})
    monkeypatch.setattr(video_scheduler, "get_rotation_rule", _async_return(SimpleNamespace(date_rules=[{"date": "2026-03-29"}])))
    monkeypatch.setattr(video_scheduler, "check_date_rules", _async_return(video))
    monkeypatch.setattr(video_scheduler, "compute_days_remaining", lambda _video, _now: 99)

    result = await video_scheduler.get_active_video(1, db, override_date=date(2026, 3, 29))

    assert result == {
        "video": video,
        "source": "date_rule",
        "schedule_id": None,
        "expires_in": 99,
    }


@pytest.mark.asyncio
async def test_get_active_video_prefers_schedule_then_rotation_then_active_default(monkeypatch):
    video_scheduler = _video_scheduler_module()
    now = datetime.now(timezone.utc)
    ar_content = SimpleNamespace(id=1, active_video_id=20)
    schedule_video = SimpleNamespace(id=11)
    rotation_video = SimpleNamespace(id=12, is_active=True, subscription_end=now + timedelta(days=8))
    active_default = SimpleNamespace(id=20, is_active=True, subscription_end=now + timedelta(days=3))
    db_schedule = _FakeDb(get_map={(video_scheduler.ARContent, 1): ar_content})
    db_rotation = _FakeDb(get_map={(video_scheduler.ARContent, 1): ar_content, (video_scheduler.Video, 30): rotation_video})
    db_default = _FakeDb(get_map={(video_scheduler.ARContent, 1): ar_content, (video_scheduler.Video, 20): active_default})
    monkeypatch.setattr(video_scheduler, "compute_days_remaining", lambda video, _now: {12: 8, 20: 3}[video.id])

    monkeypatch.setattr(video_scheduler, "get_rotation_rule", _async_return(None))
    monkeypatch.setattr(video_scheduler, "get_videos_with_active_schedules", _async_return([schedule_video]))
    monkeypatch.setattr(video_scheduler, "get_active_video_schedule", _async_return(SimpleNamespace(id=7)))
    schedule_result = await video_scheduler.get_active_video(1, db_schedule)

    monkeypatch.setattr(video_scheduler, "get_rotation_rule", _async_return(SimpleNamespace(rotation_type="fixed", default_video_id=30, date_rules=[])))
    monkeypatch.setattr(video_scheduler, "get_videos_with_active_schedules", _async_return([]))
    rotation_result = await video_scheduler.get_active_video(1, db_rotation)

    monkeypatch.setattr(video_scheduler, "get_rotation_rule", _async_return(None))
    monkeypatch.setattr(video_scheduler, "get_videos_with_active_schedules", _async_return([]))
    monkeypatch.setattr(video_scheduler, "get_next_rotation_video", _async_return(None))
    default_result = await video_scheduler.get_active_video(1, db_default)

    assert schedule_result["source"] == "schedule"
    assert schedule_result["schedule_id"] == 7
    assert rotation_result["source"] == "rotation_rule"
    assert rotation_result["video"] is rotation_video
    assert default_result["source"] == "active_default"
    assert default_result["video"] is active_default
    assert default_result["expires_in"] == 3


@pytest.mark.asyncio
async def test_get_active_video_falls_back_to_rotation_and_any_video(monkeypatch):
    video_scheduler = _video_scheduler_module()
    now = datetime.now(timezone.utc)
    ar_content = SimpleNamespace(id=1, active_video_id=None)
    rotation_video = SimpleNamespace(id=40, subscription_end=now + timedelta(days=6))
    fallback_video = SimpleNamespace(id=41, subscription_end=now + timedelta(days=4))
    db_rotation = _FakeDb(get_map={(video_scheduler.ARContent, 1): ar_content})
    db_fallback = _FakeDb(
        get_map={(video_scheduler.ARContent, 1): ar_content},
        execute_results=[_FakeExecuteResult(one=fallback_video)],
    )
    monkeypatch.setattr(video_scheduler, "compute_days_remaining", lambda video, _now: {40: 6, 41: 4}[video.id])

    monkeypatch.setattr(video_scheduler, "get_rotation_rule", _async_return(None))
    monkeypatch.setattr(video_scheduler, "get_videos_with_active_schedules", _async_return([]))
    monkeypatch.setattr(video_scheduler, "get_next_rotation_video", _async_return(rotation_video))
    rotation_result = await video_scheduler.get_active_video(1, db_rotation)

    monkeypatch.setattr(video_scheduler, "get_rotation_rule", _async_return(None))
    monkeypatch.setattr(video_scheduler, "get_videos_with_active_schedules", _async_return([]))
    monkeypatch.setattr(video_scheduler, "get_next_rotation_video", _async_return(None))
    fallback_result = await video_scheduler.get_active_video(1, db_fallback)

    assert rotation_result["source"] == "rotation"
    assert rotation_result["expires_in"] == 6
    assert fallback_result["source"] == "fallback"
    assert fallback_result["video"] is fallback_video
    assert fallback_result["expires_in"] == 4


@pytest.mark.asyncio
async def test_update_rotation_state_handles_no_videos_sequential_and_cyclic():
    video_scheduler = _video_scheduler_module()
    no_videos_db = _FakeDb(execute_results=[_FakeExecuteResult(many=[])])
    sequential_db = _FakeDb(execute_results=[_FakeExecuteResult(many=[
        SimpleNamespace(rotation_type="sequential"),
        SimpleNamespace(rotation_type="sequential"),
    ])])
    cyclic_db = _FakeDb(execute_results=[_FakeExecuteResult(many=[
        SimpleNamespace(rotation_type="cyclic"),
        SimpleNamespace(rotation_type="cyclic"),
    ])])

    ar_content_no_videos = SimpleNamespace(id=1, rotation_state=0)
    ar_content_sequential = SimpleNamespace(id=2, rotation_state=0)
    ar_content_cyclic = SimpleNamespace(id=3, rotation_state=2)

    await video_scheduler.update_rotation_state(ar_content_no_videos, no_videos_db)
    await video_scheduler.update_rotation_state(ar_content_sequential, sequential_db)
    await video_scheduler.update_rotation_state(ar_content_cyclic, cyclic_db)

    assert no_videos_db.commit_calls == 0
    assert ar_content_sequential.rotation_state == 1
    assert sequential_db.commit_calls == 1
    assert ar_content_cyclic.rotation_state == 3
    assert cyclic_db.commit_calls == 1


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeExecuteResult:
    def __init__(self, many=None, one=None):
        self._many = list(many or [])
        self._one = one

    def scalars(self):
        return _FakeScalars(self._many)

    def scalar_one_or_none(self):
        return self._one


class _FakeDb:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.commit_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    async def commit(self):
        self.commit_calls += 1


def _video_scheduler_module():
    return importlib.import_module("app.services.video_scheduler")


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
