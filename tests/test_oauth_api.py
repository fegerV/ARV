from types import SimpleNamespace

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException


@pytest.mark.asyncio
async def test_initiate_yandex_oauth_requires_redirect_uri(monkeypatch):
    from app.api.routes import oauth

    monkeypatch.setattr(oauth, "settings", SimpleNamespace(
        YANDEX_OAUTH_REDIRECT_URI="",
        YANDEX_OAUTH_CLIENT_ID="client-id",
    ))

    with pytest.raises(HTTPException) as exc_info:
        await oauth.initiate_yandex_oauth("Vertex")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "YANDEX_OAUTH_REDIRECT_URI not configured"


@pytest.mark.asyncio
async def test_initiate_yandex_oauth_redirects_with_state(monkeypatch):
    from app.api.routes import oauth

    monkeypatch.setattr(oauth, "settings", SimpleNamespace(
        YANDEX_OAUTH_REDIRECT_URI="https://admin.example.com/oauth/callback",
        YANDEX_OAUTH_CLIENT_ID="client-id",
    ))

    async def _fake_create_state(connection_name):
        assert connection_name == "Vertex"
        return "state-123"

    monkeypatch.setattr(oauth.oauth_state_store, "create_state", _fake_create_state)

    response = await oauth.initiate_yandex_oauth("Vertex")

    assert response.headers["location"].startswith("https://oauth.yandex.ru/authorize?")
    assert "client_id=client-id" in response.headers["location"]
    assert "state=state-123" in response.headers["location"]


@pytest.mark.asyncio
async def test_yandex_oauth_callback_rejects_invalid_state():
    from app.api.routes import oauth

    background_tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as exc_info:
        await oauth.yandex_oauth_callback(
            background_tasks=background_tasks,
            code="code-1",
            state="missing-state",
            db=_FakeDb(),
        )

    assert exc_info.value.status_code == 400
    assert "Invalid or expired state parameter" in exc_info.value.detail


@pytest.mark.asyncio
async def test_yandex_oauth_callback_creates_connection_and_redirects(monkeypatch):
    from app.api.routes import oauth

    monkeypatch.setattr(oauth, "settings", SimpleNamespace(
        YANDEX_OAUTH_CLIENT_ID="client-id",
        YANDEX_OAUTH_CLIENT_SECRET="client-secret",
        ADMIN_FRONTEND_URL="https://admin.example.com",
    ))

    async def _fake_get_and_delete_state(state):
        assert state == "state-1"
        return {"connection_name": "Vertex Disk"}

    async def _fake_cleanup():
        return 1

    monkeypatch.setattr(oauth.oauth_state_store, "get_and_delete_state", _fake_get_and_delete_state)
    monkeypatch.setattr(oauth.oauth_state_store, "cleanup_expired_states", _fake_cleanup)
    monkeypatch.setattr(oauth.token_encryption, "encrypt_credentials", lambda payload: f"enc:{payload['oauth_token']}")
    monkeypatch.setattr(oauth.token_encryption, "is_encryption_available", lambda: True)

    responses = [
        _FakeResponse(200, {"access_token": "token-123", "refresh_token": "refresh-1", "expires_in": 3600, "token_type": "bearer"}),
        _FakeResponse(200, {"user": {"display_name": "Vertex"}, "total_space": 1000, "used_space": 250}),
    ]

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, data, headers):
            assert "oauth.yandex.ru/token" in url
            assert data["code"] == "code-1"
            return responses.pop(0)

        async def get(self, url, headers):
            assert "cloud-api.yandex.net/v1/disk/" in url
            assert headers["Authorization"] == "OAuth token-123"
            return responses.pop(0)

    monkeypatch.setattr(oauth.httpx, "AsyncClient", FakeAsyncClient)

    db = _FakeDb()
    background_tasks = BackgroundTasks()

    response = await oauth.yandex_oauth_callback(
        background_tasks=background_tasks,
        code="code-1",
        state="state-1",
        db=db,
    )

    assert db.added is not None
    assert db.added.name == "Vertex Disk"
    assert db.added.provider == "yandex_disk"
    assert db.added.base_path == "/"
    assert db.added.storage_metadata["credentials"] == "enc:token-123"
    assert db.added.storage_metadata["user_display_name"] == "Vertex"
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert response.headers["location"] == "https://admin.example.com/oauth/yandex/callback?success=true&connectionId=501"
    assert len(background_tasks.tasks) == 1


