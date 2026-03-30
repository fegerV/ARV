from types import SimpleNamespace

import pytest

from app.html.routes import analytics as analytics_route
from app.html.routes import logs as logs_route


@pytest.mark.asyncio
async def test_get_analytics_data_uses_cache(monkeypatch):
    calls = {"count": 0}

    async def _fake_build(_db, period=30):
        calls["count"] += 1
        return {"period": period, "total_views": calls["count"], "browser_stats": []}

    monkeypatch.setattr(analytics_route, "_build_analytics_data", _fake_build)
    monkeypatch.setattr(analytics_route, "_ANALYTICS_CACHE", {})
    monkeypatch.setattr(analytics_route.time, "monotonic", lambda: 100.0)

    first = await analytics_route.get_analytics_data(SimpleNamespace(), period=30)
    second = await analytics_route.get_analytics_data(SimpleNamespace(), period=30)

    assert calls["count"] == 1
    assert first == second


def test_summarize_log_entries_counts_levels():
    entries = [
        {"text": "boom", "level": "error"},
        {"text": "warn", "level": "warning"},
        {"text": "info", "level": "info"},
        {"text": "debug", "level": "debug"},
        {"text": "other", "level": "default"},
    ]

    assert logs_route.summarize_log_entries(entries) == {
        "error": 1,
        "warning": 1,
        "info": 1,
        "debug": 1,
        "default": 1,
        "total": 5,
    }
