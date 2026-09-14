import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.storage import StorageConnectionCreate


def _super_admin(user_id: int = 1) -> SimpleNamespace:
    """Stand-in for the ``current_user`` dependency.

    FastAPI injects this at the HTTP layer, so a direct handler call has to
    pass it explicitly. Storage administration is super-admin only
    (ARV-001), so the fake must carry ``is_super_admin=True``.
    """
    return SimpleNamespace(id=user_id, is_super_admin=True)


@pytest.mark.asyncio
async def test_create_connection_persists_local_disk_connection():
    from app.api.routes import storage

    payload = StorageConnectionCreate(name="Local", base_path="E:/storage", is_default=True)
    db = _FakeDb()
    # FastAPI injects Request at the HTTP layer; a direct handler call must pass it.
    request = SimpleNamespace(headers={})

    result = await storage.create_connection(payload, request, db, current_user=_super_admin())

    assert db.added is not None
    assert db.added.name == "Local"
    assert db.added.provider == "local_disk"
    assert db.added.base_path == "E:/storage"
    assert db.added.is_default is True
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert result is db.added


@pytest.mark.asyncio
async def test_create_connection_rejects_non_super_admin():
    """ARV-001: storage administration must stay super-admin only."""
    from app.api.routes import storage

    payload = StorageConnectionCreate(name="Local", base_path="E:/storage", is_default=False)
    db = _FakeDb()
    request = SimpleNamespace(headers={})
    plain_user = SimpleNamespace(id=42, is_super_admin=False)

    with pytest.raises(HTTPException) as denied:
        await storage.create_connection(payload, request, db, current_user=plain_user)

    assert denied.value.status_code == 403
    assert db.added is None


@pytest.mark.asyncio
async def test_test_connection_reports_missing_base_path():
    from app.api.routes import storage

    # A path that is guaranteed not to exist on this machine.
    missing = Path(tempfile.gettempdir()) / f"arv-missing-{uuid4().hex}"
    conn = SimpleNamespace(
        id=5,
        base_path=str(missing),
        last_tested_at=None,
        test_status=None,
        test_error=None,
    )
    db = _FakeDb(get_map={(storage.StorageConnection, 5): conn})
    request = SimpleNamespace(headers={})

    result = await storage.test_connection(5, request, db, current_user=_super_admin())

    assert result["status"] == "error"
    assert "does not exist" in result["message"]
    assert conn.test_status == "error"
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_test_connection_reports_success_for_writable_dir():
    from app.api.routes import storage

    temp_dir = _make_workspace_temp_dir()
    conn = SimpleNamespace(
        id=6,
        base_path=str(temp_dir),
        last_tested_at=None,
        test_status=None,
        test_error=None,
    )
    db = _FakeDb(get_map={(storage.StorageConnection, 6): conn})
    request = SimpleNamespace(headers={})

    try:
        result = await storage.test_connection(6, request, db, current_user=_super_admin())
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    assert result["status"] == "success"
    assert result["writable"] is True
    assert conn.test_status == "success"
    assert conn.test_error is None


@pytest.mark.asyncio
async def test_get_storage_stats_uses_provider_stats(monkeypatch):
    from app.api.routes import storage

    conn = SimpleNamespace(id=7)
    db = _FakeDb(get_map={(storage.StorageConnection, 7): conn})

    class FakeProvider:
        async def get_usage_stats(self, path):
            assert path == "demo"
            return {
                "total_files": 3,
                "total_size_bytes": 2048,
                "total_size_mb": 2.0,
                "base_path": "demo",
            }

    # The factory was renamed to ``get_storage_provider`` in the storage
    # provider refactor; the old name no longer exists on the module.
    monkeypatch.setattr(storage, "get_storage_provider", lambda: FakeProvider())

    request = SimpleNamespace(headers={})
    result = await storage.get_storage_stats(7, request, path="demo", db=db, current_user=_super_admin())

    assert result.total_files == 3
    assert result.total_size_bytes == 2048
    assert result.base_path == "demo"


@pytest.mark.asyncio
async def test_set_company_storage_updates_company_fields():
    from app.api.routes import storage

    company = SimpleNamespace(id=9, storage_connection_id=None, storage_path=None)
    db = _FakeDb(get_map={(storage.Company, 9): company})

    request = SimpleNamespace(headers={})
    result = await storage.set_company_storage(
        9,
        request,
        storage_connection_id=12,
        storage_path="/mnt/data",
        company=company,
        db=db,
        current_user=_super_admin(),
    )

    assert company.storage_connection_id == 12
    assert company.storage_path == "/mnt/data"
    assert db.commit_calls == 1
    assert result == {"status": "updated"}