@pytest.mark.asyncio
async def test_yandex_oauth_callback_redirects_on_network_error(monkeypatch):
    from app.api.routes import oauth

    monkeypatch.setattr(oauth, "settings", SimpleNamespace(
        YANDEX_OAUTH_CLIENT_ID="client-id",
        YANDEX_OAUTH_CLIENT_SECRET="client-secret",
        ADMIN_FRONTEND_URL="https://admin.example.com",
    ))

    async def _fake_get_and_delete_state(_state):
        return {"connection_name": "Vertex Disk"}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, data, headers):
            raise httpx.RequestError("boom", request=httpx.Request("POST", url))

    monkeypatch.setattr(oauth.oauth_state_store, "get_and_delete_state", _fake_get_and_delete_state)
    monkeypatch.setattr(oauth.httpx, "AsyncClient", FakeAsyncClient)

    response = await oauth.yandex_oauth_callback(
        background_tasks=BackgroundTasks(),
        code="code-1",
        state="state-1",
        db=_FakeDb(),
    )

    assert response.headers["location"].startswith("https://admin.example.com/oauth/yandex/callback?success=false&error=")


def test_get_connection_credentials_prefers_storage_metadata(monkeypatch):
    from app.api.routes.oauth import _get_connection_credentials
    from app.api.routes import oauth

    monkeypatch.setattr(oauth.token_encryption, "decrypt_credentials", lambda value: {"oauth_token": f"decoded:{value}"})

    conn = SimpleNamespace(storage_metadata={"credentials": "enc-token"})

    assert _get_connection_credentials(conn) == {"oauth_token": "decoded:enc-token"}


@pytest.mark.asyncio
async def test_list_yandex_folders_returns_directory_payload(monkeypatch):
    from app.api.routes import oauth

    conn = SimpleNamespace(
        id=7,
        provider="yandex_disk",
        storage_metadata={"credentials": "enc-token"},
    )
    db = _FakeDb(get_map={(oauth.StorageConnection, 7): conn})

    monkeypatch.setattr(oauth.token_encryption, "decrypt_credentials", lambda value: {"oauth_token": "token-123"})

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params, headers):
            assert params == {"path": "/demo/folder", "limit": 100}
            assert headers["Authorization"] == "OAuth token-123"
            return _FakeResponse(
                200,
                {
                    "_embedded": {
                        "items": [
                            {"name": "Folder A", "path": "disk:/demo/folder/A", "type": "dir", "created": "c1", "modified": "m1"},
                            {"name": "file.jpg", "path": "disk:/demo/folder/file.jpg", "type": "file"},
                        ]
                    }
                },
            )

    monkeypatch.setattr(oauth.httpx, "AsyncClient", FakeAsyncClient)

    result = await oauth.list_yandex_folders(7, path="/demo/folder", db=db)

    assert result["current_path"] == "/demo/folder"
    assert result["parent_path"] == "/demo"
    assert result["has_parent"] is True
    assert result["folders"] == [
        {
            "name": "Folder A",
            "path": "disk:/demo/folder/A",
            "type": "dir",
            "created": "c1",
            "modified": "m1",
            "last_modified": "m1",
        }
    ]


@pytest.mark.asyncio
async def test_list_yandex_folders_requires_token(monkeypatch):
    from app.api.routes import oauth

    conn = SimpleNamespace(
        id=9,
        provider="yandex_disk",
        storage_metadata={},
    )
    db = _FakeDb(get_map={(oauth.StorageConnection, 9): conn})

    with pytest.raises(HTTPException) as exc_info:
        await oauth.list_yandex_folders(9, path="/", db=db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to access stored credentials. Please re-authenticate."


@pytest.mark.asyncio
async def test_create_yandex_folder_maps_conflict_error(monkeypatch):
    from app.api.routes import oauth

    conn = SimpleNamespace(
        id=10,
        provider="yandex_disk",
        storage_metadata={"credentials": "enc-token"},
    )
    db = _FakeDb(get_map={(oauth.StorageConnection, 10): conn})

    monkeypatch.setattr(oauth.token_encryption, "decrypt_credentials", lambda value: {"oauth_token": "token-123"})

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def put(self, url, params, headers):
            assert params == {"path": "/demo/new-folder"}
            return _FakeResponse(409, {})

    monkeypatch.setattr(oauth.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(HTTPException) as exc_info:
        await oauth.create_yandex_folder(10, folder_path="/demo/new-folder", db=db)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Folder already exists at this location."


class _FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self):
        return self._payload


class _FakeDb:
    def __init__(self, get_map=None):
        self.get_map = get_map or {}
        self.added = None
        self.commit_calls = 0
        self.refresh_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 501
        self.added = obj

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1
