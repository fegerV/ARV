from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.enums import ProjectStatus
from app.schemas.project_api import ProjectCreate, ProjectUpdate


def test_generate_project_links_builds_expected_paths():
    from app.api.routes.projects import _generate_project_links

    links = _generate_project_links(55)

    assert links.edit == "/api/projects/55"
    assert links.delete == "/api/projects/55"
    assert links.view_content == "/api/projects/55/ar-content"


@pytest.mark.asyncio
async def test_batch_ar_content_counts_returns_mapping():
    from app.api.routes import projects

    db = _FakeDb(execute_results=[_FakeRowsResult([(1, 4), (2, 7)])])

    result = await projects._batch_ar_content_counts(db, [1, 2, 3])

    assert result == {1: 4, 2: 7}


@pytest.mark.asyncio
async def test_list_projects_clamps_page_size_and_serializes_links():
    from app.api.routes import projects

    project = SimpleNamespace(
        id=10,
        name="Demo",
        status=ProjectStatus.ACTIVE,
        company_id=2,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db = _FakeDb(
        execute_results=[
            _FakeScalarResult(1),
            _FakeScalarsResult([project]),
            _FakeRowsResult([(10, 6)]),
        ]
    )

    result = await projects.list_projects(page=1, page_size=999, company_id=None, db=db, current_user=SimpleNamespace())

    assert result.total == 1
    assert result.page_size == 20
    assert result.items[0].ar_content_count == 6
    assert result.items[0].model_dump(by_alias=True)["_links"]["edit"] == "/api/projects/10"


@pytest.mark.asyncio
async def test_get_projects_by_company_returns_sorted_items():
    from app.api.routes import projects

    company = SimpleNamespace(id=3, name="Vertex")
    project = SimpleNamespace(
        id=30,
        name="Project A",
        status="active",
        company_id=3,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=None,
    )
    db = _FakeDb(
        get_map={(projects.Company, 3): company},
        execute_results=[
            _FakeScalarsResult([project]),
            _FakeRowsResult([(30, 2)]),
        ],
    )

    result = await projects.get_projects_by_company(3, db, current_user=SimpleNamespace())

    assert result == {
        "projects": [
            {
                "id": 30,
                "name": "Project A",
                "status": "active",
                "company_id": 3,
                "ar_content_count": 2,
                "created_at": project.created_at.isoformat(),
                "updated_at": None,
            }
        ]
    }


@pytest.mark.asyncio
async def test_create_project_general_requires_existing_company():
    from app.api.routes import projects

    payload = ProjectCreate(company_id=1, name="New Project", status=ProjectStatus.ACTIVE)
    db = _FakeDb(get_map={(projects.Company, 1): None})

    with pytest.raises(HTTPException) as exc_info:
        await projects.create_project_general(payload, db, current_user=SimpleNamespace())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Company not found"


@pytest.mark.asyncio
async def test_create_project_general_persists_project():
    from app.api.routes import projects

    company = SimpleNamespace(id=7, name="Vertex")
    db = _FakeDb(get_map={(projects.Company, 7): company})
    payload = ProjectCreate(company_id=7, name="New Project", status=ProjectStatus.ACTIVE)

    result = await projects.create_project_general(payload, db, current_user=SimpleNamespace())

    assert db.added is not None
    assert db.added.company_id == 7
    assert db.added.name == "New Project"
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert result.name == "New Project"


@pytest.mark.asyncio
async def test_update_project_general_updates_fields():
    from app.api.routes import projects

    project = SimpleNamespace(
        id=14,
        name="Before",
        status=ProjectStatus.ACTIVE,
        company_id=3,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db = _FakeDb(
        get_map={(projects.Project, 14): project},
        execute_results=[_FakeScalarResult(9)],
    )

    result = await projects.update_project_general(
        14,
        ProjectUpdate(name="After", status=ProjectStatus.ARCHIVED),
        db,
        current_user=SimpleNamespace(),
    )

    assert project.name == "After"
    assert project.status == ProjectStatus.ARCHIVED
    assert result.ar_content_count == 9
    assert db.commit_calls == 1
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_delete_project_general_blocks_when_content_exists():
    from app.api.routes import projects

    project = SimpleNamespace(id=22, name="Blocked", company_id=5)
    db = _FakeDb(
        get_map={(projects.Project, 22): project},
        execute_results=[_FakeScalarResult(4)],
    )

    with pytest.raises(HTTPException) as exc_info:
        await projects.delete_project_general(22, db, current_user=SimpleNamespace())

    assert exc_info.value.status_code == 400
    assert "Cannot delete project with 4 AR content items" in exc_info.value.detail


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeRowsResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


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
        self.deleted = None
        self.commit_calls = 0
        self.refresh_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 101
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.added = obj

    async def delete(self, obj):
        self.deleted = obj

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1
