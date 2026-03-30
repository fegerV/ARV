from app.utils import oauth_state as mod


import pytest


@pytest.mark.asyncio
async def test_create_get_delete_and_one_time_use(monkeypatch):
    store = mod.OAuthStateStore()
    monkeypatch.setattr(mod.secrets, "token_urlsafe", lambda size: "fixed-state-token")
    monkeypatch.setattr(mod.time, "time", lambda: 1000.0)

    state = await store.create_state("demo-connection", folder="root", company_id=7)
    assert state == "fixed-state-token"
    assert store._memory_store[state]["connection_name"] == "demo-connection"
    assert store._memory_store[state]["metadata"] == {"folder": "root", "company_id": 7}

    payload = await store.get_and_delete_state(state)
    assert payload == {
        "connection_name": "demo-connection",
        "timestamp": 1000.0,
        "metadata": {"folder": "root", "company_id": 7},
    }
    assert await store.get_and_delete_state(state) is None


@pytest.mark.asyncio
async def test_cleanup_expired_states_and_is_state_valid(monkeypatch):
    store = mod.OAuthStateStore()
    store._ttl_seconds = 300
    store._memory_store = {
        "fresh": {"connection_name": "a", "timestamp": 1000.0, "metadata": {}},
        "edge": {"connection_name": "b", "timestamp": 900.0, "metadata": {}},
        "expired": {"connection_name": "c", "timestamp": 600.0, "metadata": {}},
    }

    monkeypatch.setattr(mod.time, "time", lambda: 1200.0)
    assert await store.is_state_valid("fresh") is True
    assert await store.is_state_valid("edge") is True
    assert await store.is_state_valid("expired") is False
    assert await store.is_state_valid("missing") is False

    cleaned = await store.cleanup_expired_states()
    assert cleaned == 1
    assert set(store._memory_store) == {"fresh", "edge"}
