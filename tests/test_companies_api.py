from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.enums import CompanyStatus, StorageProviderType
from app.schemas.company_api import CompanyCreate


def test_generate_company_links_builds_expected_paths():
    from app.api.routes.companies import _generate_company_links

    links = _generate_company_links(42)

    assert links.edit == "/companies/42"
    assert links.delete == "/companies/42"
    assert links.view_projects == "/companies/42/projects"
    assert links.view_content == "/companies/42/ar-content"


@pytest.mark.asyncio
async def test_list_companies_clamps_page_size_and_builds_counts():
    from app.api.routes import companies

    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    company = SimpleNamespace(
        id=1,
        name="Vertex",
        contact_email="team@example.com",
        storage_provider="local",
        status=CompanyStatus.ACTIVE,
        created_at=created_at,
    )
    db = _FakeDb(
        execute_results=[
            _FakeScalarResult(1),
            _FakeScalarsResult([company]),
            _FakeRowsResult([SimpleNamespace(company_id=1, count=3)]),
        ]
    )

    result = await companies.list_companies(page=1, page_size=999, search=None, status=None, db=db, current_user=SimpleNamespace())

    assert result.total == 1
    assert result.page_size == 20
    assert result.total_pages == 1
    assert len(result.items) == 1
    assert result.items[0].projects_count == 3
    assert result.items[0].name == "Vertex"
    assert result.items[0].model_dump(by_alias=True)["_links"]["view_projects"] == "/companies/1/projects"


@pytest.mark.asyncio
async def test_create_company_rejects_duplicate_default_name():
    from app.api.routes import companies

    payload = CompanyCreate(name="Vertex AR", contact_email="", status=CompanyStatus.ACTIVE, storage_provider=StorageProviderType.LOCAL)
    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(SimpleNamespace(id=7, name="Vertex AR"))])

    with pytest.raises(HTTPException) as exc_info:
        await companies.create_company(payload, db, current_user=SimpleNamespace())

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_company_persists_new_company(monkeypatch):
    from app.api.routes import companies

    payload = CompanyCreate(
        name="New Co",
        contact_email="hello@example.com",
        status=CompanyStatus.ACTIVE,
        storage_provider=StorageProviderType.LOCAL,
    )
    db = _FakeDb(
        execute_results=[
            _FakeScalarOneOrNoneResult(None),
            _FakeScalarOneOrNoneResult(None),
        ]
    )

    monkeypatch.setattr(companies, "generate_slug", lambda name: "new-co")

    result = await companies.create_company(payload, db, current_user=SimpleNamespace())

    assert db.added is not None
    assert db.added.name == "New Co"
    assert db.added.slug == "new-co"
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert result.name == "New Co"
    assert result.storage_provider == "local"


@pytest.mark.asyncio
async def test_get_yandex_auth_url_requires_client_id(monkeypatch):
    from app.api.routes import companies

    cfg = SimpleNamespace(YANDEX_OAUTH_CLIENT_ID="")
    company = SimpleNamespace(id=5, name="Vertex")
    db = _FakeDb(get_map={(companies.Company, 5): company})

    monkeypatch.setattr(companies, "get_settings", lambda: cfg)

    with pytest.raises(HTTPException) as exc_info:
        await companies.get_yandex_auth_url(5, db, current_user=SimpleNamespace())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "YANDEX_OAUTH_CLIENT_ID is not configured on the server"


@pytest.mark.asyncio
async def test_delete_yandex_token_disconnects_company():
    from app.api.routes import companies

    company = SimpleNamespace(id=9, yandex_disk_token="encrypted", storage_provider="yandex_disk")
    db = _FakeDb(get_map={(companies.Company, 9): company})

    result = await companies.delete_yandex_token(9, db, current_user=SimpleNamespace())

    assert company.yandex_disk_token is None
    assert company.storage_provider == "local"
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert result == {"status": "disconnected", "company_id": 9, "storage_provider": "local"}


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


class _FakeRowsResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.commit_calls = 0
        self.refresh_calls = 0
        self.added = None

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    def add(self, obj):
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if getattr(obj, "id", None) is None:
            obj.id = 101
        self.added = obj

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1