@pytest.mark.asyncio
async def test_list_storage_connections_returns_safe_payload():
    from app.api.routes import storage

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conn = SimpleNamespace(
        id=1,
        name="Local",
        provider="local_disk",
        is_active=True,
        is_default=False,
        base_path="E:/storage",
        test_status="success",
        last_tested_at=now,
        created_at=now,
        updated_at=now,
        storage_metadata={"a": 1},
    )
    db = _FakeDb(execute_results=[_FakeScalarsResult([conn])])

    request = SimpleNamespace(headers={})
    result = await storage.list_storage_connections(
        request, is_active=True, db=db, current_user=_super_admin()
    )

    assert result == [
        {
            "id": 1,
            "name": "Local",
            "provider": "local_disk",
            "is_active": True,
            "is_default": False,
            "base_path": "E:/storage",
            "test_status": "success",
            "last_tested_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {"a": 1},
        }
    ]


@pytest.mark.asyncio
async def test_proxy_yandex_disk_file_validates_company_and_storage(monkeypatch):
    from app.api.routes import storage
    from app.utils.signed_urls import _signature
    import time

    request = SimpleNamespace(headers={})

    def _sig(path: str, company_id: int) -> dict:
        """Build a valid, unexpired signature for the proxy endpoint (ARV-004)."""
        exp = int(time.time()) + 300
        return {"exp": exp, "sig": _signature(path, company_id, exp)}

    # Missing/invalid signature must be rejected before any storage lookup.
    with pytest.raises(HTTPException) as unsigned:
        await storage.proxy_yandex_disk_file(request, path="demo/file.jpg", company_id=404, db=_FakeDb())
    assert unsigned.value.status_code == 403

    with pytest.raises(HTTPException) as missing_company:
        await storage.proxy_yandex_disk_file(
            request, path="demo/file.jpg", company_id=404, db=_FakeDb(), **_sig("demo/file.jpg", 404)
        )
    assert missing_company.value.status_code == 404

    company = SimpleNamespace(id=4, storage_provider="local", yandex_disk_token=None)
    db = _FakeDb(get_map={(storage.Company, 4): company})
    with pytest.raises(HTTPException) as wrong_storage:
        await storage.proxy_yandex_disk_file(
            request, path="demo/file.jpg", company_id=4, db=db, **_sig("demo/file.jpg", 4)
        )
    assert wrong_storage.value.status_code == 400
    assert wrong_storage.value.detail == "Company does not use Yandex Disk storage"

    class NotYandexProvider:
        pass

    company = SimpleNamespace(id=5, storage_provider="yandex_disk", yandex_disk_token="encrypted")
    db = _FakeDb(get_map={(storage.Company, 5): company})

    async def _fake_get_provider_for_company(_company):
        return NotYandexProvider()

    monkeypatch.setattr(storage, "get_provider_for_company", _fake_get_provider_for_company)
    with pytest.raises(HTTPException) as mismatch:
        await storage.proxy_yandex_disk_file(
            request, path="demo/file.jpg", company_id=5, db=db, **_sig("demo/file.jpg", 5)
        )
    assert mismatch.value.status_code == 400
    assert mismatch.value.detail == "Provider mismatch"


@pytest.mark.asyncio
async def test_proxy_yandex_disk_file_rejects_expired_signature():
    """ARV-004: an expired signature must not be accepted."""
    from app.api.routes import storage
    from app.utils.signed_urls import _signature
    import time

    request = SimpleNamespace(headers={})
    expired = int(time.time()) - 60

    with pytest.raises(HTTPException) as denied:
        await storage.proxy_yandex_disk_file(
            request,
            path="demo/file.jpg",
            company_id=4,
            exp=expired,
            sig=_signature("demo/file.jpg", 4, expired),
            db=_FakeDb(),
        )
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_proxy_yandex_disk_file_rejects_cross_tenant_signature():
    """ARV-004: a signature minted for one company must not open another's file."""
    from app.api.routes import storage
    from app.utils.signed_urls import _signature
    import time

    request = SimpleNamespace(headers={})
    exp = int(time.time()) + 300

    # Signature is valid for company 4 but the request asks for company 5.
    with pytest.raises(HTTPException) as denied:
        await storage.proxy_yandex_disk_file(
            request,
            path="demo/file.jpg",
            company_id=5,
            exp=exp,
            sig=_signature("demo/file.jpg", 4, exp),
            db=_FakeDb(),
        )
    assert denied.value.status_code == 403


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


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
        self.commit_calls = 0
        self.refresh_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 101
        self.added = obj

    async def flush(self):
        return None

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1

    async def execute(self, _stmt):
        return self.execute_results.pop(0)


def _make_workspace_temp_dir():
    """Create a portable scratch directory.

    Previously hardcoded to ``e:/Project/ARV/.pytest-temp``, which only exists
    on the original developer's machine and made the whole module fail on any
    other host or CI runner.
    """
    return Path(tempfile.mkdtemp(prefix="arv-storage-test-"))
