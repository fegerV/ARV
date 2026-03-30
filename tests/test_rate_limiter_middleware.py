from types import SimpleNamespace

import pytest

from app.middleware import rate_limiter as mod


@pytest.mark.asyncio
async def test_disconnect_guard_returns_empty_response_for_client_disconnect():
    request = SimpleNamespace(
        url=SimpleNamespace(path="/backups"),
        headers={"x-real-ip": "10.0.0.5"},
        client=SimpleNamespace(host="127.0.0.1"),
        is_disconnected=_async_return(True),
    )

    async def _call_next(_request):
        raise RuntimeError("No response returned.")

    response = await mod._call_next_with_disconnect_guard(request, _call_next)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_disconnect_guard_reraises_unrelated_runtime_error():
    request = SimpleNamespace(
        url=SimpleNamespace(path="/backups"),
        headers={},
        client=SimpleNamespace(host="127.0.0.1"),
        is_disconnected=_async_return(False),
    )

    async def _call_next(_request):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await mod._call_next_with_disconnect_guard(request, _call_next)


def _async_return(value):
    async def _inner():
        return value

    return _inner
