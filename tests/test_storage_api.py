import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.storage import StorageConnectionCreate


@pytest.mark.asyncio
async def test_create_connection_persists_local_disk_connection():
    from app.api.routes import storage

    payload = StorageConnectionCreate(name="Local", base_path="E:/storage", is_default=True)
    db = _FakeDb()

    result = await storage.create_connection(payload, db)

    assert db.added is not None
    assert db.added.name == "Local"
    assert db.added.provider == "local_disk"
    assert db.added.base_path == "E:/storage"
    assert db.added.is_default is True
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert result is db.added


@pytest.mark.asyncio
async def test_test_connection_reports_missing_base_path():
    from app.api.routes import storage

    conn = SimpleNamespace(
        id=5,
        base_path="e:/Project/ARV/.pytest-temp-storage/missing",
        last_tested_at=None,
        test_status=None,
        test_error=None,
    )
    db = _FakeDb(get_map={(storage.StorageConnection, 5): conn})

    result = await storage.test_connection(5, db)

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

    try:
        result = await storage.test_connection(6, db)
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

    monkeypatch.setattr(storage, "get_storage_provider_instance", lambda: FakeProvider())

    result = await storage.get_storage_stats(7, path="demo", db=db)

    assert result.total_files == 3
    assert result.total_size_bytes == 2048
    assert result.base_path == "demo"


@pytest.mark.asyncio
async def test_set_company_storage_updates_company_fields():
    from app.api.routes import storage

    company = SimpleNamespace(id=9, storage_connection_id=None, storage_path=None)
    db = _FakeDb(get_map={(storage.Company, 9): company})

    result = await storage.set_company_storage(9, storage_connection_id=12, storage_path="/mnt/data", db=db)

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

    result = await storage.list_storage_connections(is_active=True, db=db)

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

    request = SimpleNamespace(headers={})

    with pytest.raises(HTTPException) as missing_company:
        await storage.proxy_yandex_disk_file(request, path="demo/file.jpg", company_id=404, db=_FakeDb())
    assert missing_company.value.status_code == 404

    company = SimpleNamespace(id=4, storage_provider="local", yandex_disk_token=None)
    db = _FakeDb(get_map={(storage.Company, 4): company})
    with pytest.raises(HTTPException) as wrong_storage:
        await storage.proxy_yandex_disk_file(request, path="demo/file.jpg", company_id=4, db=db)
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
        await storage.proxy_yandex_disk_file(request, path="demo/file.jpg", company_id=5, db=db)
    assert mismatch.value.status_code == 400
    assert mismatch.value.detail == "Provider mismatch"


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
    root = Path("e:/Project/ARV/.pytest-temp") / f"storage-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root
